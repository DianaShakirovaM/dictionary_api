from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer

from settings import Config


app = Flask(__name__)
app.config.from_object(Config)

jwt = JWTManager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

from . import error_handlers, views, models
