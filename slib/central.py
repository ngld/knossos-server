import codecs
from flask import Flask
import redis

# Default to replace errors when de/encoding.
codecs.register_error('strict', codecs.replace_errors)
codecs.register_error('really_strict', codecs.strict_errors)

app = Flask('server')
app.config.from_pyfile('./conf/settings.py')

r = redis.StrictRedis(connection_pool=redis.ConnectionPool.from_url(app.config['REDIS']))
