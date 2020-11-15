.. include:: ../globals.rst

.. _detailed_seqprog:

*********************************************
Sequential Program Simulation
*********************************************



With the message and timer callbacks explained before, you can model already everything.

However, when you want to model a sequential execution, 
it can be quite cumbersome to do this with the event based mechanism. 
For example if you want to model the execution of a software program like this

	* Get inputs (from Moddy messages), takes 100 |microseconds|
	* Calculate, takes 1ms
	* Set outputs, takes 200 |microseconds|
	
With the event based mechanism, you would need a state machine in the timer's callback routine, 
which is not easy to understand.

So Moddy allows an alternative way to model those sequential programs, simply called "Programs" in the following.
 
To create a "program", your Part must be a subclass of either :class:`~.vthread.vThread` 
or :class:`~.vtSchedRtos.vSimpleProg`. 
(More about the difference between them in chapter :ref:`diff-simpleprog-and-vthread`).


Program Model
=============

.. code-block:: python

	
	class Client(vSimpleProg):
	    def __init__(self, sim):
	        super().__init__(sim=sim, objName="Client", parentObj=None)
	        self.create_ports('QueuingIO', ['netPort']) 
	
	    def runVThread(self):
	        while True:
	            self.wait(1.2*ms)
	            self.netPort.send('test', 100*us)
	            self.busy(100*us, 'TX1', whiteOnBlue)
	            self.netPort.send('test1', 100*us)
	            self.busy(100*us, 'TX2', whiteOnRed)
   
.. figure:: ../_static/0200_vthread.png 
 

In the above example, you see a very simple sequential program, that is

	* Idle (waiting) for 1.2ms
	* Performing a send "TX1" operation, which takes 100 |microseconds|
	* Performing a send "TX2" operation, which takes 100 |microseconds|

Moddy parts derived from :class:`~.vthread.vThread` or :class:`~.vtSchedRtos.vSimpleProg` 
must implement a method :meth:`~.vthread.vThread.runVThread`. This method contains your sequential program model. 

It is called at the start of the simulation time (simulation time 0).

The :meth:`~.vthread.vThread.runVThread` method is not supposed to exit/return, that's why it contains an endless loop. 
(However, for remote controlled vThreads it makes sense to exit/return, see :ref:`remote-controlled-thread` 
for more information)

