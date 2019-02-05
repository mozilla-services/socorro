# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from django.forms import ValidationError

from crashstats.crashstats import form_fields


class TestFormFields(object):
    def test_build_ids_field(self):
        field = form_fields.BuildIdsField(required=False)
        res = field.clean('12')
        assert res == [12]

        res = field.clean('12, 13')
        assert res == [12, 13]

        res = field.clean('')
        assert res is None

        res = field.clean('12, , 14, 0')
        assert res == [12, 14, 0]

    def test_build_ids_field_validation_error(self):
        field = form_fields.BuildIdsField(required=False)
        with pytest.raises(ValidationError):
            field.clean('asd')

    def test_build_ids_field_validation_error_list(self):
        field = form_fields.BuildIdsField(required=False)
        with pytest.raises(ValidationError):
            field.clean('12, 13, 14e')
