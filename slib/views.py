## Copyright 2014 fs2mod-py authors, see NOTICE file
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

import os
import logging
import tempfile
import time
import re
from urllib.request import urlopen
from urllib.parse import urlencode

from flask import request, json, jsonify, render_template
from sqlalchemy.orm.exc import NoResultFound

from . import models
from .output import ws_logging
from .central import app, db, ws
from lib.util import str_random


@app.route('/converter')
def render_conv():
    return render_template('converter.html')


@app.route('/api/converter/request', methods=('POST',))
def conv_request():
    passwd = request.form.get('passwd')
    if passwd not in app.config['API_KEYS']:
        return 'Access denied', 403

    data = request.form.get('data', None)
    token = str_random(30)

    r = models.ConvRequest(token=token, data=data,
        webhook=request.form.get('webhook', None),
        status=models.ConvRequest.WAITING,
        expire=time.time() + 1 * 24 * 60 * 60)  # Will expire after a day

    db.session.add(r)
    db.session.commit()

    return jsonify(
        ticket=r.id_,
        token=r.token
    )


@app.route('/api/converter/get_status/<int:ticket>')
def conv_get_status(ticket):
    try:
        r = db.session.query(models.ConvRequest).filter_by(id_=ticket).one()
    except NoResultFound:
        logging.exception('Couldn\'t find converter ticket!')
        return 0

    return r.status


@app.route('/api/converter/retrieve', methods=('POST',))
def conv_retrieve():
    try:
        r = db.session.query(models.ConvRequest).filter_by(id_=request.form.get('ticket', None)).one()
    except NoResultFound:
        return jsonify(
            json=None,
            success=False,
            finished=True,
            found=False
        )

    if r.token != request.form.get('token'):
        return ('Failed to validate token!', 403, [])

    if r.status not in (models.ConvRequest.DONE, models.ConvRequest.FAILED):
        return jsonify(
            json=None,
            success=False,
            finished=False,
            found=True
        )

    data = jsonify(
        json=r.result,
        success=r.status == models.ConvRequest.DONE,
        finished=True
    )
    db.session.delete(r)
    db.session.commit()

    return data


@ws.route('/ws/converter')
@ws_logging(logging.INFO, '%(levelname)s: %(message)s')
def do_convert(ws):
    os.environ['QT_API'] = 'headless'
    from lib import progress, util, qt
    from converter import download

    download.init_ws_mode(ws)

    lu = 0
    dl_path = None
    dl_link = None

    def p_update(prog, text):
        nonlocal lu

        # Throttle updates
        now = time.time()

        if now - lu > 0.3:
            ws.send(json.dumps(('progress', prog, text)))
            lu = now

    def p_wrap(cb):
        progress.set_callback(p_update)
        ws_keep_alive()
        cb()

    def ws_keep_alive():
        # Make sure the WebSocket connection stays alive.
        try:
            ws.send('["keep_alive"]')
        except:
            pass

        qt.QtCore.QTimer.singleShot(1000, ws_keep_alive)

    with tempfile.TemporaryDirectory() as tdir:
        repo = os.path.join(tdir, 'repo.json')
        output = os.path.join(tdir, 'out.json')

        try:
            mid = int(ws.receive())
            tk = db.session.query(models.ConvRequest).filter_by(id_=mid).one()
        except NoResultFound:
            logging.exception('Failed to process request! I can\'t find your ticket.')
            ws.send(json.dumps('what ticket?',))
            return

        if app.config['MIRROR_PATH'] is not None:
            try:
                info = json.loads(tk.data)
            except:
                # No point in logging invalid JSON here. It will be logged later, anyway.
                pass
            else:
                try:
                    if 'mods' not in info and 'title' in info and 'id' in info:
                        mods = [info]
                    else:
                        mods = info['mods']

                    if len(mods) == 1:
                        dl_path = os.path.join(os.path.basename(mods[0]['id']), os.path.basename(mods[0]['version']))
                    else:
                        dl_path = 'general'

                    dl_link = util.pjoin(app.config['MIRROR_URL'], dl_path)
                    dl_path = os.path.join(app.config['MIRROR_PATH'], dl_path)

                    if not os.path.isdir(dl_path):
                        os.makedirs(dl_path)
                except KeyError:
                    # We're missing some keys here, this will be logged later, too.
                    dl_path = None

        try:
            tk.status = models.ConvRequest.WORKING
            db.session.add(tk)
            db.session.commit()

            with open(repo, 'w') as stream:
                stream.write(tk.data)

            import converter

            result = converter.generate_checksums(repo, output, p_wrap, dl_path, dl_link)

            # Clear the cache to prevent a memory leak.
            util.HASH_CACHE = {}

            if os.path.isfile(output):
                with open(output, 'r') as stream:
                    tk.result = stream.read()
        except ValueError as exc:
            logging.exception('Failed to parse JSON data: %s', str(exc))
            result = False
        except:
            logging.exception('Failed to perform conversion!')
            result = False
        
        if result:
            tk.status = models.ConvRequest.DONE
        else:
            tk.status = models.ConvRequest.FAILED

        db.session.add(tk)
        db.session.commit()
        
        if tk.webhook is not None:
            if re.match(r'^https?://(localhost|127\..*)', tk.webhook):
                logging.warning('Ignored the webhook because it points to localhost.')
            else:
                try:
                    hdl = urlopen(tk.webhook, data=urlencode({'ticket': tk.id_}).encode('utf8'))
                    response = hdl.read().decode('utf8', 'replace').strip()
                    hdl.close()

                    if len(response) > 0 and '{' in response:
                        response = json.loads(response)
                        if isinstance(response, dict) and response.get('cancelled', False):
                            db.session.delete(tk)
                            db.session.commit()
                except:
                    logging.exception('Webhook failed!')

        ws.send(json.dumps(('done', result)))

    download.finish_mode()
