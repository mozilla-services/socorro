"""Default configuration values used by the Crontabber app."""
from configman.dotdict import DotDict


# Ignore non-config module members like DotDict
always_ignore_mismatches = True

crontabber = DotDict({
    'database_class': 'socorro.external.postgresql.connection_context.ConnectionContext',

    'class-BugzillaCronApp.days_into_past': 0,
})


resource = DotDict({
    'postgresql': {
        'database_class': 'socorro.external.postgresql.connection_context.ConnectionContext',
    }
})
