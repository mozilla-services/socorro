import json

from django import forms

from . import form_fields


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

        # Generate the list of fields.
        for field_data in all_fields.values():
            if (
                field_data['form_field_type'] is None or
                not field_data['is_exposed']
            ):
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
                    continue

            field_type = getattr(
                form_fields,
                field_data['form_field_type']
            )

            field_obj = field_type(
                required=field_data['is_mandatory']
            )

            if field_data['form_field_choices']:
                field_obj.choices = make_restricted_choices(
                    field_data['form_field_choices'], ['any', 'all']
                )

            self.fields[field_data['name']] = field_obj

        # Default values loaded from a database.
        if 'product' in self.fields:
            products = [(x, x) for x in current_products]
            self.fields['product'].choices = products
        if 'version' in self.fields:
            versions = [
                (v['version'], v['version']) for v in current_versions
            ]
            self.fields['version'].choices = versions
        if 'platform' in self.fields:
            platforms = [(x['name'], x['name']) for x in current_platforms]
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
            elif isinstance(field, form_fields.BooleanField):
                field_type = 'bool'
            else:
                field_type = 'string'

            if field_type == 'int':
                value_type = 'number'
            elif field_type == 'date':
                value_type = 'date'
            elif field_type == 'bool':
                value_type = 'bool'
            elif isinstance(field, form_fields.StringField):
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


class QueryForm(forms.Form):
    query = forms.CharField()
    indices = form_fields.MultipleValueField(required=False)

    def clean_query(self):
        try:
            return json.loads(self.cleaned_data['query'])
        except ValueError as x:
            raise forms.ValidationError(x)
