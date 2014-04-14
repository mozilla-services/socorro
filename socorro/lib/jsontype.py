# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from sqlalchemy import types


class JsonType(types.UserDefinedType):
    name = 'json'

    def get_col_spec(self):
        return 'JSON'

    def bind_processor(self, dialect):
        return lambda value: value

    def result_processor(self, dialect, coltype):
        return lambda value: value

    def __repr__(self):
        return "json"
