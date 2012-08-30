# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
from operator import itemgetter
import logging
import sys
import threading
import time

import psycopg2

logger = logging.getLogger("cachedIdAccess")


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
