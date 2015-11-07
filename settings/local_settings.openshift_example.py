import os

DEBUG = False
DEBUG_TB_INTERCEPT_REDIRECTS = False

SQLALCHEMY_DATABASE_URI = (
    'postgresql://{user}:{password}@{host}:{port}/viralata'
    .format(
        user=os.environ['OPENSHIFT_POSTGRESQL_DB_USERNAME'],
        password=os.environ['OPENSHIFT_POSTGRESQL_DB_PASSWORD'],
        host=os.environ['OPENSHIFT_POSTGRESQL_DB_HOST'],
        port=os.environ['OPENSHIFT_POSTGRESQL_DB_PORT']))

SOCIAL_AUTH_FACEBOOK_KEY = '{your_facebook_dev_key}'
SOCIAL_AUTH_FACEBOOK_SECRET = '{your_facebook_dev_secret}'
# This is required for PSA for sessions, even though we are not using them...
SECRET_KEY = '{long_string...}'

PRIVATE_KEY_PASSWORD = '{your_key_password}'


# ----------------------------- #
# Forgot password functionality #
# ----------------------------- #

__username__ = '{email_username}@gmail.com'

# These are used to send e-mails to the admin when a comment is reported.
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = __username__
MAIL_PASSWORD = '{email_password}'
SENDER_NAME = __username__
