# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use settings_local.py

from funfactory.settings_base import *

# Name of the top-level module where you put all your apps.
# If you did not install Playdoh with the funfactory installer script
# you may need to edit this value. See the docs about installing from a
# clone.
PROJECT_MODULE = 'crashstats'

# Bundles is a dictionary of two dictionaries, css and js, which list css files
# and js files that can be bundled together by the minify app.
MINIFY_BUNDLES = {
    'css': {
        'screen_css': (
            'css/crashstats/screen.css',
        ),
        'daily_css': (
            'css/crashstats/daily.css',
        ),
        'topcrash_css': (
            'css/crashstats/flora/flora.tablesorter.css',
        ),
        'reportindex_css': (
            'css/crashstats/flora/flora.all.css',
        ),
        'example_mobile_css': (
            'css/crashstats/mobile.css',
        ),
    },
    'js': {
       'crashstats_js': (
            'js/crashstats/jquery/jquery-1.6.4.min.js',
            'js/crashstats/jquery/plugins/jquery.cookies.2.2.0.js',
            'js/crashstats/socorro/nav.js',
       ),
       'crashstats_flot': (
           'js/crashstats/flot-0.7/jquery.flot.pack.js',
       ),
       'crashstats_daily': (
            'js/crashstats/socorro/daily.js',
       ),
       'crashstats_topcrash': (
            'js/crashstats/socorro/topcrash.js',
       ),
       'crashstats_bugzilla': (
            'js/crashstats/socorro/bugzilla.js',
       ),
       'crashstats_correlation': (
            'js/crashstats/socorro/correlation.js',
       ),
       'crashstats_report': (
            'js/crashstats/socorro/report.js',
       ),
       'crashstats_tablesorter': (
            'js/crashstats/jquery/plugins/ui/jquery.tablesorter.min.js',
       ),
    }
}

# Defines the views served for root URLs.
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

INSTALLED_APPS = list(INSTALLED_APPS) + [
    # Application base, containing global templates.
    '%s.base' % PROJECT_MODULE,
    # Example code. Can (and should) be removed for actual projects.
    '%s.crashstats' % PROJECT_MODULE,
]


# Because Jinja2 is the default template loader, add any non-Jinja templated
# apps here:
JINGO_EXCLUDE_APPS = [
    'admin',
    'registration',
]

MIDDLEWARE_EXCLUDE_CLASSES = [
    'funfactory.middleware.LocaleURLMiddleware',
]

MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES)

for app in MIDDLEWARE_EXCLUDE_CLASSES:
    if app in MIDDLEWARE_CLASSES:
        MIDDLEWARE_CLASSES.remove(app)

MIDDLEWARE_CLASSES = tuple(MIDDLEWARE_CLASSES)


# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.
DOMAIN_METHODS['messages'] = [
    ('%s/**.py' % PROJECT_MODULE,
        'tower.management.commands.extract.extract_tower_python'),
    ('%s/**/templates/**.html' % PROJECT_MODULE,
        'tower.management.commands.extract.extract_tower_template'),
    ('templates/**.html',
        'tower.management.commands.extract.extract_tower_template'),
],

# # Use this if you have localizable HTML files:
# DOMAIN_METHODS['lhtml'] = [
#    ('**/templates/**.lhtml',
#        'tower.management.commands.extract.extract_tower_template'),
# ]

# # Use this if you have localizable JS files:
# DOMAIN_METHODS['javascript'] = [
#    # Make sure that this won't pull in strings from external libraries you
#    # may use.
#    ('media/js/**.js', 'javascript'),
# ]

LOGGING = dict(loggers=dict(playdoh = {'level': logging.DEBUG}))
