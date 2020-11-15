=========================
Remote Controlled Threads
=========================

Covers:

- How to use a remote controlled thread.
- Thread execptions and assertions

This demo demonstrates remote controlable vThreads. The *myRCThread* is instantiated with the *remoteControlled* 
attribute, which means it will have a *threadControlPort*, through which it can be started and stopped.

The *Stim* object starts and kills the *myRCThread*.

This demo also shows 

	* That messages on input ports get lost while a thread is dead
	* That thread instance variables (e.g. *threadInvocationCount*) survive a thread restart
	* What happens if a thread calls *assertion_failed*
	* What happens if a thread throws an Exception



.. warning:: 
 	It is intended that this demo reports

	1) an assertion 
	2) an exception 

	To demonstrate what happens if threads throw exceptions or model assertions


.. literalinclude:: code/6_vthreadRemoteControlled.py

The simulation outputs:

 :download:`The sequence diagram <code/output/6_vthreadRemoteControlled.html>`

