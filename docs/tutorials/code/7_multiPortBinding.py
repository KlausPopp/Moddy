'''
Created on 27.03.2019

@author: Klaus Popp

test binding of multiple output ports to a single input port
'''

import moddy
from moddy import MS, US

def producerProg(self):
    self.netPort2.set_color('blue')
    while True:
        self.wait(100*US)
        self.netPort1.send('test1a', 100*US)
        self.netPort2.send('test2a', 100*US)
        self.busy(100*US, 'TX1', moddy.BC_WHITE_ON_BLUE)
        self.netPort1.send('test1b', 100*US)
        self.busy(100*US, 'TX1', moddy.BC_WHITE_ON_BLUE)
        self.netPort2.send('test2b', 100*US)

def consumerProg(self):
    while True:
        msg = self.waitForMsg( timeout=None, ports=self.netPort )
        self.annotation('got message ' + msg)
 
            
if __name__ == '__main__':
    SIMU = moddy.Sim()
    SIMU.tracing.set_display_time_unit('us')
    
    prod = moddy.VSimpleProg( sim=SIMU, obj_name="Producer", target=producerProg, elems={ 'out': ['netPort1', 'netPort2'] } )
    cons = moddy.VSimpleProg( sim=SIMU, obj_name="Consumer", target=consumerProg, elems={ 'QueuingIn': 'netPort' } )

    # bind two output ports to same input port
    SIMU.smart_bind( [ [ 'Producer.netPort1', 'Producer.netPort2', 'Consumer.netPort'] ] )

    # let simulator run
    try:
        SIMU.run(stop_time=3*MS)
        
    except: raise
    finally:
        # create sequence diagram
        moddy.moddyGenerateSequenceDiagram( sim=SIMU, 
                                      fileName="output/7_multiPortBinding.html", 
                                      fmt="iaViewer", 
                                      showPartsList=["Producer","Consumer"],
                                      excludedElementList=['allTimers'], 
                                      title="Multi Port Binding",
                                      timePerDiv = 50*US, 
                                      pixPerDiv = 30)    
        # Output model structure graph
        moddy.moddyGenerateStructureGraph(SIMU, 'output/7_multiPortBinding_structure.svg')
        