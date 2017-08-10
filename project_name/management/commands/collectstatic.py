# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib

from django.contrib.staticfiles.management.commands import collectstatic
from django.core.management.base import CommandError
from traceback import print_exc

from ...storage import S3BotoManifestStaticFilesStorage


class Command(collectstatic.Command):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

        # needed for quick load of etag data
        if isinstance(self.storage, S3BotoManifestStaticFilesStorage):
            self.stdout.write('Collecting static files to: {}.'.format(
                self.storage.bucket_name
            ))
            self.storage.preload_metadata = True

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser=parser)
        parser.add_argument(
            '--manifest',
            action='store_true', dest='manifest', default=False,
            help="Renames pending manifest after run with --noinput."
        )

    def set_options(self, **options):
        super(Command, self).set_options(**options)
        self.manifest = options['manifest']

    def handle(self, **options):
        self.set_options(**options)
        if not self.interactive:
            if not self.storage.manifest_name.endswith('.tmp'):
                self.storage.manifest_name += '.tmp'
            if self.manifest:
                self.log('Activating manifest.', level=1)
                tmp_manifest_name = self.storage.manifest_name
                if not self.dry_run:
                    manifest_name = tmp_manifest_name.replace('.tmp', '')
                    try:
                        self.storage.copy_from(tmp_manifest_name, manifest_name)
                    except:
                        raise CommandError('No temporary manifest to activate.')
                    else:
                        self.storage.delete(tmp_manifest_name)
                        self.log('Manifest activated.', level=1)
                return
            else:
                self.log('Collecting files with temporary manifest.', level=1)
        elif self.manifest:
            raise CommandError('--manifest must be used with --noinput')
        return super(Command, self).handle(**options)

    def delete_file(self, path, prefixed_path, source_storage):
        """
        Checks if the target file should be deleted if it already exists
        """
        if isinstance(self.storage, S3BotoManifestStaticFilesStorage):
            if self.storage.exists(prefixed_path):
                try:
                    # get target etag
                    target_etag = self.storage.etag(prefixed_path)

                    # get local file hash
                    source = source_storage.open(path)
                    contents = source.read()
                    source_etag = '"%s"' % hashlib.md5(contents).hexdigest()
                    source.close()

                    if target_etag == source_etag:
                        self.log("ETAG match: '%s'" % path)
                        return False
                except:
                    print_exc()

                # if we make it here, we have excepted or hash did not match
                if self.dry_run:
                    self.log("Pretending to delete '%s'" % path)
                else:
                    self.log("Deleting '%s'" % path)
                    self.storage.delete(prefixed_path)
            # definitely upload in all cases except one valid matched case
            return True
        # fallback to normal behavior
        return super(Command, self).delete_file(path=path,
                                                prefixed_path=prefixed_path,
                                                source_storage=source_storage)
