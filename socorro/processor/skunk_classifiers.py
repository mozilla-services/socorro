# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This package is a Socorro implementation of bsmedberg's skunk processor
crash classification system.  This package is intended for use in Socorro
Processor2012.  It is implemented on top of the Processor TransformRule
System.  It is intended that this package demonstrate the implementation
technique for all future enhancements to Processor2012 and well as how
the entirety of the future BixieProcessor2013 and SocorroProcessor2014
implementations.

The intent is to provide a framework for which ad hoc classification rules
can be added to the processor easily.  The rules, that all follow the same
programatic form, are executed one at a time, in order, until one of the rules
reports that it succeeds.  At that point, execution of classificiation rules
stops.

Classification rules are applied after all other processing of a crash is
complete.  Classification rules are given access to both the raw_crash and the
processed_crash.  In this version, the classification rule has complete read
and write access to all fields with in both versions two versions of the crash.
Rules should probably refrain from making modifications and instead use the
base class API for adding a classification to the processed_cash.

All rules have two major components: a predicate and an action.

The predicate: this method is used to initially determine if the rule should
be applied.

The action: if the predicate succeeds, the 'action' function is executed.  If
this method succeeds, it uses the '_add_classification' method from the base
class to tag the crash with new data and return True.  If this method fails or
otherwise decides that its action should not apply, it just quits returning
False.  The act of returning False tells the underlying TransformRule system to
continue trying to apply rules.

Successful application of an action results in the following structure to be
added to the processed crash:

