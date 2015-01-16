#!/usr/bin/python
## Copyright 2014 Knossos authors, see NOTICE file
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

from __future__ import absolute_import, print_function
import logging
import sys
import os
import functools

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s@%(module)s] %(funcName)s %(levelname)s: %(message)s')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'knossos'))

import tornadoredis
from tornado import ioloop, web, websocket, gen
from flask import json

from slib.central import app, r
from slib.util import parse_redis_url

redis_sub = None
watchers = {}


def redis_listener(msg):
    global watchers

    if msg.kind == 'message':
        try:
            data = json.loads(msg.body)
        except ValueError:
            logging.exception('Received invalid JSON from Redis!')
            return

        task = msg.channel
        if task in watchers:
            for w in watchers[task]:
                w(data)
    elif msg.kind == 'disconnect':
        # Disconnected from the server.
        # TODO: Should we try to reconnect?
        logging.error('Disconnected from Redis!')


@gen.coroutine
def subscribe_task(task, cb):
    global watchers
    task = 'task_' + str(task)

    if task not in watchers:
        watchers[task] = [cb]
        yield gen.Task(redis_sub.subscribe, task)
    else:
        watchers[task].append(cb)

    if len(watchers) == 1:
        logging.debug('Starting Redis listener...')
        redis_sub.listen(redis_listener)


@gen.coroutine
def unsubscribe_task(task, cb):
    global watchers
    task = 'task_' + str(task)

    watchers[task].remove(cb)
    if len(watchers[task]) == 0:
        del watchers[task]
        yield gen.Task(redis_sub.unsubscribe, task)


class WatchHandler(websocket.WebSocketHandler):
    _task_id = None
    _pinger = None

    def check_origin(self, origin):
        return True

    @gen.coroutine
    def open(self, task):
        self._task_id = int(task)
        self._pinger = ioloop.PeriodicCallback(functools.partial(self.ping, b' '), 5000)
        self._pinger.start()

        # Deliver all stored log entries.
        log_name = 'task_' + task + '_log'
        log_entries = r.lrange(log_name, 0, r.llen(log_name))

        for entry in log_entries:
            self.write_message(entry)

        yield subscribe_task(self._task_id, self._process_message)

    def on_message(self, msg):
        pass

    @gen.coroutine
    def on_close(self):
        self._pinger.stop()
        yield unsubscribe_task(self._task_id, self._process_message)

    def _process_message(self, msg):
        self.write_message(json.dumps(msg))


class InteractiveHandler(WatchHandler):

    def on_message(self, msg):
        # Make sure the JSON data is valid.
        try:
            json.loads(msg)
        except ValueError:
            logging.exception('Received invalid JSON!')
            return

        r.publish('task_' + str(self._task_id) + '_input', msg)


if __name__ == '__main__':
    redis_sub = tornadoredis.Client(**parse_redis_url(app.config['REDIS']))
    application = web.Application([
        (r'/ws/watcher/(\d+)', WatchHandler),
        (r'/ws/inter/(\d+)', InteractiveHandler)
    ])
    
    application.listen(app.config['WS_LISTEN'][1], app.config['WS_LISTEN'][0])

    logging.info('Ready.')
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        logging.info('Shutting down...')
