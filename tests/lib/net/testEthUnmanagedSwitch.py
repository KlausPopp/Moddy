'''
Created on 08.04.2019

@author: klauspopp@gmx.de
'''

import unittest
from moddy import *
from moddy.lib.net.ethernet import ethBCastAddr, ethFlightTime, ethPdu
from moddy.lib.net.ethUnmanagedSwitch import EthUnmanagedSwitch
from moddy.lib.pdu import Pdu
from tests.utils import *

    

class TestEthUnmanagedSwitch1GB(unittest.TestCase):
    netSpeed = 1E9 # 1GBit/s
   
    @classmethod
    def ethPduSend( cls, port, src, dst, payload ):
        pdu = ethPdu(src, dst, ethType=0x0800, payload=payload)
        port.send( pdu, ethFlightTime(cls.netSpeed, pdu.byteLen()) )
    
    @classmethod
    def ethClient1Prog(cls, self: vThread):
        src = "00:c0:3a:00:00:01"
        while True:
            self.waitUntil(20*us)
            # client2 not yet known, switch will send message to all ports
            cls.ethPduSend(self.netPort, src, "00:c0:3a:00:00:02", Pdu( "Data", {"stream":"Hello from Client1"}, 1000 ))
            
            # send broadcast
            self.waitUntil(140*us)
            cls.ethPduSend(self.netPort, src, ethBCastAddr(), Pdu( "Data", {"stream":"Hello to all"}, 1000 ))
            
            # simulate incoming traffic on all ports
            self.waitUntil(200*us)
            cls.ethPduSend(self.netPort, src, "00:c0:3a:00:00:02", Pdu( "Data", {"stream":"Hello from Client1"}, 1000 ))

            self.wait(None)
            
    @classmethod
    def ethClient2Prog(cls, self: vThread):
        src = "00:c0:3a:00:00:02"
        while True:
            self.waitUntil(60*us)
            # client1 already known, switch will send message only to client1
            cls.ethPduSend(self.netPort, src, "00:c0:3a:00:00:01", Pdu( "Data", {"stream":"Hello from Client2"}, 1500 ))
            
            # simulate incoming traffic on all ports
            self.waitUntil(200*us)
            cls.ethPduSend(self.netPort, src, "00:c0:3a:00:00:01", Pdu( "Data", {"stream":"Hello from Client2"}, 1000 ))

            self.wait(None)
            
    @classmethod
    def ethClient3Prog(cls, self: vThread):
        src = "00:c0:3a:00:00:03"
        while True:
            self.waitUntil(100*us)
            # client2 already known, switch will send message only to client2
            cls.ethPduSend(self.netPort, src, "00:c0:3a:00:00:02", Pdu( "Data", {"stream":"Hello from Client3"}, 500 ))
            # simulate incoming traffic on all ports
            self.waitUntil(200*us)
            cls.ethPduSend(self.netPort, src, ethBCastAddr(), Pdu( "Data", {"stream":"Hello to all"}, 1500 ))
            self.wait(None)
    
    
    def testBasicSwitchFunctions(self):
       
        simu = sim()
       
        switch = EthUnmanagedSwitch( simu, "SWITCH", numPorts=3, netSpeed=self.__class__.netSpeed)         
        vSimpleProg( sim=simu, objName="Comp1", target=self.__class__.ethClient1Prog, elems={ 'QueuingIO': 'netPort' } )
        vSimpleProg( sim=simu, objName="Comp2", target=self.__class__.ethClient2Prog, elems={ 'QueuingIO': 'netPort' } )
        vSimpleProg( sim=simu, objName="Comp3", target=self.__class__.ethClient3Prog, elems={ 'QueuingIO': 'netPort' } )

        simu.smartBind([ ['SWITCH.Port0', 'Comp1.netPort'], 
                         ['SWITCH.Port1', 'Comp2.netPort'],
                         ['SWITCH.Port2', 'Comp3.netPort']])
    
        simu.setDisplayTimeUnit('us')
        # let simulator run
        simu.run(stopTime=10*ms)
        
        # Output sequence diagram
        moddyGenerateSequenceDiagram( sim=simu, 
                                      fileName="output/%s_%s.html" % (baseFileName(), funcName()), 
                                      fmt="iaViewer", 
                                      showPartsList=['Comp1', 'Comp2', 'Comp3', 'SWITCH'], 
                                      excludedElementList=['allTimers'],
                                      timePerDiv = 10*us, 
                                      pixPerDiv = 30
                                      )    
       
       
if __name__ == "__main__":
    unittest.main()