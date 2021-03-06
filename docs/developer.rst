.. include:: globals.rst

.. _developer:


*******************
Developer Guide
*******************

Running Test Suite
==================

``tests`` subdirectory contains a number of tests for the moddy simulator.

To run all tests: 

.. code-block:: console

	cd tests
	python -m unittest


Updating the docs
==================

The ``docs`` subdirectory contains the source files for the sphinx documentation.

First, ensure you have installed sphinx: https://www.sphinx-doc.org/en/master/usage/installation.html

To update the docs, create a new directory ``moddy-docs`` in parallel to the directory 
where you checked out moddy master branch.


.. code-block:: console

	mkdir moddy-docs
	cd moddy-docs
	git clone -b gh-pages https://github.com/KlausPopp/Moddy.git html

Then you should have a directory structure like this.

.. code-block:: console

	moddy					directory where you checked out moddy master branch
		docs
		src
			moddy
			tutorial
		tests

	moddy-docs				directory where you checked out moddy gh-pages branch
		html
		
Then, go to ``moddy/docs`` and run:


.. code-block:: console

	cd ../moddy/docs
	make html
	
This updates the ``moddy-docs/html`` content.

When you commit and push ``moddy-docs/html`` back, you'll should see the update on https://klauspopp.github.io/Moddy

Creating PDF
------------

Requires a latex installation. For windows, I used https://miktex.org/download


.. code-block:: console

	cd ../moddy/docs
	make latex
	
	cd ../../moddy-docs/latex
	pdflatex ModdyDiscreteEventSimulator.tex
	
I had to run pdflatex twice to resolve references.

This creates ``ModdyDiscreteEventSimulator.pdf``.


	



