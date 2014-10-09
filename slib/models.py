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

from .central import db


class ConvRequest(db.Model):
    id_ = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(30))
    data = db.Column(db.Text)
    result = db.Column(db.Text)
    status = db.Column(db.Integer)
    webhook = db.Column(db.String(100))
    expire = db.Column(db.Integer)

    # Constants
    WAITING = 1
    WORKING = 2
    DONE = 3
    FAILED = 4
