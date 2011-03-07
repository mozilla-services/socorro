import socorro.unittest.testlib.expectations as expect
import socorro.services.emailCampaignCreate as ecc
import socorro.lib.util as util

from datetime import datetime, timedelta

#-----------------------------------------------------------------------------------------------------------------
def getDummyContext():
  context = util.DotDict()
  context.databaseHost = 'fred'
  context.databaseName = 'wilma'
  context.databaseUserName = 'ricky'
  context.databasePassword = 'lucy'
  context.databasePort = 127
  context.smtpHostname = 'localhost'
  context.smtpPort = 25
  context.smtpUsername = None
  context.smtpPassword = None
  context.unsubscribeBaseUrl = 'http://example.com/unsubscribe/%s'
  context.fromEmailAddress = 'from@example.com'
  return context

#-----------------------------------------------------------------------------------------------------------------
def testDetermineEmails():
  context = getDummyContext()

  product = 'Foobar'
  versions = '5'
  signature = 'JohnHancock'
  start_date = datetime.now()
  end_date = datetime.now() + timedelta(hours=1)

  parameters = {
    'product': product,
    'versions': versions,
    'signature': signature,
  }

  version_clause = ''
  if len(versions) > 0:
    version_clause = " version IN %(versions)s AND "

  sql = """
        SELECT DISTINCT contacts.id, reports.email, contacts.subscribe_token
        FROM reports
        LEFT JOIN email_contacts AS contacts ON reports.email = contacts.email
        WHERE TIMESTAMP WITHOUT TIME ZONE '%s' <= reports.date_processed AND
              TIMESTAMP WITHOUT TIME ZONE '%s' > reports.date_processed AND
              reports.product = %%(product)s AND
              %s
              reports.signature = %%(signature)s AND
              LENGTH(reports.email) > 4 AND
              contacts.subscribe_status IS NOT FALSE
              AND contacts.email NOT IN (
                  SELECT contacted.email
                  FROM email_campaigns AS prev_campaigns
                  JOIN email_campaigns_contacts ON email_campaigns_contacts.email_campaigns_id = prev_campaigns.id
                  JOIN email_contacts AS contacted ON email_campaigns_contacts.email_contacts_id = contacted.id
                  WHERE prev_campaigns.product = %%(product)s
                  AND prev_campaigns.signature = %%(signature)s
             ) """ % (start_date, end_date, version_clause)


  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)
  dummyCursor.expect('fetchall', (), {}, [])

  campaign = ecc.EmailCampaignCreate(context)
  email_rows = campaign.determine_emails(dummyCursor, product, versions, signature, start_date, end_date)

def testEnsureContacts():
  context = getDummyContext()

  parameters = [('me@example.com', 'abcdefg')]
  sql = """INSERT INTO email_contacts (email, subscribe_token) VALUES (%s, %s) RETURNING id"""
  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('executemany', (sql, parameters), {}, None)

  # with dbID already set
  campaign = ecc.EmailCampaignCreate(context)
  email_rows = [['1234', 'me@example.com', 'abcdefg']]
  full_email_rows = campaign.ensure_contacts(dummyCursor, email_rows)
  assert full_email_rows == [{'token': 'abcdefg', 'id': '1234', 'email': 'me@example.com'}]

  # without dbID set
  email_rows = [[None, 'me@example.com', None]]
  full_email_rows = campaign.ensure_contacts(dummyCursor, email_rows, 'abcdefg')
  assert full_email_rows == [{'token': 'abcdefg', 'id': None, 'email': 'me@example.com'}]

