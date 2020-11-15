"""
:mod:`simulator` -- Moddy Simulator core
========================================

.. module:: simulator
   :platform: Unix, Windows
   :synopsis: Moddy Simulator Core Routines
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

"""
import sys
from heapq import heappush, heappop
from datetime import datetime

from .version import VERSION
from .sim_base import SimEvent
from .sim_parts_mgr import SimPartsManager
from .sim_trace import SimTracing
from .sim_var_watch import SimVarWatchManager
from .sim_monitor import SimMonitorManager


class Sim:
    # pylint: disable=too-many-instance-attributes
    """Simulator main class"""

    def __init__(self):
        self.parts_mgr = SimPartsManager()
        self.tracing = SimTracing(self.time)
        self.var_watch_mgr = SimVarWatchManager(self.tracing)
        self.monitor_mgr = SimMonitorManager()

        # a heapq with list of pending events takes pendingEvent objects,
        # sorted by execTime
        self._list_events = []
        self._time = 0.0  # current simulator time
        self._stop_on_assertion_failure = False
        self._is_running = False
        self._has_run = False
        self._stop_event = None
        self._num_events = 0
        self._start_real_time = None

    def time(self):
        """ Return current simulation time """
        return self._time

    def schedule_event(self, event):
        """
        schedule a new event for execution.
        """
        heappush(self._list_events, event)

    def stop(self):
        """ stop simulator """
        self._is_running = False
        elapsed_time = datetime.now() - self._start_real_time
        self._terminate_all_parts()
        print(
            "SIM: Simulator stopped at",
            self.time_str(self._time)
            + ". Executed %d events in %.3f seconds"
            % (self._num_events, elapsed_time.total_seconds()),
        )
        self.tracing.print_assertion_failures()

    def run(
        self,
        stop_time,
        max_events=100000,
        enable_trace_printing=True,
        stop_on_assertion_failure=True,
    ):
        """

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

        """
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
        self.var_watch_mgr.watch_variables_current_value()
        self._start_all_parts()
        # Check for changed variables
        self.var_watch_mgr.watch_variables()

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
                if event.is_cancelled():
                    continue

                self._num_events += 1
                assert self._time <= event.exec_time, "time can't go backward"
                self._time = event.exec_time

                if event == self._stop_event:
                    print("SIM: Stops because stopTime reached")
                    break

                # print("SIM: Exec event", event, self._time)
                # pylint: disable=bare-except
                try:
                    # Catch model exceptions
                    event.execute()
                except Exception:
                    print(
                        "SIM: Caught exception while executing event %s"
                        % event,
                        file=sys.stderr,
                    )
                    # re-raise model exception
                    raise
                # Check for changed variables
                self.var_watch_mgr.watch_variables()
                # Call monitors
                self.monitor_mgr.call_monitors()

                if max_events is not None and self._num_events >= max_events:
                    print(
                        "SIM: Simulator has got too many events "
                        "(pass a higher number to run(maxEvents=n)"
                    )
                    break

                if (
                    self._stop_on_assertion_failure
                    and self.tracing.assertion_failures() > 0
                ):
                    print("SIM: Stops due to Assertion Failure")
                    break
        finally:
            self.stop()

    def is_running(self):
        """ Return if simulator is running """
        return self._is_running

    def _start_all_parts(self):
        for part in self.parts_mgr.walk_parts():
            part.start_sim()

    def _terminate_all_parts(self):
        for part in self.parts_mgr.walk_parts():
            part.terminate_sim()

    def smart_bind(self, bindings):
        """
        Create many port bindings at once using simple lists.

        Example:

        .. code-block:: python

            simu.smart_bind( [
                ['App.out_port1', 'Dev1.in_port', 'Dev2.in_port'],
                ['App.io_port1', 'Server.net_port' ]  ])

        :param list bindings: Each list element must be a list of strings, \
            which specifies ports that shall be \
            connected to each other. \
            The strings must specify the hierarchy names of the ports.

        """
        self.parts_mgr.smart_bind(bindings)

    def time_str(self, time):
        """
        return a formatted time string of *time* based on the display scale
        """
        return self.tracing.time_str(time)
