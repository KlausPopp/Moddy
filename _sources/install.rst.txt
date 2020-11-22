.. include:: globals.rst

.. _install:


*********************************************
Installation
*********************************************

Install Python
==============

Download & Install Python from https://www.python.org/downloads/

Please install python Version >=3.5. 

.. warning:: Moddy does not support Python 2.x.

During install, click checkbox ``add python to PATH``

Tested with python 3.5, 3.6 and 3.7 under Windows 10.

Installing GraphViz
===================

Install GraphViz from http://www.graphviz.org/Download.php

Then ensure that the ``bin/`` subdirectory of the GraphViz installation is in your ``PATH``.

Install Moddy
==============

.. code-block:: console

	$ pip install -U moddy
	

Test Moddy
==========

Copy the text from :download:`this Basic Demo <tutorials/code/1_hello.py>` and save it to ``1_hello.py`` 
into an arbitrary directory on your machine.

Then try to run the demo:

.. code-block:: console

	$ python 1_hello.py
	
.. _hello-output: 

Demo output
------------
	
The console log should end with

.. code-block:: console

	TRC:      11.8s STA     Bob(Part) // 
	TRC:      11.8s >MSG    Bob.mouth(OutPort) //  req=11.8s beg=11.8s end=12.8s dur=1.0s msg=[Hm?]
	SIM: Stops because stop_time reached
	SIM: Simulator stopped at 12.0s. Executed 9 events in 0.000 seconds
	saved sequence diagram in output/1_hello.html as iaViewer
	Saved structure graph to output/1_hello_structure.svg
	saved output/1_hello.csv as CSV
	

You should also find a folder ``output`` in your directory that contains the result files:	

.. code-block:: console

	|   1_hello.py
	|
	+---output
	        1_hello.csv
	        1_hello.html
	        1_hello_structure.svg
	
Open ``1_hello.html`` into a web browser and it should look like this 
:download:`The sequence diagram <tutorials/code/output/1_hello.html>`



Using Moddy with Eclipse
========================

.. note:: 
	
	This step is optional, you can use Moddy also without Eclipse. I just put it here because
	I personally use Eclipse.
 
 
Installing Eclipse
------------------

Download & Install Eclipse from https://eclipse.org/downloads/

Installing PyDev
----------------

In Eclipse, select ``Help->Install new Software`` and enter http://www.pydev.org/updates for both Name and location

 
.. figure:: _static/0500_pydev.png 
 
Create a Moddy Project
----------------------

In Eclipse Select ``New --> Project --> PyDev Project``:

 
.. figure:: _static/0510_eclipse_new.png 
 
Name the project ``myFirstModdyProject``:

.. figure:: _static/0520_pydev.png

 
Create a module named ``1_hello.py``:
 

.. figure:: _static/0530_createmod.png

Copy the text from :download:`this Basic Demo <tutorials/code/1_hello.py>` and paste it into ``1_hello.py``.

Now you can ``Run`` the ``1_hello.py``. You should get an output as described in :ref:`hello-output`.  



 

