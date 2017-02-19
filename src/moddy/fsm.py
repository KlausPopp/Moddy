'''
Created on 11.02.2017

@author: Klaus Popp

A general finite state machine with hierarchical state support
'''
def isSubFsmSpecification(nameClsTuple):
    name, cls = nameClsTuple
    if type(cls) is type:
        return cls
    else:
        return None

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
    
    Note that entry and exit actions are NOT called at self transitions (transitions to the current state)
    
        # Off actions    
        def State_Off_Entry(self):
            print("State_Off_Entry")
    
        def State_Off_Exit(self):
            print("State_Off_Exit")
    
    You can also define a "do" Method that is invoked
    - after the "Entry" methode
    - at self transistions to the state
    These methods must follow the naming convention "STATE_<statename>_Do".
    
    
    Such routines can be also defined for the special 'ANY' state. If they exist they are called at
    the entry or exit or self transitions to/from any state.

    Note: You cannot define actions for transitions!
            
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
    
    
    Hierarchically Nested State Support
    https://en.wikipedia.org/wiki/UML_state_machine#Hierarchically_nested_states
    
    Rules:
    Nested states are defined by the user in the transition list: 
     
    
    Main FSM:
                transitions = { 
                '':
                    [('INITIAL', 'Off')],
                'Off': 
                    [('PowerApplied', 'Standby')],
                'Standby':
                    [('PowerButtonPressed', 'NormalOp')],
                'NormalOp':
                    [ 
                    ####### NESTED FSM ('fsm-Name', Class-Name)
                     ('fsm-name' , subfsm),
                     ('PowerButtonPressed', 'Standby'),
                     ('OsShutdown', 'Standby')],
                'ANY':
                    [('PowerRemoved', 'Off')]
            }

    A nested FSM is instantiated when the upper level state is entered
    A nested FSM cannot exit
    A nested FSM receives all events from the upper level FSM. If the event is not known in the nested FSM,
    it is directed to the upper FSM. Events that are known in the nested FSM are NOT directed to upper FSM 

    If the upper state exits, the exit action of the current states (first, the state in the nested fsm, then the upper fsm) 
    are called. Then the nested fsm is terminated.
    
    Orthogonal nested states are also supported. Meaning, multiple nested fsms exist in parallel  
    '''
    
    def __init__(self, dictTransitions, parentFsm=None):
        '''
        dictTransitions must be a dictionary, with the transitions (see example in class doc)

        The dict key is the state, and the values are a list of transition from
        that state. Each transition consists of a tuple (event, targetState).
        
        
        '''
        self.state = None
        self._parentFsm = parentFsm
        self._listChildFsms = [] # currently ACTIVE children
        
        self._dictTransitions = dictTransitions
        self._stateChangeCallback = None
        self._listEvents = []
        
        # Validate transitions and build list of events
        for state, listTrans in dictTransitions.items():
            for trans in listTrans:
                if isSubFsmSpecification(trans) is None:
                    event, toState = trans
                
                    if event not in self._listEvents:
                        self._listEvents.append(event)
                        
                    assert(self.stateExists(toState)),"toState %s doesn't exist" % toState
                    assert(toState != 'ANY'),"ANY cannot be a target state"    
        
        # check for initial event and remove it
        try: idxInitial = self._listEvents.index('INITIAL')
        except ValueError: 
            raise Exception('INITIAL event missing')
        
        del self._listEvents[idxInitial]
    #
    # Public API
    # 
    def getDictTransitions(self):
        return self._dictTransitions        
                
    def execAnyAndCurrentStateMethod(self, methodName, *args):
        ''' 
        Execute the state specific methods:
         The method self.State_ANY_<methodName>(*args) is called if it exists.
         The method self.State_<stateName>_<methodName>(*args) is called if it exists.
         Returns True if at least one method exists
        '''
        handled = 0
        if self.execStateMethod('ANY', methodName, *args) == True:
            handled += 1
        if self.execStateMethod(self.state, methodName, *args) == True:
            handled += 1
        return handled > 0

    def setStateChangeCallback(self, callback):
        ''' Register a method that is called whenever the state of the fsm changes '''
        self._stateChangeCallback = callback

    def hasEvent(self,evName):
        ''' check if the event is known by the fsm or a currently active statemachine '''
        rv = False
        if evName in self._listEvents:
            rv = True
        else:
            for subFsm in self._listChildFsms:
                if subFsm.hasEvent(evName):
                    rv = True
                    break
        return rv
        
    
    def startFsm(self):
        assert(self.state is None)
        self._event('INITIAL')     

    def event(self, evName):
        '''
        Execute an Event in the "ANY" and current state.
        Raises AssertError if the current state is None.
        Returns True if the event causes a state change, False if not.
        '''
        assert(self.state is not None),"Did you call startFsm?"
        return self._event(evName)
        
    #
    # Internal methods
    #
    
    def execStateMethod(self, state, methodName, *args):
        '''
        Execute a state specific method that might exist in the fsm subclass.
        
        The method self.State_<stateName>_<methodName>(*args) is called if it exists, True is returned.
        If it doesn't exist, nothing happens, but False is returned.   
        '''
        execStr = "self.State_%s_%s" % (state, methodName)
        #print("execStateMethod %s" % execStr)
        try: 
            exec( "m=" + execStr)

        except AttributeError:
            #print("%s execStateMethod cannot exec %s" % (type(self).__name__,execStr))
            return False
        
        exec(execStr + "(*args)")
        return True
        
    def stateExists(self, state):
        return state in self._dictTransitions
        
    def gotoState(self, state):
        assert(state != 'ANY' and self.stateExists(state)),"gotoState invalid state %s"%state
        
        if self.state != state: # ignore self transitions
            oldState = self.state        
            print("+++ GOTO STATE %s" % state)
            # exit old state
            if self.state is not None:
                # terminate subFsms
                self.terminateSubFsms()
                # call current state Exit method
                self.execAnyAndCurrentStateMethod( 'Exit')
            
            # enter new state
            self.state = state
            self.execAnyAndCurrentStateMethod( 'Entry')
            
            # Start any possible nested fsms
            self.startSubFsms()
            
            if self._stateChangeCallback is not None:
                self._stateChangeCallback( oldState, self.state)
        # in any case, execute the "Do" Method of the current state
        self.execAnyAndCurrentStateMethod( 'Do')
         
    def _event(self, evName):
        '''
        Execute an Event in the "ANY" and current state.
        Returns True if the event causes a state change, False if not.
        '''
        # Check if there is a matching transition
        oldState = self.state
        
        # first, check if the current state has subFsms which handle the event
        # if event handled by subFsm, ignore the event for this fsm
        if self.passEventToSubFsms( evName ) == False:
            
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
    
            print("+++ %s EVENT %s in state %s" % (type(self).__name__, evName, self.state))
            
            for transList in transLists:
                for trans in transList:
                    if isSubFsmSpecification(trans) is None:
                        event,toState = trans
                        if event == evName:
                            print("+++ %s TRANS %s -> %s" % (type(self).__name__,self.state, toState))
                            self.gotoState(toState)
                            break
        return oldState != self.state

    def passEventToSubFsms(self, evName):
        ''' 
        check if the current state has subFsms which handle the event
        if event handled by subFsm, return True
        '''
        handled = False
        for subFsm in self._listChildFsms:
            if subFsm.hasEvent(evName):
                subFsm.event(evName)
                print("Event %s handled by subFsm %s" % (evName, type(subFsm).__name__))
                handled = True
                
        return handled
    

    
    def startSubFsms(self):
        transList = self._dictTransitions[self.state]
        for trans in transList:
            subFsmCls = isSubFsmSpecification(trans)
            if subFsmCls is not None: 
                # create new fsm
                subFsm = subFsmCls(parentFsm = self)
                # add subFsm to list of active subFsms
                self._listChildFsms.append(subFsm)
                # goto initial state
                subFsm.startFsm()
    
    def terminateSubFsms(self):
        for subFsm in self._listChildFsms:
            subFsm.execAnyAndCurrentStateMethod( 'Exit')
        self._listChildFsms = []

#
# Test Code
#         
if __name__ == '__main__':
    from moddy import moddyGenerateFsmGraph
    class Computer(Fsm):
    
        def __init__(self, parentFsm=None):
            
            transitions = { 
                '':
                    [('INITIAL', 'Off')],
                'Off': 
                    [('PowerApplied', 'Standby')],
                'Standby':
                    [('PowerButtonPressed', 'NormalOp')],
                'NormalOp':
                    [
                     ('Apps' , Computer.ApplicationsFsm ),  # SUBFSM
                     ('Vol' , Computer.VolumeFsm ),         # SUBFSM
                     ('PowerButtonPressed', 'Standby'),
                     ('OsShutdown', 'Standby')],
                'ANY':
                    [('PowerRemoved', 'Off')]
            }
            
            super().__init__( dictTransitions=transitions, parentFsm=parentFsm )
                
        
        # Off actions    
        def State_Off_Entry(self):
            print("State_Off_Entry")
    
        def State_Off_Exit(self):
            print("State_Off_Exit")
        

        # Subfsm 
        class ApplicationsFsm(Fsm):
        
            def __init__(self, parentFsm):
                
                transitions = { 
                    '':
                        [('INITIAL', 'Radio')],
                    'Radio': 
                        [('NaviButton', 'Navi')],
                    'Navi':
                        [('RadioButton', 'Radio')]
                }
                
                super().__init__( dictTransitions=transitions, parentFsm=parentFsm )
                
            def State_Radio_Entry(self):
                print("State_Radio_Entry")
        
            def State_Radio_Exit(self):
                print("State_Radio_Exit")
    
            def State_Navi_Exit(self):
                print("State_Radio_Exit")
                
        class VolumeFsm(Fsm):
        
            def __init__(self, parentFsm):
                
                transitions = { 
                    '':
                        [('INITIAL', 'On')],
                    'On': 
                        [('MuteButton', 'Mute'),
                         ('IncVol', 'On'),
                         ('DecVol', 'On')],
                    'Mute':
                        [('MuteButton', 'On'),
                         ('IncVol', 'On')]
                }
                
                super().__init__( dictTransitions=transitions, parentFsm=parentFsm )
                
            def State_On_Exit(self):
                print("State_On_Exit")
    
    comp = Computer()
    #print("events ", comp._listEvents)
    #print("trans ", comp._dictTransitions)

    comp.startFsm()
    
    comp.event('PowerApplied')
    print("State %s" % comp.state)
    comp.event('PowerButtonPressed')
    print("State %s" % comp.state)
    comp.event('RadioButton')
    comp.event('MuteButton')
    comp.event('IncVol')
    comp.event('PowerRemoved')
    print("State %s" % comp.state)
    
    moddyGenerateFsmGraph(comp, fileName='computerFsm.svg', keepGvFile=True)
    