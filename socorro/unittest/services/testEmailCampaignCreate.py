# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socorro.unittest.testlib.expectations as expect
import socorro.services.emailCampaignCreate as ecc
import socorro.lib.util as util

from socorro.database.schema import EmailCampaignsTable

from socorro.lib.datetimeutil import UTC, utc_now

from datetime import datetime, timedelta

#-----------------------------------------------------------------------------------------------------------------
def getDummyContext():
  context = util.DotDict()
  context.database_hostname = 'fred'
  context.database_name = 'wilma'
  context.database_username = 'ricky'
  context.database_password = 'lucy'
  context.database_port = 127
  context.smtpHostname = 'localhost'
  context.smtpPort = 25
  context.smtpUsername = None
  context.smtpPassword = None
  context.unsubscribeBaseUrl = 'http://example.com/unsubscribe/%s'
  context.fromEmailAddress = 'from@example.com'
  return context

#-----------------------------------------------------------------------------------------------------------------
def testCreateEmailCampaign():
  context = getDummyContext()

  product = 'Foobar'
  versions = '5'
  signature = 'JohnHancock'
  start_date = utc_now()
  end_date = start_date + timedelta(hours=1)
  # FIXME where should this go?
  end_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59,
                      tzinfo=UTC)
  subject = 'test subject'
  body = 'test body'
  author = 'John Doe'
  email_count = 0

  parameters = {
    'product': product,
    'versions': versions,
    'signature': signature,
  }

  version_clause = ''
  if len(versions) > 0:
    version_clause = " version IN %(versions)s AND "

  sql = """
        SELECT DISTINCT contacts.id, reports.email, reports.client_crash_date AS crash_date, reports.uuid AS ooid, contacts.subscribe_token
        FROM reports
        LEFT JOIN email_contacts AS contacts ON reports.email = contacts.email
        WHERE TIMESTAMP WITH TIME ZONE '%s' <= reports.date_processed AND
              TIMESTAMP WITH TIME ZONE '%s' > reports.date_processed AND
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
  dummyCursor.expect('mogrify', (sql, parameters), {}, None)
  dummyCursor.expect('execute', (sql, parameters), {}, None)
  dummyCursor.expect('fetchall', (), {}, [('0','one@example.com','abc','def',None)])

  parameters = [product, versions, signature, subject, body, start_date, end_date, email_count, author]
  logger = util.FakeLogger()
  table = EmailCampaignsTable(logger)
  sql = table.insertSql
  dummyCursor.expect('mogrify', (sql, parameters), {}, None)
  dummyCursor.expect('execute', (sql, parameters), {}, None)
  dummyCursor.expect('fetchone', (), {}, ['1234'])

  campaign = ecc.EmailCampaignCreate(context)
  campaignId = campaign.create_email_campaign(dummyCursor, product, versions, signature, subject, body, start_date, end_date, author)
  assert campaignId == ('1234', [{'token': None, 'crash_date': 'abc', 'id': '0', 'ooid': 'def', 'email': 'one@example.com'}])

#-----------------------------------------------------------------------------------------------------------------
def testDetermineEmails():
  context = getDummyContext()

  product = 'Foobar'
  versions = '5'
  signature = 'JohnHancock'
  start_date = utc_now()
  end_date = start_date + timedelta(hours=1)

  parameters = {
    'product': product,
    'versions': versions,
    'signature': signature,
  }

  version_clause = ''
  if len(versions) > 0:
    version_clause = " version IN %(versions)s AND "

  sql = """
        SELECT DISTINCT contacts.id, reports.email, reports.client_crash_date AS crash_date, reports.uuid AS ooid, contacts.subscribe_token
        FROM reports
        LEFT JOIN email_contacts AS contacts ON reports.email = contacts.email
        WHERE TIMESTAMP WITH TIME ZONE '%s' <= reports.date_processed AND
              TIMESTAMP WITH TIME ZONE '%s' > reports.date_processed AND
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
  dummyCursor.expect('mogrify', (sql, parameters), {}, None)
  dummyCursor.expect('execute', (sql, parameters), {}, None)
  dummyCursor.expect('fetchall', (), {}, [])

  campaign = ecc.EmailCampaignCreate(context)
  email_rows = campaign.determine_emails(dummyCursor, product, versions, signature, start_date, end_date)

def testEnsureContacts():
  context = getDummyContext()

  parameters = [('me@example.com', 'd64298ce-6217-4a97-917b-7c18d3f67e18', 'abcdefg', '2011-09-01 00:00')]
  sql = """INSERT INTO email_contacts (email, subscribe_token) VALUES (%s, %s) RETURNING id"""
  sql = """INSERT INTO email_contacts (email, subscribe_token, ooid, crash_date) VALUES (%s, %s, %s, %s) RETURNING id"""
  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('executemany', (sql, parameters), {}, None)

  # with dbID already set
  campaign = ecc.EmailCampaignCreate(context)
  email_rows = [('1234', 'me@example.com', '2011-09-01 00:00', 'abcdefg', 'hijklmn')]

  full_email_rows = campaign.ensure_contacts(dummyCursor, email_rows)
  assert full_email_rows == [{'token': 'hijklmn', 'crash_date': '2011-09-01 00:00', 'id': '1234', 'ooid': 'abcdefg', 'email': 'me@example.com'}]

  # without dbID set
  # FIXME this now returns the token which is unpredictable, need to make this more testable
  #email_rows = [(None, 'me@example.com', '2011-09-01 00:00', 'abcdefg', 'hijklmn')]
  #full_email_rows = campaign.ensure_contacts(dummyCursor, email_rows)
  #assert full_email_rows == [{'token': 'abcdefg', 'id': None, 'email': 'me@example.com'}]

def testSaveCampaign():
  context = getDummyContext()

  product = 'Foobar'
  versions = '5'
  signature = 'JohnHancock'
  subject = 'email subject'
  body = 'email body'
  start_date = utc_now()
  end_date = start_date + timedelta(hours=1)
  author = 'me@example.com'
  email_count = 0

  parameters = (product, versions, signature, subject, body, start_date, end_date, email_count, author)

  sql =  """INSERT INTO email_campaigns (product, versions, signature, subject, body, start_date, end_date, email_count, author)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('mogrify', (sql, list(parameters)), {}, None)
  dummyCursor.expect('execute', (sql, list(parameters)), {}, None)
  dummyCursor.expect('fetchone', (), {}, ['123'])

  campaign = ecc.EmailCampaignCreate(context)
  campaignId = campaign.save_campaign(dummyCursor, product, versions, signature, subject, body, start_date, end_date, author)

  assert campaignId == '123'

