# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from nose.tools import eq_

from socorro.external.postgresql.error_service import Error
from socorro.lib import datetimeutil
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
)

from unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestError(PostgreSQLTestCase):
    """Test socorro.external.postgresql.error_service.Error class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestError, self).setUp(Error)

        # Insert data
        self.now = datetimeutil.utc_now()
        uuid = (
            "%%s000aaf-98e0-4ece-a904-2573e2%s" % self.now.strftime("%y%m%d")
        )
        self.transaction(
            execute_no_results,
            """
                SET search_path TO bixie;
                INSERT INTO crashes (
                    crash_id
                    , signature
                    , error
                    , product
                    , protocol
                    , hostname
                    , username
                    , port
                    , path
                    , query
                    , full_url
                    , user_agent
                    , success
                    , client_crash_datetime
                    , client_submitted_datetime
                    , processor_started_datetime
                    , processor_completed_datetime
                )
                VALUES (
                    '%(uuid)s'
                    , 'Terrible Things Happening'
                    , '{
                            "protocol": "https",
                            "hostname": "localhost",
                            "path": "/api/0/store/",
                            "query": "sentry_version=2.0&sentry_client=raven-js/1.0.7&sentry_key=public&sentry_data=things",
                            "duplicateQueryParameters": false,
                            "fullUrl": "https://localhost/api/0/store/?sentry_version=2.0&sentry_client=raven-js/1.0.7&sentry_key=public&sentry_data=things"
                        }'
                    , 'hrafnsmal'
                    , 'https'
                    , 'localhost'
                    , NULL
                    , NULL
                    , 'sentry_version=2.0&sentry_client=raven-js/1.0.7&sentry_key=public&sentry_data=things'
                    , 'sentry_version=2.0&sentry_client=raven-js/1.0.7&sentry_key=public&sentry_data=things'
                    , 'https://localhost/api/0/store/?sentry_version=2.0&sentry_client=raven-js/1.0.7&sentry_key=public&sentry_data=things'
                    , 'Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/534.34 (KHTML, like Gecko) PhantomJS/1.9.0 Safari/534.34'
                    , TRUE
                    , '%(timestamp)s'
                    , '%(timestamp)s'
                    , '%(timestamp)s'
                    , '%(timestamp)s'
                );
            """ %
            {
                'uuid': uuid % "a1",
                'timestamp': self.now
            }
        )

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        self.transaction(
            execute_no_results,
            """
                SET search_path TO bixie;
                TRUNCATE crashes CASCADE;
            """
        )
        super(IntegrationTestError, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        """ Test GET for Bixie Errors """
        error = Error(config=self.config)
        uuid = (
            "%%s000aaf-98e0-4ece-a904-2573e2%s" % self.now.strftime("%y%m%d")
        )

        # Test 1: a valid crash
        params = {
            "uuid": uuid % "a1"
        }
        res = error.get(**params)

        res_expected = {
            'hits': [
                {
                    'product': 'Terrible Things Happening',
                    'signature': """{
                        "protocol": "https",
                        "hostname": "localhost",
                        "path": "/api/0/store/",
                        "query": "sentry_version=2.0&sentry_client=raven-js/1.0.7&sentry_key=public&sentry_data=things",
                        "duplicateQueryParameters": false,
                        "fullUrl": "https://localhost/api/0/store/?sentry_version=2.0&sentry_client=raven-js/1.0.7&sentry_key=public&sentry_data=things"
                    }""".replace(' ', ''),
                    'error': 'hrafnsmal'
                }
            ],
            'total': 1
        }
        res['hits'][0]['signature'] = \
            res['hits'][0]['signature'].replace(' ', '')
        eq_(res, res_expected)
