"""
schema.py - support for subSchemaSubEntry information

See http://www.python-ldap.org/ for details.

\$Id: models.py,v 1.45 2012/03/07 19:07:15 stroeder Exp $
"""

import UserDict,ldap.cidict

from ldap.schema.tokenizer import split_tokens,extract_tokens

if __debug__:
  from types import TupleType,StringType,IntType
  try:
    from types import BooleanType
  except ImportError:
    BooleanType = IntType


NOT_HUMAN_READABLE_LDAP_SYNTAXES = {
  '1.3.6.1.4.1.1466.115.121.1.4':None,  # Audio
  '1.3.6.1.4.1.1466.115.121.1.5':None,  # Binary
  '1.3.6.1.4.1.1466.115.121.1.8':None,  # Certificate
  '1.3.6.1.4.1.1466.115.121.1.9':None,  # Certificate List
  '1.3.6.1.4.1.1466.115.121.1.10':None, # Certificate Pair
  '1.3.6.1.4.1.1466.115.121.1.23':None, # G3 FAX
  '1.3.6.1.4.1.1466.115.121.1.28':None, # JPEG
  '1.3.6.1.4.1.1466.115.121.1.40':None, # Octet String
  '1.3.6.1.4.1.1466.115.121.1.49':None, # Supported Algorithm
}


class SchemaElement:
  """
  Base class for all schema element classes. Not used directly!

  Arguments:
  
  schema_element_str
    String which contains the schema element description to be parsed.

  Class attributes:

  schema_attribute
    LDAP attribute type containing a certain schema element description
  token_defaults
    Dictionary internally used by the schema element parser
    containing the defaults for certain schema description key-words
  """
  token_defaults = {
    'DESC':(None,),
  }
  
  def __init__(self,schema_element_str=None):
    if schema_element_str:
      l = split_tokens(schema_element_str,self.token_defaults)
      self.set_id(l[1])
      d = extract_tokens(l,self.token_defaults)
      self._set_attrs(l,d)

  def _set_attrs(self,l,d):
    self.desc = d['DESC'][0]
    return

  def set_id(self,element_id):
    self.oid = element_id

  def get_id(self):
    return self.oid

  def key_attr(self,key,value,quoted=0):
    assert value is None or type(value)==StringType,TypeError("value has to be of StringType, was %s" % repr(value))
    if value:
      if quoted:        
        return " %s '%s'" % (key,value.replace("'","\\'"))
      else:
        return " %s %s" % (key,value)
    else:
      return ""

  def key_list(self,key,values,sep=' ',quoted=0):
    assert type(values)==TupleType,TypeError("values has to be of ListType")
    if not values:
      return ''
    if quoted:
      quoted_values = [ "'%s'" % value.replace("'","\\'") for value in values ]
    else:
      quoted_values = values
    if len(values)==1:
      return ' %s %s' % (key,quoted_values[0])
    else:
      return ' %s ( %s )' % (key,sep.join(quoted_values))

  def __str__(self):
    result = [str(self.oid)]
    result.append(self.key_attr('DESC',self.desc,quoted=1))
    return '( %s )' % ''.join(result)


