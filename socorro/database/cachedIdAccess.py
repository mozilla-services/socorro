import re
from operator import itemgetter
import logging
import sys
import threading
import time

import psycopg2

logger = logging.getLogger("cachedIdAccess")

maxOsIdCacheLength = 2048
maxProductIdCacheLength = 256
maxUriIdCacheLength = 32768
osIdCache = None     # may become {(os_name,os_version): osdims_id}
osIdCount = None     # may become {(os_name,os_version): count_of_cache_hits}
productIdCache = None # may become {(product_name,version_string): productdims_id}
productBranchCache = None # may become {productdims_id: branch}
productIdCount = None # may become {(product_name,version_string): count_of_cache_hits}
#signatureIdCache = None  # may become {(signature,): signatureims_id}
#signatureIdCount = None  # may become {(signature,): count_of_cache_hits}
uriIdCache = None     # may become {(domain,url): urldims_id}
uriIdCount = None     # may become {(domain,url): count_of_cache_hits}

# Retain the trailing $ needed to force a match on the full value
#-----------------------------------------------------------------------------------------------------------------
majorPattern = re.compile(r'(\d+\.)+\d+$')
developmentPattern = re.compile(r'(\d+\.)+\d+[ab]\d*$')
milestonePattern = re.compile(r'(\d+\.)+\d+([ab]\d*)?pre$')
def createProductRelease(version):
  """Given a version, create the appropriate release type. Assumes param version has no extraneous whitespace"""
  m = milestonePattern.match(version)
  if m and m.groups(0):
    return 'milestone'
  m = developmentPattern.match(version)
  if m and m.groups(0):
    return 'development'
  m = majorPattern.match(version)
  if m and m.groups(0):
    return 'major'
  return None

#-----------------------------------------------------------------------------------------------------------------
def initializeIdCache(keyColumns, idColumn, tableName, cursor):
  """create maps {key:id} (actual cache) and {key:0} (cache count) for all keys in the given table, and return them"""
  sql = "SELECT %s,%s from %s"%(','.join(keyColumns),idColumn,tableName)
  cursor.execute(sql)
  data = cursor.fetchall()
  idCache = dict((tuple(x[:-1]),x[-1]) for x in data)
  idCount = dict((tuple(x[:-1]),0) for x in data)
  cursor.connection.commit()
  return idCache, idCount

#-----------------------------------------------------------------------------------------------------------------
def initializeProductBranchCache(idMap,cursor):
  cursor.execute("SELECT id,branch from productdims")
  data = cursor.fetchall()
  cursor.connection.rollback()
  return dict(data)

#-----------------------------------------------------------------------------------------------------------------
def clearCache():
  global productIdCache,productIdCount,productBranchCache,uriIdCache,uriIdCount,osIdCache,osIdCount
  productIdCache = productIdCount = productBranchCache = None
  uriIdCache = uriIdCount = None
  osIdCache = osIdCount = None

#-----------------------------------------------------------------------------------------------------------------
def shrinkIdCache(cacheMap, cacheCount, oneKeyToSave=None):
  """
  Remove the least-used half of the cached data, retaining oneKeyToSave (most recently used) if provided
  return two new cache maps. Raises KeyError if oneKeyToSave is not a key in both maps
  counts for retained keys are reset to 1
  """
  if oneKeyToSave:
    oneIdToSave = cacheMap[oneKeyToSave]
  killer = []
  for (k,count) in cacheCount.items():
    killer.append((k,count))
  killer.sort(key=itemgetter(1))
  s2 = len(killer)/2
  idCache = dict([(x[0],cacheMap[x[0]]) for x in killer[s2:]])
  idCount = dict((x[0],1) for x in killer[s2:])
  if oneKeyToSave:
    # may be redundant if oneKeyToSave is already there. Oh well.
    idCache[oneKeyToSave] = oneIdToSave
    idCount[oneKeyToSave] = 1
  return idCache,idCount

