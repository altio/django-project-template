# -*- coding: utf-8 -*-

import sys

from .base import *  # NOQA

DEBUG = bool(os.environ.setdefault('DEBUG', str(False)) == 'True')

INTERNAL_IPS = ('127.0.0.1', )

ALLOWED_HOSTS = ['*']

#: Don't send emails, just print them on stdout
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

#: Run celery tasks synchronously
CELERY_ALWAYS_EAGER = True

#: Tell us when a synchronous celery task fails
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

SECRET_KEY = os.environ.get('SECRET_KEY', '{{ secret_key }}')

# Special test settings
if 'test' in sys.argv:
    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.SHA1PasswordHasher',
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )

    LOGGING['root']['handlers'] = []
