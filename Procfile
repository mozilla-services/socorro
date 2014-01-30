web: cd webapp-django; ./virtualenv/bin/python manage.py runserver 0.0.0.0:8000
collector: PYTHONPATH=. socorro-virtualenv/bin/python socorro/collector/collector_app.py --admin.conf=config/collector.ini
middleware: PYTHONPATH=. socorro-virtualenv/bin/python socorro/middleware/middleware_app.py --admin.conf=config/middleware.ini
processor: PYTHONPATH=. socorro-virtualenv/bin/python socorro/processor/processor_app.py --admin.conf=config/processor.ini
