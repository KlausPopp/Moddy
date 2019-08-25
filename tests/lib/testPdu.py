'''
Created on 30.04.2019

@author: klauspopp@gmx.de
'''

import unittest
from moddy.lib.pdu import Pdu, PduDefragmenter
from tests.utils import *

    

class TestPdu(unittest.TestCase):
    
    def testBasic(self):
        # basic pdu
        pdu1 = Pdu( 'Test1', { 'm1': 1, 'm2': 2 }, 50 )
        self.assertEqual( pdu1.byteLen(), 50)
        
        # nested pdu
        pdu2 = Pdu( 'Test2', { 's1': pdu1, 'v2': 2 }, 8 )
        self.assertEqual( pdu2.byteLen(), 58)
        print(pdu2)
        print(pdu2.dump())
   
    
    def testReplace(self):
        ipPdu = Pdu( 'Ip', { 'ihl' : 14, 'flags': 0x0000, 'src': '192.1.1.2', 'dst': '192.1.1.8', 
                        'payld': Pdu( 'Raw', {'raw':"IPPAYLOAD"},1000) }, 20 )
        self.assertEqual( ipPdu.byteLen(), 1020)
        self.assertEqual( "IpPdu(1020) ihl=14 flags=0 src=192.1.1.2 dst=192.1.1.8 payld=RawPdu(1000)", ipPdu.__repr__())

        # replace payload
        udpPay = Pdu('Udp', {'raw': 'UDPPAYLOAD'}, 250)
        ipPdu['payld'] = Pdu( 'Udp', {'src':'1.2.3.4', 'udpPay':udpPay},25)
        self.assertEqual( ipPdu.byteLen(), 295)

        # replace UDP payload
        appPay = Pdu('App', {'raw': 'AppPayload'}, 200)
        ipPdu['payld']['udpPay'] = appPay
        print(ipPdu.dump())
        self.assertEqual( ipPdu.byteLen(), 245)

    def testFillUp(self):
        ipPdu = Pdu( 'Ip', { 'ihl' : 14, 'flags': 0x0000, 'src': '192.1.1.2', 'dst': '192.1.1.8', 
                        'payld': Pdu( 'Raw', {'raw':"IPPAYLOAD"},1000) }, 20 )
        ipPdu.fillUp(1500)
        self.assertEqual( ipPdu.byteLen(), 1500)
        with self.assertRaises(AttributeError):
            ipPdu.fillUp(1000)
        
    def testAppend(self):
        ipPdu = Pdu( 'Ip', { 'ihl' : 14, 'flags': 0x0000, 'src': '192.1.1.2', 'dst': '192.1.1.8', 
                        'payld': Pdu( 'Raw', {'raw':"IPPAYLOAD"},1000) }, 20 )
        ipPdu['payld2'] = Pdu( 'Raw', {'raw':"AnotherPayld"},200)
        print(ipPdu.dump())
        self.assertEqual( ipPdu.byteLen(), 1220)
        
     
    def testSplitToFragments(self):
        pdu = Pdu('App', {'raw': 'AppPayload'}, 2000)
        
        frags = pdu.splitToFragments('frag', 550)
        self.assertEqual( frags[0].byteLen(), 550)
        self.assertEqual( frags[3].byteLen(), 350)
        
        defrag = PduDefragmenter()
        self.assertEqual( defrag.thePdu(), None)
        defrag.addFragment(frags[3])
        print(defrag.defragCompleteInfo()) 
        self.assertEqual( defrag.thePdu(), None)
        defrag.addFragment(frags[0])
        defrag.addFragment(frags[1])
        print(defrag.defragCompleteInfo()) 
        defrag.addFragment(frags[2])
        dPdu = defrag.thePdu()        
        self.assertNotEqual( dPdu, None)
        self.assertEqual( dPdu.byteLen(), 2000)
        
         
         
if __name__ == "__main__":
    unittest.main()