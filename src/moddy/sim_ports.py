'''
:mod:`sim_ports` -- Moddy Simulator Ports and Timers
====================================================

.. module:: sim_ports
   :platform: Unix, Windows
   :synopsis: Moddy Simulator Ports
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
import pickle
from heapq import heappush, heappop
from collections import deque

from .sim_base import SimBaseElement, SimEvent
from .sim_base import add_elem_to_list
from .sim_trace import SimTraceEvent


class SimInputPort(SimBaseElement):
    '''Simulator input port

    :param sim sim: Simulator instance
    :param SimPart part: simPart that contains this port
    :param name: port name
    :param msg_received_func: callback function to call for message \
        receiption. Signature ``func(port, msg)``. May be None
    :param io_port: reference to the IOPort which contains this inPort \
        (None if not part of IOPort).

    '''

    # pylint: disable=too-many-arguments
    def __init__(self, sim, part, name, msg_received_func, io_port=None):
        super().__init__(sim, part, name, "InPort")
        self._out_ports = []  # connected output ports
        # function that gets called when message arrives
        self._msg_received_func = msg_received_func
        # function that gets called when message transmission has started on
        # outPort
        self._msg_started_func = None
        # reference to the IOPort which contains this inPort
        # (None if not part of IOPort)
        self._io_port = io_port
    # pylint: enable=too-many-arguments

    def msg_event(self, msg):
        '''called from bound outport when a new message is received'''
        if self._msg_received_func is not None:
            self._msg_received_func(self, msg)

    def uses_msg_start_event(self):
        '''return true if msg_started_func is not None'''
        return self._msg_started_func is not None

    def msg_start_event(self, msg, out_port, flight_time):
        '''
        called from bound outport when a new message transmission just started
        '''
        if self._msg_started_func is not None:
            self._msg_started_func(self, msg, out_port, flight_time)

    def set_msg_started_func(self, msg_started_func):
        '''
        register a function that gets called when the bound output port
        begins a message transmission

        :param msg_started_func: callback function to call on \
            message transmission start.\
            Signature ``func(inPort, msg, outPort, flightTime)``
        '''
        self._msg_started_func = msg_started_func

    def is_bound(self):
        '''Report True if port is bound to an output port'''
        return len(self._out_ports) > 0

    def out_ports(self):
        '''Return list of connected output ports'''
        return self._out_ports

    def io_port(self):
        '''
        Return IOPort to which this input port belongs
        (None if not in an IO Port)
        '''
        return self._io_port


class SimOutputPort(SimBaseElement):
    '''Simulator output port

    :param sim sim: Simulator instance
    :param simPart part: simPart that contains this port
    :param name: port name
    :param color: message color to use in sequence diagram. \
        Use default color if *None*
    :param ioPort: reference to the IOPort which contains this outPort \
        (None if not part of IOPort).

    '''

    class FireEvent(SimEvent):
        ''' Event that is passed to scheduler to send a message '''

        # pylint: disable=too-many-instance-attributes
        def __init__(self, sim, port, msg, flight_time):
            super().__init__()
            self._sim = sim
            self.port = port
            self._serialized_msg = self.__class__.msg_serialize(msg)
            self.msg_color = msg.msgColor if hasattr(msg, 'msgColor') \
                else None
            self.flight_time = flight_time  # message transmit time
            # time when application called send()
            self.request_time = sim.time()
            self.exec_time = -1  # when message arrives at input port
            self.is_lost = False  # Flags that message is a lost message

        def __str__(self):
            '''Create a user readable form of the event. Used by tracer'''
            return "%s req=%s beg=%s end=%s dur=%s msg=[%s]" % \
                ("(LOST)" if self.is_lost else "",
                 self._sim.time_str(self.request_time),
                 self._sim.time_str(self.exec_time - self.flight_time),
                 self._sim.time_str(self.exec_time),
                 self._sim.time_str(self.flight_time),
                 self.msg_text())

        def __repr__(self):
            return self.port.obj_name() + "#fireEvent"

        def msg_text(self):
            ''' return message's __str__ '''
            return self.__class__.msg_unserialize(
                self._serialized_msg).__str__()

        def execute(self):

            # pass the message to all bound input ports
            for inport in self.port.in_ports():

                self._sim.tracing.add_trace_event(SimTraceEvent(
                    self.port.parent_obj, inport, self, '<MSG'))

                if not self.is_lost:
                    # make a deep copy (by using pickle) of the message,
                    # so that application can modify the message
                    msg_copy = self.__class__.msg_unserialize(
                        self._serialized_msg)
                    inport.msg_event(msg_copy)

            # remove me from pending queue
            # print(self, "exec", len(self.port._list_pending_msg))
            self.port.pending_msg().popleft()
            # and send next message in queue
            if self.port.pending_msg():
                event = self.port.pending_msg()[0]
                self.port.send_schedule(event)
                self._sim.tracing.add_trace_event(SimTraceEvent(
                    self.port.parent_obj, self.port, event, '>MSG(Q)'))
            self.port._seq_no += 1

        def notify_start(self):
            '''
            tell all bound input ports that message transmission has begun
            '''
            for inport in self.port.in_ports():
                if inport.uses_msg_start_event():
                    inport.msg_start_event(self.__class__.msg_unserialize(
                        self._serialized_msg), self, self.flight_time)

        @staticmethod
        def msg_serialize(msg):
            '''Serialize message using pickle'''
            return pickle.dumps(msg, pickle.HIGHEST_PROTOCOL)

        @staticmethod
        def msg_unserialize(stream):
            '''Un-Serialize message using pickle'''
            return pickle.loads(stream)

    def __init__(self, sim, part, name, color=None, io_port=None):
        # pylint: disable=too-many-arguments
        super().__init__(sim, part, name, "OutPort")
        # list of all input ports
        self._list_in_ports = []
        # list of pending messages (not yet fired)
        self._list_pending_msg = deque()
        # color for messages leaving that port
        self.color = color
        # reference to the IOPort which contains this outPort
        # (None if not part of IOPort)
        self._io_port = io_port
        # learned message types that left this port
        self._list_msg_types = []
        # next message sequence number (for lost messages)
        self._seq_no = 0
        # heap with message sequence numbers that will be lost
        self._lost_seq_heap = []

    def bind(self, input_port):
        '''bind an output port to an input port

        :param input_port: input port to which this output port shall be bound
        :raise RuntimeError: if input port is already bound to that output port

        '''
        add_elem_to_list(input_port.out_ports(), self,
                         input_port.__str__() + ":outPorts")
        add_elem_to_list(self.in_ports(), input_port,
                         self.__str__() + ":inPorts")

    def is_bound(self):
        '''Report True if port is bound to at least one input port'''
        return len(self._list_in_ports) >= 1

    def _learn_msg_types(self, msg):
        '''
        Learn which types of messages are leaving the port.
        Will be displayed in Structure Graphs
        '''
        msg_type = type(msg).__name__
        if msg_type not in self._list_msg_types:
            self._list_msg_types.append(msg_type)

    def learned_msg_types(self):
        '''
        Return list of learned message types that left the port until now.
        (Strings with types)
        '''
        return self._list_msg_types

    def pending_msg(self):
        ''' Return list of pending messages '''
        return self._list_pending_msg

    def send_schedule(self, event):
        ''' schedule a send event '''
        event.exec_time = self._sim.time() + event.flight_time
        self._sim.schedule_event(event)
        # check if the message is marked as lost
        event.is_lost = self.is_lost_message()
        if not event.is_lost:
            event.notify_start()

    def send(self, msg, flight_time):
        '''User interface to send a message

        :param msg: message to send
        :param flight_time: flight time of message

        '''
        self._learn_msg_types(msg)
        event = self.FireEvent(self._sim, self, msg, flight_time)
        if not self._list_pending_msg:
            # no pending messages, send now
            self.send_schedule(event)
            self._sim.tracing.add_trace_event(SimTraceEvent(
                self.parent_obj, self, event, '>MSG'))

        self._list_pending_msg.append(event)
        # print(self, "sendlp", len(self._list_pending_msg))

    def set_color(self, color):
        ''' Set color for messages leaving that port '''
        self.color = color

    def inject_lost_message_error_by_sequence(self, next_seq):
        '''
        Inject error. Force one of the next messages sent via this port to
        be lost.
        If nextSeq is 0, the next message sent via this port will be lost,
        if it is 1 the next but one message is lost etc.
        '''
        lost_seq = self._seq_no + next_seq

        # add the sequence number to be lost to the _lostSeqHeap,
        # if this sequence is not already there
        # this maintains the heap sequence.
        if lost_seq not in self._lost_seq_heap:
            heappush(self._lost_seq_heap, lost_seq)
        # print("lostSeqHeap=", self._lostSeqHeap)

    def is_lost_message(self):
        '''
        Test if the current message is marked to be lost.
        Return True if so and remove the current sequence from the lost
        sequence heap
        '''
        if len(self._lost_seq_heap) > 0 and self._seq_no == \
                self._lost_seq_heap[0]:

            heappop(self._lost_seq_heap)
            return True
        return False

    def io_port(self):
        '''
        Return IOPort to which this output port belongs
        (None if not in an IO Port)
        '''
        return self._io_port

    def in_ports(self):
        ''' Return list of connected input ports'''
        return self._list_in_ports


