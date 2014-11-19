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


class MessagesFormatter(logging.Formatter):

    def format(self, record):
        """
        Format the specified record as text.

        The record's attribute dictionary is used as the operand to a
        string formatting operation which yields the returned string.
        Before formatting the dictionary, a couple of preparatory steps
        are carried out. The message attribute of the record is computed
        using LogRecord.getMessage(). If the formatting string uses the
        time (as determined by a call to usesTime(), formatTime() is
        called to format the event time. If there is exception information,
        it is formatted using formatException() and appended to the message.
        """
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)
        return s


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


class TaskLogHandler(logging.Handler):
    task = None

    def __init__(self, task, level=logging.NOTSET):
        super(TaskLogHandler, self).__init__(level)

        self.task = task

    def emit(self, record):
        try:
            fr = self.format(record)
            self.send(fr)
        except:
            self.handleError(record)

    def send(self, data):
        self.task.emit('log_message', data)


def ws_logging(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s'):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(ws):
            h = WebSocketHandler(ws, level)
            h.setFormatter(MessagesFormatter(format))
            l = logging.getLogger()
            l.addHandler(h)

            try:
                func(ws)
            finally:
                l.removeHandler(h)

        return wrapper

    return decorator
