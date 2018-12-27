'''
Moddy - Python system simulator
 
'''
from copy import deepcopy
from moddy import ms,us,ns,VERSION
from heapq import heappush, heappop
from collections import deque  
from datetime import datetime
import sys, inspect, os
import pickle

def timeUnit2Factor(unit):
    """Convert time unit to factor"""
    if unit=="s":      factor = 1.0
    elif unit == "ms": factor = ms
    elif unit == "us": factor = us
    elif unit == "ns": factor = ns
    else: assert(False),"Illegal time unit " + unit
    return factor
  


class simBaseElement:
    def __init__(self, sim, parentObj, objName, typeStr):
        self._sim = sim
        self._parentObj = parentObj
        self._objName = objName
        self._typeStr = typeStr
    
    def hierarchyName(self):
        '''
        Return the element name within the hierarchy.
        E.g. Top.Lower.myName
        '''
        if self._parentObj is None:
            return self._objName
        else:
            return self._parentObj.hierarchyName() + "." + self._objName

    def hierarchyNameWithType(self):
        '''
        Return the element name within the hierarch including the element type
        E.g. "Top.Lower.myName (Inport)"
        '''
        return self.hierarchyName() + "(" + self._typeStr + ")"
    
    def objName(self):
        return self._objName


class simPart(simBaseElement):
    """Simulator block"""
    def __init__(self, sim, objName, parentObj = None ):
        super().__init__(sim, parentObj, objName, "Part")
        self._listPorts = []
        self._listTimers = []
        self._listSubParts = []     # child parts list
        self._listVarWatchers = []
        if not parentObj is None:
            parentObj.addSubPart(self) 
        sim.addPart(self)
    
    def addSubPart(self, subPart):
        '''add subPart to list of subParts '''
        assert( subPart not in self._listSubParts)
        self._listSubParts.append(subPart)
        
    def addAnnotation(self,text):
        """Add annotation from model at current simulation time"""
        self._sim.addAnnotation(self, text)
        
    def assertionFailed(self, assertionStr, frameIdx=1):
        '''
        Add an assertion failure trace event
        Increment simulator global assertion failure counter
        Stop simulator if configured so
        
        :param assertionStr error message to display
        :param frame traceback frame index (1 if caller's frame, 2 if caller-caller's frame...)
        '''
        self._sim.assertionFailed(self, assertionStr, frameIdx+1 )
        
    def setStateIndicator(self,text,appearance={}):
        """set part's state from model at simulation time"""
        self._sim.setStateIndicator(self, text, appearance)
    
    def newInputPort(self, name, msgReceivedFunc):
        port = simInputPort(self._sim, self, name, msgReceivedFunc)
        self.addInputPort(port)
        return port
    
    def newOutputPort(self, name):
        port = simOutputPort(self._sim, self, name)
        self.addOutputPort(port)
        return port
    
    def newIOPort(self, name, msgReceivedFunc):
        port = simIOPort(self._sim, self, name, msgReceivedFunc)
        self.addIOPort(port)
        return port

    def newTimer(self, name, elapsedFunc):
        timer = simTimer(self._sim, self, name, elapsedFunc)
        self.addTimer(timer)
        return timer
    
    def newVarWatcher(self, varName, formatString ):
        """
        Add a variable to the watched variables.
        A watched variables value will be checked for changes during simulation.
        If a value change is detected, a simulator trace event is generated
         
        :param string varName: Variable name as seen from part's scope
        :param string formatString: print() like format to format the value when traced  
        """
        watcher = simVariableWatcher(self._sim, self, varName, formatString)
        self.addVarWatcher(watcher)
        return watcher

    def addInputPort(self, port):
        self._listPorts.append(port)
        self._sim.addInputPort(port)
    
    def addOutputPort(self, port):
        self._listPorts.append(port)
        self._sim.addOutputPort(port)

    def addIOPort(self, port):
        self._listPorts.append(port)
        self._sim.addOutputPort(port._outPort)
        self._sim.addInputPort(port._inPort)

    def addTimer(self, timer):
        self._listTimers.append(timer)
        self._sim.addTimer(timer)
    
    def addVarWatcher(self, varWatcher):
        self._listVarWatchers.append(varWatcher)
        self._sim.addVarWatcher(varWatcher)
    
    def createPorts(self, ptype, listPortNames):
        '''
        Convinience functions to create multiple ports at once.
        <type> must be one of 'in', 'out' or 'io
        The function creates for each port a member variable with this name in the part.
        For "in" and "io" ports, a receive function <portName>Recv must be provided by caller 
        '''
        if ptype == 'in':
            for portName in listPortNames:
                setattr(self, portName, self.newInputPort(portName, getattr(self,"%sRecv"%portName)))
        elif ptype == 'out':
            for portName in listPortNames:
                setattr(self, portName, self.newOutputPort(portName))
        elif ptype == 'io':
            for portName in listPortNames:
                setattr(self, portName, self.newIOPort(portName, getattr(self,"%sRecv"%portName)))
        else:
            raise(ValueError("Unknown port type %s" % ptype))
            
    def createTimers(self, listTimerNames):
        '''
        Convinience functions to create multiple timers at once.
        The function creates for each port a member variable with this name in the part.
        A timer callback function <tmrName>Expired must be provided by caller 
        '''
        for tmrName in listTimerNames:
            exec('self.%s = self.newTimer("%s", self.%sExpired)' % (tmrName,tmrName,tmrName)) 
    
    def startSim(self):
        '''Called from simulator when simulation begins'''
        pass
            
    def terminateSim(self):
        '''Called from simulator when simulation stops. Terminate block (e.g. stop threads)'''
        pass
    
    def time(self):
        '''Get current simulation time'''
        return self._sim.time()


