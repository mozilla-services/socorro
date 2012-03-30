#!/usr/bin/env python

"""
CronTabber is a configman app for executing all Socorro cron jobs.
"""
import traceback
import functools
import logging
import logging.handlers
import inspect
import datetime
import sys
import re
import json
import copy
from configman import RequiredConfig, ConfigurationManager, Namespace
from configman.converters import class_converter


class JobNotFoundError(Exception):
    pass


class FrequencyDefinitionError(Exception):
    pass


class BaseCronApp(RequiredConfig):
    """The base class from which Socorro apps are based"""

    def __init__(self, config):
        self.config = config

    def run(self):
        raise NotImplementedError("Your fault!")


class JSONJobDatabase(dict):

    _utc_fmt = '%Y-%m-%d %H:%M:%S.%f'
    _day_fmt = '%Y-%m-%d'

    def load(self, file_path):
        try:
            self.update(self._recurse_load(json.load(open(file_path))))
        except IOError:
            pass
        except ValueError:
            # oh nos! the JSON is broken
            sys.stderr.write(('JSON PAYLOAD (%s) ' % file_path)
                             .ljust(79, '-') + '\n')
            sys.stderr.write(open(file_path).read())
            sys.stderr.write('\n' + '-' * 79 + '\n')
            raise

    def _recurse_load(self, struct):
        for key, value in struct.items():
            if isinstance(value, dict):
                self._recurse_load(value)
            else:
                try:
                    value = datetime.datetime.strptime(value, self._utc_fmt)
                    struct[key] = value
                except (ValueError, TypeError):
                    try:
                        value = (datetime.datetime
                                 .strptime(value, self._day_fmt).date())
                        struct[key] = value
                    except (ValueError, TypeError):
                        pass
        return struct

    def save(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self._recurse_serialize(copy.deepcopy(dict(self))),
                      f, indent=2)

    def _recurse_serialize(self, struct):
        for key, value in struct.items():
            if isinstance(value, dict):
                self._recurse_serialize(value)
            elif isinstance(value, datetime.datetime):
                struct[key] = value.strftime(self._utc_fmt)
            elif isinstance(value, (int, long, float)):
                pass
            elif not isinstance(value, basestring):
                struct[key] = unicode(value)
        return struct


def job_lister(input_str):
    return [x.strip() for x
            in input_str.splitlines()
            if x.strip()]


def timesince(d, now=None):  # pragma: no cover
    """
    Taken from django.utils.timesince
    """
    def ungettext(a, b, n):
        if n == 1:
            return a
        return b

    def ugettext(s):
        return s

    def is_aware(v):
        return v.tzinfo is not None and v.tzinfo.utcoffset(v) is not None

    chunks = (
      (60 * 60 * 24 * 365, lambda n: ungettext('year', 'years', n)),
      (60 * 60 * 24 * 30, lambda n: ungettext('month', 'months', n)),
      (60 * 60 * 24 * 7, lambda n: ungettext('week', 'weeks', n)),
      (60 * 60 * 24, lambda n: ungettext('day', 'days', n)),
      (60 * 60, lambda n: ungettext('hour', 'hours', n)),
      (60, lambda n: ungettext('minute', 'minutes', n))
    )
    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    if not now:
        now = datetime.datetime.now(utc if is_aware(d) else None)

    delta = now - d
    # ignore microseconds
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        return u'0 ' + ugettext('minutes')
    for i, (seconds, name) in enumerate(chunks):
        count = since // seconds
        if count != 0:
            break
    s = ugettext('%(number)d %(type)s') % {
      'number': count, 'type': name(count)}
    if i + 1 < len(chunks):
        # Now get the second item
        seconds2, name2 = chunks[i + 1]
        count2 = (since - (seconds * count)) // seconds2
        if count2 != 0:
            s += ugettext(', %(number)d %(type)s') % {
                 'number': count2, 'type': name2(count2)}
    return s


