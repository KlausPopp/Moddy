'''
Created on 04.01.2017

@author: klaus popp
'''
import threading
from moddy.simulator import simPart
from moddy.vthread import vThread

class vtSchedRtos(simPart):
    '''
    RTOS scheduler for vThreads
    Behaves as a typical, simple RTOS
    
    16 thread priorities - 0 is highest priority
    priority based scheduling. Low prio threads run only if no higher thread ready.
    Threads with same priority will be scheduled round robin (when one of the same prio threads
    releases the processor, the next same prio thread which is ready is selected)
    
    The scheduler tracks the currently ready tasks in the <_readyVThreads> list of lists.
    A list of all vThreads is maintained in <_listVThreads>
    
    '''
    numPrio = 16
    schedVThreadComTimeout = 2.0 # seconds

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
        # TODO: Check if the thread is already added
        if vThread in self._listVThreads:
            raise ValueError('vThread already added')
        
                   
        self._listVThreads.append(vThread)
        
        # add scheduler members to vThread
        vThread._scheduler = self
        vThread._scPrio = prio
        vThread._scState = 'INIT'
        vThread._scIsPythonThreadStarted = False
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
    
        self.vtStateMachine(vThread, 'init')
    
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
        if not vThread._scIsPythonThreadStarted:
            # first time, start python thread
            vThread._scIsPythonThreadStarted = True
            vThread.start()
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
                
            else:
                raise ValueError('Illegal syscall %s' % sysCallName)
    
            if timer is not None:
                vThread._scSysCallTimer.start(timer)
            self.schedule()
        else:
            # Timeout waiting for thread to issue sysCall
            print("Timeout waiting for vThread %s to issue sysCall" % vThread.objName())
            if vThread.is_alive():
                raise RuntimeError("Timeout waiting for vThread %s to issue sysCall" % vThread.objName())
            else:
                # VThread stopped
                vThread.setStateIndicator("TERM")

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
            if event is None or event in vThread._scWaitEvents:
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
            "run"
            "wait"
            "preempt"
            "wake"
            
        Return True if state changed

        vThread State Machine

         INIT
          v  <init>
        READY <--------------------------+<--------------------+
          | <run>                        |                     |
          v                              |<preempt>            | <wake>
        RUNNING--------------------------+                     |
          | <wait>                                             |
          v                                                    |
        WAITING -----------------------------------------------+
        
        '''
        print("  vtSmac %s %s %s" % (vThread.objName(), vThread._scState, event))
        oldState = vThread._scState
        newState = oldState
        
        if oldState == 'INIT':
            if event == 'init':
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
                print( "     preempt remain=%f %f" % (vThread._scRemainBusyTime, vThread._scBusyStartTime))
                assert(vThread._scRemainBusyTime >= 0)
                vThread._scSysCallTimer.stop()
                newState = 'READY'
        
        elif oldState == 'WAITING':
            if event == 'wake':
                newState = 'READY'
        
        #
        # Perform State entry/exit actions
        #
        if oldState != newState:

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
            if vt._scIsPythonThreadStarted is True:
                vt._scCallReturnVal = 'exit'    # tell vThreads to exit. Causes a TerminateException() in user code
                vt._scReturnEvent.set()
            
    #
    # Methods to be called from a vThread thread context
    #
    def sysCall(self, vThread, call, args):
        '''
        Called in vThread context to execute a system call, which may cause re-scheduling
        call -- string with system call 'busy', 'wait'
        args -- list of arguments to system call
        returns when scheduler schedules vThread again
        returns the list of return values from scheduler
        '''
        # invoke system call
        assert(vThread._scPendingCall is None)
        vThread._scPendingCall = (call, args)
        vThread._scCallReturnVal = None
        #print("  VT:sysCall exec",call,args)
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
        #print("  VT:sysCall ret",call,vThread._scCallReturnVal)
        if vThread._scCallReturnVal == 'exit':
            raise vThread.TerminateException()
        
        vThread._scPendingCall = None
        return vThread._scCallReturnVal
        
class vSimpleProg(vThread):
    ''' A special version of a vThread that has its own scheduler and no concurrency '''
    
    def __init__(self, sim, **vThreadArgs):
        ''' See vThread.__init__ for arguments '''
        vThread.__init__(self, sim, **vThreadArgs )
        sched= vtSchedRtos(sim=sim, objName="sched", parentObj=self)
        sched.addVThread(self, 0)
        

        
#
# Test code
#
if __name__ == '__main__':
    from moddy.simulator import sim
    import moddy.svgSeqD
    busyAppearance = {'boxStrokeColor':'blue', 'boxFillColor':'green', 'textColor':'white'}
 
    
    def testScheduling():
        
        class myThread1(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='hiThread', parentObj=None)
            def runVThread(self):
                print("   VtHi1")
                self.busy(50,'1',busyAppearance)
                print("   VtHi2")
                self.wait(20,[])
                print("   VtHi3")
                self.busy(10,'2',busyAppearance)
                print("   VtHi4")
                self.wait(100,[])
                print("   VtHi5")
                self.wait(100,[])
                while True:
                    print("   VtHi5")
                    self.busy(10,'3',busyAppearance)
                    self.wait(5,[])
    
        class myThread2(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='lowThreadA', parentObj=None)
            def runVThread(self):
                print("   VtLoA1")
                self.busy(50,'1',busyAppearance)
                print("   VtLoA2")
                self.wait(20,[])
                print("   VtLoA3")
                self.busy(20,'2',busyAppearance)
                print("   VtLoA4")
                self.busy(250,'3',busyAppearance)
            
        class myThread3(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='lowThreadB', parentObj=None)
            def runVThread(self):
                print("   VtLoB1")
                self.busy(50,'1',busyAppearance)
                print("   VtLoB2")
                self.wait(20,[])
                print("   VtLoB3")
                self.busy(100,'2',busyAppearance)
                print("   VtLoB4")
                self.busy(250,'3',busyAppearance)
    
        simu = sim()
        sched= vtSchedRtos(sim=simu, objName="sched", parentObj=None)
                
        t1 = myThread1(simu)
        t2 = myThread2(simu)
        t3 = myThread3(simu)
        sched.addVThread(t1, 0)
        sched.addVThread(t2, 1)
        sched.addVThread(t3, 1)
        simu.run(400)
        
        sd = moddy.svgSeqD.svgSeqD(evList=simu.tracedEvents(), 
                                    timePerDiv = 10, pixPerDiv = 30)
        
        sd.addParts([sched,t1,t2,t3])
        
        
        # generate drawing
        sd.draw()
        
        sd.save("sched.html","svgInHtml")

    def testQueingPort():
        class myThread1(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Thread', parentObj=None)
                self.createPorts('QueingIn', ['inP1'])
            
            def getAllMsg(self):
                lstMsg = []
                while True:
                    try:
                        msg = self.inP1.readMsg()
                        lstMsg.append(msg)
                    except BufferError:
                        break
                
                self.addAnnotation(lstMsg)
         
             
            def runVThread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.busy(33,cycle,busyAppearance)
                    self.getAllMsg()
                    self.wait(20,[self.inP1])
                    self.getAllMsg()


        class stimThread(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Stim', parentObj=None)
                self.createPorts('out', ['toT1Port'])
                                
            def runVThread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15,[])
                    self.toT1Port.send('hello%d' % count,5)


        simu = sim()
                        
        t1 = myThread1(simu)
        
        stim = stimThread(simu)
        stim.toT1Port.bind(t1.inP1)
        
        simu.run(200)
        
        sd = moddy.svgSeqD.svgSeqD(evList=simu.tracedEvents(), 
                                    timePerDiv = 10, pixPerDiv = 30)
        
        sd.addParts([stim,t1])
        
        
        # generate drawing
        sd.draw()
        
        sd.save("sched.html","svgInHtml")
    
    
    def testSamplingPort():
        class myThread1(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Thread', parentObj=None)
                self.createPorts('SamplingIn', ['inP1'])
                
            def showMsg(self):
                try:
                    msg = self.inP1.readMsg()
                except BufferError:
                    msg = 'No message'
                self.addAnnotation(msg)
                
            def runVThread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.showMsg()
                    self.busy(18,cycle,busyAppearance)
                    self.showMsg()
                    self.busy(14,cycle,busyAppearance)
                    self.wait(20,[self.inP1])


        class stimThread(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Stim', parentObj=None)
                self.createPorts('out', ['toT1Port'])
                                
            def runVThread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15,[])
                    self.toT1Port.send('hello%d' % count,5)


        simu = sim()
        sched= vtSchedRtos(sim=simu, objName="sched", parentObj=None)
        schedStim = vtSchedRtos(sim=simu, objName="schedStim", parentObj=None)
                        
        t1 = myThread1(simu)
        sched.addVThread(t1, 0)
        
        stim = stimThread(simu)
        schedStim.addVThread(stim, 0)
        stim.toT1Port.bind(t1.inP1)
        
        simu.run(200)
        
        sd = moddy.svgSeqD.svgSeqD(evList=simu.tracedEvents(), 
                                    timePerDiv = 10, pixPerDiv = 30)
        
        sd.addParts([stim,t1])
        
        
        # generate drawing
        sd.draw()
        
        sd.save("sched.html","svgInHtml")        

    def testVtTimer():
        class myThread1(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Thread', parentObj=None)
                self.createTimers(['tmr1'])
                
            def runVThread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.tmr1.start(16)
                    self.busy(18,cycle,busyAppearance)
                    self.addAnnotation("A Fired " + str(self.tmr1.hasFired()))
                    self.tmr1.start(20)
                    rv = self.wait(100,[self.tmr1])
                    self.addAnnotation("B rv " + rv)
                    self.tmr1.start(20)
                    rv = self.wait(30,[])
                    self.addAnnotation("C rv " + rv)
                    self.tmr1.start(40)
                    rv = self.wait(30,[self.tmr1])
                    self.addAnnotation("D Fired " + str(self.tmr1.hasFired()) + " rv " + rv)
                    self.tmr1.stop()

        simu = sim()
        sched= vtSchedRtos(sim=simu, objName="sched", parentObj=None)
                        
        t1 = myThread1(simu)
        sched.addVThread(t1, 0)
        
        
        simu.run(200)
        
        sd = moddy.svgSeqD.svgSeqD(evList=simu.tracedEvents(), 
                                    timePerDiv = 10, pixPerDiv = 30)
        
        sd.addParts([t1])
        
        
        # generate drawing
        sd.draw()
        
        sd.save("sched.html","svgInHtml")        
  
    testQueingPort()
    #testSamplingPort()
    #testVtTimer()
    #testScheduling()