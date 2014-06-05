web: sh -c 'cd webapp-django && gunicorn wsgi.socorro-crashstats'
collector: gunicorn wsgi.collector
middleware: gunicorn wsgi.collector
processor: socorro/processor/processor_app.py --admin.conf=config/processor.ini
