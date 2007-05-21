#!/usr/bin/python
import os
import shutil
import glob
from utils import *

pylonsDir = "./dist/pylons"
webapp = "./webapp/socorro/"

def distFilter(tocopy, dirname, names):
  subtree = dirname[len(webapp):]
  for name in names:
    if (name == ".svn"):
      names.remove(name)
  for name in names:
    if (name.endswith("pyc") or name.endswith("~") or
        name.startswith("#")):
      pass
    else:
      tocopy.append((os.path.join(dirname, name),
                     os.path.join(pylonsDir, "socorro", subtree, name)))

def setup(distPath):
  makeDistDirs(distPath)
  if not os.path.exists(os.path.join(distPath, "socorro")):
    os.makedirs(os.path.join(distPath, "socorro"))

  toCopy = []
  os.path.walk(webapp, distFilter, toCopy)
  for (src, dest) in toCopy:
    if os.path.isdir(src):
      if not os.path.exists(dest):
        os.mkdir(dest)
    else:
      shutil.copy(src, dest)

  topLevel = ["production.ini.dist", "setup.py", "setup.cfg", "README.txt"]
  for name in topLevel:
    shutil.copy(os.path.join("./webapp/", name),
                os.path.join(pylonsDir, name))
  
setup(pylonsDir)
