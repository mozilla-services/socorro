import datetime as dt
import socorro.lib.uuid as uu

defaultDepth = 2
oldHardDepth = 4

def createNewOoid(timestamp=None, depth=None):
  if not timestamp:
    timestamp = dt.datetime.today()
  if not depth:
    depth = defaultDepth
  assert depth <= 4 and depth >=1
  uuid = str(uu.uuid4())
  return "%s%d%02d%02d%02d" %(uuid[:-7],depth,timestamp.year%100,timestamp.month,timestamp.day)

def uuidToOoid(uuid,timestamp=None, depth= None):
  if not timestamp:
    timestamp = dt.datetime.today()
  if not depth:
    depth = defaultDepth
  assert depth <= 4 and depth >=1
  return "%s%d%02d%02d%02d" %(uuid[:-7],depth,timestamp.year%100,timestamp.month,timestamp.day)

def dateAndDepthFromOoid(ooid):
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
    return (dt.datetime(year,month,day),depth)
  except:
    return None,None
  return None,None

def depthFromOoid(ooid):
  return dateAndDepthFromOoid(ooid)[1]

def dateFromOoid(ooid):
  return dateAndDepthFromOoid(ooid)[0]

  