class SimIOPort(SimBaseElement):
    ''' An element that contains one input and one output port

    :param sim sim: Simulator instance
    :param simPart part: simPart that contains this port
    :param name: port name
    :param msg_received_func: callback function to call for message \
        receiption. Signature ``func(port, msg)``
    :param special_in_port: if None, create a standard :class:`simInputPort`, \
        otherwise use the supplied specialInPort

    '''

    def __init__(self, sim, part, name, msg_received_func,
                 special_in_port=None):
        # pylint: disable=too-many-arguments

        super().__init__(sim, part, name, "IOPort")
        self._out_port = SimOutputPort(sim, part, name + "Out", io_port=self)
        if special_in_port is None:
            self._in_port = SimInputPort(
                sim, part, name + "In", msg_received_func, io_port=self)
        else:
            self._in_port = special_in_port
            self._in_port._io_port = self

    def in_port(self):
        ''' Return the input port '''
        return self._in_port

    def out_port(self):
        ''' Return the output port '''
        return self._out_port

    def bind(self, other_io_port):
        ''' Bind IOPort to another IOPort, in/out will be crossed '''
        self._out_port.bind(other_io_port.in_port())
        other_io_port.out_port().bind(self.in_port())

    def loop_bind(self):
        ''' Loop in/out ports of an IO port together '''
        self._out_port.bind(self._in_port)

    # delegation methods to output port

    def send(self, msg, flight_time):
        ''' send message to IoPorts output port

        Refer to :func:`simOutputPort.send` for parameters.
         '''
        self._out_port.send(msg, flight_time)

    def inject_lost_message_error_by_sequence(self, next_seq):
        '''
        inject error on IoPorts output port
        Refer to :func:`simOutputPort.inject_lost_message_error_by_sequence`
        for details.
        '''
        self._out_port.inject_lost_message_error_by_sequence(next_seq)

    def set_color(self, color):
        ''' Set color for messages leaving that IOport '''
        self._out_port.color = color

    def peer_ports(self):
        '''
        return all peer IOPorts to which this port is bound to.
        return list of peer ports (empty list if none)
        '''
        list_peers = []
        if self._in_port.is_bound():
            for port in self.in_port().out_ports():
                if port.io_port() is not None:
                    port = port.io_port().in_port()
                    if port in self.out_port().in_ports():
                        list_peers.append(port.io_port())
        return list_peers

    # delegation methods to input port
    def set_msg_started_func(self, msg_started_func):
        '''
        register a function that gets called when the bound output port
        begins a message transmission

        Refer to :func:`simInputPort.setMsgStartedFunc` for details.
        '''
        self._in_port.setMsgStartedFunc(msg_started_func)


