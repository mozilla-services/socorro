# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socorro.lib.ConfigurationManager as cm

testNil = cm.Option()

testSingleCharacter = cm.Option()
testSingleCharacter.singleCharacter = 'T'

testDefault = cm.Option()
testDefault.default = 'default'

testDoc = cm.Option()
testDoc.doc = 'test doc'

