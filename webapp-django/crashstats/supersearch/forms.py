from django import forms

from crashstats.supersearch import form_fields


PII_RESTRICTED_FIELDS = {
    'email': form_fields.StringField(required=False),
    'url': form_fields.StringField(required=False),
}


class SearchForm(forms.Form):
    '''Handle the data populating the search form. '''

    # Processed crash fields.
    address = form_fields.StringField(required=False)
    app_notes = form_fields.MultipleValueField(required=False)
    build_id = form_fields.IntegerField(required=False)
    cpu_info = form_fields.StringField(required=False)
    cpu_name = form_fields.MultipleValueField(required=False)
    date = form_fields.DateTimeField(required=False)
    distributor = form_fields.MultipleValueField(required=False)
    distributor_version = form_fields.MultipleValueField(required=False)
    dump = form_fields.StringField(required=False)
    flash_version = form_fields.MultipleValueField(required=False)
    install_age = form_fields.IntegerField(required=False)
    java_stack_trace = form_fields.MultipleValueField(required=False)
    last_crash = form_fields.IntegerField(required=False)
    platform = form_fields.MultipleValueField(required=False)
    platform_version = form_fields.MultipleValueField(required=False)
    plugin_name = form_fields.MultipleValueField(required=False)
    plugin_filename = form_fields.MultipleValueField(required=False)
    plugin_version = form_fields.MultipleValueField(required=False)
    processor_notes = form_fields.MultipleValueField(required=False)
    product = form_fields.MultipleValueField(required=False)
    productid = form_fields.MultipleValueField(required=False)
    reason = form_fields.StringField(required=False)
    release_channel = form_fields.MultipleValueField(required=False)
    signature = form_fields.StringField(required=False)
    topmost_filenames = form_fields.MultipleValueField(required=False)
    uptime = form_fields.IntegerField(required=False)
    user_comments = form_fields.StringField(required=False)
    version = form_fields.MultipleValueField(required=False)
    winsock_lsp = form_fields.MultipleValueField(required=False)

    # Raw crash fields.
    accessibility = form_fields.BooleanField(required=False)
    additional_minidumps = form_fields.MultipleValueField(required=False)
    adapter_device_id = form_fields.MultipleValueField(required=False)
    adapter_vendor_id = form_fields.MultipleValueField(required=False)
    android_board = form_fields.MultipleValueField(required=False)
    android_brand = form_fields.MultipleValueField(required=False)
    android_cpu_abi = form_fields.MultipleValueField(required=False)
    android_cpu_abi2 = form_fields.MultipleValueField(required=False)
    android_device = form_fields.MultipleValueField(required=False)
    android_display = form_fields.MultipleValueField(required=False)
    android_fingerprint = form_fields.MultipleValueField(required=False)
    android_hardware = form_fields.MultipleValueField(required=False)
    android_manufacturer = form_fields.MultipleValueField(required=False)
    android_model = form_fields.StringField(required=False)
    android_version = form_fields.MultipleValueField(required=False)
    async_shutdown_timeout = form_fields.MultipleValueField(required=False)
    available_page_file = form_fields.IntegerField(required=False)
    available_physical_memory = form_fields.IntegerField(required=False)
    available_virtual_memory = form_fields.IntegerField(required=False)
    b2g_os_version = form_fields.MultipleValueField(required=False)
    bios_manufacturer = form_fields.MultipleValueField(required=False)
    cpu_usage_flash_process1 = form_fields.IntegerField(required=False)
    cpu_usage_flash_process2 = form_fields.IntegerField(required=False)
    em_check_compatibility = form_fields.BooleanField(required=False)
    frame_poison_base = form_fields.MultipleValueField(required=False)
    frame_poison_size = form_fields.IntegerField(required=False)
    is_garbage_collecting = form_fields.BooleanField(required=False)
    min_arm_version = form_fields.MultipleValueField(required=False)
    number_of_processors = form_fields.IntegerField(required=False)
    oom_allocation_size = form_fields.IntegerField(required=False)
    plugin_cpu_usage = form_fields.IntegerField(required=False)
    plugin_hang = form_fields.BooleanField(required=False)
    plugin_hang_ui_duration = form_fields.IntegerField(required=False)
    startup_time = form_fields.IntegerField(required=False)
    system_memory_use_percentage = form_fields.IntegerField(required=False)
    throttleable = form_fields.BooleanField(required=False)
    throttle_rate = form_fields.IntegerField(required=False)
    theme = form_fields.MultipleValueField(required=False)
    total_virtual_memory = form_fields.IntegerField(required=False)
    useragent_locale = form_fields.MultipleValueField(required=False)
    vendor = form_fields.MultipleValueField(required=False)

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
        pii_mode,
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

        if pii_mode:
            self.fields.update(PII_RESTRICTED_FIELDS)

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
