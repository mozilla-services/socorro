import collections

#-----------------------------------------------------------------------------------------------------------------
def hexifyCharacter(character):
  if ord(character) < 128:
    return character
  return '\\x%x' % ord(character)

#-----------------------------------------------------------------------------------------------------------------
def sanitizeForJson(something):
  if type(something) in [int, float, unicode]:
    return something
  if type(something) == str:
    try:
      return something.decode('ascii')
    except UnicodeDecodeError:
      return ''.join((hexifyCharacter(x) for x in something))
  if isinstance(something, collections.Mapping):
    return dict((k, sanitizeForJson(v)) for k, v in something.iteritems())
  if isinstance(something, collections.Iterable):
    return [sanitizeForJson(x) for x in something]
  return str(something)