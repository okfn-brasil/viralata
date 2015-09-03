#!/usr/bin/env python
# coding: utf-8

import re

import bleach
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from flask import redirect, url_for, make_response
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

arguments = {
    'token': {
        'location': 'json',
        'help': 'The authentication token.',
    },
    'username': {
        'location': 'json',
        'help': 'The username.',
    },
    'password': {
        'location': 'json',
        'help': 'The password.',
    },
    'email': {
        'location': 'json',
        'help': 'The email.',
    },
    'description': {
        'location': 'json',
        'help': 'The user description.',
    },
}


def create_parser(*args):
    '''Create a parser for the passed arguments.'''
    parser = api.parser()
    for arg in args:
        parser.add_argument(arg, **arguments[arg])
    return parser


general_parser = create_parser(*arguments)


@api.route('/login/external/manual/<string:backend>')
class LoginExtManAPI(Resource):

    def get(self, backend):
        '''Asks the URL that should be used to login with a specific backend
        (like Facebook).'''
        print('AUTH-GET')
        return {'redirect': get_auth_url(backend, 'loginextmanapi')}


@api.route('/complete/manual/<string:backend>')
class CompleteLoginExtManAPI(Resource):

    def post(self, backend):
        '''Completes the login with a specific backend.'''
        print('COMPLETE-GET')
        username = get_username(backend, redirect_uri='/')
        return create_tokens(username)


# @api.route('/login/external/automatic/<string:backend>')
# class StartLoginExtAutoAPI(Resource):

#     def get(self, backend):
#         '''Asks the URL that should be used to login with a specific backend
#         (like Facebook).'''
#         print('AUTH-GET')
#         print(get_auth_url(backend, 'completeloginautoapi'))
#         return {'redirect': get_auth_url(backend, 'completeloginautoapi')}
#         # return redirect(get_auth_url(backend, 'completeloginautoapi'))

# @api.route('/complete/automatic/<string:backend>')
# class CompleteLoginAutoAPI(Resource):

#     def get(self, backend):
#         '''Completes the login with a specific backend.'''
#         print('COMPLETE-GET')
#         username = get_username(backend,
#                                 url_for('completeloginautoapi',
#                                         backend='facebook'))
#         tokens = create_tokens(username)
#         response = redirect("http://localhost:5001/")
#         # import IPython; IPython.embed()
#         return response
#         # return create_tokens(username)


@api.route('/login/local')
class LoginLocalAPI(Resource):

    @api.doc(parser=create_parser('username', 'password'))
    def post(self):
        '''Login using local DB, not a third-party service.'''
        args = general_parser.parse_args()
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

    @api.doc(parser=create_parser('token'))
    def post(self):
        '''Get a new micro token to be used with the other microservices.'''
        args = general_parser.parse_args()
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

    @api.doc(parser=create_parser('token'))
    def post(self):
        '''Invalidates the main token.'''
        args = general_parser.parse_args()
        decoded = decode_token(args['token'])
        # Invalidates all main tokens
        get_user(decoded['username']).last_token_exp = 0
        # TODO: será que não precisa commitar aqui?
        return {}


@api.route('/user/<string:username>')
class UserAPI(Resource):

    @api.doc(parser=create_parser('token'))
    def get(self, username):
        '''Get information about an user.'''
        args = general_parser.parse_args()
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

    @api.doc(parser=create_parser('token', 'description', 'email'))
    def put(self, username):
        '''Edit information about an user.'''
        args = general_parser.parse_args()
        decoded = decode_token(args['token'])
        if username == decoded['username']:
            user = get_user(decoded['username'])
            if args['description']:
                user.description = bleach.clean(args['description'],
                                                strip=True)
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

    @api.doc(parser=create_parser('password', 'email'))
    def post(self, username):
        '''Register a new user.'''
        args = general_parser.parse_args()

        # TODO: case insensitive? ver isso na hora de login tb
        # username = username.lower()
        if len(username) < 5:
            api.abort(400, 'Invalid username. Needs at least 5 characters.')
        if not re.match(r'[A-Za-z0-9]{5,}', username):
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


@api.route('/users')
class ListUsers(Resource):

    def get(self):
        '''List registered users.'''
        users = db.session.query(User.username).all()

        return {
            'users': [u[0] for u in users]
        }


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
    '''Returns a token for the passed username.
    "main" controls the type of the token.'''

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
