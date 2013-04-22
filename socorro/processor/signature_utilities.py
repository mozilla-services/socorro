# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re

from configman import Namespace, RequiredConfig


#==============================================================================
class SignatureTool(RequiredConfig):
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.max_len = config.setdefault('signature_max_len', 255)
        self.escape_single_quote = \
            config.setdefault('signature_escape_single_quote', True)

    #--------------------------------------------------------------------------
    def generate(self,
                 source_list,
                 hang_type=0,
                 crashed_thread=None,
                 delimiter=' | '):
        signature, signature_notes = self._do_generate(source_list,
                                                       hang_type,
                                                       crashed_thread,
                                                       delimiter)
        if len(signature) > self.max_len:
            signature = "%s..." % signature[:self.max_len - 3]
            signature_notes.append('SignatureTool: signature truncated due to '
                                   'length')
        if self.escape_single_quote:
            signature = signature.replace("'", "''")
        return signature, signature_notes


#==============================================================================
class CSignatureTool(SignatureTool):
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
                  '(wchar_t const*, wchar_t const*, wchar_t const*, unsigned '
                  'int, unsigned int)'
              ]""",
      from_string_converter=eval
    )
    required_config.add_option(
      'irrelevant_signature_re',
      doc='a regular expression matching frame signatures that should be '
          'ignored when generating an overall signature',
      default="""'|'.join([
          '@0x[0-9a-fA-F]{2,}',
          '@0x[1-9a-fA-F]',
          'ashmem',
          'app_process@0x.*',
          'core\.odex@0x.*',
          '_CxxThrowException',
          'dalvik-heap',
          'dalvik-jit-code-cache',
          'dalvik-LinearAlloc',
          'dalvik-mark-stack',
          'data@app@org\.mozilla\.fennec-\d\.apk@classes\.dex@0x.*',
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
          'mnt@asec@org\.mozilla\.fennec-\d@pkg\.apk@classes\.dex@0x.*',
          'MOZ_Assert',
          'MOZ_Crash',
          'mozcrt19.dll@0x.*',
          'mozilla::ipc::RPCChannel::Call\(IPC::Message\*, IPC::Message\*\)',
          '_NSRaiseError',
          '(Nt|Zw)WaitForSingleObject(Ex)?',
          '(Nt|Zw)WaitForMultipleObjects(Ex)?',
          'nvmap@0x.*',
          'org\.mozilla\.fennec-\d\.apk@0x.*',
          'RaiseException',
          'RtlpAdjustHeapLookasideDepth',
          'system@framework@*\.jar@classes\.dex@0x.*',
          '___TERMINATING_DUE_TO_UNCAUGHT_EXCEPTION___',
          'WaitForSingleObjectExImplementation',
          'WaitForMultipleObjectsExImplementation',
          'RealMsgWaitFor.*'
          '_ZdlPv',
          'zero',
          ])""",
      from_string_converter=eval
    )
    required_config.add_option(
      'prefix_signature_re',
      doc='a regular expression matching frame signatures that should always '
          'be coupled with the following frame signature when generating an '
          'overall signature',
      default="""'|'.join([
          '@0x0',
          'Abort',
          '.*abort',
          '_alloca_probe.*',
          '__android_log_assert',
          'arena_.*',
          'BaseGetNamedObjectDirectory',
          '.*calloc',
          'cert_.*',
          'CERT_.*',
          'CFRelease',
          '_chkstk',
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
          'GCGraphBuilder::NoteXPCOMChild',
          'getanswer',
          'huge_dalloc',
          'ialloc',
          'init_library',
          'isalloc',
          'je_malloc',
          'jemalloc_crash',
          'je_realloc',
          'JNI_CreateJavaVM',
          '_JNIEnv.*',
          'JNI_GetCreatedJavaVM.*',
          'JS_DHashTableEnumerate',
          'JS_DHashTableOperate',
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
          'mozilla::ipc::RPCChannel::Call',
          'mozilla::ipc::RPCChannel::CxxStackFrame::CxxStackFrame',
          'mozilla::ipc::RPCChannel::EnteredCxxStack',
          'mozilla::ipc::RPCChannel::Send',
          'moz_xmalloc',
          'moz_xrealloc',
          'NP_Shutdown',
          'nsCOMPtr.*',
          'NS_DebugBreak.*',
          '[-+]\[NSException raise(:format:(arguments:)?)?\]',
          'nsObjCExceptionLogAbort(\(.*?\)){0,1}',
          'nsRefPtr.*',
          'NSS.*',
          'nss.*',
          'nsTArray<.*',
          'nsTArray_base<.*',
          'NtUser.*',
          'objc_exception_throw',
          'objc_msgSend',
          'operator new\([^,\)]+\)',
          'PL_.*',
          'port_.*',
          'PORT_.*',
          '_PR_.*',
          'PR_.*',
          'pthread_mutex_lock',
          '_purecall',
          'raise',
          'realloc',
          'recv',
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
        ])""",
      from_string_converter=eval
    )
    required_config.add_option(
      'signatures_with_line_numbers_re',
      doc='any signatures that match this list should be combined with their '
          'associated source code line numbers',
      default='js_Interpret'
    )

    hang_prefixes = {-1: "hang",
                      1: "chromehang"
                    }

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(CSignatureTool, self).__init__(config)
        self.irrelevant_signature_re = \
             re.compile(self.config.irrelevant_signature_re)
        self.prefix_signature_re =  \
            re.compile(self.config.prefix_signature_re)
        self.signatures_with_line_numbers_re = \
            re.compile(self.config.signatures_with_line_numbers_re)
        self.fixupSpace = re.compile(r' (?=[\*&,])')
        self.fixupComma = re.compile(r',(?! )')
        self.fixupInteger = re.compile(r'(<|, )(\d+)([uUlL]?)([^\w])')

    #--------------------------------------------------------------------------
    def normalize_signature(self, module_name, function, source, source_line,
                            instruction):
        """ returns a structured conglomeration of the input parameters to
        serve as a signature
        """
        #if function is not None:
        if function:
            if self.signatures_with_line_numbers_re.match(function):
                function = "%s:%s" % (function, source_line)
            # Remove spaces before all stars, ampersands, and commas
            function = self.fixupSpace.sub('', function)
            # Ensure a space after commas
            function = self.fixupComma.sub(', ', function)
            # normalize template signatures with manifest const integers to
            #'int': Bug 481445
            function = self.fixupInteger.sub(r'\1int\4', function)
            return function
        #if source is not None and source_line is not None:
        if source and source_line:
            filename = source.rstrip('/\\')
            if '\\' in filename:
                source = filename.rsplit('\\')[-1]
            else:
                source = filename.rsplit('/')[-1]
            return '%s#%s' % (source, source_line)
        if not module_name:
            module_name = ''  # might have been None
        return '%s@%s' % (module_name, instruction)

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
        for a_sentinel in self.config.signature_sentinels:
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
        newSignatureList = []
        for aSignature in source_list:
            if self.irrelevant_signature_re.match(aSignature):
                continue
            newSignatureList.append(aSignature)
            if not self.prefix_signature_re.match(aSignature):
                break
        if hang_type:
            newSignatureList.insert(0, self.hang_prefixes[hang_type])
        signature = delimiter.join(newSignatureList)

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
class JavaSignatureTool(SignatureTool):
    java_line_number_killer = re.compile(r'\.java\:\d+\)$')
    java_hex_addr_killer = re.compile(r'@[0-9a-f]{8}\s')

    #--------------------------------------------------------------------------
    @staticmethod
    def join_ignore_empty(delimiter, list_of_strings):
        return delimiter.join(x for x in list_of_strings if x)

    #--------------------------------------------------------------------------
    def _do_generate(self,
                     source,
                     hang_type_unused=0,
                     crashed_thread_unused=None,
                     delimiter=' '):
        signature_notes = []
        try:
            source_list = [x.strip() for x in source.splitlines()]
        except AttributeError:
            signature_notes.append('JavaSignatureTool: stack trace not '
                                   'in expected format')
            return ("EMPTY: Java stack trace not in expected format",
                    signature_notes)
        try:
            java_exception_class, description = source_list[0].split(':')
            java_exception_class = java_exception_class.strip() + ':'
            description = description.strip()
        except ValueError:
            java_exception_class = source_list[0] + ':'
            description = ''
            signature_notes.append('JavaSignatureTool: stack trace line 1 is '
                                   'not in the expected format')
        try:
            java_method = re.sub(self.java_line_number_killer,
                                 '.java)',
                                 source_list[1])
            if not java_method:
                signature_notes.append('JavaSignatureTool: stack trace line 2 '
                                       'is empty')
        except IndexError:
            signature_notes.append('JavaSignatureTool: stack trace line 2 is '
                                   'missing')
            java_method = ''

        signature = self.join_ignore_empty(delimiter,
                                           (java_exception_class,
                                            description,
                                            java_method))

        # relace all hex addresses by the string <addr>
        signature = self.java_hex_addr_killer.sub(r'@<addr>: ', signature)

        if len(signature) > self.max_len:
            signature = delimiter.join((java_exception_class,
                                             java_method))
            # must reapply the address masking
            signature = self.java_hex_addr_killer.sub(r'@<addr>: ',
                                                      signature)
            signature_notes.append('JavaSignatureTool: dropped Java exception '
                                   'description due to length')

        return signature, signature_notes
