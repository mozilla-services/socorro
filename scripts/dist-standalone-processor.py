#!/usr/bin/python
import os
import shutil
import glob

processorDir = "./dist/processor/socorro"


def moveModule(name, globString, distPath):
  if not os.path.exists(os.path.join(distPath, name)):
    os.mkdir(os.path.join(distPath, name))
  matchFiles = glob.glob(globString)
  for fname in matchFiles:
    shutil.copy(fname, os.path.join(distPath, name, os.path.basename(fname)))

def setup(distPath):
  if not os.path.exists(distPath):
    os.makedirs(distPath)
  if not os.path.exists(os.path.join(distPath, "lib")):
    os.makedirs(os.path.join(distPath, "lib"))
  toplevel = ["collect.py", "config.py", "uuid.py", "monitor.py",
              "processor.py"]
  for name in toplevel:
    shutil.copy("./webapp/socorro/lib/" + name, distPath + "/lib/" + name)
  moveModule("simplejson", "./webapp/socorro/lib/simplejson/*.py", distPath)
  moveModule("models", "./webapp/socorro/models/*.py", distPath)

  
setup(processorDir)
