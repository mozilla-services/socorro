# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import random

from nose.plugins.attrib import attr
from nose.tools import eq_, ok_

from socorro.external.postgresql.laglog import LagLog
from socorro.lib.util import DotDict

from unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestLagLog(PostgreSQLTestCase):

    def tearDown(self):
        """Clean up the database. """
        cursor = self.connection.cursor()
        cursor.execute("TRUNCATE lag_log")
        self.connection.commit()
        super(IntegrationTestLagLog, self).tearDown()

    def _generate_random_data(self, names, points=40):
        now = datetime.datetime.utcnow()

        sqls = []
        for i in range(points):
            moment = now - datetime.timedelta(seconds=(points - i) * 60)
            for name in names:
                if name == names[0]:  # first one
                    bytes = random.randint(180, 500 - i)
                else:
                    bytes = random.randint(170 + i * 10, 300 + i * 12)
                sqls.append(
                    "INSERT INTO lag_log "
                    "(replica_name, moment, lag, master)"
                    "values ('%s', '%s', %s, 'master1');"
                    % (name, moment, bytes)
                )

        cursor = self.connection.cursor()
        cursor.execute('\n'.join(sqls))
        self.connection.commit()

    def _get_model(self, **overrides):
        config = self.config
        config['laglog'] = DotDict({
            'max_bytes_warning': 1000,
            'max_bytes_critical': 2000,
        })
        config.update(overrides)
        return LagLog(config=config)

    def test_get_empty(self):
        laglog = self._get_model()
        res = laglog.get()
        eq_(res, {'replicas': []})

    def test_get(self):
        self._generate_random_data(['DB1', 'DB2'], points=20)
        laglog = self._get_model()
        res = laglog.get()
        ok_(res['replicas'])

        names = [x['name'] for x in res['replicas']]
        eq_(names, ['DB1', 'DB2'])
        db1s, db2s = res['replicas']

        ok_(db1s['rows'])
        ok_(db1s['averages'])
        eq_(db1s['name'], 'DB1')
        eq_(
            db1s['last_average'],
            db1s['averages'][-1]['y']
        )
        last = db1s['rows'][-12:]
        assert len(last) == 12
        sum_ys = sum(x['y'] for x in last)
        calculated_last_average = int(1.0 * sum_ys / len(last))
        eq_(calculated_last_average, db1s['last_average'])

    def test_get_paginated(self):
        self._generate_random_data(['DB'], points=20)
        laglog = self._get_model()
        res = laglog.get(limit=2)
        rows = res['replicas'][0]['rows']
        self.assertEqual(len(rows), 2)
