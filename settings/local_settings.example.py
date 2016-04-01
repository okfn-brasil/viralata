DEBUG = True
DEBUG_TB_INTERCEPT_REDIRECTS = False

SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@localhost/{database}'
SOCIAL_AUTH_FACEBOOK_KEY = '{your_facebook_dev_key}'
SOCIAL_AUTH_FACEBOOK_SECRET = '{your_facebook_dev_secret}'
# This is required for PSA for sessions, even though we are not using them...
SECRET_KEY = '{long_string...}'

# Password to unlock key. Use None if no password is needed.
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
