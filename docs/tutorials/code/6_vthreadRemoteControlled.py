'''
Created on 17.12.2018

@author: klauspopp@gmx.de

Demonstrate remote controlable vThreads 

NOTE: It is intended that this demo reports
1) an assertion 
2) an exception 
To demonstrate what happens if threads throw exceptions or model assertions
'''
import moddy


class myRcThread(moddy.VThread):
    def __init__(self, sim ):
        super().__init__(sim=sim, obj_name='rcThread', parent_obj=None, remote_controlled=True)
        self.create_ports('QueingIn', ["fromUtilPort"])
        self.threadInvocationCount = 0
        
    def run_vthread(self):
        # variables stored in the simPart object (self) are persistant through thread restarts 
        self.threadInvocationCount += 1 

        self.annotation('invocation %d' % self.threadInvocationCount)
        self.busy(20,'1', moddy.BC_WHITE_ON_GREEN)
        
        # This shows that arriving messages are lost while the thread is dead 
        for _ in range(20):
            self.wait(2)
            while self.fromUtilPort.n_msg() > 0:
                self.annotation('Got %s' % self.fromUtilPort.read_msg())
        
        # In the 4th invocation generate a model assertion failure 
        if self.threadInvocationCount == 4:
            self.assertion_failed('4rd invocation assertion')

        # In the 5th invocation simulate an exception. This terminates the thread and the simulator
        if self.threadInvocationCount == 5:
            raise ValueError("Test what happens in case of thread exceptions")
        
        self.busy(20,'2',moddy.BC_WHITE_ON_BLUE)

        
def utilThread(self):
    count = 0
    while(True):
        self.busy(10,'1',moddy.BC_WHITE_ON_RED)
        self.toRcPort.send(count, 1)
        count += 1


def stimProg(self):

    # @2s: initial start of rcTread 
    self.wait_until(2)
    self.rcPort.send('start',0)
    
    # @5s: kill rcThread
    self.wait_until(5)
    self.rcPort.send('kill',0)
    
    # @7s: restart rcThread
    self.wait_until(7)
    self.rcPort.send('start',0)
    
    # @130s: restart rcThread, it has terminated, because it finished its main loop
    self.wait_until(130)
    self.rcPort.send('start',0)
    
    # @180s: kill rcThread
    self.wait_until(180)
    self.rcPort.send('kill',0)
    
    # @200s: restart rcThread, it has terminated because it has been killed
    self.wait_until(200)
    self.rcPort.send('start',0)

    # @290s: restart rcThread, it has terminated because it finished its main loop
    self.wait_until(290)
    self.rcPort.send('start',0)
    self.wait(70)

if __name__ == '__main__':
    simu = moddy.Sim()
    simu.tracing.set_display_time_unit('s')
    
    sched = moddy.VtSchedRtos(sim=simu, obj_name="sched", parent_obj=None)
    rcThread = myRcThread(simu)
    utilThread = moddy.VThread( sim=simu, obj_name="utilThread", target=utilThread, elems={ 'out': 'toRcPort' } )
    sched.add_vthread(rcThread, 0)
    sched.add_vthread(utilThread, 1)

    stim = moddy.VSimpleProg( sim=simu, obj_name="Stim", target=stimProg, elems={ 'out': 'rcPort' } )

    simu.smart_bind([['rcThread._thread_control_port', 'Stim.rcPort'], 
                    ['utilThread.toRcPort', 'rcThread.fromUtilPort'] ])

    # let simulator run
    try:
        simu.run(stop_time=400, stop_on_assertion_failure=False)
        
    except: raise
    finally:
        # create SVG drawing
        moddy.moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/6_vthreadRemoteControlled.html", 
                                      fmt="iaViewer", 
                                      showPartsList=[ "utilThread", "rcThread", "Stim"],
                                      excludedElementList=['allTimers'], 
                                      title="remote controlled vThreads Demo",
                                      timePerDiv = 10, 
                                      pixPerDiv = 30)    