def testSaveCampaign():
  context = getDummyContext()

  product = 'Foobar'
  versions = '5'
  signature = 'JohnHancock'
  subject = 'email subject'
  body = 'email body'
  start_date = datetime.now()
  end_date = datetime.now() + timedelta(hours=1)
  author = 'me@example.com'
  email_count = 0

  parameters = (product, versions, signature, subject, body, start_date, end_date, email_count, author)

  sql =  """INSERT INTO email_campaigns (product, versions, signature, subject, body, start_date, end_date, email_count, author)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, list(parameters)), {}, None)
  dummyCursor.expect('fetchone', (), {}, ['123'])

  campaign = ecc.EmailCampaignCreate(context)
  campaignId = campaign.save_campaign(dummyCursor, product, versions, signature, subject, body, start_date, end_date, author)

  assert campaignId == '123'

def testSendAllEmails():
  context = getDummyContext()

  testContacts = ['1@example.com', '2@example.com']
  contacts = [
    {'email': testContacts[0], 'token': 'abc'},
    {'email': testContacts[1], 'token': 'def'},
  ]
  subject = 'email subject'
  body = 'email body'

  dummySmtp = expect.DummyObjectWithExpectations()
  # no variables
  noVarBody = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keQ==\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], noVarBody % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], noVarBody % testContacts[1]), {}, None)

  campaign = ecc.EmailCampaignCreate(context)
  contacted_emails = campaign.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == [testContacts[0], testContacts[1]]

  # unsubscribe variable
  unsubVarBody1 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSBodHRwOi8vZXhhbXBsZS5jb20vdW5zdWJzY3JpYmUvYWJj\n'
  unsubVarBody2 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSBodHRwOi8vZXhhbXBsZS5jb20vdW5zdWJzY3JpYmUvZGVm\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], unsubVarBody1 % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], unsubVarBody2 % testContacts[1]), {}, None)

  body = 'email body *|UNSUBSCRIBE_URL|*'
  contacted_emails = campaign.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == [testContacts[0], testContacts[1]]

  # email_address variable
  emailVarBody1 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSAxQGV4YW1wbGUuY29t\n'
  emailVarBody2 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSAyQGV4YW1wbGUuY29t\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], emailVarBody1 % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], emailVarBody2 % testContacts[1]), {}, None)

  body = 'email body *|EMAIL_ADDRESS|*'
  contacted_emails = campaign.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == [testContacts[0], testContacts[1]]

def testSaveCampaignContacts():
  context = getDummyContext()

  campaign_id = 123
  contacted_emails = ['1@example.com', '2@example.com']

  sql = """
        INSERT INTO email_campaigns_contacts (email_campaigns_id, email_contacts_id)
          SELECT %(campaign_id)s, email_contacts.id
          FROM email_contacts
          WHERE email IN %(emails)s
      """
  parameters = {'campaign_id': campaign_id, 'emails': tuple(contacted_emails)}

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)

  campaign = ecc.EmailCampaignCreate(context)
  assert campaign.save_campaign_contacts(dummyCursor, campaign_id, contacted_emails) == None

def testUpdateCampaign():
  context = getDummyContext()

  campaign_id = 123
  email_count = 321

  sql = """UPDATE email_campaigns SET email_count = %s WHERE id = %s"""
  parameters = (email_count, campaign_id)

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)

  campaign = ecc.EmailCampaignCreate(context)
  assert campaign.update_campaign(dummyCursor, campaign_id, email_count) == None
import socorro.unittest.testlib.expectations as expect
import socorro.services.emailCampaignCreate as ecc
import socorro.lib.util as util

from datetime import datetime, timedelta

#-----------------------------------------------------------------------------------------------------------------
def getDummyContext():
  context = util.DotDict()
  context.databaseHost = 'fred'
  context.databaseName = 'wilma'
  context.databaseUserName = 'ricky'
  context.databasePassword = 'lucy'
  context.databasePort = 127
  context.smtpHostname = 'localhost'
  context.smtpPort = 25
  context.smtpUsername = None
  context.smtpPassword = None
  context.unsubscribeBaseUrl = 'http://example.com/unsubscribe/%s'
  context.fromEmailAddress = 'from@example.com'
  return context

#-----------------------------------------------------------------------------------------------------------------
def testDetermineEmails():
  context = getDummyContext()

  product = 'Foobar'
  versions = '5'
  signature = 'JohnHancock'
  start_date = datetime.now()
  end_date = datetime.now() + timedelta(hours=1)

  parameters = {
    'product': product,
    'versions': versions,
    'signature': signature,
  }

  version_clause = ''
  if len(versions) > 0:
    version_clause = " version IN %(versions)s AND "

  sql = """
        SELECT DISTINCT contacts.id, reports.email, contacts.subscribe_token
        FROM reports
        LEFT JOIN email_contacts AS contacts ON reports.email = contacts.email
        WHERE TIMESTAMP WITHOUT TIME ZONE '%s' <= reports.date_processed AND
              TIMESTAMP WITHOUT TIME ZONE '%s' > reports.date_processed AND
              reports.product = %%(product)s AND
              %s
              reports.signature = %%(signature)s AND
              LENGTH(reports.email) > 4 AND
              contacts.subscribe_status IS NOT FALSE
              AND contacts.email NOT IN (
                  SELECT contacted.email
                  FROM email_campaigns AS prev_campaigns
                  JOIN email_campaigns_contacts ON email_campaigns_contacts.email_campaigns_id = prev_campaigns.id
                  JOIN email_contacts AS contacted ON email_campaigns_contacts.email_contacts_id = contacted.id
                  WHERE prev_campaigns.product = %%(product)s
                  AND prev_campaigns.signature = %%(signature)s
             ) """ % (start_date, end_date, version_clause)


  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)
  dummyCursor.expect('fetchall', (), {}, [])

  campaign = ecc.EmailCampaignCreate(context)
  email_rows = campaign.determine_emails(dummyCursor, product, versions, signature, start_date, end_date)

def testEnsureContacts():
  context = getDummyContext()

  parameters = [('me@example.com', 'abcdefg')]
  sql = """INSERT INTO email_contacts (email, subscribe_token) VALUES (%s, %s) RETURNING id"""
  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('executemany', (sql, parameters), {}, None)

  # with dbID already set
  campaign = ecc.EmailCampaignCreate(context)
  email_rows = [['1234', 'me@example.com', 'abcdefg']]
  full_email_rows = campaign.ensure_contacts(dummyCursor, email_rows)
  assert full_email_rows == [{'token': 'abcdefg', 'id': '1234', 'email': 'me@example.com'}]

  # without dbID set
  email_rows = [[None, 'me@example.com', None]]
  full_email_rows = campaign.ensure_contacts(dummyCursor, email_rows, 'abcdefg')
  assert full_email_rows == [{'token': 'abcdefg', 'id': None, 'email': 'me@example.com'}]

def testSaveCampaign():
  context = getDummyContext()

  product = 'Foobar'
  versions = '5'
  signature = 'JohnHancock'
  subject = 'email subject'
  body = 'email body'
  start_date = datetime.now()
  end_date = datetime.now() + timedelta(hours=1)
  author = 'me@example.com'
  email_count = 0

  parameters = (product, versions, signature, subject, body, start_date, end_date, email_count, author)

  sql =  """INSERT INTO email_campaigns (product, versions, signature, subject, body, start_date, end_date, email_count, author)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, list(parameters)), {}, None)
  dummyCursor.expect('fetchone', (), {}, ['123'])

  campaign = ecc.EmailCampaignCreate(context)
  campaignId = campaign.save_campaign(dummyCursor, product, versions, signature, subject, body, start_date, end_date, author)

  assert campaignId == '123'