class simEvent(object):
    def __init__(self):
        self._cancelled = False
    
    def __lt__(self, other):
        return self.execTime < other.execTime
        
class simInputPort(simBaseElement):
    """Simulator input port"""
    def __init__(self, sim, part, name, msgReceivedFunc, ioPort=None):
        super().__init__(sim, part, name, "InPort")
        self._outPort = None        # connected output port
        self._msgReceivedFunc = msgReceivedFunc # function that gets called when message arrives
        self._ioPort = ioPort       # reference to the IOPort which contains this inPort (None if not part of IOPort)
        
    def msgEvent(self,msg):
        """called from bound outport when a new message is received"""
        self._msgReceivedFunc(self,msg)
        
    def isBound(self):
        """Report True if port is bound to an output port"""
        return self._outPort is not None 
    
class simOutputPort(simBaseElement):
    """Simulator output port"""
   
    class fireEvent(simEvent):
        """ Event that is passed to scheduler to send a message """
        def __init__(self, sim, port, msg, flightTime):
            super().__init__()
            self._sim = sim
            self._port = port
            self._serializedMsg = self.__class__.msgSerialize(msg)
            self._msgColor = msg.msgColor if hasattr(msg, 'msgColor') else None
            self._flightTime = flightTime       # message transmit time
            self._requestTime = sim.time()      # time when application called send()
            self.execTime = -1;                 # when message arrives at input port
            self._isLost = False                # Flags that message is a lost message
        
        def __str__(self):
            """Create a user readable form of the event. Used by tracer"""
            return "%s req=%s beg=%s end=%s dur=%s msg=[%s]" % ("(LOST)" if self._isLost else "",  
                                                                    self._sim.timeStr(self._requestTime), 
                                                                    self._sim.timeStr(self.execTime - self._flightTime),
                                                                    self._sim.timeStr(self.execTime),
                                                                    self._sim.timeStr(self._flightTime),
                                                                    self.msgText())
                                                                    
                
            
        def __repr__(self):
            return self._port.objName() + "#fireEvent"
        
        def msgText(self):
            ''' return message's __str__ '''
            return self.__class__.msgUnserialize(self._serializedMsg).__str__()
        
        def execute(self):
            # check if the message is marked as lost
            self._isLost = self._port.isLostMessage()

            # pass the message to all bound input ports
            for inport in self._port._listInPorts:
                    
                self._sim.addTraceEvent( simTraceEvent(self._port._parentObj, inport, self, '<MSG') )

                if not self._isLost:
                    # make a deep copy (by using pickle) of the message, so that application can modify the message
                    msgCopy = self.__class__.msgUnserialize(self._serializedMsg)
                    inport.msgEvent(msgCopy)
                
            # remove me from pending queue
            #print(self, "exec", len(self._port._listPendingMsg))
            self._port._listPendingMsg.popleft()
            # and send next message in queue
            if self._port._listPendingMsg:
                event = self._port._listPendingMsg[0]
                self._port._sendSchedule(event)
                self._sim.addTraceEvent( simTraceEvent(self._port._parentObj, self._port, event, '>MSG(Q)') )
            self._port._seqNo += 1    
    
        @staticmethod
        def msgSerialize(msg):
            return pickle.dumps(msg, pickle.HIGHEST_PROTOCOL)

        @staticmethod
        def msgUnserialize(stream):
            return pickle.loads(stream)
        
    
    def __init__(self, sim, part, name, color=None, ioPort=None):
        super().__init__(sim, part, name, "OutPort")
        self._listInPorts = []      # list of all input ports
        self._listPendingMsg = deque() # list of pending messages (not yet fired)
        self._color = color         # color for messages leaving that port
        self._ioPort = ioPort       # reference to the IOPort which contains this outPort (None if not part of IOPort)
        self._listMsgTypes = []     # learned message types that left this port
        self._seqNo = 0             # next message sequence number (for lost messages)
        self._lostSeqHeap = []      # heap with message sequence numbers that will be lost 
        
    def bind(self, inputPort):
        """bind an output port to an input port"""
        assert(inputPort._outPort is None),"input port already bound"
        inputPort._outPort = self
        self._listInPorts.append(inputPort)
    
    def isBound(self):
        """Report True if port is bound to at least one input port"""
        return len(self._listInPorts) >= 1         
 
    def _learnMsgTypes(self, msg):
        ''' 
        Learn which types of messages are leaving the port.
        Will be displayed in Structure Graphs
        '''
        msgType = type(msg).__name__
        if not msgType in self._listMsgTypes:
            self._listMsgTypes.append(msgType)
 
    def learnedMsgTypes(self):
        ''' Return list of learned message types that left the port until now. (Strings with types) '''
        return self._listMsgTypes
 
    def _sendSchedule(self, event):
        event.execTime = self._sim.time() + event._flightTime
        self._sim.scheduleEvent(event)
        
    
    def send(self, msg, flightTime):
        """User interface to send a message"""
        self._learnMsgTypes(msg)
        event = self.fireEvent(self._sim, self, msg, flightTime)
        if not self._listPendingMsg:
            # no pending messages, send now
            self._sendSchedule(event)
            self._sim.addTraceEvent( simTraceEvent(self._parentObj, self, event, '>MSG') )

        self._listPendingMsg.append(event)
        #print(self, "sendlp", len(self._listPendingMsg))
        
    def setColor(self, color):
        ''' Set color for messages leaving that port '''
        self._color = color

    def injectLostMessageErrorBySequence(self, nextSeq):
        ''' Inject error. Force one of the next messages sent via this port to be lost
        If nextSeq is 0, the next message sent via this port will be lost, if it is 1 the next but one
        message is lost etc.
        ''' 
        lostSeq = self._seqNo + nextSeq;
        
        # add the sequence number to be lost to the _lostSeqHeap, if this sequence is not already there
        # this maintains the heap sequence.
        if not lostSeq in self._lostSeqHeap: 
            heappush(self._lostSeqHeap, lostSeq )
        #print("lostSeqHeap=", self._lostSeqHeap)
    
    def isLostMessage(self):
        ''' 
        Test if the current message is marked to be lost. 
        Return True if so and remove the current sequence from the lost sequence heap 
        '''
        if len(self._lostSeqHeap) > 0 and self._seqNo == self._lostSeqHeap[0]:
            heappop(self._lostSeqHeap)
            return True    
        else:
            return False    
        
