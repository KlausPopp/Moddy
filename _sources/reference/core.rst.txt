*****************************
Simulator Core API Reference
*****************************

Simulator Core
--------------

These are the user relevant methods of the simulator core:

.. autoclass:: moddy.simulator.sim
   :members: run, setDisplayTimeUnit, timeStr, smartBind, addMonitor, deleteMonitor
   
SimPart
--------------

These are the user relevant methods of the simPart class:

.. autoclass:: moddy.simulator.simPart
   :members: createPorts, createTimers, newInputPort, newOutputPort, newIOPort, newTimer, newVarWatcher,
    setStateIndicator, addAnnotation, assertionFailed, startSim, terminateSim, time

Input Port
--------------
.. autoclass:: moddy.simulator.simInputPort
   :members: setMsgStartedFunc
 

Output Port
--------------
.. autoclass:: moddy.simulator.simOutputPort
   :members: bind, send, setColor, injectLostMessageErrorBySequence

I/O Port
--------------
.. autoclass:: moddy.simulator.simIOPort
   :members: bind, loopBind, send, setColor, injectLostMessageErrorBySequence, setMsgStartedFunc


Timer
--------------
.. autoclass:: moddy.simulator.simTimer
   :members: start, stop, restart

Global Constants 
----------------

.. _predef-bc-colors:

Predefined color names for status boxes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autodata:: moddy.__init__.bcWhiteOnGreen
.. autodata:: moddy.__init__.bcWhiteOnRed
.. autodata:: moddy.__init__.bcWhiteOnBlue
.. autodata:: moddy.__init__.bcWhiteOnBrown
.. autodata:: moddy.__init__.bcWhiteOnBlack
.. autodata:: moddy.__init__.bcBlackOnPink
.. autodata:: moddy.__init__.bcBlackOnGrey
.. autodata:: moddy.__init__.bcWhiteOnGrey
.. autodata:: moddy.__init__.bcBlackOnWhite 
