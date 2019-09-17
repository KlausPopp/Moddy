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
        
        # In the 4th invocation generate a model assertion failure 
        if self.threadInvocationCount == 4:
            self.assertionFailed('4rd invocation assertion')

        # In the 5th invocation simulate an exception. This terminates the thread and the simulator
        if self.threadInvocationCount == 5:
            raise ValueError("Test what happens in case of thread exceptions")
        
        self.busy(20,'2',bcWhiteOnBlue)

        
def utilThread(self):
    count = 0
    while(True):
        self.busy(10,'1',bcWhiteOnRed)
        self.toRcPort.send(count, 1)
        count += 1


def stimProg(self):

    # @2s: initial start of rcTread 
    self.waitUntil(2)
    self.rcPort.send('start',0)
    
    # @5s: kill rcThread
    self.waitUntil(5)
    self.rcPort.send('kill',0)
    
    # @7s: restart rcThread
    self.waitUntil(7)
    self.rcPort.send('start',0)
    
    # @130s: restart rcThread, it has terminated, because it finished its main loop
    self.waitUntil(130)
    self.rcPort.send('start',0)
    
    # @180s: kill rcThread
    self.waitUntil(180)
    self.rcPort.send('kill',0)
    
    # @200s: restart rcThread, it has terminated because it has been killed
    self.waitUntil(200)
    self.rcPort.send('start',0)

    # @290s: restart rcThread, it has terminated because it finished its main loop
    self.waitUntil(290)
    self.rcPort.send('start',0)
    self.wait(70)

if __name__ == '__main__':
    simu = sim()
    simu.setDisplayTimeUnit('s')
    
    sched = vtSchedRtos(sim=simu, objName="sched", parentObj=None)
    rcThread = myRcThread(simu)
    utilThread = vThread( sim=simu, objName="utilThread", target=utilThread, elems={ 'out': 'toRcPort' } )
    sched.addVThread(rcThread, 0)
    sched.addVThread(utilThread, 1)

    stim = vSimpleProg( sim=simu, objName="Stim", target=stimProg, elems={ 'out': 'rcPort' } )

    simu.smartBind([['rcThread.threadControlPort', 'Stim.rcPort'], 
                    ['utilThread.toRcPort', 'rcThread.fromUtilPort'] ])

    # let simulator run
    try:
        simu.run(stopTime=400, stopOnAssertionFailure=False)
        
    except: raise
    finally:
        # create SVG drawing
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/6_vthreadRemoteControlled.html", 
                                      fmt="iaViewer", 
                                      showPartsList=[ "utilThread", "rcThread", "Stim"],
                                      excludedElementList=['allTimers'], 
                                      title="remote controlled vThreads Demo",
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)    
