'''
:mod:`vthread` -- Moddy virtual threads
=======================================================================

.. module:: vthread
   :platform: Unix, Windows
   :synopsis: Moddy virtual threads
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''

from collections import deque
import threading

from .sim_part import SimPart
from .sim_ports import SimInputPort, SimTimer, SimIOPort


class VtInPort(SimInputPort):
    '''
    Base class for input ports of vThreads which extends the standard
    input port:

    * buffers the incoming message: vtInport can be a sampling or queuing port

        - a :class:`vtSamplingInPort` buffers only the last received message
        - a :class:`vtQueuingInPort` buffers all messages

    * wakes up the vThread from :meth:`~.vThread.wait` if the vThread is
      waiting for input on that port
    * provides an API to read the messages from the buffer
    '''

    def __init__(self, sim, name, v_thread, q_depth):
        '''
        Constructor
        '''
        # no msgReceived function, because msg_event()
        # is overwritten in subclasses
        super().__init__(sim, v_thread, name, msg_received_func=None)
        self._v_thread = v_thread
        self._sampled_msg = deque(maxlen=q_depth)

    def wake(self):
        '''
        Wake up the thread
        '''
        self._v_thread.scheduler().wake(self._v_thread, self)

    def read_msg(self, default=None):
        '''Read a message from the port's buffer. Overwritten by subclass'''

    def n_msg(self):
        '''
        Check how many messages are in the port's buffer. Overwritten
        by subclass
        '''

    def clear(self):
        '''clear input port'''
        self._sampled_msg.clear()


class VtSamplingInPort(VtInPort):
    '''
    Sampling input port for vThreads
    A sampling port buffers only the last received message
    A read from the sampling buffer does not consume the buffered message

    :param sim: Simulator instance
    :param name: port name
    :param vThread vThread: vThread to which the port shall be added to
    '''

    def __init__(self, sim, name, v_thread):
        super().__init__(sim, name, v_thread, q_depth=1)

    def msg_event(self, msg):
        # overwritten from base simInputPort class!
        # print("vtSamplingInPort inRecv %s %s" % (self,msg))
        if self._v_thread.scheduler().vthread_can_receive_messages(
                self._v_thread):
            self._sampled_msg.append(msg)
            self.wake()

    def read_msg(self, default=None):
        '''
        Get current message from sampling buffer.
        The message is not consumed, i.e. if `read_msg` is called again before
        a new message comes in, the same message is returned.

        :param default: value to return if no message was received at all
        :raise BufferError: if no message was received at all AND `default`\
         is None
        :return: message in buffer
        '''
        if len(self._sampled_msg) > 0:
            return self._sampled_msg[0]

        if default is None:
            raise BufferError("No msg in sampling buffer")

        return default

    def n_msg(self):
        '''
        :return: 1 if message is available, or 0 if not
        '''
        return 1 if len(self._sampled_msg) > 0 else 0


class VtQueuingInPort(VtInPort):
    '''
    Queuing input port for vThreads.
    A queuing port buffers all messages in a fifo queue. The queue depth is
    infinite.
    A read from the buffer consumes the oldest message.

    :param sim: Simulator instance
    :param name: port name
    :param vThread vThread: vThread to which the port shall be added to
    '''

    def __init__(self, sim, name, v_thread):
        super().__init__(sim, name, v_thread, q_depth=None)

    def msg_event(self, msg):
        # overwritten from base simInputPort class!
        # print("vtQueuingInPort inRecv %s %s" % (self,msg))
        if self._v_thread.scheduler().vthread_can_receive_messages(
                self._v_thread):

            self._sampled_msg.append(msg)
            if len(self._sampled_msg) == 1:
                # wakeup waiting thread if queue changes from empty to
                # one entry
                self.wake()

    def read_msg(self, default=None):
        '''
        Get first message from queue.
        The message is consumed.

        :param default: ignored
        :raise BufferError: if no message in buffer
        :return: message in buffer
        '''
        del default
        if len(self._sampled_msg) > 0:
            return self._sampled_msg.popleft()
        raise BufferError("No msg in queue")

    def n_msg(self):
        '''
        :return: number of messages in queue
        '''
        return len(self._sampled_msg)


