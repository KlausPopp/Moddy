'''
@author: klauspopp@gmx.de
'''

import moddy

def varChangerProg(self):
    self.var1 = 0
    # self.var2 is created during execution
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
    simu = moddy.Sim()
    vc = moddy.VSimpleProg( sim=simu, obj_name="VC", target=varChangerProg )

    var1watch = vc.new_var_watcher('var1', "0x%08x")
    var2watch = vc.new_var_watcher('var2', "%s")
        
    simu.run(10)
    moddy.moddyGenerateTraceTable( simu, 'output/4_varwatch.csv')

    moddy.moddyGenerateSequenceDiagram( sim=simu, 
                                  fileName="output/4_varwatch.html", 
                                  fmt="iaViewer", 
                                  showPartsList=['VC'],
                                  showVarList=['VC.var1', 'VC.var2'],
                                  excludedElementList=['allTimers'], 
                                  timePerDiv = 0.5, 
                                  pixPerDiv = 30,
                                  title="Variable Watcher Demo")    