class simIOPort(simBaseElement):
    ''' An element that contains one input and one output port '''
    def __init__(self, sim, part, name, msgReceivedFunc, specialInPort=None):
        super().__init__(sim, part, name, "IOPort")
        self._outPort = simOutputPort( sim, part, name + "Out", ioPort=self)
        if specialInPort is None:
            self._inPort = simInputPort(sim, part, name + "In", msgReceivedFunc, ioPort=self)
        else:
            self._inPort = specialInPort
            self._inPort._ioPort = self
        
    def bind(self, otherIoPort):
        ''' Bind IOPort to another IOPort, in/out will be crossed '''
        self._outPort.bind(otherIoPort._inPort)
        otherIoPort._outPort.bind(self._inPort)
        
    def loopBind(self):
        ''' Loop in/out ports of an IO port together '''
        self._outPort.bind(self._inPort)
    
    
    # delegation methods to output port     
    def send(self, msg, flightTime):
        ''' send message to IoPorts output port '''
        self._outPort.send(msg, flightTime)
    
    def injectLostMessageErrorBySequence(self, nextSeq):
        ''' inject error on IoPorts output port '''
        self._outPort.injectLostMessageErrorBySequence(self, nextSeq)
        
    def setColor(self, color):
        ''' Set color for messages leaving that IOport '''
        self._outPort._color = color

    def peerPort(self):
        ''' 
        return the peer IOPort to which this port is bound to.
        return None if there is none
        '''
        peer = None
        if self._inPort.isBound():
            p = self._inPort._outPort   # get reference to the peer
            if p._ioPort is not None:
                p = p._ioPort._inPort
                if p in self._outPort._listInPorts:
                    peer = p._ioPort
        return peer         
         
        
