# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


def as_backfill_cron_app(cls):
    """a class decorator for Crontabber Apps.  This decorator embues a CronApp
    with the parts necessary to be a backfill CronApp.  It adds a main method
    that forces the base class to use a value of False for 'once'.  That means
    it will do the work of a backfilling app.
    """
    def main(self, function=None):
        return super(cls, self).main(function=function, once=False)
    cls.main = main
    cls._is_backfill_app = True
    return cls
