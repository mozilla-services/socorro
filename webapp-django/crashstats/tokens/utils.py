from raven.processors import SanitizePasswordsProcessor


class RavenSanitizeAuthTokenProcessor(SanitizePasswordsProcessor):
    """Extend the standard SanitizePasswordsProcessor with one more key
    which is 'Auth-Token' which is what we use in our API."""
    FIELDS = tuple(SanitizePasswordsProcessor.FIELDS) + ('auth-token',)
