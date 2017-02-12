'''
Created on 11.02.2017

@author: Klaus Popp

A general finite state machine
'''
class Fsm(object):
    '''
    A finite state machine.
    Subclass your FSM from this class.
    
    Example: 
    class Computer(Fsm):
    
        def __init__(self):
            
            transitions = { 
                '':
                    [('INITIAL', 'Off')],
                'Off': 
                    [('PowerApplied', 'Standby')],
                'Standby':
                    [('PowerButtonPressed', 'NormalOp')],
                'NormalOp':
                    [('PowerButtonPressed', 'Standby'),
                     ('OsShutdown', 'Standby')],
                'ANY':
                    [('PowerRemoved', 'Off')]
            }
            
            super().__init__( dictTransitions=transitions )

        The special 'ANY' state means that the transitions can be initiated from ANY state.
        The special 'INITIAL' must be in the '' (uninitialized) state and specifies the INITIAL transistion
        which is triggered by startFsm()

                
    You can define entry and exit method that are executed when a state is entered or left.
    These methods must follow the naming convention "STATE_<statename>_<Entry/Exit>".
    They don't need to exist. They are called only if they are defined.
    
    
    Note that entry and exit actions are also called at self transitions (transitions to the current state)
    
        # Off actions    
        def State_Off_Entry(self):
            print("State_Off_Entry")
    
        def State_Off_Exit(self):
            print("State_Off_Exit")
    
    Such routines can be also defined for the special 'ANY' state. If they exist they are called at
    the entry or exit from any state.
            
    Use the fsm as follows:
    
        comp = Computer()
        comp.startFsm()    # sets the state machine to its initial state 
        
        comp.event('PowerApplied')
        print("State %s" % comp.state)
        
        comp.event('PowerButtonPressed')
        print("State %s" % comp.state)
        
        comp.event('PowerRemoved')
        print("State %s" % comp.state)
    
    
    You can call execAnyAndCurrentStateMethod to execute a state specific optional if it has been defined
    by the designer of the fsm subclass (e.g. the simFsmPart uses it to execute the _Msg and _Expiration
    functions)
    
    '''
    
    def __init__(self, dictTransitions):
        '''
        dictTransitions must be a dictionary, with the transitions (see example in class doc)

        The dict key is the state, and the values are a list of transition from
        that state. Each transition consists of a tuple (event, targetState).
        
        
        '''
        self.state = None
        
        self._dictTransitions = dictTransitions
        self._stateChangeCallback = None
        self._listEvents = []
        
        # Validate transitions and build list of events
        for state, listTrans in dictTransitions.items():
            for trans in listTrans:
                event, toState = trans
                
                if event not in self._listEvents:
                    self._listEvents.append(event)
                    
                assert(self.stateExists(toState)),"toState %s doesn't exist" % toState
                assert(toState != 'ANY'),"ANY cannot be a target state"    
    
    #
    # Public PAI
    # 
    def getDictTransitions(self):
        return self._dictTransitions        
                
    def execAnyAndCurrentStateMethod(self, methodName, *args):
        ''' 
        Execute the state specific methods:
         The method self.State_ANY_<methodName>(*args) is called if it exists.
         The method self.State_<stateName>_<methodName>(*args) is called if it exists.
        '''
        self.execStateMethod('ANY', methodName, *args)
        self.execStateMethod(self.state, methodName, *args)

    def setStateChangeCallback(self, callback):
        ''' Register a method that is called whenever the state of the fsm changes '''
        self._stateChangeCallback = callback

    def hasEvent(self,evName):
        return evName in self._listEvents
    
    def startFsm(self):
        assert(self.state is None)
        self._event('INITIAL')     

    def event(self, evName):
        assert(self.state is not None),"Did you call startFsm?"
        self._event(evName)
        
    #
    # Internal methods
    #
    
    def execStateMethod(self, state, methodName, *args):
        '''
        Execute a state specific method that might exist in the fsm subclass.
        
        The method self.State_<stateName>_<methodName>(*args) is called if it exists.
        If it doesn't exist, nothing happens.   
        '''
        execStr = "self.State_%s_%s" % (state, methodName)
        print("execStateMethod %s" % execStr)
        try: 
            exec( "m=" + execStr)

        except AttributeError:
            return
        
        exec(execStr + "(*args)")
        
    def stateExists(self, state):
        return state in self._dictTransitions
        
    def gotoState(self, state):
        assert(state != 'ANY' and self.stateExists(state)),"gotoState invalid state %s"%state
        
        oldState = self.state        
        print("+++ GOTO STATE %s" % state)
        # exit old state
        if self.state is not None:
            self.execAnyAndCurrentStateMethod( 'Exit')
        
        # enter new state
        self.state = state
        self.execAnyAndCurrentStateMethod( 'Entry')
        
        if self._stateChangeCallback is not None:
            self._stateChangeCallback( oldState, self.state)
         
    def _event(self, evName):
        assert(evName in self._listEvents),"Event %s not defined"%evName
        # Check if there is a matching transition
        
        # Check all transitions in ANY state and current state 
        transLists = []
        try:
            transLists.append(self._dictTransitions['ANY'])
        except KeyError:
            # ANY state may not exist
            pass
        
        if self.state is not None:
            transLists.append(self._dictTransitions[self.state])
        else:
            transLists.append(self._dictTransitions['']) # events in uninitialized state

        print("+++ EVENT %s in state %s transList %s" % (evName, self.state, transLists))
        
        for transList in transLists:
            for trans in transList:
                event,toState = trans
                if event == evName:
                    print("+++ TRANS %s -> %s" % (self.state, toState))
                    self.gotoState(toState)
                    break

#
# Test Code
#         
if __name__ == '__main__':
    class Computer(Fsm):
    
        def __init__(self):
            
            transitions = { 
                '':
                    [('INITIAL', 'Off')],
                'Off': 
                    [('PowerApplied', 'Standby')],
                'Standby':
                    [('PowerButtonPressed', 'NormalOp')],
                'NormalOp':
                    [('PowerButtonPressed', 'Standby'),
                     ('OsShutdown', 'Standby')],
                'ANY':
                    [('PowerRemoved', 'Off')]
            }
            
            super().__init__( dictTransitions=transitions )
                
        
        # Off actions    
        def State_Off_Entry(self):
            print("State_Off_Entry")
    
        def State_Off_Exit(self):
            print("State_Off_Exit")
        

    
    comp = Computer()
    #print("events ", comp._listEvents)
    #print("trans ", comp._dictTransitions)

    comp.startFsm()
    
    comp.event('PowerApplied')
    print("State %s" % comp.state)
    comp.event('PowerButtonPressed')
    print("State %s" % comp.state)
    comp.event('PowerRemoved')
    print("State %s" % comp.state)
    