{...
    'classifications': {
        'skunk_works': {
            'classification': 'some classification',
            'classification_data': 'extra information saved by rule',
            'classificaiton_version': '0.0',
        }
    }

...}
"""

import datetime

from socorro.lib.util import DotDict


#==============================================================================
class SkunkClassificationRule(object):
    """the base class for Skunk Rules.  It provides the framework for the rules
    'predicate', 'action', and 'version' as well as utilites to help rules do
    their jobs."""

    #--------------------------------------------------------------------------
    def predicate(self, raw_crash,  processed_crash, processor):
        """the default predicate for Skunk Classifiers invokes any derivied
        _predicate function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity act.  An error during the predicate application is a
        failure of the rule, not a failure of the classification system itself
        """
        try:
            return self._predicate(raw_crash,  processed_crash, processor)
        except Exception, x:
            processor.config.logger.debug(
                'skunk_classifier: %s predicate rejection - consideration of '
                '%s failed because of "%s"',
                self.__class__,
                raw_crash.get('uuid', 'unknown uuid'),
                x,
                exc_info=True
            )
            return False

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash,  processed_crash, processor):
        """"The default predicate is too look into the processed crash to see
        if the 'skunk_works' classification has already been applied.
        parameters:
            raw_crash - a mapping representing the raw crash data originally
                        submitted by the client
            processed_crash - the ultimate result of the processor, this is the
                              analized version of a crash.  It contains the
                              output of the MDSW program for each of the dumps
                              within the crash.
            processor - a reference to the processor object that is assigned
                        to working on the current crash. This object contains
                        resources that might be useful to a classifier rule.
                        'processor.config' is the configuration for the
                        processor in which database connection paramaters can
                        be found.  'processor.config.logger' is useful for any logging
                        of debug information. 'processor.c_signature_tool' or
                        'processor.java_signature_tool' contain utilities that
                        might be useful during classification.

        returns:
            True - this rule should be applied
            False - this rule should not be applied
        """
        try:
            if 'classification' in processed_crash.classifications.skunk_works:
                return False
            return True
        except KeyError:
            return True

    #--------------------------------------------------------------------------
    def action(self, raw_crash,  processed_crash, processor):
        """the default action for Skunk Classifiers invokes any derivied
        _action function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity act and perhaps (mitigate the error).  An error during the
        action application is a failure of the rule, not a failure of the
        classification system itself."""
        try:
            return self._action(raw_crash,  processed_crash, processor)
        except Exception, x:
            processor.config.logger.debug(
                'skunk_classifier: %s action failure - %s failed because of '
                '"%s"',
                self.__class__,
                raw_crash.get('uuid', 'unknown uuid'),
                x,
                exc_info=True
            )
            return False

    #--------------------------------------------------------------------------
    def _action(self, raw_crash,  processed_crash, processor):
        """Rules derived from this base class ought to override this method
        with an actual classification rule.  Successful application of this
        method should include a call to '_add_classification'.

        parameters:
            raw_crash - a mapping representing the raw crash data originally
                        submitted by the client
            processed_crash - the ultimate result of the processor, this is the
                              analized version of a crash.  It contains the
                              output of the MDSW program for each of the dumps
                              within the crash.
            processor - a reference to the processor object that is assigned
                        to working on the current crash. This object contains
                        resources that might be useful to a classifier rule.
                        'processor.config' is the configuration for the
                        processor in which database connection paramaters can
                        be found.  'processor.config.logger' is useful for any logging
                        of debug information. 'processor.c_signature_tool' or
                        'processor.java_signature_tool' contain utilities that
                        might be useful during classification.

        returns:
            True - this rule was applied successfully and no further rules
                   should be applied
            False - this rule did not succeed and further rules should be
                    tried
        """
        return True

    #--------------------------------------------------------------------------
    def version(self):
        """This method should be overridden in a base class."""
        return '0.0'

    #--------------------------------------------------------------------------
    def _add_classification(
        self,
        processed_crash,
        classification,
        classification_data,
        logger=None
    ):
        """This method adds a 'skunk_works' classification to a processed
        crash.

        parameters:
            processed_crash - a reference to the processed crash to which the
                              classification is to be added.
            classification - a string that is the classification.
            classification_data - a string of extra data that goes along with a
                                  classification
        """
        if 'classifications' not in processed_crash:
            processed_crash.classifications = DotDict()
        processed_crash.classifications['skunk_works'] = DotDict({
            'classification': classification,
            'classification_data': classification_data,
            'classification_version': self.version()
        })
        if logger and "not classified" not in classification:
            logger.debug(
                'skunk classification: %s',
                classification
            )

    #--------------------------------------------------------------------------
    @staticmethod
    def _get_stack(processed_crash, dump_name='upload_file_minidump_plugin'):
        """This utility method offers derived classes a way to fetch the stack
        for the thread that caused the crash

        parameters:
            processed_crash - this is the mapping that contains the MDSW output
            dump_name - each dump within a crash has a name.

        returns:
            False - if something goes wrong in trying to get the stack
            a list of frames from the crashing thread of the specified dump in
            this form:
                [
                    {
                        'module': '...',
                        'function': '...',
                        'file': '...',
                        'line': '...',
                        'offset': '...',
                        'module_offset': '...',
                        'funtion_offset': '...',
                    }, ...
                ]

        """
        try:
            if (dump_name == 'upload_file_minidump_plugin'
                and processed_crash['process_type'] == 'plugin'
            ):
                a_json_dump = processed_crash['json_dump']
            else:
                a_json_dump = processed_crash[dump_name]['json_dump']
        except KeyError:
            # no plugin or plugin json dump
            return False
        try:
            stack = a_json_dump['crashing_thread']['frames']
        # these exceptions are kept as separate cases just to help keep track
        # of what situations they cover
        except KeyError, x:
            # no threads or no crash_info or no crashing_thread
            return False
        except IndexError:
            # no stack for crashing_thread
            return False
        except ValueError:
            # crashing_thread is not an integer
            return False
        return stack

    #--------------------------------------------------------------------------
    @staticmethod
    def _stack_contains(
        stack,
        signature,
        a_signature_tool,
        cache_normalizations=True
    ):
        """this utility will return a boolean indicitating if a string
        appears at the beginning of any of the nomalized frame signatures
        within a stack.

        parameters:
            stack - the stack to examine
            signature - the string to search for
            a_signature_tool - a reference to an object having a
                               'normalize_signature' method.  This is applied
                               to each frame of the stack prior to testing
            cache_normalizations - sometimes many rules will need to do the
                                   same normalizations over and over.  This
                                   method will save the normalized form of a
                                   stack frame within the processed_crash's
                                   copy of the processed stack.  This cache
                                   will persist and get saved to processed
                                   crash storage.
        """
        for a_frame in stack:
            try:
                normalized_frame = a_frame['normalized']
            except KeyError:
                normalized_frame = a_signature_tool.normalize_signature(
                    **a_frame
                )
                if cache_normalizations:
                    a_frame['normalized'] = normalized_frame
            if normalized_frame.startswith(signature):
                return True
        return False

#==============================================================================
class DontConsiderTheseFilter(SkunkClassificationRule):
    """This classifier is meant to match every crash that is of no interest.
    Once identified by the predicate, these uninteresting crashes are passed
    on to the action.  The action does nothing but declare the classification
    process as being done.  This derails any further consideration of matching
    crashes"""
    first19 = datetime.date(2012, 10, 17)
    first18 = datetime.date(2012, 10, 23)

    #--------------------------------------------------------------------------
    def predicate(self, raw_crash,  processed_crash, processor):
        """this method overrides the base class predicate.  The base class
        assumes that an exception raised during the predicate is a failure of
        the predicate.  In this case, the logic is the opposite, an exception
        means the success of the predicate.

        This class is to find all crashes that are not Firefox Plugin crashes
        of with certian qualities.  If an error happens during the
        determination, then we consider the crash in question to be
        not of the proper type.  So the predicate returns true, forcing the
        rule system to take the action (which does nothing) and stops the rule
        application process.
        """
        try:
            return self._predicate(raw_crash,  processed_crash, processor)
        except Exception, x:
            processor.config.logger.debug(
                'skunk_classifier: %s predicate rejection - consideration of '
                '%s failed because of "%s"',
                self.__class__,
                raw_crash.get('uuid', 'unknown uuid'),
                x,
                exc_info=True
            )
            return False

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash,  processed_crash, processor):
        """this predicate matches all crashes that are NOT Firefox Plugin
        crashes of a certain vintage.  This prediciate was adapted from
        bsmedberg's skunk processor.

        Predicates normally return True for accepting and False for rejecting.
        Somewhat counter intuitively, in this predicate, we return True when we
        ultimately want to reject the crash in question.  Think of it this way,
        the predicate is saying "yes, we want to reject this crash".  By saying
        'yes', the crash gets passed to the action where the ulimate rejection
        actually happens."""

        plugin_hang = raw_crash.get('PluginHang', '0')
        if plugin_hang == '0':
            return True

        product_name = raw_crash.get('ProductName', None)
        if product_name != 'Firefox':
            processor.config.logger.debug(
                'skunk_classifier: reject - Product "%s" is not Firefox',
                product_name
            )
            return True

        version = raw_crash.get('Version', None)
        if version is None:
            processor.config.logger.debug(
                'skunk_classifier: reject - Version missing'
            )
            return True

        try:
            majorversion = int(version.split('.')[0])
        except ValueError:
            processor.config.logger.debug(
                'skunk_classifier: reject - bad Version string "%s"',
                version
            )
            return True

        buildid = raw_crash.get('BuildID', None)
        if buildid is None:
            processor.config.logger.debug(
                'skunk_classifier: reject - BuiltID missing'
            )
            return True

        try:
            builddate = datetime.date(
                int(buildid[0:4]),
                int(buildid[4:6]),
                int(buildid[6:8])
            )
        except ValueError:
            processor.config.logger.debug(
                'skunk_classifier: reject - bad BuildID "%s"',
                buildid
            )
            return True

        if majorversion < 17:
            processor.config.logger.debug(
                'skunk_classifier: reject - not accepting Version '
                '"%s"',
                majorversion
            )
            return True
        elif majorversion == 18:
            if builddate < self.first18:
                processor.config.logger.debug(
                    'skunk_classifier: reject - not accepting Version'
                    ' "%s" with old BuildID',
                    majorversion
                )
                return True
        elif builddate < self.first19:
            processor.config.logger.debug(
                'skunk_classifier: reject - not accepting old BuildID '
                '"%s"',
                buildid
            )
            return True

        # bsmedberg's code stores dumps differently than Socorro does.  In
        # Socorro, a 'plugin' crash has the 'plugin' dump as the primary
        # dump named 'dump' rather than stored with the name 'plugin'
        if 'dump' not in processed_crash:
            processor.config.logger.debug(
                'skunk_classifier: reject - plugin dump missing',
            )
            return True

        try:
            if processed_crash.json_dump['system_info']['cpu_arch'] == 'amd64':
                processor.config.logger.debug(
                    'skunk_classifier: reject - not accepting amd64 '
                    'architecture',
                )
                return True
        except (KeyError, AttributeError), x:
            processor.config.logger.debug(
                'skunk_classifier: reject - no architecture info found',
                exc_info=True
            )
            return True

        if not processed_crash.get('success', False):
            return True

        for a_dump_name in processed_crash.additional_minidumps:
            # in the original code, this section made sure that all
            # dumps had identified 'crashing threads'.  Socorro doesn't
            # work that way.  Ulitimately, this section asks the question,
            # "were all dump successful in processing by MDSW?"
            try:
                if not processed_crash[a_dump_name].success:
                    processor.config.logger.debug(
                        'skunk_classifier: reject - all dumps must have '
                        'processed correctly: %s has MDSW errors',
                        a_dump_name
                    )
                    return True
            except (KeyError, AttributeError):
                processor.config.logger.debug(
                    'skunk_classifier: reject - all dumps must have '
                    'processed correctly: %s is missing components',
                    a_dump_name
                )
                return True

        # by getting this far, this crash is interesting.  declare that this
        # rule does not apply by returning False.  This means that the
        # classification process will continue by applying further rules.
        return False


    #--------------------------------------------------------------------------
    def version(self):
        return '0.1'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash,  processed_crash, processor):
        """the predicate has determined that the crash is uninteresting to
        the SkunkClassifiers.  Don't do anything but return true to stop any
        further application of rules."""
        return True


#==============================================================================
class UpdateWindowAttributes(SkunkClassificationRule):
    """"""
    #--------------------------------------------------------------------------
    def version(self):
        return '0.1'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash,  processed_crash, processor):
        stack = self._get_stack(processed_crash, 'upload_file_minidump_plugin')
        if stack is False:
            return False

        # normalize the stack of the crashing thread
        # then look for these 3 target frames
        target_signatures = [
            "F_1152915508___________________________________",
            "mozilla::plugins::PluginInstanceChild::UpdateWindowAttributes"
                "(bool)",
            "mozilla::ipc::RPCChannel::Call(IPC::Message*, IPC::Message*)"
        ]

        current_target_signature = target_signatures.pop(0)
        for i, a_frame in enumerate(stack):
            normalized_signature = \
                processor.c_signature_tool.normalize_signature(**a_frame)
            if (current_target_signature in normalized_signature):
                current_target_signature = target_signatures.pop(0)
                if not target_signatures:
                    break
        if target_signatures:
            return False

        try:
            classification_data = \
                processor.c_signature_tool.normalize_signature(**stack[i + 1])
        except IndexError:
            classification_data = None

        self._add_classification(
            processed_crash,
            'adbe-3355131',
            classification_data,
            processor.config.logger
        )

        return True


#==============================================================================
class SetWindowPos(SkunkClassificationRule):
    #--------------------------------------------------------------------------
    def version(self):
        return '0.1'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash,  processed_crash, processor):
        found = self._do_set_window_pos_classification(
            processed_crash,
            processor.c_signature_tool,
            'upload_file_minidump_plugin',
            ('F_320940052', 'F_1378698112', 'F_468782153'),
            processor
        )
        if not found:
            found = self._do_set_window_pos_classification(
                processed_crash,
                processor.c_signature_tool,
                'upload_file_minidump_flash2',
                ('F455544145',),
                processor
            )
        return found

    #--------------------------------------------------------------------------
    def _do_set_window_pos_classification(
        self,
        processed_crash,
        signature_normalization_tool,
        dump_name,
        secondary_sentinels,
        processor
    ):

        stack = self._get_stack(processed_crash, dump_name)
        if stack is False:
            return False
        truncated_stack = self._get_stack(processed_crash, dump_name)[:5]
        stack_contains_sentinel = self._stack_contains(
            truncated_stack,
            'NtUserSetWindowPos',
            signature_normalization_tool,
        )
        if stack_contains_sentinel:
            for a_second_sentinel in secondary_sentinels:
                stack_contains_secondary = self._stack_contains(
                    truncated_stack,
                    a_second_sentinel,
                    signature_normalization_tool,
                )
                if stack_contains_secondary:
                        self._add_classification(
                            processed_crash,
                            'NtUserSetWindowPos | %s' % a_second_sentinel,
                            None,
                            processor.config.logger
                        )
                        return True
            self._add_classification(
                processed_crash,
                'NtUserSetWindowPos | other',
                None,
                processor.config.logger
            )
            return True
        return False


#==============================================================================
class SendWaitReceivePort(SkunkClassificationRule):
    #--------------------------------------------------------------------------
    def version(self):
        return '0.1'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash,  processed_crash, processor):

        stack = self._get_stack(processed_crash, 'upload_file_minidump_flash2')
        if stack is False:
            return False

        if self._stack_contains(
            stack[:5],
            'NtAlpcSendWaitReceivePort',
            processor.c_signature_tool,
        ):
            self._add_classification(
                processed_crash,
                'NtAlpcSendWaitReceivePort',
                None,
                processor.config.logger
            )

            return True
        return False


#==============================================================================
class Bug811804(SkunkClassificationRule):
    #--------------------------------------------------------------------------
    def version(self):
        return '0.1'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash,  processed_crash, processor):

        try:
            signature = processed_crash.upload_file_minidump_flash2.signature
        except KeyError:
            return False

        if (signature == 'hang | NtUserWaitMessage | F34033164'
                         '________________________________'):
            self._add_classification(
                processed_crash,
                'bug811804-NtUserWaitMessage',
                None,
                processor.config.logger
            )
            return True
        return False


#==============================================================================
class Bug812318(SkunkClassificationRule):
    #--------------------------------------------------------------------------
    def version(self):
        return '0.1'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash,  processed_crash, processor):
        stack = self._get_stack(processed_crash, 'upload_file_minidump_flash2')
        if stack is False:
            return False

        primary_found = self._stack_contains(
            stack[:5],
            'NtUserPeekMessage',
            processor.c_signature_tool,
        )
        if not primary_found:
            return False

        secondary_found = self._stack_contains(
            stack[:5],
            'F849276792______________________________',
            processor.c_signature_tool,
        )
        if secondary_found:
            classification = 'bug812318-PeekMessage'
        else:
            classification = 'NtUserPeekMessage-other'
        self._add_classification(
            processed_crash,
            classification,
            None,
            processor.config.logger
        )
        return True


#==============================================================================
class NullClassification(SkunkClassificationRule):
    #--------------------------------------------------------------------------
    def version(self):
        return '0.1'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash,  processed_crash, processor):
        self._add_classification(
            processed_crash,
            'not classified',
            None,
            processor.config.logger
        )
        return True



default_classifier_rules = (
    (DontConsiderTheseFilter, (), {}, DontConsiderTheseFilter, (), {}),
    (UpdateWindowAttributes, (), {}, UpdateWindowAttributes, (), {}),
    (SetWindowPos, (), {}, SetWindowPos, (), {}),
    (SendWaitReceivePort, (), {}, SendWaitReceivePort, (), {}),
    (Bug811804, (), {}, Bug811804, (), {}),
    (Bug812318, (), {}, Bug812318, (), {}),
    (NullClassification, (), {}, NullClassification, (), {}),
)
