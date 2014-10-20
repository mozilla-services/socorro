import json

from django import forms

from . import form_fields


TYPE_TO_FIELD_MAPPING = {
    'enum': form_fields.MultipleValueField,
    'string': form_fields.StringField,
    'number': form_fields.IntegerField,
    'bool': form_fields.BooleanField,
    'flag': form_fields.StringField,
    'date': form_fields.DateTimeField,
}


def make_restricted_choices(sequence, exclude=None):
    if exclude is None:
        exclude = []
    return [(x, x) for x in sequence if x not in exclude]


class SearchForm(forms.Form):
    '''Handle the data populating the search form. '''

    def __init__(
        self,
        all_fields,
        current_products,
        current_versions,
        current_platforms,
        user,
        *args,
        **kwargs
    ):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.all_fields = all_fields.copy()

        # Default values loaded from a database.
        if 'product' in self.all_fields:
            self.all_fields['product']['form_field_choices'] = \
                current_products.keys()

        if 'version' in self.all_fields:
            self.all_fields['version']['form_field_choices'] = [
                x['version'] for x in current_versions
            ]

        if 'platform' in self.all_fields:
            self.all_fields['platform']['form_field_choices'] = [
                x['name'] for x in current_platforms
            ]

        # Generate the list of fields.
        for field_name, field_data in all_fields.iteritems():
            if not field_data['is_exposed']:
                del self.all_fields[field_name]
                continue

            if field_data['permissions_needed']:
                user_has_permissions = True
                for permission in field_data['permissions_needed']:
                    if not user.has_perm(permission):
                        user_has_permissions = False
                        break

                if not user_has_permissions:
                    # The user is lacking one of the permissions needed
                    # for this field, so we do not add it to the list
                    # of fields.
                    del self.all_fields[field_name]
                    continue

            field_type = TYPE_TO_FIELD_MAPPING.get(
                field_data['query_type'],
                form_fields.MultipleValueField
            )

            field_obj = field_type(
                required=field_data['is_mandatory']
            )

            if field_data['form_field_choices']:
                field_obj.choices = make_restricted_choices(
                    field_data['form_field_choices'], ['any', 'all']
                )

            self.fields[field_name] = field_obj

    def get_fields_list(self, exclude=None):
        '''Return a dictionary describing the fields, to pass to the
        dynamic_form.js library. '''
        fields_list = {}

        if exclude is None:
            exclude = []

        for field in self.all_fields.itervalues():
            if field['name'] in exclude:
                continue

            fields_list[field['name']] = {
                'name': field['name'].replace('_', ' '),
                'valueType': field['query_type'],
                'values': field['form_field_choices'],
                'multiple': True,
                'extensible': True,
            }

        return fields_list


class QueryForm(forms.Form):
    query = forms.CharField()
    indices = form_fields.MultipleValueField(required=False)

    def clean_query(self):
        try:
            return json.loads(self.cleaned_data['query'])
        except ValueError as x:
            raise forms.ValidationError(x)
