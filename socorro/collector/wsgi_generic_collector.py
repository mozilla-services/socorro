# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import web
import time
import zlib
import cgi
import cStringIO

from contextlib import closing

from socorro.lib.ooid import createNewOoid
from socorro.lib.util import DotDict
from socorro.collector.throttler import DISCARD, IGNORE
from socorro.lib.datetimeutil import utc_now
from socorro.external.crashstorage_base import MemoryDumpsMapping

from configman import RequiredConfig, Namespace, class_converter


#==============================================================================
class GenericCollectorBase(RequiredConfig):
    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()

    required_config.add_option(
        'accept_submitted_crash_id',
        doc='a boolean telling the collector to use a crash_id provided in '
            'the crash submission',
        default=False
    )
    required_config.add_option(
        'checksum_method',
        doc='a reference to method that accepts a string and calculates a'
            'hash value',
        default='hashlib.md5',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.logger = self.config.logger
        self.checksum_method = self._get_checksum_method()
        self.accept_submitted_crash_id = self._get_accept_submitted_crash_id()

    #--------------------------------------------------------------------------
    def _get_accept_submitted_crash_id(self):
        return self.config.accept_submitted_crash_id

    #--------------------------------------------------------------------------
    def _get_checksum_method(self):
        return self.config.checksum_method

    #--------------------------------------------------------------------------
    def _process_fieldstorage(self, fs):
        if isinstance(fs, list):
            return [self._process_fieldstorage(x) for x in fs]
        elif fs.filename is None:
            return fs.value
        else:
            return fs

    #--------------------------------------------------------------------------
    def _form_as_mapping(self):
        """this method returns the POST form mapping with any gzip
        decompression automatically handled"""
        if web.ctx.env.get('HTTP_CONTENT_ENCODING') == 'gzip':
            # Handle gzipped form posts
            gzip_header = 16 + zlib.MAX_WBITS
            data = zlib.decompress(web.webapi.data(), gzip_header)
            e = web.ctx.env.copy()
            with closing(cStringIO.StringIO(data)) as fp:
                # this is how web.webapi.rawinput() handles
                # multipart/form-data, as of this writing
                fs = cgi.FieldStorage(fp=fp, environ=e, keep_blank_values=1)
                form = web.utils.storage(
                    [(k, self._process_fieldstorage(fs[k])) for k in fs.keys()]
                )
                return form
        return web.webapi.rawinput()

    #--------------------------------------------------------------------------
    @staticmethod
    def _no_x00_character(value):
        if isinstance(value, unicode) and u'\u0000' in value:
            return ''.join(c for c in value if c != u'\u0000')
        if isinstance(value, str) and '\x00' in value:
            return ''.join(c for c in value if c != '\x00')
        return value

    #--------------------------------------------------------------------------
    def _get_raw_crash_from_form(self):
        """this method creates the raw_crash and the dumps mapping using the
        POST form"""
        dumps = MemoryDumpsMapping()
        raw_crash = DotDict()
        raw_crash.dump_checksums = DotDict()
        for name, value in self._form_as_mapping().iteritems():
            name = self._no_x00_character(name)
            if isinstance(value, basestring):
                if name != "dump_checksums":
                    raw_crash[name] = self._no_x00_character(value)
            elif hasattr(value, 'file') and hasattr(value, 'value'):
                dumps[name] = value.value
                raw_crash.dump_checksums[name] = \
                    self.checksum_method(value.value).hexdigest()
            elif isinstance(value, int):
                raw_crash[name] = value
            else:
                raw_crash[name] = value.value
        return raw_crash, dumps

    #--------------------------------------------------------------------------
    def POST(self, *args):
        raise NotImplementedError()

#==============================================================================
class GenericCollector(GenericCollectorBase):
    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()

    required_config.add_option(
        'type_tag',
        doc='the prefix to return to the client in front of the crash_id',
        default='xx-'
    )
    #--------------------------------------------------------------------------
    # storage namespace
    #     the namespace is for config parameters crash storage
    #--------------------------------------------------------------------------
    required_config.namespace('storage')
    required_config.storage.add_option(
        'crashstorage_class',
        doc='the source storage class',
        default='socorro.external.fs.crashstorage'
                '.FSLegacyDatedRadixTreeStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(GenericCollector, self).__init__(config)
        self.type_tag = self.config.type_tag
        self.crash_storage = self.config.storage.crashstorage_class(
            self.config.storage
        )

    #--------------------------------------------------------------------------
    def POST(self, *args):
        raw_crash, dumps = self._get_raw_crash_from_form()

        current_timestamp = utc_now()
        raw_crash.submitted_timestamp = current_timestamp.isoformat()
        # legacy - ought to be removed someday
        raw_crash.timestamp = time.time()

        if (not self.config.accept_submitted_crash_id
            or 'crash_id' not in raw_crash
        ):
            crash_id = createNewOoid(current_timestamp)
            raw_crash.crash_id = crash_id
            self.logger.info('%s received', crash_id)
        else:
            crash_id = raw_crash.crash_id
            self.logger.info('%s received with existing crash_id:', crash_id)

        raw_crash.type_tag = self.type_tag

        self.crash_storage.save_raw_crash(
            raw_crash,
            dumps,
            crash_id
        )
        self.logger.info('%s accepted', crash_id)
        return "CrashID=%s%s\n" % (self.type_tag, crash_id)
