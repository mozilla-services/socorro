import os
import shutil
import glob

"""stuff for our distribution scripts"""

def copyModule(name, globString, distPath):
  if not os.path.exists(os.path.join(distPath, name)):
    os.mkdir(os.path.join(distPath, name))
  matchFiles = glob.glob(globString)
  for fname in matchFiles:
    shutil.copy(fname, os.path.join(distPath, name, os.path.basename(fname)))

def makeDistDirs(baseDir, kids=[]):
  """make dist dir. kids is a list of children"""
  if not os.path.exists(baseDir):
    os.makedirs(baseDir)
  for kid in kids:
    if not os.path.exists(os.path.join(baseDir, kid)):
      os.makedirs(os.path.join(baseDir, kid))
