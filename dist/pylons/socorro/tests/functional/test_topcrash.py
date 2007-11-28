from socorro.tests import *
from socorro.models import Branch

class TestTopcrashController(TestController):
  def test_index(self):
    response = self.app.get(url_for(controller='topcrasher'))
    aproductversion = Branch.getProductVersions().fetchone()
    response = self.app.get(url_for(controller='topcrasher',
                                    action='byversion',
                                    product=aproductversion.product,
                                    version=aproductversion.version))

    abranch = Branch.getBranches().fetchone()
    response = self.app.get(url_for(controller='topcrasher',
                                    action='bybranch',
                                    branch=abranch.branch))
