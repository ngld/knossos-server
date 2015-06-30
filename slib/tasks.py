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

import os
import json
import time
import logging
import tempfile
import re
from urllib.parse import urlencode
from urllib.request import urlopen
from threading import Lock

from .central import r, app
from .output import TaskLogHandler, MessagesFormatter

os.environ['QT_API'] = 'headless'
from knossos import progress, util
import converter
import converter.download


class Task(object):
    _id = None
    _str_id = None
    _args = None
    _status = None
    _p = None
    _p_thread = None
    _listeners = None

    def __init__(self, *args, id_=None):
        self._type = self.__class__.__name__
        self._args = args
        self._listeners = {}

        if id_ is not None:
            self._id = id_
            self._str_id = str(self._id)

            if not r.hexists('task_status', self._str_id):
                raise Exception('Invalid task id specified!')

    def run(self):
        raise NotImplemented

    # Internal API
    
    def _run_task(self):
        self._setup()
        try:
            self.run()
        except KeyboardInterrupt:
            raise
        except:
            logging.exception('Task "%s" failed!', self._type)
        finally:
            self._teardown()

    def _setup(self):
        self._p = r.pubsub()
        self._p.subscribe(**{'task_' + self._str_id + '_input': self._handle_message, 'ignore_subscribe_messages': True})
        self._p_thread = self._p.run_in_thread(sleep_time=0.3)

        self._h = TaskLogHandler(self, logging.INFO)
        self._h.setFormatter(MessagesFormatter('%(levelname)s: %(message)s'))
        logging.getLogger().addHandler(self._h)

        r.hset('task_status', self._str_id, json.dumps({'state': 'WORKING', 'time': time.time()}))

    def _teardown(self):
        self._p_thread.stop()
        self._p.unsubscribe('task_' + self._str_id + '_input')

        status = self.get_status(True)
        now = time.time()
        r.hset('task_status', self._str_id, json.dumps({'state': 'DONE', 'time': now, 'runtime': now - status['time']}))

        logging.getLogger().removeHandler(self._h)

    def _handle_message(self, msg):
        if msg['type'] == 'message':
            try:
                data = json.loads(msg['data'].decode('utf8'))
            except ValueError:
                logging.exception('Received invalid JSON data from Redis!')
                return

            if data[0] in self._listeners:
                for l in self._listeners[data[0]]:
                    l(*data[1])

    def on(self, name, cb):
        if name not in self._listeners:
            self._listeners[name] = [cb]
        else:
            self._listeners[name].append(cb)

    def off(self, name, cb):
        self._listeners[name].remove(cb)
        if len(self._listeners[name]) == 0:
            del self._listeners[name]

    def once(self, name, cb):
        wrapper = None

        def wrapper(*data):
            self.off(name, wrapper)
            cb(*data)

        self.on(name, wrapper)

    def consume(self, name, timeout=3600):
        r = None

        def wrapper(*data):
            nonlocal r
            r = data

        self.on(name, wrapper)
        start = time.time()
        while r is None and (time.time() - start) < timeout:
            time.sleep(0.2)

        self.off(name, wrapper)
        return r

    def emit(self, name, *args, log=True):
        data = json.dumps((name, args))
        r.publish('task_' + self._str_id, data)

        if log:
            # Store all log messages.
            r.rpush('task_' + self._str_id + '_log', data)
        else:
            r.hset('task_' + self._str_id + '_vlog', name, data)

    def wait_for_user(self, timeout=30):
        self.consume('user_ready', timeout)

    def save_result(self, data):
        r.hset('task_result', self._str_id, json.dumps(data))

    # External API

    def run_async(self):
        self._id = r.incr('task_id')
        self._str_id = str(self._id)

        r.hset('task_status', self._str_id, json.dumps({'state': 'WAITING', 'time': time.time()}))
        r.rpush('task_queue', json.dumps((self._id, self._type, self._args)))

        return self._id

    def get_status(self, update=False):
        if self._status is None or update:
            data = r.hget('task_status', self._str_id)
            if data is not None:
                self._status = json.loads(data.decode('utf8'))

        return self._status

    def has_result(self):
        return r.hexists('task_result', self._str_id)

    def get_result(self, block=True):
        if block:
            while not self.has_result():
                time.sleep(0.3)
        elif not self.has_result():
            return None

        return json.loads(r.hget('task_result', self._str_id).decode('utf8'))

    def remove(self):
        r.hdel('task_status', self._str_id)
        r.hdel('task_result', self._str_id)
        r.delete('task_' + self._str_id + '_log')
        r.delete('task_' + self._str_id + '_vlog')


class Worker(object):
    _running = True
    _tasks = None

    def __init__(self):
        self._tasks = {}

    def register_task(self, cls):
        self._tasks[cls.__name__] = cls

    def run(self):
        import signal

        signal.signal(signal.SIGINT, self.sig_quit)

        self._running = True
        logging.info('Registered tasks: %s', ', '.join(self._tasks.keys()))
        logging.info('Ready and waiting for tasks.')

        while self._running:
            task = r.blpop('task_queue', timeout=5)
            if not task:
                continue

            try:
                task = json.loads(task[1].decode('utf8', 'replace'))
            except ValueError:
                logging.exception('Invalid JSON in task queue!')
                continue

            if task[1] not in self._tasks:
                logging.error('Unknown task type "%s"!', task[1])
                continue

            logging.info('Running task #%d of type %s...', task[0], task[1])

            task = self._tasks[task[1]](*task[2], id_=task[0])
            task._run_task()

            logging.info('Task finished!')

        logging.info('Quitting...')

    def sig_quit(self, a, b):
        logging.info('I will shut down once the running task is finished!')
        self.quit()

    def quit(self):
        self._running = False


