'''
Created on 09.04.2017

@author: Klaus Popp
'''

from moddy import *

class VarChanger(vSimpleProg):   
    def __init__(self, sim):
        super().__init__(sim=sim, objName="VC", parentObj=None)
        self.var1 = 0
        # self.var2 is created during execution
        
    def runVThread(self):
        while True:
            self.var1 = 1
            self.wait(2)
            
            self.var1 = 2
            self.var2 = "ABC"

            self.wait(2)
            self.var2 = "DEF"
            
            self.busy(2,'WAIT')
            self.var1 = 3
            
            self.wait(3)

if __name__ == '__main__':
    simu = sim()
    vc = VarChanger(simu)
    var1watch = vc.newVarWatcher('var1', "0x%08x")
    var2watch = vc.newVarWatcher('var2', "%s")
        
    simu.run(10)
    moddyGenerateTraceTable( simu, 'output/4_varwatch.csv')

    moddyGenerateSequenceDiagram( sim=simu, 
                                  fileName="output/4_varwatch.html", 
                                  fmt="iaViewer", 
                                  showPartsList=['VC'],
                                  showVarList=['VC.var1', 'VC.var2'],
                                  excludedElementList=['allTimers'], 
                                  timePerDiv = 0.5, 
                                  pixPerDiv = 30,
                                  title="Variable Watcher Demo")    
