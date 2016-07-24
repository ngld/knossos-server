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

import logging
import time
import hashlib
import os.path
import tempfile
import shutil

from flask import request, json, jsonify, render_template

from . import tasks
from .central import app, r
from knossos.util import str_random


@app.route('/converter')
def render_conv():
    return render_template('converter.html')


@app.route('/tasks')
def task_monitor():
    return render_template('task_monitor.html')


@app.route('/watch/<int:task_id>')
def render_watcher(task_id):
    return render_template('watcher.html', task_id=task_id)


@app.route('/drop/<int:t>/<token>/<int:kid>', methods=('POST', 'OPTIONS'))
def receive_drop(t, token, kid):
    if app.config.get('UPLOAD_PATH', None) is None or app.config.get('MIRROR_PATH', None) is None:
        return 'Access denied', 403

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Max-Age': '86400'
    }

    if request.method == 'OPTIONS':
        return '', 200, headers

    if time.time() > t:
        return 'Access denied', 403, headers

    try:
        key = app.config['API_KEYS'][kid]
    except KeyError:
        return 'Access denied', 403, headers

    my_tk = hashlib.new('sha256')
    my_tk.update(('%s%d' % (key, t)).encode('utf8'))
    my_tk = my_tk.hexdigest()
    if my_tk != token:
        return 'Access denied', 403, headers

    if 'file' not in request.files:
        return 'Access denied', 403, headers

    file = request.files['file']
    if file.filename == '' or '.' not in file.filename or file.filename.rsplit('.', 1)[1] not in app.config['UPLOAD_EXTENSIONS']:
        return jsonify(
            error=True,
            message='Invalid filename!'
        ), 200, headers

    fhash = hashlib.new('sha256')
    fs = file.stream
    buf = None

    if not file.stream.seekable():
        buf = tempfile.TemporaryFile()

        # This while loop is copy&pasted from below to avoid checking buf on every iteration
        while True:
            chunk = fs.read(32 * fhash.block_size)
            if not chunk:
                break

            fhash.update(chunk)
            buf.write(chunk)
    else:
        while True:
            chunk = fs.read(32 * fhash.block_size)
            if not chunk:
                break

            fhash.update(chunk)

    suffix = app.config['UPLOAD_PATH'] + '/' + fhash.hexdigest()
    dst = os.path.join(app.config['MIRROR_PATH'], suffix)
    
    if not os.path.isfile(dst):
        if buf is None:
            file.stream.seek(0)
            file.save(dst)
        else:
            with open(dst, 'wb') as stream:
                shutil.copyfileobj(buf, stream)

            buf.close()

    return jsonify(
        error=False,
        url=app.config['MIRROR_URL'] + '/' + suffix
    ), 200, headers


@app.route('/api/converter/request', methods=('POST',))
def conv_request():
    passwd = request.form.get('passwd')
    if passwd not in app.config['API_KEYS']:
        return 'Access denied', 403

    data = request.form.get('data', None)
    webhook = request.form.get('webhook', None)
    token = str_random(30)

    try:
        data = json.loads(data)
    except ValueError:
        logging.exception('Received invalid JSON in converter request!')
        return jsonify(
            ticket=None,
            token=None,
            error=True
        )

    task_id = tasks.ConverterTask(data, webhook, token).run_async()

    return jsonify(
        ticket=task_id,
        token=token
    )


@app.route('/api/converter/get_status/<int:task_id>')
def conv_get_status(task_id):
    task = tasks.ConverterTask(id_=task_id)
    return json.dumps(task.get_status())


@app.route('/api/converter/retrieve', methods=('POST',))
def conv_retrieve():
    try:
        task = tasks.ConverterTask(id_=request.form.get('ticket', None))
    except:
        return jsonify(
            json=None,
            success=False,
            finished=True,
            found=False
        )

    if not task.has_result():
        return jsonify(
            json=None,
            success=False,
            finished=False,
            found=True
        )

    result = task.get_result()

    if result['token'] != request.form.get('token'):
        return ('Failed to validate token!', 403, [])

    data = jsonify(
        json=result['json'],
        success=result['success'],
        finished=True
    )
    task.remove()

    return data


@app.route('/api/list_tasks')
def list_tasks():
    tasks = {}
    for task in r.hkeys('task_status'):
        task = task.decode('utf8')
        tasks[task] = json.loads(r.hget('task_status', task))

    return json.dumps(tasks)
