#!/usr/bin/env python

"""
CronTabber is a configman app for executing all Socorro cron jobs.
"""
import traceback
import inspect
import datetime
import sys
import re
import json
import copy
from configman import Namespace, RequiredConfig
from configman.converters import class_converter, py_obj_to_str
from socorro.database.transaction_executor import (
  #TransactionExecutorWithInfiniteBackoff,
  TransactionExecutor)
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.app.generic_app import App, main


class JobNotFoundError(Exception):
    pass


class FrequencyDefinitionError(Exception):
    pass


class TimeDefinitionError(Exception):
    pass


class JobDescriptionError(Exception):
    pass


class BaseCronApp(RequiredConfig):
    """The base class from which Socorro apps are based"""
    required_config = Namespace()

    def __init__(self, config):
        self.config = config

    def main(self):
        self.run()

    def run(self):
        raise NotImplementedError("Your fault!")


class PostgreSQLCronApp(BaseCronApp):

    def main(self):
        database = self.config.database_class(self.config)
        executor = self.config.transaction_executor_class(self.config,
                                                          database)
        executor(self.run)


class JSONJobDatabase(dict):

    _date_fmt = '%Y-%m-%d %H:%M:%S.%f'
    _day_fmt = '%Y-%m-%d'

    def load(self, file_path):
        try:
            self.update(self._recurse_load(json.load(open(file_path))))
        except IOError:
            pass

    def _recurse_load(self, struct):
        for key, value in struct.items():
            if isinstance(value, dict):
                self._recurse_load(value)
            else:
                try:
                    value = datetime.datetime.strptime(value, self._date_fmt)
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
                struct[key] = value.strftime(self._date_fmt)
            elif isinstance(value, (int, long, float)):
                pass
            elif not isinstance(value, basestring):
                struct[key] = unicode(value)
        return struct


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


#------------------------------------------------------------------------------
def _default_list_splitter(class_list_str):
    return [x.strip() for x in class_list_str.split(',')]


def _default_class_extractor(list_element):
    return list_element


def _default_extra_extractor(list_element):
    raise NotImplementedError()


def classes_in_namespaces_converter_with_compression(
      reference_namespace={},
      template_for_namespace="class-%(name)s",
      list_splitter_fn=_default_list_splitter,
      class_extractor=_default_class_extractor,
      extra_extractor=_default_extra_extractor
    ):
    """
    parameters:
        template_for_namespace - a template for the names of the namespaces
                                 that will contain the classes and their
                                 associated required config options.  There are
                                 two template variables available: %(name)s -
                                 the name of the class to be contained in the
                                 namespace; %(index)d - the sequential index
                                 number of the namespace.
        list_converter - a function that will take the string list of classes
                         and break it up into a sequence if individual elements
        class_extractor - a function that will return the string version of
                          a classname from the result of the list_converter
        extra_extractor - a function that will return a Namespace of options
                          created from any extra information associated with
                          the classes returned by the list_converter function
                              """

    #--------------------------------------------------------------------------
    def class_list_converter(class_list_str):
        """This function becomes the actual converter used by configman to
        take a string and convert it into the nested sequence of Namespaces,
        one for each class in the list.  It does this by creating a proxy
        class stuffed with its own 'required_config' that's dynamically
        generated."""
        if isinstance(class_list_str, basestring):
            class_str_list = list_splitter_fn(class_list_str)
        else:
            raise TypeError('must be derivative of a basestring')

        #======================================================================
        class InnerClassList(RequiredConfig):
            """This nested class is a proxy list for the classes.  It collects
            all the config requirements for the listed classes and places them
            each into their own Namespace.
            """
            # we're dynamically creating a class here.  The following block of
            # code is actually adding class level attributes to this new class

            # 1st requirement for configman
            required_config = Namespace()

            # to help the programmer know what Namespaces we added
            subordinate_namespace_names = []

            # save the template for future reference
            namespace_template = template_for_namespace

            # for display
            original_input = class_list_str.replace('\n', '\\n')

            # for each class in the class list
            class_list = []
            for namespace_index, class_list_element in enumerate(
                                                               class_str_list):
                try:
                    a_class = class_converter(
                                           class_extractor(class_list_element))
                except AttributeError:
                    raise JobNotFoundError(class_list_element)
                class_list.append((a_class.__name__, a_class))
                # figure out the Namespace name
                namespace_name_dict = {'name': a_class.__name__,
                                       'index': namespace_index}
                namespace_name = template_for_namespace % namespace_name_dict
                subordinate_namespace_names.append(namespace_name)
                # create the new Namespace
                required_config.namespace(namespace_name)
                a_class_namespace = required_config[namespace_name]
                # add options for the 'extra data'
                try:
                    extra_options = extra_extractor(class_list_element)
                    a_class_namespace.update(extra_options)
                except NotImplementedError:
                    pass
                # add options frr the classes required config
                try:
                    for k, v in a_class.get_required_config().iteritems():
                        if k not in reference_namespace:
                            a_class_namespace[k] = v
                except AttributeError:  # a_class has no get_required_config
                    pass

            @classmethod
            def to_str(cls):
                """this method takes this inner class object and turns it back
                into the original string of classnames.  This is used
                primarily as for the output of the 'help' option"""
                return cls.original_input
                #return ', '.join(
                    #py_obj_to_str(v[name_of_class_option].value)
                        #for v in cls.get_required_config().values()
                        #if isinstance(v, Namespace))

        return InnerClassList  # result of class_list_converter
    return class_list_converter  # result of classes_in_namespaces_converter


