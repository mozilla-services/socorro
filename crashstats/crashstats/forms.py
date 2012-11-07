import re
import datetime
import collections

from django import forms
from django.conf import settings


class CarefulFieldBase(object):
    """Because Django's forms.fields.DateTimeField class is not careful
    enough when it uses datetime.datetime.strptime() to try to convert
    we improve that by using our own.

    We need this till
    https://github.com/django/django/commit/\
      3174b5f2f5bb0b0a6b775a1a50464b6bf2a4b067
    is included in the next release.
    """

    def strptime(self, value, format):
        try:
            return datetime.datetime.strptime(value, format)
        except TypeError, e:
            raise ValueError(e)


class CarefulDateTimeField(CarefulFieldBase, forms.DateTimeField):
    pass


class CarefulDateField(CarefulFieldBase, forms.DateField):
    pass


class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(BaseForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            if isinstance(self.fields[field], forms.DateTimeField):
                attributes = dict(self.fields[field].__dict__)
                attributes.pop('creation_counter')
                self.fields[field] = CarefulDateTimeField(**attributes)
            elif isinstance(self.fields[field], forms.DateField):
                attributes = dict(self.fields[field].__dict__)
                attributes.pop('creation_counter')
                self.fields[field] = CarefulDateField(**attributes)


class BugInfoForm(BaseForm):

    bug_ids = forms.CharField(required=True)
    include_fields = forms.CharField(required=True)

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

    def clean_include_fields(self):
        value = self.cleaned_data['include_fields']
        include_fields = [x.strip() for x in value.split(',') if x.strip()]
        # include fields must be variable looking strings
        regex = re.compile('[^\w_]+')
        nasty_fields = [x for x in include_fields if regex.findall(x)]
        if nasty_fields:
            raise forms.ValidationError(
                'Not valid include_fields %s' %
                (', '.join(repr(x) for x in nasty_fields))
            )
        return include_fields


class ReportListForm(BaseForm):

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


class SignatureSummaryForm(BaseForm):

    signature = forms.CharField(required=True)
    range_value = forms.IntegerField(required=False, min_value=0)
    range_unit = forms.ChoiceField(required=False, choices=[
        ('days', 'days'),
    ])

    def clean_range_value(self):
        return self.cleaned_data['range_value'] or 1

    def clean_range_unit(self):
        return self.cleaned_data['range_unit'] or 'days'


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


class DailyFormBase(BaseForm):
    p = forms.ChoiceField(required=True)
    v = forms.MultipleChoiceField(required=False)
    hang_type = forms.ChoiceField(required=False)
    date_range_type = forms.ChoiceField(required=False)
    start_date = forms.DateField(required=False)
    end_date = forms.DateField(required=False)

    def __init__(self,
                 current_versions,
                 platforms,
                 date_range_types=None,
                 hang_types=None,
                 *args, **kwargs):
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

        if not date_range_types:
            raise ValueError("date_range_types must be something")
        self.fields['date_range_type'].choices = [
            (x, x) for x in date_range_types
        ]

        if not hang_types:
            raise ValueError("hang_types must be something")
        self.fields['hang_type'].choices = [
            (x, x) for x in hang_types
        ]

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


class CrashTrendsForm(BaseForm):

    product = forms.ChoiceField(required=True)
    version = forms.ChoiceField(required=True)
    start_date = forms.DateField(required=True)
    end_date = forms.DateField(required=True)

    def __init__(self, nightly_versions,
                 *args, **kwargs):
        super(CrashTrendsForm, self).__init__(*args, **kwargs)
        self.versions = collections.defaultdict(list)
        for each in nightly_versions:
            self.versions[each['product']].append(each['version'])

        self.fields['product'].choices = [
            (x, x) for x in self.versions
        ]

        self.fields['version'].choices = [
            (x, x) for sublist in self.versions.values() for x in sublist
        ] + [('', 'blank')]

    def clean_version(self):
        if 'product' not in self.cleaned_data:
            # don't bother, the product didn't pass validation
            return
        value = self.cleaned_data['version']
        allowed_versions = self.versions[self.cleaned_data['product']]

        if value not in allowed_versions:
            raise forms.ValidationError(
                "Unrecognized version for product: %s" % value
            )

        return value


class FrontpageJSONForm(forms.Form):
    product = forms.ChoiceField(required=False)
    versions = forms.MultipleChoiceField(required=False)
    duration = forms.IntegerField(required=False, min_value=1)
    date_range_type = forms.ChoiceField(required=False)

    def __init__(self, current_versions,
                 date_range_types=None,
                 default_duration=7,
                 default_product=settings.DEFAULT_PRODUCT,
                 *args, **kwargs):
        super(FrontpageJSONForm, self).__init__(*args, **kwargs)
        self.default_product = default_product
        self.default_duration = default_duration
        self.versions = collections.defaultdict(list)
        for each in current_versions:
            self.versions[each['product']].append(each['version'])

        self.fields['product'].choices = [
            (x, x) for x in self.versions
        ]

        # initially, make it all of them
        self.fields['versions'].choices = [
            (x, x) for sublist in self.versions.values() for x in sublist
        ] + [('', 'blank')]

        if not date_range_types:
            raise ValueError("date_range_types must be something")
        self.fields['date_range_type'].choices = [
            (x, x) for x in date_range_types
        ]

    def clean_product(self):
        value = self.cleaned_data['product']
        if not value:
            value = self.default_product
        return value

    def clean_duration(self):
        value = self.cleaned_data['duration']
        if not value:
            value = self.default_duration
        return value

    def clean_versions(self):
        versions = [x.strip() for x in self.cleaned_data['versions']
                    if x.strip()]
        if 'product' not in self.cleaned_data:
            # 'p' failed, no point checking the invariance
            return versions
        allowed_versions = self.versions[self.cleaned_data['product']]
        if set(versions) - set(allowed_versions):
            left = set(versions) - set(allowed_versions)
            raise forms.ValidationError(
                "Unrecognized versions: %s" % list(left)
            )
        return versions
