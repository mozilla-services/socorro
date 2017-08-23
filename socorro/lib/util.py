# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import collections
import logging
import sys
import threading
import traceback


class FakeLogger(object):
    loggingLevelNames = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
        logging.FATAL: "FATAL"
    }

    def create_log_message(self, *args):
        try:
            level = FakeLogger.loggingLevelNames[args[0]]
        except KeyError:
            level = "Level[%s]" % str(args[0])
        message = args[1] % args[2:]
        return '%s %s' % (level, message)

    def log(self, *args, **kwargs):
        print >>sys.stderr, self.create_log_message(*args)

    def debug(self, *args, **kwargs):
        self.log(logging.DEBUG, *args)

    def info(self, *args, **kwargs):
        self.log(logging.INFO, *args)

    def warning(self, *args, **kwargs):
        self.log(logging.WARNING, *args)
    warn = warning

    def error(self, *args, **kwargs):
        self.log(logging.ERROR, *args)

    def critical(self, *args, **kwargs):
        self.log(logging.CRITICAL, *args)
    fatal = critical


class SilentFakeLogger(object):
    def log(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def critical(self, *args, **kwargs):
        pass

    def fatal(self, *args, **kwargs):
        pass


class StringLogger(FakeLogger):
    def __init__(self):
        super(StringLogger, self).__init__()
        self.messages = []

    def log(self, *args, **kwargs):
        message = self.create_log_message(*args)
        self.messages.append(message)

    def getMessages(self):
        log = '\n'.join(self.messages)
        self.messages = []
        return log


# logging routines

def setup_logging_handlers(logger, config):
    stderrLog = logging.StreamHandler()
    stderrLog.setLevel(config.stderrErrorLoggingLevel)
    stderrLogFormatter = logging.Formatter(config.stderrLineFormatString)
    stderrLog.setFormatter(stderrLogFormatter)
    logger.addHandler(stderrLog)

    syslog = logging.handlers.SysLogHandler(facility=config.syslogFacilityString)
    syslog.setLevel(config.syslogErrorLoggingLevel)
    syslogFormatter = logging.Formatter(config.syslogLineFormatString)
    syslog.setFormatter(syslogFormatter)
    logger.addHandler(syslog)


def echo_config(logger, config):
    logger.info("current configuration:")
    for value in str(config).split('\n'):
        logger.info('%s', value)


logging_report_lock = threading.RLock()


def report_exception_and_continue(logger=FakeLogger(), loggingLevel=logging.ERROR,
                                  ignoreFunction=None, showTraceback=True):
    try:
        exc_type, exc, tb = sys.exc_info()
        if ignoreFunction and ignoreFunction(exc_type, exc, tb):
            return
        if exc_type in (KeyboardInterrupt, SystemExit):
            raise
        logging_report_lock.acquire()  # make sure these multiple log entries stay together
        try:
            logger.log(loggingLevel, "Caught Error: %s", exc_type)
            logger.log(loggingLevel, str(exc))
            if showTraceback:
                logger.log(loggingLevel, "trace back follows:")
                for aLine in traceback.format_exception(exc_type, exc, tb):
                    logger.log(loggingLevel, aLine.strip())
        finally:
            logging_report_lock.release()
    except Exception as x:
        print >>sys.stderr, x


# utilities

def backoff_seconds_generator():
    seconds = [10, 30, 60, 120, 300]
    for x in seconds:
        yield x
    while True:
        yield seconds[-1]


class DotDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def flatten(d, parent_key='', sep='.'):
    """Return a dictionary with only top-level keys. The sub-level fields
    are moved to a top-level key named by concatenating the keys of each level.
    For example:
        IN:
        {
            "a": 1,
            "b": {
                "c": 2,
                "d": {
                    "e": 3
                }
            }
        }
        OUT:
        {
            "a": 1,
            "b.c": 2,
            "b.d.e": 3
        }
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
