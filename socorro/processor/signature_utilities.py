# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re

from itertools import islice

from configman import Namespace, RequiredConfig
from configman.converters import class_converter

from socorro.lib.transform_rules import Rule
from socorro.external.postgresql.dbapi2_util import execute_query_fetchall


#==============================================================================
class SignatureTool(RequiredConfig):
    """this is the base class for signature generation objects.  It defines the
    basic interface and provides truncation and quoting service.  Any derived
    classes should implement the '_do_generate' function.  If different
    truncation or quoting techniques are desired, then derived classes may
    override the 'generate' function."""
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        self.config = config
        self.max_len = config.setdefault('signature_max_len', 255)
        self.escape_single_quote = \
            config.setdefault('signature_escape_single_quote', True)
        self.quit_check_callback = quit_check_callback

    #--------------------------------------------------------------------------
    def generate(
        self,
        source_list,
        hang_type=0,
        crashed_thread=None,
        delimiter=' | '
    ):
        signature, signature_notes = self._do_generate(
            source_list,
            hang_type,
            crashed_thread,
            delimiter
        )
        if self.escape_single_quote:
            signature = signature.replace("'", "''")
        if len(signature) > self.max_len:
            signature = "%s..." % signature[:self.max_len - 3]
            signature_notes.append('SignatureTool: signature truncated due to '
                                   'length')
        return signature, signature_notes

    #--------------------------------------------------------------------------
    def _do_generate(
        self,
        source_list,
        hang_type,
        crashed_thread,
        delimiter
    ):
        raise NotImplementedError


