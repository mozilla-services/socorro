import mimetypes
import zipfile
import gzip
import tarfile
from cStringIO import StringIO


def preview_archive_content(file_object, content_type):
    """return file listing of the contents of an archive file"""
    out = StringIO()
    print >>out, "FILENAME".ljust(70),
    print >>out, "SIZE".ljust(9)
    print >>out, "-" * 80
    if content_type == 'application/zip':
        zf = zipfile.ZipFile(file_object)
        for member in zf.infolist():
            print >>out, member.filename.ljust(70),
            print >>out, str(member.file_size).rjust(9)

    elif content_type == 'application/x-gzip':
        tar = gzip.GzipFile(fileobj=file_object)
        zf = tarfile.TarFile(fileobj=tar)
        for member in zf.getmembers():
            if member.isfile():
                print >>out, member.name.ljust(70),
                print >>out, str(member.size).rjust(9)

    elif content_type == 'application/x-tar':
        zf = tarfile.TarFile(fileobj=file_object)
        for member in zf.getmembers():
            if member.isfile():
                print >>out, member.name.ljust(70),
                print >>out, str(member.size).rjust(9)

    else:
        raise NotImplementedError(content_type)

    return out.getvalue()


def filename_to_mimetype(filename):
    filename = filename.lower()
    # .tgz and .tar.gz files in mimetypes.guess_type
    # returns 'application/x-tar' :(
    if filename.endswith('.tgz') or filename.endswith('.tar.gz'):
        return 'application/x-gzip'
    return mimetypes.guess_type(filename)[0]
