# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import configman
import collections
import inspect

from configman import RequiredConfig, Namespace
from configman.dotdict import DotDict
from configman.converters import to_str

from socorrolib.lib.converters import (
    str_to_classes_in_namespaces_converter,
)

#------------------------------------------------------------------------------
# support methods

# a regular expression that will parse out all pairs in the form:
#   a=b, c=d, e=f
kw_list_re = re.compile('([^ =]+) *= *("[^"]*"|[^ ]*)')


#------------------------------------------------------------------------------
def kw_str_parse(a_string):
    """convert a string in the form 'a=b, c=d, e=f' to a dict"""
    try:
        return dict((k, eval(v.rstrip(',')))
                    for k, v in kw_list_re.findall(a_string))
    except (AttributeError, TypeError):
        if isinstance(a_string, collections.Mapping):
            return a_string
        return {}


#==============================================================================
class Rule(RequiredConfig):
    """the base class for Support Rules.  It provides the framework for the
    rules 'predicate', 'action', and 'version' as well as utilites to help
    rules do their jobs."""
    required_config = Namespace()
    required_config.add_option(
        'chatty',
        doc='should this rule announce what it is doing?',
        default=False,
    )


    #--------------------------------------------------------------------------
    def __init__(self, config=None, quit_check_callback=None):
        self.config = config
        self.quit_check_callback = quit_check_callback

    #--------------------------------------------------------------------------
    def predicate(self, *args, **kwargs):
        """the default predicate for Support Classifiers invokes any derivied
        _predicate function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity to act.  An error during the predicate application is a
        failure of the rule, not a failure of the classification system itself
        """
        try:
            return self._predicate(*args, **kwargs)
        except Exception, x:
            self.config.logger.debug(
                'Rule %s predicicate failed because of "%s"',
                to_str(self.__class__),
                x,
                exc_info=True
            )
            return False

    #--------------------------------------------------------------------------
    def _predicate(self, *args, **kwargs):
        """"The default support classifier predicate just returns True.  We
        want all the support classifiers run.

        returns:
            True - this rule should be applied
            False - this rule should not be applied
        """
        return True

    #--------------------------------------------------------------------------
    def action(self, *args, **kwargs):
        """the default action for Support Classifiers invokes any derivied
        _action function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity to act and perhaps mitigate the error.  An error during the
        action application is a failure of the rule, not a failure of the
        classification system itself."""
        try:
            return self._action(*args, **kwargs)
        except KeyError, x:
            self.config.logger.debug(
                'Rule %s action failed because of missing key "%s"',
                to_str(self.__class__),
                x,
            )
        except Exception, x:
            self.config.logger.debug(
                'Rule %s action failed because of "%s"',
                to_str(self.__class__),
                x,
                exc_info=True
            )
        return False

    #--------------------------------------------------------------------------
    def _action(self, *args, **kwargs):
        """Rules derived from this base class ought to override this method
        with an actual classification rule.  Successful application of this
        method should include a call to '_add_classification'.

        returns:
            True - this rule was applied successfully and no further rules
                   should be applied
            False - this rule did not succeed and further rules should be
                    tried
        """
        return True

    #--------------------------------------------------------------------------
    def version(self):
        """This method should be overridden in a derived class."""
        return '0.0'

    #--------------------------------------------------------------------------
    def act(self, *args, **kwargs):
        """gather a rules parameters together and run the predicate. If that
        returns True, then go on and run the action function

        returns:
            a tuple indicating the results of applying the predicate and the
            action function:
               (False, None) - the predicate failed, action function not run
               (True, True) - the predicate and action functions succeeded
               (True, False) - the predicate succeeded, but the action function
                               failed"""
        if self.predicate(*args, **kwargs):
            bool_result = self.action(*args, **kwargs)
            return (True, bool_result)
        else:
            return (False, None)


