'''
:mod:`vthread` -- Moddy virtual threads
=======================================================================

.. module:: vthread
   :platform: Unix, Windows
   :synopsis: Moddy virtual threads
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''

from moddy.simulator import simPart,simInputPort,simTimer,simIOPort
from collections import deque
import threading


class vtInPort(simInputPort):
    '''
    Base class for input ports of vThreads which extends the standard input port:
    
    * buffers the incoming message: vtInport can be a sampling or queuing port
    
        - a :class:`vtSamplingInPort` buffers only the last received message
        - a :class:`vtQueuingInPort` buffers all messages
        
    * wakes up the vThread from :meth:`~.vThread.wait` if the vThread is waiting for input on that port
    * provides an API to read the messages from the buffer 
    '''
    def __init__(self, sim, name, vThread, qDepth):
        '''
        Constructor
        '''
        # no msgReceived function, because msgEvent() is overwritten in subclasses 
        super().__init__( sim, vThread, name, msgReceivedFunc=None)  
        self._vThread = vThread
        self._sampledMsg = deque(maxlen=qDepth)
        
    def wake(self):
        self._vThread._scheduler.wake(self._vThread, self)
    
    def readMsg(self, default=None):
        '''Read a message from the port's buffer. Overwritten by subclass'''
        pass

    def nMsg(self):
        '''Check how many messages are in the port's buffer. Overwritten by subclass'''
        pass

    def clear(self):
        '''clear input port'''
        self._sampledMsg.clear()

class vtSamplingInPort(vtInPort):
    '''
    Sampling input port for vThreads
    A sampling port buffers only the last received message
    A read from the sampling buffer does not consume the buffered message
    
    :param sim: Simulator instance
    :param name: port name
    :param vThread vThread: vThread to which the port shall be added to 
    '''
    def __init__(self, sim, name, vThread):
        super().__init__(sim, name,vThread,qDepth=1)

    def msgEvent(self,msg):
        # overwritten from base simInputPort class!
        #print("vtSamplingInPort inRecv %s %s" % (self,msg))
        if self._vThread.pythonThreadRunning:
            self._sampledMsg.append(msg)
            self.wake()
        
    def readMsg(self, default=None):
        ''' 
        Get current message from sampling buffer.
        The message is not consumed, i.e. if `readMsg` is called again before a new message comes in, the 
        same message is returned.
                    
        :param default: value to return if no message was received at all
        :raise BufferError: if no message was received at all AND `default` is None    
        :return: message in buffer 
        '''
        if len(self._sampledMsg) > 0:
            return self._sampledMsg[0]
        else:
            if default is None:
                raise BufferError("No msg in sampling buffer")
            else:
                return default

    def nMsg(self):
        ''' 
        :return: 1 if message is available, or 0 if not
        '''
        return 1 if len(self._sampledMsg) > 0 else 0

class vtQueuingInPort(vtInPort):
    '''
    Queuing input port for vThreads.
    A queuing port buffers all messages in a fifo queue. The queue depth is infinite.
    A read from the buffer consumes the oldest message.
    
    :param sim: Simulator instance
    :param name: port name
    :param vThread vThread: vThread to which the port shall be added to 
    '''
    def __init__(self, sim, name, vThread):
        super().__init__(sim, name, vThread,qDepth=None)

    def msgEvent(self,msg):
        # overwritten from base simInputPort class!
        #print("vtQueuingInPort inRecv %s %s" % (self,msg))
        if self._vThread.pythonThreadRunning:
            self._sampledMsg.append(msg)
            if len(self._sampledMsg) == 1:
                # wakeup waiting thread if queue changes from empty to one entry
                self.wake()
        
    def readMsg(self, default=None):
        ''' 
        Get first message from queue.
        The message is consumed.
        
        :param default: ignored
        :raise BufferError: if no message in buffer    
        :return: message in buffer 
        '''
        if len(self._sampledMsg) > 0:
            return self._sampledMsg.popleft()
        else:
            raise BufferError("No msg in queue")

    def nMsg(self):
        ''' 
        :return: number of messages in queue
        '''
        return len(self._sampledMsg)
    


class vtIOPort(simIOPort):
    '''
    An IOPort that combines a Sampling/Queuing input port and a standard output port

    :param sim: Simulator instance
    :param name: port name
    :param vThread vThread: vThread to which the port shall be added to
    :param inPort: The input port for the IO-Port. Either :class:`vtSamplingInPort` or :class:`vtQueuingInPort`  
    
    '''
    def __init__(self, sim, name, vThread, inPort):
        super().__init__(sim, vThread, name, msgReceivedFunc=None, specialInPort=inPort)
    
    def readMsg(self, default=None):
        return self._inPort.readMsg(default)
    def nMsg(self):
        return self._inPort.nMsg()
    def clear(self):
        self._inPort.clear()

