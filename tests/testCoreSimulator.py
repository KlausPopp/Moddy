'''
Created on 23.12.2018

@author: klauspopp@gmx.de
'''


import unittest
import os
from moddy import *

def searchTrc( trc, time, subObj, action):
    for e in trc:
        #print("searchTrc %f %s %s" % (e.traceTime, e.subObj.hierarchyName(), e.action))
        if e.traceTime == time and e.subObj == subObj and e.action == action:
            return e
    return None    
    
def searchInMsg(trc, time, port):
    e = searchTrc( trc, time, port, "<MSG")
    if e is None: raise RuntimeError("searchInMsg not found")
    return e.transVal._msg.__str__()

def searchAnn(trc, time, part):
    e = searchTrc( trc, time, part, "ANN")
    if e is None: raise RuntimeError("searchAnn not found")
    return e.transVal.__str__()

def searchTExp(trc, time, subObj):
    e = searchTrc( trc, time, subObj, "T-EXP")
    if e is None: raise RuntimeError("searchTExp not found")
    return True
    

class TestSimulatorMsgPassing(unittest.TestCase):
    '''
    Test the simulator core
    '''

    class Consumer(simPart):
        def __init__(self, sim, objName):
            super().__init__(sim=sim, objName=objName)
    
            self.createPorts('in', ['consPort'])
            self.createTimers(['timeoutTmr'])
            self.timeoutTmr.restart(5)
    
        def consPortRecv(self, port, msg):
            self.addAnnotation(msg)
            # damage msg
            msg = {}
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
            self.prodPort.send(msg, 0.1)
            
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
                                  fileName="output/%s.html" % __name__, 
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
        self.assertEqual(searchInMsg(trc, 8.1, cons1.consPort), "{'submsg': {'subattr': 567}}" )    
        self.assertEqual(searchInMsg(trc, 8.1, cons2.consPort), "{'submsg': {'subattr': 567}}" )    

        # check if second and third message is correctly received on both consumers as ANN
        self.assertEqual(searchAnn(trc, 8.0, cons1), "{'submsg': {'subattr': 234}}" )    
        self.assertEqual(searchAnn(trc, 8.0, cons2), "{'submsg': {'subattr': 234}}" )    
        self.assertEqual(searchAnn(trc, 8.1, cons1), "{'submsg': {'subattr': 567}}" )    
        self.assertEqual(searchAnn(trc, 8.1, cons2), "{'submsg': {'subattr': 567}}" )    

        # check timeouts
        self.assertEqual(searchTExp(trc, 13.1, cons1.timeoutTmr), True )    
        self.assertEqual(searchTExp(trc, 13.1, cons2.timeoutTmr), True )    
        self.assertEqual(searchAnn(trc, 13.1, cons1), "Timeout" )    
        self.assertEqual(searchAnn(trc, 13.1, cons2), "Timeout" )    
        
if __name__ == '__main__':
    unittest.main()