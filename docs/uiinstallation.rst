.. index:: uiinstallation

.. _uiinstallation-chapter:


UI Installation
===============

Installation
---------------

Follow these steps to get the Socorro UI up and running.

Apache
````````````

Set up Apache with a vhost as you see fit. You will either need
AllowOverride to enable .htaccess files or you may paste the .htaccess
rules into your vhost.

KohanaPHP Installation
``````````````````````

1. Copy .htaccess file and edit the host path if your webapp is not at
   the domain root.::

     cp htaccess-dist .htaccess
     vim .htaccess

2. Copy application/config/config.php-dist and change the hosting path
   and domain.::

    cp application/config/config.php-dist application/config/config.php
    vim application/config/config.php

For a production install, you may want to set
$config['display_errors'] to FALSE.

3. Copy application/config/database.php and edit its database
   settings.::

    cp application/config/database.php-dist application/config/database.php
    vim application/config/database.php

4. Copy application/config/cache.php and update the cache setting to
   be file-based or memcache-based.::

    cp application/config/cache.php-dist application/config/cache.php
     vim application/config/cache.php

5. If you selected memcache-based caching, copy
   application/config/cache_memcache.php and update the settings
   accordingly.::

    cp application/config/cache_memcache.php-dist application/config/cache_memcache.php
    vim application/config/cache_memcache.php

6. Copy all other config -dist files to their config location.::

    cp application/config/application.php-dist application/config/application.php
    cp application/config/webserviceclient.php-dist application/config/webserviceclient.php
    cp application/config/daily.php-dist application/config/daily.php
    cp application/config/products.php-dist application/config/products.php

7. Copy application/config/auth.php and edit it to setup your
   preferred authentication method, or to disable authentication. Edit
   $config['driver'] to change your authentication method. Edit
   $config['proto'] to remove the https requirement if necessary.::

     cp application/config/auth.php-dist application/config/auth.php
     vim application/config/auth.php

8. If you are using LDAP, copy application/config/ldap.php and edit
   its settings.::

     cp application/config/ldap.php-dist application/config/ldap.php
     vim application/config/ldap.php

9. Ensure that the application logs and cache directories are
   writeable.::

     a+rw application/logs application/cache

Dump Files
````````````

Socorro UI needs to access the processed dump files via HTTP. You will
need to setup Apache or some other system to ensure that dump files
may be accessed at 'http://example.com/dumps/<UUID>.jsonz' . This can be
accomplished via mod_rewrite rules, just like in the next section
"Serving Raw dump files".

Example config: `processeddumps.mod_rewrite.txt
<https://github.com/mozilla/socorro/blob/master/webapp-php/docs/processeddumps.mod_rewrite.txt>`_

Next, update the $config['crash_dump_local_url'] value in
application/config/application.php to point to the proper directory.


Raw Dump Files
```````````````

When a user is logged in to Socorro UI as an admin, they may view raw
crash dump files. These raw crashes can be served up by Apache by
adding the following rewrite rules. The values should match the values
in the middleware code at scripts/config/commonconfig.py settings.
Links to raw dumps are available in the
http://example.com/report/index/{uuid} crash report pages.

Example config: `webapp-php/docs/rawdumps.mod_rewrite.txt
<https://github.com/mozilla/socorro/blob/master/webapp-php/docs/rawdumps.mod_rewrite.txt>`_

Next, update the $config['raw_dump_url'] value in
application/config/application.php to point to the proper directory.

Web Services
````````````

Many parts of Socorro UI rely on web services provided by the
Python-based middleware layer.

Middleware
````````````

Copy the scripts/config/webapiconfig.py file, edit it accordingly and
execute the script to listen on the indicated port.::

 cp scripts/config/webapiconfig.py-dist scripts/config/webapiconfig.py.py
 vim scripts/config/webapiconfig.py
 python scripts/webservices.py 8083

Socorro UI
````````````

Copy application/config/webserviceclient.php, edit the file and change
$config['socorro_hostname'] to contain the proper hostname and port
number. If necessary, update $config['basic_auth']::

 cp application/config/webserviceclient.php-dist application/config/webserviceclient.php
 vim application/config/webserviceclient.php

Testing Your Setup
```````````````````

There are 2 ways in which you can test your Socorro UI setup.

Search
````````````

Visit the website containing the Socorro UI, and click Advanced
Search. Perform a search for the product you've added to the site,
which you know have crash reports associated with it in the reports
table in your database.


Report
````````````

Within the search results set you received, click a signature in the
results set. Next click the timestamp for a particular signature,
which will take you to a page that displays an individual crash
report.


Trouble Shooting
-----------------

println the sql
````````````````

To see what SQL queries are being executed: Edit
'webapp-php/system/libraries/Database.php' line 443 Kohana::log('debug', $sql);
Do a svn ignore on this file, if you plan on checking in code.

This will show up in the debug log 'application/logs/date.log.php'

Examine your database and see why you don't get the expected results.

404?
````````````

Is your '.htaccess' properly setup?

/report/pending never goes to /report/index?
`````````````````````````````````````````````

If you see a pending screen and didn't expect one this means that the
record in report and dumps couldn't be joined so it's waiting for the
processor on the backend to populate one or both tables. Investigate
with the uuid and look at reports and dump tables.

Config Files
````````````

Ensure that the appropriate config files in webapp/application/config
have been copied from ``.php-dist`` to ``.php``
