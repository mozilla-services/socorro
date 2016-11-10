# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from sqlalchemy import types


class BuildTypeType(types.UserDefinedType):
    name = 'build_type'

    def get_col_spec(self):
        return 'build_type'

    def bind_processor(self, dialect):
        return lambda value: value

    def result_processor(self, dialect, coltype):
        return lambda value: value

    def __repr__(self):
        return 'build_type'

class BuildTypeEnumType(types.UserDefinedType):
    name = 'build_type_enum'

    def get_col_spec(self):
        return 'build_type_enum'

    def bind_processor(self, dialect):
        return lambda value: value

    def result_processor(self, dialect, coltype):
        return lambda value: value

    def __repr__(self):
        return 'build_type_enum'