class ObjectClass(SchemaElement):
  """
  Arguments:
  
  schema_element_str
    String containing an ObjectClassDescription

  Class attributes:

  oid
    OID assigned to the object class
  names
    This list of strings contains all NAMEs of the object class
  desc
    This string contains description text (DESC) of the object class
  obsolete
    Integer flag (0 or 1) indicating whether the object class is marked
    as OBSOLETE in the schema
  must
    This list of strings contains NAMEs or OIDs of all attributes
    an entry of the object class must have
  may
    This list of strings contains NAMEs or OIDs of additional attributes
    an entry of the object class may have
  kind
    Kind of an object class:
    0 = ABSTRACT,
    1 = STRUCTURAL,
    2 = AUXILIARY
  sup
    This list of strings contains NAMEs or OIDs of object classes
    this object class is derived from
  """
  schema_attribute = 'objectClasses'
  token_defaults = {
    'NAME':(()),
    'DESC':(None,),
    'OBSOLETE':None,
    'SUP':(()),
    'STRUCTURAL':None,
    'AUXILIARY':None,
    'ABSTRACT':None,
    'MUST':(()),
    'MAY':()
  }

  def _set_attrs(self,l,d):
    self.obsolete = d['OBSOLETE']!=None
    self.names = d['NAME']
    self.desc = d['DESC'][0]
    self.must = d['MUST']
    self.may = d['MAY']
    # Default is STRUCTURAL, see RFC2552 or draft-ietf-ldapbis-syntaxes
    self.kind = 0
    if d['ABSTRACT']!=None:
      self.kind = 1
    elif d['AUXILIARY']!=None:
      self.kind = 2
    if self.kind==0 and not d['SUP'] and self.oid!='2.5.6.0':
      # STRUCTURAL object classes are sub-classes of 'top' by default
      self.sup = ('top',)
    else:
      self.sup = d['SUP']
    assert type(self.names)==TupleType
    assert self.desc is None or type(self.desc)==StringType
    assert type(self.obsolete)==BooleanType and (self.obsolete==0 or self.obsolete==1)
    assert type(self.sup)==TupleType
    assert type(self.kind)==IntType
    assert type(self.must)==TupleType
    assert type(self.may)==TupleType
    return

  def __str__(self):
    result = [str(self.oid)]
    result.append(self.key_list('NAME',self.names,quoted=1))
    result.append(self.key_attr('DESC',self.desc,quoted=1))
    result.append(self.key_list('SUP',self.sup,sep=' $ '))
    result.append({0:'',1:' OBSOLETE'}[self.obsolete])
    result.append({0:' STRUCTURAL',1:' ABSTRACT',2:' AUXILIARY'}[self.kind])
    result.append(self.key_list('MUST',self.must,sep=' $ '))
    result.append(self.key_list('MAY',self.may,sep=' $ '))
    return '( %s )' % ''.join(result)


AttributeUsage = ldap.cidict.cidict({
  'userApplication':0, # work-around for non-compliant schema
  'userApplications':0,
  'directoryOperation':1,
  'distributedOperation':2,
  'dSAOperation':3,
})


