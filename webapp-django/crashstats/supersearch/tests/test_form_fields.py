# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import pytest

from django.utils.timezone import utc
from django.forms import ValidationError

from crashstats.supersearch import form_fields


class TestFormFields:
    def test_integer_field(self):
        field = form_fields.IntegerField()
        cleaned_value = field.clean([">13"])
        assert cleaned_value == [13]
        assert field.prefixed_value == [">13"]

        # With a ! prefix.
        cleaned_value = field.clean(["!13"])
        assert cleaned_value == [13]
        assert field.prefixed_value == ["!13"]

    def test_datetime_field(self):
        field = form_fields.DateTimeField()
        cleaned_value = field.clean([">12/31/2012 10:20:30"])
        dt = datetime.datetime(2012, 12, 31, 10, 20, 30)
        dt = dt.replace(tzinfo=utc)
        assert cleaned_value == [dt]
        assert field.prefixed_value == [">2012-12-31T10:20:30+00:00"]

        field = form_fields.DateTimeField()
        cleaned_value = field.clean([">=2012-12-31"])
        dt = datetime.datetime(2012, 12, 31)
        dt = dt.replace(tzinfo=utc)
        assert cleaned_value == [dt]
        assert field.prefixed_value == [">=2012-12-31T00:00:00+00:00"]

        field = form_fields.DateTimeField()
        cleaned_value = field.clean([">=2012-12-31T01:02:03+00:00"])
        dt = datetime.datetime(2012, 12, 31, 1, 2, 3)
        dt = dt.replace(tzinfo=utc)
        assert cleaned_value == [dt]
        assert field.prefixed_value == [">=2012-12-31T01:02:03+00:00"]

    def test_several_fields(self):
        field1 = form_fields.DateTimeField()
        cleaned_value1 = field1.clean([">12/31/2012 10:20:30"])

        field2 = form_fields.DateTimeField()
        cleaned_value2 = field2.clean(["<12/31/2012 10:20:40"])

        dt = datetime.datetime(2012, 12, 31, 10, 20, 30)
        dt = dt.replace(tzinfo=utc)
        assert cleaned_value1 == [dt]
        assert field1.prefixed_value == [">2012-12-31T10:20:30+00:00"]

        dt = datetime.datetime(2012, 12, 31, 10, 20, 40)
        dt = dt.replace(tzinfo=utc)
        assert cleaned_value2 == [dt]
        assert field2.prefixed_value == ["<2012-12-31T10:20:40+00:00"]

        assert field1.operator == ">"
        assert field2.operator == "<"

    def test_several_fields_illogically_integerfield(self):
        field = form_fields.IntegerField()
        with pytest.raises(ValidationError):
            field.clean([">10", "<10"])
        with pytest.raises(ValidationError):
            field.clean(["<10", ">10"])
        with pytest.raises(ValidationError):
            field.clean(["<10", ">=10"])
        with pytest.raises(ValidationError):
            field.clean(["<=10", ">10"])
        with pytest.raises(ValidationError):
            field.clean(["<10", "<10"])

    def test_several_fields_illogically_datetimefield(self):
        field = form_fields.DateTimeField()
        with pytest.raises(ValidationError):
            field.clean([">2016-08-10", "<2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean(["<2016-08-10", "<2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean([">=2016-08-10", "<2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean([">2016-08-10", "<=2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean([">=2016-08-10", "<=2016-08-09"])

        # but note, this should work!
        field.clean([">=2016-08-10", "<=2016-08-10"])

        # any use of the equal sign and a less or greater than
        with pytest.raises(ValidationError):
            field.clean(["=2016-08-10", "<2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean(["=2016-08-10", ">2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean([">2016-08-10", "=2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean(["<2016-08-10", "=2016-08-10"])

        # more than two fields
        with pytest.raises(ValidationError):
            field.clean([">2016-08-01", "<=2016-08-02", ">=2016-08-02"])
        with pytest.raises(ValidationError):
            field.clean(["<2016-08-01", "<2016-08-02", "<2016-08-03"])

    def test_boolean_field(self):
        field = form_fields.BooleanField(required=False)
        # If the input is None, leave it as None
        cleaned_value = field.clean(None)
        assert cleaned_value is None

        # The list of known truthy strings
        for value in form_fields.BooleanField.truthy_strings:
            cleaned_value = field.clean(value)
            assert cleaned_value == "__true__"
        # But it's also case insensitive, so check that it still works
        for value in form_fields.BooleanField.truthy_strings:
            cleaned_value = field.clean(value.upper())  # note
            assert cleaned_value == "__true__"

        # Any other string that is NOT in form_fields.BooleanField.truthy_strings
        # should return `!__true__`
        cleaned_value = field.clean("FALSE")
        assert cleaned_value == "!__true__"
        cleaned_value = field.clean("anything")
        assert cleaned_value == "!__true__"
        # But not choke on non-ascii strings
        cleaned_value = field.clean("Nöö")
        assert cleaned_value == "!__true__"
