'''
Moddy - Python system simulator
 
'''
from copy import deepcopy
from moddy import ms,us,ns,VERSION
import sys

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
    
    def createPorts(self, ptype, listPortNames):
        '''
        Convinience functions to create multiple ports at once.
        <type> must be one of 'in', 'out' or 'io
        The function creates for each port a member variable with this name in the part.
        For "in" and "io" ports, a receive function <portName>Recv must be provided by caller 
        '''
        if ptype == 'in':
            for portName in listPortNames:
                exec('self.%s = self.newInputPort("%s", self.%sRecv)' % (portName,portName,portName)) 
        elif ptype == 'out':
            for portName in listPortNames:
                exec('self.%s = self.newOutputPort("%s")' % (portName,portName)) 
        elif ptype == 'io':
            for portName in listPortNames:
                exec('self.%s = self.newIOPort("%s", self.%sRecv)' % (portName,portName,portName)) 
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
   
class simInputPort(simBaseElement):
    """Simulator input port"""
    def __init__(self, sim, part, name, msgReceivedFunc, ioPort=None):
        super().__init__(sim, part, name, "InPort")
        self._outPort = None        # connected output port
        self._msgReceivedFunc = msgReceivedFunc # function that gets called when message arrives
        self._ioPort = ioPort       # reference to the IOPort which contains this outPort (None if not part of IOPort)
        
    def msgEvent(self,msg):
        """called from bound outport when a new message is received"""
        self._msgReceivedFunc(self,msg)
        
    def isBound(self):
        """Report True if port is bound to an output port"""
        return self._outPort is not None 
    
class simOutputPort(simBaseElement):
    """Simulator output port"""
   
    class fireEvent:
        """ Event that is passed to scheduler to send a message """
        def __init__(self, sim, port, msg, flightTime):
            self._sim = sim
            self._port = port
            self._msg = msg
            self._flightTime = flightTime       # message transmit time
            self._requestTime = sim.time()      # time when application called send()
            self.execTime = -1;                 # when message arrives at input port
        
        def __str__(self):
            """Create a user readable form of the event. Used by tracer"""
            return "req=%s beg=%s end=%s dur=%s msg=[%s]" % (self._sim.timeStr(self._requestTime), 
                                                                    self._sim.timeStr(self.execTime - self._flightTime),
                                                                    self._sim.timeStr(self.execTime),
                                                                    self._sim.timeStr(self._flightTime),
                                                                    self._msg.__str__())
                                                                    
                
            
        def name(self):
            return self._port.objName() + "#fireEvent"
        
        def execute(self):
            # pass the message to all bound input ports
            for inport in self._port._listInPorts:
                self._sim.addTraceEvent( simTraceEvent(self._port._parentObj, inport, self, '<MSG') )
                # make a deep copy of the message, so that application can modify the message
                msgCopy = deepcopy(self._msg)
                inport.msgEvent(msgCopy)
                
            # remove me from pending queue
            #print(self.name(), "exec", len(self._port._listPendingMsg))
            del self._port._listPendingMsg[0]
            # and send next message in queue
            if self._port._listPendingMsg:
                event = self._port._listPendingMsg[0]
                self._port._sendSchedule(event)
                self._sim.addTraceEvent( simTraceEvent(self._port._parentObj, self._port, event, '>MSG(Q)') )
                
    
    def __init__(self, sim, part, name, color=None, ioPort=None):
        super().__init__(sim, part, name, "OutPort")
        self._listInPorts = []      # list of all input ports
        self._listPendingMsg = []   # list of pending messages (not yet fired)
        self._color = color         # color for messages leaving that port
        self._ioPort = ioPort       # reference to the IOPort which contains this outPort (None if not part of IOPort)
        self._listMsgTypes = []     # learned message types that left this port
        
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
        #print(self.name(), "sendlp", len(self._listPendingMsg))
        
    def setColor(self, color):
        ''' Set color for messages leaving that port '''
        self._color = color

