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
