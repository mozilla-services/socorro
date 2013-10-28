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
