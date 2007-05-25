from socorro.tests import *
import sys

class TestQueryController(TestController):
  def test_query(self):
    response = self.app.get(url_for(controller='/query'))
    response = self.app.get(url_for(controller='/query',
                                    product='Firefox', do_query=1))
    assert "'Firefox'" in response

