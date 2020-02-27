#!/usr/bin/env python
# coding:utf-8
# Author:  Klaus Popp
# Purpose: package definition file
# Created: 2016-12-26
# License: LGPLv3
# Copyright (C) 2016-2019 Klaus Popp (klauspopp@gmx.de)

"""
Moddy is a discrete event simulator to model and analyze the timing behavior
of systems consisting of objects (called PARTS in moddy) that communicate
via messages.

Moddy was written to analyze complex systems in the concept phase to
validate the suitability of the concept.
"""
from .constants import *

# import moddy global api
from .sim_core import Sim
from .sim_part import SimPart

from .vthread import VThread
from .vt_sched_rtos import VtSchedRtos, VSimpleProg

from .fsm import Fsm
from moddy.fsm_part import SimFsmPart

from moddy.interactive_sequence_diagram import gen_interactive_sequence_diagram
from moddy.trace_to_csv import generate_trace_table
from moddy.dot_structure import gen_dot_structure_graph

from moddy.dot_fsm import moddyGenerateFsmGraph

AUTHOR_NAME = 'Klaus Popp'
AUTHOR_EMAIL = 'klauspopp@gmx.de'
CYEAR = '2020'

