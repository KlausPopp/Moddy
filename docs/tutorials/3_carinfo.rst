=================
Car Infotainment
=================

Covers:

- Finite State Machines
- Nested State Machines

This demo simulates the behavior of a (extremely simplified) car infotainment system.

The main state is simulated with a Moddy Finite state machine. (Off, Booting, NormalOp etc).

The normal state has several nested sub-state machines, such as: 

- 'Apps' (Radio, Navi) - jumps between the different applications (in this simulation, the apps have no function)
- 'Volume' - manages the audio volume

The Stim part simulates user events. 

.. literalinclude:: code/3_carinfo.py

The simulation outputs:

 :download:`The sequence diagram <code/output/3_carinfo.html>`

 :download:`The FSM graph <code/output/3_carinfo_fsm.svg>`
