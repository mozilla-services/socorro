from django import forms

from crashstats.crashstats.form_fields import SignatureField
from crashstats.supersearch import form_fields


ADMIN_RESTRICTED_FIELDS = {
    'email': form_fields.StringField(required=False),
    'url': form_fields.StringField(required=False),
}


class SearchForm(forms.Form):
    '''Handle the data populating the search form. '''

    address = forms.CharField(required=False)
    app_notes = forms.CharField(required=False)
    build_id = form_fields.IntegerField(required=False)
    cpu_info = form_fields.StringField(required=False)
    cpu_name = forms.CharField(required=False)
    date = form_fields.DateTimeField(required=False)
    distributor = forms.CharField(required=False)
    distributor_version = forms.CharField(required=False)
    dump = form_fields.StringField(required=False)
    flash_version = forms.CharField(required=False)
    install_age = form_fields.IntegerField(required=False)
    java_stack_trace = forms.CharField(required=False)
    last_crash = form_fields.IntegerField(required=False)
    platform = forms.MultipleChoiceField(required=False)
    platform_version = forms.CharField(required=False)
    plugin_name = forms.CharField(required=False)
    plugin_filename = forms.CharField(required=False)
    plugin_version = forms.CharField(required=False)
    processor_notes = forms.CharField(required=False)
    product = forms.MultipleChoiceField(required=False)
    productid = forms.CharField(required=False)
    reason = form_fields.StringField(required=False)
    release_channel = forms.CharField(required=False)
    signature = SignatureField(required=False)  # CharField
    topmost_filenames = forms.CharField(required=False)
    uptime = form_fields.IntegerField(required=False)
    user_comments = forms.CharField(required=False)
    version = forms.MultipleChoiceField(required=False)
    winsock_lsp = forms.CharField(required=False)

    # TODO: This doesn't work and needs to be fixed.
    # Pending on https://bugzilla.mozilla.org/show_bug.cgi?id=919559
    # process_type = forms.ChoiceField(
    #     required=False,
    #     choices=make_choices(settings.PROCESS_TYPES)
    # )
    # hang_type = forms.ChoiceField(
    #     required=False,
    #     choices=make_choices(settings.HANG_TYPES)
    # )

    def __init__(
        self,
        current_products,
        current_versions,
        current_platforms,
        admin_mode,
        *args,
        **kwargs
    ):
        super(self.__class__, self).__init__(*args, **kwargs)

        # Default values
        platforms = [(x['name'], x['name']) for x in current_platforms]
        products = [(x, x) for x in current_products]
        versions = [
            (v['version'], v['version']) for v in current_versions
        ]

        self.fields['product'].choices = products
        self.fields['version'].choices = versions
        self.fields['platform'].choices = platforms

        if admin_mode:
            self.fields.update(ADMIN_RESTRICTED_FIELDS)

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

            if field_type == 'int':
                value_type = 'number'
            elif field_type == 'date':
                value_type = 'date'
            elif isinstance(field, (SignatureField, form_fields.StringField)):
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
