"""Default configuration values used by the FetchTransformSaveApp subclasses."""
from configman.dotdict import DotDict


# Ignore non-config module members like DotDict
always_ignore_mismatches = True


# Crash storage source
source = DotDict({
    'crashstorage_class': 'socorro.external.fs.crashstorage.FSPermanentStorage',
})


# Crash storage destinations
destination = DotDict({
    'crashstorage_class': 'socorro.external.fs.crashstorage.FSPermanentStorage',
})
