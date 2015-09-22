#!/usr/bin/env python
# coding: utf-8

import re
import json

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
    'new_password': {
        'location': 'json',
        'help': 'A new password, when changing the current one.',
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
                abort_with_msg(400, 'Wrong password...', ['password'])
        except NoResultFound:
            abort_with_msg(400,
                           'Username seems not registered...',
                           ['username'])


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
            abort_with_msg(400, 'Must use a main token', ['token'])

        token = create_token(decoded['username']),
        return {
            'microToken': token,
            'microTokenValidPeriod': MICRO_TOKEN_VALID_PERIOD,
        }


# @api.route('/reset_password')
# class ResetPassword(Resource):

#     @api.doc(parser=create_parser('username', 'email'))
#     def post(self):
#         '''.'''
#         args = general_parser.parse_args()
#         user = get_user(args['username'])
#         if user.email != args['email']:
#             abort_with_msg(400, 'Email mismatch.', ['email'])

#         token = api.urltoken.dumps((user.name, user.email))
#         suburl = api.url_for(DeleteReportedAPI, token=token)
#         delete_link = api.app.config['HOSTED_ADDRESS'] + suburl
#         msg = Message(
#             'Request to delete comment: %s' % comment.id,
#             sender=api.app.config['SENDER_NAME'],
#             recipients=api.app.config['ADMIN_EMAILS'])
#         msg.body = api.app.config['EMAIL_TEMPLATE'].format(
#             delete_link=delete_link,
#             id=comment.id,
#             author=comment.author.name,
#             thread=comment.thread.name,
#             created=comment.created,
#             modified=comment.modified,
#             text=comment.text,
#         )
#         api.mail.send(msg)
#         return {'message': 'Check email!'}


@api.route('/logout')
class Logout(Resource):

    @api.doc(parser=create_parser('token'))
    def post(self):
        '''Invalidates the main token.'''
        args = general_parser.parse_args()
        decoded = decode_token(args['token'])
        # Invalidates all main tokens
        get_user(decoded['username']).last_token_exp = 0
        db.session.commit()
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
            abort_with_msg(404, 'User not found', ['username'])

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

    @api.doc(parser=create_parser('token', 'description',
                                  'email', 'password'))
    def put(self, username):
        '''Edit information about an user.'''
        args = general_parser.parse_args()
        decoded = decode_token(args['token'])
        if username == decoded['username']:
            user = get_user(decoded['username'])
            changed = False

            print(args)
            password = args.get('password')
            # If is changing password
            if password:
                new_password = args['new_password']
                if user.verify_password(password):
                    validate_password(new_password, 'new_password')
                    user.hash_password(new_password)
                    changed = True
                else:
                    abort_with_msg(400, 'Wrong password...', ['password'])

            # If is changing description
            if args['description']:
                user.description = bleach.clean(args['description'],
                                                strip=True)
                changed = True

            email = args.get('email')
            # If is changing email
            if email:
                validate_email(email)
                user.email = email
                changed = True

            # If some data seems to have changed, commit
            if changed:
                db.session.commit()

            return {
                'username': user.username,
                'description': user.description,
                'email': user.email,
            }

        else:
            abort_with_msg(550, 'Editing other user profile...',
                           ['username', 'token'])

    @api.doc(parser=create_parser('password', 'email'))
    def post(self, username):
        '''Register a new user.'''
        args = general_parser.parse_args()

        # TODO: case insensitive? ver isso na hora de login tb
        # username = username.lower()
        if len(username) < 5:
            abort_with_msg(400,
                           'Invalid username. Needs at least 5 characters.',
                           ['username'])
        if not re.match(r'[A-Za-z0-9]{5,}', username):
            abort_with_msg(400, 'Invalid characters in username...',
                           ['username'])

        password = args['password']
        validate_password(password)

        email = args.get('email')
        validate_email(email)

        user = User(username=username, email=email)
        user.hash_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            abort_with_msg(400,
                           'It seems this username is already registered...',
                           ['username'])
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
            abort_with_msg(400, 'Invalid main token!', ['token'])

    return decoded


def get_user(username):
    try:
        return User.get_user(username)
    except NoResultFound:
        abort_with_msg(404, 'User not found', ['username'])


def validate_password(password, fieldname='password'):
    '''Check if is a valid password. The fieldname parameter is used to
    specify the fieldname in the error message.'''
    if len(password) < 5:
        abort_with_msg(400,
                       'Invalid password. Needs at least 5 characters.',
                       [fieldname])
    if not re.match(r'[A-Za-z0-9@#$%^&+=]{5,}', password):
        abort_with_msg(400,
                       'Invalid characters in password...',
                       [fieldname])


def validate_email(email):
    '''Check if is a valid email.'''
    if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        abort_with_msg(400,
                       'Invalid email...',
                       ['email'])


def abort_with_msg(error_code, msg, fields):
    '''Aborts sending information about the error.'''
    api.abort(error_code, json.dumps({
        'message': msg,
        'fields': fields
    }))
