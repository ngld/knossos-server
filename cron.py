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

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(threadName)s:%(module)s.%(funcName)s: %(message)s')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'knossos'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'third_party'))

import time

from slib.central import app, db
from slib import models


def main():
    with app.test_request_context():
        db.session.query(models.ConvRequest).filter(models.ConvRequest.expire > time.time()).delete()
        db.session.commit()


if __name__ == '__main__':
    main()