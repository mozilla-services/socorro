from socorro.tests import *
from socorro.models import Branch

class TestTopcrashController(TestController):
  def test_index(self):
    response = self.app.get(url_for(controller='topcrasher'))
    abranch = Branch.get_by()
    response = self.app.get(url_for(controller='topcrasher',
                                    action='byversion',
                                    product=abranch.product,
                                    version=abranch.version))
    response = self.app.get(url_for(controller='topcrasher',
                                    action='bybranch',
                                    branch=abranch.branch))
