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
from urllib.request import urlopen
from urllib.parse import urlencode

from flask import request, json, jsonify, render_template
from sqlalchemy.orm.exc import NoResultFound

from . import models
from .output import ws_logging, str_random
from .central import app, db, ws


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
    from lib import progress

    lu = 0

    def p_update(prog, text):
        nonlocal lu

        # Throttle updates
        now = time.time()

        if now - lu > 0.3:
            ws.send(json.dumps(('progress', prog, text)))
            lu = now

    def p_wrap(cb):
        progress.set_callback(p_update)
        cb()

    with tempfile.TemporaryDirectory() as tdir:
        repo = os.path.join(tdir, 'repo.json')
        output = os.path.join(tdir, 'out.json')

        try:
            mid = int(ws.receive())
            tk = db.session.query(models.ConvRequest).filter_by(id_=mid).one()
        except NoResultFound:
            logging.exception('Failed to process request!')
            ws.send(json.dumps('what ticket?',))
            return

        try:
            tk.status = models.ConvRequest.WORKING
            db.session.add(tk)
            db.session.commit()

            with open(repo, 'w') as stream:
                stream.write(tk.data)

            import converter

            result = converter.generate_checksums(repo, output, p_wrap)

            if os.path.isfile(output):
                with open(output, 'r') as stream:
                    tk.result = stream.read()
        except:
            logging.exception('Failed to perform conversion!')
            result = False
        
        if result:
            tk.status = models.ConvRequest.DONE
        else:
            tk.status = models.ConvRequest.FAILED

        # try:
        #     # Embed all logos...
        #     obj = json.loads(tk.result)
        #     for m in obj['mods']:
        #         if m.get('logo'):
        #             logo = os.path.join(tdir, m['logo'])
        #             if os.path.isfile(logo):
        #                 root, ext = os.path.splitext(logo)
        #                 data = 'data:image/' + ext[1:] + ',base64;'
        #                 with open(logo, 'rb') as stream:
        #                     data += base64.b64encode(stream.read()).decode('utf8')

        #                 m['logo'] = data

        #     tk.result = json.dumps(obj)
        # except:
        #     pass

        db.session.add(tk)
        db.session.commit()
        
        if tk.webhook is not None:
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
