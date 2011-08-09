import socorro.lib.ConfigurationManager as cm

testNil = cm.Option()

testSingleCharacter = cm.Option()
testSingleCharacter.singleCharacter = 'T'

testDefault = cm.Option()
testDefault.default = 'default'

testDoc = cm.Option()
testDoc.doc = 'test doc'

