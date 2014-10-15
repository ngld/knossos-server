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


def app_config(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'
    app.config['API_KEYS'] = ('<secret>',)
    app.config['MIRROR_PATH'] = 'dls'
    app.config['MIRROR_URL'] = 'http://localhost/mirror'
