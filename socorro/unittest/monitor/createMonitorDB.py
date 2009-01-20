import psycopg2

tableCreationData = {
  'branches' : [
  """CREATE TABLE branches (
    product character varying(30) NOT NULL,
    version character varying(16) NOT NULL,
    branch character varying(24) NOT NULL,
    PRIMARY KEY (product, version)
  );"""
  ],
  'dumps': [
  """CREATE TABLE dumps (
    report_id integer NOT NULL,
    date_processed timestamp without time zone,
    data text
  );
  --CREATE TRIGGER dumps_insert_trigger
  --   BEFORE INSERT ON dumps
  --   FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();"""
  ],
  'extensions': [
  """CREATE TABLE extensions (
    report_id integer NOT NULL,
    date_processed timestamp without time zone,
    extension_key integer NOT NULL,
    extension_id character varying(100) NOT NULL,
    extension_version character varying(16)
  );
  --CREATE TRIGGER extensions_insert_trigger
  --    BEFORE INSERT ON extensions
  --    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();"""
  ],
  'frames':[
  """CREATE TABLE frames (
    report_id integer NOT NULL,
    date_processed timestamp without time zone,
    frame_num integer NOT NULL,
    signature varchar(255)
  );
  --CREATE TRIGGER frames_insert_trigger
  --    BEFORE INSERT ON frames
  --    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();"""
  ],
  'jobs': [
  """CREATE TABLE jobs (
    id serial NOT NULL PRIMARY KEY,
    pathname character varying(1024) NOT NULL,
    uuid varchar(50) NOT NULL UNIQUE,
    owner integer,
    priority integer DEFAULT 0,
    queueddatetime timestamp without time zone,
    starteddatetime timestamp without time zone,
    completeddatetime timestamp without time zone,
    success boolean,
    message text,
    FOREIGN KEY (owner) REFERENCES processors (id)
  );"""
  ,
  """CREATE INDEX jobs_owner_key ON jobs (owner);""",
  """CREATE INDEX jobs_owner_starteddatetime_key ON jobs (owner, starteddatetime);""",
  """CREATE INDEX jobs_owner_starteddatetime_priority_key ON jobs (owner, starteddatetime, priority DESC);""",
  """CREATE INDEX jobs_completeddatetime_queueddatetime_key ON jobs (completeddatetime, queueddatetime);
  --CREATE INDEX jobs_priority_key ON jobs (priority);"""
  ],
  'priorityjobs': [
  """CREATE TABLE priorityjobs (uuid varchar(255) NOT NULL PRIMARY KEY);""",
  ],
  'processors': [
  """CREATE TABLE processors (
    id serial NOT NULL PRIMARY KEY,
    name varchar(255) NOT NULL UNIQUE,
    startdatetime timestamp without time zone NOT NULL,
    lastseendatetime timestamp without time zone
  );"""
  ],
  'reports': [
  """CREATE TABLE reports (
    id serial NOT NULL,
    client_crash_date timestamp with time zone,
    date_processed timestamp without time zone,
    uuid character varying(50) NOT NULL,
    product character varying(30),
    version character varying(16),
    build character varying(30),
    signature character varying(255),
    url character varying(255),
    install_age integer,
    last_crash integer,
    uptime integer,
    cpu_name character varying(100),
    cpu_info character varying(100),
    reason character varying(255),
    address character varying(20),
    os_name character varying(100),
    os_version character varying(100),
    email character varying(100),
    build_date timestamp without time zone,
    user_id character varying(50),
    started_datetime timestamp without time zone,
    completed_datetime timestamp without time zone,
    success boolean,
    truncated boolean,
    processor_notes text,
    user_comments character varying(1024),
    app_notes character varying(1024),
    distributor character varying(20),
    distributor_version character varying(20)
  );
  --CREATE TRIGGER reports_insert_trigger
  --    BEFORE INSERT ON reports
  --    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();"""
  ],
  'server_status': [
  """CREATE TABLE server_status (
    id serial NOT NULL,
    date_recently_completed timestamp without time zone,
    date_oldest_job_queued timestamp without time zone,
    avg_process_sec real,
    avg_wait_sec real,
    waiting_job_count integer NOT NULL,
    processors_count integer NOT NULL,
    date_created timestamp without time zone NOT NULL
  );""",
  """ALTER TABLE ONLY server_status
     ADD CONSTRAINT server_status_pkey PRIMARY KEY (id);""",
  """CREATE INDEX idx_server_status_date ON server_status USING btree (date_created, id);"""
  ],
  'topcrashers': [
  """CREATE TABLE topcrashers (
    id serial NOT NULL,
    signature character varying(255) NOT NULL,
    version character varying(30) NOT NULL,
    product character varying(30) NOT NULL,
    build character varying(30) NOT NULL,
    total integer,
    win integer,
    mac integer,
    linux integer,
    rank integer,
    last_rank integer,
    trend character varying(30),
    uptime real,
    users integer,
    last_updated timestamp without time zone
    );""",
    """ALTER TABLE ONLY topcrashers
       ADD CONSTRAINT topcrashers_pkey PRIMARY KEY (id);"""
  ],
}

class CreateMonitorDB:
  def __init__(self):
    self.madeConnection = False
    
  def maybeCloseConnection(self,connection):
    if self.madeConnection:
      self.madeConnection = False
      connection.close()
    
  def getCursor(self,**kwargs):
    cursor = None
    connection = None
    try:
      cursor = kwargs['cursor']
    except:
      try:
        connection = kwargs['connection']
      except:
        connection = psycopg2.connect(kwargs['dsn'])
        self.madeConnection = True
      cursor = connection.cursor()
    return cursor

  def createDB(self,**kwargs):
    cursor = self.getCursor(**kwargs)
    for name,sqlList in tableCreationData.items():
      try:
        cursor.execute('drop table if exists %s cascade'%name)
        for sql in sqlList:
          cursor.execute(sql)
      except Exception,x:
        print "IN CREATE DB: (%s: %s) %s: %s"%(name,sql,type(x),x)
        raise
    cursor.connection.commit()
    self.maybeCloseConnection(cursor.connection)

  def populateDB(self,**kwargs):
    cursor = self.getCursor(**kwargs)
    print "PopulateDB() Not yet implemented"
    self.maybeCloseConnection(cursor.connection)

  def dropDB(self,**kwargs):
    cursor = self.getCursor(**kwargs)
    sql = "DROP TABLE IF EXISTS %s CASCADE;" %(','.join(tableCreationData.keys()))
    cursor.execute(sql)
    cursor.connection.commit()
    self.maybeCloseConnection(cursor.connection)

