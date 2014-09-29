from flask import Flask
from flask.ext.uwsgi_websocket import WebSocket
from flask.ext.sqlalchemy import SQLAlchemy
from config import app_config


app = Flask('server')
app_config(app)

ws = WebSocket(app)
db = SQLAlchemy(app)
