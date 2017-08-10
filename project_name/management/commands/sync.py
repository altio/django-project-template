# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import stat
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from subprocess import check_call
from .deploy import get_dumpfile_name, ProjectStorage


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
            '-s', '--source', default='production',
            help="Source to use for sync (default: production).",
        )
        parser.add_argument(
            '-f', '--force', '--fresh',
            action='store_true', dest='force', default=False,
            help="Force acquisition of a fresh snapshot of the source.",
        )
        parser.add_argument(
            '-r', '--real',
            action='store_false', dest='fake', default=True,
            help="Set fake passwords (if available).",
        )
        parser.add_argument(
            '-k', '--keep',
            action='store_false', dest='delete', default=True,
            help="Keep downloaded DB snapshot for use by future sync commands.",
        )
        parser.add_argument(
            '-u', '--no-migrate',
            action='store_false', dest='migrate', default=True,
            help="Do not migrate the database.",
        )

    def set_options(self, **options):
        """
        Set instance variables based on an options dict
        """
        self.interactive = options['interactive']
        self.verbosity = options['verbosity']
        self.force = options['force']
        self.source = options['source']
        self.fake = options['fake']
        self.delete = options['delete']
        self.migrate = options['migrate']

    def get_dump_from_s3(self, dumpfile):
        storage = ProjectStorage()
        with storage.open(dumpfile, 'rb') as src:
            with open(dumpfile, 'wb') as dst:
                dst.write(src.read())

    def restore_from_pg_backup(self, dumpfile, common_args):
        check_call(['psql', '--file={}'.format(dumpfile)] + common_args +
                   [settings.DATABASES['default']['NAME']])

    def restore_from_heroku(self, dumpfile, common_args):
        check_call([
            'pg_restore', '--no-owner',
            '--dbname={}'.format(settings.DATABASES['default']['NAME'])
        ] + common_args + [dumpfile])

    def handle(self, **options):
        self.set_options(**options)
        if self.source not in settings.DEPLOY_ENVIRONMENTS:
            self.stderr.write(
                'Synchronization only permitted from {}.'.format(
                    ' or '.join(settings.DEPLOY_ENVIRONMENTS)))
            exit(0)
        dumpfile = get_dumpfile_name(self.source)
        if os.path.exists(dumpfile) and not self.force:
            self.stdout.write(
                'Found existing database dump from {}.\n'.format(self.source)
            )
        else:
            if self.force:
                self.stdout.write(
                    'Forcing fresh database dump from {}.\n'.format(self.source)
                )
                call_command('backup', source=self.source)
            self.stdout.write(
                'Downloading database dump from {}.\n'.format(self.source)
            )
            self.get_dump_from_s3(dumpfile)
        self.stdout.write('Syncing DB.\n')
        passfile = os.path.join(os.path.expanduser('~'), '.pgpass')
        with open(passfile, 'w') as fd:
            fd.write('*:*:*:*:{password}'.format(
                password=settings.DATABASES['default']['PASSWORD'],
            ))
        os.chmod(passfile, stat.S_IRUSR | stat.S_IWUSR)

        common_args = [
            '--host={}'.format(settings.DATABASES['default']['HOST']),
            '--port={}'.format(settings.DATABASES['default']['PORT']),
            '--username={}'.format(settings.DATABASES['default']['USER']),
            '--no-password'
        ]

        # only for local env perform a db reset... others will do it elsewhere
        if settings.ENVIRONMENT == 'local':
            check_call(['dropdb'] + common_args + [
                settings.DATABASES['default']['NAME'],
                '--if-exists'])
            check_call(['createdb'] + common_args + [
                settings.DATABASES['default']['NAME']])

        self.restore_from_heroku(dumpfile, common_args)

        # cleanup temp files
        os.remove(passfile)
        if self.delete:
            os.remove(dumpfile)

        self.stdout.write('DB sync complete.  Migrating...\n')

        # migrate the restored database
        if self.migrate:
            call_command('migrate', interactive=False)

        # set passwords to password
        if self.fake:
            call_command('set_fake_passwords', interactive=False)
