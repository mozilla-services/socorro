web: sh -c 'cd webapp-django && ./manage.py runserver 0.0.0.0:8000'
collector: gunicorn wsgi.collector
middleware: gunicorn wsgi.collector
processor: socorro/processor/processor_app.py --admin.conf=config/processor.ini
