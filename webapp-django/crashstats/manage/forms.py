from django.contrib.auth.models import Permission
from django import forms

from crashstats.crashstats.forms import BaseForm


class FilterSymbolsUploadsForm(BaseForm):

    email = forms.CharField(required=False)
    filename = forms.CharField(required=False)
    content = forms.CharField(required=False)


class GraphicsDeviceForm(BaseForm):

    vendor_hex = forms.CharField(max_length=100)
    adapter_hex = forms.CharField(max_length=100)
    vendor_name = forms.CharField(max_length=100, required=False)
    adapter_name = forms.CharField(max_length=100, required=False)


class GraphicsDeviceLookupForm(BaseForm):

    vendor_hex = forms.CharField(max_length=100)
    adapter_hex = forms.CharField(max_length=100)


class GraphicsDeviceUploadForm(BaseForm):

    file = forms.FileField()
    database = forms.ChoiceField(
        choices=(
            ('pcidatabase.com', 'PCIDatabase.com'),
            ('pci.ids', 'The PCI ID Repository (https://pci-ids.ucw.cz/)'),
        )
    )


class SuperSearchFieldForm(BaseForm):

    name = forms.CharField()
    in_database_name = forms.CharField()
    namespace = forms.CharField(required=False)
    description = forms.CharField(required=False)
    query_type = forms.CharField(required=False)
    data_validation_type = forms.CharField(required=False)
    permissions_needed = forms.CharField(required=False)
    form_field_choices = forms.CharField(required=False)
    is_exposed = forms.BooleanField(required=False)
    is_returned = forms.BooleanField(required=False)
    is_mandatory = forms.BooleanField(required=False)
    has_full_version = forms.BooleanField(required=False)
    storage_mapping = forms.CharField(required=False)

    def clean_permissions_needed(self):
        """Removes unknown permissions from the list of permissions.

        This is needed because the html form will send an empty string by
        default. We don't want that to cause an error, but don't want it to
        be put in the database either.
        """
        value = self.cleaned_data['permissions_needed']
        values = [x.strip() for x in value.split(',')]

        perms = Permission.objects.filter(content_type__model='')
        all_permissions = [
            'crashstats.' + x.codename for x in perms
        ]

        return [x for x in values if x in all_permissions]

    def clean_form_field_choices(self):
        """Removes empty values from the list of choices.

        This is needed because the html form will send an empty string by
        default. We don't want that to cause an error, but don't want it to
        be put in the database either.
        """
        return [
            x.strip()
            for x in self.cleaned_data['form_field_choices'].split(',')
            if x.strip()
        ]


class CrashMeNowForm(BaseForm):

    exception_type = forms.ChoiceField(
        choices=(
            ('NameError', 'NameError'),
            ('ValueError', 'ValueError'),
            ('AttributeError', 'AttributeError'),
        )
    )
    exception_value = forms.CharField()