class simTimer(simBaseElement):
    """Simulator Timer
    timer is either running or stopped
    timer can be canceled, and restarted"""
    
    class timerEvent(simEvent):
        """ Event that is passed to scheduler for timer """
        def __init__(self, sim, timer, execTime):
            super().__init__()
            self._sim = sim
            self._timer = timer
            self.execTime = execTime;
            
        def __repr__(self):
            return self._timer.hierarchyName() + "#timerEvent"
        
        
        def execute(self):
            self._timer._pendingEvent = None
            self._sim.addTraceEvent( simTraceEvent(self._timer._parentObj, self._timer, None, 'T-EXP') )
            self._timer._elapsedFunc(self._timer)
            
    class timeoutFmt:
        """Helper class to get a formatted print of the timeout"""
        def __init__(self, sim, timeout):
            self._sim = sim
            self._timeout = timeout
        def __str__(self):
            return self._sim.timeStr(self._timeout)
 
    def __init__(self, sim, part, name, elapsedFunc):
        super().__init__(sim, part, name, "Timer")
        self._pendingEvent = None   # current scheduled event (None if timer stopped)
        self._elapsedFunc = elapsedFunc # function that gets called when time elapsed
        
    def _start(self, timeout):    
        assert(self._pendingEvent is None ),self.hierarchyName()+"already running"
        assert(timeout > 0)
        event = self.timerEvent(self._sim, self, self._sim.time()+timeout)
        self._sim.scheduleEvent(event)
        self._pendingEvent = event
    
    def start(self, timeout):
        """Start the timer. Timer will fire after <timeout>"""
        self._start(timeout)
        self._sim.addTraceEvent( simTraceEvent(self._parentObj, self, self.timeoutFmt(self._sim,timeout), 'T-START') )
    
    def _stop(self):
        if self._pendingEvent is not None:
            self._sim.cancelEvent(self._pendingEvent)
            self._pendingEvent = None
    
    def stop(self):
        """Stop timer. Does nothing if timer not running"""
        self._sim.addTraceEvent( simTraceEvent(self._parentObj, self, None, 'T-STOP') )
        self._stop()
        
    def restart(self,timeout):
        """Restart timer. Timer will fire after <timeout>"""
        self._sim.addTraceEvent( simTraceEvent(self._parentObj, self, self.timeoutFmt(self._sim,timeout), 'T-RESTA') )
        self._stop()
        self._start(timeout)

