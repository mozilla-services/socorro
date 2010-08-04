import datetime as dt


#-----------------------------------------------------------------------------------------------------------------
def datetimeFromISOdateString(s):
  """ Take an ISO date string of the form YYYY-MM-DDTHH:MM:SS.S
      and convert it into an instance of datetime.datetime
  """
  year = month = day = hour = minute = second = millisecond = 0
  try:
    year = int(s[0:4])
    month = int(s[5:7])
    day = int(s[8:10])
    if len(s) >= 19:
      hour = int(s[11:13])
      minute = int(s[14:16])
      second = int(s[17:19])
      if len(s) > 19:
        if s[-6] in '+-':
          millisecond = int(s[20:-6])
        else:
          millisecond = int(s[20:])
  except Exception, e:
    raise ValueError('Invalid timestamp - "%s": %s' % (s, str(e)))
  return dt.datetime(year, month, day, hour, minute, second, millisecond)


#-----------------------------------------------------------------------------------------------------------------
def strHoursToTimeDelta(hoursAsString):
  return dt.timedelta(hours=int(hoursAsString))

#-----------------------------------------------------------------------------------------------------------------
def timeDeltaToSeconds(td):
  return td.days * 24 * 60 * 60 + td.seconds


#=================================================================================================================
class UTC(dt.tzinfo):
  """
  """
  ZERO = dt.timedelta(0)

  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self):
    super(UTC, self).__init__()

  #-----------------------------------------------------------------------------------------------------------------
  def utcoffset(self, dt):
    return UTC.ZERO

  #-----------------------------------------------------------------------------------------------------------------
  def tzname(self, dt):
    return "UTC"

  #-----------------------------------------------------------------------------------------------------------------
  def dst(self, dt):
    return UTC.ZERO