def testSendAllEmails():
  context = getDummyContext()

  testContacts = ['1@example.com', '2@example.com']
  contacts = [
    {'email': testContacts[0], 'token': 'abc'},
    {'email': testContacts[1], 'token': 'def'},
  ]
  subject = 'email subject'
  body = 'email body'

  dummySmtp = expect.DummyObjectWithExpectations()
  # no variables
  noVarBody = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keQ==\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], noVarBody % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], noVarBody % testContacts[1]), {}, None)

  campaign = ecc.EmailCampaignCreate(context)
  contacted_emails = campaign.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == [testContacts[0], testContacts[1]]

  # unsubscribe variable
  unsubVarBody1 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSBodHRwOi8vZXhhbXBsZS5jb20vdW5zdWJzY3JpYmUvYWJj\n'
  unsubVarBody2 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSBodHRwOi8vZXhhbXBsZS5jb20vdW5zdWJzY3JpYmUvZGVm\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], unsubVarBody1 % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], unsubVarBody2 % testContacts[1]), {}, None)

  body = 'email body *|UNSUBSCRIBE_URL|*'
  contacted_emails = campaign.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == [testContacts[0], testContacts[1]]

  # email_address variable
  emailVarBody1 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSAxQGV4YW1wbGUuY29t\n'
  emailVarBody2 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSAyQGV4YW1wbGUuY29t\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], emailVarBody1 % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], emailVarBody2 % testContacts[1]), {}, None)

  body = 'email body *|EMAIL_ADDRESS|*'
  contacted_emails = campaign.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == [testContacts[0], testContacts[1]]

