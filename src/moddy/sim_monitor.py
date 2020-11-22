"""
:mod:`sim_monitor` -- Monitoring
========================================

.. module:: sim_monitor
   :synopsis: Simulator monitoring
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

"""
from .sim_base import add_elem_to_list


class SimMonitorManager:
    """
    Manage functions to be called at each simulation step
    """

    def __init__(self):
        # list of monitors (called on each simulator step)
        self._list_monitors = []

    def add_monitor(self, monitor_func):
        """
        Register a function to be called at each simulator step.
        Usually used by monitors or stimulation routines

        :param monitor_func: function to call. Gets called with no arguments
        """
        add_elem_to_list(self._list_monitors, monitor_func, "Monitors")

    def delete_monitor(self, monitor_func):
        """
        Delete a monitor function that has been registered with 'addMonitor'
        before

        :param monitor_func: function to delete
        :raises ValueError: if monitorFunc is not registered
        """
        self._list_monitors.remove(monitor_func)

    def call_monitors(self):
        """ Run all monitors """
        for monitor_func in self._list_monitors:
            monitor_func()
