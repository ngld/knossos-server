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

from flask import request, json, jsonify, render_template

from . import models
from .output import ws_logging, str_random
from .central import app, db, ws


@app.route('/converter')
def render_conv():
    return render_template('converter.html')


@app.route('/api/converter/request', methods=('POST',))
def conv_request():
    logging.info('Received password "%s".', request.form.get('passwd', 'None!'))

    data = request.form.get('data', None)
    token = str_random(30)

    r = models.ConvRequest(token=token, data=data)
    db.session.add(r)
    db.session.commit()

    return jsonify(
        ticket=r.id_,
        token=r.token
    )


@app.route('/api/converter/retrieve', methods=('POST',))
def conv_retrieve():
    r = db.session.query(models.ConvRequest).filter_by(id_=request.form.get('ticket', None)).one()
    if r.token != request.form.get('token'):
        return ('Failed to validate token!', 403, [])

    data = r.result
    db.session.delete(r)
    db.session.commit()

    return data


@ws.route('/ws/converter')
@ws_logging
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

    in_fd, repo = tempfile.mkstemp()
    os.close(in_fd)

    out_fd, output = tempfile.mkstemp()
    os.close(out_fd)

    try:
        mid = int(ws.receive())
        tk = db.session.query(models.ConvRequest).filter_by(id_=mid).one()

        with open(repo, 'w') as stream:
            stream.write(tk.data)

        import converter

        converter.main(['checksums', repo, output], p_wrap)
    except:
        logging.exception('Failed to process request!')
    else:
        with open(output, 'r') as stream:
            tk.result = stream.read()

        db.session.add(tk)
        db.session.commit()

        ws.send(json.dumps(('done',)))
    finally:
        os.unlink(repo)
        os.unlink(output)
