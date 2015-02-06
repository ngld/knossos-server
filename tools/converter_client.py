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
import time
import requests

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s@%(module)s] %(funcName)s %(levelname)s: %(message)s')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'knossos'))


def convert(src, dest, server, api_key):
    if not os.path.isfile(src):
        logging.error('I can\'t read "%s"!', src)
        return False

    with open(src, 'r') as stream:
        info = json.load(stream)

    sess = requests.Session()

    data = {'data': json.dumps(info, separators=(',', ':')), 'passwd': api_key}
    try:
        res = sess.post(server + '/api/converter/request', data=data)
    except requests.ConnectionError:
        logging.exception('Failed to submit request!')
        return False

    if res.status_code == 403:
        logging.error('You used an invalid API key!')
        return False

    if res.status_code != 200:
        logging.error('Failed to submit request!')
        return False

    ticket = res.json()
    if ticket.get('error', False):
        logging.error('You submitted invalid JSON data!')
        return False

    logging.info('Request sent. Waiting for results...')
    while True:
        time.sleep(5)
        try:
            status = sess.get(server + ('/api/converter/get_status/%d' % ticket['ticket']))
        except requests.ConnectionError:
            logging.exception('Unable to determine status. I\'ll just wait a bit longer...')
            continue

        if status.status_code != 200:
            logging.warning('Received an invalid reply! Are you sure this going as planned?')
            return False

        try:
            status = status.json()
            if status['state'] == 'DONE':
                break
        except ValueError:
            logging.exception('Unable to determine status. I\'ll just wait a bit longer...')
            continue

    try:
        results = sess.post(server + '/api/converter/retrieve', data=ticket)
    except requests.ConnectionError:
        logging.exception('Failed to retrieve the results!')
        return False

    results = results.json()
    if not results['finished']:
        logging.error('Server is unpredeictable! What\'s going on?!')
        return False

    if not results.get('found', True):
        logging.error('The task vanished!')
        return False

    if not results['success']:
        logging.error('The conversion failed!')
        return False

    with open(dest, 'w') as stream:
        stream.write(results['json'])


def main(args):
    parser = argparse.ArgumentParser(description='Converts mod JSON information.')
    parser.add_argument('-s', dest='server', default='https://s1-nebula.tproxy.de', help='The converter server to use')
    parser.add_argument('api_key', help='Your API Key')
    parser.add_argument('source', help='input file')
    parser.add_argument('dest', help='output file')

    args = parser.parse_args(args)

    convert(args.source, args.dest, args.server, args.api_key)


if __name__ == '__main__':
    codecs.register_error('strict', codecs.replace_errors)
    codecs.register_error('really_strict', codecs.strict_errors)
    main(sys.argv[1:])
