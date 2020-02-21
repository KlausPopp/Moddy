'''
:mod:`simulator` -- Moddy Simulator core
========================================

.. module:: simulator
   :platform: Unix, Windows
   :synopsis: Moddy Simulator Core Routines
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
import sys
import inspect
import os
from heapq import heappush, heappop
from collections import deque
from datetime import datetime

from . import MS, US, NS
from .version import VERSION


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

class SimVariableWatcher(SimBaseElement):
    '''
    The VariableWatcher class watches a variable for changes.
    The variable is referenced by the moddy part and its variable name
    within the part.
    It can be a variable in the part itself or a subobject "obj1.subobj.a"

    The class provides the checkValueChanged() method. In moddy,
    the simulator should call this function
    after each event (or step) to see if the value has changed
    '''

    def __init__(self, sim, part, var_name, format_string):
        '''
        :param sim sim: simulator object
        :param simPart part: part which contains the variable
        :param str varName: Variable name as seen part scope
        :param str formatString: print format like string to format value
        '''
        super().__init__(sim, part, var_name, "WatchedVar")
        self._var_name = var_name
        self._last_value = None
        self._format_string = format_string

    def current_value(self):
        '''return current value of watched var'''
        # pylint: disable=eval-used, bare-except
        try:
            cur_val = eval('self.parent_obj.' + self._var_name)
        except:
            cur_val = None
        return cur_val

    def __str__(self):
        cur_val = self.current_value()
        if cur_val is None:
            ret_val = ''
        else:
            ret_val = self._format_string % (cur_val)
        return ret_val

    def check_value_changed(self):
        '''
        Check if the variable value has changed
        :return: Changed, newVal

        Changed is True if value has changed since last call to
        check_value_changed()
        newVal is returned also if value not changed

        If the variable value cannot be evaluated
        (e.g. because the variable does not exist (anymore))
        the variables value is set to None (no exception is raised)

        '''
        old_val = self._last_value
        cur_val = self.current_value()
        changed = False

        if cur_val != old_val:
            self._last_value = cur_val
            changed = True

        return (changed, cur_val)

    def var_name(self):
        '''
        :return: Name of watched variable
        '''
        return self._var_name


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


class Sim:
    '''Simulator main class'''
    # pylint: disable=too-many-instance-attributes, too-many-public-methods
    def __init__(self):
        self._list_parts = []       # list of all parts
        # a heapq with list of pending events takes pendingEvent objects, sorted by execTime
        self._list_events = []
        self._time = 0.0      # current simulator time
        self._list_in_ports = []
        self._list_out_ports = []
        self._list_timers = []
        self._dis_time_scale = 1        # time scale factor
        self._dis_time_scale_str = "s"     # time scale string
        self._list_traced_events = deque()  # list of all traced events during execution
        self._list_variable_watches = []  # list of watched variables
        # list of monitors (called on each simulator step)
        self._list_monitors = []
        self._enable_trace_prints = True
        self._stop_on_assertion_failure = False
        self._num_assertion_failures = 0
        self._is_running = False
        self._has_run = False
        self._stop_event = None
        self._num_events = 0
        self._start_real_time = None

    #
    # Port Management
    #
    def add_input_port(self, port):
        '''Add input port to simulators list'''
        add_elem_to_list(self._list_in_ports, port, "Simulator input ports")

    def add_output_port(self, port):
        '''Add output port to simulators list'''
        add_elem_to_list(self._list_out_ports, port, "Simulator output ports")

    def check_unbound_ports(self):
        '''
        Check if all ports are connected
        print warnings for unconnected ports
        '''
        for port in self._list_in_ports + self._list_out_ports:
            if not port.is_bound():
                print("SIM: WARNING: Port %s not bound" %
                      (port.hierarchy_name_with_type()))

    def add_timer(self, timer):
        '''Add timer to list of timers'''
        add_elem_to_list(self._list_timers, timer, "Simulator timers")

    def output_ports(self):
        ''' return list of all output ports '''
        return self._list_out_ports

    def find_port_by_name(self, port_hierarchy_name):
        '''
        Find a port (input or output or IO) by its hierarchy name
        :param str port_hierarchy_name: e.g. \
            "part1.ioPort1" or "part1.ioPort1.inPort"
        :return port: the found port
        :raises ValueError: if port not found
        '''
        for part in self._list_parts:
            for port in part._listPorts:
                #print("findPortByName %s %s" % (port.hierarchy_name(),
                # port._typeStr ))
                if port.hierarchy_name() == port_hierarchy_name:
                    return port

                if port._typeStr == "IOPort":
                    if port._in_port.hierarchy_name() == port_hierarchy_name:
                        return port._in_port
                    if port._out_port.hierarchy_name() == port_hierarchy_name:
                        return port._out_port

        raise ValueError("Port not found %s" % port_hierarchy_name)

    #
    # Part management
    #
    def add_part(self, part):
        '''Add part to simulators part list'''
        add_elem_to_list(self._list_parts, part, "Simulator Parts")

    def top_level_parts(self):
        ''' get list of top level parts '''
        tl_parts = []
        for part in self._list_parts:
            if part.parent_obj is None:
                tl_parts.append(part)
        return tl_parts

    def find_part_by_name(self, part_hierarchy_name):
        '''
        Find a part by its hierarchy name
        :param string part_hierarchy_name: e.g. "part1.subpart.subsubpart"
        :return simPart part: the found part
        :raises ValueError: if part not found
        '''
        for part in self._list_parts:
            if part.hierarchy_name() == part_hierarchy_name:
                return part
        raise ValueError("Part not found %s" % part_hierarchy_name)

    #
    # Variable watching
    #
    def add_var_watcher(self, var_watcher):
        '''Add watcher to simulators watcher list'''
        add_elem_to_list(self._list_variable_watches, var_watcher,
                         "Simulator Watcher")

    def watch_variables(self):
        '''
        Check all registered variables for changes.
        Generate a trace event for all changed variables
        '''
        for var_watcher in self._list_variable_watches:
            changed, _ = var_watcher.checkValueChanged()
            if changed:
                new_val_str = var_watcher.__str__()
                trace_ev = SimTraceEvent(var_watcher.parent_obj,
                                         var_watcher, new_val_str, 'VC')
                self.add_trace_event(trace_ev)

    def watch_variables_current_value(self):
        '''
        Generate a trace event for all watched variables with their
        current value.
        Used at start of simulator to report the initial values
        '''
        for var_watcher in self._list_variable_watches:
            trace_ev = SimTraceEvent(var_watcher.parent_obj,
                                     var_watcher, var_watcher.__str__(), 'VC')
            self.add_trace_event(trace_ev)

    def find_watched_variable_by_name(self, variable_hierarchy_name):
        '''
        Find a watched variable by its hierarchy name
        :param str variable_hierarchy_name: e.g. "part1.variable"
        :return SimVariableWatcher: the found variable watcher
        :raises ValueError: if variable not found
        '''
        for var_watcher in self._list_variable_watches:
            if var_watcher.hierarchy_name() == variable_hierarchy_name:
                return var_watcher
        raise ValueError("Watched Variable not found %s" %
                         variable_hierarchy_name)

    #
    # Model Assertions
    #
    def assertion_failed(self, part, assertion_str, frame_idx=1):
        '''
        Add an assertion failure trace event.
        Increment global assertion failure counter.
        Stop simulator if configured so.

        :param simPart part: the related simPart. None if global assertion
        :param string assertion_str: error message to display
        :param int frame_idx: traceback frame index \
            (1 if caller's frame, 2 if caller-caller's frame...)
        '''
        _, file_name, line_number, function_name, _, _ = \
            inspect.stack()[frame_idx]

        te_str = "%s: in %s, (%s::%d)" % (assertion_str, function_name,
                                          os.path.basename(file_name),
                                          line_number)
        trace_ev = SimTraceEvent(part, part, te_str, 'ASSFAIL')
        self.add_trace_event(trace_ev)
        self._num_assertion_failures += 1

    #
    # Monitoring
    #
    def add_monitor(self, monitor_func):
        '''
        Register a function to be called at each simulator step.
        Usually used by monitors or stimulation routines

        :param monitor_func: function to call. Gets called with no arguments
        '''
        self._list_monitors.append(monitor_func)

    def delete_monitor(self, monitor_func):
        '''
        Delete a monitor function that has been registered with 'addMonitor'
        before

        :param monitor_func: function to delete
        :raises ValueError: if monitorFunc is not registered
        '''
        self._list_monitors.remove(monitor_func)

    def call_monitors(self):
        ''' Run all monitors '''
        for monitor_func in self._list_monitors:
            monitor_func()

    #
    # Simulator core routines
    #

    def time(self):
        ''' Return current simulation time '''
        return self._time

    def schedule_event(self, event):
        # TODO add members to SimBaseEvent
        '''schedule a new event for execution.
        Event must have members
        - exec_time
        - cancelled
        - execute()
        - __lt__()
        '''
        heappush(self._list_events, event)

    def cancel_event(self, event):
        '''Cancel an already scheduled event'''
        event._cancelled = True

    def stop(self):
        ''' stop simulator '''
        self._is_running = False
        elapsed_time = datetime.now() - self._start_real_time
        for part in self._list_parts:
            part.terminate_sim()
        print("SIM: Simulator stopped at", self.time_str(self._time) +
              ". Executed %d events in %.3f seconds" %
              (self._num_events, elapsed_time.total_seconds()))
        self.print_assertion_failures()

    def run(self,
            stop_time,
            max_events=100000,
            enable_trace_printing=True,
            stop_on_assertion_failure=True):
        '''

        run the simulator until

            - stop_time reached
            - no more events to execute
            - max_events reached
            - model called assertionFailed() and stop_on_assertion_failure
              ==True
            - a model exception (including exceptions from vThreads)
              has been caught

        :param float stop_time: simulation time at which the simulator \
            shall stop latest
        :param int maxEvents: (default: 100000) maximum number of simulator \
            events to process. Can be set to None for infinite events
        :param bool enable_trace_printing: (default: True) if set to False, \
            simulator will not display events as they are executing
        :param bool stop_on_assertion_failure: (default: True) if set to \
            False, don't stop when model calls assertionFailed().
            Just print info at end of simulation
        :raise: exceptions coming from model or simulator

        '''
        self._enable_trace_prints = enable_trace_printing
        self._stop_on_assertion_failure = stop_on_assertion_failure

        if self._has_run:
            print("SIM: run() can be called only once", file=sys.stderr)
            return

        self.check_unbound_ports()
        print("SIM: Simulator %s starting" % (VERSION))
        self._start_real_time = datetime.now()

        # create stop event that fires at stop time
        self._stop_event = SimEvent()
        self._stop_event.exec_time = stop_time
        self.schedule_event(self._stop_event)

        self._is_running = True
        self._has_run = True
        # report initial value of watched variables
        self.watch_variables_current_value()
        for part in self._list_parts:
            part.start_sim()
        # Check for changed variables
        self.watch_variables()

        self._num_events = 0

        try:
            while True:
                if not self._list_events:
                    print("SIM: Simulator has no more events")
                    break   # no more events, stop

                # get next event to execute
                # heap is a priority queue. heappop extracts the event with
                # the smallest execution time
                event = heappop(self._list_events)
                if event._cancelled:
                    continue

                self._num_events += 1
                assert(self._time <= event.exec_time), "time can't go backward"
                self._time = event.exec_time

                if event == self._stop_event:
                    print("SIM: Stops because stopTime reached")
                    break

                #print("SIM: Exec event", event, self._time)
                try:
                    # Catch model exceptions
                    event.execute()
                except:
                    print("SIM: Caught exception while executing event %s" %
                          event, file=sys.stderr)
                    # re-raise model exception
                    raise
                # Check for changed variables
                self.watch_variables()
                # Call monitors
                self.call_monitors()

                if max_events is not None and self._num_events >= max_events:
                    print(
                        "SIM: Simulator has got too many events "
                        "(pass a higher number to run(maxEvents=n)")
                    break

                if self._stop_on_assertion_failure and \
                   self._num_assertion_failures > 0:
                    print("SIM: Stops due to Assertion Failure")
                    break
        finally:
            self.stop()

    def is_running(self):
        ''' Return if simulator is running '''
        return self._is_running

    #
    # Tracing and display routines
    #
    def add_trace_event(self, trace_ev):
        ''' Add new event to Trace list, timestamp it, print it'''
        trace_ev.traceTime = self._time
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

    def print_assertion_failures(self):
        '''Print all traced assertion failures to stderr'''
        if self._num_assertion_failures > 0:
            print("%d Assertion failures during simulation" %
                  self._num_assertion_failures, file=sys.stderr)
            for trace_ev in self._list_traced_events:
                if trace_ev.action == "ASSFAIL":
                    print("%10s: %s: %s" % (self.time_str(trace_ev.traceTime),
                                            trace_ev.part,
                                            trace_ev.trans_val.__str__()),
                          file=sys.stderr)

    def smart_bind(self, bindings):
        '''
        Create many port bindings at once using simple lists.

        Example:

        .. code-block:: python

            simu.smartBind( [
                ['App.outPort1', 'Dev1.inPort', 'Dev2.inPort'],
                ['App.ioPort1', 'Server.netPort' ]  ])

        :param list bindings: Each list element must be a list of strings, \
            which specifies ports that shall be \
            connected to each other. \
            The strings must specify the hierarchy names of the ports.

        '''

        for binding in bindings:
            self._single_smart_bind(binding)

    def _single_smart_bind(self, binding):
        # determine output and input ports
        out_ports = []
        in_ports = []

        for port_name in binding:
            port = self.find_port_by_name(port_name)
            if port._type_str == "OutPort":
                out_ports.append(port)
            elif port._type_str == "IOPort":
                out_ports.append(port._out_port)
                in_ports.append(port._in_port)
            elif port._type_str == "InPort":
                in_ports.append(port)

        # bind all output ports to all input ports
        for out_port in out_ports:
            for in_port in in_ports:
                if out_port._io_port is None or \
                    (out_port._io_port != in_port._io_port):

                    out_port.bind(in_port)
