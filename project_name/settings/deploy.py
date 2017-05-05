# Settings for live deployed environments: vagrant, staging, production, etc
from .base import *  # noqa

os.environ.setdefault('CACHE_HOST', '127.0.0.1:11211')
os.environ.setdefault('BROKER_HOST', '127.0.0.1:5672')

SECRET_KEY = os.environ['SECRET_KEY']

DEBUG = False

WEBSERVER_ROOT = '/var/www/{{ project_name }}/'

PUBLIC_ROOT = os.path.join(WEBSERVER_ROOT, 'public')

STATIC_ROOT = os.path.join(PUBLIC_ROOT, 'static')

MEDIA_ROOT = os.path.join(PUBLIC_ROOT, 'media')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '%(CACHE_HOST)s' % os.environ,
    }
}

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', os.environ.get('SENDGRID_USERNAME', ''))
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', os.environ.get('SENDGRID_PASSWORD', ''))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', False)
# use TLS or SSL, not both:
assert not (EMAIL_USE_TLS and EMAIL_USE_SSL)
if EMAIL_USE_TLS:
    default_smtp_port = 587
elif EMAIL_USE_SSL:
    default_smtp_port = 465
else:
    default_smtp_port = 25
EMAIL_PORT = os.environ.get('EMAIL_PORT', default_smtp_port)
EMAIL_SUBJECT_PREFIX = '[{{ project_name|title }} %s] ' % ENVIRONMENT.title()

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '[::1]',
    '{}'.format(SITE_FQDN),
]

DOMAIN = os.environ.setdefault('DOMAIN', None)
if DOMAIN:
    ALLOWED_HOSTS.append('.{}'.format(DOMAIN))

# Redirect to HTTPS in production via ELB/proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = bool(os.environ.setdefault('SECURE_REDIRECT', str(True)) == 'True')

# Use template caching on deployed servers
for backend in TEMPLATES:
    if backend['BACKEND'].endswith('DjangoTemplates'):
        default_loaders = ['foundation.template.loaders.filesystem.Loader']
        if backend.get('APP_DIRS', False):
            default_loaders.append('foundation.template.loaders.app_directories.Loader')
            # Django gets annoyed if you both set APP_DIRS True and specify your own loaders
            backend['APP_DIRS'] = False
        loaders = backend['OPTIONS'].get('loaders', default_loaders)
        for loader in loaders:
            if len(loader) == 2 and loader[0] == 'django.template.loaders.cached.Loader':
                # We're already caching our templates
                break
        else:
            backend['OPTIONS']['loaders'] = [('django.template.loaders.cached.Loader', loaders)]

# Uncomment if using celery worker configuration
# CELERY_SEND_TASK_ERROR_EMAILS = True
# BROKER_URL = 'amqp://{{ project_name }}_%(ENVIRONMENT)s:%(BROKER_PASSWORD)s@%(BROKER_HOST)s/{{ project_name }}_%(ENVIRONMENT)s' % os.environ  # noqa

DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'

# Environment overrides
# These should be kept to an absolute minimum
if ENVIRONMENT == 'local':
    # Don't send emails from the Vagrant boxes
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    if os.environ.get('RDS_HOSTNAME'):
        DATABASES['default']['HOST'] = os.environ['RDS_HOSTNAME']
        DATABASES['default']['PORT'] = os.environ['RDS_PORT']
        DATABASES['default']['NAME'] = os.environ['RDS_DB_NAME']
        DATABASES['default']['USER'] = os.environ['RDS_USERNAME']
        DATABASES['default']['PASSWORD'] = os.environ['RDS_PASSWORD']
    else:
        import dj_database_url
        DATABASES['default'] =  dj_database_url.config()
