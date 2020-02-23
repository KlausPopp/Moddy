'''
:mod:`sim_var_watch` -- Variable Watcher
========================================

.. module:: sim_var_watch
   :synopsis: Variable Watcher
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
from .sim_base import SimBaseElement, add_elem_to_list
from .sim_trace import SimTraceEvent


class SimVariableWatcher(SimBaseElement):
    '''
    The VariableWatcher class watches a variable for changes.
    The variable is referenced by the moddy part and its variable name
    within the part.
    It can be a variable in the part itself or a subobject "obj1.subobj.a"

    The class provides the check_value_changed() method. In moddy,
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


class SimVarWatchManager:
    '''
    Class that tracks all watched variables
    '''

    def __init__(self, sim_tracing):
        self._sim_tracing = sim_tracing

        self._list_variable_watches = []  # list of watched variables

    def add_var_watcher(self, var_watcher):
        '''Add watcher to watcher list'''
        add_elem_to_list(self._list_variable_watches, var_watcher,
                         "Simulator Watcher")

    def watch_variables(self):
        '''
        Check all registered variables for changes.
        Generate a trace event for all changed variables
        '''
        for var_watcher in self._list_variable_watches:
            changed, _ = var_watcher.check_value_changed()
            if changed:
                new_val_str = var_watcher.__str__()
                trace_ev = SimTraceEvent(var_watcher.parent_obj,
                                         var_watcher, new_val_str, 'VC')
                self._sim_tracing.add_trace_event(trace_ev)

    def watch_variables_current_value(self):
        '''
        Generate a trace event for all watched variables with their
        current value.
        Used at start of simulator to report the initial values
        '''
        for var_watcher in self._list_variable_watches:
            trace_ev = SimTraceEvent(var_watcher.parent_obj,
                                     var_watcher, var_watcher.__str__(), 'VC')
            self._sim_tracing.add_trace_event(trace_ev)

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
