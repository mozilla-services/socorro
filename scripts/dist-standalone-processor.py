#!/usr/bin/python
import os
import shutil
import glob
from utils import *

processorDir = "./dist/processor/socorro"

def setup(distPath):
  makeDistDirs(distPath, ["lib"])
  copyLibFiles(["monitor.py", "processor.py"], distPath, "/lib/")
  copyModule("simplejson", "./webapp/socorro/lib/simplejson/*.py", distPath)
  copyModule("models", "./webapp/socorro/models/*.py", distPath)
  
setup(processorDir)
