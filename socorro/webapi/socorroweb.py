import web

"""When running a standalone web app based on web.py, the web.py code 
unfortunately makes some assumptions about the use of command line parameters
for setting the host and port names.  This wrapper class eliminates that
ambiguity by overriding the run method to use the host and port assigned 
in the constructor.
"""

#===============================================================================
class SocorroWebApplication(web.application):
  def __init__(self, serverIpAddress, serverPort, *args, **kwargs):
    self.serverIpAddress = serverIpAddress
    self.serverPort = serverPort
    web.application.__init__(self, *args, **kwargs)
  #-----------------------------------------------------------------------------
  def run(self, *middleware):
    f = self.wsgifunc(*middleware)
    web.runsimple(f, (self.serverIpAddress, self.serverPort))