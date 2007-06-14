from sqlalchemy import sql, func, select, types
from socorro.models import Report

class Platform(object):
  """A class representing a platform, which has helper methods for
  aggregating and limiting SQL queries."""
  def __init__(self, id, name, os_name):
    self._id = id
    self._name = name
    self._os_name = os_name
    self._condition = Report.c.os_name == self._os_name
    self._selection = sql.case([(self._condition, 1)])
    self.count_name = 'is_%s' % self._id
    self._count = func.count(self._selection).label(self.count_name)

  def id(self):
    return self._id

  def name(self):
    return self._name

  def condition(self):
    return self._condition

  def count(self):
    return self._count

  def __str__(self):
    return self._id

class PlatformList(list):
  def __getitem__(self, key):
    if isinstance(key, int):
      return list.__getitem__(self, key)

    key = str(key)
    for p in self:
      if str(p) == key:
        return p

    raise KeyError(key)

platformList = PlatformList([Platform('windows', 'Windows', 'Windows NT'),
                             Platform('mac', 'Mac OS X', 'Mac OS X'),
                             Platform('linux', 'Linux', 'Linux')])

def count_platforms():
  return [platform.count() for platform in platformList]
