'''
:mod:`sim_var_watch` -- Variable Watcher
========================================

.. module:: sim_var_watch
   :synopsis: Variable Watcher
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
from .sim_base import SimBaseElement


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
