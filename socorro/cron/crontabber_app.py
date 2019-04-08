#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import inspect
import json
import re
import sys
import time
import traceback

from configman import Namespace, RequiredConfig
from configman.converters import class_converter, CannotConvertError
import markus
from psycopg2 import OperationalError, IntegrityError
import six

from socorro.app.socorro_app import App
from socorro.cron.base import convert_frequency
from socorro.lib import raven_client
from socorro.lib.datetimeutil import utc_now, timesince
from socorro.lib.dbutil import (
    SQLDidNotReturnSingleRow,
    SQLDidNotReturnSingleValue,
    execute_no_results,
    execute_query_fetchall,
    execute_query_iter,
    single_row_sql,
    single_value_sql,
)
from socorro.lib.transaction import transaction_context


metrics = markus.get_metrics('crontabber')


class JobNotFoundError(Exception):
    pass


class TimeDefinitionError(Exception):
    pass


class JobDescriptionError(Exception):
    pass


class BrokenJSONError(ValueError):
    pass


class SentryConfigurationError(Exception):
    """When Sentry isn't configured correctly"""


class RowLevelLockError(OperationalError):
    """The reason for defining this exception is that when you attempt
    to read from a row that is actively locked (by another
    thread/process) is that you get an OperationalError which isn't
    particular developer-friendly because it might look like there's
    some other more fundamental error such as a bad network connection
    or something wrong with the credentials.
    By giving it a name, it's more clear in the crontabber_log what
    exactly was the reason why that second thread/process couldn't
    work on that row a simultaneously.
    """
    pass


class OngoingJobError(Exception):
    """Raised when you basically tried to run a job that already
    ongoing. This is the "high level" version of `RowLevelLockError`.
    """
    pass


def jobs_converter(path_or_jobs):
    """Takes a Python dotted path or a jobs spec and returns crontabber jobs

    Example Python dotted path::

        jobs_converter('socorro.cron.crontabber_app.DEFAULT_JOBS')

    Example jobs spec::

        jobs_converter('socorro.cron.jobs.archivescraper.ArchiveScraperCronApp|1h')


    :arg str path_or_jobs: a Python dotted path or a crontabber jobs spec

    :returns: crontabber jobs InnerClassList

    """
    if '|' not in path_or_jobs:
        # NOTE(willkg): configman's class_converter returns the value pointed
        # to by a Python dotted path
        input_str = class_converter(path_or_jobs)
    else:
        input_str = path_or_jobs

    # At this point, we have a big string of jobs
    from_string_converter = classes_in_namespaces_converter_with_compression(
        reference_namespace=Namespace()
    )
    return from_string_converter(input_str)


_marker = object()


