web: sh -c 'cd webapp-django && gunicorn wsgi.socorro-crashstats'
middleware: gunicorn wsgi.middleware
processor: socorro/processor/processor_app.py --admin.conf=config/processor.ini
