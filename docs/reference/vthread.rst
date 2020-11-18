*************************
Virtual Thread Reference
*************************

Virtual Threads allow Moddy users to model sequential programs. 


Virtual Thread Class
=============================================
.. autoclass:: moddy.vthread.VThread
   :members: run_vthread, wait, wait_until, wait_for_msg, busy, 
             new_vt_sampling_in_port, new_vt_queuing_in_port, 
             new_vt_sampling_io_port, new_vt_queuing_io_port, 
             new_vt_timer, create_ports, 
             create_vt_timers, TerminateException, wait_for_monitor
	
Ports for Virtual Threads
--------------------------
.. autoclass:: moddy.vthread.VtInPort
   :members: read_msg, n_msg

.. autoclass:: moddy.vthread.VtSamplingInPort
   :members: read_msg, n_msg

.. autoclass:: moddy.vthread.VtQueuingInPort
   :members: read_msg, n_msg
   
.. autoclass:: moddy.vthread.VtIOPort


Timer for Virtual Threads
--------------------------
.. autoclass:: moddy.vthread.VtTimer
   :members: start, restart, has_fired


RTOS Scheduler Simulation for Virtual Threads 
=============================================
.. autoclass:: moddy.vt_sched_rtos.VtSchedRtos
   :members: add_vthread

.. autoclass:: moddy.vt_sched_rtos.VSimpleProg

