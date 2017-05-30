'''
Created on 29.05.2017

@author: Klaus Popp
'''

import csv
from moddy import *
from moddy.simulator import simTraceEvent



class TargetTrace(object):
    '''
    Class to read a trace file recorded on a target.
    The file must be a csv file with the following line types:
    
    1. Comment line: Starts with //
    2. Event line: 
        CSV format, columns separated with ";"
        First 3 columns: TimeStamp;Action;PartName
        Further columns are Action-Specific
            <MSG: DestPartName;MessageContent;FlightTime
            STA: StatusIndicatorString
            ANN: AnnotationString    
    '''
    def __init__(self, sim, fileName):
        '''
        :param sim Simulator instance 
        :param string fileName file name of trace file
        '''
        self.sim = sim
        self.fileName = fileName
        
    def readFile(self):
        '''
        Read trace file
        build parts structure based on the parts specified in the imported actions
        generate trace events within the simulator object
        '''
        with open(self.fileName, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=';', quotechar='"')
            for row in reader:
                if row[0].startswith('//'):
                    pass # ignore comment lines
                else:
                    # Event line
                    #print("event line", row)
                
                    timeStamp,action,srcPartName = row[0:3]
                    timeStamp = float(timeStamp)
                    actionSpecificArgs = row[3:]
                    
                    if action == "<MSG":
                        self.msgRecvEvent(timeStamp, srcPartName, 
                                           dstPartName=actionSpecificArgs[0],
                                           messageContent=actionSpecificArgs[1],
                                           flightTime=actionSpecificArgs[2])
                    elif action == "STA":
                        self.statusEvent(timeStamp, srcPartName, 
                                           statusIndicatorText=actionSpecificArgs[0])
                          
                    elif action == "ANN":
                        self.annotationEvent(timeStamp, srcPartName, 
                                           annotation=actionSpecificArgs[0])
                    else:
                        print("*** WARNING: Unknown action line", row)
                    
    class fireEvent:
        def __init__(self, sim, port, msg, flightTime, execTime):
            self._sim = sim
            self._port = port
            self._msg = msg
            self._flightTime = flightTime       # message transmit time
            self._requestTime = execTime-flightTime      # time when application called send()
            self.execTime = execTime;                 # when message arrives at input port
        def __str__(self):
            """Create a user readable form of the event. Used by tracer"""
            return "req=%s beg=%s end=%s dur=%s msg=[%s]" % (self._sim.timeStr(self._requestTime), 
                                                                    self._sim.timeStr(self.execTime - self._flightTime),
                                                                    self._sim.timeStr(self.execTime),
                                                                    self._sim.timeStr(self._flightTime),
                                                                    self._msg.__str__())

    
    def msgRecvEvent(self, timeStamp, srcPartName, dstPartName, messageContent, flightTime):
        flightTime = float(flightTime)
        #print ("actionMessage ts=%f srcPartName=%s dstPartname=%s messageContent=%s flightTime=%f" % 
        #       (timeStamp, srcPartName, dstPartName, messageContent, flightTime))
    
        # Create parts and connections between parts (if not yet existing)
        srcPart = self.generatePart(srcPartName)
        dstPart = self.generatePart(dstPartName)
        outPort,inPort = self.partsAreConnected(srcPart, dstPart)
        if outPort is None:
            outPort,inPort = self.generateConnection(srcPart, dstPart)
        
        # Create message event
        fireEvent = self.fireEvent(self.sim, outPort, messageContent, flightTime, timeStamp)
        te = simTraceEvent(srcPart, inPort, fireEvent, "<MSG")
        self.addSimTraceEvent(te,timeStamp)
    
    def statusEvent(self, timeStamp, srcPartName, statusIndicatorText ):
        srcPart = self.generatePart(srcPartName)
        te = simTraceEvent( srcPart, srcPart, self.sim.StateIndTransVal(statusIndicatorText,{}), 'STA')
        self.addSimTraceEvent(te,timeStamp)
        
    def annotationEvent(self, timeStamp, srcPartName, annotation ):
        srcPart = self.generatePart(srcPartName)
        te = simTraceEvent( srcPart, srcPart, annotation, 'ANN') 
        self.addSimTraceEvent(te,timeStamp)

    def addSimTraceEvent(self,te,timeStamp):
        self.sim._time = timeStamp
        self.sim.addTraceEvent(te)

        
    def generatePart(self, partName):
        '''
        Lookup if partName exists in sim. If not, create it with all necessary parents
        :return part object
        '''
        nameElems = partName.split('.')
        
        # Lookup top level element
        try:
            hlPart = self.sim.findPartByName(nameElems[0])
        except ValueError:
            hlPart = StubPart(self.sim, nameElems[0], None ) # create top level object
        llPart = hlPart
        for nameElem in nameElems[1:]:
            # determine lower level part
            llPart = None
            for _llPart in hlPart._listSubParts:
                if _llPart._objName == nameElem:
                    llPart = _llPart
                    break
            if llPart is None:
                llPart = StubPart(self.sim, nameElem, hlPart )
            hlPart = llPart
        return llPart 

    def partsAreConnected(self, srcPart, dstPart):
        '''
        Check if srcPart has an output port that is connected to a dstPart input port
        :return (outPort,inPort) tuple or (None,None)
        '''
        for inPort in dstPart._listPorts:
            if inPort._typeStr == "InPort":
                if inPort._outPort is not None:
                    if inPort._outPort._parentObj == srcPart:
                        return (inPort._outPort, inPort)
        return (None,None)
        
    def generateConnection(self, srcPart, dstPart):
        '''
        Generate an output port in srcPart and an input port in dstPart and bind them
        :return (outPort,inPort) tuple 
        '''    
        outPort = srcPart.generateOutPort()
        inPort = dstPart.generateInPort()
        outPort.bind(inPort)
        return (outPort, inPort)
        
class StubPart(simPart):
    '''
    The StubPart class is instantiated for each part specified in the imported tracefile
    '''
    def __init__(self, sim, objName, parentObj ):
        super().__init__(sim, objName, parentObj)
        print("created %s" % self.hierarchyName())
        self.inPortIdx = 0
        self.outPortIdx = 0
        
    def msgRecvFunc(self,port,msg):
        pass
                    
    def generateOutPort(self):
        port = self.newOutputPort( "outPort%d" % self.outPortIdx)
        print("created %s" % port.hierarchyName())
        self.outPortIdx += 1
        return port
                    
    def generateInPort(self):
        port = self.newInputPort("inPort%d" % self.inPortIdx, self.msgRecvFunc)
        print("created %s" % port.hierarchyName())
        self.inPortIdx += 1
        return port
    
    
if __name__ == '__main__':
    simu = sim()
    targetTrace = TargetTrace(simu,'moddyExample.trc')
    targetTrace.readFile()
    moddyGenerateStructureGraph(simu, "targetTrcImport.svg")
    
    moddyGenerateSequenceDiagram( sim=simu, 
                              fileName="targetTrcImportSd.html", 
                              fmt="svgInHtml", 
                              showPartsList=['Node1.CP.Api', 'Node1.CP.Srv', 'Node1.IOP.rcv', 'Node1.IOP.Vot', 
                                             'Node2.IOP.Vot', 'Node2.IOP.rcv', 'Node2.CP.Srv', 'Node2.CP.Api'],
                              timePerDiv = 0.5, 
                              pixPerDiv = 30)    

    