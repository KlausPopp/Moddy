'''
Created on 27.12.2018

@author: klauspopp@gmx.de
'''
import unittest
import moddy
from utils import searchInMsg, searchAnn, searchTExp, \
                        searchSta, baseFileName, funcName


class TestSchedRtos(unittest.TestCase):

    def testScheduling(self):
        busyAppearance = moddy.BC_WHITE_ON_BLUE
        
        class myThread1(moddy.VThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='hiThread', parent_obj=None)
            def run_vthread(self):
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
    
        class myThread2(moddy.VThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='lowThreadA', parent_obj=None)
            def run_vthread(self):
                print("   VtLoA1")
                self.busy(50,'1',busyAppearance)
                print("   VtLoA2")
                self.wait(20,[])
                print("   VtLoA3")
                self.busy(20,'2',busyAppearance)
                print("   VtLoA4")
                self.busy(250,'3',busyAppearance)
            
        class myThread3(moddy.VThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='lowThreadB', parent_obj=None)
            def run_vthread(self):
                print("   VtLoB1")
                self.busy(50,'1',busyAppearance)
                print("   VtLoB2")
                self.wait(20,[])
                print("   VtLoB3")
                self.busy(100,'2',busyAppearance)
                print("   VtLoB4")
                self.busy(250,'3',busyAppearance)
    
        simu = moddy.Sim()
        sched= moddy.VtSchedRtos(sim=simu, obj_name="sched", parent_obj=None)
                
        t1 = myThread1(simu)
        t2 = myThread2(simu)
        t3 = myThread3(simu)
        sched.add_vthread(t1, 0)
        sched.add_vthread(t2, 1)
        sched.add_vthread(t3, 1)
        simu.run(400)
        
        moddy.moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()), 
                                      fmt="iaViewerRef", 
                                      showPartsList=[t1,t2,t3],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  

        trc = simu.tracing.traced_events()
        
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
        busyAppearance = moddy.BC_WHITE_ON_BLUE
        
        # Block myThread1 22s from running. Test to see if messages arrive when thread initially preempted
        # Was a bug in moddy <= 1.7.1
        class myBlockThread(moddy.VThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Block', parent_obj=None)

            def run_vthread(self):
                self.busy(22, "Block")
                self.wait(None)
        
        class myThread1(moddy.VThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Thread', parent_obj=None)
                self.create_ports('QueuingIn', ['inP1'])
            
            def getAllMsg(self):
                lstMsg = []
                while True:
                    try:
                        msg = self.inP1.read_msg()
                        lstMsg.append(msg)
                    except BufferError:
                        break
                
                self.annotation(lstMsg)
         
             
            def run_vthread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.busy(33, cycle, busyAppearance)
                    self.getAllMsg()
                    print(self.wait(20, [self.inP1]))
                    self.getAllMsg()


        class stimThread(moddy.VSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Stim', parent_obj=None)
                self.create_ports('out', ['toT1Port'])
                                
            def run_vthread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15,[])
                    self.toT1Port.send('hello%d' % count,5)


        simu = moddy.Sim()
                        
        t1 = myThread1(simu)
        t2 = myBlockThread(simu)
        
        sched = moddy.VtSchedRtos(sim=simu, obj_name="sched", parent_obj=None)
        sched.add_vthread(t1, 2)
        sched.add_vthread(t2, 1)
        stim = stimThread(simu)
        stim.toT1Port.bind(t1.inP1)
        
        simu.run(200)
        
        moddy.moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()),
                                      fmt="iaViewerRef", 
                                      showPartsList=[stim,t1,t2],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  
  
        trc = simu.tracing.traced_events()
        
        self.assertEqual(searchAnn(trc, 55.0, t1), "['hello1', 'hello2', 'hello3']" )
        self.assertEqual(searchAnn(trc, 65.0, t1), "['hello4']" )
        self.assertEqual(searchAnn(trc, 98.0, t1), "['hello5', 'hello6']" )
        self.assertEqual(searchAnn(trc, 110.0, t1), "['hello7']")
        self.assertEqual(searchAnn(trc, 143.0, t1), "['hello8', 'hello9']" )

    def testQueingIOPort(self):
        busyAppearance = moddy.BC_WHITE_ON_BLUE
        class myThread1(moddy.VSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Thread', parent_obj=None)
                self.create_ports('QueuingIO', ['ioP1'])
            
            def getAllMsg(self):
                lstMsg = []
                while True:
                    try:
                        msg = self.ioP1.read_msg()
                        lstMsg.append(msg)
                    except BufferError:
                        break
                
                self.annotation(lstMsg)
         
             
            def run_vthread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.busy(33, cycle, busyAppearance)
                    self.getAllMsg()
                    print(self.wait(18-cycle*2, [self.ioP1]))
                    self.getAllMsg()


        class stimThread(moddy.VSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Stim', parent_obj=None)
                self.create_ports('out', ['toT1Port'])
                                
            def run_vthread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15,[])
                    self.toT1Port.send('hello%d' % count,5)


        simu = moddy.Sim()
                        
        t1 = myThread1(simu)
        
        stim = stimThread(simu)
        stim.toT1Port.bind(t1.ioP1._in_port)
        
        simu.run(200)
        
        moddy.moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()),
                                      fmt="iaViewerRef", 
                                      showPartsList=[stim,t1],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  
  
        trc = simu.tracing.traced_events()
        
        self.assertEqual(searchAnn(trc, 33.0, t1), "['hello1']" )
        self.assertEqual(searchAnn(trc, 35.0, t1), "['hello2']" )
        self.assertEqual(searchAnn(trc, 68.0, t1), "['hello3', 'hello4']" )
        self.assertEqual(searchAnn(trc, 80.0, t1), "['hello5']" )
        self.assertEqual(searchAnn(trc, 113.0, t1), "['hello6', 'hello7']" )
        self.assertEqual(searchAnn(trc, 125.0, t1), "[]" ) # timeout
        self.assertEqual(searchAnn(trc, 158.0, t1), "['hello8', 'hello9', 'hello10']" )


    def testSamplingPort(self):
        busyAppearance = moddy.BC_WHITE_ON_BLUE
        class myThread1(moddy.VSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Thread', parent_obj=None)
                self.create_ports('SamplingIn', ['inP1'])
                
            def showMsg(self):
                msg = self.inP1.read_msg(default='No message')
                self.annotation(msg)
                
            def run_vthread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.showMsg()
                    self.busy(18,cycle, busyAppearance)
                    self.showMsg()
                    self.busy(14,cycle, busyAppearance)
                    self.wait(20,[self.inP1])


        class stimThread(moddy.VSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Stim', parent_obj=None)
                self.create_ports('out', ['toT1Port'])
                                
            def run_vthread(self):
                count=0
                while True:
                    count+=1
                    self.wait(15)
                    self.toT1Port.send('hello%d' % count,5)


        simu = moddy.Sim()
                        
        t1 = myThread1(simu)
        
        stim = stimThread(simu)
        stim.toT1Port.bind(t1.inP1)
        
        simu.run(200)
        
        moddy.moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()),
                                      fmt="iaViewerRef", 
                                      showPartsList=[stim,t1],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  
         
        trc = simu.tracing.traced_events()
        
        self.assertEqual(searchAnn(trc, 0.0, t1), "No message" )
        self.assertEqual(searchAnn(trc, 18.0, t1), "No message" )
        self.assertEqual(searchAnn(trc, 35.0, t1), "hello2" )
        self.assertEqual(searchAnn(trc, 53.0, t1), "hello3" )
        self.assertEqual(searchAnn(trc, 188.0, t1), "hello12" )

    def testVtTimer(self):
        busyAppearance = moddy.BC_WHITE_ON_BLUE
        class myThread1(moddy.VThread):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Thread', parent_obj=None)
                self.create_vt_timers(['tmr1'])
                
            def run_vthread(self):
                cycle=0
                while True:
                    cycle += 1
                    self.tmr1.start(16)
                    self.busy(18,cycle,busyAppearance)
                    self.annotation("A Fired " + str(self.tmr1.has_fired()))
                    self.tmr1.start(20)
                    rv = self.wait(100,[self.tmr1])
                    self.annotation("B rv " + rv)
                    self.tmr1.start(20)
                    rv = self.wait(30,[])
                    self.annotation("C rv " + rv)
                    self.tmr1.start(40)
                    rv = self.wait(30,[self.tmr1])
                    self.annotation("D Fired " + str(self.tmr1.has_fired()) + " rv " + rv)
                    self.tmr1.stop()

        simu = moddy.Sim()
        sched= moddy.VtSchedRtos(sim=simu, obj_name="sched", parent_obj=None)
                        
        t1 = myThread1(simu)
        sched.add_vthread(t1, 0)
        
        
        simu.run(200)
        
        moddy.moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()), 
                                      fmt="iaViewerRef", 
                                      showPartsList=[t1],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  

        trc = simu.tracing.traced_events()
        
        self.assertEqual(searchAnn(trc, 18.0, t1), "A Fired True" )
        self.assertEqual(searchAnn(trc, 38.0, t1), "B rv ok" )
        self.assertEqual(searchAnn(trc, 68.0, t1), "C rv timeout" )
        self.assertEqual(searchAnn(trc, 98.0, t1), "D Fired False rv timeout" )
        self.assertEqual(searchAnn(trc, 196.0, t1), "D Fired False rv timeout" )

        
if __name__ == "__main__":
    unittest.main()