import re
import collections

from django import forms
from django.conf import settings
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


make_choices = lambda seq: [(x, x) for x in seq]


class ReportListForm(BaseForm):
    all_param = 'ALL:ALL'

    signature = form_fields.SignatureField(required=True)
    product = forms.MultipleChoiceField(required=False)
    version = forms.MultipleChoiceField(required=False)
    platform = forms.MultipleChoiceField(required=False)
    date = forms.DateTimeField(required=False)
    range_value = forms.IntegerField(required=False)
    reason = forms.CharField(required=False)
    release_channels = forms.CharField(required=False)
    build_id = form_fields.BuildIdsField(required=False)
    range_unit = forms.ChoiceField(
        required=False,
        choices=make_choices(settings.RANGE_UNITS)
    )
    process_type = forms.ChoiceField(
        required=False,
        choices=make_choices(settings.PROCESS_TYPES)
    )
    hang_type = forms.ChoiceField(
        required=False,
        choices=make_choices(settings.HANG_TYPES)
    )
    plugin_field = forms.ChoiceField(
        required=False,
        choices=make_choices(settings.PLUGIN_FIELDS)
    )
    plugin_query_type = forms.ChoiceField(
        required=False,
        choices=make_choices(settings.QUERY_TYPES)
    )
    plugin_query = forms.CharField(required=False)

    def __init__(self, current_products, current_versions, current_platforms,
                 *args, **kwargs):
        super(ReportListForm, self).__init__(*args, **kwargs)

        # Default values
        platforms = [(x['code'], x['name']) for x in current_platforms]
        products = [(x, x) for x in current_products]
        versions = [(self.all_param, self.all_param)]
        for version in current_versions:
            v = '%s:%s' % (version['product'], version['version'])
            versions.append((v, v))

        self.fields['product'].choices = products
        self.fields['version'].choices = versions
        self.fields['platform'].choices = platforms

    def clean_version(self):
        versions = self.cleaned_data['version']
        if self.all_param in versions:
            versions.remove(self.all_param)
        return versions

    def clean_range_value(self):
        value = self.cleaned_data['range_value']
        if not value:
            value = 1
        elif value < 0:
            raise forms.ValidationError(
                'range_value must be a positive integer'
            )
        return value

    def clean(self):
        cleaned_data = super(ReportListForm, self).clean()
        if 'product' in cleaned_data and 'version' in cleaned_data:
            # check the invariant
            # every product in versions must be a supplied product
            for version in cleaned_data['version']:
                if version.split(':')[0] not in cleaned_data['product']:
                    raise forms.ValidationError(
                        "Mismatched product %r" % version
                    )
        return cleaned_data


class SignatureSummaryForm(BaseForm):
    all_param = 'ALL:ALL'

    signature = form_fields.SignatureField(required=False)
    range_value = forms.IntegerField(required=False, min_value=0)
    range_unit = forms.ChoiceField(required=False, choices=[
        ('days', 'days'),
    ])
    date = forms.DateTimeField(required=False)
    version = forms.MultipleChoiceField(required=False)

    def __init__(self, current_products, current_versions, *args, **kwargs):
        super(SignatureSummaryForm, self).__init__(*args, **kwargs)

        versions = [(self.all_param, self.all_param)]
        for version in current_versions:
            v = '%s:%s' % (version['product'], version['version'])
            versions.append((v, v))

        self.fields['version'].choices = versions


class QueryForm(ReportListForm):
    signature = form_fields.SignatureField(required=False)
    query = forms.CharField(required=False)
    query_type = forms.ChoiceField(
        required=False,
        choices=make_choices(settings.QUERY_TYPES)
    )


class DailyFormBase(BaseForm):
    p = forms.ChoiceField(required=True)
    v = forms.MultipleChoiceField(required=False)
    hang_type = forms.ChoiceField(required=False)
    date_range_type = forms.ChoiceField(required=False)
    date_start = forms.DateField(required=False)
    date_end = forms.DateField(required=False)

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


class GCCrashesForm(BaseForm):

    product = forms.ChoiceField(required=True)
    version = forms.ChoiceField(required=True)

    def __init__(self, nightly_versions,
                 *args, **kwargs):
        super(GCCrashesForm, self).__init__(*args, **kwargs)
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


class CorrelationsJSONFormBase(BaseForm):
    correlation_report_type = forms.ChoiceField(
        required=True,
        choices=make_choices(settings.CORRELATION_REPORT_TYPES),
    )
    product = forms.ChoiceField(required=True)
    version = forms.ChoiceField(required=True)

    def __init__(self, current_products, current_versions, current_platforms,
                 *args, **kwargs):
        super(CorrelationsJSONFormBase, self).__init__(*args, **kwargs)

        # Default values
        products = [(x, x) for x in current_products]
        versions = [(x['version'], x['version']) for x in current_versions]
        self.platforms = [(x['name'], x['name']) for x in current_platforms]

        self.fields['product'].choices = products
        self.fields['version'].choices = versions


class CorrelationsJSONForm(CorrelationsJSONFormBase):
    platform = forms.ChoiceField(required=True)
    signature = form_fields.SignatureField(required=True)

    def __init__(self, *args, **kwargs):
        super(CorrelationsJSONForm, self).__init__(*args, **kwargs)

        self.fields['platform'].choices = self.platforms


class CorrelationsSignaturesJSONForm(CorrelationsJSONFormBase):
    platforms = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        super(CorrelationsSignaturesJSONForm, self).__init__(*args, **kwargs)

        self.fields['platforms'].choices = self.platforms

    def clean_platforms(self):
        value = set(self.cleaned_data['platforms'].split(','))
        platforms = set([x[0] for x in self.platforms])
        if not value.issubset(platforms):
            raise forms.ValidationError('Invalid platform(s)')
        else:
            return '+'.join(value)
