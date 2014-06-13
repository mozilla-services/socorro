.. index:: add-product-release

Adding new products and releases
--------------------------------

Socorro products and versions are tracked in the PostgreSQL database,
and managed using functions (also called "stored procedures").

To add new products and releases, you will need to connect to PostgreSQL
as a superuser:
::
 psql -h localhost breakpad

The prompt will look like:

breakpad=#

Start by adding a new product "KillerApp"
::
 -- Arguments: prodname, major_version
 select add_new_product('KillerApp', '1.0');

Now add a few releases for this product:
::
 -- Arguments:
 -- product, version, update_channel, build_id, platform, beta_number
 select add_new_release('KillerApp', '1.0', 'beta', '201406060122',
                        'Windows', 1);
 select add_new_release('KillerApp', '1.0', 'release', '201406060123',
                        'Windows', 0);

 insert into product_release_channels (product_name, release_channel, throttle) 
                                      values ('KillerApp', 'Release', 1);
 insert into product_release_channels (product_name, release_channel, throttle) 
                                      values ('KillerApp', 'Beta', 1);

Socorro currently supports four different update_channels:
release, beta, aurora, and nightly

The "build id" is a date string used to identify this build. For 
instance 201406060122 is the time the build started: "2014 June 06 01:22"

Platforms supported are: Windows, Mac OS X and Linux.

A scheduled crontabber task will occasionally rebuild the product_versions
table causing this to show up in the UI, you can run this right away:
::
 select update_product_versions();

Finally, to get this to show up in the UI without having to wait for the cache
to expire, make sure to restart memcached as the *root* user:
::
  service memcached restart  
