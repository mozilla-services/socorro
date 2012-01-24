import re


#==============================================================================
class SignatureTool (object):
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
class CSignatureTool (SignatureTool):
    hang_prefixes = {-1: "hang",
                      1: "chromehang"
                    }

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(CSignatureTool, self).__init__(config)
        self.irrelevantSignatureRegEx = \
             re.compile(self.config.irrelevantSignatureRegEx)
        self.prefixSignatureRegEx =  \
            re.compile(self.config.prefixSignatureRegEx)
        self.signaturesWithLineNumbersRegEx = \
            re.compile(self.config.signaturesWithLineNumbersRegEx)
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
            if self.signaturesWithLineNumbersRegEx.match(function):
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
        for a_sentinel in self.config.signatureSentinels:
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
            if self.irrelevantSignatureRegEx.match(aSignature):
                continue
            newSignatureList.append(aSignature)
            if not self.prefixSignatureRegEx.match(aSignature):
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
class JavaSignatureTool (SignatureTool):
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
            source_list = source.split('\n')
            source_list = [x.strip() for x in source_list]
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
