*************************
Virtual Thread Reference
*************************

Virtual Threads allow Moddy users to model sequential programs. 


Virtual Thread Class
=============================================
.. autoclass:: moddy.vthread.vThread
   :members: runVThread, wait, waitUntil, waitForMsg, busy, newVtSamplingInPort, newVtQueuingInPort, newVtSamplingIOPort, newVtQueuingIOPort, newVtTimer, createPorts, 
             createVtTimers, TerminateException, waitForMonitor
	
Ports for Virtual Threads
--------------------------
.. autoclass:: moddy.vthread.vtInPort
   :members: readMsg, nMsg

.. autoclass:: moddy.vthread.vtSamplingInPort
   :members: readMsg, nMsg

.. autoclass:: moddy.vthread.vtQueuingInPort
   :members: readMsg, nMsg
   
.. autoclass:: moddy.vthread.vtIOPort


Timer for Virtual Threads
--------------------------
.. autoclass:: moddy.vthread.vtTimer
   :members: start, restart, hasFired


RTOS Scheduler Simulation for Virtual Threads 
=============================================
.. autoclass:: moddy.vtSchedRtos.vtSchedRtos
   :members: addVThread

.. autoclass:: moddy.vtSchedRtos.vSimpleProg

