*****************************
Simulator Core API Reference
*****************************

Simulator Core
--------------

These are the user relevant methods of the simulator core:

.. autoclass:: moddy.sim_core.Sim
   :members: run, is_running, stop, time, time_str, smart_bind

Simulator Tracing
------------------

.. autoclass:: moddy.sim_core.SimTracing
   :members: set_display_time_unit

Simulator Monitoring
--------------------

.. autoclass:: moddy.sim_monitor.SimMonitorManager
   :members: add_monitor, delete_monitor

SimPart
--------------

These are the user relevant methods of the SimPart class:

.. autoclass:: moddy.sim_part.SimPart
   :members: create_ports, create_timers, new_input_port, new_output_port, 
    new_io_port, new_timer, new_var_watcher,
    set_state_indicator, annotation, assertion_failed, start_sim, 
    terminate_sim, time

Input Port
--------------
.. autoclass:: moddy.sim_ports.SimInputPort
   :members: set_msg_started_func
 

Output Port
--------------
.. autoclass::  moddy.sim_ports.SimOutputPort
   :members: bind, send, set_color, inject_lost_message_error_by_sequence

I/O Port
--------------
.. autoclass:: moddy.sim_ports.SimIOPort
   :members: bind, loop_bind, send, set_color, 
    inject_lost_message_error_by_sequence, set_msg_started_func


Timer
--------------
.. autoclass:: moddy.sim_ports.SimTimer
   :members: start, stop, restart

Global Constants 
----------------

.. _predef-bc-colors:

Predefined color names for status boxes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autodata:: moddy.constants.BC_WHITE_ON_GREEN
.. autodata:: moddy.constants.BC_WHITE_ON_RED
.. autodata:: moddy.constants.BC_WHITE_ON_RED
.. autodata:: moddy.constants.BC_WHITE_ON_BROWN
.. autodata:: moddy.constants.BC_WHITE_ON_BLACK
.. autodata:: moddy.constants.BC_BLACK_ON_PINK
.. autodata:: moddy.constants.BC_BLACK_ON_GREY
.. autodata:: moddy.constants.BC_WHITE_ON_GREY
.. autodata:: moddy.constants.BC_BLACK_ON_WHITE