Since Moddy 1.8, you don't need a subclass of :class:`~.vthread.vThread` or :class:`~.vtSchedRtos.vSimpleProg` anymore. 
You can pass instead a function to the constructor of :class:`~.vthread.vThread` or :class:`~.vtSchedRtos.vSimpleProg` via
the `target` parameter. This function (in the example below ``bobProg`` is then called from :meth:`~.vthread.vThread.runVThread`:

.. code-block:: python

	def bobProg(self: vSimpleProg):
	    # bob starts talking
	    self.head.send("Hi Joe", 1)
	    
	    while True:
	        msg = self.waitForMsg(None, self.head)

	if __name__ == '__main__':
	    simu = sim()
    
	    vSimpleProg( sim=simu, objName="Bob", target=bobProg, elems={ 'QueuingIO': 'head' } )


The program model in :meth:`~.vthread.vThread.runVThread` can control the timing of the program via "system calls":

	* :meth:`~.vthread.vThread.wait()` delays the program execution for a specified time or 
	  until an event occurred, indicating that the program is idle. No status box is shown on 
	  the sequence diagram life line while a program is waiting
	* :meth:`~.vthread.vThread.busy()` delays the program execution for the specified time. 
	  A user defined status box (e.g. 'TX1' in the example above occurs) is shown on the life line 
	  while the program is busy.
	
.. note::
 
	Moddy executes each :meth:`~.vthread.vThread.runVThread` method in a separate python thread. 
	But don't worry: Race conditions resulting from concurrent execution cannot occur in Moddy, 
	because Moddy executes exactly only one thread at each time, either the simulator thread or one of the vThreads. 
	There is no need to protect your data via mutexes.
	
Communication between Moddy Programs and other Moddy Parts
===========================================================

Like normal Moddy parts, Moddy Programs shall communicate with other parts only via Moddy messages. 
To send messages, a Moddy program can use standard output ports. There is no difference to other parts.

But a standard input port executes a callback method. 
It cannot tell the program that a message has been received (other than setting a global variable). 
For this reason, Moddy provides "buffering input ports".

Buffering Input Ports
=====================

A buffering input port buffers received messages in the part's local memory and eventually wakes up the program.
There are two types of buffering ports

	* Sampling Port: A sampling port is used if the receiver is only interested in the most recent message. 
	
		* A sampling port buffers only the last received message.  
		* A read from the sampling buffer does not consume the buffered message
		
	* Queuing Port: A queuing port is used if the receiver wants to get all messages. 
	
		* A queuing port buffers all messages in a fifo queue. The queue depth is infinite. 
		* A read from the buffer consumes the first message

Buffering input ports are derived from :class:`~.vthread.vtInPort`.
 
A program reads a message from a buffering ports via the :meth:`~.vthread.vtInPort.readMsg()` method.
 
It can check the number of messages in the buffer through the :meth:`~.vthread.vtInPort.nMsg()` method.

A program can wait for new message using the :meth:`~.vthread.vThread.wait()` method, or alternatively 
wait for a message and read the first available message through :meth:`~.vthread.vThread.waitForMsg()`.
   
The exact behavior depends on the type of buffer port (Sampling or Queuing) and will be explained in the following.

Sampling Input Ports
--------------------

Recall from previous chapter:

	* A sampling port buffers only the last received message.  
	* A read from the sampling buffer does not consume the buffered message

A sampling input port (:class:`~.vthread.vtSamplingInPort`) is created with the :meth:`~.vthread.vThread.create_ports()` 
method, usually from the program's constructor:


.. code-block:: python

	self.create_ports('SamplingIn', ['inP1'])

The :meth:`~.vthread.vtInPort.readMsg()` method on a sampling input port returns the most recent message received. 
If no message at all was received, it returns either the "default" (if provided) or raises a BufferError exception. 

If you call :meth:`~.vthread.vtInPort.readMsg()` and now new message has arrived since the 
last :meth:`~.vthread.vtInPort.readMsg()` call, you get the same message again. Example:


.. code-block:: python

	msg = self.inP1.readMsg(default='123')

The :meth:`~.vthread.vtInPort.nMsg()` method returns 0 if no message was received at 0, or 1 otherwise. 
A program can call :meth:`~.vthread.vThread.wait()` so that is woken up if a message arrives on the port:

.. code-block:: python

	self.wait(20, [self.inP1])

A sampling input port wakes up a waiting program with every message that arrives.

The following snippet demonstrates the use of a sampling port.
*myThread1* is a program that has a sampling input port *inP1*, while *stimThread* is firing messages to that port.

.. code-block:: python

       class myThread1(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Thread', parentObj=None)
                self.create_ports('SamplingIn', ['inP1'])
                
            def showMsg(self):
                msg = self.inP1.readMsg(default='No message')
                self.annotation(msg)
                
            def runVThread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.showMsg()
                    self.busy(18,cycle, busyAppearance)
                    self.showMsg()
                    self.busy(14,cycle, busyAppearance)
                    self.wait(20,[self.inP1])


        class stimThread(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Stim', parentObj=None)
                self.create_ports('out', ['toT1Port'])
                                
            def runVThread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15)
                    self.toT1Port.send('hello%d' % count,5)



This would result in the following sequence diagram:
   
.. figure:: ../_static/0210_samplinginport.png 
 
 
Queuing Input Ports
-------------------

Recall from previous chapter:
	
	* A queuing port buffers all messages in a fifo queue. The queue depth is infinite. 
	* A read from the buffer consumes the first message

A queuing input port (:class:`~.vthread.vtQueuingInPort`) is created with the :meth:`~.vthread.vThread.create_ports()` 
method, usually from the program's constructor:


.. code-block:: python

	self.create_ports('QueuingIn', ['inP1'])

The :meth:`~.vthread.vtInPort.readMsg()` method on a queuing input port returns the first message of the queue. 
If no message is in the queue, it raises a BufferError exception.
 
The :meth:`~.vthread.vtInPort.nMsg()` method returns the number of messages in the queue (0 if none).

A program can call :meth:`~.vthread.vThread.wait()` so that is woken up when a the first message an empty queue arrives on the port:

.. code-block:: python

	self.wait(20, [self.inP1])

.. warning::

	Call :meth:`~.vthread.vThread.wait()` only on empty queuing ports, 
	otherwise the program will not be woken up (because the wakeup happens only at empty->non-empty transitions)!
	Alternatively, use :meth:`~.vthread.vThread.waitForMsg()`
	
The following snippet demonstrates the use of a queuing port. 
*myThread1* is a program that has a queuing input port *inP1*, while *stimThread* is firing messages to that port.


.. code-block:: python

       class myThread1(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Thread', parentObj=None)
                self.create_ports('QueuingIn', ['inP1'])
            
            def getAllMsg(self):
                lstMsg = []
                while True:
                    try:
                        msg = self.inP1.readMsg()
                        lstMsg.append(msg)
                    except BufferError:
                        break
                
                self.annotation(lstMsg)
         
             
            def runVThread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.busy(33, cycle, busyAppearance)
                    self.getAllMsg()
                    self.wait(20, [self.inP1])
                    self.getAllMsg()


        class stimThread(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Stim', parentObj=None)
                self.create_ports('out', ['toT1Port'])
                                
            def runVThread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15,[])
                    self.toT1Port.send('hello%d' % count,5)


   
.. figure:: ../_static/0220_queuingport.png 
 
Since Moddy 1.8, :meth:`~.vthread.vThread.waitForMsg()` is available. This method waits for a message on any of the
specified ports and returns the first available message:


.. code-block:: python

    def runVThread(self):
        while True:
            # Wait for a message on either inP1 or inP2.
            # Because 2 ports have been specified, waitForMsg returns a tuple with (msg, port) or None
            rv = self.waitForMsg(30, [self.inP1, self.inP2])

            # Wait for a message on inP2.
            # Because 1 port has been specified, waitForMsg returns a just the msg or None
            rv = self.waitForMsg(30, self.inP2)


System Calls for Sequential Programs
====================================

In the previous chapters, the system calls :meth:`~.vthread.vThread.wait()` and :meth:`~.vthread.vThread.busy()` 
were already briefly introduced. Now in more detail:

:meth:`~.vthread.vThread.wait()` delays the program execution for a specified time or until an event occurred.
The model is indicating with :meth:`~.vthread.vThread.wait()` that the program is idle. 
Therefore no status box is shown on the sequence diagram life line while a program is waiting.

.. autofunction:: moddy.vthread.vThread.wait
	:noindex:
	
:meth:`~.vthread.vThread.busy()` delays the program execution for the specified time. 
The model is indicating with :meth:`~.vthread.vThread.busy()` that the program is performing some operation. 
Therefore, a user defined status box appears on the life line while the program is busy.

.. autofunction:: moddy.vthread.vThread.busy
	:noindex:

Concurrent Program Execution/RTOS Simulation
============================================

Moddy comes with a simulation of a simple RTOS (real time operating system) scheduler (:class:`vtSchedRtos:vtSchedRtos`). 

With this feature, you can model SW threads that run concurrently on a single CPU core.
The scheduler has the following features:

	* 16 thread priorities - 0 is highest priority
	* Priority based scheduling. Low priority threads run only if no higher thread ready.
	* Threads with same priority will be scheduled round robin 
	  (when one of the same priority threads releases the processor, 
	  the next same priority thread which is ready is selected). 
	  Note that the round robin occurs not periodically. 
	  It happens only when one task executes :meth:`~.vthread.vThread.wait()`.
	  
	  
First, you create the scheduler object:


.. code-block:: python

	sched= vtSchedRtos(sim=simu, objName="sched", parentObj=None)

Then you add the threads (subclasses of vThread) that shall be scheduled by the scheduler:

.. code-block:: python

        t1 = myThread1(simu)
        t2 = myThread2(simu)
        t3 = myThread3(simu)
        sched.addVThread(t1, prio=0)
        sched.addVThread(t2, prio=1)
        sched.addVThread(t3, prio=1)

Example snippet:


.. code-block:: python

       class myThread1(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='hiThread', parentObj=None)
            def runVThread(self):
                print("   VtHi1")
                self.busy(50,'1',busyAppearance)
                print("   VtHi2")
                self.wait(20,[])
                print("   VtHi3")
                self.busy(10,'2',busyAppearance)
                print("   VtHi4")
                self.wait(100,[])
                print("   VtHi5")
                self.wait(100,[])
                while True:
                    print("   VtHi5")
                    self.busy(10,'3',busyAppearance)
                    self.wait(5,[])
    
        class myThread2(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='lowThreadA', parentObj=None)
            def runVThread(self):
                print("   VtLoA1")
                self.busy(50,'1',busyAppearance)
                print("   VtLoA2")
                self.wait(20,[])
                print("   VtLoA3")
                self.busy(20,'2',busyAppearance)
                print("   VtLoA4")
                self.busy(250,'3',busyAppearance)
            
        class myThread3(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='lowThreadB', parentObj=None)
            def runVThread(self):
                print("   VtLoB1")
                self.busy(50,'1',busyAppearance)
                print("   VtLoB2")
                self.wait(20,[])
                print("   VtLoB3")
                self.busy(100,'2',busyAppearance)
                print("   VtLoB4")
                self.busy(250,'3',busyAppearance)
    
        simu = sim()
        sched= vtSchedRtos(sim=simu, objName="sched", parentObj=None)
                
        t1 = myThread1(simu)
        t2 = myThread2(simu)
        t3 = myThread3(simu)
        sched.addVThread(t1, 0)
        sched.addVThread(t2, 1)
        sched.addVThread(t3, 1)

Resulting in the following sequence diagram:
 
   
.. figure:: ../_static/0230_rtos.png 
 
Note: The "PE" status indicator tells you that the thread is "preempted", i.e. 
it would be ready to run, but it has to wait for the CPU resource, because a higher priority thread is busy.

.. _diff-simpleprog-and-vthread:

vSimpleProg and vThread
=======================

:class:`~.vtSchedRtos.vSimpleProg` is a specialization of :class:`~.vthread.vThread`. 
:class:`~.vtSchedRtos.vSimpleProg` uses an exclusive scheduler for the program, so there are no concurrent threads.
A :class:`~.vthread.vThread` must be explicitly assigned to a scheduler.

Example for a vSimpleProg. This creates a moddy part "Producer" with a single thread attached:

.. code-block:: python

	class Producer(vSimpleProg):
	    def __init__(self, sim):
	        super().__init__(sim=sim, objName="Producer", parentObj=None)
	        self.create_ports('out', ['netPort']) 
	
	    def runVThread(self):
	        while True:
	            self.wait(100*us)
	            self.netPort.send('test', 100*us)


.. _remote-controlled-thread:

Remote Controlled vThreads
==========================

Remote Controlled vThreads are for instance useful to model computer systems that execute software, 
but only if the computer is turned on, and another moddy part shall be able to turn on/off the computer. 
Another example could be Software processes which shall be terminate-able and restart-able.

Normal vThreads are started automatically at the beginning of the simulation and they are supposed to 
run until the end of the simulation. 
Since Moddy 1.5.0, remote controlled vThreads are supported. Subclasses of vThreads like 
:class:`~.vtSchedRtos.vSimpleProg` also have the remote control feature.

Remote Controlled vThreads can be controlled (started and killed) from other moddy parts via a 
moddy input port called ``threadControlPort``. 

Remote Controlled vThreads are not started automatically, but wait for a "start" message on the threadControlPort.
To create a remote controlled vThread, pass ``remoteControlled=True`` to the vThread's __init__ method. 
In another moddy part, create an output port and bind it to ``threadControlPort``.

Extract from tutorial 6_vthreadRemoteControlled.py:


.. code-block:: python

	class myRcThread(vThread):
	    def __init__(self, sim ):
	       super().__init__(sim=sim, objName='rcThread', parentObj=None, 
							remoteControlled=True)
	
	# This thread controls the remote controllable vThread
	class Stim(vSimpleProg):
	    def __init__(self, sim ):
	        super().__init__(sim=sim, objName='Stim', parentObj=None)
	        self.create_ports('out', ["rcPort"])
	        
	    def runVThread(self):
	        self.wait(2)
	
	        # @2s: initial start of rcTread 
	        self.rcPort.send('start',0)
	       	...
	        # @180s: kill rcThread
	        self.rcPort.send('kill',0)
	        self.wait(20)
	
	        
	if __name__ == '__main__':
	    simu = sim()
	    
	    sched= vtSchedRtos(sim=simu, objName="sched", parentObj=None)
	    rcThread = myRcThread(simu)
	    ...
	    sched.addVThread(rcThread, 0)
	    sched.addVThread(utilThread, 1)
	
	    stim = Stim(simu)
	    stim.rcPort.bind(rcThread.threadControlPort)


On the ``threadControlPort``, only two string parameters are supported:

    * **start** - Start or restart the vThread's :meth:`~.vthread.vThread.runVThread` method. 
      If the :meth:`~.vthread.vThread.runVThread` is already active, the start message is ignored.
	  
    * **kill** - Force the :meth:`~.vthread.vThread.runVThread` to abort the 
      current :meth:`~.vthread.vThread.busy()` or :meth:`~.vthread.vThread.wait()` 
      call by raising a vThread.KillException. 
      When the :meth:`~.vthread.vThread.runVThread` has terminated, all pending timers are stopped, 
      all receive queues in the input ports are cleared and no messages can be received while terminated. 
      The kill message is ignored if the vThread is already terminated.

.. note:: 
	Variable persistence: When a thread is re-started, all local variables are lost and must be reinitialized. 
	However, be aware that variables stored in the :class:`~.simulator.SimPart` object (e.g. self.myvar) will survive a restart. 
