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


TODOS (FEATURE AND IMPROVEMENT LIST)
#003 Catch model exceptions, allow result output until exception
#013 add SamplingIO and QueingIO ports
#004 BlockDiagrams: Show scheduler and scheduled threads
#005 BlockDiagrams: Show message types on bindings (learn which messages are sent on outPort)
#011 SeqDiagram: Group the objects (e.g. message arrow)
#006 Show scheduler events in event trace
#009 Add waveform output (.vcf)

DONE 
#012 SeqDiagram: Do not modify simulator objects
#002 Create sequence diagrams via single function call
#010 Allow user to suppress trace prints during simulation   
#001 Allow colored messages a) via output port b) via messages
"""



version = (0, 9, 3)  
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
from moddy.vtSchedRtos import vtSchedRtos

from moddy.svgSeqD import moddyGenerateSequenceDiagram
from moddy.traceToCsv import moddyGenerateTraceTable
from moddy.dotStructure import moddyGenerateStructureGraph
