import datetime
from nose.tools import eq_, assert_raises

from django.utils.timezone import utc
from django.forms import ValidationError

from crashstats.base.tests.testbase import TestCase
from crashstats.supersearch import form_fields


class TestFormFields(TestCase):

    def test_integer_field(self):
        field = form_fields.IntegerField()
        cleaned_value = field.clean(['>13'])
        eq_(cleaned_value, [13])
        eq_(field.prefixed_value, ['>13'])

        # With a ! prefix.
        cleaned_value = field.clean(['!13'])
        eq_(cleaned_value, [13])
        eq_(field.prefixed_value, ['!13'])

    def test_datetime_field(self):
        field = form_fields.DateTimeField()
        cleaned_value = field.clean(['>12/31/2012 10:20:30'])
        dt = datetime.datetime(2012, 12, 31, 10, 20, 30)
        dt = dt.replace(tzinfo=utc)
        eq_(cleaned_value, [dt])
        eq_(field.prefixed_value, ['>2012-12-31T10:20:30+00:00'])

        field = form_fields.DateTimeField()
        cleaned_value = field.clean(['>=2012-12-31'])
        dt = datetime.datetime(2012, 12, 31)
        dt = dt.replace(tzinfo=utc)
        eq_(cleaned_value, [dt])
        eq_(field.prefixed_value, ['>=2012-12-31T00:00:00+00:00'])

        field = form_fields.DateTimeField()
        cleaned_value = field.clean(['>=2012-12-31T01:02:03+00:00'])
        dt = datetime.datetime(2012, 12, 31, 1, 2, 3)
        dt = dt.replace(tzinfo=utc)
        eq_(cleaned_value, [dt])
        eq_(field.prefixed_value, ['>=2012-12-31T01:02:03+00:00'])

    def test_several_fields(self):
        field1 = form_fields.DateTimeField()
        cleaned_value1 = field1.clean(['>12/31/2012 10:20:30'])

        field2 = form_fields.DateTimeField()
        cleaned_value2 = field2.clean(['<12/31/2012 10:20:40'])

        dt = datetime.datetime(2012, 12, 31, 10, 20, 30)
        dt = dt.replace(tzinfo=utc)
        eq_(cleaned_value1, [dt])
        eq_(field1.prefixed_value, ['>2012-12-31T10:20:30+00:00'])

        dt = datetime.datetime(2012, 12, 31, 10, 20, 40)
        dt = dt.replace(tzinfo=utc)
        eq_(cleaned_value2, [dt])
        eq_(field2.prefixed_value, ['<2012-12-31T10:20:40+00:00'])

        eq_(field1.operator, '>')
        eq_(field2.operator, '<')

    def test_several_fields_illogically_integerfield(self):
        field = form_fields.IntegerField()
        assert_raises(
            ValidationError,
            field.clean,
            ['>10', '<10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['<10', '>10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['<10', '>=10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['<=10', '>10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['<10', '<10']
        )

    def test_several_fields_illogically_datetimefield(self):
        field = form_fields.DateTimeField()
        assert_raises(
            ValidationError,
            field.clean,
            ['>2016-08-10', '<2016-08-10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['<2016-08-10', '<2016-08-10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['>=2016-08-10', '<2016-08-10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['>2016-08-10', '<=2016-08-10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['>=2016-08-10', '<=2016-08-09']
        )
        # but note, this should work!
        field.clean(['>=2016-08-10', '<=2016-08-10'])

        # any use of the equal sign and a less or greater than
        assert_raises(
            ValidationError,
            field.clean,
            ['=2016-08-10', '<2016-08-10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['=2016-08-10', '>2016-08-10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['>2016-08-10', '=2016-08-10']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['<2016-08-10', '=2016-08-10']
        )

        # more than two fields
        assert_raises(
            ValidationError,
            field.clean,
            ['>2016-08-01', '<=2016-08-02', '>=2016-08-02']
        )
        assert_raises(
            ValidationError,
            field.clean,
            ['<2016-08-01', '<2016-08-02', '<2016-08-03']
        )
