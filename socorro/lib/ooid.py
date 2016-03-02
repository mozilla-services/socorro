# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# OOID is "Our opaque ID"
import datetime as dt
import uuid as uu

from socorrolib.lib.datetimeutil import utc_now, UTC

defaultDepth = 2
oldHardDepth = 4

def createNewOoid(timestamp=None, depth=None):
  """Create a new Ooid for a given time, to be stored at a given depth
  timestamp: the year-month-day is encoded in the ooid. If none, use current day
  depth: the expected storage depth is encoded in the ooid. If non, use the defaultDepth
  returns a new opaque id string holding 24 random hex digits and encoded date and depth info
  """
  if not timestamp:
    timestamp = utc_now().date()
  if not depth:
    depth = defaultDepth
  assert depth <= 4 and depth >=1
  uuid = str(uu.uuid4())
  return "%s%d%02d%02d%02d" %(uuid[:-7],depth,timestamp.year%100,timestamp.month,timestamp.day)

def uuidToOoid(uuid,timestamp=None, depth= None):
  """ Create an ooid from a 32-hex-digit string in regular uuid format.
  uuid: must be uuid in expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxx7777777
  timestamp: the year-month-day is encoded in the ooid. If none, use current day
  depth: the expected storage depth is encoded in the ooid. If non, use the defaultDepth
  returns a new opaque id string holding the first 24 digits of the provided uuid and encoded date and depth info
  """
  if not timestamp:
    timestamp = utc_now().date()
  if not depth:
    depth = defaultDepth
  assert depth <= 4 and depth >=1
  return "%s%d%02d%02d%02d" %(uuid[:-7],depth,timestamp.year%100,timestamp.month,timestamp.day)

def dateAndDepthFromOoid(ooid):
  """ Extract the encoded date and expected storage depth from an ooid.
  ooid: The ooid from which to extract the info
  returns (datetime(yyyy,mm,dd),depth) if the ooid is in expected format else (None,None)
  """
  year = month = day = None
  try:
    day = int(ooid[-2:])
  except:
    return None,None
  try:
    month = int(ooid[-4:-2])
  except:
    return None,None
  try:
    year = 2000 + int(ooid[-6:-4])
    depth = int(ooid[-7])
    if not depth: depth = oldHardDepth
    return (dt.datetime(year,month,day,tzinfo=UTC),depth)
  except:
    return None,None
  return None,None

def depthFromOoid(ooid):
  """Extract the encoded expected storage depth from an ooid.
  ooid: The ooid from which to extract the info
  returns expected depth if the ooid is in expected format else None
  """
  return dateAndDepthFromOoid(ooid)[1]

def dateFromOoid(ooid):
  """Extract the encoded date from an ooid.
  ooid: The ooid from which to extract the info
  returns encoded date if the ooid is in expected format else None
  """
  return dateAndDepthFromOoid(ooid)[0]


