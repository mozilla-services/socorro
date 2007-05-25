#!/usr/bin/python
import os
import shutil
import glob
from utils import *

pylonsDir = "./dist/pylons"
webapp = "./webapp/socorro/"
eggdir = "./webapp/Socorro.egg-info/"

def distFilter(tocopy, dirname, names):
  for name in names:
    if (name == ".svn"):
      names.remove(name)
  for name in names:
    if (name.endswith("pyc") or name.endswith("~") or
        name.startswith("#")):
      pass
    else:
      tocopy.append((os.path.join(dirname, name), dirname, name))

def copyDirWithNoJunk(targetDir):
  toCopy = []
  os.path.walk(targetDir, distFilter, toCopy)
  for (src, dirname, name) in toCopy:
    subtree = dirname[len("./webapp/"):]
    dest = os.path.normpath(os.path.join(pylonsDir, subtree, name))
    if os.path.isdir(src):
      if not os.path.exists(dest):
        os.mkdir(dest)
    else:
      shutil.copy(src, dest)

def setup(distPath):
  makeDistDirs(distPath)
  if not os.path.exists(os.path.join(distPath, "socorro")):
    os.makedirs(os.path.join(distPath, "socorro"))
  if not os.path.exists(os.path.join(distPath, "Socorro.egg-info")):
    os.makedirs(os.path.join(distPath, "Socorro.egg-info"))
  copyDirWithNoJunk(webapp)
  copyDirWithNoJunk(eggdir)
  
  topLevel = ["production.ini.dist", "setup.py", "setup.cfg", "README.txt"]
  for name in topLevel:
    shutil.copy(os.path.join("./webapp/", name),
                os.path.join(pylonsDir, name))

  # move config.py so it doesn't overwrite
  shutil.move(os.path.join(pylonsDir, "socorro", "lib", "config.py"),
              os.path.join(pylonsDir, "socorro", "lib", "config.py.dist"))
  
setup(pylonsDir)
