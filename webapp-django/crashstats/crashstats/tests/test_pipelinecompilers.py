import os
import shutil
import tempfile

from nose.tools import ok_

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats.pipelinecompilers import GoogleAnalyticsCompiler
from crashstats import crashstats

SOURCE_FILE = os.path.join(
    crashstats.__path__[0],  # dir of the module
    'static/crashstats/js/socorro/google_analytics.js'
)
assert os.path.isfile(SOURCE_FILE), SOURCE_FILE


class TestGoogleAnalyticsCompiler(DjangoTestCase):

    def setUp(self):
        super(TestGoogleAnalyticsCompiler, self).setUp()
        self.tmp_static = tempfile.mkdtemp('static')

    def tearDown(self):
        super(TestGoogleAnalyticsCompiler, self).tearDown()
        shutil.rmtree(self.tmp_static)

    def test_match(self):
        compiler = GoogleAnalyticsCompiler(False, None)
        ok_(compiler.match_file('/foo/google_analytics.js'))
        ok_(not compiler.match_file('/foo/bar.js'))

    def test_compile(self):
        compiler = GoogleAnalyticsCompiler(False, None)
        with self.settings(GOOGLE_ANALYTICS_ID='UA-12345-6'):
            outfile = os.path.join(self.tmp_static, 'google-analytics.min.js')
            assert not os.path.isfile(outfile)
            compiler.compile_file(SOURCE_FILE, outfile)
            assert not os.path.isfile(outfile)

            # Try again
            compiler.compile_file(SOURCE_FILE, outfile, outdated=True)
            assert os.path.isfile(outfile)
            # now the outfile should have been created
            with open(outfile) as f:
                content = f.read()
                ok_('UA-12345-6' in content)
