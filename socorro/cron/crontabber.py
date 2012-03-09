#!/usr/bin/env python

"""
CronTabber is a configman app for executing all Socorro cron jobs.
"""
import functools
import logging
import logging.handlers
import cPickle
import inspect
import datetime
import sys
import re
from configman import RequiredConfig, ConfigurationManager, Namespace
from configman.converters import class_converter


class BaseCronApp(RequiredConfig):
    """The base class from which Socorro apps are based"""

    def __init__(self, config):
        self.config = config

#    def main(self):
#        if not self._check_dependencies():
#            return
#        self.run()

    def run(self):
        raise NotImplementedError("Your fault!")


class JobDatabase(dict):
    def save(self, file_path):
        raise NotImplementedError
    def load(self, file_path):
        raise NotImplementedError


class PickleJobDatabase(dict):

    def load(self, file_path):
        try:
            self.update(cPickle.load(open(file_path)))
        except IOError:
            # file doesn't exist yet
            pass

    def save(self, file_path):
        with open(file_path, 'w') as f:
            cPickle.dump(dict(self), f)


def job_lister(input_str):
    return [x.strip() for x
            in input_str.splitlines()
            if x.strip()]


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
        default=[],#'crontabber.jobs.Foo:12h','crontabber.jobs.Bar:1d'],
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
            self._database = PickleJobDatabase()
            self._database.load(self.config.database)
        return self._database

    def D(self, *args, **kwargs):
        # saves an aweful lot of typing
        self.config.logger.debug(*args, **kwargs)

    def __init__(self, config):
        self.config = config

    def list_jobs(self):
        raise WorkHarder
        print self.config.jobs

    def run_all(self):
        for each in self.config.jobs:
            job_class, seconds = self._lookup_job(each)
            if not self.time_to_run(job_class):
                self.D("skipping %r because it's not time to run", job_class)
                continue
            if not self.check_dependencies(job_class):
                self.D("skipping %r dependencies aren't met", job_class)
                continue

            self.D('about to run %r', job_class)
            try:
                self.run_job(job_class)
                self.D('successfully ran %r', job_class)
                exc_type = exc_value = exc_tb = None
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.D('error when running %r', job_class, exc_info=True)
            finally:
                self.log_run(job_class, seconds,
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
            if not job_info.get('next_run'):
                # means it has never successfully run
                return False
            if job_info['next_run'] < datetime.datetime.utcnow():
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

    def run_job(self, class_):
        # here we go!
        instance = class_(self.config)
        instance.run()

    def log_run(self, class_, seconds, exc_type, exc_value, exc_tb):
        assert inspect.isclass(class_)
        app_name = class_.app_name
        info = {
          'this_run': datetime.datetime.utcnow(),
        }
        if exc_type:
            info['last_error'] = {
              'type': exc_type,
              'value': exc_value,
              'traceback': exc_tb,
            }
        else:
            info['last_error'] = {}
            info['next_run'] = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)

        self.database[app_name] = info
        self.database.save(self.config.database)


    def _lookup_job(self, job_description):
        """return class definition and a frequency in seconds as a tuple pair.
        """
        class_path, frequency = job_description.split(':')
        seconds = self._convert_frequency(frequency)
        class_ = class_converter(class_path)

        if inspect.ismodule(class_):
            # then it was passed something like "jobs.foo" instead of "jobs.foo.MyClass"
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
        short_form='j'
    )

    definition_source.add_option(
        name='list-jobs',
        default=False,
        doc='List all jobs',
        short_form='l'
    )

    definition_source.add_option(
        name='force',
        default=False,
        doc='Force running a job despite dependencies',
        short_form='f'
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
            tab.run_job(config['job'], config.get('force'))
        else:
            tab.run_all()


if __name__ == '__main__':
    run()
