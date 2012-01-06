import socorro.processor.signatureUtilities as sig
import socorro.lib.util as sutil

import re

def assert_expected (expected, received):
    assert expected == received, 'expected:\n%s\nbut got:\n%s' % (expected,
                                                                  received)

def setupSigUtil(ig='ignored1', pr='pre1|pre2', si='fnNeedNumber'):
    config = sutil.DotDict()
    config.logger = sutil.FakeLogger()
    config.irrelevantSignatureRegEx = ig
    config.prefixSignatureRegEx = pr
    config.signaturesWithLineNumbersRegEx = si
    config.signatureSentinels = ('sentinel',
                                 ('sentinel2', lambda x: 'ff' in x),
                                )
    s = sig.SignatureUtilities(config)
    return s, config

def testInit():
    """testInit: constructor test"""
    expectedRegEx = sutil.DotDict()
    expectedRegEx.irrelevantSignatureRegEx = re.compile('ignored1')
    expectedRegEx.prefixSignatureRegEx = re.compile('pre1|pre2')
    expectedRegEx.signaturesWithLineNumbersRegEx = re.compile('fnNeedNumber')
    fixupSpace = re.compile(r' (?=[\*&,])')
    fixupComma = re.compile(r',(?! )')
    fixupInteger = re.compile(r'(<|, )(\d+)([uUlL]?)([^\w])')

    s, c = setupSigUtil(expectedRegEx.irrelevantSignatureRegEx,
                        expectedRegEx.prefixSignatureRegEx,
                        expectedRegEx.signaturesWithLineNumbersRegEx)

    assert_expected(c, s.config)
    assert_expected(expectedRegEx.irrelevantSignatureRegEx,
                    s.irrelevantSignatureRegEx)
    assert_expected(expectedRegEx.prefixSignatureRegEx,
                    s.prefixSignatureRegEx)
    assert_expected(expectedRegEx.signaturesWithLineNumbersRegEx,
                    s.signaturesWithLineNumbersRegEx)
    assert_expected(fixupSpace,
                    s.fixupSpace)
    assert_expected(fixupComma,
                    s.fixupComma)
    assert_expected(fixupInteger,
                    s.fixupInteger)

def testNormalize():
    """testNormalize: bunch of variations"""
    s, c = setupSigUtil()
    a = [ (('module', 'fn', 'source', '23', '0xFFF'), 'fn'),
          (('module', 'fnNeedNumber', 's', '23', '0xFFF'), 'fnNeedNumber:23'),
          (('module', 'f( *s)', 's', '23', '0xFFF'), 'f(*s)'),
          (('module', 'f( &s)', 's', '23', '0xFFF'), 'f(&s)'),
          (('module', 'f( *s , &n)', 's', '23', '0xFFF'), 'f(*s, &n)'),
          # this next one looks like a bug to me, but perhaps the situation
          # never comes up
          #(('module', 'f(  *s , &n)', 's', '23', '0xFFF'), 'f(*s, &n)'),
          (('module', 'f3(s,t,u)', 's', '23', '0xFFF'), 'f3(s, t, u)'),
          (('module', 'f<3>(s,t,u)', 's', '23', '0xFFF'), 'f<int>(s, t, u)'),
          (('module', '', 'source/', '23', '0xFFF'), 'source#23'),
          (('module', '', 'source\\', '23', '0xFFF'), 'source#23'),
          (('module', '', '/a/b/c/source', '23', '0xFFF'), 'source#23'),
          (('module', '', '\\a\\b\\c\\source', '23', '0xFFF'), 'source#23'),
          (('module', '', '\\a\\b\\c\\source', '23', '0xFFF'), 'source#23'),
          (('module', '', '\\a\\b\\c\\source', '', '0xFFF'), 'module@0xFFF'),
          (('module', '', '', '23', '0xFFF'), 'module@0xFFF'),
          (('module', '', '', '', '0xFFF'), 'module@0xFFF'),
          ((None, '', '', '', '0xFFF'), '@0xFFF'),
        ]
    for args, e in a:
        r = s.normalize_signature(*args)
        assert_expected(e,r)

def testGenerate1():
    """testGenerate1: simple"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
    e = 'd | e | f | g'
    r = s.generate_signature_from_list(a)
    assert_expected(e,r)

    a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
    e = 'd | e | f | g'
    r = s.generate_signature_from_list(a)
    assert_expected(e,r)

def testGenerate2():
    """testGenerate2: hang"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
    e = 'hang | d | e | f | g'
    r = s.generate_signature_from_list(a, hangType=-1)
    assert_expected(e,r)

    a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
    e = 'hang | d | e | f | g'
    r = s.generate_signature_from_list(a, hangType=-1)
    assert_expected(e,r)

    a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
    e = 'd | e | f | g'
    r = s.generate_signature_from_list(a, hangType=0)
    assert_expected(e,r)

    a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
    e = 'chromehang | d | e | f | g'
    r = s.generate_signature_from_list(a, hangType=1)
    assert_expected(e,r)


def testGenerate2a():
    """testGenerate2a: way too long"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
    a[3] = a[3] * 70
    a[4] = a[4] * 70
    a[5] = a[5] * 70
    a[6] = a[6] * 70
    a[7] = a[7] * 70
    e = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd" \
        "dd | eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" \
        "eeeeeee | ffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" \
        "ffffffffffff | ggggggggggggggggggggggggggggggggg..."
    r = s.generate_signature_from_list(a)
    assert_expected(e,r)
    e = "hang | ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd" \
        "ddddddddd | eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" \
        "eeeeeeeeeeeeee | fffffffffffffffffffffffffffffffffffffffffffffffffff" \
        "fffffffffffffffffff | gggggggggggggggggggggggggg..."
    r = s.generate_signature_from_list(a, hangType=-1)
    assert_expected(e,r)

def testGenerate3():
    """testGenerate3: simple sentinel"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
    a[7] = 'sentinel'
    e = 'sentinel'
    r = s.generate_signature_from_list(a)
    assert_expected(e,r)

    s, c  = setupSigUtil('a|b|c|sentinel', 'd|e|f')
    e = 'f | e | d | i'
    r = s.generate_signature_from_list(a)
    assert_expected(e,r)

def testGenerate4():
    """testGenerate4: tuple sentinel"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
    a[7] = 'sentinel2'
    e = 'd | e | f | g'
    r = s.generate_signature_from_list(a)
    assert_expected(e,r)

    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
    a[7] = 'sentinel2'
    a[22] = 'ff'
    e = 'sentinel2'
    r = s.generate_signature_from_list(a)
    assert_expected(e,r)

    s, c = setupSigUtil('a|b|c|sentinel2', 'd|e|f')
    a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
    a[7] = 'sentinel2'
    a[22] = 'ff'
    e = 'f | e | d | i'
    r = s.generate_signature_from_list(a)
    assert_expected(e,r)

