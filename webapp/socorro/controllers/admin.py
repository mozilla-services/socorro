from socorro.lib.base import *
from authkit.permissions import RemoteUser
from authkit import authorize

class AdminController(BaseController):
    def index(self):
        return Response('Admin Test')

# wrap the controller in authkit protection
AdminController = authorize.middleware(AdminController(), RemoteUser())
