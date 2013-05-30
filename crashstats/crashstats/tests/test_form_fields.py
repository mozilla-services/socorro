from nose.tools import eq_, raises

from django.forms import ValidationError
from django.test import TestCase

from crashstats.crashstats import form_fields


class TestFormFields(TestCase):

    def test_build_ids_field(self):
        field = form_fields.BuildIdsField(required=False)
        res = field.clean('12')
        eq_(res, [12])

        res = field.clean('12, 13')
        eq_(res, [12, 13])

        res = field.clean('')
        eq_(res, None)

        res = field.clean('12, , 14, 0')
        eq_(res, [12, 14, 0])

    @raises(ValidationError)
    def test_build_ids_field_validation_error(self):
        field = form_fields.BuildIdsField(required=False)
        field.clean('asd')

    @raises(ValidationError)
    def test_build_ids_field_validation_error_list(self):
        field = form_fields.BuildIdsField(required=False)
        field.clean('12, 13, 14e')
