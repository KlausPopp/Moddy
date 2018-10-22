'''
Created on 15.09.2018

@author: klauspopp@gmx.de
'''

from moddy import *

class Test1(vSimpleProg):   
    def __init__(self, sim):
        super().__init__(sim=sim, objName="T1", parentObj=None)
        
    def runVThread(self):
        while True:
            self.wait(2)
            self._sim.assertionFailed( self, 'Local Assertion failed')
            self.wait(1)
            self._sim.assertionFailed(None, 'Global Assertion failed')
            self.wait(None)


if __name__ == '__main__':
    simu = sim()
    t1 = Test1(simu)
    
    simu.run(10, stopOnAssertionFailure=True)
    moddyGenerateTraceTable( simu, 'output/mon.csv')

    moddyGenerateSequenceDiagram( sim=simu, 
                                  fileName="output/mon.html", 
                                  fmt="svgInHtml", 
                                  showPartsList=['T1'],
                                  excludedElementList=['allTimers'], 
                                  timePerDiv = 0.5, 
                                  pixPerDiv = 30)    

