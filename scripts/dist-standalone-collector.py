#!/usr/bin/python
import os
import shutil
import glob
from utils import *

cgiCollector = "./dist/cgi-collector"
modpythonCollector = "./dist/modpython-collector"

def setupCommon(distPath):
  makeDistDirs(distPath)
  shutil.copy("./docs/README-standalone-collector.txt",
              distPath + "/README.txt")
  copyLibFiles(["collect.py", "uuid.py"], distPath)
  copyModule("simplejson", "./webapp/socorro/lib/simplejson/*.py", distPath)

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

