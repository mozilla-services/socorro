try:
  from email.mime.text import MIMEText as MIMETextClass
except ImportError:
  from email import MIMEText as MIMETextClass

import datetime
import logging
import socket
import sys
from smtplib import SMTP

import web
from web import form

from socorro.lib import uuid
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil
import socorro.lib.util as sutil
import socorro.webapi.webapiService as webapi

logger = logging.getLogger("webapi")

EMAIL_ADDRESS_VARIABLE   = '*|EMAIL_ADDRESS|*'
UNSUBSCRIBE_URL_VARIABLE = '*|UNSUBSCRIBE_URL|*'
CRASH_DATE_VARIABLE      = '*|CRASH_DATE|*'
CRASH_URL_VARIABLE       = '*|CRASH_URL|*'

#=================================================================================================================
class EmailSender(webapi.JsonServiceBase):
  """ Hoopsnake API which sends email for a campaign
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(EmailSender, self).__init__(configContext)
    self.database = db.Database(configContext)
    self.config = configContext

    self.email_form = form.Form(
      form.Textbox('campaign_id',    form.notnull),
      form.Textbox('status',         form.notnull))

  #-----------------------------------------------------------------------------------------------------------------
  "/201103/email"
  uri = '/201103/email'

  #-----------------------------------------------------------------------------------------------------------------
  #  curl -v http://localhost:8085/201009/email/
  #
  def get(self, *args):
    """ return list of campaigns and their status (started/stopped) """
    # TODO implement
    

  #-----------------------------------------------------------------------------------------------------------------
  #  curl -v -F campaign_id=1 -F status=start http://localhost:8085/201009/email
  #
  def post(self, *args):
    " Webpy method receives inputs from uri "
    errors = []
    email_form = self.email_form()
    if email_form.validates():
      campaign_id = email_form['campaign_id'].value
      status     = email_form['status'].value

      logger.info("changing status of campaign %s to %s" % (campaign_id, status))
      connection = self.database.connection()

      try:
        if status == 'start':
          logger.info("Starting email sending for campaign ID %s" % campaign_id)
          self.start_campaign(connection.cursor(), campaign_id)

          smtp = self.smtp_connection()
          contacted_emails = []
          while True:

            cursor = connection.cursor()
            status, contacts, subject, body = self.retrieve_campaign(cursor, campaign_id)
            connection.commit()

            if status != 'started':
              logger.info("Campaign ID %s stopped, cease email activity" % campaign_id)
              break

            logger.info("Retrieved campaign info for campaign ID %s" % campaign_id)
    
            contacted_emails = self.send_all_emails(contacts, subject, body, smtp)
            logger.info("Sent %d emails to users" % len(contacted_emails))
    
            cursor = connection.cursor()
            self.update_campaign(cursor, campaign_id, contacted_emails)
            logger.info("Updated campaign ID %s" % campaign_id)
            connection.commit()
    
          smtp.quit()
          return {"emails": {"campaign_id": campaign_id, "actual_count": len(contacted_emails)}}
        elif status == 'stop':
          logger.info("Setting campaign to stopped for campaign ID %s" % campaign_id)
          self.stop_campaign(campaign_id)
        else:
          raise Exception ('unknown status: %s' % s)
      finally:
        connection.close()
    else:
      web.badrequest()
      for field in ['campaign_id', 'status']:
        if email_form[field].note:
          # Example "product: Required"
          errors.append("%s: %s" % (field, email_form[field].note))
        logger.info("Bad Request. %s" % ', '.join(errors))
        return {'message': ', '.join(errors)}

  #-----------------------------------------------------------------------------------------------------------------
  def send_all_emails(self, contacts, subject, body, smtp):
    """ returns a list of email addresses which were successfully contacted """
    contacted_emails = {}

    # It would be nice to allocate MIMEText out here, but we personalize every email

    for contact in contacts:
      try:
        contact_id, email, token, ooid, crash_date = contact
        personalized_body = self.personalize(body, email, token, ooid, crash_date)

        msg = MIMETextClass(personalized_body.encode('utf-8'), _charset='utf-8')
        msg['From'] = self.config['fromEmailAddress']
        msg['Subject'] = subject

        logger.info("calling sendmail %s with %s" % (email, personalized_body))
        # comment the next line for a safer dev env
        self.send_email(smtp, msg, email)

        contacted_emails[contact_id] = 'sent'
      except Exception, e:
        logger.error("Error while sending email to %s" % email)
        sutil.reportExceptionAndContinue(logger=logger)
        contacted_emails[contact_id] = 'failed with error: %s' % sys.exc_info()[1]
    return contacted_emails

  #-----------------------------------------------------------------------------------------------------------------
  def personalize(self, body, email, token, ooid, crash_date):
    t = body.replace(EMAIL_ADDRESS_VARIABLE, email)
    t = t.replace(UNSUBSCRIBE_URL_VARIABLE, self.config['unsubscribeBaseUrl'] % token)
    t = t.replace(CRASH_DATE_VARIABLE, crash_date.isoformat())
    t = t.replace(CRASH_URL_VARIABLE, self.config['crashBaseUrl'] % ooid)
    return t

  #-----------------------------------------------------------------------------------------------------------------
  def smtp_connection(self):
    server = SMTP(self.config['smtpHostname'], self.config['smtpPort'])
    if self.config['smtpUsername'] and self.config['smtpPassword']:
      server.login(self.config['smtpUsername'], self.config['smtpPassword'])
    #server.set_debuglevel(1)
    return server

  #-----------------------------------------------------------------------------------------------------------------
  def send_email(self, smtp, msg, email):
    msg['To'] = email
    smtp.sendmail(self.config['fromEmailAddress'], [email], msg.as_string())

  #-----------------------------------------------------------------------------------------------------------------
  def update_campaign(self, cursor, campaign_id, contacted_emails):
    logger.info('contacted_emails: %s' % contacted_emails)
    email_count = len(contacted_emails)
    # update overall campaign count
    # TODO this count includes failed emails; should it?
    cursor.execute("UPDATE email_campaigns SET email_count = email_count + %s WHERE id = %s",
                   (email_count, campaign_id))
    # update each individal contact status
    for contact_id in contacted_emails:
      status = contacted_emails[contact_id]
      logger.info('update email_campaign_contacts id %s with status %s' % (contact_id, status))
      cursor.execute("UPDATE email_campaigns_contacts SET status = %s WHERE email_contacts_id = %s",
                     (status, contact_id))
    return

  #-----------------------------------------------------------------------------------------------------------------
  def retrieve_campaign(self, cursor, campaign_id):

    contacts = {}
    mailer_id = socket.gethostname()
    params =  {'mailer_id': 'allocated to %s' % mailer_id, 'campaign_id': campaign_id}

    cursor.execute("""
      SELECT status, subject, body FROM email_campaigns
        WHERE id = %(campaign_id)s""", params)

    status, subject, body = cursor.fetchone()

    if status != 'started':
      return (status, contacts, subject, body)

    logger.info('status: %s, subject: %s, body: %s' % (status, subject, body))

    cursor.execute(""" 
      SELECT email_contacts_id FROM email_campaigns_contacts
        WHERE email_campaigns_id = %(campaign_id)s
        FOR UPDATE
        LIMIT 10""", params)
    outgoing_email_ids = cursor.fetchall()

    params['outgoing_email_ids'] = outgoing_email_ids

    cursor.execute("""
      UPDATE email_campaigns_contacts
        SET status = %(mailer_id)s
        WHERE email_campaigns_id = %(campaign_id)s
        AND status = 'ready' 
        RETURNING email_contacts_id""",  params)

    email_contacts_ids = cursor.fetchall()

    if len(email_contacts_ids) == 0:
      status = self.stop_campaign(cursor, campaign_id)
      return (status, contacts, subject, body)

    logger.info('email contacts ids: %s' % email_contacts_ids)

    cursor.execute("""
      SELECT id, email, subscribe_token, ooid, crash_date FROM email_contacts
        WHERE id IN %(email_contacts_ids)s
        AND subscribe_status = 't' """, {'email_contacts_ids': tuple(email_contacts_ids)})

    contacts = cursor.fetchall()

    return (status, contacts, subject, body)

  #-----------------------------------------------------------------------------------------------------------------
  def start_campaign(self, cursor, campaign_id):

    cursor.execute("""
      UPDATE email_campaigns
        SET status = 'started'
        WHERE id = %(campaign_id)s
        RETURNING status
    """, {'campaign_id': campaign_id})

    return cursor.fetchone()

  #-----------------------------------------------------------------------------------------------------------------
  def stop_campaign(self, cursor, campaign_id):

    cursor.execute("""
      UPDATE email_campaigns
        SET status = 'stopped'
        WHERE id = %(campaign_id)s
        RETURNING status
    """, {'campaign_id': campaign_id})

    return cursor.fetchone()

