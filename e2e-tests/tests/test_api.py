# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import defaultdict

import requests
import pytest


class TestAPI:

    @pytest.mark.nondestructive
    def test_public_api_navigation(self, base_url):
        response = requests.get(base_url + '/api/ProductVersions/', {
            'active': True,
        })
        assert response.status_code == 200

        product_versions = defaultdict(list)
        for hit in response.json()['hits']:
            product_versions[hit['product']].append(hit['version'])

        uuids = {}
        for product, versions in product_versions.items():
            response = requests.get(base_url + '/api/SuperSearch/', {
                '_columns': ['uuid'],
                'product': product,
                'version': versions,
                '_results_number': 1,
                '_facets_size': 3,
                '_facets': 'version',
            })
            assert response.status_code == 200
            results = response.json()
            assert not results['errors'], results['errors']
            assert results['facets']
            for hit in results['hits']:
                uuids[product] = hit['uuid']

            response = requests.get(base_url + '/api/ProductBuildTypes/', {
                'product': product,
            })
            assert response.status_code == 200
            assert response.json()['hits']

        assert len(uuids) == len(product_versions)

        # Look up each raw crashh and processed crash and record all
        # found signatures.
        signatures = {}
        for uuid in uuids.values():
            response = requests.get(base_url + '/api/RawCrash/', {
                'crash_id': uuid,
            })
            assert response.status_code == 200

            response = requests.get(base_url + '/api/ProcessedCrash/', {
                'crash_id': uuid,
            })
            assert response.status_code == 200
            processed_crash = response.json()
            assert processed_crash
            signatures[uuid] = processed_crash['signature']

            # UnredactedProcessedCrash should not be allowed
            response = requests.get(
                base_url + '/api/UnredactedCrash/',
                {
                    'crash_id': uuid,
                }
            )
            assert response.status_code == 403

        assert len(signatures) == len(product_versions)

        # Check that we can fetch the "signature first date" for each
        # signature.
        response = requests.get(base_url + '/api/SignatureFirstDate/', {
            'signatures': signatures.values(),
        })
        assert response.status_code == 200
        results = response.json()
        first_dates = {}
        for hit in results['hits']:
            first_dates[hit['signature']] = hit['first_date']

        assert len(first_dates) == len(signatures)

        # Find all bug IDs for these signatures
        response = requests.get(base_url + '/api/Bugs/', {
            'signatures': signatures.values(),
        })
        assert response.status_code == 200
        results = response.json()
        bug_ids = defaultdict(list)
        for hit in results['hits']:
            bug_ids[hit['signature']].append(hit['id'])

        for signature, ids in bug_ids.items():
            response = requests.get(base_url + '/api/SignaturesByBugs/', {
                'bug_ids': ids,
            })
            assert response.status_code == 200
            assert response.json()['hits']

    @pytest.mark.nondestructive
    def test_supersearch_fields(self, base_url):
        response = requests.get(base_url + '/api/SuperSearchFields/')
        assert response.status_code == 200
        fields = response.json()
        assert 'uuid' in fields

    @pytest.mark.nondestructive
    def test_platforms(self, base_url):
        response = requests.get(base_url + '/api/Platforms/')
        assert response.status_code == 200
        platforms = response.json()
        assert platforms

    @pytest.mark.nondestructive
    def test_crontabber(self, base_url):
        response = requests.get(base_url + '/api/CrontabberState/')
        assert response.status_code == 200
        assert response.json()['state']