def testSaveCampaignContacts():
  context = getDummyContext()

  campaign_id = 123
  contacted_emails = ['1@example.com', '2@example.com']

  sql = """
        INSERT INTO email_campaigns_contacts (email_campaigns_id, email_contacts_id)
          SELECT %(campaign_id)s, email_contacts.id
          FROM email_contacts
          WHERE email IN %(emails)s
      """
  parameters = {'campaign_id': campaign_id, 'emails': tuple(contacted_emails)}

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)

  campaign = ecc.EmailCampaignCreate(context)
  assert campaign.save_campaign_contacts(dummyCursor, campaign_id, contacted_emails) == None

def testUpdateCampaign():
  context = getDummyContext()

  campaign_id = 123
  email_count = 321

  sql = """UPDATE email_campaigns SET email_count = %s WHERE id = %s"""
  parameters = (email_count, campaign_id)

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)

  campaign = ecc.EmailCampaignCreate(context)
  assert campaign.update_campaign(dummyCursor, campaign_id, email_count) == None
import socorro.unittest.testlib.expectations as expect
import socorro.services.emailCampaignCreate as ecc
import socorro.lib.util as util

from datetime import datetime, timedelta

#-----------------------------------------------------------------------------------------------------------------
def getDummyContext():
  context = util.DotDict()
  context.databaseHost = 'fred'
  context.databaseName = 'wilma'
  context.databaseUserName = 'ricky'
  context.databasePassword = 'lucy'
  context.databasePort = 127
  context.smtpHostname = 'localhost'
  context.smtpPort = 25
  context.smtpUsername = None
  context.smtpPassword = None
  context.unsubscribeBaseUrl = 'http://example.com/unsubscribe/%s'
  context.fromEmailAddress = 'from@example.com'
  return context

#-----------------------------------------------------------------------------------------------------------------
def testDetermineEmails():
  context = getDummyContext()

  product = 'Foobar'
  versions = '5'
  signature = 'JohnHancock'
  start_date = datetime.now()
  end_date = datetime.now() + timedelta(hours=1)

  parameters = {
    'product': product,
    'versions': versions,
    'signature': signature,
  }

  version_clause = ''
  if len(versions) > 0:
    version_clause = " version IN %(versions)s AND "

  sql = """
        SELECT DISTINCT contacts.id, reports.email, contacts.subscribe_token
        FROM reports
        LEFT JOIN email_contacts AS contacts ON reports.email = contacts.email
        WHERE TIMESTAMP WITHOUT TIME ZONE '%s' <= reports.date_processed AND
              TIMESTAMP WITHOUT TIME ZONE '%s' > reports.date_processed AND
              reports.product = %%(product)s AND
              %s
              reports.signature = %%(signature)s AND
              LENGTH(reports.email) > 4 AND
              contacts.subscribe_status IS NOT FALSE
              AND contacts.email NOT IN (
                  SELECT contacted.email
                  FROM email_campaigns AS prev_campaigns
                  JOIN email_campaigns_contacts ON email_campaigns_contacts.email_campaigns_id = prev_campaigns.id
                  JOIN email_contacts AS contacted ON email_campaigns_contacts.email_contacts_id = contacted.id
                  WHERE prev_campaigns.product = %%(product)s
                  AND prev_campaigns.signature = %%(signature)s
             ) """ % (start_date, end_date, version_clause)


  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)
  dummyCursor.expect('fetchall', (), {}, [])

  campaign = ecc.EmailCampaignCreate(context)
  email_rows = campaign.determine_emails(dummyCursor, product, versions, signature, start_date, end_date)

