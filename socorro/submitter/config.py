"""Default configuration values used by the Socorro Submitter."""
from configman.dotdict import DotDict


# Ignore non-config module members like DotDict
always_ignore_mismatches = True


# Crash storage source
source = DotDict({
    'crashstorage_class': 'socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage',
})


# Crash storage destination
destination = DotDict({
    'crashstorage_class': 'socorro.submitter.breakpad_submitter_utilities.BreakpadPOSTDestination',
})


number_of_submissions = 'all'
