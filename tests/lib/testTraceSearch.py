'''
Created on 16.09.2019

@author: klauspopp@gmx.de
'''
import unittest
from moddy import *
from moddy.lib.traceSearch import TraceSearch

class TestTraceSearch(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.simu = simu = sim()
        
        vSimpleProg( sim=simu, objName="Bob", target=self.bobProg, elems={ 'QueuingIO': 'head' } )
        vSimpleProg( sim=simu, objName="Joe", target=self.joeProg, elems={ 'QueuingIO': 'head' } )
        
        simu.smartBind([ ['Bob.head', 'Joe.head'] ])
    
        # let simulator run
        simu.run(stopTime=12.0, enableTracePrinting=False, stopOnAssertionFailure=False)
        
        self.ts = TraceSearch(simu)
        idx = 0
        for te in self.ts.tracedEvents:
            print("#%d: %s" % (idx,te))
            idx+=1
            
    def testfindAnn(self):
        ts = self.ts

        # find any ANN        
        rv = ts.findAnn('Bob', None, 0)
        self.assertEqual(rv[0], 16)
        self.assertEqual(rv[1].transVal, "got message Hi, How are you?")
         
        rv = ts.findAnn('Bob', None)
        self.assertEqual(rv[0], 34)
        self.assertEqual(rv[1].transVal, "got message Fine")
        
        # find with wildcard match
        rv = ts.findAnn('Bob', "*Fine", 15)
        self.assertEqual(rv[0], 34)
        self.assertEqual(rv[1].transVal, "got message Fine")
        
    def testfindSta(self):
        ts = self.ts

        rv = ts.findSta('Joe', "Think", 0)
        self.assertEqual(rv[0], 9)
        rv = ts.findSta('Joe', "")
        self.assertEqual(rv[0], 13)
    
    def testfindRcvMsg(self):
        ts = self.ts

        rv = ts.findRcvMsg('Joe', None, 0)
        self.assertEqual(rv[0], 5)

    def testfindSndMsg(self):
        ts = self.ts

        rv = ts.findSndMsg('Bob', "Hi*", 0)
        self.assertEqual(rv[0], 1)

        rv = ts.findSndMsg('Bob', "How*")
        self.assertEqual(rv[0], 21)

    def testfindAssFail(self):
        ts = self.ts

        rv = ts.findAssFail('Bob', "Unknown*", 0)
        self.assertEqual(rv[0], 39)
        
        rv = ts.findAssFail('Joe', None, 0)
        self.assertEqual(rv, None)
        

    @staticmethod
    def bobProg(self: vSimpleProg):
        # bob starts talking
        self.head.send("Hi Joe", 1)
        
        while True:
            msg = self.waitForMsg(None, self.head)
            self.addAnnotation('got message ' + msg)
            
            self.busy( 1.4, 'Think')
            
            if msg == "Hi, How are you?":
                reply = "How are you?"
            else:
                self.assertionFailed("Unknown msg %s" % msg)
    
            self.head.send(reply, 1)
            
            
    @staticmethod
    def joeProg(self: vSimpleProg):
        while True:
            msg = self.waitForMsg(None, self.head)
            self.addAnnotation('got message ' + msg)
            
            self.busy( 2, 'Think')
            
            if msg == "Hi Joe":
                reply = "Hi, How are you?"
            elif msg == "How are you?":
                reply = "Fine"
            else:
                reply = "Hm?"
    
    
            self.head.send(reply, 1.5)
    
    
    
    
