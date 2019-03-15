'''
:mod:`vtSchedRtos` -- Moddy RTOS scheduler simulation 
=======================================================================

.. module:: vtSchedRtos
   :platform: Unix, Windows
   :synopsis: Moddy RTOS scheduler simulation
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>
'''
import threading
from moddy.simulator import simPart
from moddy.vthread import vThread

class vtSchedRtos(simPart):
    '''
    RTOS scheduler for vThreads, an instance of a :class:`~.simulator.simPart`
    
    Behaves as a typical, simple RTOS.
    
    * 16 thread priorities - 0 is highest priority.
    * priority based scheduling. Low prio threads run only if no higher thread ready.
    * Threads with same priority will be scheduled round robin (when one of the same prio threads \
    releases the processor, the next same prio thread which is ready is selected)
    
    
    :param sim: Simulator instance
    :param objName: scheduler name
    :param parentObj: parent part. None if scheduler has no parent. 
    
    '''

    # The scheduler tracks the currently ready tasks in the :attr:`_readyVThreads` list of lists.
    # A list of all vThreads is maintained in :attr:`_listVThreads`

    numPrio = 16
    schedVThreadComTimeout = 20.0 # seconds

    #
    # Methods to be called from the Simulator thread
    #
    def __init__(self, sim, objName, parentObj):
                
        # Initialize the parent class
        super().__init__(sim=sim, objName=objName, parentObj=parentObj)
        self._typeStr = "scheduler"     # overwrite "part" (ugly)

        self._listVThreads  = []
        self._readyVThreads = [[] for x in range(self.numPrio)]   # create list of lists, one list for each prio 
        self._scCallEvent   = threading.Event()
        self._runningVThread = None                                 # currently running vThread
    
    def addVThread(self, vThread, prio):
        '''
        :param vThread: thread to be added
        :param prio: priority of the thread 0..15 (0=highest)
        
        Checks :attr:`.vThread.remoteControl`: if True, allow thread state to be controlled through a moddy port `threadControlPort`.
        Those threads are not started automatically, but only via explicit "start" message to the `threadControlPort`.
        Those threads can be killed via "kill" and restarted via "start" message. 
        '''
        if vThread in self._listVThreads:
            raise ValueError('vThread already added')
        
                   
        self._listVThreads.append(vThread)
        
        # add scheduler members to vThread
        vThread._scheduler = self
        vThread._scPrio = prio
        vThread._scState = 'INIT'
        vThread._scRemainBusyTime = 0
        vThread._scBusyStartTime = None
        vThread._scAppStatus = ('',{})              # for status indicator   
        vThread._scLastAppStatus = None           
        vThread._scWaitEvents = None
        vThread._scPendingCall = None
        vThread._scCallReturnVal = None
        vThread._scReturnEvent = threading.Event()
        
        # create a timer for sysCalls 
        vThread._scSysCallTimer = vThread.newTimer(vThread.objName() + "ScTmr" , self.sysCallTmrExpired)
        vThread._scSysCallTimer._scVThread= vThread
    
        if not vThread.remoteControlled:
            self.vtStateMachine(vThread, 'start')
    
    def startSim(self):
        self.schedule()  
        self.updateAllStateIndicators()
        
    def runVThreadTilSysCall(self,vThread):
        '''
        Run the vThread's routine until it executes a syscall
        Then execute the syscall and possible reschedule
        ''' 
        #print("  runVThreadTilSysCall %s %d" % (vThread.objName(), vThread._scIsPythonThreadStarted))
        vThread._scSysCallTimer.stop()
        vThread._scWaitEvents = None
        if not vThread.pythonThreadRunning:
            # first time, start python thread
            vThread.startThread()
        else:
            # wake python thread up from syscall
            assert(vThread._scReturnEvent.isSet() == False)    
            vThread._scReturnEvent.set()


        #
        # wait until vThread executes syscall
        #
        rv = self._scCallEvent.wait(timeout=self.schedVThreadComTimeout)
        if rv == True:
            self._scCallEvent.clear()
            
            # 
            # Execute the sysCall
            # 
            sysCallName = vThread._scPendingCall[0]
            sysCallArg  = vThread._scPendingCall[1]
            
            #print("  runVThreadTilSysCall %s Exec sysCall %s" % (vThread.objName(), sysCallName))
            
            timer = None
            
            if sysCallName == 'busy':
                timer = sysCallArg[0]
                vThread._scAppStatus  = sysCallArg[1]
                vThread._scRemainBusyTime = timer
                vThread._scBusyStartTime = self._sim.time()
                vThread._scCallReturnVal = 'ok'
                
            elif sysCallName == 'wait':
                timer = sysCallArg[0]
                vThread._scWaitEvents = sysCallArg[1]
                self.vtStateMachine(vThread, 'wait')
                vThread._scCallReturnVal = '?'
                
            elif sysCallName == 'term':
                self.vtStateMachine(vThread, 'term')
                # if thread terminated due to an exception, raise also an exception in simulator
                if sysCallArg == 'exception':
                    raise RuntimeError("vThread %s terminated due to an exception" % (vThread.objName()))
            else:
                raise ValueError('Illegal syscall %s' % sysCallName)
    
            if timer is not None:
                vThread._scSysCallTimer.start(timer)
            self.schedule()
        else:
            # Timeout waiting for thread to issue sysCall
            print("Timeout waiting for vThread %s to issue sysCall" % vThread.objName())
            if vThread.pythonThreadRunning:
                raise RuntimeError("Timeout waiting for vThread %s to issue sysCall" % vThread.objName())
            else:
                # VThread stopped
                self.vtStateMachine(vThread, 'term')

    def updateAllStateIndicators(self):
        readyStatusAppearance = {'boxStrokeColor':'grey', 'boxFillColor':'white', 'textColor':'grey'}
        newAppStatus = ('STATE','TEXT','APPEARANCE')
        for vt in self._listVThreads:
            if vt._scState == 'RUNNING':
                newAppStatus = ('running', vt._scAppStatus[0], vt._scAppStatus[1])
            elif vt._scState == 'WAITING':
                newAppStatus = ('waiting', '', {})
            elif vt._scState == 'READY':
                newAppStatus = ('ready', 'PE', readyStatusAppearance)
            elif vt._scState == 'INIT':
                newAppStatus = ('init',  '',  {})

            if vt._scLastAppStatus is None or vt._scLastAppStatus != newAppStatus:
                vt.setStateIndicator(newAppStatus[1], newAppStatus[2] )
                vt._scLastAppStatus = newAppStatus


    def sysCallTmrExpired(self, timer):
        # Called when the sysCall timer of a vThread expired
        # this routine is used for all threads
        vThread = timer._scVThread
        vThread._scRemainBusyTime = 0  
        if vThread._scState == 'WAITING':
            self._wake(vThread, None)
        elif vThread._scState == 'RUNNING':
            self.runVThreadTilSysCall(vThread)
        else:
            raise RuntimeError("sysCallTmrExpired in bad state %s" % vThread._scState)
        self.updateAllStateIndicators()
    
    def wake(self, vThread, event):
        self._wake(vThread,event)
        self.updateAllStateIndicators()
        
    def _wake(self, vThread, event):
        '''
        Called in context of simulator to wakeup a vThread
        event is the event that caused the wakeup
        If event is None, it signals that the wake is caused by timeout
        '''
        if vThread._scWaitEvents is not None:
            ioPortEvent = None
            if event is not None:
                # allow user to specify an ioPort to wait for
                if hasattr(event, "_ioPort"):
                    ioPortEvent = event._ioPort
            
            if event is None or event in vThread._scWaitEvents or \
                (ioPortEvent is not None and ioPortEvent in vThread._scWaitEvents):
                
                if event is None:
                    vThread._scCallReturnVal = 'timeout'
                else:
                    vThread._scCallReturnVal = 'ok'
                    
                self.vtStateMachine(vThread, 'wake')
                self.schedule()
    
    def _highestReadyVThread(self):
        highest = None
        
        for prio in range(self.numPrio):
            if len(self._readyVThreads[prio]) > 0:
                #print("_highestReadyVThread ", prio, self._readyVThreads[prio])
                highest = self._readyVThreads[prio][0]
                break
        
        return highest
                 
    def schedule(self):
        '''
        Evaluate which ready vThread has highest priority.
        If this is another vThread than the currently running vThread:
            preempt the running vThread, i.e. determine remaining busy time.
            put running vThread back to _listVThreads
            make the new vThread the current one
            run new vThread until sysCall, and execute the sysCall
        '''

        highestReadyVt = self._highestReadyVThread()
        newVt = None

        if self._runningVThread is None:
            if highestReadyVt is not None:
                newVt = highestReadyVt
                #print(" schedule1: highest=%s" % (newVt.objName() ))
            else:
                #print(" schedule2")
                pass
        else:
            # there is a running vThread
            if highestReadyVt is None:
                newVt = self._runningVThread
                #print(" schedule3: old=%s" % (newVt.objName() ))
            else:
                if highestReadyVt._scPrio < self._runningVThread._scPrio:
                    newVt = highestReadyVt
                    #print(" schedule4: highest=%s" % (newVt.objName() ))
                else:
                    newVt = self._runningVThread
                    #print(" schedule5:")
        
        if newVt is not self._runningVThread:
            if self._runningVThread is not None:
                oldVt = self._runningVThread
                self.vtStateMachine(oldVt, 'preempt')

                
            if newVt is not None:
                #print(" newVt is %s busytime=%f" % (newVt.objName(), newVt._scRemainBusyTime))
                self.vtStateMachine(newVt, 'run')
                if newVt._scRemainBusyTime  == 0:
                    self.runVThreadTilSysCall(newVt)
                else:
                    # finish busy time
                    newVt._scSysCallTimer.start(newVt._scRemainBusyTime )
        
    
    def vtStateMachine(self,vThread,event):
        '''
        Change state of vThread based on <event>
        <event> is one of
            "start"
            "run"
            "wait"
            "preempt"
            "wake"
            "term"
            
        Return True if state changed

        vThread State Machine

            +-------->INIT
            |          | <start>
            |          v  
            |<-<term>-READY <--------------------------+<--------------------+
            |          | <run>                         |                     |
            |          v                               |<preempt>            | <wake>
            |<-<term>-RUNNING--------------------------+                     |
            |          | <wait>                                              |
            |          v                                                     |
            |<-<term>-WAITING -----------------------------------------------+
                                  
        '''
        #print("  vtSmac %s %s %s" % (vThread.objName(), vThread._scState, event))
        oldState = vThread._scState
        newState = oldState
        
        if oldState == 'INIT':
            if event == 'start':
                newState = 'READY'
        
        if oldState == 'READY':
            if event == 'run':
                newState = 'RUNNING'
                vThread._scBusyStartTime = self._sim.time()
        elif oldState == 'RUNNING':
            if event == 'wait':
                newState = 'WAITING'
            elif event == 'preempt':
                elapsed = self._sim.time() - vThread._scBusyStartTime
                vThread._scRemainBusyTime -= elapsed
                #print( "     preempt remain=%f %f" % (vThread._scRemainBusyTime, vThread._scBusyStartTime))
                assert(vThread._scRemainBusyTime >= 0)
                vThread._scSysCallTimer.stop()
                newState = 'READY'
        
        elif oldState == 'WAITING':
            if event == 'wake':
                newState = 'READY'

        if oldState == 'READY' or oldState == 'RUNNING' or oldState == 'WAITING':
            if event == 'term':
                newState= 'INIT'
        
        
        #
        # Perform State entry/exit actions
        #
        if oldState != newState:

            # INIT entry
            if newState == 'INIT':
                self.terminateVThread(vThread, 'kill')

            # RUNNING entry
            if newState == 'RUNNING':
                self._runningVThread = vThread

            
            # RUNNING exit
            if oldState == 'RUNNING':
                self._runningVThread = None
            
            # READY entry
            if newState == 'READY':
                if vThread in self._readyVThreads[vThread._scPrio]:
                    raise ValueError('vThread already in READY list')
                self._readyVThreads[vThread._scPrio].append(vThread)
                
            # READY exit
            if oldState == 'READY':
                # remove from ready lists
                #print("removing vThread %s from ready list" % vThread)
                self._readyVThreads[vThread._scPrio].remove(vThread)
                
            # WAITING entry
            if newState == 'WAITING':
                pass
            
        vThread._scState = newState
        return newState != oldState
        
    
    def terminateSim(self):
        ''' terminate simulation. stop all python processes executing vThreads '''
        for vt in self._listVThreads:
            self.terminateVThread(vt)
            

    def terminateVThread(self, vThread, returnCode='exit'):
        '''
        Terminate a vthread
        '''
        if vThread.pythonThreadRunning:
            #print("Terminate %s" % vThread.objName())
            # tell vThreads to exit. Causes a TerminateException() or KillException in user code
            vThread._scCallReturnVal = returnCode    
            vThread._scReturnEvent.set()
            vThread.waitUntilThreadTerminated()
        
    
    def vtRemoteControl(self, vThread, action):
        if action == 'start':
            self.vtStateMachine(vThread, 'start')
        elif action == 'kill':
            self.vtStateMachine(vThread, 'term')
        else:
            raise RuntimeError("vTRemoteControl %s bad action %s" % (vThread.objName(), action))
        self.schedule()
        self.updateAllStateIndicators()
    
    #
    # Methods to be called from a vThread thread context
    #
    def sysCall(self, vThread, call, args):
        '''
        Called in vThread context to execute a system call, which may cause re-scheduling
        call -- string with system call 'busy', 'wait', 'term'
        args -- list of arguments to system call
        returns when scheduler schedules vThread again
        returns the list of return values from scheduler
        '''
        # invoke system call
        assert(vThread._scPendingCall is None)
        vThread._scPendingCall = (call, args)
        vThread._scCallReturnVal = None
        #print("  VT:sysCall exec",vThread.objName(), call,args)
        self._scCallEvent.set()
        
        # wait until scheduler completed syscall
        rv = vThread._scReturnEvent.wait(timeout=self.schedVThreadComTimeout + 1.0)
        
        if rv == False:
            if vThread._sim.isRunning() == False:
                # Simulator stop, tell thread to exit
                vThread._scCallReturnVal = 'exit'
            else:
                raise RuntimeError("Timeout waiting for scheduler to return from sysCall")
        
        vThread._scReturnEvent.clear()
        #print("  VT:sysCall ret",vThread.objName(), call,vThread._scCallReturnVal)
        pendCall = vThread._scPendingCall[0]
        vThread._scPendingCall = None        
        
        if pendCall != 'term':
            if vThread._scCallReturnVal == 'exit':
                #print("  VT:sysCall raising TerminateException %s %s" % (vThread.objName(),vThread._scPendingCall))
                raise vThread.TerminateException()
            elif vThread._scCallReturnVal == 'kill':
                #print("  VT:sysCall raising KillException %s %s" % (vThread.objName(),vThread._scPendingCall))
                raise vThread.KillException()
        
        return vThread._scCallReturnVal
        
class vSimpleProg(vThread):
    ''' 
    A special version of a vThread that has its own scheduler and no concurrency 

    :param sim: Simulator instance
    :param vThreadArgs: see :class:`.vThread` for parameters

    '''
    
    def __init__(self, sim, **vThreadArgs):
        ''' See vThread.__init__ for arguments '''
        vThread.__init__(self, sim, **vThreadArgs )
        sched= vtSchedRtos(sim=sim, objName="sched", parentObj=self)
        sched.addVThread(self, 0)
        
