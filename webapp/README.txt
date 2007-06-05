
Development Installation and Setup
============================================

 1.) Install easy_install, if you don't have it already.
     <http://peak.telecommunity.com/DevCenter/EasyInstall>

 2.) Create a postgresql database and users as necessary.  For more
     info, see
     
      <http://www.postgresql.org/docs/8.1/static/user-manag.html>
 
     You will need psycopg2 as the db driver for postgres.  Some users
     have needed postgres-devel (CentOS) to install this.  Most distros
     have a package for this.  psycopg2 was not included in the egg or
     setup.py because of issues related to its installation.  Install
     it using your system's package manager

 3.) cp development.ini.dist development.ini.  Edit the fields in 
     development.ini to match your postgresql and Breakpad setup.

 4.) Run '(sudo) python setup.py develop'
     This command will install the necessary Python dependencies. It
     will not install Breakpad.

 5.) Run 'paster setup-app development.ini'
     This command will create the tables in the database, and do
     other initialization. It creates an initial partition for reports and
     their connected data. Further partitions will need to be created by
     the database adminstrator at appropriate intervals.

 6.) Run 'paster serve --reload development.ini' to start the app on
     port localhost:5000.
     
The list of reports is available at 

  <http://localhost:5000/report/list>

The upload URL for Breakpad's configuration is

  <http://yourhost:5000/report/add>


Production Installation and Setup
============================================

1.)  Make sure you have all of the required Python packages. This can
     be accomplished in two ways. The first is by using easy_install
     as described by the development instructions. There is a known
     bug with "paster setup-app" and the proxy filter used with
     mod_proxy. It is described in the following ticket:
      
     <http://trac.pythonpaste.org/pythonpaste/ticket/159>

     Just comment out the "proxy-prefix" configurations in your .ini
     file and run it, then add them back.

     You can also install the dependencies that the socorro
     application has separately:

      Pylons>=0.9.4
      SQLAlchemy>=0.3.5
      Genshi>=0.3.6
      AuthKit>=0.3.0pre5
      Psycopg2

2.)  Setup the database as described above, for production use.

3.)  Copy socorro/lib/config.py.dist to socorro/lib/config.py

4.)  Copy production.ini.dist to production.ini.

5.)  Customize production.ini for use in your environment. (database
     details, IP address, server port, etc)

6.)  Start the Pylons web server with "paster serve production.ini" 


Deploying Behind Apache
============================================

Mostly borrowed from
http://docs.pythonweb.org/display/pylonscookbook/Apache+and+mod_proxy+for+Pylons

Add something like the following to your Apache configuration:

      <VirtualHost *>
      ServerName some.domain

      # ... usual options here, then at the end add the ProxyPass entries...

      ProxyPass /socorro http://localhost:5000
      ProxyPassReverse /socorro http://localhost:5000
      <Proxy *>
          Order deny,allow
          Allow from all
      </Proxy>
      </VirtualHost>

You should take care not to add a trailing / after the URLs. You
should also replace 5000 with the number of the port at which the
server is actually running and replace /forms with the path at which
you want the Pylons application to be available. For example if you
want the Pylons application to be available at the root of the domain
you should replace /socorro with /.
