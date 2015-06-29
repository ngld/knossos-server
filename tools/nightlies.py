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
import argparse
import logging
import json
import re
import copy
import time
import requests


logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s@%(module)s] %(funcName)s %(levelname)s: %(message)s')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'knossos'))

LIST_PAGE = 'http://www.hard-light.net/forums/index.php?board=173.0'
LIN64_LIST = 'https://build.tproxy.de/builders/fs2-trunk-linux'
LIN64_API = 'https://build.tproxy.de/json/builders/fs2-trunk-linux/builds/%s'
FS2_VER = '3.7.1'
sess = requests.Session()

MOD_TPL = {
    'id': 'FSO_nightlies',
    'title': 'FSO Nightly',
    'version': None,
    'description': 'The cutting-edge of what the SCP is doing. New builds, using the latest SVN changes, are automatically posted every evening.',
    'logo': 'https://fsnebula.org/uploads/img/7.bmp',
    'notes': '',
    'folder': 'FSO_nightly',
    'packages': [],
    # version
    "actions": []
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


def add_nightly(link, rev, os_name, info):
    if os_name == 'FreeBSD':
        # Sorry but we don't support BSDs
        return

    if os_name not in ('Windows', 'Linux', 'OS X'):
        logging.warning('Unknown OS %s!', os_name)
        return

    page = sess.get(link.replace('&amp;', '&'))
    if info['mod']['version'] is None:
        version = re.search(r'fso_Standard_([0-9]+)_[0-9a-f]+\.', page.text)
        if not version:
            logging.error('Failed to find a build date for "%s %s"!', rev, os_name)
            return

        info['mod']['version'] = '0.0.%s+%s' % (version.group(1), rev)

    dl_link = re.search(r'Group: Standard<br/><a href="(http://[^"]+)"', page.text)
    if not dl_link:
        logging.error('Failed to find a download link for "%s %s"!', rev, os_name)
        return

    dl_link = dl_link.group(1)
    pkg = copy.deepcopy(PKG_TPL)
    pkg['files'] = [{
        'filename': os.path.basename(dl_link),
        'is_archive': True,
        'dest': '',
        'urls': [dl_link]
    }]

    version = info['mod']['version']

    if os_name == 'Windows':
        fs2_file = os.path.basename(dl_link).replace('fso_Standard', 'fs2_open_' + FS2_VER.replace('.', '_'))

        info['has_windows'] = True
        pkg['name'] = 'Windows'
        pkg['environment'] = [
            {
                'type': 'os',
                'value': 'windows'
            },
            {
                'type': 'cpu_feature',
                'value': 'sse2'
            }
        ]
        # pkg['executables'] = [
        #     {
        #         'version': version,
        #         'file': fs2_file,
        #         'debug': False
        #     },
        #     {
        #         'version': version,
        #         'file': fs2_file.replace('.exe', '-DEBUG.exe'),
        #         'debug': True
        #     }
        # ]
        info['mod']['packages'].append(pkg)

        no_sse_link = re.search(r'Group: NO-SSE<br/><a href="(http://[^"]+)"', page.text)
        if not no_sse_link:
            logging.error('Failed to find the no-sse download link for "%s %s"!', rev, os_name)
        else:
            no_sse_link = no_sse_link.group(1)
            fs2_file = os.path.basename(no_sse_link).replace('fso_NO-SSE', 'fs2_open_' + FS2_VER.replace('.', '_') + '_NO-SSE')
            pkg = PKG_TPL.copy()
            pkg['files'] = [{
                'filename': os.path.basename(no_sse_link),
                'is_archive': True,
                'dest': '',
                'urls': [no_sse_link]
            }]

            pkg['name'] = 'Windows NO-SSE'
            pkg['status'] = 'recommended'
            pkg['environment'] = [
                {
                    'type': 'os',
                    'value': 'windows'
                }
            ]
            # pkg['executables'] = [
            #     {
            #         'version': version + '+NO-SSE',
            #         'file': fs2_file,
            #         'debug': False
            #     },
            #     {
            #         'version': version + '+NO-SSE',
            #         'file': fs2_file.replace('.exe', '-DEBUG.exe'),
            #         'debug': True
            #     }
            # ]
            info['mod']['packages'].append(pkg)

        sse_link = re.search(r'Group: SSE<br/><a href="(http://[^"]+)"', page.text)
        if not sse_link:
            logging.error('Failed to find the sse download link for "%s %s"!', rev, os_name)
            return
        else:
            sse_link = sse_link.group(1)
            fs2_file = os.path.basename(sse_link).replace('fso_SSE', 'fs2_open_' + FS2_VER.replace('.', '_') + '_SSE')
            pkg = PKG_TPL.copy()
            pkg['files'] = [{
                'filename': os.path.basename(sse_link),
                'is_archive': True,
                'dest': '',
                'urls': [sse_link]
            }]

            pkg['name'] = 'Windows SSE'
            pkg['status'] = 'recommended'
            pkg['environment'] = [
                {
                    'type': 'os',
                    'value': 'windows'
                },
                {
                    'type': 'cpu_feature',
                    'value': 'sse'
                }
            ]
            # pkg['executables'] = [
            #     {
            #         'version': version + '+SSE',
            #         'file': fs2_file,
            #         'debug': False
            #     },
            #     {
            #         'version': version + '+SSE',
            #         'file': fs2_file.replace('.exe', '-DEBUG.exe'),
            #         'debug': True
            #     }
            # ]
            info['mod']['packages'].append(pkg)
    elif os_name == 'Linux':
        fs2_file = os.path.basename(dl_link).replace('fso_Standard', 'fs2_open_' + FS2_VER)
        info['has_linux'] = True
        pkg['name'] = 'Linux'
        pkg['environment'] = [
            {
                'type': 'os',
                'value': 'linux'
            },
            {
                'type': 'cpu_feature',
                'value': 'x86_32'
            }
        ]
        # pkg['executables'] = [
        #     {
        #         'version': version,
        #         'file': fs2_file,
        #         'debug': False
        #     },
        #     {
        #         'version': version,
        #         'file': fs2_file + '-DEBUG',
        #         'debug': True
        #     }
        # ]
        info['mod']['packages'].append(pkg)
    elif os_name == 'OS X':
        # fs2_file = os.path.basename(dl_link).replace('fso_Standard', 'fs2_open_' + FS2_VER).replace('.tgz', '')
        info['has_macos'] = True
        pkg['name'] = 'Mac OS X'
        pkg['environment'] = [
            {
                'type': 'os',
                'value': 'macos'
            }
        ]
        # pkg['executables'] = [
        #     {
        #         'version': version,
        #         'file': fs2_file + '.app/Contents/MacOS/FS2_Open ' + FS2_VER,
        #         'debug': False
        #     },
        #     {
        #         'version': version,
        #         'file': fs2_file + ' (debug).app/Contents/MacOS/FS2_Open ' + FS2_VER + ' (debug)',
        #         'debug': True
        #     }
        # ]
        info['mod']['packages'].append(pkg)


def fetch_nightlies(json_file):
    global LIST_PAGE, sess

    if os.path.isfile(json_file):
        with open(json_file, 'r') as stream:
            repo = json.load(stream)
    else:
        repo = {'mods': []}

    old_revs = {}
    for mod in repo['mods']:
        rev = mod['version']
        if '+' in rev:
            # 0.0.20150929+0a9ae3e
            rev = rev[rev.find('+') + 1:]
        else:
            # 0.0.4903
            rev = rev.split('.')[2]

        info = old_revs[rev] = {
            'mod': mod,
            'has_macos': False,
            'has_linux': False,
            'has_linux64': False,
            'has_windows': False
        }

        for pkg in mod['packages']:
            if pkg['name'] == 'Windows':
                info['has_windows'] = True
            elif pkg['name'] == 'Mac OS X':
                info['has_macos'] = True
            elif pkg['name'] == 'Linux':
                info['has_linux'] = True
            elif pkg['name'] == 'Linux (64bit)':
                info['has_linux64'] = True

    nlist = sess.get(LIST_PAGE)

    for m in re.finditer(r'<a href="([^"]+)">Nightly \(([^\)]+)\): [0-9]+ [A-Za-z]+ [0-9]+ - Revision ([0-9a-f]+)</a>', nlist.text):
        rev = m.group(3)
        if rev in old_revs:
            info = old_revs[rev]
            if m.group(2) == 'Windows' and info['has_windows']:
                continue
            elif m.group(2) == 'Linux' and info['has_linux']:
                continue
            elif m.group(2) == 'OS X' and info['has_macos']:
                continue
        else:
            mod = copy.deepcopy(MOD_TPL)
            repo['mods'].append(mod)
            
            info = old_revs[rev] = {
                'mod': mod,
                'has_macos': False,
                'has_linux': False,
                'has_linux64': False,
                'has_windows': False
            }

        hass = []
        for os_name in ('macos', 'linux', 'linux64', 'windows'):
            if info['has_' + os_name]:
                hass.append(os_name)

        logging.info('Fetching %s info for %s which already has %s.', m.group(2), rev, ', '.join(hass))
        add_nightly(m.group(1), rev, m.group(2), info)

    nlist = sess.get(LIN64_LIST)

    for m in re.finditer(r'">([0-9a-f]{7})[0-9a-f]+</a>\s*</div>\s*</div>\s*</td>\s*<td class="success">success</td>\s*<td><a href="[^"]+">#([0-9]+)</a></td>', nlist.text):
        rev = m.group(1)

        if rev in old_revs:
            info = old_revs[rev]
            if info['has_linux64']:
                continue
        else:
            mod = copy.deepcopy(MOD_TPL)
            repo['mods'].append(mod)

            info = old_revs[rev] = {
                'mod': mod,
                'has_macos': False,
                'has_linux': False,
                'has_linux64': False,
                'has_windows': False
            }

        link = LIN64_API % m.group(2)
        page = sess.get(link)
        data = json.loads(page.text)

        rev = data['sourceStamps'][0]['revision'][:7]
        stamp = time.strftime('%Y%m%d', time.gmtime(data['times'][1]))
        version = '0.0.%s+%s' % (stamp, rev)

        if info['mod']['version'] is None:
            info['mod']['version'] = version

        dl_link = None
        for step in data['steps']:
            if step['name'] == 'upload':
                dl_link = next(iter(step['urls'].values()))
                break

        if not dl_link:
            logging.error('Failed to find download link for "%s"!', link)
            continue

        info['has_linux64'] = True

        pkg = copy.deepcopy(PKG_TPL)
        pkg['files'] = [{
            'filename': os.path.basename(dl_link),
            'is_archive': True,
            'dest': '',
            'urls': [dl_link]
        }]
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
        # pkg['executables'] = [
        #     {
        #         'version': version,
        #         'file': 'fs2_open_' + FS2_VER,
        #         'debug': False
        #     },
        #     {
        #         'version': version,
        #         'file': 'fs2_open_' + FS2_VER + '-DEBUG',
        #         'debug': True
        #     }
        # ]
        info['mod']['packages'].append(pkg)

    with open(json_file, 'w') as stream:
        json.dump(repo, stream)


def main(args):
    parser = argparse.ArgumentParser(description='Updates the nightlies repo.')
    parser.add_argument('repo_cfg', help='The repository info.')

    args = parser.parse_args(args)

    fetch_nightlies(args.repo_cfg)


if __name__ == '__main__':
    codecs.register_error('strict', codecs.replace_errors)
    codecs.register_error('really_strict', codecs.strict_errors)
    main(sys.argv[1:])