class AttributeType(SchemaElement):
  """
  Arguments:
  
  schema_element_str
    String containing an AttributeTypeDescription

  Class attributes:

  oid
    OID assigned to the attribute type
  names
    This list of strings contains all NAMEs of the attribute type
  desc
    This string contains description text (DESC) of the attribute type
  obsolete
    Integer flag (0 or 1) indicating whether the attribute type is marked
    as OBSOLETE in the schema
  single_value
    Integer flag (0 or 1) indicating whether the attribute must
    have only one value
  syntax
    String contains OID of the LDAP syntax assigned to the attribute type
  no_user_mod
    Integer flag (0 or 1) indicating whether the attribute is modifiable
    by a client application
  equality
    String contains NAME or OID of the matching rule used for
    checking whether attribute values are equal
  substr
    String contains NAME or OID of the matching rule used for
    checking whether an attribute value contains another value
  ordering
    String contains NAME or OID of the matching rule used for
    checking whether attribute values are lesser-equal than
  usage
    USAGE of an attribute type:
    0 = userApplications
    1 = directoryOperation,
    2 = distributedOperation,
    3 = dSAOperation
  sup
    This list of strings contains NAMEs or OIDs of attribute types
    this attribute type is derived from
  """
  schema_attribute = 'attributeTypes'
  token_defaults = {
    'NAME':(()),
    'DESC':(None,),
    'OBSOLETE':None,
    'SUP':(()),
    'EQUALITY':(None,),
    'ORDERING':(None,),
    'SUBSTR':(None,),
    'SYNTAX':(None,),
    'SINGLE-VALUE':None,
    'COLLECTIVE':None,
    'NO-USER-MODIFICATION':None,
    'USAGE':('userApplications',)
  }

  def _set_attrs(self,l,d):
    self.names = d['NAME']
    self.desc = d['DESC'][0]
    self.obsolete = d['OBSOLETE']!=None
    self.sup = d['SUP']
    self.equality = d['EQUALITY'][0]
    self.ordering = d['ORDERING'][0]
    self.substr = d['SUBSTR'][0]
    try:
      syntax = d['SYNTAX'][0]
    except IndexError:
      self.syntax = None
      self.syntax_len = None
    else:
      if syntax is None:
        self.syntax = None
        self.syntax_len = None
      else:
        try:
          self.syntax,syntax_len = d['SYNTAX'][0].split("{")
        except ValueError:
          self.syntax = d['SYNTAX'][0]
          self.syntax_len = None
          for i in l:
            if i.startswith("{") and i.endswith("}"):
              self.syntax_len=long(i[1:-1])
        else:
          self.syntax_len = long(syntax_len[:-1])
    self.single_value = d['SINGLE-VALUE']!=None
    self.collective = d['COLLECTIVE']!=None
    self.no_user_mod = d['NO-USER-MODIFICATION']!=None
    self.usage = AttributeUsage.get(d['USAGE'][0],0)
    assert type(self.names)==TupleType
    assert self.desc is None or type(self.desc)==StringType
    assert type(self.sup)==TupleType,'attribute sup has type %s' % (type(self.sup))
    assert type(self.obsolete)==BooleanType and (self.obsolete==0 or self.obsolete==1)
    assert type(self.single_value)==BooleanType and (self.single_value==0 or self.single_value==1)
    assert type(self.no_user_mod)==BooleanType and (self.no_user_mod==0 or self.no_user_mod==1)
    assert self.syntax is None or type(self.syntax)==StringType
    assert self.syntax_len is None or type(self.syntax_len)==type(0L)
    return

  def __str__(self):
    result = [str(self.oid)]
    result.append(self.key_list('NAME',self.names,quoted=1))
    result.append(self.key_attr('DESC',self.desc,quoted=1))
    result.append(self.key_list('SUP',self.sup,sep=' $ '))
    result.append({0:'',1:' OBSOLETE'}[self.obsolete])
    result.append(self.key_attr('EQUALITY',self.equality))
    result.append(self.key_attr('ORDERING',self.ordering))
    result.append(self.key_attr('SUBSTR',self.substr))
    result.append(self.key_attr('SYNTAX',self.syntax))
    if self.syntax_len!=None:
      result.append(('{%d}' % (self.syntax_len))*(self.syntax_len>0))
    result.append({0:'',1:' SINGLE-VALUE'}[self.single_value])
    result.append({0:'',1:' COLLECTIVE'}[self.collective])
    result.append({0:'',1:' NO-USER-MODIFICATION'}[self.no_user_mod])
    result.append(
      {
        0:"",
        1:" USAGE directoryOperation",
        2:" USAGE distributedOperation",
        3:" USAGE dSAOperation",
      }[self.usage]
    )
    return '( %s )' % ''.join(result)


class LDAPSyntax(SchemaElement):
  """
  SyntaxDescription

  oid
    OID assigned to the LDAP syntax
  desc
    This string contains description text (DESC) of the LDAP syntax
  not_human_readable
    Integer flag (0 or 1) indicating whether the attribute type is marked
    as not human-readable (X-NOT-HUMAN-READABLE)  
  """
  schema_attribute = 'ldapSyntaxes'
  token_defaults = {
    'DESC':(None,),
    'X-NOT-HUMAN-READABLE':(None,),
  }

  def _set_attrs(self,l,d):
    self.desc = d['DESC'][0]
    self.not_human_readable = \
      NOT_HUMAN_READABLE_LDAP_SYNTAXES.has_key(self.oid) or \
      d['X-NOT-HUMAN-READABLE'][0]=='TRUE'
    assert self.desc is None or type(self.desc)==StringType
    return
                                  
  def __str__(self):
    result = [str(self.oid)]
    result.append(self.key_attr('DESC',self.desc,quoted=1))
    result.append(
      {0:'',1:" X-NOT-HUMAN-READABLE 'TRUE'"}[self.not_human_readable]
    )
    return '( %s )' % ''.join(result)


