from django.conf import settings
from django.contrib.staticfiles.storage import ManifestFilesMixin
from storages.backends import s3boto3


class S3Boto3Storage(s3boto3.S3Boto3Storage):

    def etag(self, name):
        name = self._normalize_name(self._clean_name(name))
        entry = None
        if self.entries:
            entry = self.entries.get(name)
        if entry is None:
            entry = self.bucket.Object(self._encode_name(name))
        return getattr(entry, 'e_tag', None)

    def copy_from(self, src_name, dst_name):
        src_name = self._encode_name(self._normalize_name(self._clean_name(src_name)))
        dst_name = self._encode_name(self._normalize_name(self._clean_name(dst_name)))
        dst_obj = self.bucket.Object(dst_name)
        dst_obj.copy_from(ACL='public-read', CopySource={
            'Bucket': self.bucket_name,
            'Key': src_name,
        })


class S3BotoManifestStaticFilesStorage(ManifestFilesMixin, S3Boto3Storage):
    """ An S3-aware ManifestStaticFilesStorage """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    location = settings.STATICFILES_LOCATION

    def hashed_name(self, name, content=None):
        """ Continue monitoring django.contrib.staticfiles.storage for
        improvements that make this "trick" unnecessary.  This is an
        artifact of an excessively liberal REGEX picking up files that
        do not exist, and the non-graceful failure of missing S3
        resources.  https://code.djangoproject.com/ticket/21080  """
        try:
            return super(S3BotoManifestStaticFilesStorage,
                         self).hashed_name(name, content)
        except ValueError:
            return name
