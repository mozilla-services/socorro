# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from os.path import curdir
import errno


#------------------------------------------------------------------------------
def cleanEmptySubdirectories(topLimit, leafPath, osModule=os):
    """cleanEmptySubdirectories(topLimit,leafPath)

    walks backward up the directory tree from leafPath, calling
    os.rmdir(branch-below-me) until:
     - branch-below-me isn't empty
     - my current directory matches the name topLimit (therefore, topLimit is
       never removed)
     """
    opath = os.path.normpath(leafPath)  # allows relative paths to work
    topLimit = os.path.split(os.path.normpath(topLimit))[1]  # allows name or
                                                             # path
    if not topLimit in opath:
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
        except OSError, e:
            if errno.ENOTEMPTY == e.errno:
                break
            else:
                raise
        opath = path


#------------------------------------------------------------------------------
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
    fpath = os.path.normpath(fullPath)  # allows relative paths to work as
                                        # expected
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


#------------------------------------------------------------------------------
def makedirs(name, mode=0777, osModule=os):
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
        if tail == curdir:           # xxx/newdir/. exists if xxx/newdir exists
            return
    try:
        osModule.mkdir(name, mode)
    except OSError, e:
        #be happy if someone already created the path
        if e.errno != errno.EEXIST:
            raise
        else:  # it might be an existing non-directory
            if not osModule.path.isdir(name):
                raise OSError(errno.ENOTDIR, "Not a directory: '%s'" % name)


#------------------------------------------------------------------------------
#!/usr/bin/python
#
# Copyright 2005 by Centaur Software Engineering, Inc.
#
#    This file is part of The CSE Python Library.
#
#    The CSE Python Library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    The CSE Python Library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with The CSE Python Library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#------------------------------------------------------------------------------
def defaultAcceptanceFunction(dummy):
    return True


#------------------------------------------------------------------------------
def findFileGenerator(
  rootDirectory,
  acceptanceFunction=defaultAcceptanceFunction,
  directoryAcceptanceFunction=defaultAcceptanceFunction,
  directorySortFunction=cmp,
  maxDepth=100000,
  **kwargs
):
    """This function returns a generator that walks a filesystem tree.  It
    applies a user supplied function to each file that it encounters.  It only
    returns files for which the user supplied function returns true. It returns
    a tuple consiting of three items: the root path of the file, the name of
    the object, and the complete pathname of the object.  The user supplied
    function uses the same tuple as its input.
    """
    if 0 >= maxDepth:
        return
    for aCurrentDirectoryItem in [
      (rootDirectory, x, os.path.join(rootDirectory, x))
        for x in sorted(os.listdir(rootDirectory), directorySortFunction)
    ]:
        if (os.path.isdir(aCurrentDirectoryItem[2])
            and directoryAcceptanceFunction(aCurrentDirectoryItem)):
            for aSubdirectoryItem in findFileGenerator(
              aCurrentDirectoryItem[2],
              acceptanceFunction,
              directoryAcceptanceFunction,
              directorySortFunction,
              maxDepth=maxDepth - 1
            ):
                yield aSubdirectoryItem
        if acceptanceFunction(aCurrentDirectoryItem):
            yield aCurrentDirectoryItem

#==============================================================================
if __name__ == "__main__":
    for path, name, pathname in findFileGenerator("."):
        print pathname
