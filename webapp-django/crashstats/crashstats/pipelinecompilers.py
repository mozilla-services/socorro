from django.conf import settings

from pipeline.compilers import CompilerBase


class GoogleAnalyticsCompiler(CompilerBase):
    """All this compiler does is to replace the fake Google Analytics
    Tracking ID in the static asset called google_analytics.js."""
    output_extension = 'js'

    def match_file(self, filename):
        return 'google_analytics.js' in filename

    def compile_file(self, infile, outfile, outdated=False, force=False):
        if not outdated and not force:
            return  # No need to recompiled file

        # It might not be set. For example, in Travis runs.
        if settings.GOOGLE_ANALYTICS_ID:
            with open(infile) as source:
                new_content = source.read().replace(
                    'UA-XXXXX-X',
                    settings.GOOGLE_ANALYTICS_ID
                )
                with open(outfile, 'w') as destination:
                    destination.write(new_content)
