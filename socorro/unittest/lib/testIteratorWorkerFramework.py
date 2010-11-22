import socorro.lib.iteratorWorkerFramework as siwf
import socorro.lib.util as sutil

import time

def testConstuctor1 ():
    logger = sutil.SilentFakeLogger()
    config = sutil.DotDict({ 'logger': logger,
               'numberOfThreads': 1
             })
    iwf = siwf.IteratorWorkerFramework(config,
                                       name='Wilma',
                                      )
    try:
        assert iwf.config == config
        assert iwf.name == 'Wilma'
        assert iwf.logger == logger
        assert iwf.taskFunc == siwf.defaultTaskFunc
        assert iwf.quit == False
    finally:
        # we got threads to join
        iwf.workerPool.waitForCompletion()

def testStart1 ():
    logger = sutil.SilentFakeLogger()
    config = sutil.DotDict({ 'logger': logger,
               'numberOfThreads': 1
             })
    iwf = siwf.IteratorWorkerFramework(config,
                                       name='Wilma',
                                      )
    try:
        iwf.start()
        time.sleep(2.0)
        assert iwf.queuingThread.isAlive(), "the queing thread is not running"
        assert len(iwf.workerPool.threadList) == 1, "where's the worker thread?"
        assert iwf.workerPool.threadList[0].isAlive(), "the worker thread is stillborn"
        iwf.stop()
        assert iwf.queuingThread.isAlive() == False, "the queuing thread did not stop"
    except Exception:
        # we got threads to join
        iwf.workerPool.waitForCompletion()

def testDoingWorkWithOneWorker():
    logger = sutil.SilentFakeLogger()
    config = sutil.DotDict({ 'logger': logger,
               'numberOfThreads': 1
             })
    myList = []
    def insertIntoList(anItem):
        myList.append(anItem[0])
        return siwf.ok
    iwf = siwf.IteratorWorkerFramework(config,
                                       name='Wilma',
                                       taskFunc=insertIntoList
                                      )
    try:
        iwf.start()
        time.sleep(2.0)
        assert len(myList) == 10, 'expected to do 10 inserts, but %d were done instead' % len(myList)
        assert myList == range(10), 'expected %s, but got %s' % (range(10), myList)
        iwf.stop()
    except Exception:
        # we got threads to join
        iwf.workerPool.waitForCompletion()
        raise


def testDoingWorkWithTwoWorkers():
    logger = sutil.SilentFakeLogger()
    config = sutil.DotDict({ 'logger': logger,
               'numberOfThreads': 2
             })
    myList = []
    def insertIntoList(anItem):
        myList.append(anItem[0])
        return siwf.ok
    iwf = siwf.IteratorWorkerFramework(config,
                                       name='Wilma',
                                       taskFunc=insertIntoList
                                      )
    try:
        iwf.start()
        time.sleep(2.0)
        assert len(iwf.workerPool.threadList) == 2, "expected 2 threads, but found %d" % len(iwf.workerPool.threadList)
        assert len(myList) == 10, 'expected to do 10 inserts, but %d were done instead' % len(myList)
        assert sorted(myList) == range(10), 'expected %s, but got %s' % (range(10), sorted(myList))
        iwf.stop()
    except Exception:
        # we got threads to join
        iwf.workerPool.waitForCompletion()
        raise
