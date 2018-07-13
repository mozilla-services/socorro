from past.builtins import basestring

from django import forms
from . import form_fields


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
            if isinstance(cleaned_data[field], basestring):
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


def make_choices(seq):
    return [(x, x) for x in seq]


class GraphicsReportForm(BaseForm):

    date = forms.DateField()
    product = forms.CharField(required=False)


class ExploitabilityReportForm(BaseForm):

    product = forms.ChoiceField()
    version = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        active_versions = kwargs.pop('active_versions')
        self.available_products = dict(
            (p, [x['version'] for x in v])
            for p, v in active_versions.items()
        )
        super(ExploitabilityReportForm, self).__init__(*args, **kwargs)

        self.fields['product'].choices = [
            (k, k) for k in self.available_products
        ]
        all_versions = []
        [all_versions.extend(v) for v in self.available_products.values()]

        self.fields['version'].choices = [
            (v, v) for v in set(
                x for line in self.available_products.values() for x in line
            )
        ]

    def clean(self):
        cleaned_data = super(ExploitabilityReportForm, self).clean()
        if 'product' in cleaned_data and 'version' in cleaned_data:
            product = cleaned_data['product']
            version = cleaned_data['version']
            if version and version not in self.available_products[product]:
                raise forms.ValidationError(
                    '{} is not an available version for {}'.format(
                        version,
                        product,
                    )
                )
        return cleaned_data