class MatchingRule(SchemaElement):
  """
  Arguments:
  
  schema_element_str
    String containing an MatchingRuleDescription

  Class attributes:

  oid
    OID assigned to the matching rule
  names
    This list of strings contains all NAMEs of the matching rule
  desc
    This string contains description text (DESC) of the matching rule
  obsolete
    Integer flag (0 or 1) indicating whether the matching rule is marked
    as OBSOLETE in the schema
  syntax
    String contains OID of the LDAP syntax this matching rule is usable with
  """
  schema_attribute = 'matchingRules'
  token_defaults = {
    'NAME':(()),
    'DESC':(None,),
    'OBSOLETE':None,
    'SYNTAX':(None,),
  }

  def _set_attrs(self,l,d):
    self.names = d['NAME']
    self.desc = d['DESC'][0]
    self.obsolete = d['OBSOLETE']!=None
    self.syntax = d['SYNTAX'][0]
    assert type(self.names)==TupleType
    assert self.desc is None or type(self.desc)==StringType
    assert type(self.obsolete)==BooleanType and (self.obsolete==0 or self.obsolete==1)
    assert self.syntax is None or type(self.syntax)==StringType
    return

  def __str__(self):
    result = [str(self.oid)]
    result.append(self.key_list('NAME',self.names,quoted=1))
    result.append(self.key_attr('DESC',self.desc,quoted=1))
    result.append({0:'',1:' OBSOLETE'}[self.obsolete])
    result.append(self.key_attr('SYNTAX',self.syntax))
    return '( %s )' % ''.join(result)


class MatchingRuleUse(SchemaElement):
  """
  Arguments:
  
  schema_element_str
    String containing an MatchingRuleUseDescription

  Class attributes:

  oid
    OID of the accompanying matching rule
  names
    This list of strings contains all NAMEs of the matching rule
  desc
    This string contains description text (DESC) of the matching rule
  obsolete
    Integer flag (0 or 1) indicating whether the matching rule is marked
    as OBSOLETE in the schema
  applies
    This list of strings contains NAMEs or OIDs of attribute types
    for which this matching rule is used
  """
  schema_attribute = 'matchingRuleUse'
  token_defaults = {
    'NAME':(()),
    'DESC':(None,),
    'OBSOLETE':None,
    'APPLIES':(()),
  }

  def _set_attrs(self,l,d):
    self.names = d['NAME']
    self.desc = d['DESC'][0]
    self.obsolete = d['OBSOLETE']!=None
    self.applies = d['APPLIES']
    assert type(self.names)==TupleType
    assert self.desc is None or type(self.desc)==StringType
    assert type(self.obsolete)==BooleanType and (self.obsolete==0 or self.obsolete==1)
    assert type(self.applies)==TupleType
    return

  def __str__(self):
    result = [str(self.oid)]
    result.append(self.key_list('NAME',self.names,quoted=1))
    result.append(self.key_attr('DESC',self.desc,quoted=1))
    result.append({0:'',1:' OBSOLETE'}[self.obsolete])
    result.append(self.key_list('APPLIES',self.applies,sep=' $ '))
    return '( %s )' % ''.join(result)


