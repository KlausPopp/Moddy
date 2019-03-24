.. _2_sergw: 

==============
Serial Gateway
==============

Covers:

- Sequential Program Simulation
- Multitasking 
- Moddy output port send queuing behavior

This demo models a serial gateway between a network port and a serial port. The gateway has a CPU which runs 
two threads a RxThread and a TxThread, which are scheduled by Moddy's built-in RTOS scheduler simulation.

The RxThread waits for data from the serial device and forwards it to the network port, which is connected to the
Client program.

The TxThread waits for data from the Client and forwards it to the serial port.
 

.. literalinclude:: code/2_sergw.py

The simulation outputs:

 :download:`The sequence diagram <code/output/2_sergw.html>`

 :download:`The structure graph <code/output/2_sergw_structure.svg>`
