'''
Created on 17.12.2018

@author: klauspopp@gmx.de

Demonstrate remote controlable vThreads 

NOTE: It is intended that this demo reports
1) an assertion 
2) an exception 
To demonstrate what happens if threads throw exceptions or model assertions
'''
from moddy import *


class myRcThread(vThread):
    def __init__(self, sim ):
        super().__init__(sim=sim, objName='rcThread', parentObj=None, remoteControlled=True)
        self.createPorts('QueingIn', ["fromUtilPort"])
        self.threadInvocationCount = 0
        
    def runVThread(self):
        # variables stored in the simPart object (self) are persistant through thread restarts 
        self.threadInvocationCount += 1 

        self.addAnnotation('invocation %d' % self.threadInvocationCount)
        self.busy(20,'1',bcWhiteOnGreen)
        
        # This shows that arriving messages are lost while the thread is dead 
        for _ in range(20):
            self.wait(2)
            while self.fromUtilPort.nMsg() > 0:
                self.addAnnotation('Got %s' % self.fromUtilPort.readMsg())
        
        # In the 3th invocation generate a model assertion failure 
        if self.threadInvocationCount == 3:
            self.assertionFailed('3rd invocation assertion')

        # In the 4rd invocation simulate an exception. This terminates the thread and the simulator
        if self.threadInvocationCount == 4:
            raise ValueError("Test what happens in case of thread exceptions")
        
        self.busy(20,'2',bcWhiteOnBlue)

class myUtilThread(vThread):
    def __init__(self, sim ):
        super().__init__(sim=sim, objName='utilThread', parentObj=None)
        self.createPorts('out', ["toRcPort"])
        
    def runVThread(self):
        count = 0
        while(True):
            self.busy(10,'1',bcWhiteOnRed)
            self.toRcPort.send(count, 1)
            count += 1


class Stim(vSimpleProg):
    def __init__(self, sim ):
        super().__init__(sim=sim, objName='Stim', parentObj=None)
        self.createPorts('out', ["rcPort"])
        
    def runVThread(self):
        self.wait(2)

        # @2s: initial start of rcTread 
        self.rcPort.send('start',0)
        self.wait(128)
        
        # @130s: restart rcThread, it has terminated, because it finished its main loop
        self.rcPort.send('start',0)
        self.wait(50)
        
        # @180s: kill rcThread
        self.rcPort.send('kill',0)
        self.wait(20)
        
        # @200s: restart rcThread, it has terminated because it has been killed
        self.rcPort.send('start',0)
        self.wait(90)

        # @290s: restart rcThread, it has terminated because it finished its main loop
        self.rcPort.send('start',0)
        self.wait(70)

if __name__ == '__main__':
    simu = sim()
    simu.setDisplayTimeUnit('s')
    
    sched= vtSchedRtos(sim=simu, objName="sched", parentObj=None)
    rcThread = myRcThread(simu)
    utilThread = myUtilThread(simu)
    sched.addVThread(rcThread, 0)
    sched.addVThread(utilThread, 1)

    stim = Stim(simu)
    stim.rcPort.bind(rcThread.threadControlPort)

    utilThread.toRcPort.bind(rcThread.fromUtilPort)

    # let simulator run
    try:
        simu.run(stopTime=400, stopOnAssertionFailure=False)
        
    except: raise
    finally:
        # create SVG drawing
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/6_vthreadRemoteControlled.html", 
                                      fmt="iaViewerRef", 
                                      showPartsList=[ "utilThread", "rcThread", "Stim"],
                                      excludedElementList=['allTimers'], 
                                      title="remote controlled vThreads Demo",
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)    