class simVariableWatcher(simBaseElement):
    """
    The VariableWatcher class watches a variable for changes.
    The variable is referenced by the moddy part and its variable name within the part.
    It can be a variable in the part itself or a subobject "obj1.subobj.a"
    
    The class provides the checkValueChanged() method. In moddy, the simulator should call this function
    after each event (or step) to see if the value has changed   
    """
    def __init__(self, sim, part, varName, formatString):
        """
        :param sim: simulator object
        :param simPart part: part which contains the variable 
        :param string varName: Variable name as seen part scope
        :param string formatString: print format like string to format value 
        """
        super().__init__(sim, part, varName, "WatchedVar")
        self._varName = varName
        self._lastValue = None
        self._formatString = formatString
    
    def currentValue(self):
        try:
            curVal = eval('self._parentObj.' + self._varName)
        except:
            curVal = None
        return curVal
        
    def __str__(self):
        curVal = self.currentValue()
        if curVal is None:
            s = ''
        else:
            s = self._formatString % (curVal)
        return s 
        
    def checkValueChanged(self):
        """
        Check if the variable value has changed
        :return Changed, newVal 
        
        Changed is True if value has changed since last call to checkValueChanged()
        newVal is returned also if value not changed
        
        If the variable value cannot be evaluated (e.g. because the variable does not exist (anymore))
        the variables value is set to None (no exception is raised) 
        
        """
        oldVal = self._lastValue
        curVal = self.currentValue()
        changed = False
            
        if curVal != oldVal:
            self._lastValue = curVal
            changed = True
            
        return (changed, curVal)
    
    def varName(self):
        return self._varName
    
        
    
class simTraceEvent:
    ''' simTraceEvents are the objects that are added to the simulators trace buffer''' 
    def __init__(self, part, subObj, tv, act):
        self.traceTime      = -1        # when the event occurred
        self.part           = part      # generating part
        self.subObj         = subObj   # timer or port
        self.transVal       = tv        # Transport value (e.g. message)
        self.action         = act       # action string
        
    def __repr__(self):
        traceStr = "%-8s" %  (self.action)
        if self.subObj is not None:
            traceStr += self.subObj.hierarchyNameWithType() 
        if self.transVal is not None:
            traceStr += " // %s" % self.transVal.__str__()
        return traceStr

