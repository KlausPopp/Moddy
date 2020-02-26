'''
:mod:`vtSchedRtos` -- Moddy RTOS scheduler simulation
=======================================================================

.. module:: vtSchedRtos
   :platform: Unix, Windows
   :synopsis: Moddy RTOS scheduler simulation
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>
'''
import threading
from .sim_part import SimPart
from .vthread import VThread


class SchedRtosData:
    # pylint: disable=too-few-public-methods, too-many-instance-attributes
    '''
    An instance of this class is stored in the vthread's sched_data member
    '''

    def __init__(self, prio, tmr):
        self.reset()
        self.prio = prio
        self.state = 'INIT'
        self.call_return_val = None
        self.return_event = threading.Event()
        self.sys_call_timer = tmr

    def reset(self):
        ''' Reset the sched data to defaults '''
        self.remain_busy_time = 0
        self.busy_start_time = None
        self.app_status = ('', {})  # for status indicator
        self.last_app_status = None
        self.wait_events = None
        self.pending_call = None


class VtSchedRtos(SimPart):
    '''
    RTOS scheduler for vThreads, an instance of a :class:`~.sim_part.SimPart`

    Behaves as a typical, simple RTOS.

    * 16 thread priorities - 0 is highest priority.
    * priority based scheduling. Low prio threads run only if no higher
      thread ready.
    * Threads with same priority will be scheduled round robin \
        (when one of the same prio threads \
        releases the processor, the next same prio \
        thread which is ready is selected)


    :param sim: Simulator instance
    :param obj_name: scheduler name
    :param parent_obj: parent part. None if scheduler has no parent.

    '''

    # The scheduler tracks the currently ready tasks in the
    # :attr:`_readyVThreads` list of lists.
    # A list of all vThreads is maintained in :attr:`_listVThreads`

    num_prio = 16
    sched_vthread_com_timeout = None

    #
    # Methods to be called from the Simulator thread
    #
    def __init__(self, sim, obj_name, parent_obj):

        # Initialize the parent class
        super().__init__(sim=sim, obj_name=obj_name, parent_obj=parent_obj)
        self._type_str = "scheduler"  # overwrite "part" (ugly)

        self._list_vthreads = []
        # create list of lists, one list for each prio
        self._ready_vthreads = [[] for _ in range(self.num_prio)]
        self._sc_call_event = threading.Event()
        # currently running v_thread
        self._running_vthread = None

    def add_vthread(self, v_thread, prio):
        '''
        :param v_thread: thread to be added
        :param prio: priority of the thread 0..15 (0=highest)

        Checks :attr:`.v_thread.remoteControl`: if True, allow thread state
        to be controlled through a moddy port `threadControlPort`.
        Those threads are not started automatically, but only via explicit
        "start" message to the `threadControlPort`.
        Those threads can be killed via "kill" and restarted via "start"
        message.
        '''
        if v_thread in self._list_vthreads:
            raise ValueError('v_thread already added')

        self._list_vthreads.append(v_thread)

        # create a timer for sysCalls
        tmr = v_thread.new_timer(
            v_thread.obj_name() + "ScTmr", self._sys_call_tmr_expired)
        # Store a ref. to this vthread in the timer
        tmr.sched_data_v_thread = v_thread

        # add scheduler members to v_thread
        v_thread.set_scheduler(self, SchedRtosData(prio, tmr))

        if not v_thread.remote_controlled:
            self.vt_state_machine(v_thread, 'start')

    def start_sim(self):
        self.schedule()
        self._update_all_state_indicators()

    def run_vthread_til_sys_call(self, v_thread):
        '''
        Run the v_thread's routine until it executes a syscall
        Then execute the syscall and possible reschedule
        '''
        sched_data = v_thread.sched_data
        # print("  run_vthread_til_sys_call %s %d" % (v_thread.obj_name(),
        # v_thread._scIsPythonThreadStarted))
        sched_data.sys_call_timer.stop()
        sched_data.wait_events = None

        if not v_thread.python_thread_running:
            # first time, start python thread
            v_thread.start_thread()
        else:
            # wake python thread up from syscall
            if sched_data.return_event.isSet():
                raise RuntimeError("%s return event is set" % (v_thread))

            sched_data.return_event.set()

        #
        # wait until v_thread executes syscall
        #
        ret_val = \
            self._sc_call_event.wait(timeout=self.sched_vthread_com_timeout)

        if ret_val:
            self._sc_call_event.clear()

            #
            # Execute the sys_call
            #
            self._exec_syscall(v_thread)
        else:
            # Timeout waiting for thread to issue sys_call
            print("Timeout waiting for v_thread %s to issue sys_call" %
                  v_thread)
            if v_thread.python_thread_running:
                raise RuntimeError(
                    "Timeout waiting for v_thread %s to issue sys_call" %
                    (v_thread))
            # VThread stopped
            self.vt_state_machine(v_thread, 'term')

    def _exec_syscall(self, v_thread):
        sched_data = v_thread.sched_data
        #
        # Execute the sys_call
        #
        sys_call_name = sched_data.pending_call[0]
        sys_call_arg = sched_data.pending_call[1]

        # print("  run_vthread_til_sys_call %s Exec sys_call %s" %
        # (v_thread, sys_call_name))

        timer = None

        if sys_call_name == 'busy':
            timer = sys_call_arg[0]
            sched_data.app_status = sys_call_arg[1]
            sched_data.remain_busy_time = timer
            sched_data.busy_start_time = self._sim.time()
            sched_data.call_return_val = 'ok'

        elif sys_call_name == 'wait':
            timer = sys_call_arg[0]
            sched_data.wait_events = sys_call_arg[1]
            self.vt_state_machine(v_thread, 'wait')
            sched_data.call_return_val = '?'

        elif sys_call_name == 'term':
            self.vt_state_machine(v_thread, 'term')
            # if thread terminated due to an exception,
            # raise also an exception in simulator
            if sys_call_arg == 'exception':
                raise RuntimeError(
                    "v_thread %s terminated due to an exception" % (v_thread))
        else:
            raise ValueError('Illegal syscall %s' % sys_call_name)

        if timer is not None:
            sched_data.sys_call_timer.start(timer)
        self.schedule()

    def _update_all_state_indicators(self):
        ready_status_appearance = {
            'boxStrokeColor': 'grey',
            'boxFillColor': 'white',
            'textColor': 'grey'}

        new_app_status = ('STATE', 'TEXT', 'APPEARANCE')
        for v_thread in self._list_vthreads:
            if v_thread.sched_data.state == 'RUNNING':
                new_app_status = (
                    'running',
                    v_thread.sched_data.app_status[0],
                    v_thread.sched_data.app_status[1])
            elif v_thread.sched_data.state == 'WAITING':
                new_app_status = ('waiting', '', {})
            elif v_thread.sched_data.state == 'READY':
                new_app_status = ('ready', 'PE', ready_status_appearance)
            elif v_thread.sched_data.state == 'INIT':
                new_app_status = ('init', '', {})

            if v_thread.sched_data.last_app_status is None or \
                    v_thread.sched_data.last_app_status != new_app_status:

                v_thread.set_state_indicator(new_app_status[1],
                                             new_app_status[2])
                v_thread.sched_data.last_app_status = new_app_status

    def _sys_call_tmr_expired(self, timer):
        '''
        Called when the sys_call timer of a v_thread expired
        this routine is used for all threads
        '''
        v_thread = timer.sched_data_v_thread
        v_thread.sched_data.remain_busy_time = 0
        if v_thread.sched_data.state == 'WAITING':
            self._wake(v_thread, None)
        elif v_thread.sched_data.state == 'RUNNING':
            self.run_vthread_til_sys_call(v_thread)
        else:
            raise RuntimeError(
                "_sys_call_tmr_expired in bad state %s" %
                (v_thread.sched_data.state))
        self._update_all_state_indicators()

    def wake(self, v_thread, event):
        '''
        Called in context of simulator to wakeup a v_thread
        event is the event that caused the wakeup
        If event is None, it signals that the wake is caused by timeout
        '''
        self._wake(v_thread, event)
        self._update_all_state_indicators()

    def _wake(self, v_thread, event):

        if v_thread.sched_data.wait_events is not None:
            io_port_event = None
            if event is not None:
                # allow user to specify an ioPort to wait for
                if hasattr(event, "io_port"):
                    io_port_event = event.io_port()

            if event is None or event in v_thread.sched_data.wait_events or \
                    (io_port_event is not None and
                     io_port_event in v_thread.sched_data.wait_events):

                if event is None:
                    v_thread.sched_data.call_return_val = 'timeout'
                else:
                    v_thread.sched_data.call_return_val = 'ok'

                self.vt_state_machine(v_thread, 'wake')
                self.schedule()

    def _highest_ready_vthread(self):
        highest = None

        for prio in range(self.num_prio):
            if len(self._ready_vthreads[prio]) > 0:
                # print("_highest_ready_vthread ", prio,
                # self._readyVThreads[prio])
                highest = self._ready_vthreads[prio][0]
                break

        return highest

    def schedule(self):
        '''
        Evaluate which ready vThread has highest priority.
        If this is another vThread than the currently running vThread:
            preempt the running vThread, i.e. determine remaining busy time.
            put running vThread back to _listVThreads
            make the new vThread the current one
            run new vThread until sys_call, and execute the sys_call
        '''

        highest_ready_vt = self._highest_ready_vthread()
        new_vt = None

        if self._running_vthread is None:
            if highest_ready_vt is not None:
                new_vt = highest_ready_vt
                # print(" schedule1: highest=%s" % (new_vt.obj_name() ))
            else:
                # print(" schedule2")
                pass
        else:
            # there is a running vThread
            if highest_ready_vt is None:
                new_vt = self._running_vthread
                # print(" schedule3: old=%s" % (new_vt.obj_name() ))
            else:
                if highest_ready_vt.sched_data.prio < \
                     self._running_vthread.sched_data.prio:

                    new_vt = highest_ready_vt
                    # print(" schedule4: highest=%s" % (new_vt.obj_name() ))
                else:
                    new_vt = self._running_vthread
                    # print(" schedule5:")

        if new_vt is not self._running_vthread:
            if self._running_vthread is not None:
                old_vt = self._running_vthread
                self.vt_state_machine(old_vt, 'preempt')

            if new_vt is not None:
                # print(" new_vt is %s busytime=%f" % (new_vt.obj_name(),
                # new_vt.sched_data.remain_busy_time))
                self.vt_state_machine(new_vt, 'run')
                if new_vt.sched_data.remain_busy_time == 0:
                    self.run_vthread_til_sys_call(new_vt)
                else:
                    # finish busy time
                    new_vt.sched_data.sys_call_timer.start(
                        new_vt.sched_data.remain_busy_time)

    def vt_state_machine(self, v_thread, event):
        # pylint: disable=too-many-branches
        '''
        Change state of v_thread based on <event>
        <event> is one of
            "start"
            "run"
            "wait"
            "preempt"
            "wake"
            "term"

        Return True if state changed

        v_thread State Machine

            +-------->INIT
            |          | <start>
            |          v
            |<-<term>-READY <--------------------------+<--------------------+
            |          | <run>                         |                     |
            |          v                               |<preempt>      <wake>|
            |<-<term>-RUNNING--------------------------+                     |
            |          | <wait>                                              |
            |          v                                                     |
            |<-<term>-WAITING -----------------------------------------------+

        '''
        # print("  vtSmac %s %s %s" % (v_thread,
        # v_thread.sched_data.state, event))
        old_state = v_thread.sched_data.state
        new_state = old_state

        if old_state == 'INIT':
            if event == 'start':
                new_state = 'READY'

        if old_state == 'READY':
            if event == 'run':
                new_state = 'RUNNING'
                v_thread.sched_data.busy_start_time = self._sim.time()
        elif old_state == 'RUNNING':
            if event == 'wait':
                new_state = 'WAITING'
            elif event == 'preempt':
                elapsed = self._sim.time() - \
                    v_thread.sched_data.busy_start_time
                v_thread.sched_data.remain_busy_time -= elapsed
                # print( "     preempt remain=%f %f" %
                # (v_thread.sched_data.remain_busy_time,
                # v_thread.sched_data.busy_start_time))
                if v_thread.sched_data.remain_busy_time < 0:
                    raise RuntimeError("vThread busy time negative")
                v_thread.sched_data.sys_call_timer.stop()
                new_state = 'READY'

        elif old_state == 'WAITING':
            if event == 'wake':
                new_state = 'READY'

        if old_state in ('READY', 'RUNNING', 'WAITING'):
            if event == 'term':
                new_state = 'INIT'

        #
        # Perform State entry/exit actions
        #
        if old_state != new_state:
            self._sm_actions(v_thread, new_state, old_state)

        v_thread.sched_data.state = new_state
        return new_state != old_state

    def _sm_actions(self, v_thread, new_state, old_state):
        # INIT entry
        if new_state == 'INIT':
            self.terminate_vthread(v_thread, 'kill')

        # RUNNING entry
        if new_state == 'RUNNING':
            self._running_vthread = v_thread

        # RUNNING exit
        if old_state == 'RUNNING':
            self._running_vthread = None

        # READY entry
        if new_state == 'READY':
            if v_thread in self._ready_vthreads[v_thread.sched_data.prio]:
                raise ValueError('v_thread already in READY list')
            self._ready_vthreads[v_thread.sched_data.prio].append(v_thread)

        # READY exit
        if old_state == 'READY':
            # remove from ready lists
            # print("removing v_thread %s from ready list" % v_thread)
            self._ready_vthreads[v_thread.sched_data.prio].remove(v_thread)

        # WAITING entry
        if new_state == 'WAITING':
            pass

    def terminate_sim(self):
        '''
        terminate simulation.
        stop all python processes executing vThreads
        '''
        for v_thread in self._list_vthreads:
            self.terminate_vthread(v_thread)

    @staticmethod
    def terminate_vthread(v_thread, return_code='exit'):
        '''
        Terminate a vthread
        '''
        if v_thread.python_thread_running:
            # print("Terminate %s" % v_thread.obj_name())
            # tell vThreads to exit. Causes a TerminateException()
            # or KillException in user code
            v_thread.sched_data.call_return_val = return_code
            v_thread.sched_data.return_event.set()
            v_thread.wait_until_thread_terminated()

            v_thread.sched_data.reset()

    def vt_remote_control(self, v_thread, action):
        '''
        Remote control thread state
        :param action: 'start' or 'term'
        '''
        if action == 'start':
            self.vt_state_machine(v_thread, 'start')
        elif action == 'kill':
            self.vt_state_machine(v_thread, 'term')
        else:
            raise RuntimeError("vTRemoteControl %s bad action %s" %
                               (v_thread, action))
        self.schedule()
        self._update_all_state_indicators()

    #
    # Methods to be called from a vthread thread context
    #
    def sys_call(self, v_thread, call, args):
        '''
        Called in v_thread context to execute a system call,
        which may cause re-scheduling
        :param call: string with system call 'busy', 'wait', 'term'
        :param args: list of arguments to system call
        returns when scheduler schedules v_thread again
        :return: the list of return values from scheduler
        '''
        # invoke system call
        if v_thread.sched_data.pending_call is not None:
            raise RuntimeError("syscall still pending for %s " % (v_thread))
        v_thread.sched_data.pending_call = (call, args)
        v_thread.sched_data.call_return_val = None
        # print("  VT:sys_call exec",v_thread.obj_name(), call,args)
        self._sc_call_event.set()

        # wait until scheduler completed syscall
        ret_val = v_thread.sched_data.return_event.wait(
            timeout=self.sched_vthread_com_timeout + 1.0
            if self.sched_vthread_com_timeout is not None else None)

        if not ret_val:
            if not self._sim.isRunning():

                # Simulator stop, tell thread to exit
                v_thread.sched_data.call_return_val = 'exit'
            else:
                raise RuntimeError(
                    "%s: Timeout waiting for scheduler to return "
                    "from sys_call" % (v_thread))

        v_thread.sched_data.return_event.clear()
        # print("  VT:sys_call ret",v_thread,
        # call,v_thread.sched_data.call_return_val)

        pend_call = v_thread.sched_data.pending_call[0]
        v_thread.sched_data.pending_call = None

        if pend_call != 'term':
            if v_thread.sched_data.call_return_val == 'exit':
                # print("  VT:sys_call raising TerminateException %s %s" %
                # (v_thread,v_thread.sched_data.pending_call))
                raise v_thread.TerminateException()
            if v_thread.sched_data.call_return_val == 'kill':
                # print("  VT:sys_call raising KillException %s %s" %
                # (v_thread,v_thread.sched_data.pending_call))
                raise v_thread.KillException()

        return v_thread.sched_data.call_return_val

    @staticmethod
    def vthread_can_receive_messages(v_thread):
        '''
        Return true if the v_thread is in a state in which it can receive
        moddy messages
        '''
        return v_thread.sched_data.state != 'INIT'


class VSimpleProg(VThread):
    '''
    A special version of a vThread that has its own scheduler and no
    concurrency

    :param sim: Simulator instance
    :param vThreadArgs: see :class:`.vThread` for parameters

    '''

    def __init__(self, sim, **v_thread_args):
        ''' See v_thread.__init__ for arguments '''
        super().__init__(sim, **v_thread_args)
        sched = VtSchedRtos(sim=sim, obj_name="sched", parent_obj=self)
        sched.add_vthread(self, 0)