#==============================================================================
class TransformRule(Rule):
    """a pairing of two functions with default parameters to be used as
    transformation rule."""
    #--------------------------------------------------------------------------
    def __init__(self, predicate,
                       predicate_args,
                       predicate_kwargs,
                       action,
                       action_args,
                       action_kwargs,
                       config=None):
        """construct a new predicate/action rule pair.
        input parameters:
            pedicate - the name of a function to serve as a predicate.  The
                       function must accept two dicts followed by any number
                       of constant args or kwargs.  Alternatively, this could
                       be a classname for a class that has a method called
                       'predicate' with the aforementioned charactistics
            predicate_args - arguments to be passed on to the predicate
                             function in addition to the two required dicts.
            predicate_kwargs - kwargs to be passed on to the predicate
                               function in addition to the two required dicts.
            action - the name of a function to be run if the predicate returns
                     True.  The method must accept two dicts followed by
                     any number of args or kwargs.    Alternatively, this could
                     be a classname for a class that has a method called
                     'predicate' with the aforementioned charactistics
            action_args - arguments to be passed on to the action function
                          in addition to the two required dicts
            action_kwargs - kwargs to be passed on to the action function in
                            addition to the two required dicts
        """
        try:
            self.predicate = configman.converters.class_converter(predicate)
        except TypeError:
            # conversion failed, let's assume it was already function or a
            # callable object
            self.predicate = predicate
        if inspect.isclass(self.predicate):
            # the predicate is a class, instantiate it and set the predicate
            # function to the object's 'predicate' method
            self._predicate_implementation = self.predicate(config)
            self.predicate = self._predicate_implementation.predicate
        else:
            self._predicate_implementation = type(self.predicate)

        try:
            if predicate_args in ('', None):
                self.predicate_args = ()
            elif isinstance(predicate_args, tuple):
                self.predicate_args = predicate_args
            else:
                self.predicate_args = tuple(
                    [eval(x.strip()) for x in predicate_args.split(',')]
                )
        except AttributeError:
            self.predicate_args = ()

        self.predicate_kwargs = kw_str_parse(predicate_kwargs)
        try:
            self.action = configman.class_converter(action)
        except TypeError:
            # the conversion failed, let's assume that the action was passed in
            # as something callable.
            self.action = action
        if inspect.isclass(self.action):
            # the action is actually a class, go on and instantiate it, then
            # assign the 'action' to be the object's 'action' method
            if self._predicate_implementation.__class__ is self.action:
                # if the predicate and the action are implemented in the same
                # class, only instantiate one copy.
                self._action_implementation = self._predicate_implementation
            else:
                self._action_implementation = self.action(config)
            self.action = self._action_implementation.action

        try:
            if action_args in ('', None):
                self.action_args = ()
            elif isinstance(action_args, tuple):
                self.action_args = action_args
            else:
                self.action_args = tuple(
                    [eval(x.strip()) for x in action_args.split(',')]
                )
        except AttributeError:
            self.action_args = ()
        self.action_kwargs = kw_str_parse(action_kwargs)

    #--------------------------------------------------------------------------
    @staticmethod
    def function_invocation_proxy(fn, proxy_args, proxy_kwargs):
        """execute the fuction if it is one, else evaluate the fn as a boolean
        and return that value.

        Sometimes rather than providing a predicate, we just give the value of
        True.  This is shorthand for writing a predicate that always returns
        true."""
        try:
            return fn(*proxy_args, **proxy_kwargs)
        except TypeError:
            return bool(fn)

    #--------------------------------------------------------------------------
    def act(self, *args, **kwargs):
        """gather a rules parameters together and run the predicate. If that
        returns True, then go on and run the action function

        returns:
            a tuple indicating the results of applying the predicate and the
            action function:
               (False, None) - the predicate failed, action function not run
               (True, True) - the predicate and action functions succeeded
               (True, False) - the predicate succeeded, but the action function
                               failed"""
        pred_args = tuple(args) + tuple(self.predicate_args)
        pred_kwargs = kwargs.copy()
        pred_kwargs.update(self.predicate_kwargs)
        if self.function_invocation_proxy(self.predicate,
                                          pred_args,
                                          pred_kwargs):
            act_args = tuple(args) + tuple(self.action_args)
            act_kwargs = kwargs.copy()
            act_kwargs.update(self.action_kwargs)
            bool_result = self.function_invocation_proxy(self.action, act_args,
                                                         act_kwargs)
            return (True, bool_result)
        else:
            return (False, None)

    #--------------------------------------------------------------------------
    def __eq__(self, another):
        if isinstance(another, TransformRule):
            return self.__dict__ == another.__dict__
        else:
            return False

    #--------------------------------------------------------------------------
    def close(self):
        self.config.logger.debug('null close on rule %s', self.__class__)
        pass