class DITContentRule(SchemaElement):
  """
  Arguments:
  
  schema_element_str
    String containing an DITContentRuleDescription

  Class attributes:

  oid
    OID of the accompanying structural object class
  names
    This list of strings contains all NAMEs of the DIT content rule
  desc
    This string contains description text (DESC) of the DIT content rule
  obsolete
    Integer flag (0 or 1) indicating whether the DIT content rule is marked
    as OBSOLETE in the schema
  aux
    This list of strings contains NAMEs or OIDs of all auxiliary
    object classes usable in an entry of the object class
  must
    This list of strings contains NAMEs or OIDs of all attributes
    an entry of the object class must have which may extend the
    list of required attributes of the object classes of an entry
  may
    This list of strings contains NAMEs or OIDs of additional attributes
    an entry of the object class may have which may extend the
    list of optional attributes of the object classes of an entry
  nots
    This list of strings contains NAMEs or OIDs of attributes which
    may not be present in an entry of the object class
  """
  schema_attribute = 'dITContentRules'
  token_defaults = {
    'NAME':(()),
    'DESC':(None,),
    'OBSOLETE':None,
    'AUX':(()),
    'MUST':(()),
    'MAY':(()),
    'NOT':(()),
  }

  def _set_attrs(self,l,d):
    self.names = d['NAME']
    self.desc = d['DESC'][0]
    self.obsolete = d['OBSOLETE']!=None
    self.aux = d['AUX']
    self.must = d['MUST']
    self.may = d['MAY']
    self.nots = d['NOT']
    assert type(self.names)==TupleType
    assert self.desc is None or type(self.desc)==StringType
    assert type(self.obsolete)==BooleanType and (self.obsolete==0 or self.obsolete==1)
    assert type(self.aux)==TupleType
    assert type(self.must)==TupleType
    assert type(self.may)==TupleType
    assert type(self.nots)==TupleType
    return

  def __str__(self):
    result = [str(self.oid)]
    result.append(self.key_list('NAME',self.names,quoted=1))
    result.append(self.key_attr('DESC',self.desc,quoted=1))
    result.append({0:'',1:' OBSOLETE'}[self.obsolete])
    result.append(self.key_list('AUX',self.aux,sep=' $ '))
    result.append(self.key_list('MUST',self.must,sep=' $ '))
    result.append(self.key_list('MAY',self.may,sep=' $ '))
    result.append(self.key_list('NOT',self.nots,sep=' $ '))
    return '( %s )' % ''.join(result)


class DITStructureRule(SchemaElement):
  """
  Arguments:
  
  schema_element_str
    String containing an DITStructureRuleDescription

  Class attributes:

  ruleid
    rule ID of the DIT structure rule (only locally unique)
  names
    This list of strings contains all NAMEs of the DIT structure rule
  desc
    This string contains description text (DESC) of the DIT structure rule
  obsolete
    Integer flag (0 or 1) indicating whether the DIT content rule is marked
    as OBSOLETE in the schema
  form
    List of strings with NAMEs or OIDs of associated name forms
  sup
    List of strings with NAMEs or OIDs of allowed structural object classes
    of superior entries in the DIT
  """
  schema_attribute = 'dITStructureRules'

  token_defaults = {
    'NAME':(()),
    'DESC':(None,),
    'OBSOLETE':None,
    'FORM':(None,),
    'SUP':(()),
  }

  def set_id(self,element_id):
    self.ruleid = element_id

  def get_id(self):
    return self.ruleid

  def _set_attrs(self,l,d):
    self.names = d['NAME']
    self.desc = d['DESC'][0]
    self.obsolete = d['OBSOLETE']!=None
    self.form = d['FORM'][0]
    self.sup = d['SUP']
    assert type(self.names)==TupleType
    assert self.desc is None or type(self.desc)==StringType
    assert type(self.obsolete)==BooleanType and (self.obsolete==0 or self.obsolete==1)
    assert type(self.form)==StringType
    assert type(self.sup)==TupleType
    return

  def __str__(self):
    result = [str(self.ruleid)]
    result.append(self.key_list('NAME',self.names,quoted=1))
    result.append(self.key_attr('DESC',self.desc,quoted=1))
    result.append({0:'',1:' OBSOLETE'}[self.obsolete])
    result.append(self.key_attr('FORM',self.form,quoted=0))
    result.append(self.key_list('SUP',self.sup,sep=' $ '))
    return '( %s )' % ''.join(result)


