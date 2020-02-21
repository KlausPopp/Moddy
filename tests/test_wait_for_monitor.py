'''
Created on 21.09.2019

@author: klauspopp@gmx.de
'''
import unittest
import moddy
from utils import searchAnn,  \
                         baseFileName, funcName


class TestWaitForMonitor(unittest.TestCase):

 
    def testMonitor(self):

        class myThread1(moddy.VSimpleProg):
            def __init__(self, sim ):
                super().__init__(sim=sim, obj_name='Thread', parent_obj=None)
           
             
            def runVThread(self):
                cycle = 0
                while True:
                    self.busy(30, 'DEL#%d' % cycle)
                    self.wait(10)
                    cycle += 1
                    
        class stimThread(moddy.VSimpleProg):
            def __init__(self, sim, supervisedThread ):
                super().__init__(sim=sim, obj_name='Stim', parent_obj=None)
                self.supervisedThread = supervisedThread 
            def runVThread(self):
                self.waitForMonitor(None, self.monitorFunc1)
                self.annotation('got mon1')
                self.waitForMonitor(None, self.monitorFunc3)
                self.annotation('got mon3')
                if self.waitForMonitor(10, self.monitorFunc1) == 'timeout':
                    self.annotation('tout waiting for mon1')

            def monitorFunc1(self):
                # called in the context of the simulator!
                return self.supervisedThread._state_ind == "DEL#1"
                    
            def monitorFunc3(self):
                # called in the context of the simulator!
                return self.supervisedThread._state_ind == "DEL#3"

        simu = moddy.Sim()
                        
        t1 = myThread1(simu)
        
        stim = stimThread(simu, t1)
        
        simu.run(200)
        
        moddy.moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()),
                                      fmt="iaViewerRef", 
                                      showPartsList=[stim,t1],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)  
  
        trc = simu.traced_events()
        
        self.assertEqual(searchAnn(trc, 40.0, stim), "got mon1" )
        self.assertEqual(searchAnn(trc, 120.0, stim), "got mon3" )
        self.assertEqual(searchAnn(trc, 130.0, stim), "tout waiting for mon1" )


        
if __name__ == "__main__":
    unittest.main()