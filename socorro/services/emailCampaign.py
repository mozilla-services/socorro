import logging

import socorro.webapi.webapiService as webapi
import socorro.database.database as db

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
  # curl http://localhost:8085/emailcampaigns/campaign/1
  "/emailcampaigns/campaign/{id}"
  uri = '/emailcampaigns/campaign/(.*)'

  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    " Webpy method receives inputs from uri "
    id = int(args[0])

    connection = self.database.connection()
    try:
      cursor = connection.cursor()
      campaign = None
      counts = None
      cursor.execute("""SELECT id, product, versions, signature,
                               subject, body, start_date, end_date,
                               email_count, author, date_created, status
                        FROM email_campaigns WHERE id = %s """, [id])
      rs = cursor.fetchone()
      if rs:
        id, product, versions, signature, subject, body, start_date, end_date, email_count, author, date_created, status = rs
        campaign = {'id': id, 'product': product, 'versions': versions,
                    'signature': signature, 'subject': subject, 'body': body,
                    'start_date': start_date.isoformat(), 'end_date': end_date.isoformat(),
                    'email_count': email_count, 'author': author, 'date_created': date_created.isoformat(), 'status': status, 'send': True}

      cursor.execute("""SELECT count(status), status FROM email_campaigns_contacts
                        WHERE email_campaigns_id = %s
                        GROUP BY status""", [id])
      counts = cursor.fetchall()

      return {'campaign': campaign, 'counts': counts}
    finally:
      connection.close()