class NameForm(SchemaElement):
  """
  Arguments:
  
  schema_element_str
    String containing an NameFormDescription

  Class attributes:

  oid
    OID of the name form
  names
    This list of strings contains all NAMEs of the name form
  desc
    This string contains description text (DESC) of the name form
  obsolete
    Integer flag (0 or 1) indicating whether the name form is marked
    as OBSOLETE in the schema
  form
    List of strings with NAMEs or OIDs of associated name forms
  oc
    String with NAME or OID of structural object classes this name form
    is usable with
  must
    This list of strings contains NAMEs or OIDs of all attributes
    an RDN must contain
  may
    This list of strings contains NAMEs or OIDs of additional attributes
    an RDN may contain
  """
  schema_attribute = 'nameForms'
  token_defaults = {
    'NAME':(()),
    'DESC':(None,),
    'OBSOLETE':None,
    'OC':(None,),
    'MUST':(()),
    'MAY':(()),
  }

  def _set_attrs(self,l,d):
    self.names = d['NAME']
    self.desc = d['DESC'][0]
    self.obsolete = d['OBSOLETE']!=None
    self.oc = d['OC'][0]
    self.must = d['MUST']
    self.may = d['MAY']
    assert type(self.names)==TupleType
    assert self.desc is None or type(self.desc)==StringType
    assert type(self.obsolete)==BooleanType and (self.obsolete==0 or self.obsolete==1)
    assert type(self.oc)==StringType
    assert type(self.must)==TupleType
    assert type(self.may)==TupleType
    return

  def __str__(self):
    result = [str(self.oid)]
    result.append(self.key_list('NAME',self.names,quoted=1))
    result.append(self.key_attr('DESC',self.desc,quoted=1))
    result.append({0:'',1:' OBSOLETE'}[self.obsolete])
    result.append(self.key_attr('OC',self.oc))
    result.append(self.key_list('MUST',self.must,sep=' $ '))
    result.append(self.key_list('MAY',self.may,sep=' $ '))
    return '( %s )' % ''.join(result)


class Entry(UserDict.UserDict):
  """
  Schema-aware implementation of an LDAP entry class.
  
  Mainly it holds the attributes in a string-keyed dictionary with
  the OID as key.
  """

  def __init__(self,schema,dn,entry):
    self._keytuple2attrtype = {}
    self._attrtype2keytuple = {}
    self._s = schema
    self.dn = dn
    UserDict.UserDict.__init__(self,{})
    self.update(entry)

  def _at2key(self,nameoroid):
    """
    Return tuple of OID and all sub-types of attribute type specified
    in nameoroid.
    """
    try:
      # Mapping already in cache
      return self._attrtype2keytuple[nameoroid]
    except KeyError:
      # Mapping has to be constructed
      oid = self._s.getoid(ldap.schema.AttributeType,nameoroid)
      l = nameoroid.lower().split(';')
      l[0] = oid
      t = tuple(l)
      self._attrtype2keytuple[nameoroid] = t
      return t

  def update(self,dict):
    for key in dict.keys():
      self[key] = dict[key]

  def __contains__(self,key):
    return self.has_key(key)

  def __getitem__(self,nameoroid):
    return self.data[self._at2key(nameoroid)]

  def __setitem__(self,nameoroid,attr_values):
    k = self._at2key(nameoroid)
    self._keytuple2attrtype[k] = nameoroid
    self.data[k] = attr_values

  def __delitem__(self,nameoroid):
    k = self._at2key(nameoroid)
    del self.data[k]
    del self._attrtype2keytuple[nameoroid]
    del self._keytuple2attrtype[k]

  def has_key(self,nameoroid):
    k = self._at2key(nameoroid)
    return self.data.has_key(k)

  def get(self,nameoroid,failobj):
    try:
      return self[nameoroid]
    except KeyError:
      return failobj

  def keys(self):
    return self._keytuple2attrtype.values()

  def items(self):
    return [
      (k,self[k])
      for k in self.keys()
    ]

  def attribute_types(
    self,attr_type_filter=None,raise_keyerror=1
  ):
    """
    Convenience wrapper around SubSchema.attribute_types() which
    passes object classes of this particular entry as argument to
    SubSchema.attribute_types()
    """
    return self._s.attribute_types(
      self.get('objectClass',[]),attr_type_filter,raise_keyerror
    )
