'''
:mod:`sim_base` -- Simulator Base Classes
========================================

.. module:: sim_base
   :synopsis: Simulator base classes and functions
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''

from . import MS, US, NS


def time_unit_to_factor(unit):
    '''Convert time unit to factor'''
    if unit == "s":
        factor = 1.0
    elif unit == "ms":
        factor = MS
    elif unit == "us":
        factor = US
    elif unit == "ns":
        factor = NS
    else:
        assert(False), "Illegal time unit " + unit
    return factor


def add_elem_to_list(lst, elem, list_name):
    '''
    Add elem to lst
    :lst list: list to add element to
    :elem: element to add to list
    :list_name str: list name to add to exception
    :raise: RuntimeError if elem already in list
    '''
    if elem in lst:
        raise RuntimeError("element %s already in %s" % (elem, list_name))
    lst.append(elem)


class SimBaseElement:
    '''
    Moddy simulator base class
    Base class for parts, ports, ...

    :param sim: Simulator instance
    :param parent_obj: parent part. None if part has no parent.
    :param obj_name: part's name
    :param type_str: type of object as a string
    '''

    def __init__(self, sim, parent_obj, obj_name, type_str):
        self._sim = sim
        self.parent_obj = parent_obj
        self._obj_name = obj_name
        self.type_str = type_str

    def hierarchy_name(self):
        '''
        Return the element name within the hierarchy.
        E.g. Top.Lower.myName
        '''
        if self.parent_obj is None:
            return self._obj_name
        return self.parent_obj.hierarchy_name() + "." + self._obj_name

    def hierarchy_name_with_type(self):
        '''
        Return the element name within the hierarch including the element type
        E.g. "Top.Lower.myName (Inport)"
        '''
        return self.hierarchy_name() + "(" + self.type_str + ")"

    def obj_name(self):
        '''
        :return string: object name (without hierarchy)
        '''
        return self._obj_name

    def __repr__(self):
        return self.hierarchy_name_with_type()

    def __str__(self):
        return self.hierarchy_name()


class SimEvent():
    '''
    Base class of all simulator events
    '''
    def __init__(self):
        self._cancelled = False
        self.exec_time = None

    def __lt__(self, other):
        return self.exec_time < other.exec_time

    def execute(self):
        '''Execute the event'''

class SimTraceEvent:
    '''
    simTraceEvents are the objects that are added to the simulators trace
    buffer
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self, part, sub_obj, tv, act):
        self.trace_time = -1  # when the event occurred
        self.part = part      # generating part
        self.sub_obj = sub_obj# timer or port
        self.trans_val = tv   # Transport value (e.g. message)
        self.action = act     # action string

    def __repr__(self):
        trace_str = "%-8s" % (self.action)
        if self.sub_obj is not None:
            trace_str += self.sub_obj.hierarchy_name_with_type()
        if self.trans_val is not None:
            trace_str += " // %s" % self.trans_val.__str__()
        return trace_str


