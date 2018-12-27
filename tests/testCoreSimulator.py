'''
Created on 23.12.2018

@author: klauspopp@gmx.de
'''


import unittest
from moddy import *
from tests.utils import *

    

class TestSimulatorMsgPassing(unittest.TestCase):
    '''
    Test the simulator core
    '''

    class Consumer(simPart):
        def __init__(self, sim, objName):
            super().__init__(sim=sim, objName=objName)
    
            self.createPorts('in', ['consPort'])
            self.createTimers(['timeoutTmr'])
            self.timeoutTmr.restart(5.1)
    
        def consPortRecv(self, port, msg):
            self.addAnnotation(msg.__str__())
            # damage msg
            msg["submsg"] = "ABC"
            self.timeoutTmr.restart(5)
    
        def timeoutTmrExpired(self, timer):
            self.addAnnotation("Timeout")
            
    
    class Producer(vSimpleProg):
        def __init__(self, sim, objName):
            # Initialize the parent class
            super().__init__(sim=sim, objName=objName, parentObj=None)
    
            # Ports
            self.createPorts('out', ['prodPort'])
    
        def runVThread(self):
            
            submsg = { "subattr" : 123 }
            msg = { "submsg": submsg }
            
            self.waitUntil( 2 )
            self.prodPort.send(msg, 3)
            # manipulate msg to test if deepcopy works
            submsg['subattr'] = 234
            self.prodPort.send(msg, 3)
            submsg['subattr'] = 567
            self.prodPort.send(msg, 0.0)
            
    def testSimulatorMsgPassing(self):
        simu = sim()
    
        prod = TestSimulatorMsgPassing.Producer( simu, "Prod" )
        cons1 = TestSimulatorMsgPassing.Consumer( simu, "Cons1" )
        cons2 = TestSimulatorMsgPassing.Consumer( simu, "Cons2" )
        
        prod.prodPort.bind(cons1.consPort)
        prod.prodPort.bind(cons2.consPort)
    
        # let simulator run
        simu.run(stopTime=100)

        moddyGenerateSequenceDiagram( sim=simu, 
                                  showPartsList=["Prod","Cons1","Cons2"],
                                  fileName="output/%s_%s.html" % (baseFileName(), funcName()), 
                                  fmt="iaViewerRef", 
                                  timePerDiv = 1.0, 
                                  pixPerDiv = 30)

        trc = simu.tracedEvents()

        # check if first message is correctly received on both consumers in trace
        self.assertEqual(searchInMsg(trc, 5.0, cons1.consPort), "{'submsg': {'subattr': 123}}" )    
        self.assertEqual(searchInMsg(trc, 5.0, cons2.consPort), "{'submsg': {'subattr': 123}}" )    

        # check if first message is correctly received on both consumers as ANN
        self.assertEqual(searchAnn(trc, 5.0, cons1), "{'submsg': {'subattr': 123}}" )    
        self.assertEqual(searchAnn(trc, 5.0, cons2), "{'submsg': {'subattr': 123}}" )    

        # check if second and third message is correctly received on both consumers in trace
        self.assertEqual(searchInMsg(trc, 8.0, cons1.consPort), "{'submsg': {'subattr': 234}}" )    
        self.assertEqual(searchInMsg(trc, 8.0, cons2.consPort), "{'submsg': {'subattr': 234}}" )    
        self.assertEqual(searchInMsg(trc, 8.0, cons1.consPort, 2), "{'submsg': {'subattr': 567}}" )    
        self.assertEqual(searchInMsg(trc, 8.0, cons2.consPort, 2), "{'submsg': {'subattr': 567}}" )    

        # check if second and third message is correctly received on both consumers as ANN
        self.assertEqual(searchAnn(trc, 8.0, cons1), "{'submsg': {'subattr': 234}}" )    
        self.assertEqual(searchAnn(trc, 8.0, cons2), "{'submsg': {'subattr': 234}}" )    
        self.assertEqual(searchAnn(trc, 8.0, cons1, 2), "{'submsg': {'subattr': 567}}" )    
        self.assertEqual(searchAnn(trc, 8.0, cons2, 2), "{'submsg': {'subattr': 567}}" )    

        # check timeouts
        self.assertEqual(searchTExp(trc, 13.0, cons1.timeoutTmr), True )    
        self.assertEqual(searchTExp(trc, 13.0, cons2.timeoutTmr), True )    
        self.assertEqual(searchAnn(trc, 13.0, cons1), "Timeout" )    
        self.assertEqual(searchAnn(trc, 13.0, cons2), "Timeout" )    
        
if __name__ == '__main__':
    unittest.main()