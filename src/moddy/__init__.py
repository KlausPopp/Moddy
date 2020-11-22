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
from .constants import *  # noqa: F403, F401

# import moddy global api
from .sim_core import Sim  # noqa: F401
from .sim_part import SimPart  # noqa: F401

from .vthread import VThread  # noqa: F401
from .vt_sched_rtos import VtSchedRtos, VSimpleProg  # noqa: F401

from .fsm import Fsm  # noqa: F401
from moddy.fsm_part import SimFsmPart  # noqa: F401

from moddy.interactive_sequence_diagram import (  # noqa: F401
    gen_interactive_sequence_diagram,  # noqa: F401
)
from moddy.trace_to_csv import gen_trace_table  # noqa: F401
from moddy.dot_structure import gen_dot_structure_graph  # noqa: F401

from moddy.dot_fsm import gen_fsm_graph  # noqa: F401

AUTHOR_NAME = "Klaus Popp"
AUTHOR_EMAIL = "klauspopp@gmx.de"
CYEAR = "2020"
