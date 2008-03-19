#
# This script will read a Socorro database, and try to retrieve
# missing symbols from Microsoft's symbol server. It honors a blacklist
# (blacklist.txt) of symbols that are known to be from our applications,
# and it maintains its own list of symbols that the MS symbol server
# doesn't have (skiplist.txt). It also saves the last-run time of the
# script (last-run.txt) and will only query for reports newer than that
# time on successive runs.
#
# The script must have installed alongside it:
# * The symsrv_convert.exe utility
# * dbghelp.dll
# * symsrv.dll
# * symsrv.yes (a zero-byte file that indicates that you've accepted
#               the Microsoft symbol server EULA)
# * config.py  (create this from the template in config.py.in)
# The script also depends on having write access to the directory it is
# installed in, to write the skiplist/last-run text files. For obvious
# reasons, the script also needs write access to the symbol_path
# configured in config.py.

import config
import sys
import os.path
import time, datetime
import subprocess
import urllib

# Just hardcoded here
MICROSOFT_SYMBOL_SERVER = "http://msdl.microsoft.com/download/symbols"

if not os.path.exists(config.symbol_path):
    print >>sys.stderr, "Symbol path %s doesn't exist" % config.symbol_path
    sys.exit(1)

# Symbols that we know belong to us, so don't ask Microsoft for them.
blacklist=[]
try:
  bf = file('blacklist.txt', 'r')
  for line in bf:
      blacklist.append(line.strip())
  bf.close()
except IOError:
  pass

# Symbols that we've asked for in the past unsuccessfully
skiplist={}
try:
  sf = file('skiplist.txt', 'r')
  for line in sf:
      line = line.strip()
      if line == '':
          continue
      (debug_id, debug_file) = line.split(None, 1)
      skiplist[debug_id] = debug_file
  sf.close()
except IOError:
  pass

try:
  f = urllib.urlopen(config.query_data_url)
except IOError:
  print >>sys.stderr, "Failed to get query data from %s" % config.query_data_url
  sys.exit(1)

# skip the header lines
f.readline()
f.readline()

for line in f:
  if line.startswith('('):
    break
  (id, filename) = line.split('|', 1)
  id = id.strip()
  filename = filename.strip()
  if filename in blacklist:
    # This is one of our our debug files from Firefox/Thunderbird/etc
    continue
  if id in skiplist and skiplist[id] == filename:
    # We've asked the symbol server previously about this, so skip it.
    continue
  sym_file = os.path.join(config.symbol_path, filename, id,
                          filename.replace(".pdb","") + ".sym")
  if os.path.exists(sym_file):
    # We already have this symbol
    continue
  if config.read_only_symbol_path != '' and \
     os.path.exists(os.path.join(config.symbol_path, filename, id,
                                 filename.replace(".pdb","") + ".sym")):
    # We already have this symbol
    continue
  # Not in the blacklist, skiplist, and we don't already have it, so
  # ask the symbol server for it.
  # This expects that symsrv_convert.exe and all its dependencies
  # are in the current directory.
  rv = subprocess.call(["symsrv_convert.exe",
                        MICROSOFT_SYMBOL_SERVER,
                        config.symbol_path,
                        filename,
                        id])
  # Return code of 2 or higher is an error
  if rv >= 2:
    skiplist[id] = filename
  # Otherwise we just assume it was written out, not much we can do
  # if it wasn't. We'll try again next time we see it anyway.

# Write out our new skip list
try:
  sf = file('skiplist.txt', 'w')
  for (debug_id,debug_file) in skiplist.iteritems():
      sf.write("%s %s\n" % (debug_id, debug_file))
  sf.close()
except IOError:
  print >>sys.stderr, "Error writing skiplist.txt"
