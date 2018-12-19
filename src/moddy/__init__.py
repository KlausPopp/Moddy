#!/usr/bin/env python
#coding:utf-8
# Author:  Klaus Popp
# Purpose: package definition file
# Created: 2016-12-26
# License: LGPLv3
# Copyright (C) 2016-2019 Klaus Popp (klauspopp@gmx.de)

"""
Moddy is a discrete event simulator to model and analyze the timing behavior of systems consisting of 
objects (called PARTS in moddy) that communicate via messages.

Moddy was written to analyze complex systems in the concept phase to validate the suitability of the concept.


"""



version = (1, 5, 0)  
VERSION = '%d.%d.%d' % version

AUTHOR_NAME = 'Klaus Popp'
AUTHOR_EMAIL = 'klauspopp@gmx.de'
CYEAR = '2017'

# Time factors
ns = 1E-9
us = 1E-6
ms = 1E-3

# Commonly used status box appearance colors
bcWhiteOnGreen = {'boxStrokeColor':'black', 'boxFillColor':'green', 'textColor':'white'}
bcWhiteOnRed = {'boxStrokeColor':'black', 'boxFillColor':'red', 'textColor':'white'}
bcWhiteOnBlue = {'boxStrokeColor':'blue', 'boxFillColor':'blue', 'textColor':'white'}
bcWhiteOnBrown = {'boxStrokeColor':'brown', 'boxFillColor':'brown', 'textColor':'white'}
bcWhiteOnBlack = {'boxStrokeColor':'black', 'boxFillColor':'black', 'textColor':'white'}
bcBlackOnPink = {'boxStrokeColor':'pink', 'boxFillColor':'pink', 'textColor':'black'}
bcBlackOnGrey = {'boxStrokeColor':'grey', 'boxFillColor':'grey', 'textColor':'black'}
bcWhiteOnGrey = {'boxStrokeColor':'grey', 'boxFillColor':'grey', 'textColor':'white'}
bcBlackOnWhite = {'boxStrokeColor':'black', 'boxFillColor':'white', 'textColor':'black'}


# import moddy global api
from moddy.simulator import sim,simPart

from moddy.vthread import vThread
from moddy.vtSchedRtos import vtSchedRtos,vSimpleProg

from moddy.fsm import Fsm
from moddy.fsmPart import simFsmPart

from moddy.seqDiagInteractiveGen import moddyGenerateSequenceDiagram
from moddy.traceToCsv import moddyGenerateTraceTable
from moddy.dotStructure import moddyGenerateStructureGraph

from moddy.dotFsm import moddyGenerateFsmGraph
