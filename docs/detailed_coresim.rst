.. include globals.rst

.. _detailed_coresim:


***************
Core Simulator
***************



Initializing the Simulator
==========================

The simulator is the first class you must instantiate. The simulator constructor has no arguments:

.. code-block: python

	from moddy import *
	simu = sim()

The *simu* variable has to be passed to the parts.