class CleanupTask(Task):

    def run(self):
        living_tasks = []
        now = time.time()

        # Check for expired / stuck tasks.
        for task in r.hkeys('task_status'):
            task = task.decode('utf8')
            try:
                info = json.loads(r.hget('task_status', task).decode('utf8'))

                if 'time' not in info:
                    logging.warning('Task #%s doesn\'t have a "time" field! Deleting it...', task)
                    r.hdel('task_status', task)
                elif info['state'] == 'DONE':
                    if now - info['time'] > app.config['RESULT_LIFETIME']:
                        logging.debug('Expiring task %s.', task)
                        r.hdel('task_status', task)
                    else:
                        living_tasks.append(task)
                elif now - info['time'] > app.config['TASK_LIFETIME']:
                    logging.debug('Expiring task %s.', task)
                    r.hdel('task_status', task)
                else:
                    living_tasks.append(task)
            except:
                # Make sure we only skip the failed task and we don't want to delete it's data because it might still be running.
                logging.exception('Failed to check task #' + task + ' !')
                living_tasks.append(task)

        # Check for orphans.
        for task in r.hkeys('task_result'):
            task = task.decode('utf8')
            if task not in living_tasks:
                logging.debug('Removing orphaned task result %s.', task)
                r.hdel('task_result', task)

        # Check for stale logs.
        for name in r.keys('task_*_log'):
            task = name.decode('utf8').split('_')[1]
            if task not in living_tasks:
                logging.debug('Removing stale log for task %s.', task)
                r.delete('task_' + task + '_log')

        for name in r.keys('task_*_vlog'):
            task = name.decode('utf8').split('_')[1]
            if task not in living_tasks:
                logging.debug('Removing stale vlog for task %s.', task)
                r.delete('task_' + task + '_vlog')


class ConverterTask(Task):
    lu = 0
    _captcha_lock = None

    def p_update(self, prog, text):
        # Throttle updates
        now = time.time()

        if now - self.lu > 0.3:
            self.emit('progress', prog, text, log=False)
            self.lu = now

    def p_wrap(self, cb):
        progress.set_callback(self.p_update)
        cb()

    def ask_user(self, img_url):
        with self._captcha_lock:
            _result = None

            def cb(code):
                nonlocal _result
                _result = code

            self.once('captcha_response', cb)
            self.emit('captcha', img_url, log=False)

            while _result is None:
                time.sleep(0.3)

        logging.debug('Received captcha response: %s', _result)
        return _result

    def run(self):
        dl_path = None
        dl_link = None
        self._captcha_lock = Lock()
        converter.download.ASK_USER = self.ask_user

        try:
            with tempfile.TemporaryDirectory() as tdir:
                repo = os.path.join(tdir, 'repo.json')
                output = os.path.join(tdir, 'out.json')

                if app.config['MIRROR_PATH'] is not None:
                    info = self._args[0]
                    try:
                        if 'mods' not in info and 'title' in info and 'id' in info:
                            mods = [info]
                        else:
                            mods = info['mods']

                        if len(mods) == 1:
                            dl_path = os.path.join(os.path.basename(mods[0]['id']), os.path.basename(mods[0]['version']))
                        else:
                            dl_path = 'general'

                        dl_link = util.pjoin(app.config['MIRROR_URL'], dl_path)
                        dl_path = os.path.join(app.config['MIRROR_PATH'], dl_path)

                        if not os.path.isdir(dl_path):
                            os.makedirs(dl_path)
                    except KeyError:
                        # We're missing some keys here, this will be logged later, too.
                        dl_path = None

                try:
                    with open(repo, 'w') as stream:
                        stream.write(json.dumps(self._args[0]))

                    result = converter.generate_checksums(repo, output, self.p_wrap, dl_path, dl_link, list_files=True)

                    # Clear the cache to prevent a memory leak.
                    util.HASH_CACHE = {}

                    if result and os.path.isfile(output):
                        with open(output, 'r') as stream:
                            self.save_result({
                                'json': stream.read(),
                                'success': True,
                                'token': self._args[2]
                            })
                except ValueError as exc:
                    logging.exception('Failed to parse JSON data: %s', str(exc))
                    result = False
                except KeyboardInterrupt:
                    raise
                except:
                    logging.exception('Failed to perform conversion!')
                    result = False

                if not result:
                    self.save_result({
                        'json': None,
                        'success': False,
                        'token': self._args[2]
                    })
                
                if self._args[1] is not None:
                    if re.match(r'^https?://(localhost|127\..*)', self._args[1]):
                        logging.warning('Ignored the webhook because it points to localhost.')
                    else:
                        try:
                            hdl = urlopen(self._args[1], data=urlencode({'ticket': self._str_id}).encode('utf8'))
                            response = hdl.read().decode('utf8', 'replace').strip()
                            hdl.close()

                            if len(response) > 0 and '{' in response:
                                response = json.loads(response)
                                if isinstance(response, dict) and response.get('cancelled', False):
                                    # TODO: Is this still necessary?
                                    self.remove()
                        except:
                            logging.exception('Webhook failed!')

                self.emit('done', result)
        finally:
            converter.download.ASK_USER = None