def get_extra_as_options(input_str):
    if '|' not in input_str:
        raise JobDescriptionError("No frequency and/or time defined")
    metadata = input_str.split('|')[1:]
    if len(metadata) == 1:
        if ':' in metadata[0]:
            frequency = '1d'
            time_ = metadata[0]
        else:
            frequency = metadata[0]
            time_ = None
    else:
        frequency, time_ = metadata

    n = Namespace()
    n.add_option('frequency',
                 doc='frequency',
                 default=frequency,
                 #from_string_converter=int
                 exclude_from_print_conf=True,
                 exclude_from_dump_conf=True
                 )
    n.add_option('time',
                 doc='time',
                 default=time_,
                 exclude_from_print_conf=True,
                 exclude_from_dump_conf=True
                 )
    return n


class CronTabber(App):

    app_name = 'crontabber'
    app_version = '0.1'
    app_description = __doc__

    required_config = Namespace()
    # the most important option, 'jobs', is defined last

    required_config.add_option(
        name='database',
        default='./crontabbers.json',
        doc='Location of file where job execution logs are stored',
    )

    required_config.add_option('database_class',
                               default=ConnectionContext,
                               from_string_converter=class_converter)

    required_config.add_option('transaction_executor_class',
                               #default=TransactionExecutorWithBackoff,
                               default=TransactionExecutor,
                               doc='a class that will execute transactions')

    required_config.add_option(
        name='job',
        default='',
        doc='Run a specific job',
        short_form='j',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True,
    )

    required_config.add_option(
        name='list-jobs',
        default=False,
        doc='List all jobs',
        short_form='l',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True,
    )

    required_config.add_option(
        name='force',
        default=False,
        doc='Force running a job despite dependencies',
        short_form='f',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True,
    )

    required_config.add_option(
        name='configtest',
        default=False,
        doc='Check that all configured jobs are OK',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True,
    )

    required_config.add_option(
      'jobs',
      default='',
      from_string_converter=
        classes_in_namespaces_converter_with_compression(
          reference_namespace=required_config,
          list_splitter_fn=lambda x: x.splitlines(),
          class_extractor=lambda x: x.split('|', 1)[0],
          extra_extractor=get_extra_as_options
        )
    )

    def main(self):
        if self.config.get('list-jobs'):
            self.list_jobs()
        elif self.config.get('job'):
            self.run_one(self.config['job'], self.config.get('force'))
        elif self.config.get('configtest'):
            if not self.configtest():
                return 1
        else:
            self.run_all()
        return 0

    @property
    def database(self):
        if not getattr(self, '_database', None):
            self._database = JSONJobDatabase()
            self._database.load(self.config.database)
        return self._database

    def list_jobs(self, stream=None):
        if not stream:
            stream = sys.stdout
        _fmt = '%Y-%m-%d %H:%M:%S'
        _now = datetime.datetime.now()
        PAD = 12
        for class_name, job_class in self.config.jobs.class_list:
            class_config = self.config['class-%s' % class_name]
            freq = class_config.frequency
            if class_config.time:
                freq += ' @ %s' % class_config.time
            class_name = job_class.__module__ + '.' + job_class.__name__
            print >>stream, '=== JOB ' + '=' * 72
            print >>stream, "Class:".ljust(PAD), class_name
            print >>stream, "App name:".ljust(PAD), job_class.app_name
            print >>stream, "Frequency:".ljust(PAD), freq
            try:
                info = self.database[job_class.app_name]
            except KeyError:
                print >>stream, "*NO PREVIOUS RUN INFO*"
                continue

            print >>stream, "Last run:".ljust(PAD),
            print >>stream, info['last_run'].strftime(_fmt).ljust(20),
            print >>stream, '(%s ago)' % timesince(info['last_run'], _now)
            print >>stream, "Next run:".ljust(PAD),
            print >>stream, info['next_run'].strftime(_fmt).ljust(20),
            print >>stream, '(in %s)' % timesince(_now, info['next_run'])
            if info.get('last_error'):
                print >>stream, "Error!!".ljust(PAD),
                print >>stream, "(%s times)" % info['error_count']
                print >>stream, info['last_error']['traceback']
            print >>stream, ''

    def run_all(self):
        for class_name, job_class in self.config.jobs.class_list:
            class_config = self.config['class-%s' % class_name]
            self._run_one(job_class, class_config)

    def run_one(self, description, force=False):
        # the description in this case is either the app_name or the full
        # module/class reference
        for class_name, job_class in self.config.jobs.class_list:
            if (job_class.app_name == description or
              description == job_class.__module__ + '.' + job_class.__name__):
                class_config = self.config['class-%s' % class_name]
                self._run_one(job_class, class_config, force=force)
                return
        raise JobNotFoundError(description)

    def _run_one(self, job_class, config, force=False):
        _debug = self.config.logger.debug
        seconds = self._convert_frequency(config.frequency)
        time_ = config.time
        if not force:
            if not self.time_to_run(job_class):
                _debug("skipping %r because it's not time to run", job_class)
                return
            if not self.check_dependencies(job_class):
                _debug("skipping %r dependencies aren't met", job_class)
                return

        _debug('about to run %r', job_class)
        try:
            self._run_job(job_class, config)
            _debug('successfully ran %r', job_class)
            exc_type = exc_value = exc_tb = None
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            _debug('error when running %r', job_class, exc_info=True)
        finally:
            self._log_run(job_class, seconds, time_,
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
            if job_info['next_run'] < datetime.datetime.now():
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
        if next_run < datetime.datetime.now():
            return True
        return False

    def _run_job(self, class_, config):
        # here we go!
        instance = class_(config)
        instance.main()

    def _log_run(self, class_, seconds, time_, exc_type, exc_value, exc_tb):
        assert inspect.isclass(class_)
        app_name = class_.app_name
        info = {
          'last_run': datetime.datetime.now(),
          'next_run': (datetime.datetime.now() +
                       datetime.timedelta(seconds=seconds))
        }
        if time_:
            h, m = [int(x) for x in time_.split(':')]
            info['next_run'] = info['next_run'].replace(hour=h,
                                                        minute=m,
                                                        second=0,
                                                        microsecond=0)

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
            raise FrequencyDefinitionError(unit)
        return number

    def _check_time(self, value):
        """check that it's a value like 03:45 or 1:1"""
        try:
            h, m = value.split(':')
            h = int(h)
            m = int(m)
            if h >= 24 or h < 0:
                raise ValueError
            if m >= 60 or m < 0:
                raise ValueError
        except ValueError:
            raise TimeDefinitionError("Invalid definition of time %r" % value)

    def configtest(self):
        """return true if all configured jobs are configured OK"""
        # similar to run_all() but don't actually run them
        failed = 0
        for class_name, __ in self.config.jobs.class_list:
            class_config = self.config['class-%s' % class_name]
            if not self._configtest_one(class_config):
                failed += 1
        return not failed

    def _configtest_one(self, config):
        try:
            seconds = self._convert_frequency(config.frequency)
            time_ = config.time
            if time_:
                self._check_time(time_)
                # if less than 1 day, it doesn't make sense to specify hour
                if seconds < 60 * 60 * 24:
                    raise FrequencyDefinitionError(config.time)
            return True

        except (JobNotFoundError,
                JobDescriptionError,
                FrequencyDefinitionError,
                TimeDefinitionError):
            exc_type, exc_value, exc_tb = sys.exc_info()
            print >>sys.stderr, "Error type:", exc_type
            print >>sys.stderr, "Error value:", exc_value
            print >>sys.stderr, ''.join(traceback.format_tb(exc_tb))
            return False


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(CronTabber))
