from raven.processors import SanitizePasswordsProcessor


class RavenSanitizeAuthTokenProcessor(SanitizePasswordsProcessor):
    """Extend the standard SanitizePasswordsProcessor with one more key
    which is 'Auth-Token' which is what we use in our API."""
    # Make it a frozenset because that's what the base class has.
    FIELDS = frozenset(
        tuple(SanitizePasswordsProcessor.FIELDS) + ('auth-token',)
    )
