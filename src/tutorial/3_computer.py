'''
Created on 12.02.2017

@author: Klaus Popp

Simulate the behavior of a computer (power on, power button etc.) via Moddy FSM 

The Stim part simulates power on/off, power button press and OS shutdown events.
The KVM part simulates user "Requests". 

The FSM demonstrates how states and transitions are specified.


'''

from moddy import *
whiteOnGreen = {'boxStrokeColor':'black', 'boxFillColor':'green', 'textColor':'white'}
whiteOnRed = {'boxStrokeColor':'black', 'boxFillColor':'red', 'textColor':'white'}
whiteOnBlue = {'boxStrokeColor':'blue', 'boxFillColor':'blue', 'textColor':'white'}
blackOnWhite = {'boxStrokeColor':'black', 'boxFillColor':'white', 'textColor':'black'}

class Computer(simFsmPart):

    def __init__(self, sim, objName):
        statusBoxReprMap = {
            'Off':      (None, blackOnWhite),
            'Standby':  ('SBY', whiteOnRed),
            'Booting':  ('BOOT', whiteOnBlue),
            'NormalOp': ('NORM', whiteOnGreen),
            'Shutdown':  ('SD', whiteOnRed)
        }
        
        
        
        super().__init__(sim=sim, objName=objName, fsm=self.FSM(self), statusBoxReprMap=statusBoxReprMap)

        # Ports & Timers
        self.createPorts('in', ['powerPort', 'powerButtonPort', 'osPort'])
        self.createPorts('io', ['kvmPort']) 
        self.createTimers(['bootTmr', 'shutdownTmr', 'blinkCursorTmr'])

        
    class FSM(Fsm):
        def __init__(self, part):
            self._part = part
            
            transitions = { 
                '': # FSM uninitialized
                    [('INITIAL', 'Off')],                
                'Off': 
                    [('PowerApplied', 'Standby')],
                'Standby':
                    [('powerButtonPort_Msg', 'Booting')],
                'Booting':
                    [('bootTmr_Expired', 'NormalOp')],
                'NormalOp':
                    [('powerButtonPort_Msg', 'Shutdown'),
                     ('osPort_Msg', 'Shutdown'),
                     ('blinkCursorTmr_Expired', 'NormalOp')], # transition to self, should execute the do method
                'Shutdown':
                    [('shutdownTmr_Expired', 'Standby')],
                'ANY':
                    [('PowerRemoved', 'Off')]
            }
            
            super().__init__( dictTransitions=transitions )
                
        
        # Off actions    
        def State_Off_Entry(self):
            print("State_Off_Entry")
            self._part.bootTmr.stop()
            self._part.shutdownTmr.stop()
            self._part.blinkCursorTmr.stop()
        # Booting actions
        def State_Booting_Entry(self):
            print("Booting_Entry")
            self._part.bootTmr.start(12)
    
        # Shutdown actions
        def State_Shutdown_Entry(self):
            self._part.shutdownTmr.start(5)
        
        # Cursor Blink in NormalOp state
        def State_NormalOp_Entry(self):
            self._cursorState = 'on'
        
        def State_NormalOp_Do(self):
            self._part.blinkCursorTmr.start(3)
            if self._cursorState == 'on':
                self._cursorState = 'off'
            else:
                self._cursorState = 'on'
                
            self._part.kvmPort.send('cursor %s' % self._cursorState, 0.1 )
            
        # Message handlers
        def State_ANY_powerPort_Msg(self, msg):
            if msg == 'on':
                self.event('PowerApplied')
            elif msg == 'off':
                self.event('PowerRemoved')
                
        def State_NormalOp_kvmPortIn_Msg(self, msg):
            self._part.kvmPort.send('reply',0.1)
                
class Stim(vSimpleProg):   
    def __init__(self, sim):
        super().__init__(sim=sim, objName="Stim", parentObj=None)
        self.createPorts('out', ['powerPort', 'powerButtonPort', 'osPort']) 
        self.powerButtonPort.setColor('green')
        self.osPort.setColor('red')
        
    def runVThread(self):
        while True:
            self.powerPort.send('on',1)
            self.wait(2)
            self.powerButtonPort.send('press',1)
            self.wait(25)
            self.osPort.send('shutdown',1)
            self.wait(2)
            self.powerPort.send('off',1)
            self.wait(1000)
    
class Kvm(vSimpleProg):   
    # Simulate user in/output via keyboard and video
    def __init__(self, sim):
        super().__init__(sim=sim, objName="KVM", parentObj=None)
        self.createPorts('SamplingIO', ['kvmPort']) 
        
    def runVThread(self):
        while True:
            self.wait(5)
            self.kvmPort.send('request',0.1)
        
        
if __name__ == '__main__':         
    simu = sim()
    comp = Computer(simu, "comp")
    stim = Stim(simu)
    kvm = Kvm(simu)
    
    stim.powerPort.bind(comp.powerPort)
    stim.powerButtonPort.bind(comp.powerButtonPort)
    stim.osPort.bind(comp.osPort)
    kvm.kvmPort.bind(comp.kvmPort)
    
    moddyGenerateFsmGraph( fsm=comp.fsm, fileName='3_computer_fsm.svg')  
    
    simu.run(100)
    
    moddyGenerateSequenceDiagram( sim=simu, 
                              fileName="3_computer.html", 
                              fmt="svgInHtml", 
                              showPartsList=[stim, comp, kvm], 
                              timePerDiv = 1.0, 
                              pixPerDiv = 30) 
    
