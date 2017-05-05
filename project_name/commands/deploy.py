# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils import timezone
from storages.backends.s3boto3 import S3Boto3Storage
from subprocess import check_call, run, PIPE


class ProjectStorage(S3Boto3Storage):
    bucket_name = '{{ project_name }}'
    default_acl = bucket_acl = 'private'
    encryption = True
    url_protocol = 'https:'


def get_dumpfile_name(source):
    return settings.DB_DUMP_FORMAT_STRING.format(source)


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_false', dest='interactive', default=True,
            help="Do NOT prompt the user for input of any kind.",
        )
        parser.add_argument(
            '-n', '--dry-run',
            action='store_true', dest='dry_run', default=False,
            help="Do everything except modify the filesystem.",
        )

    def set_options(self, **options):
        """
        Set instance variables based on an options dict
        """
        self.interactive = options['interactive']
        self.verbosity = options['verbosity']
        self.dry_run = options['dry_run']

    def heroku_call(self, *args):
        args = ('heroku', ) + args + ('--app', settings.APP_NAME)
        check_call(args)

    def heroku_run(self, *args):
        self.heroku_call('run', *args)

    def deploy_to_heroku(self):

        # show maintenance screen
        self.heroku_call('maintenance:on')

        # scale down worker dynos to prevent db access
        # self.heroku_call('scale', 'worker=0')

        # get this commit's hash and push to heroku master
        git_hash = run(['git', 'rev-parse', 'HEAD'], stdout=PIPE).stdout.decode().strip()
        check_call(['git', 'push',
                    'git@heroku.com:{}.git'.format(settings.APP_NAME),
                    # 'https://git.heroku.com/{}.git'.format(settings.APP_NAME),
                    '{}:master'.format(git_hash),
                    '--force', '-v'])

        # for staging, always grab a current copy of production
        if settings.ENVIRONMENT == 'staging':
            call_command('backup', source='production')

        # for non-production, restore the production database unless disabled
        if settings.ENVIRONMENT != 'production' and settings.DEPLOY_SYNC_DB:
            self.heroku_call('pg:backups:restore', '{{ project_name }}-production::',
                             '--confirm', settings.APP_NAME)

        # always migrate the db
        self.heroku_run('./manage.py', 'migrate', '--noinput')

        # for production, force a new backup
        if settings.ENVIRONMENT == 'production':
            call_command('backup')

        # restore worker dynos
        # self.heroku_call('scale', 'worker=1')

        # restore web access
        self.heroku_call('maintenance:off')

    def handle(self, **options):
        self.set_options(**options)
        if settings.DEPLOY_ENVIRONMENT not in settings.DEPLOY_ENVIRONMENTS:
            raise CommandError('Deploy is only supported to {}.'.format(
                ', '.join(settings.DEPLOY_ENVIRONMENTS)
            ))
        self.stdout.write('Activating UTC timezone.\n')
        timezone.activate('UTC')
        check_call(['npm', 'run', 'build'])
        self.stdout.write('Collecting static files.\n')
        collectstatic_args = [
            'collectstatic', '-i', 'less', '--noinput'
        ]
        call_command(*collectstatic_args)
        self.stdout.write('Deploying and migrating app.\n')
        self.deploy_to_heroku()
        self.stdout.write('Activating new static file manifest.\n')
        collectstatic_args.append('--manifest')
        call_command(*collectstatic_args)
        self.stdout.write('Deployment complete.\n')
