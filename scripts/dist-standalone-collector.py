#!/usr/bin/python
import os
import shutil
import glob

distPath = "./dist/standalone-collector"
if not os.path.exists(distPath):
  os.makedirs(distPath)
if not os.path.exists(distPath + "/simplejson"):
  os.mkdir(distPath + "/simplejson")

shutil.copy("./docs/README-standalone-collector.txt", distPath + "/README.txt")

toplevel = ["standalone_collector.py", "config.py", "uuid.py"]
for name in toplevel:
  shutil.copy("./webapp/socorro/lib/" + name, distPath + "/" + name)

simplejsonFiles = glob.glob("./webapp/socorro/lib/simplejson/*.py")
for name in simplejsonFiles:
  shutil.copy(name, distPath + "/simplejson/" + os.path.basename(name))
