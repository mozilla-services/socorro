from django.contrib.auth.models import ContentType, Permission

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.manage import forms


class TestForms(DjangoTestCase):

    def test_supersearch_field_form(self):
        # Test field choices are correctly separated.
        form = forms.SuperSearchFieldForm({
            'name': 'foo',
            'in_database_name': 'foo',
            'form_field_choices': 'a, b,c , ',
        })
        assert form.is_valid()
        assert form.cleaned_data['form_field_choices'] == ['a', 'b', 'c']

        # Test permissions are correctly filtered.
        appname = 'crashstats'
        ct, __ = ContentType.objects.get_or_create(
            model='',
            app_label=appname,
        )
        permission, __ = Permission.objects.get_or_create(
            codename='view_foobar',
            name='View Foo and Bar',
            content_type=ct
        )

        form = forms.SuperSearchFieldForm({
            'name': 'foo',
            'in_database_name': 'foo',
            'permissions_needed': 'crashstats.view_foobar, crashstats.unknown',
        })
        assert form.is_valid()
        assert form.cleaned_data['permissions_needed'] == ['crashstats.view_foobar']
