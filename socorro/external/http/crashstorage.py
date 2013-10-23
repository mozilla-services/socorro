#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
from configman import Namespace, class_converter
from socorro.external.crashstorage_base import CrashStorageBase

import os
import urllib2
import poster
import socket
import contextlib
poster.streaminghttp.register_openers()

#==============================================================================
class DumpReader(object):
    """this class wraps a dump object to embue it with a read method.  This
    allows the dump to be streamed out as "file" upload."""
    #--------------------------------------------------------------------------
    def __init__(self, the_dump):
        self.dump = the_dump

    #--------------------------------------------------------------------------
    def read(self):
        return self.dump


#==============================================================================
class HTTPPOSTCrashStorage(CrashStorageBase):
    """this a crashstorage derivative that just pushes a crash out to a
    Socorro collector waiting at a url"""
    required_config = Namespace()
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
                "TransactionExecutorWithLimitedBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'url',
        short_form='u',
        doc="The url of the Socorro collector to submit to",
        default="http://127.0.0.1:8882/submit"
    )
    required_config.add_option(
        'timeout',
        doc="timeout in seconds",
        default=5
    )
    required_config.add_option(
        'dump_field_name',
        doc="the default name for the dump field in the http POST",
        default='upload_file_minidump'
    )

    operational_exceptions = (
        socket.timeout
    )
    conditional_exceptions = (
        urllib2.HTTPError,
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(HTTPPOSTCrashStorage, self).__init__(
            config,
            quit_check_callback
        )
        self.transaction = self.config.transaction_executor_class(
            self.config,
            self,
            quit_check_callback
        )

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        self.transaction(
            self.__class__._submit_crash_via_http_POST,
            raw_crash,
            dumps,
            crash_id
        )

    #--------------------------------------------------------------------------
    def _submit_crash_via_http_POST(self, raw_crash, dumps, crash_id):
        for dump_name, dump in dumps.iteritems():
            if not dump_name:
                dump_name = self.config.dump_field_name
            raw_crash[dump_name] = poster.encode.MultipartParam(
                name=dump_name,
                filename=dump_name,
                fileobj=DumpReader(dump)
            )
        datagen, headers = poster.encode.multipart_encode(raw_crash)
        request = urllib2.Request(
            self.config.url,
            datagen,
            headers
        )
        submission_response = urllib2.urlopen(request).read().strip()
        try:
            self.config.logger.debug(
                'submitted %s (original crash_id)',
                raw_crash['uuid']
            )
        except KeyError:
            pass
        self.config.logger.debug(
            'submission response: %s',
            submission_response
            )

    # We want this class to be able to participate in retriable transactions.
    # However transactions is a connecton based system and we really don't
    # have a persistant connection associated with an HTTP POST.  So we
    # will use this class itself as its own connection class.  That means
    # that it must have the following methods.  The really important one here
    # is the __call__ method.  That's the key method employed by the
    # transaction class.
    #--------------------------------------------------------------------------
    def commit(self):
        """HTTP POST doesn't support transactions so this silently
        does nothing"""

    #--------------------------------------------------------------------------
    def rollback(self):
        """HTTP POST doesn't support transactions so this silently
        does nothing"""

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self):
        """this class will serve as its own context manager.  That enables it
        to use the transaction_executor class for retries"""
        yield self

    #--------------------------------------------------------------------------
    def in_transaction(self, dummy):
        """HTTP POST doesn't support transactions, so it is never in
        a transaction."""
        return False

    #--------------------------------------------------------------------------
    def is_operational_exception(self, msg):
        lower_msg = msg.lower()
        if 'timed out' in lower_msg or 'timeout' in lower_msg:
            return True
        return False

    #--------------------------------------------------------------------------
    def force_reconnect(self):
        pass
