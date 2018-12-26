'''
Created on 25.12.2018

@author: klauspopp@gmx.de
'''
import unittest
from moddy import *
from tests.utils import *

class TestFsm(unittest.TestCase):
    '''
    Test the moddy FSM with sub-fsms
    '''

    class CarInfoSystem(simFsmPart):
    
        def __init__(self, sim, objName):
            statusBoxReprMap = {
                'Off':      (None, bcBlackOnWhite),
                'Standby':  ('SBY', bcWhiteOnRed),
                'Booting':  ('BOOT', bcWhiteOnBlue),
                'NormalOp': ('NORM', bcWhiteOnGreen),
                'Shutdown':  ('SD', bcWhiteOnRed)
            }
            
            
            super().__init__(sim=sim, objName=objName, fsm=self.FSM(), statusBoxReprMap=statusBoxReprMap)
    
            # Ports & Timers
            self.createPorts('in', ['powerPort', 'ignitionPort', 'buttonPort'])
            self.createPorts('out', ['audioPort', 'visualPort'])
            self.createTimers(['bootTmr', 'shutdownTmr', 'clockTmr'])
    
            
        class FSM(Fsm):
            def __init__(self):
                
                transitions = { 
                    '': # FSM uninitialized
                        [('INITIAL', 'Off')],                
                    'Off': 
                        [('PowerApplied', 'Standby')],
                    'Standby':
                        # This transition is triggered whenever ANY message arrives on the powerButtonPort
                        [('PowerButton', 'Booting'),
                         ('IgnitionOn', 'Booting')],
                    'Booting':
                        [('bootTmr_Expired', 'NormalOp')],
                    'NormalOp':
                         # The following two lines specify nested state machines, executing in parallel
                        [('Apps' , TestFsm.CarInfoSystem.FSM.ApplicationsFsm ),  
                         ('Vol' , TestFsm.CarInfoSystem.FSM.VolumeFsm ),         
                         # This transition is triggered whenever ANY message arrives on the powerButtonPort
                         ('PowerButton', 'Shutdown'),
                         ('IgnitionOff', 'Shutdown'),
                         # This transition is triggered whenever clockTmr expires, transition to self, 
                         # executes the 'Do' methode
                         ('clockTmr_Expired', 'NormalOp')], 
                    'Shutdown':
                        [('shutdownTmr_Expired', 'Standby')],
                    'ANY':
                        [('PowerRemoved', 'Off')]
                }
                
                super().__init__( dictTransitions=transitions )
                    
            
            # Off actions    
            def State_Off_Entry(self):
                print("State_Off_Entry")
                self.moddyPart().bootTmr.stop()
                self.moddyPart().shutdownTmr.stop()
                self.moddyPart().clockTmr.stop()
            # Booting actions
            def State_Booting_Entry(self):
                print("Booting_Entry")
                self.moddyPart().bootTmr.start(5)
        
            # Shutdown actions
            def State_Shutdown_Entry(self):
                self.moddyPart().shutdownTmr.start(2)
            
            # Cursor Blink in NormalOp state
            def State_NormalOp_Entry(self):
                self._clockTime = 100
                
            def State_NormalOp_Do(self):
                self.moddyPart().clockTmr.start(5)                
                self.moddyPart().visualPort.send('time %d' % self._clockTime, 0.1 )
                self._clockTime += 5
                
            # Message handlers
            def State_ANY_powerPort_Msg(self,msg):
                if msg == 'on':
                    self.event('PowerApplied')
                elif msg == 'off':
                    self.event('PowerRemoved')
                                
            def State_ANY_ignitionPort_Msg(self, msg):
                if msg == 'on':
                    self.event('IgnitionOn')
                elif msg == 'off':
                    self.event('IgnitionOff')
    
            def State_ANY_buttonPort_Msg(self, msg):            
                self.event(msg) # Message are directly the event names
            
            # Nested state machine CarInfo System Applications
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
                    self.moddyPart().addAnnotation('Radio activated')
            
                def State_Navi_Entry(self):
                    self.moddyPart().addAnnotation('Navi activated')
                    
            class VolumeFsm(Fsm):
            
                def __init__(self, parentFsm):
                    self._volume = 50
                    
                    transitions = { 
                        '':
                            [('INITIAL', 'On')],
                        'On': 
                            [('MuteButton', 'Mute'),
                             ('VolKnobRight', 'IncVol'),
                             ('VolKnobLeft', 'DecVol')],
                        'IncVol':
                            [('VolChangeDone', 'On')],
                        'DecVol':
                            [('VolChangeDone', 'On')],
                        'Mute':
                            [('MuteButton', 'On'),
                             ('VolKnobRight', 'On')]
                    }
                    
                    super().__init__( dictTransitions=transitions, parentFsm=parentFsm )
                    
                def State_On_Do(self):
                    self.moddyPart().audioPort.send('volume=%d' % self._volume, 0.1)
                    
                def State_Mute_Do(self):
                    self.moddyPart().audioPort.send('volume=%d' % 0, 0.1)
    
                def State_IncVol_Entry(self):
                    self._volume += 1
                    self.topFsm().event('VolChangeDone')
    
                def State_DecVol_Entry(self):
                    self._volume -= 1
                    self.topFsm().event('VolChangeDone')
     
    class Stim(vSimpleProg):   
        def __init__(self, sim):
            super().__init__(sim=sim, objName="Stim", parentObj=None)
            self.createPorts('out', ['powerPort', 'ignitionPort', 'buttonPort']) 
            self.createPorts('SamplingIn', ['audioPort', 'visualPort']) 
            self.ignitionPort.setColor('red')
            self.buttonPort.setColor('blue')
            
        def runVThread(self):
            while True:
                self.powerPort.send('on',1)
                self.wait(2)
                self.buttonPort.send('PowerButton',1)
                self.wait(8)
                self.buttonPort.send( 'NaviButton', 0.5)
                self.wait(2)
                self.buttonPort.send( 'VolKnobRight', 0.5)
                self.buttonPort.send( 'VolKnobRight', 0.5)
                self.wait(1)
                self.buttonPort.send( 'VolKnobLeft', 0.5)
                self.wait(1)
                self.buttonPort.send( 'MuteButton', 0.5)
                self.wait(1)
                self.buttonPort.send( 'VolKnobRight', 0.5)
                self.wait(5)
                self.ignitionPort.send('off',1)
                self.wait(2)
                self.powerPort.send('off',1)
                self.wait(None)


    def testCarInfo(self):
        simu = sim()
        cis = TestFsm.CarInfoSystem(simu, "CarInfoSys")
        stim = TestFsm.Stim(simu)
        
        # bind ports
        stim.powerPort.bind(cis.powerPort)
        stim.ignitionPort.bind(cis.ignitionPort)
        stim.buttonPort.bind(cis.buttonPort)
        cis.visualPort.bind(stim.visualPort)
        cis.audioPort.bind(stim.audioPort)
            
        simu.run(100)
        
        moddyGenerateSequenceDiagram( sim=simu, 
                                  fileName="output/%s.html" % funcName(),  
                                  fmt="iaViewerRef", 
                                  showPartsList=[stim, cis], 
                                  timePerDiv = 0.3, 
                                  pixPerDiv = 30,
                                  title = "Car Info FSM Test") 
           
        trc = simu.tracedEvents()

        # check CarInfo Main states
        self.assertEqual(searchSta(trc, 1.0, cis), "SBY" )    
        self.assertEqual(searchSta(trc, 3.0, cis), "BOOT" )    
        self.assertEqual(searchSta(trc, 8.0, cis), "NORM" )    
        self.assertEqual(searchSta(trc, 21.0, cis), "SD" )    
         
        self.assertEqual(searchAnn(trc, 8.0, cis), "Radio activated" )    
        self.assertEqual(searchAnn(trc, 10.5, cis), "Navi activated" )    
         
        self.assertEqual(searchInMsg(trc, 12.6, stim.audioPort), "volume=51" )    
        self.assertEqual(searchInMsg(trc, 13.1, stim.audioPort), "volume=52" )    
        self.assertEqual(searchInMsg(trc, 14.6, stim.audioPort), "volume=0" )    

        self.assertEqual(searchInMsg(trc, 18.1, stim.visualPort), "time 110" )    

if __name__ == "__main__":
    unittest.main()