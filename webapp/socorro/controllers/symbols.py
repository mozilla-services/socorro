from socorro.lib.base import *

class SymbolsController(BaseController):
  def index(self):
    return Response('')
  
  def upload(self):
    """Upload debug symbols in bz2 format."""
    if (request.environ['REQUEST_METHOD'] == 'POST' and
        request.environ['CONTENT_TYPE'] and request.environ['CONTENT_LENGTH']):
      length = int(request.environ['CONTENT_LENGTH'])
      #body = request.environ['wsgi.input'].read(length)
      return Response("haven't implemented this yet..")
    else:
      #XXXsayrer set a 4xx status
      h.log("upload test")
      x = "symbol dir: " + g.pylons_config.app_conf['socorro.symbol_dir'] + " "
      x += "breakpad: " + g.pylons_config.app_conf['socorro.minidump_stackwalk']
      return Response(x)      
