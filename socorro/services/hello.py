import socorro.webapi.webapiService as webapi


#===============================================================================
class Hello(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------
  def __init__(self, context):
    super(Hello, self).__init__(context)
  #-----------------------------------------------------------------------------
  "/hello"
  uri = '/hello'
  #-----------------------------------------------------------------------------
  def get(self, *args):
    return "hello"
