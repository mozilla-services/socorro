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

  If you are setting this up for production, you will want to set up partitions.
  See the README for more info on that.
  """
  uri = conf['sqlalchemy.dburi']
  engine = create_engine(uri)
  print "Connecting to database %s" % uri
  model.meta.connect(engine)
  print "Creating tables"
  model.meta.create_all()  

  # create the directory that will hold our symbol files
  dirname = conf['socorro.symbol_dir']
  print "Creating symbol directory", dirname 
  if not os.path.isdir(dirname):
    os.mkdir(dirname)

  print "Setup complete"
