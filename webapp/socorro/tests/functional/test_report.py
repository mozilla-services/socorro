from socorro.tests import *

class TestReportController(TestController):
    def test_index(self):
        response = self.app.get(url_for(controller='report'))
        # Test response...