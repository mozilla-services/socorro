import datetime

from django.contrib.auth.models import User, Group, Permission
from django import forms
from django.utils import timezone

from crashstats.crashstats.forms import BaseForm, BaseModelForm
from crashstats.tokens.models import Token


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


class FilterEventsForm(BaseForm):

    user = forms.CharField(required=False)
    action = forms.CharField(required=False)


class FilterAPITokensForm(BaseForm):

    user = forms.CharField(required=False)
    key = forms.CharField(required=False)
    expired = forms.ChoiceField(required=False, choices=(
        ('', 'All'),
        ('yes', 'Expired'),
        ('no', 'Not expired'),
    ))


class APITokenForm(BaseModelForm):

    user = forms.CharField(required=True)
    expires = forms.ChoiceField(required=True)

    class Meta:
        model = Token
        fields = ('user', 'expires', 'notes', 'permissions')

    def __init__(self, *args, **kwargs):
        self.possible_permissions = kwargs.pop('possible_permissions', [])
        expires_choices = kwargs.pop('expires_choices', [])
        super(APITokenForm, self).__init__(*args, **kwargs)
        self.fields['permissions'].choices = (
            (x.pk, x.name) for x in self.possible_permissions
        )
        self.fields['user'].widget = forms.widgets.TextInput()
        self.fields['user'].label = 'User (by email)'
        self.fields['expires'].choices = expires_choices

    def clean_user(self):
        value = self.cleaned_data['user']
        try:
            user = User.objects.get(email__istartswith=value.strip())
            if not user.is_active:
                raise forms.ValidationError(
                    '%s is not an active user' % user.email
                )
            return user
        except User.DoesNotExist:
            raise forms.ValidationError('No user found by that email address')
        except User.MultipleObjectsReturned:
            raise forms.ValidationError(
                'More than one user found by that email address'
            )

    def clean_expires(self):
        value = self.cleaned_data['expires']
        return timezone.now() + datetime.timedelta(days=int(value))

    def clean(self):
        cleaned_data = super(APITokenForm, self).clean()
        if 'user' in cleaned_data and 'permissions' in cleaned_data:
            user = cleaned_data['user']
            for permission in cleaned_data['permissions']:
                if not user.has_perm('crashstats.' + permission.codename):
                    only = [
                        p.name for p in self.possible_permissions
                        if user.has_perm('crashstats.' + p.codename)
                    ]
                    msg = (
                        '%s does not have the permission "%s". ' % (
                            user.email,
                            permission.name
                        )
                    )
                    if only:
                        msg += ' Only permissions possible are: '
                        msg += ', '.join(only)
                    else:
                        msg += ' %s has no permissions!' % user.email
                    raise forms.ValidationError(msg)
        return cleaned_data


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
