'''
:mod:`ethUnmanagedSwitch` -- Unmanaged Ehternet Switch
======================================================

.. module:: ethUnmanagedSwitch
   :synopsis: Unmanaged Ehternet Switch
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>
'''

from moddy import simPart
from moddy.lib.net.ethernet import ethBCastAddr, ethFlightTime, ethHdrLen

class EthUnmanagedSwitch(simPart):
    
    
    def __init__(self, sim, objName, numPorts, netSpeed):
        super().__init__(sim=sim, objName=objName) 

        self._numPorts = numPorts
        self._netSpeed = netSpeed
        self._lookupTable = {}  # key=macAddr, value=NetPort

        self._netPorts = []
    
        for portNum in range(numPorts):
            self._netPorts.append(self.NetPort(self,portNum))
            
            
    def lookupMacAddr(self, macAddr):
        """
        lookup macAddr in lookupTable.
        :param str macAddr: address to lookup (e.g. '00:11:22:33:44:55')
        :return: NetPort where macAddr is known. None if not found or if it macAddr is broadcast
        """    
        if macAddr != ethBCastAddr() and macAddr in self._lookupTable:
            return self._lookupTable[macAddr]
        else:
            return None
    
    def addMacToLookupTable(self, netPort, macAddr):
        """
        Add macAddr tp lookupTable. Update if it is already in lookup Table
        :param NetPort netPort: netPort where this macAddr is attached to  
        :param str macAddr: address to addr (e.g. '00:11:22:33:44:55')
        """    
        self._lookupTable[macAddr] = netPort
            
    class NetPort():
        def __init__(self, switch, portNum):
            
            self._switch = switch
            self._netSpeed = switch._netSpeed
            
            # create network port
            self._netPort = switch.newIOPort('Port%d' % portNum, None)
            self._netPort.setMsgStartedFunc(self.netPortRecvStart)

            # create a port that simulates the cut-through delay
            self._cutThroughDelPort = switch.newIOPort('CutThroughDelPort%d' % portNum, self.cutThroughDelPortRecv)
            self._cutThroughDelPort.loopBind()
            

        def netPortRecvStart(self, inPort, pdu, outPort, flightTime):
            self._cutThroughDelPort.send( pdu, ethFlightTime(self._netSpeed, ethHdrLen()))
        
        def cutThroughDelPortRecv(self, inPort, pdu):
            dstAddr = pdu['dst']
            srcAddr = pdu['src']
            
            # Add source addr to lookupTable
            self._switch.addMacToLookupTable( self, srcAddr)
            
            # check which port has destination address
            dstPort = self._switch.lookupMacAddr(dstAddr)
            
            if srcAddr != dstAddr:
                if dstPort is None:
                    # forward to all ports (except my own)
                    for netPort in self._switch._netPorts:
                        if netPort is not self:
                            netPort.sendPdu(pdu)
                else:
                    # forward to specific port
                    dstPort.sendPdu(pdu)
                
                
        
        def sendPdu(self, pdu):
            self._netPort.send( pdu, ethFlightTime(self._netSpeed, pdu.byteLen())) 
   
        