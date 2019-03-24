.. include:: ../globals.rst

.. _detailed_modelchecking:


*********************************************
Model Checking
*********************************************


Moddy 1.5 added a possibility for checkers in the model to tell the simulator that it detected 
some abnormal situation, e.g. encountered an invalid state, a result is out of range or some timeout has occurred.

A moddy part can call the following method to signal a problem 
(An example can be found in ``6_vthreadRemoteControlled.py``):


.. code-block:: python
	
	self.assertionFailed('3rd invocation assertion')

By default, such an assertion failure causes the simulation to stop, 
unless you pass ``stopOnAssertionFailure=False`` to the simulators :meth:`~.simulator.sim.run()` method. 
In this case, the simulator gathers all assertions during the simulation 
and prints a summary at the end of the simulation:


.. code-block:: console
	
	1 Assertion failures during simulation
	    260.0s 3rd invocation assertion: in runVThread, (6_vthreadRemoteControlled.py::37)

Assertion failures are also displayed in the sequence diagram in purple color: 
 
 
.. figure:: ../_static/0300_checking.png 
 