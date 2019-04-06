'''
Created on 27.03.2019

@author: Klaus Popp

test binding of multiple output ports to a single input port
'''

from moddy import *

def producerProg(self):
    self.netPort2.setColor('blue')
    while True:
        self.wait(100*us)
        self.netPort1.send('test1a', 100*us)
        self.netPort2.send('test2a', 100*us)
        self.busy(100*us, 'TX1', bcWhiteOnBlue)
        self.netPort1.send('test1b', 100*us)
        self.busy(100*us, 'TX1', bcWhiteOnBlue)
        self.netPort2.send('test2b', 100*us)

def consumerProg(self):
    while True:
        msg = self.waitForMsg( timeout=None, ports=self.netPort )
        self.addAnnotation('got message ' + msg)
 
            
if __name__ == '__main__':
    simu = sim()
    simu.setDisplayTimeUnit('us')
    
    prod = vSimpleProg( sim=simu, objName="Producer", target=producerProg, elems={ 'out': ['netPort1', 'netPort2'] } )
    cons = vSimpleProg( sim=simu, objName="Consumer", target=consumerProg, elems={ 'QueuingIn': 'netPort' } )

    # bind two output ports to same input port
    simu.smartBind( [ [ 'Producer.netPort1', 'Producer.netPort2', 'Consumer.netPort'] ] )

    # let simulator run
    try:
        simu.run(stopTime=3*ms)
        
    except: raise
    finally:
        # create sequence diagram
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/7_multiPortBinding.html", 
                                      fmt="iaViewer", 
                                      showPartsList=["Producer","Consumer"],
                                      excludedElementList=['allTimers'], 
                                      title="Multi Port Binding",
                                      timePerDiv = 50*us, 
                                      pixPerDiv = 30)    
        # Output model structure graph
        moddyGenerateStructureGraph(simu, 'output/7_multiPortBinding_structure.svg')
        