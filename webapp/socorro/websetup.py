import os

import paste.deploy
from sqlalchemy import create_engine
import socorro.models as model

def setup_config(command, filename, section, vars):
  """
  Place any commands to setup socorro here.
  """
  conf = paste.deploy.appconfig('config:' + filename)
  paste.deploy.CONFIG.push_process_config({'app_conf':conf.local_conf,
                                           'global_conf':conf.global_conf})
    
  """
  Set up database.  Later on when we revise the database again we will have
  to add additional logic to support database upgrades and versioning.

  If you are setting this up for production, you will want to set up
  partitions.  See the README for more info on that.
  """
  uri = conf['sqlalchemy.dburi']
  engine = create_engine(uri)
  print "Connecting to database %s" % uri
  model.meta.connect(engine)
  print "Creating tables"
  model.reports_id_sequence.create()
  model.meta.create_all()  
  model.upgrade_db(engine)

  # XXX-Turn this off, for now
  #
  # create the directory that will hold our symbol files
  #dirnames = conf['socorro.symbol_dirs']
  #print "Checking symbol directories"
  #for dirname in dirnames:
  #  if not os.path.isdir(dirname):
  #    print "Creating directory at " + dirname
  #    os.mkdir(dirname)

  print "Setup complete"
