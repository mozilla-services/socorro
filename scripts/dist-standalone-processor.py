#!/usr/bin/python
import os
import shutil
import glob
from utils import *

processorDir = "./dist/processor/socorro"

def setup(distPath):
  makeDistDirs(distPath, ["lib"])
  toplevel = ["collect.py", "config.py", "uuid.py", "monitor.py",
              "processor.py"]
  for name in toplevel:
    shutil.copy("./webapp/socorro/lib/" + name, distPath + "/lib/" + name)
  copyModule("simplejson", "./webapp/socorro/lib/simplejson/*.py", distPath)
  copyModule("models", "./webapp/socorro/models/*.py", distPath)

  
setup(processorDir)
