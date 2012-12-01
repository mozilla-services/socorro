## This Source Code Form is subject to the terms of the Mozilla Public
## License, v. 2.0. If a copy of the MPL was not distributed with this
## file, You can obtain one at http://mozilla.org/MPL/2.0/.


# THE COMMENTING OUT OF THE CONTENTS OF THIS FILE IS TEMPORARY
#
# it will be rewritten and renabled when the new HBase multidump code
# is ready.

#import socorro.storage.storageMover as smover
#import socorro.lib.util as sutil
#import socorro.storage.crashstorage as cstore
#import time

#import socorro.unittest.testlib.expectations as exp

#def getHbaseStorage1(config):
    #h = exp.DummyObjectWithExpectations()
    #h.expect('__call__', (config,), {}, h) # return self
    #h.expect('save_raw', ('1', 'one', 'eins'), {},
             #cstore.CrashStorageSystem.OK)
    #h.expect('save_raw', ('2', 'two', 'zwei'), {},
             #cstore.CrashStorageSystem.RETRY)
    #h.expect('save_raw', ('2', 'two', 'zwei'), {},
             #cstore.CrashStorageSystem.OK)
    #return h

#class fakeSource(object):
    #def __init__(self, config):
        #pass
    #def newUuids(self):
        #for x in ['1', '2', '2']:
            #yield x
        #time.sleep(15)
        #raise KeyboardInterrupt
    #def get_meta_iter(self):
        #for x in ['one', 'two', 'two']:
            #yield x
    #def get_meta(self, ooid):
        #try:
            #return self.meta_iter.next()
        #except AttributeError:
            #self.meta_iter = self.get_meta_iter()
            #return self.meta_iter.next()
    #def get_raw_dump_iter(self):
        #for x in ['eins', 'zwei', 'zwei']:
            #yield x
    #def get_raw_dump(self, ooid):
        #try:
            #return self.raw_iter.next()
        #except AttributeError:
            #self.raw_iter = self.get_raw_dump_iter()
            #return self.raw_iter.next()
    #def quickDelete(self, ooid):
        #pass

#def testMovement ():
    #"""testMovement (this will take 15-20 seconds)"""
    #config = sutil.DotDict({'logger': sutil.SilentFakeLogger(),
                            #'numberOfThreads': 1,
                          #})
    #fakeHbaseStorage = getHbaseStorage1(config)
    #smover.move(config,
                #sourceCrashStorageClass=fakeSource,
                #destCrashStorageClass=fakeHbaseStorage)
