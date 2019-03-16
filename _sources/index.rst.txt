.. Moddy Discrete Event Simulator documentation master file, created by
   sphinx-quickstart on Sat Mar  9 20:24:34 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Moddy Discrete Event Simulator's documentation!
==========================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quick_start.rst
   detailed.rst
   reference.rst


What is Moddy?
--------------

Moddy is a simulator to model and analyze the timing behavior of systems consisting 
of objects that communicate via messages. The objects are called "parts" in Moddy, 
to be consistent with the term SysML uses in internal block diagrams.

Moddy was written to analyze complex systems in the concept phase to validate the 
suitability of the concept. Typical applications are

* Modelling communication protocols
* Modelling highly distributed computer systems

You describe the structure and the behavior of your model via a program written in "python" language.
After the simulation run, Moddy can produce a number of result files that you will analyze to 
evaluate whether the model behaves as expected. These result files are

* A sequence diagram 
* An event trace
* A static structure graph of your model (block diagram) 
* A static graph of your finite state machines in the model 

Further result files, such as wave forms may be added in the future.
Moddy's Simulator is a classic Discrete Event simulator. 

From Wikipedia https://en.wikipedia.org/wiki/Discrete_event_simulation:
 *A discrete-event simulation (DES) models the operation of a system as a discrete sequence of events 
 in time. Each event occurs at a particular instant in time and marks a change of state in the system. 
 Between consecutive events, no change in the system is assumed to occur; 
 thus the simulation can directly jump in time from one event to the next.*

Why another Simulator?
----------------------
I was looking for a simulator that

* Supports Quick Model generation: Meaning: Modelling shall be doable by non-programmers in an intuitive and easy-to-remember way
* Is suitable to model communication between objects
* Can visualize those communication at least in form of sequence diagrams
* Is open source or at least affordable
* I could not find commercial or open source tools that provided those features.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
