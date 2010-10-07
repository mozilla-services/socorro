import datetime
import logging

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil

logger = logging.getLogger("webapi")

#=================================================================================================================
class EmailCampaign(webapi.JsonServiceBase):
  """ Hoopsnake API which retrieves a single campaign
      { campagin: {id: 1, product: 'Firefox', versions: "3.5.10, 4.0b6", signature: "js_foo",
                   start_date: "2010-06-05", end_date: "2010-06-07", author: "guilty@charged.name"}}
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(EmailCampaign, self).__init__(configContext)
    self.database = db.Database(configContext)

  #-----------------------------------------------------------------------------------------------------------------
  # curl http://localhost:8085/201009/email/campaign/1
  "/201009/email/campaign/{id}"
  uri = '/201009/email/campaign/(.*)'

  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    " Webpy method receives inputs from uri "
    id = int(args[0])

    connection = self.database.connection()
    try:
      cursor = connection.cursor()
      campaign = None
      cursor.execute("""SELECT id, product, versions, signature,
                               subject, body, start_date, end_date,
                               email_count, author, date_created   
                        FROM email_campaigns WHERE id = %s """, [id])
      rs = cursor.fetchone()
      if rs:
        id, product, versions, signature, subject, body, start_date, end_date, email_count, author, date_created = rs
        campaign = {'id': id, 'product': product, 'versions': versions,
                    'signature': signature, 'subject': subject, 'body': body,
                    'start_date': start_date.isoformat(), 'end_date': end_date.isoformat(),
                    'email_count': email_count, 'author': author, 'date_created': date_created.isoformat()}
      return {'campaign': campaign}
    finally:
      connection.close()
