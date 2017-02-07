#!/usr/bin/python

import sys
import os.path
import re
import json


WIN_RE = re.compile(r'(?:fs2|fred2)_open_.*\.exe')
LIN_RE = re.compile(r'fs2_open_.*')
MAC_RE = re.compile(r'.*/Contents/MacOS/.*')


def fix_mods(mods):
    for mod in mods:
        for pkg in mod['packages']:
            exes = []
            os = None

            for check in pkg['environment']:
                if check['type'] == 'os' and not check.get('not', False):
                    os = check['value']
                    break

            if os is None:
                continue

            for item in pkg['filelist']:
                if os == 'windows':
                    m = WIN_RE.match(item['filename'])
                elif os == 'linux':
                    m = LIN_RE.match(item['filename'])
                elif os == 'macos':
                    m = MAC_RE.match(item['filename'])
                
                if m:
                    exes.append({
                        'version': mod['version'],
                        'file': item['filename'],
                        'debug': 'debug' in item['filename'].lower() or 'FASTDBG' in item['filename']
                    })

            pkg['executables'] = exes


def main(args):
    if len(args) == 1:
        if not os.path.isfile(args[0]):
            print('Error: File "%s" was not found!' % args[0])
            sys.exit(1)

        with open(args[0], 'r') as stream:
            data = json.load(stream)

        fix_mods(data['mods'])

        with open(args[0], 'w') as stream:
            json.dump(data, stream)
    else:
        print('Usage: %s <json file>' % os.path.basename(__file__))

if __name__ == '__main__':
    main(sys.argv[1:])
