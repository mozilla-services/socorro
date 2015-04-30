.. index:: databasesetup

.. _databasesetup-chapter:


Postgres Database Setup and Operation
=======================================

There are three major steps in creating a Socorro database for production:

 * Run ``socorro setupdb``
 * Create a new product (currently not automated)
 * Run crontabber jobs to normalize incoming crash and product data

socorro setupdb
---------------

This is an application that will set up the Postgres database schema
for Socorro. It starts with an empty database and creates all the
tables, indexes, constraints, stored procedures and triggers needed to
run a Socorro instance.     

Before this application can be run, however, there have been set up a
regular user that will be used for the day to day operations. While it
is not recommended that the regular user have the full set of super
user privileges, the regular user must be privileged enough to create
tables within the database.

This tool also requires a user with superuser permissions if you want
to be able to run the script without logging into the database and 
first creating a suitable database, and if you want to use the ``--dropdb`` 
option.

This script also requires an ``alembic`` configuration file for 
initializing our database migration system. An example configuration
file can be found in ``config/alembic.ini-dist``.

**Running socorro setupdb**

``socorro setupdb --database_name=mydatabasename --createdb``

Common options listed below.::

  --fakedata -- populate the database with preset fixture data
  --fakedata_days=2 -- the number of days worth of crash data to generate
  --dropdb -- drop a database with the same name as --database_name

For more information about fakedata, see ``socorro/external/postgresql/fakedata.py``.

Creating a new product
-----------------------

Current (as of 2/4/2015) 

There is work underway to automate adding a new product.

The minimal set of actions to enable products viewable in the Django webapp is:
    
1. ``SELECT add_new_product()`` in the Postgres database
2. ``SELECT add_new_release()`` in the Postgres database
3. Insert channels into ``product_release_channels``
4. ``SELECT update_product_versions()`` in the Postgres database
5. ``service memcached restart`` on your memcached server
 
Details on the Postgres related operations are below.

**``SELECT add_new_product()``**

This function adds rows to the ``products``, ``product_build_types``, and ``product_productid_map`` tables.

Minimum required to call this function::

    SELECT add_new_product('MyNewProduct', '1.0');

The first value is the product name, used in the webapp and other places for display. Currently we require that this have no spaces. We'd welcome a pull request to make whitespace in a product name possible in our Django webapp.

The second value is the product initial version. This should be the minimum version number that you'll receive crashes for in dotted notation. This is currently a DOMAIN, and has some special type checking associated with it. In the future, we may change this to be NUMERIC type so as to make it easier to work with across ORMs and with Python.

Additional options include::

 prodid TEXT -- a UUID surrounded by '{}' used by Mozilla for Firefox and other products
 ftpname TEXT -- an alternate name used to match the product name as given by our release metadata server (ftp and otherwise)
 release_throttle NUMERIC -- used by our collectors to only process a percentage of all crashes, a percentage
 rapid_beta_version NUMERIC -- documents the first release version that supports the 'rapid_beta' feature for Socorro

These options are not required and have suitable defaults for all installations.

**``SELECT add_new_release()``**

This function adds new rows to ``releases_raw`` table, and optionally adds new rows to ``product_versions``.

Minimum required to call this function::

    SELECT add_new_release('MyNewProduct', '1.0', 'release', '201501010000', 'Linux');

The first value is product name and must match either the product name or ftpname from the add_new_product() function run (or whatever is in the products table). 

The second value is a version, and this must be numerically equal to or less than the major version added during the add_new_product() run. We support several common alphanumeric versioning schemes. Examples of supported version numbers::

    1.0.1
    1.0a1 
    1.0b10 
    1.0.6esr
    1.0.10pre
    1.0.3(beta)

The third value is a release_channel.  Our supported release channel types currently include: release, nightly, aurora (aka alpha), beta, esr (extended support release). 'pre' is mapped to 'aurora'.  Rules for support of 'nightly' release channels are complicated.

If you need to support release channels in addition or with names different than our defaults, you may need to modify the ``build_type`` ENUM defined in the database. There are a number of other dependencies out of scope for this document. Recommendation at this time is to just use our release_channels.

The fourth value is a build identifier. Our builds are typically identified by a timestamp. 

The fifth value is an operating system name. Supported operating systems are: Windows, Mac OS X and Linux. There are a few caveats to Windows naming with the tables ``os_name``, ``os_versions`` and ``os_name_matches`` playing important roles in our materialized view generation.


Additional options include::
 beta_number INTEGER -- a number derived from the version_string if passed in to help sort betas when displayed
 repository TEXT -- an label indicating of where the release came from, often same name as an FTP repo
 version_build TEXT -- a label to help identify specific builds associated with the version string
 update_products (True/False) -- calls update_product_versions() for you
 ignore_duplicates (True/False) -- catches UNIQUE violations

**Insert channels into ``product_release_channels``**

Here is a a SQL command to populate this table:: 

    INSERT into product_release_channels
    (product_name, release_channel, throttle)
    VALUES
    ('MyNewProduct', 'release', '0.1');


The first value is product name and must match either the product name or ftpname from the add_new_product() function run (or whatever is in the products table). 

The second value is a release_channel.  Our supported release channel types currently include: release, nightly, aurora (aka alpha), beta, esr (extended support release). 'pre' is mapped to 'aurora'.  Rules for support of 'nightly' release channels are complicated.

The third value is release_throttle and is a NUMERIC value indicating what percentage of crashes are processed.

**``SELECT update_product_versions()``**

This function inserts rows into the ``product_versions`` and ``product_version_builds`` tables.

Minimum required to call this function::

 SELECT update_product_versions();

No values need to be passed to the function by default. 

Options include::
 product_window INTEGER -- the number of days you'd like product versions to be inserted and updated for, default is 30 days

