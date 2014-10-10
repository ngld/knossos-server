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

import json
import logging
import functools
import random


class WebSocketHandler(logging.Handler):
    socket = None

    def __init__(self, socket, level=logging.NOTSET):
        super(WebSocketHandler, self).__init__(level)

        self.socket = socket

    def emit(self, record):
        try:
            fr = self.format(record)
            self.send(fr)
        except:
            self.handleError(record)

    def send(self, data):
        data = ('log_message', data)
        data = json.dumps(data)
        self.socket.send(data)


def ws_logging(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s'):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(ws):
            h = WebSocketHandler(ws, level)
            h.setFormatter(logging.Formatter(format))
            l = logging.getLogger()
            l.addHandler(h)

            try:
                func(ws)
            finally:
                l.removeHandler(h)

        return wrapper

    return decorator


def str_random(slen):
    s = ''
    for i in range(0, slen):
        s += random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

    return s
