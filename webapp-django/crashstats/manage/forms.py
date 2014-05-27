from django.contrib.auth.models import User, Group, Permission
from django import forms

from crashstats.crashstats.forms import BaseForm, BaseModelForm
from crashstats.supersearch import form_fields


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
    permissions_needed = form_fields.MultipleValueField(required=False)
    form_field_type = forms.CharField(required=False)
    form_field_choices = form_fields.MultipleValueField(required=False)
    is_exposed = forms.BooleanField(required=False)
    is_returned = forms.BooleanField(required=False)
    is_mandatory = forms.BooleanField(required=False)
    has_full_version = forms.BooleanField(required=False)
    storage_mapping = forms.CharField(required=False)
