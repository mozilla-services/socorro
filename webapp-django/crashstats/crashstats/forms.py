from django import forms
import six

from crashstats.crashstats import form_fields


class _BaseForm(object):
    def __init__(self, *args, **kwargs):
        super(_BaseForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            if isinstance(self.fields[field], forms.DateTimeField):
                attributes = dict(self.fields[field].__dict__)
                attributes.pop('creation_counter')
                self.fields[field] = form_fields.CarefulDateTimeField(
                    **attributes
                )
            elif isinstance(self.fields[field], forms.DateField):
                attributes = dict(self.fields[field].__dict__)
                attributes.pop('creation_counter')
                self.fields[field] = form_fields.CarefulDateField(
                    **attributes
                )

    def clean(self):
        cleaned_data = super(_BaseForm, self).clean()
        for field in cleaned_data:
            if isinstance(cleaned_data[field], six.string_types):
                cleaned_data[field] = (
                    cleaned_data[field].replace('\r\n', '\n')
                    .replace(u'\u2018', "'").replace(u'\u2019', "'").strip())

        return cleaned_data


class BaseModelForm(_BaseForm, forms.ModelForm):
    pass


class BaseForm(_BaseForm, forms.Form):
    pass


class Html5DateInput(forms.DateInput):
    input_type = 'date'


class BugInfoForm(BaseForm):

    bug_ids = forms.CharField(required=True)

    def clean_bug_ids(self):
        value = self.cleaned_data['bug_ids']
        bug_ids = [x.strip() for x in value.split(',') if x.strip()]
        nasty_bug_ids = [x for x in bug_ids if not x.isdigit()]
        if nasty_bug_ids:
            # all were invalid
            raise forms.ValidationError(
                'Not valid bug_ids %s' %
                (', '.join(repr(x) for x in nasty_bug_ids))
            )
        return bug_ids