#==============================================================================
class TransformRuleSystem(RequiredConfig):
    """A collection of TransformRules that can be applied together"""
    required_config = Namespace()
    required_config.add_option(
        name='rules_list',
        default=[],
        from_string_converter=str_to_classes_in_namespaces_converter()
    )
    required_config.add_option(
        'chatty_rules',
        doc='should the rules announce what they are doing?',
        default=False,
    )

    #--------------------------------------------------------------------------
    def __init__(self, config=None, quit_check=None):
        if quit_check:
            self._quit_check = quit_check
        else:
            self._quit_check = self._null_quit_check
        self.rules = []
        if not config:
            config = DotDict()
        if 'chatty_rules' not in config:
            config.chatty_rules = False
        self.config = config
        if "rules_list" in config:
            self.tag = config.tag
            self.act = getattr(self, config.action)
            list_of_rules = config.rules_list.class_list

            for a_rule_class_name, a_rule_class, ns_name in list_of_rules:
                try:
                    self.rules.append(
                        a_rule_class(config[ns_name])
                    )
                except KeyError, x:
                    self.rules.append(
                        a_rule_class(config)
                    )

    #--------------------------------------------------------------------------
    def _null_quit_check(self):
        "a no-op method to do nothing if no quit check method has been defined"
        pass

    #--------------------------------------------------------------------------
    def load_rules(self, an_iterable):
        """cycle through a collection of Transform rule tuples loading them
        into the TransformRuleSystem"""
        self.rules = [
            TransformRule(*x, config=self.config) for x in an_iterable
        ]

    #--------------------------------------------------------------------------
    def append_rules(self, an_iterable):
        """add rules to the TransformRuleSystem"""
        self.rules.extend(
            TransformRule(*x, config=self.config) for x in an_iterable
        )

    #--------------------------------------------------------------------------
    def apply_all_rules(self, *args, **kwargs):
        """cycle through all rules and apply them all without regard to
        success or failure

        returns:
             True - since success or failure is ignored"""
        for x in self.rules:
            self._quit_check()
            if self.config.chatty_rules:
                self.config.logger.debug(
                    'apply_all_rules: %s',
                    to_str(x.__class__)
                )
            predicate_result, action_result = x.act(*args, **kwargs)
            if self.config.chatty_rules:
                self.config.logger.debug(
                    '               : pred - %s; act - %s',
                    predicate_result,
                    action_result
                )
        return True

    #--------------------------------------------------------------------------
    def apply_until_action_succeeds(self, *args, **kwargs):
        """cycle through all rules until an action is run and succeeds

        returns:
           True - if an action is run and succeeds
           False - if no action succeeds"""
        for x in self.rules:
            self._quit_check()
            if self.config.chatty_rules:
                self.config.logger.debug(
                    'apply_until_action_succeeds: %s',
                    to_str(x.__class__)
                )
            predicate_result, action_result = x.act(*args, **kwargs)
            if self.config.chatty_rules:
                self.config.logger.debug(
                    '                           : pred - %s; act - %s',
                    predicate_result,
                    action_result
                )
            if action_result:
                return True
        return False

    #--------------------------------------------------------------------------
    def apply_until_action_fails(self, *args, **kwargs):
        """cycle through all rules until an action is run and fails

        returns:
            True - an action ran and it failed
            False - no action ever failed"""
        for x in self.rules:
            self._quit_check()
            if self.config.chatty_rules:
                self.config.logger.debug(
                    'apply_until_action_fails: %s',
                    to_str(x.__class__)
                )
            predicate_result, action_result = x.act(*args, **kwargs)
            if self.config.chatty_rules:
                self.config.logger.debug(
                    '                        : pred - %s; act - %s',
                    predicate_result,
                    action_result
                )
            if not action_result:
                return True
        return False

    #--------------------------------------------------------------------------
    def apply_until_predicate_succeeds(self, *args, **kwargs):
        """cycle through all rules until a predicate returns True

        returns:
            True - an action ran and it succeeded
            False - an action ran and it failed
            None - no predicate ever succeeded"""
        for x in self.rules:
            self._quit_check()
            if self.config.chatty_rules:
                self.config.logger.debug(
                    'apply_until_predicate_succeeds: %s',
                    to_str(x.__class__)
                )
            predicate_result, action_result = x.act(*args, **kwargs)
            if self.config.chatty_rules:
                self.config.logger.debug(
                    '                              : pred - %s; act - %s',
                    predicate_result,
                    action_result
                )
            if predicate_result:
                return action_result
        return None

    #--------------------------------------------------------------------------
    def apply_until_predicate_fails(self, *args, **kwargs):
        """cycle through all rules until a predicate returns False

        returns:
            False - a predicate ran and it failed
            None - no predicate ever failed"""
        for x in self.rules:
            self._quit_check()
            if self.config.chatty_rules:
                self.config.logger.debug(
                    'apply_until_predicate_fails: %s',
                    to_str(x.__class__)
                )
            predicate_result, action_result = x.act(*args, **kwargs)
            if self.config.chatty_rules:
                self.config.logger.debug(
                    '                           : pred - %s; act - %s',
                    predicate_result,
                    action_result
                )
            if not predicate_result:
                return False
        return None

    #--------------------------------------------------------------------------
    def close(self):
        for a_rule in self.rules:
            try:
                self.config.logger.debug('trying to close %s', to_str(a_rule.__class__))
                close_method = a_rule.close
            except AttributeError:
                self.config.logger.debug('%s has no close',  to_str(a_rule.__class__))
                # no close method mean no need to close
                continue
            close_method()


