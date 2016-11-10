# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This module creates the classfications.support part of the processed crash. All
the support classifcation rules live here.

{...
    'classifications': {
        'support': {
            'classification': 'some classification',
            'classification_data': 'extra information saved by rule',
            'classification_version': '0.0',
        }
    }

...
}
"""

from configman import Namespace
from configman.converters import to_str

from socorro.lib.ver_tools import normalize
from socorro.lib.util import DotDict
from socorro.lib.transform_rules import Rule

from sys import maxint


#==============================================================================
class SupportClassificationRule(Rule):
    """the base class for Support Rules.  It provides the framework for the
    rules 'predicate', 'action', and 'version' as well as utilites to help
    rules do their jobs."""

    #--------------------------------------------------------------------------
    def predicate(self, *args, **kwargs):
        """the default predicate for Support Classifiers invokes any derivied
        _predicate function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity act.  An error during the predicate application is a
        failure of the rule, not a failure of the classification system itself
        """
        try:
            return self._predicate(*args, **kwargs)
        except Exception, x:
            if not self.config:
                if 'processor' in kwargs:
                    self.config = kwargs['processor'].config
                else:
                    raise
            self.config.logger.debug(
                'Rule %s predicicate failed because of "%s"',
                to_str(self.__class__),
                x,
                exc_info=True
            )
            return False

    #--------------------------------------------------------------------------
    def action(self, *args, **kwargs):
        """the default action for Support Classifiers invokes any derivied
        _action function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity act and perhaps (mitigate the error).  An error during the
        action application is a failure of the rule, not a failure of the
        classification system itself."""
        try:
            return self._action(*args, **kwargs)
        except KeyError, x:
            if not self.config:
                if 'processor' in kwargs:
                    self.config = kwargs['processor'].config
                else:
                    raise
            self.config.logger.debug(
                'Rule %s action failed because of missing key "%s"',
                to_str(self.__class__),
                x,
            )
        except Exception, x:
            if not self.config and 'processor' in kwargs:
                self.config = kwargs['processor'].config
            if not self.config:
                raise
            self.config.logger.debug(
                'Rule %s action failed because of "%s"',
                to_str(self.__class__),
                x,
                exc_info=True
            )
        return False

    #--------------------------------------------------------------------------
    def _add_classification(
        self,
        processed_crash,
        classification,
        classification_data,
        logger=None
    ):
        """This method adds a 'support' classification to a processed
        crash.

        parameters:
            processed_crash - a reference to the processed crash to which the
                              classification is to be added.
            classification - a string that is the classification.
            classification_data - a string of extra data that goes along with a
                                  classification
        """
        if 'classifications' not in processed_crash:
            processed_crash['classifications'] = DotDict()
        processed_crash['classifications']['support'] = DotDict({
            'classification': classification,
            'classification_data': classification_data,
            'classification_version': self.version()
        })
        if logger:
            logger.debug(
                'Support classification: %s',
                classification
            )
        return True


#==============================================================================
class BitguardClassifier(SupportClassificationRule):
    """To satisfy Bug 931907, this rule will detect 'bitguard.dll' in the
    modules list.  If present, it will add the classification,
    classifications.support.classification.bitguard to the processed crash"""
    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor):
        for a_module in processed_crash['json_dump']['modules']:
            if a_module['filename'] == 'bitguard.dll':
                self._add_classification(
                    processed_crash,
                    'bitguard',
                    None,
                    processor.config.logger
                )
                return True
        # bitguard was never found, this rule fails
        return False


#==============================================================================
class OutOfDateClassifier(SupportClassificationRule):
    """To satisfy Bug 956879, this rule will detect classify crashes as out
    of date if the version is less than the threshold
    'firefox_out_of_date_version' found in the processor configuration"""

    required_config = Namespace()
    required_config.add_option(
        'firefox_out_of_date_version',
        doc='the version of Firefox that is considered to be old enough '
            'to warrant a warning to the user',
        default='17',
    )

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, processor):
        try:
            return (
                raw_crash.ProductName == 'Firefox'
                and normalize(raw_crash.Version) < self.out_of_date_threshold
            )
        except AttributeError:
            try:
                self.out_of_date_threshold = normalize(
                    self.config.firefox_out_of_date_version
                )
            except (AttributeError, KeyError):
                self.out_of_date_threshold = normalize(
                    processor.config.firefox_out_of_date_version
                )
            return self._predicate(
                raw_crash,
                raw_dumps,
                processed_crash,
                processor
            )

    #--------------------------------------------------------------------------
    @staticmethod
    def _normalize_windows_version(version_str):
        ver_list = version_str.split('.')[:2]

        def as_int(x):
            try:
                return int(x)
            except ValueError:
                return maxint
        # get the first integer out of the last last token
        ver_list[-1] = ver_list[-1].split(' ')[0]
        ver_list_normalized = [as_int(x) for x in ver_list]
        if "Service" in version_str:
            try:
                # assume last space delimited field is service pack number
                ver_list_normalized.append(int(version_str.split(' ')[-1]))
            except ValueError:  # appears to have been a bad assumption
                ver_list_normalized.append(0)
        return tuple(ver_list_normalized)

    #--------------------------------------------------------------------------
    def _windows_action(
        self,
        raw_crash,
        raw_dumps,
        processed_crash,
        processor
    ):
        win_version_normalized = self._normalize_windows_version(
            processed_crash["json_dump"]["system_info"]["os_ver"]
        )
        if win_version_normalized[:2] == (5, 0):  # Win2K
            return self._add_classification(
                processed_crash,
                'firefox-no-longer-works-windows-2000',
                None,
                processor.config.logger
            )
        elif win_version_normalized < (5, 1, 3):  # WinXP SP2
            return self._add_classification(
                processed_crash,
                'firefox-no-longer-works-some-versions-windows-xp',
                None,
                processor.config.logger
            )
        return self._add_classification(
            processed_crash,
            'update-firefox-latest-version',
            None,
            processor.config.logger
        )

    #--------------------------------------------------------------------------
    @staticmethod
    def _normalize_osx_version(version_str):
        ver_list = version_str.split('.')[:2]

        def as_int(x):
            try:
                return int(x)
            except ValueError:
                return maxint
        return tuple(as_int(x) for x in ver_list)

    #--------------------------------------------------------------------------
    def _osx_action(self, raw_crash, raw_dumps, processed_crash, processor):
        osx_version_normalized = self._normalize_osx_version(
            processed_crash["json_dump"]["system_info"]["os_ver"]
        )
        if (
            osx_version_normalized <= (10, 4) or
            processed_crash["json_dump"]["system_info"]["cpu_arch"] == 'ppc'
        ):
            return self._add_classification(
                processed_crash,
                'firefox-no-longer-works-mac-os-10-4-or-powerpc',
                None,
                processor.config.logger
            )
        elif osx_version_normalized == (10, 5):
            return self._add_classification(
                processed_crash,
                'firefox-no-longer-works-mac-os-x-10-5',
                None,
                processor.config.logger
            )
        return self._add_classification(
            processed_crash,
            'update-firefox-latest-version',
            None,
            processor.config.logger
        )

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor):
        crashed_version = normalize(raw_crash.Version)
        if "Win" in processed_crash["json_dump"]["system_info"]['os']:
            return self._windows_action(
                raw_crash,
                raw_dumps,
                processed_crash,
                processor
            )
        elif processed_crash["json_dump"]["system_info"]['os'] == "Mac OS X":
            return self._osx_action(
                raw_crash,
                raw_dumps,
                processed_crash,
                processor
            )
        else:
            return self._add_classification(
                processed_crash,
                'update-firefox-latest-version',
                None,
                processor.config.logger
            )

#------------------------------------------------------------------------------
# the following tuple of tuples is a structure for loading rules into the
# TransformRules system. The tuples take the form:
#   predicate_function, predicate_args, predicate_kwargs,
#   action_function, action_args, action_kwargs.
#
# The args and kwargs components are additional information that a predicate
# or an action might need to have to do its job.  Providing values for args
# or kwargs essentially acts in a manner similar to functools.partial.
# When the predicate or action functions are invoked, these args and kwags
# values will be passed into the function along with the raw_crash,
# processed_crash and processor objects.
default_support_classifier_rules = (
    (BitguardClassifier, (), {}, BitguardClassifier, (), {}),
    (OutOfDateClassifier, (), {}, OutOfDateClassifier, (), {}),
)
