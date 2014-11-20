from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import redis


app = Flask('server')
app.config.from_pyfile('./conf/settings.py')

db = SQLAlchemy(app)
r = redis.StrictRedis(connection_pool=redis.ConnectionPool.from_url(app.config['REDIS']))