class SimTimer(SimBaseElement):
    '''Simulator Timer
    timer is either running or stopped
    timer can be canceled, and restarted

    :param sim sim: Simulator instance
    :param simPart part: simPart that contains this port
    :param name: port name
    :param elapsed_func: callback function to call for timer expiry.\
         Signature ``func(timer)``

    '''

    class TimerEvent(SimEvent):
        ''' Event that is passed to scheduler for timer '''

        def __init__(self, sim, timer, exec_time):
            super().__init__()
            self._sim = sim
            self._timer = timer
            self.exec_time = exec_time

        def __repr__(self):
            return self._timer.hierarchy_name() + "#timerEvent"

        def execute(self):
            self._timer._pending_event = None
            self._sim.tracing.add_trace_event(SimTraceEvent(
                self._timer.parent_obj, self._timer, None, 'T-EXP'))
            self._timer.elapsed_func(self._timer)

    class TimeoutFmt:
        # pylint: disable=too-few-public-methods
        '''Helper class to get a formatted print of the timeout'''

        def __init__(self, sim, timeout):
            self._sim = sim
            self.timeout = timeout

        def __str__(self):
            return self._sim.time_str(self.timeout)

    def __init__(self, sim, part, name, elapsed_func):
        super().__init__(sim, part, name, "Timer")
        # current scheduled event (None if timer stopped)
        self._pending_event = None
        # function that gets called when time elapsed
        self.elapsed_func = elapsed_func

    def _start(self, timeout):
        if self._pending_event is not None:
            raise RuntimeError(self.hierarchy_name() +
                               "already running")
        if timeout <= 0:
            raise AttributeError(self.hierarchy_name() +
                                 "timeout must be greate than 0")
        event = self.TimerEvent(self._sim, self, self._sim.time() + timeout)
        self._sim.schedule_event(event)
        self._pending_event = event

    def start(self, timeout):
        '''Start the timer.

        :param timeout: Timer will fire after *timeout*
        :raise: RuntimeError if timer already started
        :raise: AttributeError if timeout <= 0
        '''
        self._start(timeout)
        self._sim.tracing.add_trace_event(SimTraceEvent(
            self.parent_obj, self,
            self.TimeoutFmt(self._sim, timeout), 'T-START'))

    def _stop(self):
        if self._pending_event is not None:
            self._pending_event.cancel()
            self._pending_event = None

    def stop(self):
        '''Stop timer. Does nothing if timer not running'''
        self._sim.tracing.add_trace_event(SimTraceEvent(
            self.parent_obj, self, None, 'T-STOP'))
        self._stop()

    def restart(self, timeout):
        '''
        Restart timer, works whether timer is running or not.

        :param timeout: Timer will fire after *timeout*
        '''
        self._sim.tracing.add_trace_event(SimTraceEvent(
            self.parent_obj, self,
            self.TimeoutFmt(self._sim, timeout), 'T-RESTA'))
        self._stop()
        self._start(timeout)
