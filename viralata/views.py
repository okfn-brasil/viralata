#!/usr/bin/env python
# coding: utf-8

import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from flask.ext.restplus import Resource, Api

from auths import get_auth_url, get_username
from models import User
from extensions import db, sv
from utils import decode_validate_token


# TODO: permitir configurar melhor
MICRO_TOKEN_VALID_PERIOD = 5
# one week
MAIN_TOKEN_VALID_PERIOD = 10080


api = Api(version='1.0',
          title='Vira-lata',
          description='An authentication microservice.')


@api.route('/login/<string:backend>/')
class LoginBackend(Resource):

    def get(self, backend):
        '''Asks the URL that should be used to login with a specific backend
        (like Facebook).'''
        print('AUTH-GET')
        return {'redirect': get_auth_url(backend)}


@api.route('/complete/<string:backend>/')
class CompleteLoginBackend(Resource):

    def post(self, backend):
        '''Completes the login with a specific backend.'''
        print('COMPLETE-GET')
        username = get_username(backend)
        return create_tokens(username)


@api.route('/login_local')
class LoginLocal(Resource):

    parser = api.parser()
    parser.add_argument('username', type=str,
                        location='json', help='Username!!')
    parser.add_argument('password', type=str,
                        location='json', help='Password!!')

    def post(self):
        '''Login using local BD, not backend.'''
        args = self.parser.parse_args()
        username = args['username']
        password = args['password']
        try:
            if User.verify_user_password(username, password):
                return create_tokens(username)
            else:
                api.abort(400, 'Wrong password...')
        except NoResultFound:
            api.abort(400, 'Username seems not registered...')


@api.route('/renew_micro_token')
class RenewMicroToken(Resource):

    parser = api.parser()
    parser.add_argument('token', type=str, location='json', help='Token!!!')

    def post(self):
        '''Get a new micro token to be used with the other microservices.'''
        args = self.parser.parse_args()
        decoded = decode_token(args['token'])
        if decoded['type'] != 'main':
            # This seems not to be a main token. It must be main for security
            # reasons, for only main ones can be invalidated at logout.
            # Allowing micro tokens would allow infinite renew by a
            # compromised token
            api.abort(400)

        token = create_token(decoded['username']),
        return {
            'microToken': token,
            'microTokenValidPeriod': MICRO_TOKEN_VALID_PERIOD,
        }


@api.route('/logout')
class Logout(Resource):

    parser = api.parser()
    parser.add_argument('token', type=str, location='json', help='Token!!!')

    def post(self):
        '''Invalidates the main token.'''
        args = self.parser.parse_args()
        decoded = decode_token(args['token'])
        # Invalidates all main tokens
        get_user(decoded['username']).last_token_exp = 0
        # TODO: será que não precisa commitar aqui?
        return {}


@api.route('/users/<string:username>')
class GetUser(Resource):

    parser = api.parser()
    parser.add_argument('token', type=str, location='json', help='Token!!!')

    def get(self, username):
        '''Get information about an user.'''
        args = self.parser.parse_args()
        try:
            user = User.get_user(username)
        except NoResultFound:
            api.abort(404)

        resp = {
            'username': user.username,
            'description': user.description,
        }

        # Add email if this is the owner of the account
        token = args['token']
        if token:
            decoded = decode_token(token)
            if decoded['username'] == username:
                resp['email'] = user.email
        return resp


@api.route('/users')
class ListUsers(Resource):

    def get(self):
        '''List users.'''
        users = db.session.query(User.username).all()

        return {
            'users': [u[0] for u in users]
        }


@api.route('/users/<string:username>/edit')
class EditUser(Resource):

    parser = api.parser()
    parser.add_argument('token', type=str, location='json', help='Token!!!')
    parser.add_argument('description', type=str,
                        location='json', help='Descr!!!')
    # parser.add_argument('password', type=str,
    #                     location='json', help='Password!!')
    parser.add_argument('email', type=str,
                        location='json', help='Email!!')

    def put(self, username):
        '''Edit information about an user.'''
        args = self.parser.parse_args()
        decoded = decode_token(args['token'])
        if username == decoded['username']:
            user = get_user(decoded['username'])
            if args['description']:
                user.description = args['description']
            if args['email']:
                user.email = args['email']
            db.session.commit()
            return {
                'username': user.username,
                'description': user.description,
                'email': user.email,
            }

        else:
            api.abort(550, 'Editing other user profile...')


@api.route('/users/<string:username>/register')
class RegisterUser(Resource):

    parser = api.parser()
    parser.add_argument('password')
    parser.add_argument('email', type=str,
                        location='json', help='Email!!')

    def post(self, username):
        '''Register a new user.'''
        args = self.parser.parse_args()

        # TODO: validar username
        # TODO: case insensitive? ver isso na hora de login tb
        # username = username.lower()
        if not re.match(r'[a-z0-9]{5,}', username):
            api.abort(400, 'Invalid characters in username...')

        password = args['password']
        # Validate password
        if len(password) < 5:
            api.abort(400, 'Invalid password. Needs at least 5 characters.')
        if not re.match(r'[A-Za-z0-9@#$%^&+=]{5,}', password):
            api.abort(400, 'Invalid characters in password...')

        email = args.get('email')
        # # Validate email
        # if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        #     api.abort(400, 'Invalid email.')

        user = User(username=username, email=email)
        user.hash_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            api.abort(400, 'It seems this username is already registered...')
        return create_tokens(username)


# def create_token(username, exp_minutes=5):
#     '''Returns a token.'''
#     return sv.encode({
#         'username': username,
#     }, exp_minutes)


def create_tokens(username):
    '''Returns new main and micro tokens for the user.'''
    main_token = create_token(username, True)
    user = get_user(username)
    # TODO: Talvez usar algo mais rápido para decodificar o token,
    # como ignorar verificações?
    user.last_token_exp = sv.decode(main_token)['exp']
    db.session.commit()
    return {
        'mainToken': main_token,
        'microToken': create_token(username),
        'microTokenValidPeriod': MICRO_TOKEN_VALID_PERIOD,
    }


def create_token(username, main=False):
    '''Returns a token.'''

    if main:
        exp_minutes = MAIN_TOKEN_VALID_PERIOD
        token_type = 'main'
    else:
        exp_minutes = MICRO_TOKEN_VALID_PERIOD
        token_type = 'micro'

    return sv.encode({
        'username': username,
        'type': token_type,
    }, exp_minutes)


def decode_token(token):
    decoded = decode_validate_token(token, sv, api)

    # Verify if main token is not invalid
    if decoded['type'] == 'main':
        user = get_user(decoded['username'])
        if decoded['exp'] != user.last_token_exp:
            api.abort(400, 'Error: Invalid main token!')

    return decoded


def get_user(username):
    try:
        return User.get_user(username)
    except NoResultFound:
        api.abort(404, 'Error: User not found!')
