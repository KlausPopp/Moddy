'''
:mod:`fsmPart` -- A moddy part with a state machine 
=======================================================================

.. module:: fsmPart
   :synopsis: A moddy part with a state machine
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
from moddy import simPart


class simFsmPart(simPart):
    '''
    A moddy part with a state machine
    All simulator events are directed to the fsm.
    
    :param sim: Simulator instance
    :param objName: part name
    :param Fsm fsm: the state machine (Fsm class) object created by caller
    :param parentObj: parent part. None if part has no parent. Defaults to None
    :param dict statusBoxReprMap: defines how each state is shown in sequence diagrams' status boxes \
            Must be a dictionary with the state names as keys. The values must be a tuple of
            
            * text to display (None if org. state name shall be used)
            * appearance: The colors of the status box, see setStatIndication()   

    '''
    def __init__(self, sim, objName, fsm, parentObj=None, statusBoxReprMap=None ):
        super().__init__(sim=sim, objName=objName, parentObj=parentObj )
        
        # reference the fsm
        self.fsm = fsm
        fsm._moddyPart = self
        # register state change callback
        fsm.setStateChangeCallback( self.fsmStateChange )
    
        self._statusBoxReprMap = statusBoxReprMap
    
    def startSim(self):
        simPart.startSim(self)
        # Bring state machine into initial state
        self.fsm.startFsm()
        
    def createPorts(self, ptype, listPortNames):
        # Override simPart method to route all events to central handlers
        '''
        Convinience functions to create multiple ports at once.
        
        :param ptype: Type of ports, must be one of 'in', 'out' or 'io'
        :param list listPortNames: list of port names to create
        
        The function creates for each port a member variable with this name in the part.
        
        '''
        if ptype == 'in':
            for portName in listPortNames:
                exec('self.%s = self.newInputPort("%s", self.msgRecv)' % (portName,portName)) 
        elif ptype == 'io':
            for portName in listPortNames:
                exec('self.%s = self.newIOPort("%s", self.msgRecv)' % (portName,portName)) 
        else:
            super().createPorts(ptype, listPortNames)
        
    def createTimers(self, listTimerNames):
        # Override simPart method to route all events to central handlers
        '''
        Convinience functions to create multiple timers at once.
        
        :param list listTimerNames: list of timer names to create
        
        The function creates for each port a member variable with this name in the part.
        '''
        for tmrName in listTimerNames:
            exec('self.%s = self.newTimer("%s", self.tmrExpired)' % (tmrName,tmrName)) 

    def msgRecv(self, port, msg):
        
        # If an event name <portname>_Msg exists in the fsm, trigger that event, 
        # otherwise call the STATE_<portName>_Msg(msg) in the fsm 
        fsmEventName = "%s_Msg" % port.objName()
        
        if self.fsm.hasEvent(fsmEventName):
            self.fsm.event(fsmEventName)
        else:
            if self.fsm.execStateDependentMethod( fsmEventName, True, msg) == False:
                self.addAnnotation('%s not handled' % fsmEventName)
                
    
    def tmrExpired(self, timer):
        # If an event name <timerName>_Expired exists in the fsm, trigger that event, 
        # otherwise call the STATE_<timerName>_Expired() in the fsm 
        fsmEventName = "%s_Expired" % timer.objName()
        
        if self.fsm.hasEvent(fsmEventName):
            self.fsm.event(fsmEventName)
        else:
            if self.fsm.execStateDependentMethod( fsmEventName, True ) == False:
                self.addAnnotation('%s not handled' % fsmEventName)
        
    def fsmStateChange(self, oldState, newState):
        ''' 
        Called by the fsm whenever the state changes.
        Set the part status indicator to new state using the representation map
        '''     
        text = newState
        appearance = {}
        
        if self._statusBoxReprMap is not None:
            try:
                text, appearance = self._statusBoxReprMap[newState]
                if text is None:
                    text = newState
            except KeyError:
                pass
            
        self.setStateIndicator(text, appearance)
    
