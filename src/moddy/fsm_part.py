'''
:mod:`fsm_part` -- A moddy part with a state machine
=======================================================================

.. module:: fsm_part
   :synopsis: A moddy part with a state machine
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
from .sim_part import SimPart


class SimFsmPart(SimPart):
    '''
    A moddy part with a state machine
    All simulator events are directed to the fsm.

    :param sim: Simulator instance
    :param obj_name: part name
    :param Fsm fsm: the state machine (Fsm class) object created by caller
    :param parentObj: parent part. None if part has no parent. Defaults to None
    :param dict statusBoxReprMap: defines how each state is shown in
            sequence diagrams' status boxes
            Must be a dictionary with the state names as keys.
            The values must be a tuple of

            * text to display (None if org. state name shall be used)
            * appearance: The colors of the status box, see setStatIndication()

    '''

    def __init__(self, sim, obj_name, fsm, parent_obj=None,
                 status_box_repr_map=None):
        # pylint: disable=too-many-arguments
        super().__init__(sim=sim, obj_name=obj_name, parent_obj=parent_obj)

        # reference the fsm
        self.fsm = fsm
        fsm.the_moddy_part = self
        # register state change callback
        fsm.set_state_change_callback(self.fsm_state_change)

        self._status_box_repr_map = status_box_repr_map

    def start_sim(self):
        SimPart.start_sim(self)
        # Bring state machine into initial state
        self.fsm.start_fsm()

    def create_ports(self, ptype, list_port_names):
        # Override simPart method to route all events to central handlers
        '''
        Convinience functions to create multiple ports at once.

        :param ptype: Type of ports, must be one of 'in', 'out' or 'io'
        :param list list_port_names: list of port names to create

        The function creates for each port a member variable with this name
        in the part.

        '''
        if ptype == 'in':
            for port_name in list_port_names:
                setattr(self, port_name,
                        self.new_input_port(port_name, self.msg_recv))
        elif ptype == 'io':
            for port_name in list_port_names:
                setattr(self, port_name,
                        self.new_io_port(port_name, self.msg_recv))
        else:
            super().create_ports(ptype, list_port_names)

    def create_timers(self, list_timer_names):
        # Override simPart method to route all events to central handlers
        '''
        Convinience functions to create multiple timers at once.

        :param list list_timer_names: list of timer names to create

        The function creates for each port a member variable with this name
        in the part.
        '''
        for tmr_name in list_timer_names:
            setattr(self, tmr_name,
                    self.new_timer(tmr_name, self.tmr_expired))

    def msg_recv(self, port, msg):
        '''
        receive function for messages

        If an event name <portname>_Msg exists in the fsm, trigger that event,
        otherwise call the state_<portName>_Msg(msg) in the fsm
        '''
        fsm_event_name = "%s_msg" % port.obj_name()

        if self.fsm.has_event(fsm_event_name):
            self.fsm.event(fsm_event_name)
        else:
            if not self.fsm.exec_state_dependent_method(
                 fsm_event_name, True, msg):
                self.annotation('%s not handled' % fsm_event_name)

    def tmr_expired(self, timer):
        '''
        Timer expired handler

        If an event name <timerName>_Expired exists in the fsm, trigger that
        event, otherwise call the state_<timerName>_expired() in the fsm
        '''

        fsm_event_name = "%s_expired" % timer.obj_name()

        if self.fsm.has_event(fsm_event_name):
            self.fsm.event(fsm_event_name)
        else:
            if not self.fsm.exec_state_dependent_method(fsm_event_name, True):
                self.annotation('%s not handled' % fsm_event_name)

    def fsm_state_change(self, _, new_state):
        '''
        Called by the fsm whenever the state changes.
        Set the part status indicator to new state using the representation map
        '''
        text = new_state
        appearance = {}

        if self._status_box_repr_map is not None:
            try:
                text, appearance = self._status_box_repr_map[new_state]
                if text is None:
                    text = new_state
            except KeyError:
                pass

        self.set_state_indicator(text, appearance)
