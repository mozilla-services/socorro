#!/usr/bin/env python

import json
import urllib

product_versions = json.load(urllib.urlopen(
    'https://crash-stats.mozilla.com/api/ProductVersions/'
    '?active=true&product=Firefox'
))['hits']

versions = [
    x['version'] for x in product_versions if 'esr' not in x['version']
]
print ' '.join(sorted(versions))
