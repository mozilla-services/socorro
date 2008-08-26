from stat import S_IRGRP, S_IXGRP, S_IWGRP, S_IRUSR, S_IXUSR, S_IWUSR, S_ISGID
from datetime import timedelta
import re

# Storage constants
storageRoot = "/home/lars/temp/standard"
deferredStorageRoot = "/home/lars/temp/deferred"
dumpDirPrefix = "bp_"
jsonFileSuffix = ".json"
dumpFileSuffix = ".dump"

# Dump files are stored with these permissions
dumpPermissions = S_IRGRP | S_IWGRP | S_IRUSR | S_IWUSR
dirPermissions = S_IRGRP | S_IXGRP | S_IWGRP | S_IRUSR | S_IXUSR | S_IWUSR

# Set the group ID on minidumps so that they can be deleted by other users.
# (optional)
# dumpGID = 501
dumpGID = None

# Tell the collector where the reporter lives (optional)
# reporterURL = 'http://crash-stats.mozilla.com'
reporterURL = None

# The form field the client sends the dump in
dumpField = "upload_file_minidump"

# The number of dumps to be stored in a single directory
dumpDirCount = 500

# Returned to the client with a uuid following
dumpIDPrefix = "bp-"

# Dump directories age for a while before they are deleted
dumpDirDelta = timedelta(hours=2)
dateDirDelta = timedelta(hours=1)

# Database details for standalone dump processors
processorDatabaseURI = "postgres://socorro:password@localhost:5432/socorro"
processorMinidump = "/usr/local/bin/minidump_stackwalk"
processorSymbols = ["/home/sayrer/dump"]
processorConnTimeout = 600

# Number of seconds to wait between walking the minidump directory tree.
processorLoopTime = 360

# By default, minidumps that failed processing will be saved to this directory.
# NOTE: This must be on the same filesystem as storageRoot, but must not live
# within storageRoot.
saveMinidumpsTo = '/tmp/socorro-saved'
saveFailedMinidumps = True

# When testing, set to true to rename processed minidump files instead of
# deleting them.
saveProcessedMinidumps = False
saveFailedMinidumps = False

# Settings for creating a link to a file in a given version control viewing
# website. For example:
#    {'cvs':{'cvs.mozilla.org/cvsroot':'http://bonsai.mozilla.org/cvsblame.cgi?file=%(file)s&rev=%(revision)s&mark=%(line)s#%(line)s'}}
vcsMappings = {}

throttleConditions = [
  #("Version", lambda x: x[-3:] == "pre", 25), # queue 25% of crashes with version ending in "pre"
  #("Add-ons", re.compile('inspector\@mozilla\.org\:1\..*'), 75), # queue 75% of crashes where the inspector addon is at 1.x
  #("UserID", "d6d2b6b0-c9e0-4646-8627-0b1bdd4a92bb", 100), # queue all of this user's crashes
  #("SecondsSinceLastCrash", lambda x: 300 >= int(x) >= 0, 100), # queue all crashes that happened within 5 minutes of another crash
  (None, True, 10) # queue 10% of what's left
]

