#!/usr/bin/env python
import sys, os
import psycopg2, psycopg2.extensions

if len(sys.argv) > 1:
   proc_pw = sys.argv[1]
else:
   # error, we need a password
   sys.exit('a password parameter is required to run this script')

#connect to postgresql
conn = psycopg2.connect("dbname=postgres user=postgres")

cur = conn.cursor()

# simple shell command runner
def runshell(shell_command):
   shell_result = os.system(shell_command)
   if shell_result != 0:
      sys.exit("command %s failed with error code %s",shell_command,shell_result)

# untar all the new configuration files and directories
runshell('tar -xvzf pgbouncer.tgz -C /')

#create and set the password for the new processor user
cur.execute("""
	CREATE USER processor IN ROLE breakpad_rw WITH PASSWORD %s
   """, ( proc_pw, ) )

#now get the md5 of the password
cur.execute("""
        SELECT passwd FROM pg_shadow WHERE usename = 'processor'
    """)
    
md5pw = str(cur.fetchone()[0])

#write it to the new auth file
runshell('cp /etc/pg_auth.conf /etc/pgbouncer/pg_auth.conf')
with open('/etc/pgbouncer/pg_auth.conf','a') as authfile:
  authfile.write('"processor"  "%s"\n',md5pw)

# change the active services
runshell("chkconfig --add pgbouncer-web")
runshell("chkconfig pgbouncer-web on")
runshell("chkconfig --add pgbouncer-processor")
runshell("chkconfig pgbouncer-processor on")
runshell("chkconfig pgbouncer off")

# switch services
runshell("/etc/init.d/pgbouncer stop")
runshell("/etc/init.d/pgbouncer-web start")
runshell("/etc/init.d/pgbouncer-processor start")

# done
sys.exit(0)