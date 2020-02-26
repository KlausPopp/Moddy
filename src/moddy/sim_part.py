'''
:mod:`sim_part` -- Moddy Simulator Parts
========================================

.. module:: sim_part
   :platform: Unix, Windows
   :synopsis: Moddy Simulator Part Class
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
from .sim_base import SimBaseElement, add_elem_to_list
from .sim_var_watch import SimVariableWatcher
from .sim_ports import SimInputPort, SimOutputPort, SimIOPort, SimTimer


class SimPart(SimBaseElement):
    '''an instance of SimPart forms a moddy object

    :param sim: Simulator instance
    :param objName: part's name
    :param parentObj: parent part. None if part has no parent. Defaults to None
    :param dict elems: A dictionary with elements (ports and timers) to \
     create, \
    e.g. ``{ 'in': 'inPort1', 'out': ['outPort1', 'outPort2'], 'tmr' :
      'timer1' }``
    '''

    def __init__(self, sim, obj_name, parent_obj=None, elems=None):
        super().__init__(sim, parent_obj, obj_name, "Part")
        self._list_ports = []
        self._list_timers = []
        self._list_subparts = []  # child parts list
        self._list_var_watchers = []
        self._state_ind = None

        if parent_obj is not None:
            parent_obj.add_sub_part(self)
        else:
            if sim is not None:
                sim.parts_mgr.add_top_level_part(self)

        if elems is not None:
            self.create_elements(elems)

    def add_sub_part(self, sub_part):
        '''
        add subPart to list of subParts
        :param simPart: part to add
        :raise: RuntimeError If subPart already in this part
        '''
        add_elem_to_list(self._list_subparts, sub_part, self.__str__() +
                         ":subparts")

    def sub_parts(self):
        ''' return list of child parts '''
        return self._list_subparts

    def ports(self):
        ''' return all ports of that part '''
        return self._list_ports

    def annotation(self, text):
        '''Add annotation from model at current simulation time'''
        self._sim.tracing.annotation(self, text)

    def assertion_failed(self, assertion_str, frame_idx=1):
        '''
        Add an assertion failure trace event
        Increment simulator global assertion failure counter
        Stop simulator if configured so

        :param assertionStr: error message to display
        :param frameIdx: traceback frame index \
            (1 if caller's frame, 2 if caller-caller's frame...)
        '''
        self._sim.tracing.assertion_failed(self, assertion_str, frame_idx + 1)

    def set_state_indicator(self, text, appearance=None):
        '''set part's state from model at simulation time

        :param text: text to show in life line
        :param dict appearance: appearance of state indicator. \
        Dictionary with color values, e.g. \
        ``{'boxStrokeColor':'black', 'boxFillColor':'green', \
            'textColor':'white'}``
        '''
        self._state_ind = text
        self._sim.tracing.set_state_indicator(self, text, appearance)

    def new_input_port(self, name, msg_received_func):
        '''
        Add a new input port to the part

        :param name: name of port
        :param msgReceivedFunc: callback function to call for message \
            receiption. Signature ``func(port, msg)``

        '''
        port = SimInputPort(self._sim, self, name, msg_received_func)
        self.add_port(port)
        return port

    def new_output_port(self, name):
        '''
        Add a new output port to the part

        :param name: name of port
        '''
        port = SimOutputPort(self._sim, self, name)
        self.add_port(port)
        return port

    def new_io_port(self, name, msg_received_func):
        '''
        Add a new "I/O" port to the part

        :param name: name of port
        :param msg_received_func: callback function to call for message \
            receiption. Signature ``func(port, msg)``

        '''
        port = SimIOPort(self._sim, self, name, msg_received_func)
        self.add_port(port)
        return port

    def new_timer(self, name, elapsed_func):
        '''
        Add a new timer to the part

        :param name: name of timer
        :param elapsed_func: callback function to call for timer expiry. \
            Signature ``func(timer)``

        '''
        timer = SimTimer(self._sim, self, name, elapsed_func)
        self.add_timer(timer)
        return timer

    def new_var_watcher(self, var_name, format_string):
        '''
        Add a variable to the watched variables.
        A watched variables value will be checked for changes during
        simulation.
        If a value change is detected, a simulator trace event is generated.

        :param string var_name: Variable name as seen from part's scope
        :param string format_string: print() like format to format \
            the value when traced
        '''
        watcher = SimVariableWatcher(self._sim, self, var_name, format_string)
        self.add_var_watcher(watcher)
        return watcher

    def add_port(self, port):
        '''
        Add a port to this part
        :param port: port to add
        :raise: RuntimeError If port already in this part
        '''
        add_elem_to_list(self._list_ports, port, self.__str__() + ":ports")

    def add_timer(self, timer):
        '''
        Add a timer port to this part

        :param timer: timer to add
        :raise: RuntimeError If timer already in this part
        '''
        add_elem_to_list(self._list_timers, timer, self.__str__() + ":timers")

    def add_var_watcher(self, var_watcher):
        '''
        Add a variable watcher to this part and to simulator

        :param var_watcher: watcher to add
        :raise: RuntimeError If watcher already in this part
        '''
        add_elem_to_list(self._list_var_watchers, var_watcher,
                         self.__str__() + ":var_watchers")
        self._sim.var_watch_mgr.add_var_watcher(var_watcher)

    def create_ports(self, ptype, list_port_names):
        '''
        Convinience functions to create multiple ports at once.

        :param ptype: Type of ports, must be one of 'in', 'out' or 'io'
        :param list list_port_names: list of port names to create
        :raise: ValueError if unknown port type

        The function creates for each port a member variable with this
        name in the part.
        For "in" and "io" ports, a receive function *<portName>_recv*
        must be provided by caller

        '''
        if ptype == 'in':
            for port_name in list_port_names:
                setattr(self, port_name, self.new_input_port(
                    port_name, getattr(self, "%s_recv" % port_name)))
        elif ptype == 'out':
            for port_name in list_port_names:
                setattr(self, port_name, self.new_output_port(port_name))
        elif ptype == 'io':
            for port_name in list_port_names:
                setattr(self, port_name, self.new_io_port(
                    port_name, getattr(self, "%s_recv" % port_name)))
        else:
            raise ValueError("Unknown port type %s" % ptype)

    def create_timers(self, list_timer_names):
        '''
        Convinience functions to create multiple timers at once.

        :param list list_timer_names: list of timer names to create

        The function creates for each port a member variable with this name
        in the part.
        A timer callback function *<tmrName>_expired* must be provided
        by caller
        '''
        for tmr_name in list_timer_names:
            setattr(self, tmr_name, self.new_timer(
                tmr_name, getattr(self, "%s_expired" % tmr_name)))

    def create_elements(self, elems):
        '''
        Create ports and timers based on a dictionary.

        :param dict elems: A dictionary with elements (ports and timers) \
            to create, \
        e.g. ``{ 'in': 'inPort1', 'out': ['outPort1', 'outPort2'], 'tmr' : \
            'timer1' }``
        '''

        for el_type, names in elems.items():
            if isinstance(names, str):
                names = [names]  # make a list if only a string is given

            if el_type == 'tmr':
                self.create_timers(names)
            else:
                self.create_ports(el_type, names)

    def start_sim(self):
        '''Called from simulator when simulation begins'''

    def terminate_sim(self):
        '''
        Called from simulator when simulation stops. Terminate block
        (e.g. stop threads)
        '''

    def time(self):
        '''Get current simulation time'''
        return self._sim.time()
