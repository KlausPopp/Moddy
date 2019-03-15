*****************************
Simulator Core API Reference
*****************************

Simulator Core
--------------

These are the user relevant methods of the simulator core:

.. autoclass:: moddy.simulator.sim
   :members: run, setDisplayTimeUnit, timeStr
   
SimPart
--------------

These are the user relevant methods of the simPart class:

.. autoclass:: moddy.simulator.simPart
   :members: createPorts, createTimers, newInputPort, newOutputPort, newIOPort, newTimer, newVarWatcher,
    setStateIndicator, addAnnotation, assertionFailed, startSim, terminateSim, time

Input Port
--------------
.. autoclass:: moddy.simulator.simInputPort

Output Port
--------------
.. autoclass:: moddy.simulator.simOutputPort
   :members: bind, send, setColor, injectLostMessageErrorBySequence

I/O Port
--------------
.. autoclass:: moddy.simulator.simIOPort
   :members: bind, loopBind, send, setColor, injectLostMessageErrorBySequence

Timer
--------------
.. autoclass:: moddy.simulator.simTimer
   :members: start, stop, restart

