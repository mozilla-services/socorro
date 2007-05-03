
Development Installation and Setup
============================================

 1.) Install easy_install, if you don't have it already.
     <http://peak.telecommunity.com/DevCenter/EasyInstall>

 2.) Create a postgresql database and users as necessary.  For more info, see
     <http://www.postgresql.org/docs/8.1/static/user-manag.html>
     You will need psycopg2 as the db driver for postgres.  Some users have
     needed postgres-dev (CentOS) to install this.  Most distros have a package
     for this.  psycopg2 was not included in the egg or setup.py because of
     issues related to its installation.  Install it using your system's package
     manager

     Note: Two files exist in the models directory that can be used to create
     partitions if so desired.  The plpgsql code there is not a part of the
     default install because most devs do not need it.  If you want to enable
     partitioning to deal with large data sets, execute functions.sql then
     partitions.sql.  Read the comments in both files before doing so.

 3.) cp development.ini.dist development.ini.  Edit the fields in 
     development.ini to match your postgresql and Breakpad setup.

 4.) Run '(sudo) python setup.py develop'
     This command will install the necessary Python dependencies. It
     will not install Breakpad.

 5.) Run 'paster setup-app development.ini'
     This command will create the tables in the database, and do
     other initialization.

 6.) Run 'paster serve --reload development.ini' to start the app on
     port localhost:5000.
     
The list of reports is available at 

<http://localhost:5000/report/list>

The upload URL for Breakpad's configuration is

<http://yourhost:5000/report/add>

XXXsayrer Production Installation and Setup
============================================
XXXsayrer -- these are just the default instructions...

Install ``Socorro`` using easy_install::

    easy_install Socorro

Make a config file as follows::

    paster make-config Socorro config.ini
    
Tweak the config file as appropriate and then setup the application::

    paster setup-app config.ini
    
Then you are ready to go.
