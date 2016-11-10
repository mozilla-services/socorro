#!/usr/bin/python
# Copyright (c) 2004-2005 Oregon State University - Open Source Lab
# All rights reserved.

# $Id$
# $HeadURL$

# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.

# This software is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.

# You should have received a copy of the GNU General Public License
# along with this software; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# Copyright 2005 by Oregon State Univeristy Open Source Lab
#
#    This file is part of OSUOSL Sentry Application of the Bouncer Project
#
#    The OSUOSL Sentry Application is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    The OSUOSL Sentry Application is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with The OSUOSL Sentry Application; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Written by K "Lars" Lohn 2/05

import threading
import Queue
import traceback
import sys

#======================
# T a s k M a n a g e r
#======================
class TaskManager(object):
  """This class serves as a manager for a set of threads.

  Based very loosely on: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/203871
  """
  #----------------
  # _ _ i n i t _ _
  #----------------
  def __init__ (self, numberOfThreads, maxQueueSize=0):
    """Initialize and start all threads"""
    self.threadList = []
    self.numberOfThreads = numberOfThreads
    self.taskQueue = Queue.Queue(maxQueueSize)
    for x in range(numberOfThreads):
      newThread = TaskManagerThread(self)
      self.threadList.append(newThread)
      newThread.start()

  #--------------
  # n e w T a s k
  #--------------

  def newTask (self, task, args=None):
    """Add a task to be executed by a thread

    The input is a tuple with these components:
        task - a function to be run by a thread
        args - a tuple of arguments to be passed to the function
    """
    self.taskQueue.put((task, args))

  #----------------------------------
  # w a i t F o r C o m p l e t i o n
  #----------------------------------
  def waitForCompletion (self):
    """Wait for all threads to complete their work

    The worker threads are told to quit when they receive a task
    that is a tuple of (None, None).  This routine puts as many of
    those tuples in the task queue as there are threads.  As soon as
    a thread receives one of these tuples, it dies.
    """
    for x in range(self.numberOfThreads):
      self.taskQueue.put((None, None))
    for t in self.threadList:
      # print "attempting to join %s" % t.getName()
      t.join()


#==================================
# T a s k M a n a g e r T h r e a d
#==================================
class TaskManagerThread(threading.Thread):
  """This class represents a worker thread for the TaskManager class"""

  #----------------
  # _ _ i n i t _ _
  #----------------
  def __init__(self, manager):
    """Initialize a new thread.
    """
    super(TaskManagerThread, self).__init__()
    self.manager = manager

  #------
  # r u n
  #------
  def run(self):
    """The main routine for a thread's work.

    The thread pulls tasks from the manager's task queue and executes
    them until it encounters a task with a function that is None.
    """
    try:
      while True:
        aFunction, arguments = self.manager.taskQueue.get()
        if aFunction is None:
          break
        aFunction(arguments)
    except KeyboardInterrupt:
      import thread
      print >>sys.stderr, "%s caught KeyboardInterrupt" % threading.currentThread().getName()
      thread.interrupt_main()
    except Exception, x:
      print >>sys.stderr, "Something BAD happened in %s:" % threading.currentThread().getName()
      traceback.print_exc(file=sys.stderr)
      print >>sys.stderr, x