class VtIOPort(SimIOPort):
    '''
    An IOPort that combines a Sampling/Queuing input port and a
    standard output port

    :param sim: Simulator instance
    :param name: port name
    :param vThread vThread: vThread to which the port shall be added to
    :param inPort: The input port for the IO-Port. Either \
         :class:`vtSamplingInPort` or :class:`vtQueuingInPort`

    '''

    def __init__(self, sim, name, v_thread, in_port):
        super().__init__(sim, v_thread, name, msg_received_func=None,
                         special_in_port=in_port)

    def read_msg(self, default=None):
        '''Read a message from the in-port's buffer.'''
        return self._in_port.read_msg(default)

    def n_msg(self):
        '''
        Check how many messages are in the in-port's buffer.
        '''
        return self._in_port.n_msg()

    def clear(self):
        '''clear input port'''
        self._in_port.clear()


class VtTimer(SimTimer):
    '''
    A timer for vThreads which extends the standard simulation timer

    When the timer expires, it sets a flag, that the user can test
    with :meth:`has_fired`.
    The flag is reset with :meth:`start` and :meth:`restart`

    :param sim: Simulator instance
    :param name: timer name
    :param vThread vThread: vThread to which the timer shall be added to
    '''

    def __init__(self, sim, name, v_thread):
        '''
        Constructor
        '''
        super().__init__(sim, v_thread, name, self._tmr_expired)
        self._v_thread = v_thread
        self._tmr_fired = False

    def _tmr_expired(self, _):
        self._tmr_fired = True
        self._v_thread.scheduler().wake(self._v_thread, self)

    def has_fired(self):
        '''
        :return: True if timer expired
        '''
        return self._tmr_fired

    def start(self, timeout):
        # Override method from simTimer
        self._tmr_fired = False
        super().start(timeout)

    def restart(self, timeout):
        # Override method from simTimer
        self._tmr_fired = False
        super().restart(timeout)


