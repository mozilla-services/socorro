
Development Installation and Setup
============================================

 1.) Install easy_install, if you don't have it already.
     <http://peak.telecommunity.com/DevCenter/EasyInstall>

 2.) Create a mysql database and users as necessary

 3.) cp development.ini.dist development.ini.  Edit the fields in 
     development.ini to match your mysql and Breakpad setup.

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
