# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import defaultdict

import requests
import pytest


# Because there are so few crashes for these products, instead of
# looking for crashes from the *active* versions, we'll for any
# version of any recent crashes for these.
ANY_VERSION_PRODUCTS = ('SeaMonkey',)


class TestAPI:

    @pytest.mark.nondestructive
    def test_public_api_navigation(self, base_url):
        # Request a list of all the products and versions
        response = requests.get(base_url + '/api/ProductVersions/', {
            'active': True,
        })
        assert response.status_code == 200

        product_versions = defaultdict(list)
        for hit in response.json()['hits']:
            product_versions[hit['product']].append(hit['version'])

        # For each product, do a supersearch for all versions getting the uuid
        # for a single crash for that product
        product_to_uuid = {}
        for product, versions in product_versions.items():
            if product in ANY_VERSION_PRODUCTS:
                # Effectively, don't filter by any particular version
                versions = None
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
                product_to_uuid[product] = hit['uuid']

            response = requests.get(base_url + '/api/ProductBuildTypes/', {
                'product': product,
            })
            assert response.status_code == 200
            assert response.json()['hits']

        # Assert we have at least one crash for every product
        assert len(product_to_uuid) == len(product_versions)

        # Fetch the raw crash and processed crash for each uuid and verify we
        # can't get the unredacted processed crash
        uuid_to_signature = {}
        for uuid in product_to_uuid.values():
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
            uuid_to_signature[uuid] = processed_crash['signature']

            # UnredactedProcessedCrash should not be allowed
            response = requests.get(
                base_url + '/api/UnredactedCrash/',
                {
                    'crash_id': uuid,
                }
            )
            assert response.status_code == 403

        assert len(uuid_to_signature) == len(product_versions)

        # Check that we can fetch the "signature first date" for each
        # signature--some don't have one, so we try to roll with that
        response = requests.get(base_url + '/api/SignatureFirstDate/', {
            'signatures': uuid_to_signature.values(),
        })
        assert response.status_code == 200
        results = response.json()

        signature_to_first_date = {}
        for hit in results['hits']:
            signature_to_first_date[hit['signature']] = hit['first_date']

        assert 0 < len(signature_to_first_date) <= len(uuid_to_signature)

        # Find all bug IDs for these signatures
        response = requests.get(base_url + '/api/Bugs/', {
            'signatures': uuid_to_signature.values(),
        })
        assert response.status_code == 200
        results = response.json()
        signature_to_bug_ids = defaultdict(list)
        for hit in results['hits']:
            signature_to_bug_ids[hit['signature']].append(hit['id'])

        for signature, ids in signature_to_bug_ids.items():
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
