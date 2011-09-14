
gringoValues = [(1,'one','all lonely'),
                (2,'two','lilly white boiz'),
                (3,'three','the rivals'),
                (4,'four','gospel writers'),
                (5,'five','weird symbols'),
                (6,'six','proud skywalkers'),
                (7,'seven','bold stars'),
                (8,'eight','dem reins'),
                (9,'nine','bright ones'),
                (10,'ten','doze commands'),
                (11,'eleven','day went up'),
                (12,'twelve','dem good time apostles'),
                ]
def dropDB(connection):
  cursor = connection.cursor()
  cursor.execute('DROP TABLE IF EXISTS gringo')
  cursor.execute('DROP TABLE IF EXISTS chartable')
  connection.commit()

def createDB(connection):
  cursor = connection.cursor()
  cursor.execute('DROP TABLE IF EXISTS gringo;')
  cursor.execute('CREATE TABLE gringo(id INTEGER, number VARCHAR(50), example VARCHAR(50));')
  for row in gringoValues:
    cursor.execute('INSERT INTO gringo VALUES (%s,%s,%s);',row)
  cursor.execute('DROP TABLE IF EXISTS chartable;')
  cursor.execute('CREATE TABLE chartable(c CHAR);')
  connection.commit()

