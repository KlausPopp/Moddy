.. include:: globals.rst

.. _install:


*********************************************
Installation
*********************************************

Tested with python 3.5.2 and 3.6 under Windows 10, Eclipse Neon/pyDev.

Required libraries: 

	* svgwrite https://pypi.python.org/pypi/svgwrite , tested with svgwrite 1.1.9

Required tools: 
	* GraphViz, tested with Version 2.38
	 
Installing Eclipse
==================

Download & Install Eclipse from https://eclipse.org/downloads/

Install Python
==============

Download & Install Python from https://www.python.org/downloads/

Please install python Version >=3.5. 

.. warning:: Moddy does not support Python 2.x.

During install, click checkbox ``add python to PATH``

Installing PyDev
================

In Eclipse, select ``Help->Install new Software`` and enter http://www.pydev.org/updates for both Name and location

 
.. figure:: _static/0500_pydev.png 
 
 
Select ``pyDev`` and follow the installation instructions.

Installing svgwrite
===================

Open Windows command line.
From the command line, call


.. code-block:: console

	pip install svgwrite

Installing GraphViz
===================

Install GraphViz from http://www.graphviz.org/Download.php

Then ensure that the ``bin/`` subdirectory of the GraphViz installation is in your ``PATH``.

Installing moddy
================

Clone moddy from GitHub. 

Let's assume you want to clone into an eclipse project called ``mymoddy``.
 
Change into the eclipse workspace path:

.. code-block:: console

	# D:
	# cd D:\owncloud\documents\Klaus\eclipse

Clone moddy into ``mymoddy`` subdirectory


.. code-block:: console

	# git clone https://github.com/KlausPopp/Moddy.git mymoddy

From eclipse, select ``File->New->PyDev Project``.

Choose a the project name according to the directory where you cloned moddy to (here:``mymoddy``).

Select PyDev - Interpreter = 3.x (according to your phyton version)

Select "Create ``src`` folder and add it to the ``PYTHONPATH``:
 
 
.. figure:: _static/0510_eclipsemoddy.png 
 

In eclipse, try to run the tutorial:

Right click in Package Explorer to ``moddy/src/tutorial/1_hello.py``. 

Select "Run As"->"Python Run"

The console log should end with

.. code-block:: console

	Drawing ANN events
	saved 1_hello.html as svgInHtml
	Saved structure graph to 1_hello_structure.svg
	saved 1_hello.csv as CSV

If you want to update Moddy, go into the directory where you have Moddy cloned to and execute:

.. code-block:: console

	# git pull
