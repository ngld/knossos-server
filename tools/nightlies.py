## Copyright 2015 Knossos authors, see NOTICE file
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

from __future__ import absolute_import, print_function, division

import os.path
import codecs
import sys
import logging
import json
import re
import copy
import requests


logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s@%(module)s] %(funcName)s %(levelname)s: %(message)s')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'knossos'))

LIST_PAGE = 'https://dl.bintray.com/scp-fs2open/FSO/'
sess = requests.Session()

MOD_TPL = {
    'id': 'FSO_nightlies',
    'title': 'FSO Nightly',
    'type': 'engine',
    'version': None,
    'description': 'The cutting-edge of what the SCP is doing. New builds, using the latest git changes, are automatically posted every evening.',
    'logo': 'https://fsnebula.org/uploads/img/5.bmp',
    'notes': '',
    'folder': 'FSO_nightly',
    'packages': [],
    'actions': []
}

PKG_TPL = {
    # 'name': '...', // required
    'notes': '',
    'status': 'required',
    'dependencies': [],
    # 'environment': [ // optional
    #     {
    #         'type': 'cpu_feature', // required
    #         'value': '<SSE|SSE2|AVX|...>', // required
    #         'not': false // optional, default: false, this value negates the requirement
    #         //              (The package isn't installed if the user's processor has this feature.)
    #     },
    #     {
    #         'type': 'os', // required
    #         'value': '<windows|linux|macos>', // required
    #         'not': false, // optional, default: false, this value negates the requirement
    #         //              (The package isn't installed if the user uses the given OS.)
    #     },
    #     ...
    # ],
    # 'executables': [ // optional
    #     {
    #         'version': '...', // required, http://semver.org
    #         'file': '...', // required, path to the executable (*.exe file on Windows), relative to the mod folder
    #         'debug': false // optional, default: true, Is this a debug build?
    #     }
    # ],
    # 'files': [ // optional
    #     /* You can use this syntax ...
    #         [
    #             [ // required
    #                 '<link1>',
    #                 '...'
    #             ],
    #             {
    #                 '<filename>': {
    #                     'is_archive': true, // optional, default: true
    #                     'dest': '<destination path>' // optional, default: '', relative to the mod folder
    #                 }
    #             }
    #         ],
    #         ...
    #     /* ... or this one: */
    #         {
    #             'filename': '<filename>', // required
    #             'is_archive': true, // optional, default: true
    #             'dest': '<destination path>', // optional, default: '', relative to the mod folder
    #             'urls': ['<url1>', '<url2>'] // required
    #         },
    #         ...
    #     /* . */
    # ]
}


def add_nightly(link, date, rev, os_name, info):
    if os_name not in ('Win32', 'Win64', 'Linux', 'MacOSX'):
        logging.warning('Unknown OS %s!', os_name)
        return

    if info['mod']['version'] is None:
        info['mod']['version'] = '0.0.%s+%s' % (date, rev)

    dl_link = os.path.join(LIST_PAGE, link)
    pkg = copy.deepcopy(PKG_TPL)
    pkg['files'] = [{
        'filename': os.path.basename(dl_link),
        'is_archive': True,
        'dest': '',
        'urls': [dl_link]
    }]

    if os_name == 'Win32':
        info['has_win32'] = True
        pkg['name'] = 'Windows'
        pkg['environment'] = [
            {
                'type': 'os',
                'value': 'windows'
            },
            {
                'type': 'cpu_feature',
                'value': 'x86_32'
            }
        ]
        info['mod']['packages'].append(pkg)
    elif os_name == 'Win64':
        info['has_win64'] = True
        pkg['name'] = 'Windows (64bit)'
        pkg['environment'] = [
            {
                'type': 'os',
                'value': 'windows'
            },
            {
                'type': 'cpu_feature',
                'value': 'x86_64'
            }
        ]
        info['mod']['packages'].append(pkg)
    elif os_name == 'Linux':
        info['has_linux64'] = True
        pkg['name'] = 'Linux (64bit)'
        pkg['environment'] = [
            {
                'type': 'os',
                'value': 'linux'
            },
            {
                'type': 'cpu_feature',
                'value': 'x86_64'
            }
        ]
        info['mod']['packages'].append(pkg)
    elif os_name == 'OS X':
        info['has_macos'] = True
        pkg['name'] = 'Mac OS X'
        pkg['environment'] = [
            {
                'type': 'os',
                'value': 'macos'
            }
        ]
        info['mod']['packages'].append(pkg)


def fetch_nightlies(json_file):
    global LIST_PAGE, sess

    repo = {'mods': []}

    revs = {}
    nlist = sess.get(LIST_PAGE)

    # <pre><a onclick="navi(event)" href=":nightly_20160727_aec35e4-builds-Linux.tar.gz" rel="nofollow">nightly_20160727_aec35e4-builds-Linux.tar.gz</a></pre>
    for m in re.finditer(r'<a [^>]+>(?P<file>nightly_(?P<date>[0-9]+)_(?P<rev>[0-9a-f]+)\-builds\-(?P<os>[A-Za-z3264]+)\.(?P<ext>tar\.gz|zip))</a>', nlist.text):
        rev =  m.group('rev')
        if rev in revs:
            info = revs[rev]
            if m.group('os') == 'Win32' and info['has_win32']:
                continue
            elif m.group('os') == 'Win64' and info['has_win64']:
                continue
            elif m.group('os') == 'Linux' and info['has_linux64']:
                continue
            elif m.group('os') == 'MacOSX' and info['has_macos']:
                continue
        else:
            mod = copy.deepcopy(MOD_TPL)
            repo['mods'].append(mod)

            info = revs[rev] = {
                'mod': mod,
                'has_macos': False,
                'has_linux': False,
                'has_linux64': False,
                'has_win32': False,
                'has_win64': False
            }

        add_nightly(m.group('file'), m.group('date'), rev, m.group('os'), info)

    if not json_file:
        print(json.dumps(repo))
    else:
        with open(json_file, 'w') as stream:
            json.dump(repo, stream)


def main(args):
    if len(args) < 1:
        fetch_nightlies(None)
    else:
        fetch_nightlies(args[0])


if __name__ == '__main__':
    codecs.register_error('strict', codecs.replace_errors)
    codecs.register_error('really_strict', codecs.strict_errors)
    main(sys.argv[1:])
