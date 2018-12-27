'''
Created on 27.12.2018

@author: klauspopp@gmx.de
'''
import unittest
from moddy import *
from tests.utils import *


class TestSchedRtos(unittest.TestCase):

    def testScheduling(self):
        busyAppearance = bcWhiteOnBlue
        
        class myThread1(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='hiThread', parentObj=None)
            def runVThread(self):
                print("   VtHi1")
                self.busy(50,'1',busyAppearance)
                print("   VtHi2")
                self.wait(20,[])
                print("   VtHi3")
                self.busy(10,'2',busyAppearance)
                print("   VtHi4")
                self.wait(100,[])
                print("   VtHi5")
                self.wait(100,[])
                while True:
                    print("   VtHi5")
                    self.busy(10,'3',busyAppearance)
                    self.wait(5,[])
    
        class myThread2(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='lowThreadA', parentObj=None)
            def runVThread(self):
                print("   VtLoA1")
                self.busy(50,'1',busyAppearance)
                print("   VtLoA2")
                self.wait(20,[])
                print("   VtLoA3")
                self.busy(20,'2',busyAppearance)
                print("   VtLoA4")
                self.busy(250,'3',busyAppearance)
            
        class myThread3(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='lowThreadB', parentObj=None)
            def runVThread(self):
                print("   VtLoB1")
                self.busy(50,'1',busyAppearance)
                print("   VtLoB2")
                self.wait(20,[])
                print("   VtLoB3")
                self.busy(100,'2',busyAppearance)
                print("   VtLoB4")
                self.busy(250,'3',busyAppearance)
    
        simu = sim()
        sched= vtSchedRtos(sim=simu, objName="sched", parentObj=None)
                
        t1 = myThread1(simu)
        t2 = myThread2(simu)
        t3 = myThread3(simu)
        sched.addVThread(t1, 0)
        sched.addVThread(t2, 1)
        sched.addVThread(t3, 1)
        simu.run(400)
        
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()), 
                                      fmt="iaViewerRef", 
                                      showPartsList=[t1,t2,t3],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  

        trc = simu.tracedEvents()
        
        self.assertEqual(searchSta(trc, 0.0, t1), "1" )
        self.assertEqual(searchSta(trc, 0.0, t2), "PE" )
        self.assertEqual(searchSta(trc, 0.0, t3), "PE" )

        self.assertEqual(searchSta(trc, 50.0, t1), "" )
        self.assertEqual(searchSta(trc, 50.0, t2), "1" )

        self.assertEqual(searchSta(trc, 70.0, t1), "2" )
        self.assertEqual(searchSta(trc, 70.0, t2), "PE" )
        
        self.assertEqual(searchSta(trc, 80.0, t1), "" )
        self.assertEqual(searchSta(trc, 80.0, t3), "1" )

        self.assertEqual(searchSta(trc, 130.0, t2), "1" )
        self.assertEqual(searchSta(trc, 130.0, t3), "" )

        self.assertEqual(searchSta(trc, 160.0, t3), "2" )

        self.assertEqual(searchSta(trc, 280.0, t1), "3" )

    def testQueingPort(self):
        busyAppearance = bcWhiteOnBlue
        class myThread1(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Thread', parentObj=None)
                self.createPorts('QueuingIn', ['inP1'])
            
            def getAllMsg(self):
                lstMsg = []
                while True:
                    try:
                        msg = self.inP1.readMsg()
                        lstMsg.append(msg)
                    except BufferError:
                        break
                
                self.addAnnotation(lstMsg)
         
             
            def runVThread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.busy(33, cycle, busyAppearance)
                    self.getAllMsg()
                    print(self.wait(20, [self.inP1]))
                    self.getAllMsg()


        class stimThread(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Stim', parentObj=None)
                self.createPorts('out', ['toT1Port'])
                                
            def runVThread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15,[])
                    self.toT1Port.send('hello%d' % count,5)


        simu = sim()
                        
        t1 = myThread1(simu)
        
        stim = stimThread(simu)
        stim.toT1Port.bind(t1.inP1)
        
        simu.run(200)
        
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()),
                                      fmt="iaViewerRef", 
                                      showPartsList=[stim,t1],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  
  
        trc = simu.tracedEvents()
        
        self.assertEqual(searchAnn(trc, 33.0, t1), "['hello1']" )
        self.assertEqual(searchAnn(trc, 35.0, t1), "['hello2']" )
        self.assertEqual(searchAnn(trc, 68.0, t1), "['hello3', 'hello4']" )
        self.assertEqual(searchAnn(trc, 80.0, t1), "['hello5']" )
        self.assertEqual(searchAnn(trc, 113.0, t1), "['hello6', 'hello7']" )

    def testQueingIOPort(self):
        busyAppearance = bcWhiteOnBlue
        class myThread1(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Thread', parentObj=None)
                self.createPorts('QueuingIO', ['ioP1'])
            
            def getAllMsg(self):
                lstMsg = []
                while True:
                    try:
                        msg = self.ioP1.readMsg()
                        lstMsg.append(msg)
                    except BufferError:
                        break
                
                self.addAnnotation(lstMsg)
         
             
            def runVThread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.busy(33, cycle, busyAppearance)
                    self.getAllMsg()
                    print(self.wait(18-cycle*2, [self.ioP1]))
                    self.getAllMsg()


        class stimThread(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Stim', parentObj=None)
                self.createPorts('out', ['toT1Port'])
                                
            def runVThread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15,[])
                    self.toT1Port.send('hello%d' % count,5)


        simu = sim()
                        
        t1 = myThread1(simu)
        
        stim = stimThread(simu)
        stim.toT1Port.bind(t1.ioP1._inPort)
        
        simu.run(200)
        
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()),
                                      fmt="iaViewerRef", 
                                      showPartsList=[stim,t1],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  
  
        trc = simu.tracedEvents()
        
        self.assertEqual(searchAnn(trc, 33.0, t1), "['hello1']" )
        self.assertEqual(searchAnn(trc, 35.0, t1), "['hello2']" )
        self.assertEqual(searchAnn(trc, 68.0, t1), "['hello3', 'hello4']" )
        self.assertEqual(searchAnn(trc, 80.0, t1), "['hello5']" )
        self.assertEqual(searchAnn(trc, 113.0, t1), "['hello6', 'hello7']" )
        self.assertEqual(searchAnn(trc, 125.0, t1), "[]" ) # timeout
        self.assertEqual(searchAnn(trc, 158.0, t1), "['hello8', 'hello9', 'hello10']" )


    def testSamplingPort(self):
        busyAppearance = bcWhiteOnBlue
        class myThread1(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Thread', parentObj=None)
                self.createPorts('SamplingIn', ['inP1'])
                
            def showMsg(self):
                msg = self.inP1.readMsg(default='No message')
                self.addAnnotation(msg)
                
            def runVThread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.showMsg()
                    self.busy(18,cycle, busyAppearance)
                    self.showMsg()
                    self.busy(14,cycle, busyAppearance)
                    self.wait(20,[self.inP1])


        class stimThread(vSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Stim', parentObj=None)
                self.createPorts('out', ['toT1Port'])
                                
            def runVThread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15)
                    self.toT1Port.send('hello%d' % count,5)


        simu = sim()
                        
        t1 = myThread1(simu)
        
        stim = stimThread(simu)
        stim.toT1Port.bind(t1.inP1)
        
        simu.run(200)
        
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()),
                                      fmt="iaViewerRef", 
                                      showPartsList=[stim,t1],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  
         
        trc = simu.tracedEvents()
        
        self.assertEqual(searchAnn(trc, 0.0, t1), "No message" )
        self.assertEqual(searchAnn(trc, 18.0, t1), "No message" )
        self.assertEqual(searchAnn(trc, 35.0, t1), "hello2" )
        self.assertEqual(searchAnn(trc, 53.0, t1), "hello3" )
        self.assertEqual(searchAnn(trc, 188.0, t1), "hello12" )

    def testVtTimer(self):
        busyAppearance = bcWhiteOnBlue
        class myThread1(vThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, objName='Thread', parentObj=None)
                self.createVtTimers(['tmr1'])
                
            def runVThread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.tmr1.start(16)
                    self.busy(18,cycle,busyAppearance)
                    self.addAnnotation("A Fired " + str(self.tmr1.hasFired()))
                    self.tmr1.start(20)
                    rv = self.wait(100,[self.tmr1])
                    self.addAnnotation("B rv " + rv)
                    self.tmr1.start(20)
                    rv = self.wait(30,[])
                    self.addAnnotation("C rv " + rv)
                    self.tmr1.start(40)
                    rv = self.wait(30,[self.tmr1])
                    self.addAnnotation("D Fired " + str(self.tmr1.hasFired()) + " rv " + rv)
                    self.tmr1.stop()

        simu = sim()
        sched= vtSchedRtos(sim=simu, objName="sched", parentObj=None)
                        
        t1 = myThread1(simu)
        sched.addVThread(t1, 0)
        
        
        simu.run(200)
        
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()), 
                                      fmt="iaViewerRef", 
                                      showPartsList=[t1],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  

        trc = simu.tracedEvents()
        
        self.assertEqual(searchAnn(trc, 18.0, t1), "A Fired True" )
        self.assertEqual(searchAnn(trc, 38.0, t1), "B rv ok" )
        self.assertEqual(searchAnn(trc, 68.0, t1), "C rv timeout" )
        self.assertEqual(searchAnn(trc, 98.0, t1), "D Fired False rv timeout" )
        self.assertEqual(searchAnn(trc, 196.0, t1), "D Fired False rv timeout" )

        
if __name__ == "__main__":
    unittest.main()