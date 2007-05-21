from socorro.tests import *

class TestSymbolsController(TestController):
    def test_index(self):
        response = self.app.get(url_for(controller='symbols'))
        # Test response...