import unittest

import datetime as dt

import socorro.cron.daily_crash as daily_crash

class TestDailyUrl(unittest.TestCase):
  def setUp(self):
    pass

  def testContinueAggregating(self):
    """ We should be able to run the cron multiple times
        without causing problems.
        Given a start date, the cron will look at the reports
        table for start date - 8 hours through start date + 16 hours

        If we process previousDay set to 2010-06-04,
        we'll be looking for reports with date_processed
        2010-06-03 16:00:00 through 2010-06-04 16:00:00
    """
    previousDay = dt.datetime(2010, 6, 4, 0, 0, 0)
    today = dt.datetime(2010, 6, 4, 0, 0, 0)
    self.assertFalse(daily_crash.continue_aggregating(previousDay, today),
                     "previousDay isn't in the past")

    today = dt.datetime(2010, 6, 4, 15, 30, 0)
    self.assertFalse(daily_crash.continue_aggregating(previousDay, today),
                     "We are still inside of the ADU adjusted range by 30 minutes")

    today = dt.datetime(2010, 6, 4, 23, 59, 59)
    self.assertFalse(daily_crash.continue_aggregating(previousDay, today),
                     "It's probably safe, but we'll give ourselfs a 4 hour buffer...")

    today = dt.datetime(2010, 6, 5, 0, 0, 0)
    self.assertTrue(daily_crash.continue_aggregating(previousDay, today),
                     "It's probably safe")

    today = dt.datetime(2010, 6, 25, 12, 0, 0)
    self.assertTrue(daily_crash.continue_aggregating(previousDay, today),
                     "It's definately  safe")    

    today = dt.datetime(2010, 6, 3, 0, 0, 0)
    self.assertFalse(daily_crash.continue_aggregating(previousDay, today),
                     "Invalid state, today is before previous Day")
