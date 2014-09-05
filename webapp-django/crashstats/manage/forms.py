import datetime

from django.contrib.auth.models import User, Group, Permission
from django import forms

from crashstats.crashstats.forms import BaseForm, BaseModelForm


class SkipListForm(BaseForm):
    category = forms.CharField(required=True)
    rule = forms.CharField(required=True)


class EditUserForm(BaseModelForm):

    class Meta:
        model = User
        fields = ('is_superuser', 'is_active', 'groups')


class FilterUsersForm(BaseForm):

    email = forms.CharField(required=False)
    superuser = forms.CharField(required=False)
    active = forms.CharField(required=False)
    group = forms.ModelChoiceField(queryset=Group.objects, required=False)

    def clean_superuser(self):
        value = self.cleaned_data['superuser']
        return {'0': None, '1': True, '-1': False}.get(value)

    def clean_active(self):
        value = self.cleaned_data['active']
        return {'0': None, '1': True, '-1': False}.get(value)


class GroupForm(BaseModelForm):

    class Meta:
        model = Group

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields['permissions'].choices = [
            (x.pk, x.name) for x in
            Permission.objects
            .filter(content_type__model='')
        ]

    def clean_permissions(self):
        value = self.cleaned_data['permissions']
        if not value:
            raise forms.ValidationError('Must select at least one')
        return value


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


class ProductForm(BaseForm):

    product = forms.CharField()
    initial_version = forms.CharField()

    def __init__(self, *args, **kwargs):
        self.existing_products = kwargs.pop('existing_products', [])
        super(ProductForm, self).__init__(*args, **kwargs)

    def clean_product(self):
        value = self.cleaned_data['product']
        if value in self.existing_products:
            raise forms.ValidationError('%s already exists' % (value,))
        return value


class ReleaseForm(BaseForm):

    product = forms.CharField()
    version = forms.CharField()
    update_channel = forms.CharField()
    build_id = forms.CharField(
        help_text='Must start in the format YYYYMMDD and this date to be '
                  'within the last 30 days.'
    )
    platform = forms.ChoiceField()
    beta_number = forms.CharField(required=False)
    release_channel = forms.CharField()
    throttle = forms.CharField()

    def __init__(self, *args, **kwargs):
        self.platforms = kwargs.pop('platforms', [])
        super(ReleaseForm, self).__init__(*args, **kwargs)
        self.fields['platform'].choices = [
            (x, x) for x in self.platforms
        ]

    def clean_throttle(self):
        value = self.cleaned_data['throttle']
        try:
            return int(value)
        except ValueError:
            raise forms.ValidationError('not a number')

    def clean_beta_number(self):
        value = self.cleaned_data['beta_number']
        if not value.strip():
            # that's ok
            return None
        try:
            return int(value)
        except ValueError:
            raise forms.ValidationError('not a number')

    def clean_build_id(self):
        value = self.cleaned_data['build_id']
        try:
            date = datetime.datetime.strptime(value[:8], '%Y%m%d')
            now = datetime.datetime.utcnow()
            if (now - date) > datetime.timedelta(days=30):
                raise forms.ValidationError('Date older than 30 days')
            return value
        except ValueError:
            raise forms.ValidationError('Must start with YYYYMMDD')
