try:
  from email.mime.text import MIMEText as MIMETextClass
except ImportError:
  from email import MIMEText as MIMETextClass

import datetime
import logging
from smtplib import SMTP

import web
from web import form

from socorro.lib import uuid
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil
import socorro.lib.util as sutil
import socorro.webapi.webapiService as webapi

from socorro.database.schema import EmailCampaignsTable
from socorro.database.schema import EmailContactsTable

logger = logging.getLogger("webapi")

EMAIL_ADDRESS_VARIABLE   = '*|EMAIL_ADDRESS|*'
UNSUBSCRIBE_URL_VARIABLE = '*|UNSUBSCRIBE_URL|*'

#=================================================================================================================
class EmailCampaignCreate(webapi.JsonServiceBase):
  """ Hoopsnake API which estimates the total volume of emails
      a given campaign will generate. A campaign is based on:
      * Product
      * Version list (optional)
      * Crash Signature
      * Date Range

      The API returns a raw number
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(EmailCampaignCreate, self).__init__(configContext)
    self.database = db.Database(configContext)
    self.config = configContext

    self.email_form = form.Form(
      form.Textbox('product',    form.notnull),
      form.Textbox('versions',  form.notnull),
      form.Textbox('signature',  form.notnull),
      form.Textbox('subject',    form.notnull),
      form.Textarea('body',      form.notnull),
      form.Textbox('start_date', form.notnull),
      form.Textbox('end_date',   form.notnull),
      form.Textbox('author',     form.notnull))

  #-----------------------------------------------------------------------------------------------------------------
  # Intentionally not using /201009/emailcampaigns (and emailCampaigns.py) to avoid any accidental email campaign creations, since
  # this is such a dangerous web service call... </REST pedantic note>
  #
  #  curl -v -F product=Firefox -F versions=4.0b6,3.0.11 -F signature=js_FinishSharingTitle -F subject='Good News' -F body='Test Email' \
  #       -F start_date=2010-06-14 -F end_date=2010-06-15 -F author=tester http://localhost:8085/201009/email
  #
  "/201009/email"
  uri = '/201009/email'

  #-----------------------------------------------------------------------------------------------------------------
  def post(self, *args):
    " Webpy method receives inputs from uri "
    errors = []
    email_form = self.email_form()
    if email_form.validates():
      product    = email_form['product'].value
      versions   = tuple([x.strip() for x in email_form['versions'].value.split(',')])
      signature  = email_form['signature'].value
      subject    = email_form['subject'].value
      body       = email_form['body'].value
      start_date = dtutil.datetimeFromISOdateString(email_form['start_date'].value)
      end_date   = dtutil.datetimeFromISOdateString(email_form['end_date'].value)
      author     = email_form['author'].value
      logger.info("%s is creating an email campaign for %s %s crashes in [%s] Between %s and %s" %(author, product, versions, signature, start_date, end_date))

      connection = self.database.connection()
      try:
        return {"emails": self.create_email_campaign(connection, product, versions, signature, subject, body, start_date, end_date, author)}
      finally:
        connection.close()
    else:
      web.badrequest()
      for field in ['product', 'versions', 'signature', 'subject', 'body', 'start_date', 'end_date', 'author']:
        if email_form[field].note:
          # Example "product: Required"
          errors.append("%s: %s" % (field, email_form[field].note))
        logger.info("Bad Request. %s" % ', '.join(errors))
        return {'message': ', '.join(errors)}

  #-----------------------------------------------------------------------------------------------------------------
  def create_email_campaign(self, connection, product, versions, signature, subject, body, start_date, end_date, author):
    """ We want to do as much DB work as possible before doing
        email work, as databases are transactional, but email is not.

        Grab all the email addresses
          Filter out bad addresses
          Filter out already contacted
          Filter out opt-out emails
        create new contacts
        create campaign
        Loop over contacts and send email
        Remove failed emails from the contacts

        create entries for addresses with campaign
        update campaigns entry with email_count

        Error Conditions: SMTP DOWN, DB DOWN

    """
    end_date = datetime.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

    email_rows = self.determine_emails(connection, product, versions, signature, start_date, end_date)
    full_email_rows = self.ensure_contacts(connection, email_rows)
    campaign_id = self.save_campaign(connection, product, versions, signature, subject, body, start_date, end_date, author, 0)

    contacted_emails = self.send_all_emails(full_email_rows, subject, body)

    logger.info("Sent %d emails to users" % len(contacted_emails))

    self.save_campaign_contacts(connection, campaign_id, contacted_emails)
    self.update_campaign(connection, campaign_id, len(contacted_emails))
    connection.commit()
    return {"campaign_id": campaign_id, "estimated_count": len(email_rows), "actual_count": len(contacted_emails)}

  #-----------------------------------------------------------------------------------------------------------------
  def determine_emails(self, connection, product, versions, signature, start_date, end_date):
    """ Retrieves a list of email addresses based on the criteria """
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
             )
    """ % (start_date, end_date, version_clause)
    cursor = connection.cursor()
    #logger.info(cursor.mogrify(sql, {'product': product, 'versions': versions, 'signature': signature}))
    cursor.execute(sql, {'product': product, 'versions': versions, 'signature': signature})
    return cursor.fetchall()

  #-----------------------------------------------------------------------------------------------------------------
  def ensure_contacts(self, connection, email_rows):
    """ Returns a three element tuple, which captures if
        we need to save this entry into the database once
        we are done sending the email
        * email
        * token
        * dirty
    """
    # tupple tied to determine_emails SQL (id, email, token) id and token NULL for new entries
    new_emails = []
    contacts = []
    for row in email_rows:
      dbid, email, token = row
      if not dbid:
        new_token = str(uuid.uuid4())
        new_emails.append((email, new_token))
        contacts.append({'id': None, 'email': email, 'token': new_token})
      else:
        contacts.append({'id': dbid, 'email': email, 'token': token})
    if new_emails:
      cursor = connection.cursor()
      table = EmailContactsTable(logger)
      cursor.executemany(table.insertSql, new_emails)
    return contacts

  #-----------------------------------------------------------------------------------------------------------------
  def send_all_emails(self, contacts, subject, body):
    """ returns a list of email addresses which were successfully contacted """
    contacted_emails = []
    # this can raise SMTPHeloError, SMTPAuthenticationError, SMTPException
    # Error handeling... This Service Call will either work or fail. Failure comes from
    # SMTP, Database, ... ?

    smtp = self.smtp_connection()
    # It would be nice to allocate MIMEText out here, but we personalize every email

    for contact in contacts:
      if '@' not in contact['email']:
        continue
      try:
        personalized_body = self.personalize(body, contact['email'], contact['token'])

        msg = MIMETextClass(personalized_body.encode('utf-7'), _charset='utf-7')
        msg['From'] = self.config['fromEmailAddress']
        msg['Subject'] = subject

        # Swap the comment for the next two lines for a safer dev env
        #logger.info("calling sendmail %s with %s" % (contact['email'], personalized_body))
        self.send_email(smtp, msg, contact['email'])

        contacted_emails.append(contact['email'])
      except Exception:
        logger.error("Error while sending email to %s" % contact['email'])
        sutil.reportExceptionAndContinue(logger=logger)
    smtp.quit()
    return contacted_emails

  #-----------------------------------------------------------------------------------------------------------------
  def personalize(self, body, email, token):
    t = body.replace(EMAIL_ADDRESS_VARIABLE, email)
    return t.replace(UNSUBSCRIBE_URL_VARIABLE, self.config['unsubscribeBaseUrl'] % token)

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
  def save_campaign(self, connection, product, versions, signature, subject, body, start_date, end_date, author, email_count):
    """ TODO(aok): Actually we'll create the campaign first and then update it at a later set
        so email_count is 0 """
    cursor = connection.cursor()

    parameters = [product, versions, signature, subject, body, start_date, end_date, email_count, author]

    table = EmailCampaignsTable(logger)
    #logger.info(cursor.mogrify(table.insertSql, parameters))
    cursor.execute(table.insertSql, parameters)
    last_id = cursor.fetchone()[0]

    return last_id

  #-----------------------------------------------------------------------------------------------------------------
  def save_campaign_contacts(self, connection, campaign_id, contacted_emails):
    if len(contacted_emails) > 0:
      cursor = connection.cursor()
      sql = """
        INSERT INTO email_campaigns_contacts (email_campaigns_id, email_contacts_id)
          SELECT %(campaign_id)s, email_contacts.id
          FROM email_contacts
          WHERE email IN %(emails)s
      """
      parameters = {'campaign_id': campaign_id, 'emails': tuple(contacted_emails)}

      #logger.info(cursor.mogrify(sql, parameters))
      cursor.execute(sql, parameters)
    else:
      logger.warn("No contacts given in call to associate campaign to contacts")

  #-----------------------------------------------------------------------------------------------------------------
  def update_campaign(self, connection, campaign_id, email_count):
    cursor = connection.cursor()
    cursor.execute("UPDATE email_campaigns SET email_count = %s WHERE id = %s",
                   (email_count, campaign_id))
    return
