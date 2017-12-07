import pytest

from django.forms import ValidationError

from crashstats.base.tests.testbase import TestCase
from crashstats.crashstats import form_fields


class TestFormFields(TestCase):

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