class JobStateDatabase(RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
        'database_class',
        default='socorro.external.postgresql.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql'
    )

    def __init__(self, config=None):
        self.config = config
        self.database_class = config.database_class(config)

    def has_data(self):
        with transaction_context(self.database_class) as conn:
            return bool(single_value_sql(conn, 'SELECT count(*) FROM cron_job'))

    def __iter__(self):
        records = []
        with transaction_context(self.database_class) as conn:
            records.extend([
                record[0] for record in
                execute_query_fetchall(conn, 'SELECT app_name FROM cron_job')
            ])
        return iter(records)

    def __contains__(self, key):
        """return True if we have a job by this key"""
        try:
            with transaction_context(self.database_class) as conn:
                single_value_sql(
                    conn,
                    """SELECT app_name
                    FROM cron_job
                    WHERE app_name = %s""",
                    (key,)
                )
                return True
        except SQLDidNotReturnSingleValue:
            return False

    def items(self):
        """return all the app_names and their values as tuples"""
        sql = """
            SELECT
                app_name,
                next_run,
                first_run,
                last_run,
                last_success,
                depends_on,
                error_count,
                last_error
            FROM cron_job"""
        columns = (
            'app_name',
            'next_run', 'first_run', 'last_run', 'last_success',
            'depends_on', 'error_count', 'last_error'
        )
        items = []
        with transaction_context(self.database_class) as conn:
            for record in execute_query_fetchall(conn, sql):
                row = dict(zip(columns, record))
                items.append((row.pop('app_name'), row))
        return items

    def keys(self):
        """return a list of all app_names"""
        return [key for key, _ in self.items()]

    def values(self):
        """return a list of all state values"""
        return [val for _, val in self.items()]

    def __getitem__(self, key):
        """return the job info or raise a KeyError"""
        sql = """
            SELECT
                next_run,
                first_run,
                last_run,
                last_success,
                depends_on,
                error_count,
                last_error,
                ongoing
            FROM cron_job
            WHERE app_name = %s
        """
        columns = (
            'next_run', 'first_run', 'last_run', 'last_success',
            'depends_on', 'error_count', 'last_error', 'ongoing'
        )
        try:
            with transaction_context(self.database_class) as conn:
                record = single_row_sql(conn, sql, (key,))
        except SQLDidNotReturnSingleRow:
            raise KeyError(key)
        row = dict(zip(columns, record))

        # Unserialize last_error into a Python dict
        if row['last_error']:
            row['last_error'] = json.loads(row['last_error'])

        return row

    def __setitem__(self, key, value):
        class LastErrorEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, type):
                    return repr(obj)
                return json.JSONEncoder.default(self, obj)

        with transaction_context(self.database_class) as connection:
            try:
                single_value_sql(
                    connection,
                    """
                    SELECT ongoing
                    FROM cron_job
                    WHERE
                        app_name = %s
                    FOR UPDATE NOWAIT
                    """,
                    (key,)
                )
                # If the above single_value_sql() didn't raise a
                # SQLDidNotReturnSingleValue exception, it means
                # there is a row by this app_name.
                # Therefore, the next SQL is an update.
                next_sql = """
                    UPDATE cron_job
                    SET
                        next_run = %(next_run)s,
                        first_run = %(first_run)s,
                        last_run = %(last_run)s,
                        last_success = %(last_success)s,
                        depends_on = %(depends_on)s,
                        error_count = %(error_count)s,
                        last_error = %(last_error)s,
                        ongoing = %(ongoing)s
                    WHERE
                        app_name = %(app_name)s
                """
            except OperationalError as exception:
                if 'could not obtain lock' in exception.args[0]:
                    raise RowLevelLockError(exception.args[0])
                else:
                    raise
            except SQLDidNotReturnSingleValue:
                # the key does not exist, do an insert
                next_sql = """
                    INSERT INTO cron_job (
                        app_name,
                        next_run,
                        first_run,
                        last_run,
                        last_success,
                        depends_on,
                        error_count,
                        last_error,
                        ongoing
                    ) VALUES (
                        %(app_name)s,
                        %(next_run)s,
                        %(first_run)s,
                        %(last_run)s,
                        %(last_success)s,
                        %(depends_on)s,
                        %(error_count)s,
                        %(last_error)s,
                        %(ongoing)s
                    )
                """

            # serialize last_error if it's a {}
            last_error = value['last_error']
            if isinstance(last_error, dict):
                last_error = json.dumps(value['last_error'], cls=LastErrorEncoder)

            parameters = {
                'app_name': key,
                'next_run': value['next_run'],
                'first_run': value['first_run'],
                'last_run': value['last_run'],
                'last_success': value.get('last_success'),
                'depends_on': value['depends_on'],
                'error_count': value['error_count'],
                'last_error': last_error,
                'ongoing': value.get('ongoing'),
            }
            try:
                execute_no_results(connection, next_sql, parameters)
            except IntegrityError as exception:
                # See CREATE_CRONTABBER_APP_NAME_UNIQUE_INDEX for why
                # we know to look for this mentioned in the error message.
                if 'crontabber_unique_app_name_idx' in exception.args[0]:
                    raise RowLevelLockError(exception.args[0])
                raise

    def copy(self):
        with transaction_context(self.database_class) as connection:
            sql = """SELECT
                    app_name,
                    next_run,
                    first_run,
                    last_run,
                    last_success,
                    depends_on,
                    error_count,
                    last_error,
                    ongoing
                FROM cron_job
            """
            columns = (
                'app_name',
                'next_run', 'first_run', 'last_run', 'last_success',
                'depends_on', 'error_count', 'last_error', 'ongoing'
            )
            all = {}
            for record in execute_query_iter(connection, sql):
                row = dict(zip(columns, record))
                all[row.pop('app_name')] = row
            return all

    def update(self, data):
        for key in data:
            self[key] = data[key]

    def get(self, key, default=None):
        """return the item by key or return 'default'"""
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, default=_marker):
        """remove the item by key
        If not default is specified, raise KeyError if nothing
        could be removed.
        Return 'default' if specified and nothing could be removed
        """
        try:
            popped = self[key]
            del self[key]
            return popped
        except KeyError:
            if default == _marker:
                raise
            return default

    def __delitem__(self, key):
        """remove the item by key or raise KeyError"""
        with transaction_context(self.database_class) as connection:
            try:
                # result intentionally ignored
                single_value_sql(
                    connection,
                    """SELECT app_name
                       FROM cron_job
                       WHERE
                            app_name = %s""",
                    (key,)
                )
            except SQLDidNotReturnSingleValue:
                raise KeyError(key)

            # item exists
            execute_no_results(
                connection,
                """DELETE FROM cron_job
                   WHERE app_name = %s""",
                (key,)
            )


