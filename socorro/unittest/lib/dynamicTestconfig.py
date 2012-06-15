# Deliberately use base-class's Option class just to see if things break (they better not)
import socorro.lib.ConfigurationManager as cm

testOption0 = cm.Option()
testOption0.doc = 'option 0'
testOption0.default = 0

testOption1 = cm.Option()
testOption1.doc = 'option one'
testOption1.default = 'one'

logFilePathname = cm.Option()
logFilePathname.default = '/some/bogus/location'