#------------------------------------------------------------------------------
# Useful rule predicates and actions
#------------------------------------------------------------------------------
# (True, '', '', copy_key_value, '', 'source_key=sally, destination_key=fred')
def copy_value_action(source, destination,
                      source_key=None, destination_key=None):
    """copy a key from a mapping source to a mapping destination"""
    destination[destination_key] = source[source_key]


#------------------------------------------------------------------------------
# (True, '', '',
#  format_new_value, '', 'destination_key='Version', format_str=%(Version)sesr'
#  )
def format_new_value_action(source, destination, destination_key='',
                            format_str=''):
    """replace a mapping destination with a string formatted from the
    mapping source.

    parameters:
        source - a mapping to use as a source
        destination - a mapping to use as the destination
        destination_key - the key in the destination to insert/replace
        format - a string in standard python format form"""
    destination[destination_key] = format_str % source


# (eq_constant_predicate, '', 'source_key="fred", value="wilma"', ...)
#------------------------------------------------------------------------------
def eq_constant_predicate(source, destination, source_key='', value=''):
    """a predicate to test equality between a source key and a constant

    parameters:
        source - the source of the value to test
        destination - not used
        source_key - the key into the source to use for the test
        value - the constant to check for equality"""
    return source[source_key] == value


# (eq_key_predicate, '', 'left_mapping_key="fred", right_mapping_key="wilma"',
# ...)
#------------------------------------------------------------------------------
def eq_key_predicate(
    left_mapping,
    right_mapping,
    left_mapping_key='',
    right_mapping_key=''
):
    """a predicate to test equality between a left mapping key and a
   right mapping key

    parameters:
        left_mapping - the mapping containing the first value to test
        right_mapping - the mapping containing the second value
        left_mapping_key - the key into the source for the first value
        right_mapping_key - the key into the second data source"""
    return left_mapping[left_mapping_key] == right_mapping[right_mapping_key]


# (is_not_null_predicate, '', 'key="fred",
# ...)
#------------------------------------------------------------------------------
def is_not_null_predicate(
    raw_crash, dumps, processed_crash, processor, key=''
):
    """a predicate that converts the key'd source to boolean.

    parameters:
        raw_crash - dict
        dumps - placeholder in a fat interface - unused
        processed_crash - placeholder in a fat interface - unused
        processor - placeholder in a fat interface - unused
    """
    try:
        return bool(raw_crash[key])
    except KeyError:
        return False
