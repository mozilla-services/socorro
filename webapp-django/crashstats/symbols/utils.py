import mimetypes
import zipfile
import gzip
import tarfile
from cStringIO import StringIO


class _ZipMember(object):

    def __init__(self, member, container):
        self.name = member.filename
        self.size = member.file_size
        self.container = container

    def extractor(self):
        return self.container.open(self.name)


class _TarMember(object):

    def __init__(self, member, container):
        self.member = member
        self.name = member.name
        self.size = member.size
        self.container = container

    def extractor(self):
        return self.container.extractfile(self.member)


def get_archive_members(file_object, content_type):
    if content_type == 'application/zip':
        zf = zipfile.ZipFile(file_object)
        for member in zf.infolist():
            yield _ZipMember(
                member,
                zf
            )

    elif content_type == 'application/x-gzip':
        tar = gzip.GzipFile(fileobj=file_object)
        zf = tarfile.TarFile(fileobj=tar)
        for member in zf.getmembers():
            if member.isfile():
                yield _TarMember(
                    member,
                    zf
                )

    elif content_type == 'application/x-tar':
        zf = tarfile.TarFile(fileobj=file_object)
        for member in zf.getmembers():
            # Sometimes when you make a tar file you get a
            # smaller index file copy that start with "./._".
            if member.isfile() and not member.name.startswith('./._'):
                yield _TarMember(
                    member,
                    zf
                )

    else:
        raise NotImplementedError(content_type)


def preview_archive_content(file_object, content_type):
    """return file listing of the contents of an archive file"""
    out = StringIO()
    for member in get_archive_members(file_object, content_type):
        print >>out, member.name.ljust(70),
        print >>out, str(member.size).rjust(9)

    return out.getvalue()


def filename_to_mimetype(filename):
    filename = filename.lower()
    # .tgz and .tar.gz files in mimetypes.guess_type
    # returns 'application/x-tar' :(
    if filename.endswith('.tgz') or filename.endswith('.tar.gz'):
        return 'application/x-gzip'
    return mimetypes.guess_type(filename)[0]
