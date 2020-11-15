"""
:mod:`fsm` -- Moddy Finite State Machine
=======================================================================

.. module:: fsm
   :synopsis: A general finite state machine with hierarchical state support
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

"""


def is_sub_fsm_specification(name_cls_tuple):
    """
    Test if the tuple from a transition list (name, classType)
    is a subFsm specification"""
    _, cls = name_cls_tuple
    if isinstance(cls, type):
        return cls
    return None


class Fsm:
    # pylint: disable=too-many-instance-attributes
    """
    A finite state machine.
    Subclass your FSM from this class.

    Example::

        class Computer(Fsm):

            def __init__(self):

                transitions = {
                    '':
                        [('INITIAL', 'off')],
                    'off':
                        [('PowerApplied', 'standby')],
                    'standby':
                        [('PowerButtonPressed', 'normal_op')],
                    'normal_op':
                        [('PowerButtonPressed', 'standby'),
                         ('OsShutdown', 'standby')],
                    'any':
                        [('PowerRemoved', 'off')]
                }

                super().__init__( dictTransitions=transitions )

    The special *ANY* state means that the transitions can be initiated from
    ANY state.
    The special *INITIAL* event must be in the '' (uninitialized) state and
    specifies the INITIAL transistion
    which is triggered by :meth:`.start_fsm`.


    You can define entry and exit method that are executed when a state is
    entered or left.
    These methods must follow the naming convention
    ``state_<statename>_<entry/exit>``
    They don't need to exist. They are called only if they are defined.

    Note that entry and exit actions are NOT called at self transitions
    (transitions to the current state)::

        # Off actions
        def state_off_entry(self):
            print("state_off_entry")

        def state_off_exit(self):
            print("state_off_exit")

    You can also define a "do" Method that is invoked

    * after the "Entry" methode
    * at self transistions to the state

    These methods must follow the naming convention ``state_<statename>_do``


    Such routines can be also defined for the special *ANY* state.
    If they exist they are called at
    the entry or exit or self transitions to/from any state.

    .. note: You cannot define actions for transitions!

    Use the fsm as follows::

        comp = Computer()
        comp.start_fsm()    # sets the state machine to its initial state

        comp.event('PowerApplied')
        print("State %s" % comp.state)

        comp.event('PowerButtonPressed')
        print("State %s" % comp.state)

        comp.event('PowerRemoved')
        print("State %s" % comp.state)


    You can call :meth:`.exec_state_dependent_method` to execute a
    state specific method of the fsm.
    e.g. ``exec_state_dependent_method('msg', 123)`` calls
    ``state_<currentStateName>_msg( 123 )``

    (e.g. the simFsmPart uses it to execute the _msg and _expiration functions)


    **Hierarchically Nested State Support**

    https://en.wikipedia.org/wiki/UML_state_machine\
    #Hierarchically_nested_states

    Rules:
    Nested states are defined by the user in the transition list:


    Main FSM::

        transitions = {
            '':
                [('INITIAL', 'off')],
            'off':
                [('PowerApplied', 'standby')],
            'standby':
                [('PowerButtonPressed', 'normal_op')],
            'normal_op':
                [
                ####### NESTED FSM ('fsm-Name', Class-Name)
                 ('fsm-name' , subfsm),
                 ('PowerButtonPressed', 'standby'),
                 ('OsShutdown', 'standby')],
            'any':
                [('PowerRemoved', 'off')]
        }

    * A nested FSM is instantiated when the upper level state is entered
    * A nested FSM cannot exit
    * A nested FSM receives all events from the upper level FSM.
    If the event is not known in the nested FSM, \
    it is directed to the upper FSM. Events that are known in the \
    nested FSM are NOT directed to upper FSM

    * If the upper state exits, the exit action of the current states \
    (first, the state in the nested fsm, \
    then the upper fsm) are called. Then the nested fsm is terminated.

    * Orthogonal nested states are also supported. Meaning, multiple \
    nested fsms exist in parallel. Just \
    enter multiple subFsms in the transition list of a state.

    * For nested statemachines, the following methods are usefull:

        - :meth:`.top_fsm` gives you the reference to the top level Fsm. \
        E.g. to fire an event to the top Fsm.
        - :meth:`moddy_part` gives you the moddy part where the state machine \
        is contained, regardless of the fsm nesting level


    :param dict dict_transitions: a dictionary, with the transitions:
        The dict key is the state, and the values are a list of transition from
        that state. Each transition consists of a tuple (event, targetState).
    :param Fsm parent_fsm: The parent Finite State Machine. None if no parent.
    """

    def __init__(self, dict_transitions, parent_fsm=None):
        self.state = None
        self._parent_fsm = parent_fsm
        self.the_moddy_part = None  # set by simFsmPart

        # set reference to top level Fsm
        if parent_fsm is None:
            self._top_fsm = self
        else:
            self._top_fsm = parent_fsm._top_fsm

        self._list_child_fsms = []  # currently ACTIVE children

        self._dict_transitions = dict_transitions
        self._state_change_callback = None
        self._list_events = []

        # Validate transitions and build list of events
        for _, list_trans in dict_transitions.items():
            for trans in list_trans:
                if is_sub_fsm_specification(trans) is None:
                    event, to_state = trans

                    if event not in self._list_events:
                        self._list_events.append(event)

                    if not self.state_exists(to_state):
                        raise RuntimeError(
                            "to_state %s doesn't exist" % to_state
                        )
                    if to_state == "any":
                        raise RuntimeError("ANY cannot be a target state")

        # check for initial event and remove it
        try:
            idx_initial = self._list_events.index("INITIAL")
        except ValueError:
            raise Exception("INITIAL event missing")

        del self._list_events[idx_initial]

    #
    # Public API
    #
    def get_dict_transitions(self):
        """ return the transition dictionary """
        return self._dict_transitions

    def exec_state_dependent_method(self, method_name, deep, *args, **kwargs):
        """
        Execute the state specific methods:

        The method ``self.state_any_<method_name>(*args,**kwargs)``
        is called if it exists.

        The method ``self.state_<stateName>_<method_name>(*args,**kwargs)``
        is called if it exists.

        :param method_name: method name to call
        :param deep: if True, then for each currently active sub_fsm, the
            _exec_state_method is called
        :return: True if at least one method exists
        """
        handled = 0

        if deep is True:
            for sub_fsm in self._list_child_fsms:
                if sub_fsm.exec_state_dependent_method(
                    method_name, True, *args, **kwargs
                ):
                    handled += 1

        if self._exec_state_method("any", method_name, *args, **kwargs):
            handled += 1
        if self._exec_state_method(self.state, method_name, *args, **kwargs):
            handled += 1
        return handled > 0

    def set_state_change_callback(self, callback):
        """
        Register a method that is called whenever the state of the fsm changes

        :param callback: function to be called on state changes
        """
        self._state_change_callback = callback

    def has_event(self, ev_name):
        """
        check if the event is known by the fsm or a currently active
        statemachine.

        :return: True if event is known by the fsm or a currently active
        statemachine
        """
        ret_val = False
        if ev_name in self._list_events:
            ret_val = True
        else:
            for sub_fsm in self._list_child_fsms:
                if sub_fsm.has_event(ev_name):
                    ret_val = True
                    break
        return ret_val

    def start_fsm(self):
        """ start the FSM. Fire event ``INITIAL`` """
        if self.state is not None:
            raise RuntimeError("start_fsm state wrong")
        self._event("INITIAL")

    def event(self, ev_name):
        """
        Execute an Event in the *ANY* and current state.

        :param ev_name: event to execute
        :raise AssertionError: if the current state is None.
        :return: True if the event causes a state change, False if not.
        """
        assert self.state is not None, "Did you call start_fsm?"
        return self._event(ev_name)

    def top_fsm(self):
        """ get a reference to the topmost Fsm in the hierarchy """
        return self._top_fsm

    def moddy_part(self):
        """
        return a reference of the moddy part this fsm is contained in
        (regardless of the fsm nesting level).
        return None if it is not included in a moddy part
        """
        part = None
        try:
            part = self.top_fsm().the_moddy_part
        except AttributeError:
            pass
        return part

    #
    # Internal methods
    #
    def _exec_state_method(self, state, method_name, *args, **kwargs):
        """
        Execute a state specific method that might exist in the fsm subclass

        The method self.State_<stateName>_<method_name>(*args) is called if
        it exists, True is returned.
        If it doesn't exist, nothing happens, but False is returned.

        """
        full_method_name = "state_%s_%s" % (state, method_name)

        func = getattr(self, full_method_name, None)
        if func is None:
            return False

        func(*args, **kwargs)
        return True

    def state_exists(self, state):
        """ test if state exists """
        return state in self._dict_transitions

    def goto_state(self, state):
        """ change fsm state """
        if state == "any" or self.state_exists(state) is False:
            raise RuntimeError("goto_state invalid state %s" % state)

        if self.state != state:  # ignore self transitions
            old_state = self.state
            # print("+++ %s GOTO STATE %s" % (type(self).__name__,state))
            # exit old state
            if self.state is not None:
                # terminate subFsms
                self.terminate_sub_fsms()
                # call current state Exit method
                self.exec_state_dependent_method("exit", False)

            # enter new state
            self.state = state
            self.exec_state_dependent_method("entry", False)

            # Start any possible nested fsms
            self.start_sub_fsms()

            if self._state_change_callback is not None:
                self._state_change_callback(old_state, self.state)
        # in any case, execute the "Do" Method of the current state
        if self.state == state:
            # only execute this if the state was not again
            # changed by the Entry methods...
            self.exec_state_dependent_method("do", False)
        # print("+++ RETURN FROM %s GOTO STATE %s" %
        # (type(self).__name__,state))

    def _event(self, ev_name):
        """
        Execute an Event in the "ANY" and current state.
        Returns True if the event causes a state change, False if not.
        """
        # Check if there is a matching transition
        old_state = self.state

        # first, check if the current state has subFsms which handle the event
        # if event handled by subFsm, ignore the event for this fsm
        if not self.pass_event_to_sub_fsms(ev_name):

            # Check all transitions in ANY state and current state
            trans_lists = []
            try:
                trans_lists.append(self._dict_transitions["any"])
            except KeyError:
                # ANY state may not exist
                pass

            if self.state is not None:
                trans_lists.append(self._dict_transitions[self.state])
            else:
                # events in uninitialized state
                trans_lists.append(self._dict_transitions[""])

            # print("+++ %s EVENT %s in state %s" %
            # (type(self).__name__, ev_name, self.state))

            for trans_list in trans_lists:
                for trans in trans_list:
                    if is_sub_fsm_specification(trans) is None:
                        event, to_state = trans
                        if event == ev_name:
                            # print("+++ %s TRANS %s -> %s" %
                            # (type(self).__name__,self.state, to_state))
                            self.goto_state(to_state)
                            break
        return old_state != self.state

    def pass_event_to_sub_fsms(self, ev_name):
        """
        check if the current state has subFsms which handle the event
        if event handled by sub_fsm, return True
        """
        handled = False
        for sub_fsm in self._list_child_fsms:
            if sub_fsm.has_event(ev_name):
                sub_fsm.event(ev_name)
                # print("Event %s handled by sub_fsm %s" %
                # (ev_name, type(sub_fsm).__name__))
                handled = True

        return handled

    def start_sub_fsms(self):
        """ start all subfsms in current master state """
        trans_list = self._dict_transitions[self.state]
        for trans in trans_list:
            sub_fsm_cls = is_sub_fsm_specification(trans)
            if sub_fsm_cls is not None:
                # create new fsm
                sub_fsm = sub_fsm_cls(parentFsm=self)
                # add sub_fsm to list of active subFsms
                self._list_child_fsms.append(sub_fsm)
                # goto initial state
                sub_fsm.start_fsm()

    def terminate_sub_fsms(self):
        """ terminate all started sub fsms """
        for sub_fsm in self._list_child_fsms:
            sub_fsm.exec_state_dependent_method("exit", False)
        self._list_child_fsms = []
