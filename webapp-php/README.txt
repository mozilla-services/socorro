Requirements
============
PHP 5.2+
php.ini settings 
- You should enable support for <?= style tags:
short_open_tag = On 
- You may wish to configure php how (not) to report certain errors:
display_errors, display_startup_errors, error_reporting, log_errors

Apache
Configure your document root and allow for .htaccess files
AllowOverride All

Installation
============

# Copy htaccess-dist to .htaccess, tweak for installation host path if it's not
# at the domain root: Edit RewriteBase from / to the actual root.
cp htaccess-dist .htaccess 
vim htaccess

# Change hosting path and domain in application/config/config.php
# Edit config['site_domain'] to exactly match the rewriteBase above
# unless you know what you are doing ...
cp application/config/config.php-dist application/config/config.php
vim application/config/config.php

# Change database settings in application/config/database.php
cp application/config/database.php-dist application/config/database.php
vim application/config/database.php

# Switch between file-based or memcache-based caching in application/config/cache.php
vim application/config/cache.php

# Change memcache settings in application/config/cache_memcache.php
cp application/config/cache_memcache.php-dist application/config/cache_memcache.php
vim application/config/cache_memcache.php

# Ensure that the application logs and cache directories can be written to
chmod a+rw application/logs application/cache

Development
============

Running Unit Tests
cd tests/
phpunit *.php
