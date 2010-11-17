import socorro.storage.storageMover as smover
import socorro.lib.util as sutil

import socorro.unittest.testlib.expectations as exp

def getLocalFs1Storage1(config):
    s = exp.DummyObjectWithExpectations()
    s.expect('__call__', (config,), {}, s) # return self


def getHbaseStorage1(config):
    fakeHbaseStorage = exp.DummyObjectWithExpectations()

def testMovement ():
    config = sutil.DotDict({
                          })
    fakeLocalFsStorage = getLocalFs1Storage1(config)
    fakeHbaseStorage = getHbaseStorage1(config)


