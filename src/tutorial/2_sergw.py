'''
2_sergw: A tutorial that models a serial gateway to show the use of moddy vThreads

Created on 04.02.2017

@author: Klaus Popp
'''

from moddy import *


class Gateway(simPart):
    def __init__(self, sim):
        # Initialize the parent class
        super().__init__(sim=sim, objName="GW")
        
        # Create a scheduler
        self.sched = vtSchedRtos(sim=sim, objName="sched", parentObj=self)
        
        # Create a Rx and a Tx thread
        self.rxThread = self.RxThread( sim=sim, gateway=self)
        self.txThread = self.TxThread( sim=sim, gateway=self)
        self.sched.addVThread(self.rxThread, prio=1)
        self.sched.addVThread(self.txThread, prio=2)


         
    class RxThread(vThread):
        def __init__(self, sim, gateway ):
            super().__init__(sim=sim, objName="RxThr", parentObj=gateway)
            # Create serial port for serial input (with Queuing) 
            self.createPorts('QueuingIn', ['serPort']) 
            # Create a network output port (interface to network client)
            self.createPorts('out', ['netPort']) 
            
        
        def runVThread(self):
            while True:
                # Wait until serial data available
                if self.serPort.nMsg() == 0:
                    self.wait( timeout=None, evList=[self.serPort])
                
                # Read serial data. Simulate read from HW Fifo (each message is only one char)
                # Simulate fifo depth of 8 (if more than 8 messages received, Fifo overflow)
                nChars = self.serPort.nMsg()
                
                msgStr = ''
                for i in range(nChars):
                    msgStr += self.serPort.readMsg()

                if nChars > 8:
                    self.addAnnotation('FIFO overflow!')
                    nChars = 8
                    msgStr = msgStr[:nChars]
                    
                # Simulate reading from HW Fifo takes time (20us per char, really slow CPU...)
                self.busy( nChars * 20 *us, 'RFIFO', bcWhiteOnRed)
                
                # push data to network
                self.busy( 150*us, 'TXNET', bcWhiteOnGreen)
                
                self.netPort.send( msgStr, 100*us)

            
    class TxThread(vThread):
        def __init__(self, sim, gateway ):
            super().__init__(sim=sim, objName="TxThr", parentObj=gateway)
            # Create serial port for serial output (with Queuing) 
            self.createPorts('out', ['serPort']) 
            # Create a network output input (interface to network client)
            self.createPorts('QueuingIn', ['netPort']) 
            
        
        def runVThread(self):
            while True:
                if self.netPort.nMsg() == 0:
                    self.wait( timeout=None, evList=[self.netPort])
                
                self.busy( 100*us, 'RXNET', bcWhiteOnGreen)
                
                # read one message
                msg = self.netPort.readMsg()

                self.busy( len(msg) * 20*us, 'TXFIFO', bcWhiteOnRed)
            
                # push to serial port
                for c in msg:
                    self.serPort.send( c, serFlightTime(c))
            
class Client(vSimpleProg):
    def __init__(self, sim):
        super().__init__(sim=sim, objName="Client", parentObj=None)
        self.createPorts('QueuingIO', ['netPort']) 

    def runVThread(self):
        while True:
            self.wait(1.2*ms)
            self.netPort.send('test', 100*us)
            self.busy(100*us, 'TX1', bcWhiteOnBlue)
            self.netPort.send('test1', 100*us)
            self.busy(100*us, 'TX2', bcWhiteOnRed)
            self.wait(2.3*ms)
            self.netPort.send('Data1', 100*us)
            self.busy(100*us, 'TX3', bcWhiteOnGreen)

class SerialDevice(vSimpleProg):
    def __init__(self, sim):
        super().__init__(sim=sim, objName="SerDev", parentObj=None)
        self.createPorts('QueuingIO', ['serPort']) 
        
    def runVThread(self):
        while True:
            # Generate some serial output
            self.wait(2*ms)
            
            msgStr = 'abc'
            for c in msgStr: 
                self.serPort.send(c, serFlightTime(c))
            
            self.wait(1*ms)
            
            msgStr = 'Hello-World' 
            for c in msgStr: 
                self.serPort.send(c, serFlightTime(c))
            


def serFlightTime(txString):
    ''' Compute flight time for txString (baudrate=115200) '''
    timePerChar = (1.0/115200) * 10 
    return timePerChar * len(txString)


if __name__ == '__main__':
    simu = sim()
    simu.setDisplayTimeUnit('us')
    
    client = Client(simu)
    gateway = Gateway(simu)
    serDev = SerialDevice(simu)
    
    serDev.serPort._outPort.bind( gateway.rxThread.serPort )
    gateway.txThread.serPort.bind( serDev.serPort._inPort)
    
    client.netPort._outPort.bind( gateway.txThread.netPort )
    gateway.rxThread.netPort.bind( client.netPort._inPort)
    
    serDev.serPort._outPort.setColor('blue')
    
    # let simulator run
    try:
        simu.run(stopTime=12*ms)
        
    except: raise
    finally:
        # create SVG drawing
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/2_sergw.html", 
                                      fmt="iaViewer", 
                                      showPartsList=[client, gateway.rxThread, gateway.txThread, serDev],
                                      excludedElementList=['allTimers'], 
                                      timePerDiv = 50*us, 
                                      pixPerDiv = 30,
                                      title = "Serial Gateway Demo")    
    
    # Output model structure graph
    moddyGenerateStructureGraph(simu, 'output/2_sergw_structure.svg')
        