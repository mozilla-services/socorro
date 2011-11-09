import socorro.unittest.testlib.expectations as expect
import socorro.services.emailSender as es
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
  context.crashBaseUrl = 'test/%s'
  return context

def testSendAllEmails():
  context = getDummyContext()

  testContacts = ['1@example.com', '2@example.com']
  crash_date = datetime.strptime('2011-09-01', '%Y-%m-%d')
  contacts = [
    (0, testContacts[0], 'abc', 'ooid1', crash_date),
    (0, testContacts[1], 'abc', 'ooid2', crash_date)
  ]
  subject = 'email subject'
  body = 'email body'

  dummySmtp = expect.DummyObjectWithExpectations()
  # no variables
  noVarBody = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keQ==\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], noVarBody % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], noVarBody % testContacts[1]), {}, None)

  sender = es.EmailSender(context)
  contacted_emails = sender.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == {0: 'sent'}

# FIXME 
#  # unsubscribe variable
#  unsubVarBody1 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSBodHRwOi8vZXhhbXBsZS5jb20vdW5zdWJzY3JpYmUvYWJj\n'
#  unsubVarBody2 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSBodHRwOi8vZXhhbXBsZS5jb20vdW5zdWJzY3JpYmUvZGVm\n'
#  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], unsubVarBody1 % testContacts[0]), {}, None)
#  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], unsubVarBody2 % testContacts[1]), {}, None)
#
#  body = 'email body *|UNSUBSCRIBE_URL|*'
#  contacted_emails = sender.send_all_emails(contacts, subject, body, dummySmtp)
#  print contacted_emails
  #assert contacted_emails == [testContacts[0], testContacts[1]]

  # email_address variable
  emailVarBody1 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSAxQGV4YW1wbGUuY29t\n'
  emailVarBody2 = 'Content-Type: text/plain; charset="utf-8"\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\nFrom: from@example.com\nSubject: email subject\nTo: %s\n\nZW1haWwgYm9keSAyQGV4YW1wbGUuY29t\n'
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[0]], emailVarBody1 % testContacts[0]), {}, None)
  dummySmtp.expect('sendmail', (context.fromEmailAddress, [testContacts[1]], emailVarBody2 % testContacts[1]), {}, None)

  body = 'email body *|EMAIL_ADDRESS|*'
  contacted_emails = sender.send_all_emails(contacts, subject, body, dummySmtp)
  assert contacted_emails == {0: 'sent'}

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

  sender = es.EmailSender(context)
  #assert sender.save_campaign_contacts(dummyCursor, campaign_id, contacted_emails) == None

def testUpdateCampaign():
  context = getDummyContext()

  campaign_id = 123
  email_count = 321

  sql = """UPDATE email_campaigns SET email_count = %s WHERE id = %s"""
  parameters = (email_count, campaign_id)

  dummyCursor = expect.DummyObjectWithExpectations()
  dummyCursor.expect('execute', (sql, parameters), {}, None)

  sender = es.EmailSender(context)
  #assert sender.update_campaign(dummyCursor, campaign_id, email_count) == None

