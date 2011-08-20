import web


class StandAloneWebApplication(web.application):

    """
    When running a standalone web app based on web.py, the web.py code
    unfortunately makes some assumptions about the use of command line
    parameters for setting the host and port names.  This wrapper class
    eliminates that ambiguity by overriding the run method to use the host and
    port assigned in the constructor.

    """

    def __init__(self, server_ip_address, server_port, *args, **kwargs):
        """
        Construct the web application.
        """
        self.serverIpAddress = server_ip_address
        self.serverPort = server_port
        super(StandAloneWebApplication, self).__init__(self, *args, **kwargs)

    def run(self, *middleware):
        """
        Run the application.
        """
        f = self.wsgifunc(*middleware)
        web.runsimple(f, (self.serverIpAddress, self.serverPort))
