'''
Created on 30.08.2017

@author: Klaus Popp

test lost messages
'''

from moddy import *
# Status indicator color defs
whiteOnGreen = {'boxStrokeColor':'black', 'boxFillColor':'green', 'textColor':'white'}
whiteOnRed = {'boxStrokeColor':'black', 'boxFillColor':'red', 'textColor':'white'}
whiteOnBlue = {'boxStrokeColor':'blue', 'boxFillColor':'blue', 'textColor':'white'}

class Producer(vSimpleProg):
    def __init__(self, sim):
        super().__init__(sim=sim, objName="Producer", parentObj=None)
        self.createPorts('out', ['netPort']) 

    def runVThread(self):
        self.netPort.injectLostMessageErrorBySequence(2)
        self.netPort.injectLostMessageErrorBySequence(5)
        self.netPort.injectLostMessageErrorBySequence(6)
        while True:
            self.wait(100*us)
            self.netPort.send('test', 100*us)
            self.busy(100*us, 'TX1', whiteOnBlue)
            self.netPort.send('test1', 100*us)
            self.busy(100*us, 'TX2', whiteOnRed)
            self.wait(100*us)
            self.netPort.send('Data1', 100*us)
            self.busy(100*us, 'TX3', whiteOnGreen)

class Consumer(simPart):
    def __init__(self, sim):
        super().__init__(sim=sim, objName="Consumer", parentObj=None)
        self.createPorts('in', ['netPort']) 

    def netPortRecv(self, port, msg):
        self.addAnnotation('got message ' + msg)
 
            
if __name__ == '__main__':
    simu = sim()
    simu.setDisplayTimeUnit('us')
    
    prod = Producer(simu)
    cons = Consumer(simu)

    prod.netPort.bind(cons.netPort)
    
    # let simulator run
    try:
        simu.run(stopTime=3*ms)
        
    except: raise
    finally:
        # create SVG drawing
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="5_lostMsg.html", 
                                      fmt="svgInHtml", 
                                      showPartsList=["Producer","Consumer"],
                                      excludedElementList=['allTimers'], 
                                      title="Lost Message Demo",
                                      timePerDiv = 50*us, 
                                      pixPerDiv = 30)    
