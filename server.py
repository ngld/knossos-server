#!/usr/bin/python
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

from __future__ import absolute_import, print_function
import logging
import sys
import os

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'knossos'))

from flask import Flask, render_template
from flask.ext.uwsgi_websocket import WebSocket

app = Flask(__name__)
ws = WebSocket(app)


@app.route('/')
def index_page():
    return 'Hi, there!'


if __name__ == '__main__':
    app.run()