def logging_required_config(app_name):
    lc = Namespace()
    lc.add_option('syslog_host',
              doc='syslog hostname',
              default='localhost')
    lc.add_option('syslog_port',
              doc='syslog port',
              default=514)
    lc.add_option('syslog_facility_string',
              doc='syslog facility string ("user", "local0", etc)',
              default='user')
    lc.add_option('syslog_line_format_string',
              doc='python logging system format for syslog entries',
              default='%s (pid %%(process)d): '
                      '%%(asctime)s %%(levelname)s - %%(threadName)s - '
                      '%%(message)s' % app_name)
    lc.add_option('syslog_error_logging_level',
              doc='logging level for the log file (10 - DEBUG, 20 '
                  '- INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)',
              default=40)
    lc.add_option('stderr_line_format_string',
              doc='python logging system format for logging to stderr',
              default='%(asctime)s %(levelname)s - %(threadName)s - '
                      '%(message)s')
    lc.add_option('stderr_error_logging_level',
              doc='logging level for the logging to stderr (10 - '
                  'DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, '
                  '50 - CRITICAL)',
              default=10)
    return lc


def setup_logger(app_name, config, local_unused, args_unused):
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    stderr_log = logging.StreamHandler()
    stderr_log.setLevel(config.stderr_error_logging_level)
    stderr_log_formatter = logging.Formatter(config.stderr_line_format_string)
    stderr_log.setFormatter(stderr_log_formatter)
    logger.addHandler(stderr_log)

    syslog = logging.handlers.SysLogHandler(
                                        facility=config.syslog_facility_string)
    syslog.setLevel(config.syslog_error_logging_level)
    syslog_formatter = logging.Formatter(config.syslog_line_format_string)
    syslog.setFormatter(syslog_formatter)
    logger.addHandler(syslog)
    return logger


