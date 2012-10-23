import datetime
import collections

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

    signature = forms.CharField(required=True)
    product = forms.MultipleChoiceField(required=False)
    version = forms.MultipleChoiceField(required=False)
    platform = forms.MultipleChoiceField(required=False)
    date = forms.DateTimeField(required=False)
    range_value = forms.IntegerField(required=False)
    range_unit = forms.ChoiceField(required=False, choices=[
        ('hours', 'hours'),
        ('days', 'days'),
        ('weeks', 'weeks')
    ])
    reason = forms.CharField(required=False)
    build_id = forms.CharField(required=False)
    process_type = forms.CharField(required=False)
    hang_type = forms.CharField(required=False)
    plugin_field = forms.CharField(required=False)
    plugin_query_type = forms.CharField(required=False)
    plugin_query = forms.CharField(required=False)

    def __init__(self, current_products, current_verisons, current_platforms,
                 *args, **kwargs):
        super(ReportListForm, self).__init__(*args, **kwargs)

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

    def clean_date(self):
        return self.cleaned_data['date'] or datetime.datetime.utcnow()

    def clean_range_value(self):
        value = self.cleaned_data['range_value']
        if not value:
            value = 1
        elif value < 0:
            raise forms.ValidationError(
                'range_value must be a positive integer'
            )
        return value

    def clean_range_unit(self):
        return self.cleaned_data['range_unit'] or 'weeks'

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


class QueryForm(ReportListForm):

    signature = forms.CharField(required=False)
    query = forms.CharField(required=False)
    query_type = forms.CharField(required=False)

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


class DailyFormBase(forms.Form):
    p = forms.ChoiceField(required=True)
    v = forms.MultipleChoiceField(required=False)
    hang_type = forms.CharField(required=False)
    date_range_type = forms.CharField(required=False)
    start_date = forms.DateField(required=False)
    end_date = forms.DateField(required=False)

    def __init__(self, current_versions, platforms, *args, **kwargs):
        super(DailyFormBase, self).__init__(*args, **kwargs)
        self.versions = collections.defaultdict(list)
        for each in current_versions:
            self.versions[each['product']].append(each['version'])
        self.platforms = platforms

        self.fields['p'].choices = [
            (x, x) for x in self.versions
        ]

        # initially, make it all of them
        self.fields['v'].choices = [
            (x, x) for sublist in self.versions.values() for x in sublist
        ] + [('', 'blank')]

    def clean_v(self):
        versions = [x.strip() for x in self.cleaned_data['v'] if x.strip()]
        if 'p' not in self.cleaned_data:
            # 'p' failed, no point checking the invariance
            return versions
        allowed_versions = self.versions[self.cleaned_data['p']]
        if set(versions) - set(allowed_versions):
            left = set(versions) - set(allowed_versions)
            raise forms.ValidationError(
                "Unrecognized versions: %s" % list(left)
            )
        return versions


class DailyFormByOS(DailyFormBase):
    pass


class DailyFormByVersion(DailyFormBase):
    os = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super(DailyFormByVersion, self).__init__(*args, **kwargs)

        self.fields['os'].choices = [
            (x['name'], x['name']) for x in self.platforms
        ]
