#!/usr/bin/python
import os
import shutil
import glob

procssorDir = "./dist/processor"

def setupCommon(distPath):
  toplevel = ["collect.py", "config.py", "uuid.py", "monitor.py",
              "processor.py"]
  for name in toplevel:
    shutil.copy("./webapp/socorro/lib/" + name, distPath + "/" + name)