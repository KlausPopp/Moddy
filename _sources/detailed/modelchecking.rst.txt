.. include:: ../globals.rst

.. _detailed_modelchecking:


*********************************************
Model Checking
*********************************************

Model Assertions
==========================

Moddy 1.5 added a possibility for checkers in the model to tell the simulator that it detected 
some abnormal situation, e.g. encountered an invalid state, a result is out of range or some timeout has occurred.

A moddy part can call the following method to signal a problem 
(An example can be found in ``6_vthread_remote_controlled.py``):


.. code-block:: python
	
	self.assertion_failed('3rd invocation assertion')

By default, such an assertion failure causes the simulation to stop, 
unless you pass ``stop_on_assertion_failure=False`` to the simulators :meth:`~.sim_core.Sim.run()` method. 
In this case, the simulator gathers all assertions during the simulation 
and prints a summary at the end of the simulation:


.. code-block:: console
	
	1 Assertion failures during simulation
	    260.0s 3rd invocation assertion: in run_vthread, (6_vthread_remote_controlled.py::37)

Assertion failures are also displayed in the sequence diagram in purple color: 
 
 
.. figure:: ../_static/0300_checking.png 
 

Model Monitors
==========================

Moddy 1.10 added a possibility to register functions that gets called at each simulation
step. More specifically, they are called at the *end* of each simulation step, after
the scheduled event has been executed.

This can be useful e.g. to check if some model variable is within the allowed
range.

Monitor functions can be dynamically added and deleted.

Monitor functions are executed in the context of the simulator and get called without
arguments.

See :meth:`~.sim_monitor.SimMonitorManager.add_monitor()` and :meth:`~.sim_core.SimMonitorManager.delete_monitor()`.

Using a model monitor in a Stimulation Program
----------------------------------------------

Moddy 1.10 introduced the :meth:`~.VThread.wait_for_monitor` method to suspend the
thread until the monitor returns ``True``.

Example:

.. code-block:: python

        class MyThread1(moddy.VSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Thread', parent_obj=None)
           
             
            def run_vthread(self):
                cycle = 0
                while True:
                    self.busy(30, 'DEL#%d' % cycle)
                    self.wait(10)
                    cycle += 1
                    
        class StimThread(moddy.VSimpleProg):
            def __init__(self, sim, supervised_thread ):
                super().__init__(sim=sim, obj_name='Stim', parent_obj=None)
                self.supervised_thread = supervised_thread 

            def run_vthread(self):
                self.wait_for_monitor(None, self.monitor_func1)
                self.annotation('got mon1')
                self.wait_for_monitor(None, self.monitor_func3)
                self.annotation('got mon3')
                if self.wait_for_monitor(10, self.monitor_func1) == 'timeout':
                    self.annotation('tout waiting for mon1')

            def monitor_func1(self):
                # called in the context of the simulator!
                return self.supervised_thread._state_ind == "DEL#1"
                    
            def monitor_func3(self):
                # called in the context of the simulator!
                return self.supervised_thread._state_ind == "DEL#3"

        simu = moddy.Sim()
                        
        t1 = MyThread1(simu)
        
        stim = StimThread(simu, t1)
        
        simu.run(200)
        


 