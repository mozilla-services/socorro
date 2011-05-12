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
  #  curl -v -F product=Firefox -F versions=4.0b6,3.0.11 -F signature=js_FinishSharingTitle -F subject='Good News' -F body='Test Email' \
  #       -F start_date=2010-06-14 -F end_date=2010-06-15 -F author=tester http://localhost:8085/201103/emailcampaigns/create
  #
  "/201103/emailcampaigns/create"
  uri = '/201103/emailcampaigns/create'

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
        cursor = connection.cursor()
        campaign_id, full_email_rows = self.create_email_campaign(cursor, product, versions, signature, subject, body, start_date, end_date, author)
        logger.info('full_email_rows: %s' % full_email_rows)
        email_addresses = [row['email'] for row in full_email_rows]
        logger.info('email_addresses: %s' % email_addresses)
        email_contact_ids = self.save_campaign_contacts(cursor, campaign_id, email_addresses)
        logger.info('email_contact_ids: %s' % email_contact_ids)

        connection.commit()
        
        return {'campaign_id': campaign_id}
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
  def create_email_campaign(self, cursor, product, versions, signature, subject, body, start_date, end_date, author):
    """ We want to do as much DB work as possible before doing
        email work, as databases are transactional, but email is not.

        Grab all the email addresses
          Filter out bad addresses
          Filter out already contacted
          Filter out opt-out emails
        create new contacts
        create campaign
        create entries for addresses with campaign

        Error Conditions: SMTP DOWN, DB DOWN

    """
    end_date = datetime.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

    # choose only unique email addresses. 
    # in the case of duplicates, pick the latest crash_date.
    dedupe_emails = {}
    for row in self.determine_emails(cursor, product, versions, signature, start_date, end_date):
      email = row[1]
      crash_date = row[2]
      if email in dedupe_emails.keys():
        if crash_date > dedupe_emails[email][2]:
            dedupe_emails[email] = row
      else:
        dedupe_emails[email] = row

    email_rows = dedupe_emails.values()

    full_email_rows = self.ensure_contacts(cursor, email_rows)
    logger.info('full_email_rows: %s' % full_email_rows)
    campaign_id = self.save_campaign(cursor, product, versions, signature, subject, body, start_date, end_date, author)
    logger.info('campaign_id: %s' % campaign_id)
    return (campaign_id, full_email_rows)

  #-----------------------------------------------------------------------------------------------------------------
  def determine_emails(self, cursor, product, versions, signature, start_date, end_date):
    """ Retrieves a list of email addresses based on the criteria """
    version_clause = ''
    if len(versions) > 0:
      version_clause = " version IN %(versions)s AND "
    sql = """
        SELECT DISTINCT contacts.id, reports.email, reports.client_crash_date AS crash_date, reports.uuid AS ooid, contacts.subscribe_token
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
    logger.info(cursor.mogrify(sql, {'product': product, 'versions': versions, 'signature': signature}))
    cursor.execute(sql, {'product': product, 'versions': versions, 'signature': signature})
    return cursor.fetchall()

  #-----------------------------------------------------------------------------------------------------------------
  def ensure_contacts(self, cursor, email_rows):
    """ Returns a list of five-element dicts
        * id
        * email
        * crash_date
        * ooid
        * token

        Also inserts into email_contacts table.
    """
    # tupple tied to determine_emails SQL (id, email, token) id and token NULL for new entries
    new_emails = []
    contacts = []
    for row in email_rows:
      logger.info('dbid: %s, email: %s, crash_date: %s, ooid: %s, token: %s' % row)
      dbid, email, crash_date, ooid, token = row
      if '@' not in email:
        continue
      if not dbid:
        logger.info('new email address found')
        new_token = str(uuid.uuid4())
        new_emails.append((email, new_token, ooid, crash_date))
        logger.info('using token %s for email %s' % (new_token, email))
        contacts.append({'id': None, 'email': email, 'crash_date': crash_date, 'ooid': ooid, 'token': new_token})
      else:
        contacts.append({'id': dbid, 'email': email, 'crash_date': crash_date, 'ooid': ooid, 'token': token})
    if new_emails:
      logger.info('inserting new email addresses into emailcontacts')
      table = EmailContactsTable(logger)
      cursor.executemany(table.insertSql, new_emails)
    return contacts

  #-----------------------------------------------------------------------------------------------------------------
  def save_campaign(self, cursor, product, versions, signature, subject, body, start_date, end_date, author, email_count=0):
    parameters = [product, versions, signature, subject, body, start_date, end_date, email_count, author]

    table = EmailCampaignsTable(logger)
    logger.info(cursor.mogrify(table.insertSql, parameters))
    cursor.execute(table.insertSql, parameters)
    last_id = cursor.fetchone()[0]

    return last_id

  #-----------------------------------------------------------------------------------------------------------------
  def save_campaign_contacts(self, cursor, campaign_id, contacted_emails):
    if len(contacted_emails) > 0:
      sql = """
        INSERT INTO email_campaigns_contacts (email_campaigns_id, email_contacts_id, status)
          SELECT %(campaign_id)s, email_contacts.id, %(status)s
          FROM email_contacts
          WHERE email IN %(emails)s
        RETURNING email_contacts_id
      """
      parameters = {'campaign_id': campaign_id, 'emails': tuple(contacted_emails), 'status': 'ready'}

      logger.info(cursor.mogrify(sql, parameters))
      cursor.execute(sql, parameters)
      return cursor.fetchall()
    else:
      logger.warn("No contacts given in call to associate campaign to contacts")