class VThread(SimPart):
    '''
    A virtual thread simulating a software running on an operating system.
    The scheduler of the operating system schedules the vthreads.

    The simulated software must be written in python and must only
    call the functions from the scheduler for timing functions:

        * :meth:`busy` - tell the scheduler how much time the current
            operation takes
        * :meth:`wait` - wait for an event: Event can be a timeout,
            a simulation timer expiration, or a message arriving on an
            input port

    A vthread is a :class:`~moddy.simulator.simPart` part, which can exchange
    messages with other simulation parts, but unlike pure simPart parts,

    * the input ports are :class:`vtInPort` that buffer incoming messages

        * a sampling input port (:class:`vtSamplingInPort`) buffers
            always the latest message
        * a queuing input port (:class:`vtQueuingInPort`) buffers all messages

        vThreads can :func:`wait` for messages.
        They can read messages from the input ports via

        * :meth:`~vtInPort.read_msg` - read one message from port
        * :meth:`~vtInPort.n_msg` - determine how many messages are pending

    * the simPart timers are indirectly available to vThreads via vtTimers
        (set a flag on timeout)

    :param sim: Simulator instance
    :param obj_name: part's name
    :param parent_obj: parent part. None if part has no parent.
    :param bool remote_controlled: if True, allow thread state to be \
    controlled through a moddy port "_thread_control_port".\
    Those threads are not started automatically, but only via explicit \
    "start" message to the "_thread_control_port".\
    Those threads can be killed via "kill" and restarted via "start".
    :param _target: Instead of sublcassing vThread and implementing the model \
    code in the subclasses ``run_vthread`` method, \
    specify the method with your model code in `_target`. \
    I gets called without parameters.
    :param dict elems: A dictionary with elements (ports and timers) \
    to create, \
    e.g. ``{ 'QueuingIn': 'inPort1', 'out': ['outPort1', 'outPort2'], \
    'vtTmr' : 'timer1' }``


    '''

    # pylint: disable=too-many-arguments
    def __init__(self, sim, obj_name, parent_obj=None, remote_controlled=False,
                 target=None, elems=None):
        '''
        Constructor
        '''
        SimPart.__init__(self, sim=sim, obj_name=obj_name,
                         parent_obj=parent_obj, elems=elems)
        self.remote_controlled = remote_controlled
        self.python_thread_running = False
        self.thread = None
        self._target = target
        self._monitor_func = None

        # scheduler that is scheduling this thread and its data
        self._scheduler = None
        self.sched_data = None

        if remote_controlled:
            self.create_ports('in', ['_thread_control_port'])

    def set_scheduler(self, scheduler, sched_data):
        '''
        Connect the scheduler to this thread
        :param scheduler: the scheduler
        :param sched_data: schedulers data, a reference is stored in this
            vthread ad self.sched_data
        '''
        self._scheduler = scheduler
        self.sched_data = sched_data

    def scheduler(self):
        ''' Return the scheduler '''
        return self._scheduler

    def start_thread(self):
        '''
        To be called from scheduler to start python thread which
        runs this v_thread
        :raises RuntimeError: if the thread is already running
        '''
        if self.thread is not None and self.thread.is_alive():
            raise RuntimeError(
                "start_thread: old vThread %s still running" % self.obj_name())
        self.thread = threading.Thread(target=self.run)
        self.python_thread_running = True
        self.thread.start()

    def wait_until_thread_terminated(self):
        '''
        To be called from scheduler when it has told the thread to terminate
        @raise RuntimeError: if the thread did not terminate within the timeout
        '''
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(3.0)
            if self.thread.is_alive():
                raise RuntimeError(
                    "wait_until_thread_terminated: Thread %s did not terminate"
                    % self.obj_name())

    class TerminateException(Exception):
        '''
        Exception that is raised to tell the thread that it shall be terminated
        because simulator terminates
        '''

    class KillException(Exception):
        '''
        Exception that is raised to tell the thread that it has been killed
        by another thread
        '''

    def run(self):
        '''
        runs the vthread code
        '''
        if self.remote_controlled:
            self.annotation('vThread started')
        term_reason = None
        try:
            self.run_vthread()
            # normal exit
            term_reason = "exited normally"
            self.term("exit")  # tell scheduler that thread has terminated
        except self.TerminateException:
            # simulator is about to terminate
            term_reason = "Terminated"
        except self.KillException:
            # killed by another thread
            term_reason = "Killed"
        except Exception:
            term_reason = "Exception in run_vthread"
            # catch all exceptions coming from the thread's model code
            self.term("exception")  # tell scheduler that thread has terminated
            raise  # re-raise exception, so that it's printed
        finally:
            self._stop_all_timers()
            self._clear_ports()
            self.python_thread_running = False
            if term_reason != "Terminated":
                self.annotation('vThread %s' % term_reason)

    def run_vthread(self):
        ''' Model code of the VThread. can be overridden by subclass'''
        if self._target is not None:
            self._target(self)
        else:
            raise RuntimeError(
                "%s: No implementation for run_vthread available\n" % self)

    def _stop_all_timers(self):
        for tmr in self._list_timers:
            tmr.stop()

    def _clear_ports(self):
        for port in self._list_ports:
            if hasattr(port, 'clear'):
                port.clear()

    def wait(self, timeout, ev_list=[]):
        # pylint: disable=dangerous-default-value
        '''
        Suspend vThread until one of the events in `ev_list` occurs or timeout

        :param timeout: time to wait for events. If None, wait forever. \
            A timeout value of 0 is invalid.
        :param list ev_list: list of events to wait for. \
            Events can be :class:`vtSamplingInPort`, \
             :class:`vtQueuingInPort`, :class:`vtIOPort`, \
             or :class:`vtTimer` object. \
             If ev_list is empty (or omitted), \
             wait for timeout unconditionally.

        :return: 'ok' if one of the events has been triggered \
        (it does not tell you which one), 'timeout' if timeout

        :raise TerminateException: if simulator stopped
        '''
        return self._scheduler.sys_call(self, 'wait', (timeout, ev_list))

    def wait_for_msg(self, timeout, ports):
        '''
        Suspend vThread until a message is available on at least at one
        of the `ports`.

        In contrast to :meth:`wait()`, you don't need to check that all
        ports are empty before calling this method.

        .. note::

            It makes not a lot of sense to call this method on
            :class:`vtSamplingInPort`, because once such a port
            has received at least once a message,
            this method returns immediately.

        :param timeout: time to wait for messsages. If None, wait forever. \
            If `0` is specified, don't wait, just \
            return what is available.
        :param ports: a port or a list of ports to wait for. \
            Each port can be :class:`vtQueuingInPort` or :class:`vtIOPort`.

        :return: One of the following:

            * if multiple ports were specified: tuple `(msg, port)`
                for the first message that is available one of the ports,
            * if a single port was specified: `msg` for the first message
                that is available on the ports,
            * None if no message available

        :raise TerminateException: if simulator stopped
        '''
        lst_ports = ports if isinstance(ports, list) else [ports]

        # check if already a message available
        ret_val = self._check_msg(lst_ports)

        if ret_val is None and timeout != 0:
            # wait for message
            self.wait(timeout, lst_ports)
            ret_val = self._check_msg(lst_ports)

        return ret_val

    @staticmethod
    def _check_msg(lst_ports):
        ret_val = None

        for port in lst_ports:
            if port.n_msg() > 0:
                if len(lst_ports) > 1:
                    ret_val = (port.read_msg(), port)
                else:
                    ret_val = port.read_msg()
                break

        return ret_val

    def wait_until(self, time, ev_list=[]):
        # pylint: disable=dangerous-default-value
        '''
        Suspend vThread until one of the events in `ev_list` occurs or until
        specified time

        :param time: _target time. Must be >= current simulation time, \
            otherwise :class:`ValueError` is thrown
        :param list ev_list: list of events to wait for. Events can be \
            :class:`VtSamplingInPort`, \
            :class:`VtQueuingInPort`, or :class:`VtTimer` object

        :return: 'ok' if one of the events has been triggered, \
            'timeout' if timeout

        :raise TerminateException: if simulator stopped
        :raise ValueError: if _target time already gone
        '''
        if time < self.time():
            raise ValueError("wait_until: _target time already gone")
        return self.wait(time - self.time(), ev_list)

    def wait_for_monitor(self, timeout, monitor_func):
        '''
        Suspend vThread until the 'monitor_func' detects a match.

        Usefull for stimulation threads to wait until the model has reached
        some state.
        The 'monitor_func' is called from the simulator at each simulation
        step.
        If the 'monitor_func' returns True, this function returns to caller.

        :param timeout: time to wait for monitor. If None, wait forever. \
            A timeout value of 0 is invalid.
        :param monitor_func: the monitor function to be triggered at each \
            simulation step. called without parameters

        :return: 'ok' the monitor has returned True, 'timeout' if timeout

        :raise TerminateException: if simulator stopped
        '''
        self._monitor_func = monitor_func
        self._sim.monitor_mgr.add_monitor(self._monitor_execute)

        res = self.wait(timeout, ["monitorEvent"])

        self._sim.monitor_mgr.delete_monitor(self._monitor_execute)
        return res

    def _monitor_execute(self):
        if self._monitor_func() is True:
            self._scheduler.wake(self, "monitorEvent")

    def busy(self, time, status, status_appearance={}):
        # pylint: disable=dangerous-default-value
        '''
        tell the scheduler how much time the current operation takes

        :param time: the busy time. May be 0
        :param status: the status text shown on the sequence diagram life line
        :param status_appearance: defines the decoration of the status \
            box in the sequence diagram.
            See svgSeqD.statusBox
        :return: always 'ok'
        :raise TerminateException: if simulator stopped

        '''
        return self._scheduler.sys_call(self, 'busy',
                                        (time, (status, status_appearance)))

    def term(self, term_reason):
        '''
        Terminate thread
        '''
        return self._scheduler.sys_call(self, 'term', (term_reason))

    def new_vt_sampling_in_port(self, name):
        """
        Add a new sampling input port (:class:`vtSamplingInPort`) to the part

        :param name: name of port
        """

        port = VtSamplingInPort(self._sim, name, self)
        self.add_port(port)
        return port

    def new_vt_queuing_in_port(self, name):
        """
        Add a new queueing input port (:class:`vtQueuingInPort`) to the part

        :param name: name of port
        """
        port = VtQueuingInPort(self._sim, name, self)
        self.add_port(port)
        return port

    def new_vt_sampling_io_port(self, name):
        """
        Add a new sampling I/O port (via :class:`vtIOPort`) to the part

        :param name: name of port
        """
        port = VtIOPort(self._sim, name, self, VtSamplingInPort(
            self._sim, name + '_in', self))
        self.add_port(port)
        return port

    def new_vt_queuing_io_port(self, name):
        """
        Add a new queueing I/O port(via :class:`vtIOPort`)  to the part

        :param name: name of port
        """
        port = VtIOPort(self._sim, name, self, VtQueuingInPort(
            self._sim, name + '_in', self))
        self.add_port(port)
        return port

    def new_vt_timer(self, name):
        """
        Add a new virtual timer to the part

        :param name: name of timer
        """
        timer = VtTimer(self._sim, name, self)
        self.add_timer(timer)
        return timer

    def create_ports(self, ptype, list_port_names):
        '''
        Convinience functions to create multiple vtPorts at once.

        :param str ptype: must be one of

            * 'SamplingIn',
            * 'QueuingIn',
            * 'SamplingIO'
            * 'QueuingIO'
            * 'in'
            * 'out'
            * 'io'
        :param list list_port_names: list of port names to create

        The function creates for each port a member variable with this
        name in the part.
        '''
        if ptype == 'SamplingIn':
            for port_name in list_port_names:
                setattr(self, port_name,
                        self.new_vt_sampling_in_port(port_name))
        # support also the old, mis-spelled name
        elif ptype in ['QueuingIn', 'QueingIn']:
            for port_name in list_port_names:
                setattr(self, port_name,
                        self.new_vt_queuing_in_port(port_name))
        elif ptype == 'SamplingIO':
            for port_name in list_port_names:
                setattr(self, port_name,
                        self.new_vt_sampling_io_port(port_name))
        # support also the old, mis-spelled name
        elif ptype in ['QueuingIO', 'QueingIO']:
            for port_name in list_port_names:
                setattr(self, port_name,
                        self.new_vt_queuing_io_port(port_name))
        else:
            SimPart.create_ports(self, ptype, list_port_names)

    def create_vt_timers(self, list_timer_names):
        '''
        Convinience functions to create multiple vtTimers at once.

        :param list_timer_names: list of timers to create

        The function creates for each port a member variable with this name
        in the part.
        '''
        for tmr_name in list_timer_names:
            setattr(self, tmr_name, self.new_vt_timer(tmr_name))

    def create_elements(self, elems):
        """
        Create ports and timers based on a dictionary.

        :param dict elems: A dictionary with elements (ports and timers) \
        to create, \
        e.g. ``{ 'QueuingIn': 'inPort1', 'out': ['outPort1', 'outPort2'], \
                 'vtTmr' : 'timer1' }``
        """

        for el_type, names in elems.items():
            if isinstance(names, str):
                names = [names]  # make a list if only a string is given

            if el_type == 'vtTmr':
                self.create_vt_timers(names)
            else:
                self.create_ports(el_type, names)

    def _thread_control_port_recv(self, _, msg):
        self._scheduler.vt_remote_control(self, msg)