#=================================================================================================================
class IdCache:
  linuxLineRE = re.compile(r'0\.0\.0 [lL]inux.+[lL]inux$|[0-9.]+.+(i586|i686|sun4u|i86pc|x86_64)?')
  linuxVersionRE = re.compile(r'(0\.0\.0 [lL]inux.)([0-9.]+[0-9]).*(i586|i686|sun4u|i86pc|x86_64).*')
  linuxShortVersionRE = re.compile(r'(0\.0\.0 [lL]inux.)([0-9.]+[0-9]).*')

  def __init__(self,databaseCursor, **kwargs):
    global logger
    if kwargs.get('logger'):
      logger = kwargs.get('logger')
    self.truncateUrlLength = kwargs.get('truncateUrlLength',0)
    if self.truncateUrlLength:
      self.truncateUrlLength = int(self.truncateUrlLength)
    self.cursor = databaseCursor
    self.initializeCache()

  def initializeCache(self):
    global maxOsIdCacheLength, maxProductIdCacheLength, maxUriIdCacheLength
    global productIdCache,productIdCount,productBranchCache
    global uriIdCache,uriIdCount
    global osIdCache,osIdCount
    if not productIdCache:
      if maxProductIdCacheLength:
        productIdCache,productIdCount = initializeIdCache(('product','version'),'id','productdims',self.cursor)
        productBranchCache = initializeProductBranchCache(productIdCache,self.cursor)
    if not uriIdCache:
      if maxUriIdCacheLength:
        uriIdCache, uriIdCount = initializeIdCache(('domain','url'),'id','urldims',self.cursor)
    if not osIdCache:
      if maxOsIdCacheLength:
        osIdCache,osIdCount = initializeIdCache(('os_name','os_version',),'id','osdims',self.cursor)

  #---------------------------------------------------------------------------------------------------------------
  def assureAndGetId(self, key, table, getSql, putSql, cacheMap, countMap, dkey=None):
    """
    If possible, get the cached id associated with key and update the cache count.
    If not, then assure the data in (dkey, else key) is available in the database, and get the id from table
    If caching is turned on (cacheMap is not None), then cache the key and its id, and update count
    return the id, which may be None if all attempts to get the id fail.
    Called by individual getSomeKindId() methods
    key is a tuple, suitable for key in a dictionary. Must be present if caching is turned on.
    dkey is a dictionary, suitable as data for select and insert statements. It may be null if key alone is sufficient for insert
    """
    sqlKey = key
    if dkey: sqlKey = dkey
    id = None
    if None != cacheMap:
      try:
        id = cacheMap[key]
        countMap[key] += 1
      except KeyError:
        pass
    if not id:
      self.cursor.execute(getSql,sqlKey)
      self.cursor.connection.rollback() # we didn't change the data, no need to commit
      try:
        id = self.cursor.fetchone()[0]
        if None != cacheMap:
          cacheMap[key] = id
          countMap[key] = 1
      except (IndexError, TypeError): # might be empty list or None
        try:
          self.cursor.execute(putSql,sqlKey)
          self.cursor.execute('SELECT lastval()')
          self.cursor.connection.commit()
          id = self.cursor.fetchone()[0]
          if None != cacheMap:
            cacheMap[key] = id
            countMap[key] = 1
        except psycopg2.IntegrityError,x: # in case of race condition
          logger.info("%s - Failed (%s) insert %s into %s",threading.currentThread().getName(),x,key,table)
          self.cursor.connection.rollback()
          self.cursor.execute(getSql,sqlKey)
          try:
            uriId = self.cursor.fetchone()[0]
            self.cursor.connection.commit()
            if None != cacheMap:
              cacheMap[key] = id
              countMap[key] = 1
          except (IndexError, TypeError):
            logger.error("%s - Unable to SELECT %s.id for (%s). Giving up.",threading.currentThread().getName(),table,key)
    return id

  #---------------------------------------------------------------------------------------------------------------
  # these 'knownProtocols' are here in case we ever want to use them. Not now consulted to see if a protocol is 'legal'
  knownProtocols = set([
    # from http://en.wikipedia.org/wiki/WYCIWYG and http://en.wikipedia.org/wiki/URI_scheme#Official_IANA-registered_schemes
    # 'official'
    'aaa', 'aaas', 'acap', 'cap', 'cid', 'crid', 'data', 'dav', 'dict', 'dns', 'fax', 'file', 'ftp', 'go', 'gopher','h323',
    'http', 'https', 'icap', 'im', 'imap', 'info', 'ipp', 'iris', 'iris.beep', 'iris.xpc', 'iris.xpcs', 'iris.lws', 'ldap',
    'mailto', 'mid', 'modem', 'msrp', 'msrps', 'mtqp', 'mupdate', 'news', 'nfs', 'nntp', 'pop', 'pres', 'prospero', 'rtsp',
    'service', 'shttp', 'sip', 'sips', 'snmp', 'soap.beep', 'soap.beeps', 'tag', 'tel', 'telnet', 'tftp', 'tip', 'tv', 'urn',
    'vemmi', 'wais', 'xmlrpc.beep', 'xmpp', 'z39.50r', 'z39.50s',
    # 'unofficial but common'
    'about', 'afp', 'aim', 'apt', 'aw', 'bolo', 'bzr', 'callto', 'cel', 'chrome', 'content', 'cvs', 'daap', 'doi', 'ed2k',
    'feed', 'finger', 'fish', 'gg', 'git', 'gizmoproject', 'iax2', 'irc', 'ircs', 'itms', 'jar', 'javascript', 'lastfm',
    'ldaps', 'magnet', 'mms', 'msnim', 'mvn', 'notes', 'psyc', 'rmi', 'rsync', 'secondlife', 'sftp', 'sgn', 'skype', 'smb',
    'ssh', 'sftp', 'smb', 'sms', 'soldat', 'steam', 'svn', 'unreal', 'ut2004', 'view-source', 'vzochat', 'webcal', 'wtai',
    'wyciwyg', 'xfire', 'xri', 'ymsgr',
  ])
  # Bug 532500: further restrict the tail group to end with [?&=;] (was: [?])
  URIstring = r'^(?P<uri>(?P<proto>\w+):(?P<lead>//)?(?P<domain>[^/]+)?(?P<tail>[^?&=;]*))(?P<query>.*)$'
  uriPattern = re.compile(URIstring)
  def getUrlId(self,fullUrl):
    """
    Get the uri id given a full string. Cache results. Clean cache if length is too great.
    Note that the 'full url' that is stored will be truncated at any of [?&=;] after the first '/'
    Note that the 'full url' that is stored may be truncated at self.truncateUrlLength if set
    """
    global uriIdCache,uriIdCount
    uriId = None
    queryPart = ''
    if not fullUrl:
      return uriId,queryPart
    m = IdCache.uriPattern.match(fullUrl.strip())
    if not m:
      logger.warn("%s - Illegal url '%s' not parsed",threading.currentThread().getName(),fullUrl)
      return uriId,queryPart
    dpart = m.group('domain')
    if not dpart:
      if not m.group('lead'): # chrome:// and wyciwyg:// are legal, but not chrome: or wyciwyg:
        return None,''
      dpart = ''
    upart = m.group('uri').rstrip('/')
    if(self.truncateUrlLength and upart):
      logger.info('Truncating url from "%s" to "%s"',upart,upart[:self.truncateUrlLength])
      upart = upart[:self.truncateUrlLength]
    key = (dpart, upart)
    queryPart = m.group('query')
    uriId = self.assureAndGetId(key,'urldims',
                                "SELECT id FROM urldims WHERE domain=%s and url=%s",
                                "INSERT INTO urldims (domain,url) VALUES (%s,%s)",
                                uriIdCache, uriIdCount)
    return uriId,queryPart

  #---------------------------------------------------------------------------------------------------------------
  def getBestBranch(self,pvKey):
    """
    Look up branch by key (product,version). If unavailable:
     SELECT WHERE product=product ORDER BY id DESC LIMIT 1 -- assume id is in date order
     if THAT is unavailable return None
    """
    global productBranchCache
    id = branch = None
    if None != productIdCache:
      id = productIdCache.get(pvKey)
    if id:
      branch = productBranchCache.get(id)
    if branch:
      return branch
    elif id:
      self.cursor.execute("SELECT branch from productdims WHERE product = %s AND version = %s",(pvKey[0],pvKey[1]))
      self.cursor.connection.rollback()
      try:
        branch = self.cursor.fetchone()[0]
        if None != productBranchCache:
          productBranchCache['id'] = branch
        return branch
      except (IndexError, TypeError): # might be empty list or None
        pass
    # no cached branch, no id, no branch in db. begin heuristic:
    self.cursor.execute("SELECT branch FROM productdims WHERE product = %s ORDER BY id DESC LIMIT 1",(pvKey[0],))
    self.cursor.connection.rollback()
    try:
      branch = self.cursor.fetchone()[0]
      logger.warn("Interpolating branch (%s) for product,version %s)",branch,str(pvKey))
      return branch
    except:
      return None

  #---------------------------------------------------------------------------------------------------------------
  def getProductId(self,product,version,branch=''):
    """
    Get product id given a product and version. Cache results. Clean cache if length is too great.
    """
    global productIdCache,productIdCount
    productId = None
    if not product or not version:
      return productId
    if not branch:
      branch = self.getBestBranch((product,version))
    if not branch:
      # Fail if we don't have a reasonable idea of the correct gecko version aka branch
      return productId
    release = createProductRelease(version)
    key = (product.strip(),version.strip())
    dkey = {'product':key[0],'version':key[1],'branch':branch.strip(),'release':release}
    productId = self.assureAndGetId(key,'productdims',
                                    """SELECT id FROM productdims WHERE product=%(product)s and version=%(version)s""",
                                    """INSERT INTO productdims (product,version,branch,release)
                                             VALUES (%(product)s,%(version)s,%(branch)s,%(release)s)""",
                                productIdCache, productIdCount, dkey=dkey)
    return productId

  #-----------------------------------------------------------------------------------------------------------------
  def getAppropriateOsVersion(self, name,origVersion):
    """
    If this is a linux os, chop out all the gubbish retaining only the actual version numbers
    and, if available, the architecture name. Uses Regular expressions as:
    Is this a legal Linux version string?
    linuxLineRE = re.compile(r'0\.0\.0 [lL]inux.+[lL]inux$|[0-9.]+.+(i586|i686|sun4u|i86pc|x86_64)?')

    If FULL legal Linux version string, substitute "\2 \3"
    linuxVersionRE = re.compile(r'(0\.0\.0 [lL]inux.)?([0-9.]+[0-9]).*(i586|i686|sun4u|i86pc|x86_64).*')

    If TRUNCATED legal Linux version string, substitute "\2 ?arch?"
    linuxShortVersionRE = re.compile(r'(0\.0\.0 [lL]inux.)?([0-9.]+[0-9]).*')
    """
    ret = origVersion
    if 'Linux' != name:
      pass
    elif not IdCache.linuxLineRE.match(origVersion):
      ret = ''
    else:
      m = IdCache.linuxVersionRE.sub(r'\2 \3',origVersion)
      ret = m
      if origVersion == m:
        m = IdCache.linuxShortVersionRE.sub(r'\2',origVersion)
        ret = "%s ?arch?"%(m)
        if origVersion == m:
          ret = ''
    return ret

  #-----------------------------------------------------------------------------------------------------------------
  def getOsId(self,osName,osVersion):
    """
    Get the os id given the name and version. Cache results. Clean cache if length is too great.
    """
    global osIdCache, osIdCount
    osId = None
    if None != osName:
      osName = osName.strip()
    if None != osVersion:
      osVersion = osVersion.strip()
    key = (osName,self.getAppropriateOsVersion(osName,osVersion))
    osId = self.assureAndGetId(key,'osdims',
                               "SELECT id FROM osdims WHERE os_name=%s and os_version=%s",
                               "INSERT INTO osdims (os_name,os_version) VALUES (%s,%s)",
                                osIdCache, osIdCount)
    return osId
