# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This module used to contain the overly complicated definition of the
Socorro App class definitions.  That system has been moved to socorro_app.py.
The following two imports into this module are for backwards compatibility.
"""

from socorrolib.app.socorro_app import main
from socorrolib.app.socorro_app import App