class CronTabber(RequiredConfig):

    required_config = Namespace()
    required_config.add_option(
        name='jobs',
        default=[],
        doc='List of jobs and their frequency separated by `:`',
        from_string_converter=job_lister
    )

    required_config.add_option(
        name='database',
        default='./crontabbers.json',
        doc='Location of file where job execution logs are stored',
    )

    @property
    def database(self):
        if not getattr(self, '_database', None):
            #self._database = PickleJobDatabase()
            self._database = JSONJobDatabase()
            self._database.load(self.config.database)
        return self._database

    def D(self, *args, **kwargs):
        # saves an aweful lot of typing
        self.config.logger.debug(*args, **kwargs)

    def __init__(self, config):
        self.config = config

    def list_jobs(self):
        _fmt = '%Y-%m-%d %H:%M:%S'
        _now = datetime.datetime.utcnow()
        PAD = 12
        for each in self.config.jobs:
            try:
                freq = each.split('|', 1)[1]
            except IndexError:
                raise FrequencyDefinitionError(each)
            job_class, seconds = self._lookup_job(each)
            class_name = job_class.__module__ + '.' + job_class.__name__
            print '=== JOB ' + '=' * 72
            print "Class:".ljust(PAD), class_name
            print "App name:".ljust(PAD), job_class.app_name
            print "Frequency:".ljust(PAD), freq
            try:
                info = self.database[job_class.app_name]
            except KeyError:
                print "*NO PREVIOUS RUN INFO*"
                continue

            print "Last run:".ljust(PAD),
            print info['last_run'].strftime(_fmt).ljust(20),
            print '(%s ago)' % timesince(info['last_run'], _now)
            print "Next run:".ljust(PAD),
            print info['next_run'].strftime(_fmt).ljust(20),
            print '(in %s)' % timesince(_now, info['next_run'])
            if info.get('last_error'):
                print "Error!!".ljust(PAD),
                print "(%s times)" % info['error_count']
                print info['last_error']['traceback']
            print

    def run_all(self):
        for each in self.config.jobs:
            self.run_one(each)

    def run_one(self, description, force=False):
        job_class, seconds = self._lookup_job(description)
        if not force:
            if not self.time_to_run(job_class):
                self.D("skipping %r because it's not time to run", job_class)
                return
            if not self.check_dependencies(job_class):
                self.D("skipping %r dependencies aren't met", job_class)
                return

        self.D('about to run %r', job_class)
        try:
            self._run_job(job_class)
            self.D('successfully ran %r', job_class)
            exc_type = exc_value = exc_tb = None
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.D('error when running %r', job_class, exc_info=True)
        finally:
            self._log_run(job_class, seconds,
                         exc_type, exc_value, exc_tb)

    def check_dependencies(self, class_):
        try:
            depends_on = class_.depends_on
        except AttributeError:
            # that's perfectly fine
            return True
        if isinstance(depends_on, basestring):
            depends_on = [depends_on]
        for dependency in depends_on:
            try:
                job_info = self.database[dependency]
            except KeyError:
                # the job this one depends on hasn't been run yet!
                return False
            if job_info.get('last_error'):
                # errored last time it ran
                return False
            if job_info['next_run'] < datetime.datetime.utcnow():
                # the dependency hasn't recently run
                return False
        # no reason not to stop this class
        return True

    def time_to_run(self, class_):
        """return true if it's time to run the job.
        This is true if there is no previous information about its last run
        or if the last time it ran and set its next_run to a date that is now
        past.
        """
        app_name = class_.app_name
        try:
            info = self.database[app_name]
        except KeyError:
            # no past information, run now
            return True
        next_run = info['next_run']
        if next_run < datetime.datetime.utcnow():
            return True
        return False

    def _run_job(self, class_):
        # here we go!
        instance = class_(self.config)
        instance.run()

    def _log_run(self, class_, seconds, exc_type, exc_value, exc_tb):
        assert inspect.isclass(class_)
        app_name = class_.app_name
        info = {
          'last_run': datetime.datetime.utcnow(),
          'next_run': (datetime.datetime.utcnow() +
                       datetime.timedelta(seconds=seconds))
        }
        if exc_type:
            tb = ''.join(traceback.format_tb(exc_tb))
            info['last_error'] = {
              'type': exc_type,
              'value': exc_value,
              'traceback': tb,
            }
            info['error_count'] = info.get('error_count', 0) + 1
        else:
            info['last_error'] = {}
            info['error_count'] = 0

        self.database[app_name] = info
        self.database.save(self.config.database)

    def _lookup_job(self, job_description):
        """return class definition and a frequency in seconds as a tuple pair.
        """
        if '|' not in job_description and '.' not in job_description:
            # the job is described by its app_name
            for each in self.config.jobs:
                #freq = each.split('|', 1)[1]
                job_class, seconds = self._lookup_job(each)
                if job_class.app_name == job_description:
                    return job_class, seconds

            # still here! Then it couldn't be found
            raise JobNotFoundError(job_description)

        class_path, frequency = job_description.split('|')
        seconds = self._convert_frequency(frequency)
        class_ = class_converter(class_path)

        if inspect.ismodule(class_):
            # then it was passed something like "jobs.foo" instead
            # of "jobs.foo.MyClass"
            for name, cls in inspect.getmembers(class_, inspect.isclass):
                if name == BaseCronApp.__name__:
                    continue
                if BaseCronApp.__name__ in [x.__name__ for x in cls.__mro__]:
                    # XXX: why oh why can't I use `issubclass(cls, BaseCronApp)` ????
                    class_ = cls
                    break

        return class_, seconds

    def _convert_frequency(self, frequency):
        number = int(re.findall('\d+', frequency)[0])
        unit = re.findall('[^\d]+', frequency)[0]
        if unit == 'h':
            number *= 60 * 60
        elif unit == 'm':
            number *= 60
        elif unit == 'd':
            number *= 60 * 60 * 24
        elif unit:
            raise NotImplementedError(unit)
        return number


def run():
    definition_source = Namespace()

    definition_source.add_option(
        name='job',
        default='',
        doc='Run a specific job',
        short_form='j',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True,
    )

    definition_source.add_option(
        name='list-jobs',
        default=False,
        doc='List all jobs',
        short_form='l',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True,
    )

    definition_source.add_option(
        name='force',
        default=False,
        doc='Force running a job despite dependencies',
        short_form='f',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True,
    )

    app_name = 'crontabber'
    definition_source.add_aggregation(
        'logger',
        functools.partial(setup_logger, app_name)
    )

    config_manager = ConfigurationManager(
        [definition_source,
         CronTabber.required_config,
         logging_required_config(app_name)],
        app_name='crontabber',
        app_description=__doc__
    )

    with config_manager.context() as config:
        tab = CronTabber(config)
        if config.get('list-jobs'):
            tab.list_jobs()
        elif config.get('job'):
            tab.run_one(config['job'], config.get('force'))
        else:
            tab.run_all()

#def test_json():
#    db=JSONJobDatabase()
#    db.load('foo-orig.json')
#    db.update({
#      'foo': {
#        'next_run': datetime.datetime.utcnow(),
#        'error': {},
#        'name': u'FOO'
#      }
#    })
#    db.save('foo.json')


if __name__ == '__main__':
    run()