def line_splitter(text):
    return [x.strip() for x in re.split('\n|,|;', text.strip())
            if x.strip() and not x.strip().startswith('#')]


def pipe_splitter(text):
    return text.split('|', 1)[0]


def get_extra_as_options(input_str):
    if '|' not in input_str:
        raise JobDescriptionError('No frequency and/or time defined')
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
    n.add_option(
        'frequency',
        doc='frequency',
        default=frequency,
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )
    n.add_option(
        'time',
        doc='time',
        default=time_,
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )
    return n


def classes_in_namespaces_converter_with_compression(
    reference_namespace={},
    template_for_namespace="class-%(name)s",
    list_splitter_fn=line_splitter,
    class_extractor=pipe_splitter,
    extra_extractor=get_extra_as_options
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

    def class_list_converter(class_list_str):
        """This function becomes the actual converter used by configman to
        take a string and convert it into the nested sequence of Namespaces,
        one for each class in the list.  It does this by creating a proxy
        class stuffed with its own 'required_config' that's dynamically
        generated."""
        if isinstance(class_list_str, six.string_types):
            class_str_list = list_splitter_fn(class_list_str)
        else:
            raise TypeError('must be derivative of str')

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
            for namespace_index, class_list_element in enumerate(class_str_list):
                try:
                    a_class = class_converter(class_extractor(class_list_element))
                except CannotConvertError:
                    raise JobNotFoundError(class_list_element)

                class_list.append((a_class.__name__, a_class))
                # figure out the Namespace name
                namespace_name_dict = {
                    'name': a_class.__name__,
                    'index': namespace_index
                }
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
                    for k, v in a_class.get_required_config().items():
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

        # result of class_list_converter
        return InnerClassList
    # result of classes_in_namespaces_converter
    return class_list_converter


def check_time(value):
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


class CronTabberApp(App, RequiredConfig):
    app_name = 'crontabber'
    app_version = 1
    app_description = "crontabber app"

    config_defaults = {
        'always_ignore_mismatches': True,
        'resource': {
            'postgresql': {
                'database_class': (
                    'socorro.external.postgresql.connection_context.ConnectionContext'
                ),
            },
        },
        'crontabber': {
            'max_ongoing_age_hours': 2
        }
    }

    required_config = Namespace()
    # the most important option, 'jobs', is defined last
    required_config.namespace('crontabber')
    required_config.crontabber.add_option(
        name='job_state_db_class',
        default='socorro.cron.crontabber_app.JobStateDatabase',
        doc='Class to load and save the state and runs',
        from_string_converter=class_converter,
    )
    required_config.crontabber.add_option(
        'jobs',
        default='socorro.cron.crontabber_app.DEFAULT_JOBS',
        from_string_converter=jobs_converter,
        doc='Crontabber jobs spec or Python dotted path to jobs spec',
    )
    required_config.crontabber.add_option(
        'error_retry_time',
        default=300,
        doc='number of seconds to re-attempt a job that failed'
    )
    required_config.crontabber.add_option(
        'max_ongoing_age_hours',
        default=12.0,
        doc='Timeout in hours for a locked job.'
    )

    # for local use, independent of the JSONAndPostgresJobDatabase
    required_config.crontabber.add_option(
        'database_class',
        default='socorro.external.postgresql.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql'
    )

    # sentry
    required_config.namespace('sentry')
    required_config.sentry.add_option(
        'dsn',
        doc='DSN for Sentry via raven',
        default='',
        reference_value_from='secrets.sentry',
        secret=True
    )

    # subcommands
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
        name='mark-success',
        default='',
        doc='Mark specified jobs as successful. Comma-separated list of jobs or "all".',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
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
        name='sentrytest',
        default=False,
        doc='Send a sample raven exception',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True,
    )
    required_config.add_option(
        name='reset-job',
        default='',
        doc='Pretend a job has never been run',
        short_form='r',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True,
    )

    def __init__(self, config):
        super().__init__(config)
        self.database_class = self.config.crontabber.database_class(config.crontabber)

    def main(self):
        if self.config.get('list-jobs'):
            self.list_jobs()
            return 0
        elif self.config.get('mark-success'):
            self.mark_success(self.config.get('mark-success'))
            return 0
        elif self.config.get('reset-job'):
            self.reset_job(self.config.get('reset-job'))
            return 0
        elif self.config.get('audit-ghosts'):
            self.audit_ghosts()
            return 0
        elif self.config.get('configtest'):
            return not self.configtest() and 1 or 0
        elif self.config.get('sentrytest'):
            return not self.sentrytest() and 1 or 0
        if self.config.get('job'):
            self.run_one(self.config['job'], self.config.get('force'))
        else:
            try:
                self.run_all()
            except RowLevelLockError:
                self.logger.debug('Next job to work on is already ongoing')
                return 2
            except OngoingJobError:
                self.logger.debug('Next job to work on is already ongoing')
                return 3
        return 0

    @property
    def job_state_database(self):
        if not getattr(self, '_job_state_database', None):
            self._job_state_database = (
                self.config.crontabber.job_state_db_class(self.config.crontabber)
            )
        return self._job_state_database

    def list_jobs(self, stream=None):
        if not stream:
            stream = sys.stdout
        _fmt = '%Y-%m-%d %H:%M:%S'
        _now = utc_now()
        PAD = 15
        for class_name, job_class in self.config.crontabber.jobs.class_list:
            class_config = self.config.crontabber['class-%s' % class_name]
            freq = class_config.frequency
            if class_config.time:
                freq += ' @ %s' % class_config.time
            class_name = job_class.__module__ + '.' + job_class.__name__
            stream.write('=== JOB %s\n' % ('=' * 72))
            stream.write('%s%s\n' % ('Class:'.ljust(PAD), class_name))
            stream.write('%s%s\n' % ('App name:'.ljust(PAD), job_class.app_name))
            stream.write('%s%s\n' % ('Frequency:'.ljust(PAD), freq))
            try:
                info = self.job_state_database[job_class.app_name]
            except KeyError:
                stream.write('*NO PREVIOUS RUN INFO*')
                continue
            if info.get('ongoing'):
                stream.write('Ongoing now! '.ljust(PAD))
                stream.write('Started %s ago\n' % timesince(_now, info.get('ongoing')))
            stream.write('Last run:'.ljust(PAD))
            if info['last_run']:
                stream.write(info['last_run'].strftime(_fmt).ljust(20))
                stream.write('(%s ago)\n' % timesince(info['last_run'], _now))
            else:
                stream.write('none\n')
            stream.write('Last success:'.ljust(PAD))
            if info.get('last_success'):
                stream.write(info['last_success'].strftime(_fmt).ljust(20))
                stream.write('(%s ago)\n' % timesince(info['last_success'], _now))
            else:
                stream.write('no previous successful run\n')
            stream.write('Next run:'.ljust(PAD))
            if info['next_run']:
                stream.write(info['next_run'].strftime(_fmt).ljust(20))
                if _now > info['next_run']:
                    stream.write(' (was %s ago)\n' % timesince(info['next_run'], _now))
                else:
                    stream.write(' (in %s)\n' % timesince(_now, info['next_run']))
            else:
                stream.write('none\n')
            if info.get('last_error') not in (None, '{}', {}):
                last_error = json.loads(info['last_error'])
                stream.write('Error!!'.ljust(PAD) + ' (%s times)\n' % info['error_count'])
                stream.write('Traceback (most recent call last):')
                stream.write('%s %s: %s\n' % (
                    last_error['traceback'], last_error['type'], last_error['value']
                ))
            stream.write('\n')

    def get_job_data(self, job_list_string):
        """Converts job_list_string specification into list of jobs

        :arg str job_list_string: specifies the jobs to return as a comma separated
            list of app names or description or "all" to return them all

        :returns: list of ``(class_name, job_class)`` tuples

        """
        class_list = self.config.crontabber.jobs.class_list

        if job_list_string.lower() == 'all':
            return class_list

        job_list = [item.strip() for item in job_list_string.split(',')]

        job_classes = []
        for description in job_list:
            for class_name, job_class in class_list:
                python_module = job_class.__module__ + '.' + job_class.__name__
                if description == job_class.app_name or description == python_module:
                    job_classes.append((class_name, job_class))
                    break
            else:
                raise JobNotFoundError(description)
        return job_classes

    def mark_success(self, job_list_string):
        """Mark jobs as successful in crontabber bookkeeping"""
        job_classes = self.get_job_data(job_list_string)
        now = utc_now()

        for class_name, job_class in job_classes:
            app_name = job_class.app_name
            job_name = job_class.__module__ + '.' + job_class.__name__
            job_config = self.config.crontabber['class-%s' % class_name]
            self.logger.info('Marking %s (%s) for success...', app_name, job_name)
            self._log_run(
                job_class,
                seconds=0,
                time_=job_config.time,
                last_success=now,
                now=now,
                exc_type=None,
                exc_value=None,
                exc_tb=None
            )
            self._remember_success(job_class, success_date=now, duration=0)

    def reset_job(self, description):
        """remove the job from the state.
        if means that next time we run, this job will start over from scratch.
        """
        class_list = self.config.crontabber.jobs.class_list
        for class_name, job_class in class_list:
            if (
                job_class.app_name == description or
                description == job_class.__module__ + '.' + job_class.__name__
            ):
                if job_class.app_name in self.job_state_database:
                    self.logger.info('App reset')
                    self.job_state_database.pop(job_class.app_name)
                else:
                    self.logger.warning('App already reset')
                return
        raise JobNotFoundError(description)

    def run_all(self):
        class_list = self.config.crontabber.jobs.class_list
        for class_name, job_class in class_list:
            class_config = self.config.crontabber['class-%s' % class_name]
            self._run_one(job_class, class_config)

    def run_one(self, description, force=False):
        # the description in this case is either the app_name or the full
        # module/class reference
        class_list = self.config.crontabber.jobs.class_list
        for class_name, job_class in class_list:
            if (
                job_class.app_name == description or
                description == job_class.__module__ + '.' + job_class.__name__
            ):
                class_config = self.config.crontabber['class-%s' % class_name]
                self._run_one(job_class, class_config, force=force)
                return
        raise JobNotFoundError(description)

    def _run_one(self, job_class, config, force=False):
        seconds = convert_frequency(config.frequency)
        time_ = config.time
        if not force:
            if not self.time_to_run(job_class, time_):
                self.logger.debug("skipping %r because it's not time to run", job_class)
                return

        self.logger.debug('about to run %r', job_class)
        app_name = job_class.app_name
        info = self.job_state_database.get(app_name)

        last_success = None
        now = utc_now()
        log_run = True

        exc_type = exc_value = exc_tb = None
        try:
            t0 = time.time()
            for last_success in self._run_job(job_class, config, info):
                t1 = time.time()
                self.logger.debug('successfully ran %r on %s', job_class, last_success)
                self._remember_success(job_class, last_success, t1 - t0)
                # _run_job() returns a generator, so we don't know how
                # many times this will loop. Anyway, we need to reset the
                # 't0' for the next loop if there is one.
                t0 = time.time()
        except (OngoingJobError, RowLevelLockError):
            # It's not an actual runtime error. It just basically means
            # you can't start crontabber right now.
            log_run = False
            raise
        except Exception:
            t1 = time.time()
            exc_type, exc_value, exc_tb = sys.exc_info()

            if self.config.sentry and self.config.sentry.dsn:
                client = raven_client.get_client(self.config.sentry.dsn)
                identifier = client.get_ident(client.captureException())
                self.logger.info('Error captured in Sentry. Reference: %s' % identifier)

            self.logger.debug(
                'error when running %r on %s', job_class, last_success, exc_info=True
            )
            self._remember_failure(
                job_class,
                t1 - t0,
                exc_type,
                exc_value,
                exc_tb
            )

        finally:
            if log_run:
                self._log_run(
                    job_class,
                    seconds,
                    time_,
                    last_success,
                    now,
                    exc_type, exc_value, exc_tb
                )

    def _remember_success(self, class_, success_date, duration):
        with transaction_context(self.database_class) as connection:
            app_name = class_.app_name
            execute_no_results(
                connection,
                """INSERT INTO cron_log (
                    app_name,
                    success,
                    duration,
                    log_time
                ) VALUES (
                    %s,
                    %s,
                    %s,
                    %s
                )""",
                (app_name, success_date, '%.5f' % duration, utc_now()),
            )
            metrics.gauge('job_success_runtime', value=duration, tags=['job:%s' % app_name])

    def _remember_failure(self, class_, duration, exc_type, exc_value, exc_tb):
        with transaction_context(self.database_class) as connection:
            exc_traceback = ''.join(traceback.format_tb(exc_tb))
            app_name = class_.app_name
            execute_no_results(
                connection,
                """INSERT INTO cron_log (
                    app_name,
                    duration,
                    exc_type,
                    exc_value,
                    exc_traceback,
                    log_time
                ) VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )""",
                (
                    app_name,
                    '%.5f' % duration,
                    repr(exc_type),
                    repr(exc_value),
                    exc_traceback,
                    utc_now()
                ),
            )
            metrics.gauge('job_failure_runtime', value=duration, tags=['job:%s' % app_name])

    def time_to_run(self, class_, time_):
        """return true if it's time to run the job.
        This is true if there is no previous information about its last run
        or if the last time it ran and set its next_run to a date that is now
        past.
        """
        app_name = class_.app_name
        try:
            info = self.job_state_database[app_name]
        except KeyError:
            if time_:
                h, m = [int(x) for x in time_.split(':')]
                # only run if this hour and minute is < now
                now = utc_now()
                if now.hour > h:
                    return True
                elif now.hour == h and now.minute >= m:
                    return True
                return False
            else:
                # no past information, run now
                return True
        next_run = info['next_run']

        if not next_run:
            # It has never run before.
            # If it has an active ongoing status it means two
            # independent threads tried to start it. The second one
            # (by a tiny time margin) will have a job_class whose
            # `ongoing` value has already been set.
            # If that's the case, let it through because it will
            # commence and break due to RowLevelLockError in the
            # state's __setitem__ method.
            return bool(info['ongoing'])

        if next_run < utc_now():
            return True
        return False

    def _run_job(self, class_, config, info):
        # here we go!
        instance = class_(config, info)
        self._set_ongoing_job(class_)
        result = instance.main()
        return result

    def _set_ongoing_job(self, class_):
        app_name = class_.app_name
        info = self.job_state_database.get(app_name)
        if info:
            # Was it already ongoing?
            if info.get('ongoing'):
                # Unless it's been ongoing for ages, raise OngoingJobError
                age_hours = (utc_now() - info['ongoing']).seconds / 3600.0
                if age_hours < self.config.crontabber.max_ongoing_age_hours:
                    raise OngoingJobError(info['ongoing'])
                else:
                    self.logger.debug(
                        '{} has been ongoing for {:2} hours. Ignore it and running the app anyway.'
                        .format(app_name, age_hours)
                    )
            info['ongoing'] = utc_now()
        else:
            info = {
                'next_run': None,
                'first_run': None,
                'last_run': None,
                'last_success': None,
                'last_error': {},
                'error_count': 0,
                'depends_on': [],
                'ongoing': utc_now(),
            }
        self.job_state_database[app_name] = info

    def _log_run(self, class_, seconds, time_, last_success, now, exc_type, exc_value, exc_tb):
        assert inspect.isclass(class_)
        app_name = class_.app_name
        info = self.job_state_database.get(app_name, {})
        info['depends_on'] = []
        if not info.get('first_run'):
            info['first_run'] = now
        info['last_run'] = now
        if last_success:
            info['last_success'] = last_success
        if exc_type:
            # it errored, try very soon again
            info['next_run'] = now + datetime.timedelta(
                seconds=self.config.crontabber.error_retry_time
            )
        else:
            info['next_run'] = now + datetime.timedelta(seconds=seconds)
            if time_:
                h, m = [int(x) for x in time_.split(':')]
                info['next_run'] = info['next_run'].replace(
                    hour=h, minute=m, second=0, microsecond=0
                )

        if exc_type:
            tb = ''.join(traceback.format_tb(exc_tb))
            info['last_error'] = {
                'type': exc_type,
                'value': str(exc_value),
                'traceback': tb,
            }
            info['error_count'] = info.get('error_count', 0) + 1
        else:
            info['last_error'] = {}
            info['error_count'] = 0

        # Clearly it's not "ongoing" any more when it's here, because
        # being here means the job has finished.
        info['ongoing'] = None

        self.job_state_database[app_name] = info

    def sentrytest(self):
        """return true if we managed to send a sample raven exception"""
        if not (self.config.sentry and self.config.sentry.dsn):
            raise SentryConfigurationError('sentry dsn not configured')

        client = raven_client.get_client(self.config.sentry.dsn)
        identifier = client.captureMessage('Sentry test sent from crontabber')
        self.logger.info('Sentry successful identifier: %s', identifier)
        return True


# NOTE(willkg): Times are in UTC.
DEFAULT_JOBS = ','.join([
    # Elasticsearch maintenance
    'socorro.cron.jobs.elasticsearch_cleanup.ElasticsearchCleanupCronApp|7d|06:00',

    # Product/version maintenance
    'socorro.cron.jobs.archivescraper.ArchiveScraperCronApp|1h',

    # Crash data analysis
    'socorro.cron.jobs.update_signatures.UpdateSignaturesCronApp|1h',

    # Dependency checking
    'socorro.cron.jobs.monitoring.DependencySecurityCheckCronApp|1d|05:00',

    # Processed crash verification
    'socorro.cron.jobs.verify_processed.VerifyProcessedCronApp|1d|04:00',
])
