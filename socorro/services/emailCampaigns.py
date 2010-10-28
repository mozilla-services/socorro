import logging

import socorro.database.database as db
import socorro.lib.util as lib_util
import socorro.webapi.webapiService as webapi

logger = logging.getLogger("webapi")

#=================================================================================================================
class EmailCampaigns(webapi.JsonServiceBase):
  """ Hoopsnake API which provides access to email campaigns

  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(EmailCampaigns, self).__init__(configContext)
    self.database = db.Database(configContext)

  #-----------------------------------------------------------------------------------------------------------------
  # curl -v http://localhost:8085/201009/email_campaigns
  "/201009/email/campaigns/page/{page_number}"
  uri = '/201009/email/campaigns/page/(.*)'

  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    """ Webpy method receives inputs from uri
        Results will have
        * campaigns - A list of campaign objects
        * next - None or a relative url to the next page
        * previous - None or a relative url to the next page
        * total_pages - The number of pages available
    """
    if 1 != len(args):
      return {'status': "ERROR"}

    page_number = int(args[0])
    if page_number < 1:
      return {'status': "ERROR"}

    return self.load(page_number)

  #-----------------------------------------------------------------------------------------------------------------  
  def load(self, page_number):
    item_per_page = 50
    offset = (page_number -1) * item_per_page
    campaigns = []
    total_pages = 0
    campaign_ids = []
    
    connection = self.database.connection()
    try:
      cursor = connection.cursor()

      email_campaign_columns = ['id', 'product', 'signature', 'subject', 'body', 'start_date', 'end_date', 'email_count', 'author']
      sql = "SELECT %s FROM email_campaigns ORDER BY id DESC OFFSET %%s LIMIT %%s" \
            % ', '.join(email_campaign_columns)
      
      cursor.execute(sql, (offset, item_per_page))
      rows = cursor.fetchall()
      for row in rows:
        campaign = lib_util.DotDict((key, value) for key, value in zip(email_campaign_columns, row))
        campaign.start_date = campaign.start_date.isoformat()
        campaign.end_date =   campaign.end_date.isoformat()
        campaigns.append(campaign)
        campaign_ids.append(campaign.id)
      
        pages_sql = "SELECT COUNT(id) / %d FROM email_campaigns" % item_per_page
        cursor.execute(pages_sql)
        total_pages = int(cursor.fetchone()[0])

      next = previous = None
      if page_number < total_pages:
        next = EmailCampaigns.uri.replace('(.*)', str(page_number + 1))
      if page_number > 1:
        previous = EmailCampaigns.uri.replace('(.*)', str(page_number - 1))
      
      return {'campaigns': campaigns, 'next': next, 'previous':previous, 'total_pages': total_pages}
    finally:
      connection.close()