class sim:
    """Simulator main class"""
           
    def __init__(self):
        self._listParts  = []       # list of all parts
        self._listEvents     = []       # a heapq with list of pending events takes pendingEvent objects, sorted by execTime
        self._time           = 0.0      # current simulator time
        self._listInPorts    = []
        self._listOutPorts   = []
        self._listTimers     = []
        self._disTimeScale   = 1        # time scale factor
        self._disTimeScaleStr = "s"     # time scale string
        self._listTracedEvents = deque()# list of all traced events during execution
        self._listVariableWatches = []  # list of watched variables
        self._enableTracePrints = True
        self._stopOnAssertionFailure = False
        self._numAssertionFailures = 0
        self._isRunning = False
        self._hasRun = False
        self._stopEvent = None
        
    #
    # Port Management
    #
    def addInputPort(self, port):
        """Add input port to simulators list"""
        self._listInPorts.append(port)
    
    def addOutputPort(self, port):
        """Add output port to simulators list"""
        self._listOutPorts.append(port)


    def checkUnBoundPorts(self):
        """
        Check if all ports are connected
        print warnings for unconnected ports
        """
        for p in self._listInPorts + self._listOutPorts:
            if not p.isBound():
                print("SIM: WARNING: Port %s not bound" % (p.hierarchyNameWithType()))

    def addTimer(self, timer):
        """Add timer to list of timers"""
        self._listTimers.append(timer)
    
    def outputPorts(self):
        return self._listOutPorts
    
    #
    # Part management
    # 
    def addPart(self, part):
        assert( part not in self._listParts)
        self._listParts.append(part)
    
    def topLevelParts(self):
        ''' get list of top level parts '''
        tlParts = []
        for part in self._listParts:
            if part._parentObj is None:
                tlParts.append(part)
        return tlParts
    
    def findPartByName(self, partHierarchyName):
        '''
        Find a part by its hierarchy name
        :param string partHierarchyName: e.g. "part1.subpart.subsubpart"
        :return simPart part: the found part
        :raises ValueError: if part not found
        '''
        for part in self._listParts:
            if part.hierarchyName() == partHierarchyName:
                return part
        raise(ValueError("Part not found %s" % partHierarchyName))
       
    #
    # Variable watching
    #
    def addVarWatcher(self, varWatcher):
        self._listVariableWatches.append(varWatcher)
        
        
    def watchVariables(self):
        """
        Check all registered variables for changes.
        Generate a trace event for all changed variables
        """    
        for varWatcher in self._listVariableWatches:
            changed,newVal = varWatcher.checkValueChanged()
            if changed == True:
                newValStr = varWatcher.__str__() 
                te = simTraceEvent( varWatcher._parentObj, varWatcher, newValStr, 'VC')
                self.addTraceEvent(te)

    def watchVariablesCurrentValue(self):
        """
        Generate a trace event for all watched variables with their current value
        Used at start of simulator to report the initial values
        """    
        for varWatcher in self._listVariableWatches:
            te = simTraceEvent( varWatcher._parentObj, varWatcher, varWatcher.__str__(), 'VC')
            self.addTraceEvent(te)

    def findWatchedVariableByName(self, variableHierarchyName):
        '''
        Find a watched variable by its hierarchy name
        :param string variableHierarchyName: e.g. "part1.variable"
        :return simVariableWatcher: the found variable watcher
        :raises ValueError: if variable not found
        '''
        for varWatcher in self._listVariableWatches:
            if varWatcher.hierarchyName() == variableHierarchyName:
                return varWatcher
        raise(ValueError("Watched Variable not found %s" % variableHierarchyName))

    #
    # Model Assertions
    #
    def assertionFailed(self, part, assertionStr, frameIdx=1):
        '''
        Add an assertion failure trace event
        Increment global assertion failure counter
        Stop simulator if configured so
        
        :param part the related simPart. None if global assertion
        :param assertionStr error message to display
        :param frame traceback frame index (1 if caller's frame, 2 if caller-caller's frame...)
        '''
        _,fileName,lineNumber,functionName,_,_ = inspect.stack()[frameIdx]

        s = "%s: in %s, (%s::%d)" %(assertionStr, functionName, os.path.basename(fileName), lineNumber)
        te = simTraceEvent( part, part, s, 'ASSFAIL')
        self.addTraceEvent(te)
        self._numAssertionFailures += 1
        
    
    #
    # Simulator core routines
    #
        
    def time(self):
        return self._time
    
    def scheduleEvent(self, event):
        """schedule a new event for execution. 
        Event must have members
        - execTime
        - cancelled
        - execute()
        - __lt__()
        """
        heappush(self._listEvents, event)
        
    def cancelEvent(self,event):
        """Cancel an already scheduled event"""
        event._cancelled = True
        
    def stop(self):
        self._isRunning = False
        elapsedTime = datetime.now() - self._startRealTime 
        for part in self._listParts: part.terminateSim()
        print("SIM: Simulator stopped at",self.timeStr(self._time) + 
              ". Executed %d events in %.3f seconds"%(self._numEvents, elapsedTime.total_seconds()) ) #TODO
        self.printAssertionFailures()
        
    def run(self, 
            stopTime, 
            maxEvents=100000, 
            enableTracePrinting=True, 
            stopOnAssertionFailure=True):
        '''
        run the simulator until 
            - stopTime reached
            - no more events to execute
            - maxEvents reached 
            - model called assertionFailed() and stopOnAssertionFailure==True
            - a model exception (including exceptions from vThreads) has been caught
        @param stopTime - simulation time at which the simulator shall stop latest
        @param maxEvents - (default: 100000) maximum number of simulator events to process. Can be set to None for infinite events 
        @param enableTracePrinting - (default: True) if set to False, simulator will not display events as they are executing
        @param stopOnAssertionFailure - (default: True) if set to False, don't stop when model calls assertionFailed(). 
                                        Just print info at end of simulation
        @raise exceptions coming from model or simulator
        
        '''
        self._enableTracePrints = enableTracePrinting
        self._stopOnAssertionFailure = stopOnAssertionFailure
        
        if self._hasRun:
            print("SIM: run() can be called only once", file=sys.stderr)
            return 
        
        self.checkUnBoundPorts()
        print ("SIM: Simulator %s starting" % (VERSION))
        self._startRealTime = datetime.now()
        
        # create stop event that fires at stop time
        self._stopEvent = simEvent()
        self._stopEvent.execTime = stopTime
        self.scheduleEvent(self._stopEvent)
        
        self._isRunning = True
        self._hasRun = True
        # report initial value of watched variables
        self.watchVariablesCurrentValue()
        for part in self._listParts: part.startSim()
        # Check for changed variables
        self.watchVariables()
                   
        self._numEvents = 0
        
        try:
            while True:
                if not self._listEvents:
                    print("SIM: Simulator has no more events")
                    break   # no more events, stop
                    
                # get next event to execute
                # heap is a priority queue. heappop extracts the event with the smallest execution time
                event = heappop(self._listEvents)
                if event._cancelled == True:
                    continue
                
                
                self._numEvents += 1
                assert( self._time <= event.execTime),"time can't go backward"
                self._time = event.execTime

                if event == self._stopEvent:
                    print("SIM: Stops because stopTime reached")
                    break
    
                #print("SIM: Exec event", event, self._time)
                try:
                    # Catch model exceptions
                    event.execute()
                except: 
                    print ("SIM: Caught exception while executing event %s" % event, file=sys.stderr)
                    # re-raise model exception
                    raise
                # Check for changed variables
                self.watchVariables()
                
                if maxEvents is not None and self._numEvents >= maxEvents:
                    print("SIM: Simulator has got too many events (pass a higher number to run(maxEvents=n)")
                    break   
    
                if self._stopOnAssertionFailure and self._numAssertionFailures > 0:
                    print("SIM: Stops due to Assertion Failure")
                    break
        finally:
            self.stop()    

    def isRunning(self):
        return self._isRunning    

    #
    # Tracing and display routines
    #
    def addTraceEvent(self,te):
        ''' Add new event to Trace list, timestamp it, print it'''
        te.traceTime = self._time
        self._listTracedEvents.append(te)
        
        if self._enableTracePrints:
            traceStr = "TRC: %10s %s" %  (self.timeStr(te.traceTime), te)
            print (traceStr)

    def tracedEvents(self):
        ''' return list of traced events'''
        return self._listTracedEvents

    def addAnnotation(self,part,text):
        '''
        User routine to add an annotation to a life line at the current simulation time
        '''
        te = simTraceEvent( part, part, text, 'ANN')
        self.addTraceEvent(te)

    class StateIndTransVal:
        def __init__(self, text, appearance):
            self.text = text
            self.appearance = appearance
           
        def __str__(self):
            return self.text


    def setStateIndicator(self,part,text,appearance={}):
        '''
        User routine to indicate the current state of a part. Can be also used to indicate 
        UML execution specification to a life line 
        at the current simulation time. 
        An empty text flags 'no state' which removes the indication from the life line
        '''
        te = simTraceEvent( part, part, self.StateIndTransVal(text,appearance), 'STA')
        self.addTraceEvent(te)

    def setDisplayTimeUnit(self,unit):
        """Define how the simulator prints/displays time units
        Unit can be "s", "ms", "us", "ns"
        """
        self._disTimeScaleStr = unit
        self._disTimeScale = timeUnit2Factor(unit)
        
    def timeStr(self,time):
        """return a formatted time string of <time> based on the display scale"""
        tmfmt = "%.1f" % (time / self._disTimeScale)
        return tmfmt + self._disTimeScaleStr

    def printAssertionFailures(self):
        '''Print all traced assertion failures to stderr'''
        if self._numAssertionFailures > 0:
            print("%d Assertion failures during simulation" % self._numAssertionFailures, file=sys.stderr)
            for te in self._listTracedEvents: 
                if te.action == "ASSFAIL":
                    print ("%10s %s" %  (self.timeStr(te.traceTime), te.transVal.__str__()), file=sys.stderr)

    