def testEnsureContacts():
  context = getDummyContext()

  parameters = [('me@example.com', 'abcdefg')]
  sql = """INSERT INTO email_contacts (email, subscribe_token) VALUES (%s, %s) RETURNING id"""
  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('executemany', (sql, parameters), {}, None)

  # with dbID already set
  campaign = ecc.EmailCampaignCreate(context)
  email_rows = [['1234', 'me@example.com', 'abcdefg']]
  full_email_rows = campaign.ensure_contacts(dummyCursor, email_rows)
  assert full_email_rows == [{'token': 'abcdefg', 'id': '1234', 'email': 'me@example.com'}]

  # without dbID set
  email_rows = [[None, 'me@example.com', None]]
  full_email_rows = campaign.ensure_contacts(dummyCursor, email_rows, 'abcdefg')
  assert full_email_rows == [{'token': 'abcdefg', 'id': None, 'email': 'me@example.com'}]

def testSaveCampaign():
  context = getDummyContext()

  product = 'Foobar'
  versions = '5'
  signature = 'JohnHancock'
  subject = 'email subject'
  body = 'email body'
  start_date = datetime.now()
  end_date = datetime.now() + timedelta(hours=1)
  author = 'me@example.com'
  email_count = 0

  parameters = (product, versions, signature, subject, body, start_date, end_date, email_count, author)

  sql =  """INSERT INTO email_campaigns (product, versions, signature, subject, body, start_date, end_date, email_count, author)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, list(parameters)), {}, None)
  dummyCursor.expect('fetchone', (), {}, ['123'])

  campaign = ecc.EmailCampaignCreate(context)
  campaignId = campaign.save_campaign(dummyCursor, product, versions, signature, subject, body, start_date, end_date, author)

  assert campaignId == '123'

def testSendAllEmails():
  context = getDummyContext()

  testContacts = ['1@example.com', '2@example.com']
  contacts = [
    {'email': testContacts[0], 'token': 'abc'},
    {'email': testContacts[1], 'token': 'def'},
  ]
  subject = 'email subject'
  body = 'email body'

  dummySmtp = expect.DummyObjectWithExpectations()
  # no variables
  noVarBody = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keQ==\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], noVarBody % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], noVarBody % testContacts[1]), {}, None)

  campaign = ecc.EmailCampaignCreate(context)
  contacted_emails = campaign.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == [testContacts[0], testContacts[1]]

  # unsubscribe variable
  unsubVarBody1 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSBodHRwOi8vZXhhbXBsZS5jb20vdW5zdWJzY3JpYmUvYWJj\n'
  unsubVarBody2 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSBodHRwOi8vZXhhbXBsZS5jb20vdW5zdWJzY3JpYmUvZGVm\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], unsubVarBody1 % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], unsubVarBody2 % testContacts[1]), {}, None)

  body = 'email body *|UNSUBSCRIBE_URL|*'
  contacted_emails = campaign.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == [testContacts[0], testContacts[1]]

  # email_address variable
  emailVarBody1 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSAxQGV4YW1wbGUuY29t\n'
  emailVarBody2 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSAyQGV4YW1wbGUuY29t\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], emailVarBody1 % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], emailVarBody2 % testContacts[1]), {}, None)

  body = 'email body *|EMAIL_ADDRESS|*'
  contacted_emails = campaign.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == [testContacts[0], testContacts[1]]

def testSaveCampaignContacts():
  context = getDummyContext()

  campaign_id = 123
  contacted_emails = ['1@example.com', '2@example.com']

  sql = """
        INSERT INTO email_campaigns_contacts (email_campaigns_id, email_contacts_id)
          SELECT %(campaign_id)s, email_contacts.id
          FROM email_contacts
          WHERE email IN %(emails)s
      """
  parameters = {'campaign_id': campaign_id, 'emails': tuple(contacted_emails)}

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)

  campaign = ecc.EmailCampaignCreate(context)
  assert campaign.save_campaign_contacts(dummyCursor, campaign_id, contacted_emails) == None

def testUpdateCampaign():
  context = getDummyContext()

  campaign_id = 123
  email_count = 321

  sql = """UPDATE email_campaigns SET email_count = %s WHERE id = %s"""
  parameters = (email_count, campaign_id)

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)

  campaign = ecc.EmailCampaignCreate(context)
  assert campaign.update_campaign(dummyCursor, campaign_id, email_count) == None
