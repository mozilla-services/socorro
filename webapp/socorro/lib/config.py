from stat import S_IRGRP, S_IXGRP, S_IWGRP, S_IRUSR, S_IXUSR, S_IWUSR, S_ISGID

# Storage constants
storageRoot = "/tmp/socorro/"
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

# The form field the client sends the dump in
dumpField = "upload_file_minidump"

# The number of dumps to be stored in a single directory
dumpDirCount = 500

# Returned to the client with a uuid following
dumpIDPrefix = "bp-"
