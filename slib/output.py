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
        if record.exc_info is not None:
            exc_msg = str(record.exc_info[1])
            if exc_msg != record.message:
                s += ' (' + exc_msg + ')'
        
        return s


class TaskLogHandler(logging.Handler):
    task = None

    def __init__(self, task, level=logging.NOTSET):
        super(TaskLogHandler, self).__init__(level)

        self.task = task

    def emit(self, record):
        try:
            self.send(self.format(record))
        except:
            self.handleError(record)

    def send(self, data):
        self.task.emit('log_message', data)
