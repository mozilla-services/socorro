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
      default='|'.join([
        '@0x[0-9a-fA-F]{2,}',
        '@0x[1-9a-fA-F]',
        'RaiseException',
        '_CxxThrowException',
        'mozilla::ipc::RPCChannel::Call\(IPC::Message\*, IPC::Message\*\)',
        'KiFastSystemCallRet',
        '(Nt|Zw)WaitForSingleObject(Ex)?',
        '(Nt|Zw)WaitForMultipleObjects(Ex)?',
        'WaitForSingleObjectExImplementation',
        'WaitForMultipleObjectsExImplementation',
        '___TERMINATING_DUE_TO_UNCAUGHT_EXCEPTION___',
        '_NSRaiseError',
        'mozcrt19.dll@0x.*',
        'linux-gate\.so@0x.*',
        'libdvm\.so\s*@\s*0x.*',
        'dalvik-LinearAlloc\s*@0x.*',
        'dalvik-heap',
        'data@app@org\.mozilla\.fennec-1\.apk@classes\.dex@0x.*',
        'libc\.so@.*',
        'libEGL\.so@.*',
        'libc-2\.5\.so@.*',
        'RtlpAdjustHeapLookasideDepth',
        'google_breakpad::ExceptionHandler::HandleInvalidParameter.*',
        'libicudata.so@.*',
        '_ZdlPv',
      ])
    )
    required_config.add_option(
      'prefix_signature_re',
      doc='a regular expression matching frame signatures that should always '
          'be coupled with the following frame signature when generating an '
          'overall signature',
      default='|'.join([
        '@0x0',
        'strchr',
        'strstr',
        'strlen',
        'PL_strlen',
        'strcmp',
        'strcpy',
        'strncpy',
        '.*strdup',
        'wcslen',
        'memcpy',
        'memmove',
        'memcmp',
        'memset',
        '.*calloc',
        'malloc',
        'realloc',
        '.*free',
        'arena_dalloc_small',
        'arena_alloc',
        'arena_dalloc',
        'nsObjCExceptionLogAbort(\(.*?\)){0,1}',
        'libobjc.A.dylib@0x1568.',
        'objc_msgSend',
        '_purecall',
        'PL_DHashTableOperate',
        'EtwEventEnabled',
        'RtlpFreeHandleForAtom',
        'RtlpDeCommitFreeBlock',
        'RtlpAllocateAffinityIndex',
        'RtlAddAccessAllowedAce',
        'RtlQueryPerformanceFrequency',
        'RtlpWaitOnCriticalSection',
        'RtlpWaitForCriticalSection',
        '_PR_MD_ATOMIC_(INC|DEC)REMENT',
        'nsCOMPtr.*',
        'nsRefPtr.*',
        'operator new\([^,\)]+\)',
        'CFRelease',
        'objc_exception_throw',
        '[-+]\[NSException raise(:format:(arguments:)?)?\]',
        'mozalloc_handle_oom',
        'nsTArray_base<.*',
        'nsTArray<.*',
        'WaitForSingleObject(Ex)?',
        'WaitForMultipleObjects(Ex)?',
        'NtUserWaitMessage',
        'NtUserMessageCall',
        'mozalloc_abort.*',
        'NS_DebugBreak_P.*',
        'PR_AtomicIncrement',
        'PR_AtomicDecrement',
        'moz_xmalloc',
        '__libc_android_abort',
        'mozilla::ipc::RPCChannel::EnteredCxxStack',
        'mozilla::ipc::RPCChannel::CxxStackFrame::CxxStackFrame',
        'mozilla::ipc::RPCChannel::Send',
        'mozilla::ipc::RPCChannel::Call',
        'RtlDeleteCriticalSection',
        'PR_DestroyLock',
        '.*abort',
        '_ZdaPvRKSt9nothrow_t\"',
        '__swrite',
        'dvmAbort',
        'JNI_CreateJavaVM',
        'dvmStringLen',
        '(libxul\.so|xul\.dll|XUL)@0x.*',
        '_VEC_memzero',
        'arena_malloc_small',
        'arena_ralloc',
        'arena_run_reg_alloc',
        'arena_run_tree_insert',
        'ialloc',
        'isalloc',
        'moz_xrealloc',
        'arena_malloc',
        'arena_run_reg_dalloc',
        'arena_run_dalloc',
        'je_malloc',
        'je_realloc',
        '_JNIEnv::CallObjectMethod',
        'kill',
        'raise',
        'sigprocmask',
        'sigblock',
        'setjmp',
        'fastcopy_I',
        '_RTC_Terminate',
        'CrashInJS',
        'fastzero_I',
        'VEC_memcpy',
        '_chkstk',
        '_alloca_probe.*',
      ])
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

        if len(signature) > self.max_len:
            signature = delimiter.join((java_exception_class,
                                             java_method))
            signature_notes.append('JavaSignatureTool: dropped Java exception '
                                   'description due to length')

        return signature, signature_notes