class simIOPort(simBaseElement):
    ''' An element that contains one input and one output port '''
    def __init__(self, sim, part, name, msgReceivedFunc, specialInPort=None):
        super().__init__(sim, part, name, "IOPort")
        self._outPort = simOutputPort( sim, part, name + "-Out", ioPort=self)
        if specialInPort is None:
            self._inPort = simInputPort(sim, part, name + "-In", msgReceivedFunc, ioPort=self)
        else:
            self._inPort = specialInPort
        
    def bind(self, otherIoPort):
        ''' Bind IOPort to another IOPort, in/out will be crossed '''
        self._outPort.bind(otherIoPort._inPort)
        otherIoPort._outPort.bind(self._inPort)
        
    def send(self, msg, flightTime):
        ''' send message to IoPorts output port '''
        self._outPort.send(msg, flightTime)
        
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
    
    class timerEvent:
        """ Event that is passed to scheduler for timer """
        def __init__(self, sim, timer, execTime):
            self._sim = sim
            self._timer = timer
            self.execTime = execTime;
            
        def name(self):
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
    
    
class simTraceEvent:
    ''' simTraceEvents are the objects that are added to the simulators trace buffer''' 
    def __init__(self, part, subObj, tv, act):
        self.traceTime      = -1        # when the event occurred
        self.part           = part      # generating part
        self.subObj         = subObj   # timer or port
        self.transVal       = tv        # Transport value (e.g. message)
        self.action         = act       # action string
        

class sim:
    """Simulator main class"""
           
    def __init__(self):
        self._listParts  = []       # list of all parts
        self._listEvents     = []       # list of pending events, takes pendingEvent objects, sorted by execTime
        self._time           = 0.0      # current simulator time
        self._listInPorts    = []
        self._listOutPorts   = []
        self._listTimers     = []
        self._disTimeScale   = 1        # time scale factor
        self._disTimeScaleStr = "s"     # time scale string
        self._listTracedEvents = []     # list of all traced events during execution
        self._enableTracePrints = True
        self._isRunning = False
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
                
    
    #
    # Simulator core routines
    #
        
    def time(self):
        return self._time
    
    def scheduleEvent(self, event):
        """schedule a new event for execution. 
        Event must have members
        - execTime
        - execute()
        - name()
        """
        #print("scheduleEvent",event.name())
        inserted = False
        
        for i in range(len(self._listEvents)):
            if event.execTime <= self._listEvents[i].execTime:
                self._listEvents.insert(i, event)
                #print("inserting event",event.execTime,i)
                inserted = True
                break
        if inserted == False:
            self._listEvents.append(event)         
            #print("inserting event at end",event.execTime)
            
    def cancelEvent(self,event):
        """Cancel an already scheduled event"""
        self._listEvents.remove(event)
        
    def stop(self):
        self._isRunning = False
        print("SIM: Simulator stopped at",self.timeStr(self._time) )
        for part in self._listParts: part.terminateSim()
        
    def run(self, stopTime, maxEvents=10000, enableTracePrinting=True):
        '''
        run the simulator until <stopTime>
        <maxEvents> is there to prevent the simulator to run for a too long time
        <enableTracePrinting> - if set to false, simulator will not display events as they are executing
        '''
        self._enableTracePrints = enableTracePrinting
        self.checkUnBoundPorts()
        print ("SIM: Simulator %s starting" % (VERSION))
        self._isRunning = True
        for part in self._listParts: part.startSim()
        
        numEvents = 0
        
        while True:
            if not self._listEvents:
                print("SIM: Simulator has no more events")
                break   # no more events, stop
        
            if numEvents >= maxEvents:
                print("SIM: Simulator has got too many events")
                break   
                
            # get next event to execute
            event = self._listEvents.pop(0)
            numEvents += 1
            assert( self._time <= event.execTime),"time can't go backward"
            if event.execTime > stopTime:
                break
            self._time = event.execTime

            #print("SIM: Exec event", event.name(), self._time)
            try:
                # Catch model exceptions
                event.execute()
            except: 
                print ("SIM: Caught exception while executing event %s" % event.name(), file=sys.stderr)
                self.stop()
                # re-raise model exception
                raise

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
        
        traceStr = "TRC: %10s %-8s" %  (self.timeStr(te.traceTime), te.action)
        if te.subObj is not None:
            traceStr += te.subObj.hierarchyNameWithType() 
        if te.transVal is not None:
            traceStr += " // %s" % te.transVal.__str__()
        
        if self._enableTracePrints:
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


    




