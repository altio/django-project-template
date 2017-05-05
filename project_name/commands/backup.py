# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import stat
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from subprocess import check_call
from .deploy import get_dumpfile_name, ProjectStorage


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--source', default='production',
            help="Source to use for sync (default: production).",
        )

    def set_options(self, **options):
        """
        Set instance variables based on an options dict
        """
        self.verbosity = options['verbosity']
        self.source = options['source']
        self.app_name = '{{ project_name }}-{}'.format(self.source)

    def heroku_call(self, *args):
        args = ('heroku', ) + args + ('--app', self.app_name)
        check_call(args)

    def get_dump_from_heroku(self, dumpfile):
        self.heroku_call('pg:backups:capture')
        self.heroku_call('pg:backups:download', '--output', dumpfile)

    def get_dump_from_pg(self, dumpfile):

        passfile = os.path.join(os.path.expanduser('~'), '.pgpass')
        with open(passfile, 'w') as fd:
            fd.write('*:*:*:*:{password}'.format(
                password=settings.DATABASES['default']['PASSWORD'],
            ))
        os.chmod(passfile, stat.S_IRUSR | stat.S_IWUSR)

        pg_dump_args = [
            'pg_dump',
            '--host={}'.format(settings.DATABASES['default']['HOST']),
            '--port={}'.format(settings.DATABASES['default']['PORT']),
            '--username={}'.format(settings.DATABASES['default']['USER']),
            '--dbname={}'.format(settings.DATABASES['default']['NAME']),
            '--no-password', '--no-owner',
            '--file={}'.format(dumpfile)
        ]
        check_call(pg_dump_args)
        os.remove(passfile)

    def put_dump_to_s3(self, dumpfile):
        storage = ProjectStorage()
        with open(dumpfile, 'rb') as content:
            storage.save(dumpfile, content)

    def handle(self, **options):
        self.set_options(**options)
        if self.source not in settings.DEPLOY_ENVIRONMENTS:
            self.stderr.write(
                'Database backups are only permitted from {}.'.format(
                    ' or '.join(settings.DEPLOY_ENVIRONMENTS)))
            exit(0)
        self.stdout.write('Activating UTC timezone.\n')
        timezone.activate('UTC')
        self.stdout.write('Backing up database.\n')
        dumpfile = get_dumpfile_name(self.source)
        self.get_dump_from_heroku(dumpfile)
        self.stdout.write('Backup complete, uploading to S3.\n')
        self.put_dump_to_s3(dumpfile)
        os.remove(dumpfile)
