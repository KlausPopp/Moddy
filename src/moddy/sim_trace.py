'''
:mod:`sim_trace` -- Simulator Tracing
========================================

.. module:: sim_trace
   :synopsis: Moddy Simulator Tracing Support
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
import sys
from collections import deque

from .sim_base import time_unit_to_factor


class SimTraceEvent:
    '''
    simTraceEvents are the objects that are added to the simulators trace
    buffer
    '''

    # pylint: disable=too-few-public-methods
    def __init__(self, part, sub_obj, tv, act):
        self.trace_time = -1  # when the event occurred
        self.part = part  # generating part
        self.sub_obj = sub_obj  # timer or port
        self.trans_val = tv  # Transport value (e.g. message)
        self.action = act  # action string

    def __repr__(self):
        trace_str = "%-8s" % (self.action)
        if self.sub_obj is not None:
            trace_str += self.sub_obj.hierarchy_name_with_type()
        if self.trans_val is not None:
            trace_str += " // %s" % self.trans_val.__str__()
        return trace_str


class SimTracing:
    '''
    Simulator Tracing and logging
    '''

    def __init__(self):
        # list of all traced events during execution
        self._list_traced_events = deque()
        self._dis_time_scale = 1  # time scale factor
        self._dis_time_scale_str = "s"  # time scale string
        self._enable_trace_prints = False
        self._time_func = None

    def enable_trace_prints(self, enable_prints):
        ''' enable/disable trace prints '''
        self._enable_trace_prints = enable_prints

    def set_time_func(self, time_func):
        ''' set the function to retrieve current simulation time '''
        self._time_func = time_func

    def add_trace_event(self, trace_ev):
        ''' Add new event to Trace list, timestamp it, print it'''
        trace_ev.traceTime = self._time_func()
        self._list_traced_events.append(trace_ev)

        if self._enable_trace_prints:
            trace_str = "TRC: %10s %s" % (self.time_str(trace_ev.traceTime),
                                          trace_ev)
            print(trace_str)

    def traced_events(self):
        ''' return list of traced events'''
        return self._list_traced_events

    def annotation(self, part, text):
        '''
        User routine to add an annotation to a life line at the
        current simulation time
        '''
        trace_ev = SimTraceEvent(part, part, text, 'ANN')
        self.add_trace_event(trace_ev)

    class StateIndTransVal:
        '''
        class to hold the text and appearance of a state indicator
        '''

        # pylint: disable=too-few-public-methods
        def __init__(self, text, appearance):
            self.text = text
            self.appearance = appearance

        def __str__(self):
            return self.text

    def set_state_indicator(self, part, text, appearance=None):
        '''
        User routine to indicate the current state of a part.
        Can be also used to indicate
        UML execution specification to a life line
        at the current simulation time.
        An empty text flags 'no state' which removes the indication from the
        life line

        :param SimPart part: affected part
        :param str text: text to display (Empty string to clear indicator)
        :param dict appearance: (default: {}) colors for indicator
        '''
        trace_ev = SimTraceEvent(
            part, part, self.StateIndTransVal(text, appearance), 'STA')
        self.add_trace_event(trace_ev)

    def set_display_time_unit(self, unit):
        '''
        Define how the simulator prints/displays time units

        :param str unit: can be "s", "ms", "us", "ns"

        '''
        self._dis_time_scale_str = unit
        self._dis_time_scale = time_unit_to_factor(unit)

    def time_str(self, time):
        '''
        return a formatted time string of *time* based on the display scale
        '''
        tmfmt = "%.1f" % (time / self._dis_time_scale)
        return tmfmt + self._dis_time_scale_str
