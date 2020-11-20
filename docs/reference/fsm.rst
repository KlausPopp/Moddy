*********************************
Moddy Finite State Machines
*********************************

.. _fsmReference:

Finite State Machine
====================
.. autoclass:: moddy.fsm.Fsm
   :members: event, exec_state_dependent_method, start_fsm, top_fsm, 
    moddy_part, set_state_change_callback, has_event

.. _SimFsmPartReference:

Moddy Part using a Finite State Machine
========================================
.. autoclass:: moddy.fsm_part.SimFsmPart
   :members: create_ports, create_timers