#==============================================================================
class CSignatureToolBase(SignatureTool):
    """This is the base class for signature generation tools that work on
    breakpad C/C++ stacks.  It provides a method to normalize signatures
    and then defines its own '_do_generate' method."""

    required_config = Namespace()
    required_config.add_option(
        'collapse_arguments',
        default=False,
        doc="remove function arguments during normalization",
        reference_value_from='resource.signature'
    )

    hang_prefixes = {
        -1: "hang",
        1: "chromehang"
    }

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(CSignatureToolBase, self).__init__(config, quit_check_callback)
        self.irrelevant_signature_re = None
        self.prefix_signature_re = None
        self.signatures_with_line_numbers_re = None
        self.signature_sentinels = []

        self.fixup_space = re.compile(r' (?=[\*&,])')
        self.fixup_comma = re.compile(r',(?! )')

    #--------------------------------------------------------------------------
    @staticmethod
    def _is_exception(
        exception_list,
        remaining_original_line,
        line_up_to_current_position
    ):
        for an_exception in exception_list:
            if remaining_original_line.startswith(an_exception):
                return True
            if line_up_to_current_position.endswith(an_exception):
                return True
        return False

    #--------------------------------------------------------------------------
    def _collapse(
        self,
        function_signature_str,
        open_string,
        replacement_open_string,
        close_string,
        replacement_close_string,
        exception_substring_list=(),  # list of exceptions that shouldn't collapse
    ):
        """this method takes a string representing a C/C++ function signature
        and replaces anything between to possibly nested delimiters"""
        target_counter = 0
        collapsed_list = []
        exception_mode = False

        def append_if_not_in_collapse_mode(a_character):
            if not target_counter:
                collapsed_list.append(a_character)

        for index, a_character in enumerate(function_signature_str):
            if a_character == open_string:
                if self._is_exception(
                    exception_substring_list,
                    function_signature_str[index + 1:],
                    function_signature_str[:index]
                ):
                    exception_mode = True
                    append_if_not_in_collapse_mode(a_character)
                    continue
                append_if_not_in_collapse_mode(replacement_open_string)
                target_counter += 1
            elif a_character == close_string:
                if exception_mode:
                    append_if_not_in_collapse_mode(a_character)
                    exception_mode = False
                else:
                    target_counter -= 1
                    append_if_not_in_collapse_mode(replacement_close_string)
            else:
                append_if_not_in_collapse_mode(a_character)

        edited_function = ''.join(collapsed_list)
        return edited_function

    #--------------------------------------------------------------------------
    def normalize_signature(
        self,
        module=None,
        function=None,
        file=None,
        line=None,
        module_offset=None,
        offset=None,
        function_offset=None,
        normalized=None,
        **kwargs  # eat any extra kwargs passed in
    ):
        """ returns a structured conglomeration of the input parameters to
        serve as a signature.  The parameter names of this function reflect the
        exact names of the fields from the jsonMDSW frame output.  This allows
        this function to be invoked by passing a frame as **a_frame. Sometimes,
        a frame may already have a normalized version cached.  If that exsists,
        return it instead.
        """
        if normalized is not None:
            return normalized
        if function:
            function = self._collapse(
                function,
                '<',
                '<',
                '>',
                'T>',
                ('name omitted', )
            )
            if self.config.collapse_arguments:
                function = self._collapse(
                    function,
                    '(',
                    '',
                    ')',
                    '',
                    ('anonymous namespace', 'operator')
                )

            if self.signatures_with_line_numbers_re.match(function):
                function = "%s:%s" % (function, line)
            # Remove spaces before all stars, ampersands, and commas
            function = self.fixup_space.sub('', function)
            # Ensure a space after commas
            function = self.fixup_comma.sub(', ', function)
            return function
        #if source is not None and source_line is not None:
        if file and line:
            filename = file.rstrip('/\\')
            if '\\' in filename:
                file = filename.rsplit('\\')[-1]
            else:
                file = filename.rsplit('/')[-1]
            return '%s#%s' % (file, line)
        if not module and not module_offset and offset:
            return "@%s" % offset
        if not module:
            module = ''  # might have been None
        return '%s@%s' % (module, module_offset)

    #--------------------------------------------------------------------------
    def _do_generate(self,
                     source_list,
                     hang_type,
                     crashed_thread,
                     delimiter=' | '):
        """
        each element of signatureList names a frame in the crash stack; and is:
          - a prefix of a relevant frame: Append this element to the signature
          - a relevant frame: Append this element and stop looking
          - irrelevant: Append this element only after seeing a prefix frame
        The signature is a ' | ' separated string of frame names
        """
        signature_notes = []
        # shorten source_list to the first signatureSentinel
        sentinel_locations = []
        for a_sentinel in self.signature_sentinels:
            if type(a_sentinel) == tuple:
                a_sentinel, condition_fn = a_sentinel
                if not condition_fn(source_list):
                    continue
            try:
                sentinel_locations.append(source_list.index(a_sentinel))
            except ValueError:
                pass
        if sentinel_locations:
            source_list = source_list[min(sentinel_locations):]

        new_signature_list = []
        for a_signature in source_list:
            if self.irrelevant_signature_re.match(a_signature):
                continue
            new_signature_list.append(a_signature)
            if not self.prefix_signature_re.match(a_signature):
                break
        if hang_type:
            new_signature_list.insert(0, self.hang_prefixes[hang_type])
        signature = delimiter.join(new_signature_list)

        if signature == '' or signature is None:
            if crashed_thread is None:
                signature_notes.append("CSignatureTool: No signature could be "
                                       "created because we do not know which "
                                       "thread crashed")
                signature = "EMPTY: no crashing thread identified"
            else:
                signature_notes.append("CSignatureTool: No proper signature "
                                       "could be created because no good data "
                                       "for the crashing thread (%s) was found"
                                       % crashed_thread)
                try:
                    signature = source_list[0]
                except IndexError:
                    signature = "EMPTY: no frame data available"

        return signature, signature_notes


