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


def get_archive_members(file_object, file_name):
    file_name = file_name.lower()
    if file_name.endswith('.zip'):
        zf = zipfile.ZipFile(file_object)
        for member in zf.infolist():
            yield _ZipMember(
                member,
                zf
            )

    elif file_name.endswith('.tar.gz') or file_name.endswith('.tgz'):
        tar = gzip.GzipFile(fileobj=file_object)
        zf = tarfile.TarFile(fileobj=tar)
        for member in zf.getmembers():
            if member.isfile():
                yield _TarMember(
                    member,
                    zf
                )

    elif file_name.endswith('.tar'):
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
        raise NotImplementedError(file_name)


def preview_archive_content(file_object, file_name):
    """return file listing of the contents of an archive file"""
    out = StringIO()
    for member in get_archive_members(file_object, file_name):
        print >>out, member.name.ljust(70),
        print >>out, str(member.size).rjust(9)

    return out.getvalue()
