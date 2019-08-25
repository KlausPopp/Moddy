'''
Created on 27.04.2018

@author: klaus.popp@men.de
'''

def EmptyPdu():
    ''' return a empty PDU '''
    return Pdu({},0)

class Pdu(dict):
    '''
    Representation of a protocol data unit
    
    The Pdu is represented as a dictionary, containing the modelled protocol pdu fields. 
    The additional member '_bytelen' represents the real byte length of all pdu fields
    dict={ 'm1': m1value, 'm2': m2value }, _bytelen=10 
    
    Pdus can be nested. 

     
    :param str pduType: A string describing the type of the Pdu (without 'Pdu'), e.g. 'Eth'
    :param dict mapping: dictionary with member:value pairs, value can be a sub-Pdu
    :param byteLen: top level byte Len - subPdus len will be added
    '''


    def __init__(self, pduType, mapping, byteLen):
        if type(mapping) is Pdu:
            raise ValueError("Pdu cannot be initialized with mapping of type Pdu")

        self.pduType = pduType
        dict.__init__( self, mapping)
        
        # set top level bitLen
        self._byteLen = byteLen
    
    @classmethod
    def isPdu(cls, obj):
        return issubclass(obj.__class__, cls )
        
        
    def byteLen(self):
        byteLen = self._byteLen
        for value in self.values():
            if Pdu.isPdu(value):
                byteLen += value.byteLen()
        return byteLen
    
        
    def fillUp(self, nBytes):
        '''
        Fill top level PDU up, so it has a byteLen of nBytes
        if PDU already larger, raise Attribute error
        '''   
        if self.byteLen() > nBytes: 
            raise AttributeError('Pdu is longer than fillup value %d/%d' % 
                                 (self.byteLen(), nBytes))
        self._byteLen = nBytes - self.byteLen() + self._byteLen
        
    def __repr__(self):
        s = "%sPdu(%d)" % (self.pduType, self.byteLen())
        
        for key, value in self.items():
            if s != "": s += ' '
            if Pdu.isPdu(value):
                s += key + "=" + "%sPdu(%d)" % (value.pduType, value.byteLen())
            else:                    
                s += key + "=" + value.__str__()
                
        return s        

    def dump(self):
        '''
        Return a string as __repr()__, but also dump sub-pdus in separated, intended lines, e.g.:

            IpPdu(1220) ihl=14 flags=0 src=192.1.1.2 dst=192.1.1.8 payld=RawPdu(1000) payld2=RawPdu(200)
               payld:RawPdu(1000) raw=IPPAYLOAD
               payld2:RawPdu(200) raw=AnotherPayld
        '''
        return self._dump("", self, 0)
    
    def _dump(self, key, value, level):
        indentFmt = "%" + ("%d" % (3*level)) + "s"
        indent = indentFmt % ""
        s = indent + ("" if key == "" else key + ":") + value.__repr__() + "\n"
        for key,value in value.items():
            if Pdu.isPdu(value):
                s += self._dump(key, value, level+1)
        return s

    def splitToFragments(self, pduType, maxFragByteLen ):
        '''
        Split the Pdu into fragments and return list of fragments
        Each fragment is represented as a Pdu 
        
            Pdu( "<orgtype>Frag", { 'fr': (<offset of fragment>,<len of fragment>), 'org'=[<original Pdu>], fraglen )

        Note: the 'org' member is transferred with every fragment. It is enclosed in a list, so that it
        is not included in the fragment's byte length.
        
        The PduDefragmenter class can be used to defragment the fragments
        
        :param string pduType: pduType to set for fragments
        :param int maxFragByteLen: maximum bytes per fragment
        :return list: list of fragments
        '''
        frags = []
        fragOff = 0
        orgPduLen = self.byteLen()
        
        while True:
            fragLen = orgPduLen - fragOff
            if fragLen > maxFragByteLen:
                fragLen = maxFragByteLen
                
            frag = Pdu( pduType, { 'fr': (fragOff,fragLen), 'org' : [self]}, fragLen)
            frags.append(frag)
            
            fragOff += fragLen
            if fragOff >= orgPduLen:
                break
            
        return frags
    
class PduDefragmenter(object):
    def __init__(self):
        self.pdu = None
        self.frags = [] # list with tuples (off,len) of received fragments
        
    def addFragment(self, frag):
        '''
        Add a received fragment 
        '''
        self.frags.append(frag['fr'])
        self.pdu = frag['org'][0]
        
    def thePdu(self):
        if self.defragCompleteInfo() is None:
            return self.pdu
        else:
            return None
    
    def defragCompleteInfo(self):
        '''
        Check if defragmentation complete. 
        :return string: None if complete or string with info with first missing frag
        '''
        off = 0
        
        while True:
            frag = self.hasOffs(off)
            if frag is None:
                return "missing frag at offs %d" % off
            off += frag[1]
            
            if off >= self.pdu.byteLen():
                break
        return None
    
        
    def hasOffs(self, off):
        for frag in self.frags:
            if frag[0] == off:
                return frag 
        return None