class vtTimer(simTimer):
    '''
    A timer for vThreads which extends the standard simulation timer

    When the timer expires, it sets a flag, that the user can test with :meth:`hasFired`
    The flag is reset with :meth:`start` and :meth:`restart`
    
    :param sim: Simulator instance
    :param name: timer name
    :param vThread vThread: vThread to which the timer shall be added to 
    '''
    def __init__(self, sim, name, vThread):
        '''
        Constructor
        '''
        super().__init__(sim, vThread, name, self._tmrExpired) 
        self._vThread = vThread
        self._tmrFired = False
        
    def _tmrExpired(self,timer):
        self._tmrFired = True
        self._vThread._scheduler.wake(self._vThread, self)
    
    def hasFired(self):
        '''
        :return: True if timer expired
        '''
        return self._tmrFired

    def start(self, timeout):
        # Override method from simTimer
        self._tmrFired = False
        super().start(timeout)

    def restart(self, timeout):
        # Override method from simTimer
        self._tmrFired = False
        super().restart(timeout)

    
class vThread(simPart):
    '''
    A virtual thread simulating a software running on an operating system.
    The scheduler of the operating system schedules the vthreads.
    
    The simulated software must be written in python and must only call the functions from the scheduler for timing functions:
    
        * :meth:`busy` - tell the scheduler how much time the current operation takes
        * :meth:`wait` - wait for an event: Event can be a timeout, a simulation timer expiration, or a message arriving on an input port  
    
    A vthread is a :class:`~moddy.simulator.simPart` part, which can exchange messages with other simulation parts, 
    but unlike pure simPart parts, 
    
    * the input ports are :class:`vtInPort` that buffer incoming messages

        * a sampling input port (:class:`vtSamplingInPort`) buffers always the latest message
        * a queuing input port (:class:`vtQueuingInPort`) buffers all messages

        vThreads can :func:`wait` for messages. They can read messages from the input ports via
        
        * :meth:`~vtInPort.readMsg` - read one message from port
        * :meth:`~vtInPort.nMsg` - determine how many messages are pending
        
    * the simPart timers are indirectly available to vThreads via vtTimers (set a flag on timeout)
  
    :param sim: Simulator instance
    :param objName: part's name
    :param parentObj: parent part. None if part has no parent. 
    :param bool remoteControl: if True, allow thread state to be controlled through a moddy port "threadControlPort".\
    Those threads are not started automatically, but only via explicit "start" message to the "threadControlPort".\
    Those threads can be killed via "kill" and restarted via "start". 
            
    '''


    def __init__(self, sim, objName, parentObj, remoteControlled=False):
        '''
        Constructor
        '''
        simPart.__init__(self,sim=sim, objName=objName, parentObj=parentObj)
        self.remoteControlled = remoteControlled
        self.pythonThreadRunning = False;
        self.thread = None
        
        if remoteControlled:
            self.createPorts('in', ['threadControlPort'])
        
    def startThread(self):
        if self.thread is not None and self.thread.is_alive():
            raise RuntimeError("startThread: old vThread %s still running" % self.objName())
        self.thread = threading.Thread(target=self.run)
        self.pythonThreadRunning = True;
        self.thread.start()
    
    def waitUntilThreadTerminated(self):
        '''
        To be called from scheduler when it has told the thread to terminate
        @raise RuntimeError: if the thread did not terminate within the timeout 
        '''
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(3.0)
            if self.thread.is_alive():
                raise RuntimeError("waitUntilThreadTerminated: Thread %s did not terminate" % self.objName())

    class TerminateException(Exception):
        """ Exception that is raised to tell the thread that it shall be terminated"""
        pass

    class KillException(Exception):
        pass
    
    def run(self):
        '''
        runs the vthread code
        '''
        if self.remoteControlled: self.addAnnotation('vThread started')
        termReason = None
        try:
            self.runVThread()
            # normal exit
            termReason = "exited normally"
            self.term("exit") # tell scheduler that thread has terminated
        except self.TerminateException:
            # simulator is about to terminate
            termReason = "Terminated"
        except self.KillException:
            # killed by another thread
            termReason = "Killed"
        except:
            termReason = "Exception in runVThread"
            # catch all exceptions coming from the thread's model code
            self.term("exception") # tell scheduler that thread has terminated
            raise # re-raise exception, so that it's printed
        finally:
            self.stopAllTimers()
            self.clearPorts()
            self.pythonThreadRunning = False;
            if termReason != "Terminated":
                self.addAnnotation('vThread %s' % termReason)
    
    def runVThread(self):
        ''' Model code of the VThread. must be overridden by subclass'''
        pass 
    
    def stopAllTimers(self):
        for tmr in self._listTimers:
            tmr.stop()
            
    def clearPorts(self):
        for port in self._listPorts:
            if hasattr(port, 'clear'):
                port.clear()

    def wait(self, timeout, evList=[]):
        '''
        Suspend vThread until one of the events in `evList` occurs or timeout
        
        :param timeout: time to wait for events. If None, wait forever. A timeout value of 0 is invalid.
        :param list evList: list of events to wait for. Events can be :class:`vtSamplingInPort`, \
         :class:`vtQueuingInPort`, :class:`vtIOPort`, or :class:`vtTimer` object. \
         If evList is empty (or omitted), wait for timeout unconditionally.
            
        :return: 'ok' if one of the events has been triggered (it does not tell you which one), 'timeout' if timeout

        :raise TerminateException: if simulator stopped 
        '''
        return self._scheduler.sysCall( self, 'wait', (timeout, evList))
    
    def waitUntil(self, time, evList=[]):
        '''
        Suspend vThread until one of the events in `evList` occurs or until specified time 
        
        :param time: target time. Must be >= current simulation time, otherwise :class:`ValueError` is thrown
        :param list evList: list of events to wait for. Events can be :class:`vtSamplingInPort`, \
         :class:`vtQueuingInPort`, or :class:`vtTimer` object
            
        :return: 'ok' if one of the events has been triggered, 'timeout' if timeout

        :raise TerminateException: if simulator stopped 
        :raise ValueError: if target time already gone 
        '''
        if time < self.time():
            raise ValueError("waitUntil: target time already gone")
        return self.wait( time-self.time(), evList)
    
    def busy(self, time, status, statusAppearance={}):
        '''
        tell the scheduler how much time the current operation takes
        
        :param time: the busy time. May be 0
        :param status: the status text shown on the sequence diagram life line
        :param statusAppearance: defines the decoration of the status box in the sequence diagram.
            See svgSeqD.statusBox
        :return: always 'ok' 
        :raise TerminateException: if simulator stopped
        
        '''
        return self._scheduler.sysCall(self, 'busy', (time, (status, statusAppearance)))
    
    def term(self, termReason):
        '''
        Terminate thread
        '''
        return self._scheduler.sysCall( self, 'term', (termReason) )
    
    def newVtSamplingInPort(self, name):
        """ 
        Add a new sampling input port (:class:`vtSamplingInPort`) to the part 
        
        :param name: name of port
        """

        port = vtSamplingInPort(self._sim, name, self)
        self.addInputPort(port)
        return port
        
    def newVtQueuingInPort(self, name):
        """ 
        Add a new queueing input port (:class:`vtQueuingInPort`) to the part 
        
        :param name: name of port
        """
        port = vtQueuingInPort(self._sim, name, self)
        self.addInputPort(port) 
        return port
    
    def newVtSamplingIOPort(self, name):
        """ 
        Add a new sampling I/O port (via :class:`vtIOPort`) to the part 
        
        :param name: name of port
        """
        port = vtIOPort(self._sim, name, self, vtSamplingInPort(self._sim, name, self))
        self.addIOPort(port)
        return port

    def newVtQueuingIOPort(self, name):
        """ 
        Add a new queueing I/O port(via :class:`vtIOPort`)  to the part 
        
        :param name: name of port
        """
        port = vtIOPort(self._sim, name, self, vtQueuingInPort(self._sim, name, self))
        self.addIOPort(port)
        return port
        

    def newVtTimer(self, name):
        """ 
        Add a new virtual timer to the part 
        
        :param name: name of timer
        """
        timer = vtTimer(self._sim, name, self)
        self.addTimer(timer)
        return timer
    
    def createPorts(self, ptype, listPortNames):
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
        :param list listPortNames: list of port names to create
         
        The function creates for each port a member variable with this name in the part.
        '''
        if ptype == 'SamplingIn':
            for portName in listPortNames:
                setattr(self, portName, self.newVtSamplingInPort(portName))
        elif ptype == 'QueuingIn' or ptype == 'QueingIn': # support also the old, mis-spelled name
            for portName in listPortNames:
                setattr(self, portName, self.newVtQueuingInPort(portName))
        elif ptype == 'SamplingIO':
            for portName in listPortNames:
                setattr(self, portName, self.newVtSamplingIOPort(portName))
        elif ptype == 'QueuingIO' or ptype == 'QueingIO': # support also the old, mis-spelled name
            for portName in listPortNames:
                setattr(self, portName, self.newVtQueuingIOPort(portName))
        else:
            simPart.createPorts(self, ptype, listPortNames)
            
    def createVtTimers(self, listTimerNames):
        '''
        Convinience functions to create multiple vtTimers at once.
        
        :param listTimerNames: list of timers to create 

        The function creates for each port a member variable with this name in the part.
        '''
        for tmrName in listTimerNames:
            exec('self.%s = self.newVtTimer("%s")' % (tmrName,tmrName)) 
       
    
    def threadControlPortRecv(self, port, msg):
        self._scheduler.vtRemoteControl(self,msg)
            
            
            