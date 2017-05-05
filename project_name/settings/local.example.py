from .dev import *   # noqa

if DEBUG:
    INSTALLED_APPS += (
        'django_extensions',
    )

    DEBUG_TOOLBAR = bool(os.environ.setdefault('DEBUG_TOOLBAR', str(False)) == 'True')
    if DEBUG_TOOLBAR:
        INSTALLED_APPS += (
            'debug_toolbar',
        )
        MIDDLEWARE_CLASSES += (
            'debug_toolbar.middleware.DebugToolbarMiddleware',
        )
        show_toolbar = lambda request: True
        DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': '{{ project_name }}.settings.local.show_toolbar'}

AWS_STORAGE_BUCKET_NAME = '{{ project_name }}-{userid}'
