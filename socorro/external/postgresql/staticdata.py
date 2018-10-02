# flake8: noqa

"""
Static data for Socorro - basic information that Socorro expects to be
present in the database in order to function correctly.
"""


class BaseTable(object):
    def generate_rows(self):
        return iter(self.rows)


class OSNames(BaseTable):
    table = 'os_names'
    columns = ['os_name', 'os_short_name']
    rows = [['Windows', 'win'],
            ['Mac OS X', 'mac'],
            ['Linux', 'lin'],
            ['Unknown', 'unknown']]


class OSNameMatches(BaseTable):
    table = 'os_name_matches'
    columns = ['os_name', 'match_string']
    rows = [['Windows', 'Windows%'],
            ['Mac OS X', 'Mac%'],
            ['Mac OS X', 'Darwin%'],
            ['Linux', 'Linux%']]


class ReleaseChannels(BaseTable):
    table = 'release_channels'
    columns = ['release_channel', 'sort']
    rows = [['Nightly', '1'],
            ['Aurora', '2'],
            ['Beta', '3'],
            ['Release', '4'],
            ['ESR', '5']]


class ReleaseRepositories(BaseTable):
    table = 'release_repositories'
    columns = ['repository']
    rows = [
        ['mozilla-central'],
        ['mozilla-1.9.2'],
        ['comm-central'],
        ['comm-1.9.2'],
        ['comm-central-trunk'],
        ['mozilla-central-android'],
        ['mozilla-release'],
        ['mozilla-beta'],
        ['mozilla-aurora'],
        ['mozilla-aurora-android'],
        ['mozilla-esr10'],
        ['mozilla-esr10-android'],
        ['b2g-release'],
        ['mozilla-aurora-android-xul'],
        ['mozilla-central-android-xul'],
        ['comm-aurora'],
        ['mozilla-central-android-api-11'],
        ['mozilla-aurora-android-api-11'],
        ['mozilla-central-android-api-15'],
        ['mozilla-aurora-android-api-15'],
        ['mozilla-beta-android-api-15'],
        ['mozilla-release-android-api-15'],
        ['mozilla-central-android-api-16'],
        ['mozilla-esr38'],
        ['mozilla-esr45'],
        ['comm-esr38'],
        ['comm-esr45'],
        ['comm-beta'],
        ['mozilla-esr52'],
        ['comm-esr52'],
        ['mozilla-esr60'],
        ['comm-esr60'],
    ]


class Products(BaseTable):
    table = 'products'
    columns = [
        'product_name', 'sort', 'rapid_release_version', 'release_name', 'rapid_beta_version'
    ]
    rows = [
        ['Firefox', '1', '5.0', 'firefox', '23.0'],
        ['FennecAndroid', '2', '5.0', '**SPECIAL**', '999.0'],
        ['Thunderbird', '80', '6.0', 'thunderbird', '999.0'],
        ['SeaMonkey', '90', '2.3', 'seamonkey', '999.0'],
        ['Fennec', '100', '5.0', 'mobile', '999.0'],
        ['InactiveProduct', '-1', '5.0', 'inactive', '999.0'],
    ]


class ProductBuildTypes(BaseTable):
    table = 'product_build_types'
    columns = [
        'product_name', 'build_type', 'throttle'
    ]
    rows = [
        ['Firefox', 'esr', '1.0'],
        ['Firefox', 'aurora', '1.0'],
        ['Firefox', 'beta', '1.0'],
        ['Firefox', 'release', '0.1'],
        ['Firefox', 'nightly', '1.0'],
    ]


class ProductProductIDMap(BaseTable):
    table = 'product_productid_map'
    columns = [
        'product_name', 'productid', 'rewrite', 'version_began'
    ]
    rows = [
        ['Fennec', '{a23983c0-fd0e-11dc-95ff-0800200c9a66}', 'f', '0.1'],
        ['FennecAndroid', '{aa3c5121-dab2-40e2-81ca-7ea25febc110}', 't', '0.1'],
        ['Firefox', '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}', 'f', '0.7'],
        ['Thunderbird', '{3550f703-e582-4d05-9a08-453d09bdfdc6}', 'f', '0.3'],
        ['SeaMonkey', '{92650c4d-4b8e-4d2a-b7eb-24ecf4f6b63a}', 'f', '1.0a'],
    ]


# DEPRECATED
class ProductReleaseChannels(BaseTable):
    table = 'product_release_channels'
    columns = [
        'product_name', 'release_channel', 'throttle'
    ]
    rows = [
        ['Firefox', 'ESR', '1.0'],
        ['Firefox', 'Aurora', '1.0'],
        ['Firefox', 'Beta', '1.0'],
        ['Firefox', 'Release', '0.1'],
        ['Firefox', 'Nightly', '1.0'],
    ]


class SpecialProductPlatforms(BaseTable):
    table = 'special_product_platforms'
    columns = [
        'platform', 'repository', 'release_channel', 'release_name', 'product_name', 'min_version'
    ]
    rows = [
        ['android', 'mozilla-release', 'release', 'mobile', 'FennecAndroid', '10.0'],
        ['android', 'mozilla-release', 'beta', 'mobile', 'FennecAndroid', '10.0'],
        ['android', 'mozilla-beta', 'beta', 'mobile', 'FennecAndroid', '10.0'],
        ['android-arm', 'mozilla-central-android', 'nightly', 'mobile', 'FennecAndroid', '10.0'],
        ['android-arm', 'mozilla-central-android', 'aurora', 'mobile', 'FennecAndroid', '10.0'],
        ['android-arm', 'mozilla-aurora-android', 'aurora', 'mobile', 'FennecAndroid', '10.0'],
        ['android-arm', 'mozilla-central-android-api-11', 'nightly', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-aurora-android-api-11', 'aurora', 'mobile', 'FennecAndroid', '37.0'],
        ['android-x86', 'mozilla-beta', 'beta', 'mobile', 'FennecAndroid', '37.0'],
        ['android-api-9', 'mozilla-beta', 'beta', 'mobile', 'FennecAndroid', '37.0'],
        ['android-api-11', 'mozilla-beta', 'beta', 'mobile', 'FennecAndroid', '37.0'],
        ['android-x86', 'mozilla-release', 'release', 'mobile', 'FennecAndroid', '37.0'],
        ['android-api-9', 'mozilla-release', 'release', 'mobile', 'FennecAndroid', '37.0'],
        ['android-api-11', 'mozilla-release', 'release', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-central-android-api-15', 'nightly', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-aurora-android-api-15', 'aurora', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-beta-android-api-15', 'beta', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-release-android-api-15', 'release', 'mobile', 'FennecAndroid', '37.0'],

        # FennecAndroid 56+
        ['android-arm', 'mozilla-central-android-api-16', 'nightly', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-beta-android-api-16', 'aurora', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-release-android-api-16', 'aurora', 'mobile', 'FennecAndroid', '37.0'],
    ]


# NOTE(willkg): the order that tables are loaded is important
tables = [OSNames, OSNameMatches, ReleaseChannels,
          ReleaseRepositories,
          Products, ProductBuildTypes, ProductReleaseChannels,
          ProductProductIDMap, SpecialProductPlatforms]
