#!/usr/bin/python
import os
import shutil
import glob

cgiCollector = "./dist/cgi-collector"
modpythonCollector = "./dist/modpython-collector"

def setupCommon(distPath):
  if not os.path.exists(distPath):
    os.makedirs(distPath)
  if not os.path.exists(distPath + "/simplejson"):
    os.mkdir(distPath + "/simplejson")
  shutil.copy("./docs/README-standalone-collector.txt",
              distPath + "/README.txt")
  toplevel = ["collect.py", "config.py", "uuid.py"]
  for name in toplevel:
    shutil.copy("./webapp/socorro/lib/" + name, distPath + "/" + name)
  simplejsonFiles = glob.glob("./webapp/socorro/lib/simplejson/*.py")
  for name in simplejsonFiles:
    shutil.copy(name, distPath + "/simplejson/" + os.path.basename(name))

setupCommon(cgiCollector)
setupCommon(modpythonCollector)

# concat mod_python docs
modpythonDocs = open("./docs/README-mod-python.txt")
distREADME = open(modpythonCollector + "/README.txt", "a")
distREADME.write(modpythonDocs.read())
distREADME.close()
modpythonDocs.close()

# copy mod_python-only files
shutil.copy("./webapp/socorro/lib/modpython-collector.py",
             modpythonCollector + "/collector.py")

# copy cgi-only files
shutil.copy("./webapp/socorro/lib/cgi-collector.py",
             cgiCollector + "/collector.py")
