#!/usr/bin/python
import os
import shutil
import glob
from utils import *

pylonsDir = "./dist/pylons"

def setup(distPath):
  if os.path.exists(distPath):
    shutil.rmtree(distPath)
  makeDistDirs(distPath)
  shutil.copytree("./webapp/socorro", "./dist/pylons/socorro")

  # remove any pyc files
  for root, dirs, files in os.walk(distPath, topdown=False):
    for name in files:
      if name.endswith(".pyc"):
        os.remove(os.path.join(root, name))

  topLevel = ["production.ini.dist", "setup.py", "setup.cfg", "README.txt"]
  for name in topLevel:
    shutil.copy(os.path.join("./webapp/", name),
                os.path.join(pylonsDir, name))
  
setup(pylonsDir)
