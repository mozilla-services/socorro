from django import forms
from django.conf import settings

from crashstats.crashstats.form_fields import SignatureField
from crashstats.crashstats.forms import make_choices
from crashstats.supersearch import form_fields


class SearchForm(forms.Form):
    '''Handle the data populating the search form. '''

    signature = SignatureField(required=False)  # CharField
    product = forms.MultipleChoiceField(required=False)
    version = forms.MultipleChoiceField(required=False)
    platform = forms.MultipleChoiceField(required=False)
    date = form_fields.DateTimeField(required=False)
    reason = forms.CharField(required=False)
    release_channel = forms.CharField(required=False)
    build_id = form_fields.IntegerField(required=False)

    process_type = forms.ChoiceField(
        required=False,
        choices=make_choices(settings.PROCESS_TYPES)
    )
    hang_type = forms.ChoiceField(
        required=False,
        choices=make_choices(settings.HANG_TYPES)
    )

    def __init__(self, current_products, current_versions, current_platforms,
                 *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        # Default values
        platforms = [(x['name'], x['name']) for x in current_platforms]
        products = [(x, x) for x in current_products]
        versions = [('ALL:ALL', 'ALL:ALL')]
        versions.extend([
            (v['version'], v['version']) for v in current_versions
        ])

        self.fields['product'].choices = products
        self.fields['version'].choices = versions
        self.fields['platform'].choices = platforms

    def get_fields_list(self):
        '''Return a dictionary describing the fields, to pass to the
        dynamic_form.js library. '''
        fields_list = {}

        for field_name in self.fields:
            field = self.fields[field_name]
            try:
                values = [x[0] for x in field.choices]
            except AttributeError:
                values = None
            multiple = True
            extensible = True

            if isinstance(field, (forms.DateField, forms.DateTimeField)):
                field_type = 'date'
            elif isinstance(field, forms.IntegerField):
                field_type = 'int'
            else:
                field_type = 'string'

            if field_type in ('int', 'date'):
                value_type = 'range'
            elif isinstance(field, SignatureField):
                value_type = 'string'
            else:
                value_type = 'enum'

            fields_list[field_name] = {
                'name': field_name.replace('_', ' '),
                'type': field_type,
                'valueType': value_type,
                'values': values,
                'multiple': multiple,
                'extensible': extensible,
            }

        return fields_list
