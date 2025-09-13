from datetime import datetime

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.orm import validates

from . import db
from .error_handlers import InvalidApi


class BaseNewsModel(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(BaseNewsModel):
    __tablename__ = 'users'
    username = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    translations = db.relationship('Translation', backref='user')

    def to_dict(self):
        return {
            'username': self.username,
            'email': self.email,
            'words_count': self.words_count
        }

    @property
    def words_count(self):
        return Translation.query.filter_by(user_id=self.id).count()

    @validates('username')
    def validate_username(self, key, username):
        if not username.isalnum() or " " in username:
            raise InvalidApi(
                'Username should be alphanumeric and contain no spaces'
            )
        return username

    @validates('email')
    def validate_email(self, key, email):
        try:
            validate_email(email)
        except EmailNotValidError:
            raise InvalidApi('Invalid email address')
        if User.query.filter(User.email == email, User.id != self.id).first():
            raise InvalidApi('Email is already in use')
        return email

    @validates('password')
    def validate_password(self, key, password):
        if len(password) < 8:
            raise InvalidApi('Password is too short')
        return password


class Translation(BaseNewsModel):
    __tablename__ = 'translations'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    translation = db.Column(db.Text, nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'translation': self.translation,
            'date': self.created_at.strftime('%d.%m.%Y %H:%M')
        }