#==============================================================================
class CSignatureTool(CSignatureToolBase):
    """This is a C/C++ signature generation class that gets its initialization
    from configuration."""

    required_config = Namespace()
    required_config.add_option(
        'signature_sentinels',
        doc='a list of frame signatures that should always be considered top '
            'of the stack if present in the stack',
        default="""['_purecall',
               ('mozilla::ipc::RPCChannel::Call(IPC::Message*, IPC::Message*)',
                lambda x: 'CrashReporter::CreatePairedMinidumps(void*, '
                  'unsigned long, nsAString_internal*, nsILocalFile**, '
                  'nsILocalFile**)' in x
               ),
               'Java_org_mozilla_gecko_GeckoAppShell_reportJavaCrash',
               'google_breakpad::ExceptionHandler::HandleInvalidParameter'
              ]""",
        from_string_converter=eval,
        reference_value_from='resource.signature'
    )
    required_config.add_option(
        'irrelevant_signature_re',
        doc='a regular expression matching frame signatures that should be '
            'ignored when generating an overall signature',
        default="""'|'.join([
          '@0x[0-9a-fA-F]{2,}',
          '@0x[1-9a-fA-F]',
          '__aeabi_fcmpgt.*',
          'ashmem',
          'app_process@0x.*',
          'core\.odex@0x.*',
          'CrashStatsLogForwarder::CrashAction',
          '_CxxThrowException',
          'dalvik-heap',
          'dalvik-jit-code-cache',
          'dalvik-LinearAlloc',
          'dalvik-mark-stack',
          'data@app@org\.mozilla\.f.*-\d\.apk@classes\.dex@0x.*',
          'framework\.odex@0x.*',
          'google_breakpad::ExceptionHandler::HandleInvalidParameter.*',
          'KiFastSystemCallRet',
          'libandroid_runtime\.so@0x.*',
          'libbinder\.so@0x.*',
          'libc\.so@.*',
          'libc-2\.5\.so@.*',
          'libEGL\.so@.*',
          'libdvm\.so\s*@\s*0x.*',
          'libgui\.so@0x.*',
          'libicudata.so@.*',
          'libMali\.so@0x.*',
          'libutils\.so@0x.*',
          'libz\.so@0x.*',
          'linux-gate\.so@0x.*',
          'mnt@asec@org\.mozilla\.f.*-\d@pkg\.apk@classes\.dex@0x.*',
          'MOZ_Assert',
          'MOZ_Crash',
          'mozcrt19.dll@0x.*',
          'mozilla::gfx::Log<.*',
          'mozilla::ipc::RPCChannel::Call',
          '_NSRaiseError',
          '(Nt|Zw)WaitForSingleObject(Ex)?',
          '(Nt|Zw)WaitForMultipleObjects(Ex)?',
          'nvmap@0x.*',
          'org\.mozilla\.f.*-\d\.apk@0x.*',
          'RaiseException',
          'RtlpAdjustHeapLookasideDepth',
          'std::_Atomic_fetch_add_4',
          'system@framework@.*\.jar@classes\.dex@0x.*',
          '___TERMINATING_DUE_TO_UNCAUGHT_EXCEPTION___',
          'WaitForSingleObjectExImplementation',
          'WaitForMultipleObjectsExImplementation',
          'RealMsgWaitFor.*'
          '_ZdlPv',
          'zero',
          ])""",
        from_string_converter=eval,
        reference_value_from='resource.signature'
    )
    required_config.add_option(
        'prefix_signature_re',
        doc=(
            'a regular expression matching frame signatures that should '
            'always be coupled with the following frame signature when '
            'generating an overall signature'
        ),
        default="""'|'.join([
          '@0x0',
          '.*CrashAtUnhandlableOOM',
          'Abort',
          '.*abort',
          '.*alloc_impl',
          '_alloca_probe.*',
          '__android_log_assert',
          'arena_.*',
          'BaseGetNamedObjectDirectory',
          '.*calloc',
          'cert_.*',
          'CERT_.*',
          'CFRelease',
          '_chkstk',
          'CleanupPerAppKey',
          'CrashInJS',
          '__delayLoadHelper2',
          'dlmalloc',
          'dlmalloc_trim',
          'dvm.*',
          'EtwEventEnabled',
          'extent_.*',
          'fastcopy_I',
          'fastzero_I',
          '_files_getaddrinfo',
          '.*free',
          'free_impl',
          'GCGraphBuilder::NoteXPCOMChild',
          'getanswer',
          'HandleInvalidParameter',
          'HeapFree',
          'huge_dalloc',
          'ialloc',
          'imalloc',
          'init_library',
          'invalid_parameter_noinfo',
          '_invalid_parameter_noinfo',
          'isalloc',
          'jemalloc_crash',
          'je_.*',
          'JNI_CreateJavaVM',
          '_JNIEnv.*',
          'JNI_GetCreatedJavaVM.*',
          'js::AutoCompartment::AutoCompartment.*',
          'JSAutoCompartment::JSAutoCompartment.*',
          'JS_DHashTableEnumerate',
          'JS_DHashTableOperate',
          'JS_NewStringCopyZ.*',
          'kill',
          '__libc_android_abort',
          'libobjc.A.dylib@0x1568.',
          '(libxul\.so|xul\.dll|XUL)@0x.*',
          'LL_.*',
          'malloc',
          '_MD_.*',
          'memcmp',
          '__memcmp16',
          'memcpy',
          'memmove',
          'memset',
          'mozalloc_abort.*',
          'mozalloc_handle_oom',
          'moz_free',
          'mozilla::AndroidBridge::AutoLocalJNIFrame::~AutoLocalJNIFrame',
          'mozilla::ipc::MessageChannel::Send',
          'mozilla::ipc::RPCChannel::Call',
          'mozilla::ipc::RPCChannel::CxxStackFrame::CxxStackFrame',
          'mozilla::ipc::RPCChannel::EnteredCxxStack',
          'mozilla::ipc::RPCChannel::Send',
          'mozilla::layers::CompositorD3D11::Failed',
          'mozilla::layers::CompositorD3D11::HandleError',
          'mozilla.*FatalError',
          'moz_xmalloc',
          'moz_xrealloc',
          'msvcr120\.dll@0x.*',
          '\<name omitted\>',
          'NP_Shutdown',
          '(NS_)?(Lossy)?(Copy|Append|Convert).*UTF.*',
          'nsACString_internal::Assign.*',
          'nsAString_internal::Assign.*',
          'nsCOMPtr.*',
          'NS_ABORT_OOM.*',
          'NS_DebugBreak.*',
          '[-+]\[NSException raise(:format:(arguments:)?)?\]',
          'nsObjCExceptionLogAbort',
          'nsRefPtr.*',
          'NSS.*',
          'nss.*',
          'nsTArray<.*',
          'nsTArray_base<.*',
          'nsTArray_Impl<.*',
          'NtUser.*',
          'objc_exception_throw',
          'objc_msgSend',
          'operator new',
          'PLDHashTable::.*',
          'PL_.*',
          'port_.*',
          'PORT_.*',
          '_PR_.*',
          'PR_.*',
          '.*ProcessNextEvent.*',
          '__psynch_cvwait',
          '_pthread_cond_wait',
          'pthread_mutex_lock',
          '_purecall',
          'raise',
          'realloc',
          'recv',
          '.*ReentrantMonitor::Wait.*',
          '_RTC_Terminate',
          'Rtl.*',
          '_Rtl.*',
          '__Rtl.*',
          'SEC_.*Item',
          'seckey_.*',
          'SECKEY_.*',
          '__security_check_cookie',
          'send',
          'setjmp',
          'sigblock',
          'sigprocmask',
          'SocketAccept',
          'SocketAcceptRead',
          'SocketAvailable',
          'SocketAvailable64',
          'SocketBind',
          'SocketClose',
          'SocketConnect',
          'SocketGetName',
          'SocketGetPeerName',
          'SocketListen',
          'SocketPoll',
          'SocketRead',
          'SocketRecv',
          'SocketSend',
          'SocketShutdown',
          'SocketSync',
          'SocketTransmitFile',
          'SocketWrite',
          'SocketWritev',
          'ssl_.*',
          'SSL_.*',
          'strcat',
          'ssl3_.*',
          'strchr',
          'strcmp',
          'strcpy',
          '.*strdup',
          'strlen',
          'strncpy',
          'strzcmp16',
          'strstr',
          '__swrite',
          'TlsGetValue',
          'TouchBadMemory',
          '_VEC_memcpy',
          '_VEC_memzero',
          '.*WaitFor.*',
          'wcslen',
          '__wrap_realloc',
          'WSARecv.*',
          'WSASend.*',
          '_ZdaPvRKSt9nothrow_t\"',
          'zzz_AsmCodeRange_.*',
          '.*DebugAbort.*',
          'mozilla::ipc::MessageChannel::~MessageChannel.*',
        ])""",
        from_string_converter=eval,
        reference_value_from='resource.signature'
    )
    required_config.add_option(
        'signatures_with_line_numbers_re',
        doc=(
            'any signatures that match this list should be combined '
            'with their associated source code line numbers'
        ),
        default='js_Interpret'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(CSignatureTool, self).__init__(config, quit_check_callback)
        self.irrelevant_signature_re = re.compile(
            self.config.irrelevant_signature_re
        )
        self.prefix_signature_re = re.compile(
            self.config.prefix_signature_re
        )
        self.signatures_with_line_numbers_re = re.compile(
            self.config.signatures_with_line_numbers_re
        )
        self.signature_sentinels = config.signature_sentinels


#==============================================================================
class CSignatureToolDB(CSignatureToolBase):
    """This is another C/C++ signature generation class.  It gets its signature
    generation rules from a database connection instead of through
    configuration.  It expects a table to exist in the database called
    'csignature_rules' with two columns, 'category' and 'rule', both of a
    character datatype.  Content of the 'rule' column is a text string
    that can be converted via the Python 'eval' method into a Python object.
    For most categories, the rule is simply a string that is converted into
    a regular expression.  For the 'sentinel' category, however, the form
    can be either a string or a tuple comprised of a string and a reference
    to a Python function, usually in the form of a lambda expression."""
    required_config = Namespace()
    required_config.add_option(
        'database_class',
        doc="the class of the database",
        default='socorro.external.postgresql.connection_context.'
                'ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.signature'
    )
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
                "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.signature'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(CSignatureToolDB, self).__init__(config, quit_check_callback)
        self.database = config.database_class(config)
        self.transaction = \
            self.config.transaction_executor_class(
                config,
                self.database,
                quit_check_callback
            )
        self.transaction(self._read_signature_rules_from_database)

    #--------------------------------------------------------------------------
    def _read_signature_rules_from_database(self, connection):
        for category, category_re in (
            ('prefix', 'prefix_signature_re'),
            ('irrelevant', 'irrelevant_signature_re'),
            ('line_number', 'signatures_with_line_numbers_re')
        ):
            rule_element_list = [
                a_rule
                for (a_rule,) in execute_query_fetchall(
                    connection,
                    "select rule from skiplist "
                    "where category = %s",
                    (category, )
                )
            ]
            setattr(
                self,
                category_re,
                re.compile('|'.join(rule_element_list))
            )

        # get sentinel rules
        self.signature_sentinels = [
            eval(sentinel_rule)  # eval quoted strings and tuples
            if sentinel_rule[0] in "'\"(" else
            sentinel_rule  # already a string, don't need to eval
            for (sentinel_rule,) in execute_query_fetchall(
                connection,
                "select rule from csignature_rules where category = 'sentinel'"
            )
        ]


#==============================================================================
class JavaSignatureTool(SignatureTool):
    """This is the signature generation class for Java signatures."""

    java_line_number_killer = re.compile(r'\.java\:\d+\)$')
    java_hex_addr_killer = re.compile(r'@[0-9a-f]{8}')

    #--------------------------------------------------------------------------
    @staticmethod
    def join_ignore_empty(delimiter, list_of_strings):
        return delimiter.join(x for x in list_of_strings if x)

    #--------------------------------------------------------------------------
    def _do_generate(self,
                     source,
                     hang_type_unused=0,
                     crashed_thread_unused=None,
                     delimiter=': '):
        signature_notes = []
        try:
            source_list = [x.strip() for x in source.splitlines()]
        except AttributeError:
            signature_notes.append(
                'JavaSignatureTool: stack trace not in expected format'
            )
            return (
                "EMPTY: Java stack trace not in expected format",
                signature_notes
            )
        try:
            java_exception_class, description = source_list[0].split(':', 1)
            java_exception_class = java_exception_class.strip()
            # relace all hex addresses in the description by the string <addr>
            description = self.java_hex_addr_killer.sub(
                r'@<addr>',
                description
            ).strip()
        except ValueError:
            java_exception_class = source_list[0]
            description = ''
            signature_notes.append(
                'JavaSignatureTool: stack trace line 1 is '
                'not in the expected format'
            )
        try:
            java_method = re.sub(
                self.java_line_number_killer,
                '.java)',
                source_list[1]
            )
            if not java_method:
                signature_notes.append(
                    'JavaSignatureTool: stack trace line 2 is empty'
                )
        except IndexError:
            signature_notes.append(
                'JavaSignatureTool: stack trace line 2 is missing'
            )
            java_method = ''

        # an error in an earlier version of this code resulted in the colon
        # being left out of the division between the description and the
        # java_method if the description didn't end with "<addr>".  This code
        # perpetuates that error while correcting the "<addr>" placement
        # when it is not at the end of the description.  See Bug 865142 for
        # a discussion of the issues.
        if description.endswith('<addr>'):
            # at which time the colon placement error is to be corrected
            # just use the following line as the replacement for this entire
            # if/else block
            signature = self.join_ignore_empty(
                delimiter,
                (java_exception_class, description, java_method)
            )
        else:
            description_java_method_phrase = self.join_ignore_empty(
                ' ',
                (description, java_method)
            )
            signature = self.join_ignore_empty(
                delimiter,
                (java_exception_class, description_java_method_phrase)
            )

        if len(signature) > self.max_len:
            signature = delimiter.join(
                (java_exception_class, java_method)
            )
            signature_notes.append(
                'JavaSignatureTool: dropped Java exception '
                'description due to length'
            )

        return signature, signature_notes


#==============================================================================
class SignatureGenerationRule(Rule):
    required_config = Namespace()
    required_config.namespace('c_signature')
    required_config.c_signature.add_option(
        'c_signature_tool_class',
        doc='the class that can generate a C signature',
        default='socorro.processor.signature_utilities.CSignatureTool',
        from_string_converter=class_converter,
        reference_value_from='resource.signature'
    )
    required_config.c_signature.add_option(
        'maximum_frames_to_consider',
        doc='the maximum number of frames to consider',
        default=40,
        reference_value_from='resource.signature'
    )
    required_config.namespace('java_signature')
    required_config.java_signature.add_option(
        'java_signature_tool_class',
        doc='the class that can generate a Java signature',
        default='socorro.processor.signature_utilities.JavaSignatureTool',
        from_string_converter=class_converter,
        reference_value_from='resource.signature'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(SignatureGenerationRule, self).__init__(config)
        self.java_signature_tool = (
            self.config.java_signature.java_signature_tool_class(
                config.java_signature
            )
        )
        self.c_signature_tool = self.config.c_signature.c_signature_tool_class(
            config.c_signature
        )

    #--------------------------------------------------------------------------
    def _create_frame_list(
        self,
        crashing_thread_mapping,
        make_modules_lower_case=False
    ):
        frame_signatures_list = []
        for a_frame in islice(
            crashing_thread_mapping.get('frames', {}),
            self.config.c_signature.maximum_frames_to_consider
        ):
            if make_modules_lower_case and 'module' in a_frame:
                a_frame['module'] = a_frame['module'].lower()

            normalized_signature = self.c_signature_tool.normalize_signature(
                **a_frame
            )
            if 'normalized' not in a_frame:
                a_frame['normalized'] = normalized_signature
            frame_signatures_list.append(normalized_signature)
        return frame_signatures_list

    #--------------------------------------------------------------------------
    def _get_crashing_thread(self, processed_crash):
        return processed_crash.json_dump['crash_info']['crashing_thread']

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        if 'JavaStackTrace' in raw_crash and raw_crash.JavaStackTrace:
            # generate a Java signature
            signature, signature_notes = self.java_signature_tool.generate(
                raw_crash.JavaStackTrace,
                delimiter=': '
            )
            processed_crash.signature = signature
            if signature_notes:
                processor_meta.processor_notes.extend(signature_notes)
            return True

        try:
            crashed_thread = self._get_crashing_thread(processed_crash)
        except KeyError:
            crashed_thread = None
        try:
            if processed_crash.get('hang_type', None) == 1:
                # force the signature to come from thread 0
                signature_list = self._create_frame_list(
                    processed_crash.json_dump["threads"][0],
                    processed_crash.json_dump['system_info']['os'] in
                    "Windows NT"
                )
            elif crashed_thread is not None:
                signature_list = self._create_frame_list(
                    processed_crash.json_dump["threads"][crashed_thread],
                    processed_crash.json_dump['system_info']['os'] in
                    "Windows NT"
                )
            else:
                signature_list = []
        except Exception, x:
            processor_meta.processor_notes.append(
                'No crashing frames found because of %s' % x
            )
            signature_list = []

        signature, signature_notes = self.c_signature_tool.generate(
            signature_list,
            processed_crash.get('hang_type', ''),
            crashed_thread,
        )
        processed_crash.proto_signature = ' | '.join(signature_list)
        processed_crash.signature = signature
        if signature_notes:
            processor_meta.processor_notes.extend(signature_notes)
        return True


#==============================================================================
class OOMSignature(Rule):
    """To satisfy Bug 1007530, this rule will modify the signature to
    tag OOM (out of memory) crashes"""

    signature_fragments = (
        'NS_ABORT_OOM',
        'mozalloc_handle_oom',
        'CrashAtUnhandlableOOM'
    )

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        if 'OOMAllocationSize' in raw_crash:
            return True
        signature = processed_crash.signature
        for a_signature_fragment in self.signature_fragments:
            if a_signature_fragment in signature:
                return True
        return False

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.original_signature = processed_crash.signature
        try:
            size = int(raw_crash.OOMAllocationSize)
        except (TypeError, AttributeError, KeyError):
            processed_crash.signature = (
                "OOM | unknown | " + processed_crash.signature
            )
            return True

        if size <= 262144:  # 256K
            processed_crash.signature = "OOM | small"
        else:
            processed_crash.signature = (
                "OOM | large | " + processed_crash.signature
            )
        return True


#==============================================================================
class SigTrunc(Rule):
    """ensure that the signature is never longer than 255 characters"""

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return len(processed_crash.signature) > 255

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.signature = "%s..." % processed_crash.signature[:252]
        return True


#==============================================================================
class StackwalkerErrorSignatureRule(Rule):
    """ensure that the signature contains the stackwalker error message"""

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return processed_crash.signature.startswith('EMPTY')

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.signature = "%s; %s" % (
            processed_crash.signature,
            processed_crash.mdsw_status_string
        )
        return True


#==============================================================================
class SignatureRunWatchDog(SignatureGenerationRule):
    """ensure that the signature contains the stackwalker error message"""

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return '::RunWatchdog' in processed_crash['signature']

    #--------------------------------------------------------------------------
    def _get_crashing_thread(self, processed_crash):
        return 0

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        result = super(SignatureRunWatchDog, self)._action(
            raw_crash,
            raw_dumps,
            processed_crash,
            processor_meta
        )
        processed_crash['signature'] = (
            "shutdownhang | %s" % processed_crash['signature']
        )
        return result
