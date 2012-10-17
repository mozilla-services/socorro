import datetime
from django import forms
from django.conf import settings


class BugInfoForm(forms.Form):

    bug_ids = forms.CharField(required=True)
    include_fields = forms.CharField(required=True)

    def clean_bug_ids(self):
        value = self.cleaned_data['bug_ids']
        return [x.strip() for x in value.split(',') if x.strip()]

    def clean_include_fields(self):
        value = self.cleaned_data['include_fields']
        return [x.strip() for x in value.split(',') if x.strip()]


class ReportListForm(forms.Form):

    range_value = forms.IntegerField(required=True)
    signature = forms.CharField(required=False)
    version = forms.CharField(required=False)
    date = forms.DateTimeField(required=False)

    def clean_date(self):
        value = self.cleaned_data['date']
        if not value:
            value = datetime.datetime.utcnow()
        return value

    def clean_range_value(self):
        value = self.cleaned_data['range_value']
        if not value:
            value = 1
        elif value < 0:
            raise forms.ValidationError(
                'range_value must be a positive integer'
            )
        return value


class QueryForm(ReportListForm):

    query = forms.CharField(required=False)
    product = forms.MultipleChoiceField(required=False)
    version = forms.MultipleChoiceField(required=False)
    platform = forms.MultipleChoiceField(required=False)
    range_unit = forms.CharField(required=False)
    range_value = forms.IntegerField(required=False)
    query_type = forms.CharField(required=False)
    reason = forms.CharField(required=False)
    build_id = forms.CharField(required=False)
    process_type = forms.CharField(required=False)
    hang_type = forms.CharField(required=False)
    plugin_field = forms.CharField(required=False)
    plugin_query_type = forms.CharField(required=False)
    plugin_query = forms.CharField(required=False)

    def __init__(self, current_products, current_verisons, current_platforms,
                 *args, **kwargs):
        super(QueryForm, self).__init__(*args, **kwargs)

        # Default values
        platforms = [(x['code'], x['name']) for x in current_platforms]
        products = [(x, x) for x in current_products]
        versions = [('ALL:ALL', 'ALL:ALL')]
        for version in current_verisons:
            v = '%s:%s' % (version['product'], version['version'])
            versions.append((v, v))

        self.fields['product'].choices = products
        self.fields['version'].choices = versions
        self.fields['platform'].choices = platforms

    def clean_product(self):
        return self.cleaned_data['product'] or [settings.DEFAULT_PRODUCT]

    def clean_range_unit(self):
        return self.cleaned_data['range_unit'] or 'weeks'

    def clean_query_type(self):
        types = settings.QUERY_TYPES
        value = self.cleaned_data['query_type']
        if not value:
            value = types[0]
        else:
            value = self._map_query_types(value)
            if value not in types:
                raise forms.ValidationError(
                    'query_type must be one of %s' % str(types)
                )
        return value

    def clean_process_type(self):
        return self.cleaned_data['process_type'] or 'any'

    def clean_hang_type(self):
        return self.cleaned_data['hang_type'] or 'any'

    def clean_plugin_field(self):
        return self.cleaned_data['plugin_field'] or 'filename'

    def clean_plugin_query_type(self):
        types = settings.QUERY_TYPES
        value = self.cleaned_data['plugin_query_type']
        if not value:
            value = types[0]
        else:
            value = self._map_query_types(value)
            if value not in types:
                raise forms.ValidationError(
                    'plugin_query_type must be one of %s' % str(types)
                )
        return value

    def _map_query_types(self, query_type):
        """Return a query_type that is now recognize by the system. This is
        for backward compatibility with the PHP app. """
        return {
            'exact': 'is_exactly',
            'startswith': 'starts_with'
        }.get(query_type, query_type)
