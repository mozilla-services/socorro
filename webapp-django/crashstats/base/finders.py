from pipeline.finders import PipelineFinder

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class LeftoverPipelineFinder(PipelineFinder):
    """This finder is expected to come AFTER pipeline.finders.PipelineFinder
    in settings.STATICFILES_FINDERS.
    If a path is looked for here it means it's trying to find a file
    that pipeline.finders.PipelineFinder couldn't find.
    """
    def find(self, path, all=False):
        # But where was it defined?
        for config_name in 'STYLESHEETS', 'JAVASCRIPT':
            config = settings.PIPELINE[config_name]
            for key, directive in config.items():
                if path in directive['source_filenames']:
                    raise ImproperlyConfigured(
                        'Static file {} can not be found anywhere. Defined in '
                        "PIPELINE[{!r}][{!r}]['source_filenames']".format(
                            path,
                            config_name,
                            key,
                        )
                    )
        # If the file can't be found AND it's not in bundles, there's
        # got to be something else really wrong.
        raise NotImplementedError(path)
