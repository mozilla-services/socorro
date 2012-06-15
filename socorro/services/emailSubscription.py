import logging

from web import form

import socorro.webapi.webapiService as webapi
import socorro.database.database as db

logger = logging.getLogger("webapi")

#=================================================================================================================
class EmailSubscription(webapi.JsonServiceBase):
  """ Hoopsnake API which reads and writes user email preferences
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(EmailSubscription, self).__init__(configContext)
    self.database = db.Database(configContext)
    self.email_form = form.Form(
      form.Textbox('token',   form.notnull),
      form.Textbox('status',  form.notnull))

  #-----------------------------------------------------------------------------------------------------------------
  # GET
  # curl http://localhost:8085/emailcampaigns/subscription/e8aaa82c-c762-11df-a2ce-001cc4d80ee4
  "/emailcampaigns/subscription/{token}"
  #
  # POST (status can be 'true' or 'false'
  #  curl -v -F token=e8aaa82c-c762-11df-a2ce-001cc4d80ee4 -F status=false \
  #             http://localhost:8085/emailcampaigns/subscription/e8aaa82c-c762-11df-a2ce-001cc4d80ee4
  uri = '/emailcampaigns/subscription/(.*)'

  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    " Webpy method receives inputs from uri "
    token = str(args[0])
    connection = self.database.connection()
    try:
      cursor = connection.cursor()
      sql = "SELECT subscribe_status FROM email_contacts WHERE subscribe_token = %s"
      cursor.execute(sql, (token,))
      rs = cursor.fetchone()
      if rs:
        status = rs[0]
        return {'found': True, 'status': status}
      else:
        return {'found': False}
    finally:
      connection.close()

  def post(self, *args):
  #-----------------------------------------------------------------------------------------------------------------
    " Webpy method receives inputs from uri "
    email_form = self.email_form()
    if email_form.validates():
      status = 'true' == email_form['status'].value
      token  = email_form['token'].value

      connection = self.database.connection()
      try:
        cursor = connection.cursor()
        sql = "UPDATE email_contacts SET subscribe_status = %s WHERE subscribe_token = %s"
        #logger.info(cursor.mogrify(sql, (status, token,)))
        cursor.execute(sql, (status, token,))
        connection.commit()
        return {'update': True}
      finally:
        connection.close()
    else:
      return {'update': False}

