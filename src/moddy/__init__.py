#!/usr/bin/env python
#coding:utf-8
# Author:  Klaus Popp
# Purpose: package definition file
# Created: 2016-12-26
# License: LGPLv3
# Copyright (C) 2016-2017 Klaus Popp (klauspopp@gmx.de)

"""
Moddy is a discrete event simulator to model and analyze the timing behavior of systems consisting of 
objects (called PARTS in moddy) that communicate via messages.

Moddy was written to analyze complex systems in the concept phase to validate the suitability of the concept.


"""



version = (1, 2, 0)  
VERSION = '%d.%d.%d' % version

AUTHOR_NAME = 'Klaus Popp'
AUTHOR_EMAIL = 'klauspopp@gmx.de'
CYEAR = '2017'

ns = 1E-9
us = 1E-6
ms = 1E-3

# import moddy global api
from moddy.simulator import sim,simPart

from moddy.vthread import vThread
from moddy.vtSchedRtos import vtSchedRtos,vSimpleProg

from moddy.fsm import Fsm
from moddy.fsmPart import simFsmPart

from moddy.svgSeqD import moddyGenerateSequenceDiagram
from moddy.traceToCsv import moddyGenerateTraceTable
from moddy.dotStructure import moddyGenerateStructureGraph

from moddy.dotFsm import moddyGenerateFsmGraph
