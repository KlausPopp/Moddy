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
    SIMU = moddy.Sim()
    vc = moddy.VSimpleProg( sim=SIMU, obj_name="VC", target=varChangerProg )

    var1watch = vc.new_var_watcher('var1', "0x%08x")
    var2watch = vc.new_var_watcher('var2', "%s")
        
    SIMU.run(10)
    moddy.moddyGenerateTraceTable( SIMU, 'output/4_varwatch.csv')

    moddy.moddyGenerateSequenceDiagram( sim=SIMU, 
                                  fileName="output/4_varwatch.html", 
                                  fmt="iaViewer", 
                                  showPartsList=['VC'],
                                  showVarList=['VC.var1', 'VC.var2'],
                                  excludedElementList=['allTimers'], 
                                  timePerDiv = 0.5, 
                                  pixPerDiv = 30,
                                  title="Variable Watcher Demo")    
