from stat import S_IRGRP, S_IROTH, S_IRUSR, S_IXOTH, S_IXUSR, S_IWUSR

# Storage constants
storageRoot = "/tmp/socorro/"
dumpDirPrefix = "bp_"
jsonFileSuffix = ".json"
dumpFileSuffix = ".dump"

# Dump files are stored with these permissions
dumpPermissions = S_IRGRP | S_IROTH | S_IRUSR | S_IXOTH | S_IXUSR | S_IWUSR;

# The form field the client sends the dump in
dumpField = "upload_file_minidump"

# The number of dumps to be stored in a single directory
dumpDirCount = 500

# Returned to the client with a uuid following
dumpIDPrefix = "bp-"
