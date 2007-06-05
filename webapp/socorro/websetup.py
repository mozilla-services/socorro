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
  Set up database, or upgrade from previous versions.
  """
  uri = conf['sqlalchemy.dburi']
  engine = create_engine(uri)
  print "Connecting to database %s" % uri
  connection = engine.connect()

  model.meta.connect(engine)

  print "Setting up the database schema"
  model.reports_id_sequence.create()
  transaction = connection.begin()
  model.meta.create_all(connection)
  model.define_functions(connection.connection)
  model.lock_schema(connection.connection)
  model.upgrade_db(connection.connection)
  model.ensure_partitions(connection.connection)
  transaction.commit()

  print "Setup complete"
