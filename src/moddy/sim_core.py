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

from .version import VERSION
from .sim_base import SimEvent
from .sim_base import add_elem_to_list, time_unit_to_factor
from .sim_parts_mgr import SimPartsManager
from .sim_trace import SimTraceEvent, SimTracing


class Sim:
    '''Simulator main class'''

    def __init__(self):
        self.parts_mgr = SimPartsManager()
        self.tracing = SimTracing()
        self.tracing.set_time_func(self.time)
        # a heapq with list of pending events takes pendingEvent objects, sorted by execTime
        self._list_events = []
        self._time = 0.0  # current simulator time
        self._list_variable_watches = []  # list of watched variables
        # list of monitors (called on each simulator step)
        self._list_monitors = []
        self._stop_on_assertion_failure = False
        self._num_assertion_failures = 0
        self._is_running = False
        self._has_run = False
        self._stop_event = None
        self._num_events = 0
        self._start_real_time = None

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
        self._terminate_all_parts()
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
        self.tracing.enable_trace_prints(enable_trace_printing)
        self._stop_on_assertion_failure = stop_on_assertion_failure

        if self._has_run:
            print("SIM: run() can be called only once", file=sys.stderr)
            return

        self.parts_mgr.check_unbound_ports()
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
        self._start_all_parts()
        # Check for changed variables
        self.watch_variables()

        self._num_events = 0

        try:
            while True:
                if not self._list_events:
                    print("SIM: Simulator has no more events")
                    break  # no more events, stop

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

                # print("SIM: Exec event", event, self._time)
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

    def _start_all_parts(self):
        for part in self.parts_mgr.walk_parts():
            part.start_sim()

    def _terminate_all_parts(self):
        for part in self.parts_mgr.walk_parts():
            part.terminate_sim()

    def print_assertion_failures(self):
        '''Print all traced assertion failures to stderr'''
        if self._num_assertion_failures > 0:
            print("%d Assertion failures during simulation" %
                  self._num_assertion_failures, file=sys.stderr)
            for trace_ev in self.tracing.traced_events():
                if trace_ev.action == "ASSFAIL":
                    print("%10s: %s: %s" % (self.tracing.time_str(
                        trace_ev.traceTime),
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
            port = self.parts_mgr.find_port_by_name(port_name)

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

    def time_str(self, time):
        '''
        return a formatted time string of *time* based on the display scale
        '''
        return self.tracing.time_str(time)
