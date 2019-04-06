'''
Created on 30.08.2017

@author: Klaus Popp

test lost messages
'''

from moddy import *

def producerProg(self):
    self.netPort.injectLostMessageErrorBySequence(2)
    self.netPort.injectLostMessageErrorBySequence(5)
    self.netPort.injectLostMessageErrorBySequence(6)
    while True:
        self.wait(100*us)
        self.netPort.send('test', 100*us)
        self.busy(100*us, 'TX1', bcWhiteOnBlue)
        self.netPort.send('test1', 100*us)
        self.busy(100*us, 'TX2', bcWhiteOnRed)
        self.wait(100*us)
        self.netPort.send('Data1', 100*us)
        self.busy(100*us, 'TX3', bcWhiteOnGreen)

class Consumer(simPart):
    def __init__(self, sim):
        super().__init__(sim=sim, objName="Consumer", parentObj=None)
        self.createPorts('in', ['netPort']) 

    def netPortRecv(self, port, msg):
        self.addAnnotation('got message ' + msg)
 
            
if __name__ == '__main__':
    simu = sim()
    simu.setDisplayTimeUnit('us')
    
    prod = vSimpleProg( sim=simu, objName="Producer", target=producerProg, elems={ 'out': 'netPort' } )
    cons = Consumer( simu )

    prod.netPort.bind(cons.netPort)
    
    # let simulator run
    try:
        simu.run(stopTime=3*ms)
        
    except: raise
    finally:
        # create SVG drawing
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/5_lostMsg.html", 
                                      fmt="iaViewer", 
                                      showPartsList=["Producer","Consumer"],
                                      excludedElementList=['allTimers'], 
                                      title="Lost Message Demo",
                                      timePerDiv = 50*us, 
                                      pixPerDiv = 30)    

        # Output trace table
        moddyGenerateTraceTable(simu, 'output/5_lostMsg.csv', timeUnit="us" )
        