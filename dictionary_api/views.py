from datetime import timedelta
from http import HTTPStatus

import requests
from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from passlib.hash import bcrypt
from requests.exceptions import RequestException

from . import app, db, serializer
from .error_handlers import InvalidApi
from .models import Translation, User
from .utils import generate_download_file, send_reset_email

ACCESS_TOKEN_LIFESPAN_IN_HOURS = 24
REFRESH_TOKEN_LIFESPAND_IN_HOURS = ACCESS_TOKEN_LIFESPAN_IN_HOURS * 7
TRANSLATE_URL = 'https://api.mymemory.translated.net/get'
RESET_TOKEN_LIFESPAN_IN_MINUTES = 3600


def validate_required_fields(data, fields):
    if data is None:
        raise InvalidApi('Invalid JSON data')

    for field in fields:
        if field not in data:
            raise InvalidApi(f'Field {field} is required')


@app.post('/api/auth/register')
def register():
    data = request.get_json()
    validate_required_fields(data, ['username', 'password', 'email'])
    username = data['username']
    password = data['password']
    email = data['email']
    password = bcrypt.hash(password)
    user = User(username=username, password=password, email=email)
    db.session.add(user)
    db.session.commit()
    return jsonify({'user': user.to_dict()}), 201


@app.post('/api/auth/login')
def login():
    data = request.get_json()
    validate_required_fields(data, ['password', 'email'])
    email = data['email']
    password = data['password']
    user = User.query.filter_by(email=email).first()

    if not user or not bcrypt.verify(password, user.password):
        raise InvalidApi('Invalid email or password')

    access_token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(hours=ACCESS_TOKEN_LIFESPAN_IN_HOURS))

    refresh_token = create_refresh_token(
        identity=str(user.id),
        expires_delta=timedelta(hours=REFRESH_TOKEN_LIFESPAND_IN_HOURS))

    return jsonify(
        {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': ACCESS_TOKEN_LIFESPAN_IN_HOURS
        }), 200


@app.post('/api/auth/forgot-password')
def forgot_password():
    data = request.get_json()
    validate_required_fields(data, ['email'])
    email = data['email']
    user = User.query.filter_by(email=email).first()
    if not user:
        raise InvalidApi('Invalid email')
    reset_token = serializer.dumps(
        user.email,
        salt=app.config['SECURITY_PASSWORD_SALT']
    )
    send_reset_email(user.email, reset_token)
    return '', 200


@app.post('/api/auth/reset-password')
def reset_password():
    data = request.get_json()
    validate_required_fields(data, ['token', 'new_password'])
    token = data['token']
    new_password = data['new_password']
    email = serializer.loads(
        token,
        salt=app.config['SECURITY_PASSWORD_SALT'],
        max_age=RESET_TOKEN_LIFESPAN_IN_MINUTES
    )
    if not email:
        raise InvalidApi('Invalid reset token')
    user = User.query.filter_by(email=email).first()
    if not user:
        raise InvalidApi('Invalid email')
    user.password = bcrypt.hash(new_password)
    db.session.commit()
    return jsonify({'message': 'Password was successfully changed'}), 200


@app.post('/api/token/refresh')
@jwt_required(refresh=True)
def refresh_token():
    return jsonify({'access_token': create_access_token(
        identity=get_jwt_identity(),
        expires_delta=timedelta(hours=ACCESS_TOKEN_LIFESPAN_IN_HOURS)
    )}), 200


@app.get('/api/auth/me')
@jwt_required()
def me():
    user = User.query.filter_by(id=get_jwt_identity()).first()
    return jsonify({'user': user.to_dict()}), 200


@app.post('/api/translate')
def get_translation():
    user_data = request.get_json()
    validate_required_fields(user_data, ['text', 'langpair'])
    text = user_data['text']
    langpair = user_data['langpair']

    try:
        response = requests.get(
                TRANSLATE_URL,
                params={
                    'q': text,
                    'langpair': langpair
                },
        )
    except RequestException:
        raise InvalidApi('Network error connecting to translation service')

    status_code = response.status_code
    data = response.json()
    if status_code != HTTPStatus.OK:
        raise InvalidApi('Translation service unavailable')
    if 'responseData' not in data:
        raise InvalidApi('Invalid response format from translation service')
    if 'translatedText' not in data['responseData']:
        raise InvalidApi('Translation not found in response')
    return jsonify(
        {'translation': data['responseData']['translatedText']}), 200


class DictionaryApi(MethodView):
    decorators = [jwt_required()]

    def _get_user_id(self):
        return get_jwt_identity()

    def post(self):
        data = request.get_json()
        validate_required_fields(data, ['text', 'translation'])
        translation = Translation(user_id=self._get_user_id(), **data)
        db.session.add(translation)
        db.session.commit()
        return jsonify(translation.to_dict()), 201

    def get(self):
        data = []
        search_query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 100)  # set the element limit
        translations = Translation.query.filter(
            Translation.text.ilike(f'%{search_query}%'),
            Translation.user_id == self._get_user_id()
        ).order_by(
            Translation.created_at.desc()
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        for translation in translations:
            data.append(translation.to_dict())
        return jsonify({
            'pagination': {
                'page': page,
                'per_page': per_page,
                'next_num': translations.next_num,
                'prev_num': translations.prev_num
            },
            'dictionary': data}), 200


class TranslationApi(MethodView):
    decorators = [jwt_required()]

    def _get_translation(self, id):
        """Вспомогательный метод для получения перевода"""
        user_id = get_jwt_identity()
        return Translation.query.filter_by(
            user_id=user_id,
            id=id
        ).first_or_404()

    def get(self, id):
        dictionary_item = self._get_translation(id)
        return jsonify(dictionary_item.to_dict()), 200

    def patch(self, id):
        dictionary_item = self._get_translation(id)
        data = request.get_json()
        dictionary_item.text = data.get('text', dictionary_item.text)
        dictionary_item.translation = data.get(
            'translation', dictionary_item.translation
        )
        db.session.commit()
        return jsonify(dictionary_item.to_dict()), 200

    def delete(self, id):
        dictionary_item = self._get_translation(id)
        db.session.delete(dictionary_item)
        db.session.commit()
        return '', 204


@app.get('/api/dictionary-download')
@jwt_required()
def download_dictionary():
    user_id = get_jwt_identity()
    dictionary = Translation.query.filter_by(
        user_id=user_id
    ).order_by(Translation.created_at.desc()).all()
    user = User.query.get(user_id)
    response = generate_download_file(dictionary, user)
    return response


app.add_url_rule(
    '/api/dictionary',
    view_func=DictionaryApi.as_view('dictionary')
)

app.add_url_rule(
    '/api/dictionary/<int:id>',
    view_func=TranslationApi.as_view('translation')
)
