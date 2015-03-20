# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
from configman.option import Option 


#==============================================================================
class UnknownParameterError(TypeError):
   pass


#==============================================================================
class BadParameterError(ValueError):
   pass


#==============================================================================
class MissingParameterError(ValueError):
   pass


#==============================================================================
class Parameter(Option):
   def __init__(self, *args, **kwargs):
      self.required = kwargs.pop('required', False)
      super(Parameter, self).__init__(*args, **kwargs)


#==============================================================================
class MethodParameterValidator(DotDict):
   
    #--------------------------------------------------------------------------
   @staticmethod
   def get_method_validator(a_class, a_method_name):
      try:
         return getattr(a_class, 'parameter_validator_for' + a_method_name)
      except AttributeError:
         return None
      
    #--------------------------------------------------------------------------
   def add_parameter(self, name, *args, **kwargs):
      parameter = Parameter(*args, **kwargs)
      self[name] = parameter
      
    #--------------------------------------------------------------------------
   def validate(self, **kwargs):
      validated = {}
      for arg, value in kwargs.iteritems():
         if arg not in self:
            raise UnknownParameterError(arg)
         parameter = self[arg]
         try:
            validated[arg] = parameter.from_string_converter(value)
         except (TypeError, ValueError) as x:
            raise BadParameterError(x)
      for name in set(self.keys()) - set(kwargs):
         if self[name].required:
            raise MissingParameterError(name)
         else:
            validated[name] = self[name].default
      return validated
   
   
#class MethodWhiteLister()