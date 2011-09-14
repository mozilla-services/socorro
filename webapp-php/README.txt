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

Installation instructions are available at:
http://code.google.com/p/socorro/wiki/SocorroUIInstallation


Development
============

Running Unit Tests
cd tests/
phpunit *.php
