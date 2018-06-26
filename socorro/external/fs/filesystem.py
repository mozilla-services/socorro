# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import errno
import os
from os.path import curdir


def cleanEmptySubdirectories(topLimit, leafPath, osModule=os):
    """cleanEmptySubdirectories(topLimit,leafPath)

    walks backward up the directory tree from leafPath, calling
    os.rmdir(branch-below-me) until:
     - branch-below-me isn't empty
     - my current directory matches the name topLimit (therefore, topLimit is
       never removed)
     """
    opath = os.path.normpath(leafPath)  # allows relative paths to work
    # allows name or path
    topLimit = os.path.split(os.path.normpath(topLimit))[1]
    if topLimit not in opath:
        raise OSError(
            errno.ENOENT,
            '%s not on path to %s' % (topLimit, leafPath)
        )
    while True:
        path, tail = os.path.split(opath)
        if topLimit == tail:
            break
        try:
            osModule.rmdir(opath)
        except OSError as e:
            if errno.ENOTEMPTY == e.errno:
                break
            else:
                raise
        opath = path


def visitPath(rootDir, fullPath, visit, osModule=os):
    """
    Visit for each directory:
    for each directory along the path rootDir/.../fullPath,
    including rootDir as the first instance, and .../fullPath as last instance:
    call visit(currentPath)
    if fullPath is a non-directory or a link it is skipped
    Raise OSError (errno.ENOENT) if rootDir is not a parent of fullpath
    # ?Optimization option: Memoize visited paths to avoid them? How to deal
    with prefix paths?
    """
    # allows relative paths to work as expected
    fpath = os.path.normpath(fullPath)
    root = os.path.normpath(rootDir)
    if not fpath.startswith(root):
        raise OSError(
            errno.ENOENT,
            '%s not on path to %s' % (rootDir, fullPath)
        )
    pathParts = fpath[len(os.sep) + len(root):].split(os.sep)
    visit(root)
    for p in pathParts:
        root = os.path.join(root, p)
        if osModule.path.isdir(root) and not osModule.path.islink(root):
            visit(root)
        elif osModule.path.exists(root):
            pass
        else:
            raise OSError(errno.ENOENT, '%s does not exist' % (root))


def makedirs(name, mode=777, osModule=os):
    """makedirs(path [, mode=0777])

    Super-mkdir; create a leaf directory and all intermediate ones.
    Works like mkdir, except that any intermediate path segment (not
    just the rightmost) will be created if it does not exist.  This is
    recursive.

    picked up from os.py, this version switches the try:except: protection to
    the call to os.mkdir() instead of the recursive call to makedirs()
    """
    head, tail = os.path.split(name)
    if not tail:
        head, tail = os.path.split(head)
    if head and tail and not os.path.exists(head):
        makedirs(head, mode)
        # xxx/newdir/. exists if xxx/newdir exists
        if tail == curdir:
            return
    try:
        osModule.mkdir(name, mode)
    except OSError as e:
        # be happy if someone already created the path
        if e.errno != errno.EEXIST:
            raise
        else:
            # it might be an existing non-directory
            if not osModule.path.isdir(name):
                raise OSError(errno.ENOTDIR, "Not a directory: '%s'" % name)
