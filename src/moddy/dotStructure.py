'''
:mod:`dotStructure` -- Generate a graph of the model structure
=======================================================================

.. module:: dotStructure
   :synopsis: Generate a graph of the model structure
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
from moddy.simulator import sim, simPart
from moddy.utils import moddyCreateDirsAndOpenOutputFile

import subprocess
import os


def moddyGenerateStructureGraph( sim, fileName, keepGvFile=False ):
    ''' 
    Generate a graph of the model structure using the GraphViz dot tool
    
    :param sim sim: Simulator instance
    :param fileName: the relative filename including '.svg'
    :param keepGvFile: if True, don't delete graphviz input file
    '''
    ds = DotStructure(sim.topLevelParts(), sim.outputPorts())
    ds.dotGen(fileName, keepGvFile)

def space(indent):
    istr = "%" + str(3*indent) + "s"
    return istr % ""

def moddyNameToDotName(hierarchyName):
    s = hierarchyName.replace( ".", "__" )
    s = s.replace("-","_")
    return s

def subgraphName( partHierarchyName ):    
    return "cluster_" + moddyNameToDotName(partHierarchyName)

def portOrIoPortHierarchyName(port):
    ''' return port name or if port is part of IOPort, the IOPorts Name'''
    if port._ioPort is not None:
        return port._ioPort.hierarchyName()
    else:
        return port.hierarchyName()
    
def portOrIoPortObjName(port):
    ''' return port name or if port is part of IOPort, the IOPorts Name'''
    if port._ioPort is not None:
        return port._ioPort.objName()
    else:
        return port.objName()

def p2pPortMsgTypes(port1,port2):
    ''' join the message types of the two ports '''
    msgTypes = port1.learnedMsgTypes() + port2.learnedMsgTypes()
    l = []
    for msgType in msgTypes:
        if not msgType in l:
            l.append(msgType)
    return portMsgTypesToLabel(l) 

def portMsgTypesToLabel(msgTypes):
    s = ""
    for msgType in msgTypes:
        if s != "": s += ", "
        s += msgType
    return s    
 
class DotStructure(object):
    '''
    Display the model structure via the DOT language (Graphviz)
    Parts are vizualized as subgraphs
    Ports are vizualized as nodes
    Parts that have no ports will be invisible
    '''
    def __init__(self, topLevelParts, outputPorts):
        '''
        <topLevelParts> must be the list of top level parts in the model
        <outputPorts> must a list of all output ports in the model

        '''
        self._topLevelParts = topLevelParts
        self._outputPorts = outputPorts
        self._listSchedulers = []
        
    def showStructure(self):
        for part in self._topLevelParts:
            self.showPart(part, 0)
            
        print("=== bindings ===")
        ignInPorts = []
        ignOutPorts = []
        
        for port in self._outputPorts:
            if port not in ignOutPorts:
                if port._ioPort is not None:
                    # test if IOPort 
                    peer = port._ioPort.peerPort()
                    if peer is not None:
                        # Has a peer port, make bidirectional connection
                        print("C %s -- %s" %(port._ioPort.hierarchyName(), peer.hierarchyName()))
                        # These ports are already connected, ignore them in the rest of the scan
                        ignOutPorts.append(port)
                        ignOutPorts.append(peer._outPort)
                        ignInPorts.append(port._ioPort._inPort)
                        ignInPorts.append(peer._inPort)
                    
                s = ""
                for inPort in port._listInPorts:
                    if not inPort in ignInPorts: 
                        s += portOrIoPortHierarchyName(inPort) + ";" 
                if s != "": print("A %s -> %s" %(portOrIoPortHierarchyName(port), s))
                    
    def showPart(self, part, level):
        lstr = "%" + str(3*level) + "s%s"
        print(lstr % ("", part._objName))
        for port in part._listPorts:
            print(lstr % ("", " P:" + port._objName))
        
        for subPart in part._listSubParts:
            self.showPart(subPart, level+1)
        
    def partStructureGen(self, part, level):
        lines = []
        
        if part._typeStr == "scheduler":
            # show schedulers as an ellipse-node, and without subparts
            lines.append( [level, '%s [label=%s shape=ellipse];' % 
                           (moddyNameToDotName(part.hierarchyName()), moddyNameToDotName(part.objName()))])
            self._listSchedulers.append(part)
            
        else:
            # normal part is shown as a subgraph
            lines.append( [level, 'subgraph %s {' % subgraphName(part.hierarchyName())])
            lines.append( [level+1, 'label=<<B>%s</B>>' % part.objName()] )
            
            # now the ports
            listPorts = part._listPorts
            if len(listPorts) > 0:
                for port in listPorts:
                    lines.append( [level+1, '%s [label=%s];' % 
                                   (moddyNameToDotName(port.hierarchyName()), moddyNameToDotName(port.objName()))  ])
                
                    
            # now the subparts
            for subPart in part._listSubParts:
                lines += self.partStructureGen(subPart, level+1)
    
            lines.append( [level, '}' ])
        
        return lines
            
    def bindingsGen(self, level):
        lines = []
        ignInPorts = []
        ignOutPorts = []
        
        for port in self._outputPorts:
            if port not in ignOutPorts:
                if port._ioPort is not None:
                    # test if IOPort 
                    peer = port._ioPort.peerPort()
                    if peer is not None:
                        # Has a peer port, make bidirectional connection
                        lines.append( [level, '%s -> %s  [dir=none penwidth=3 label="%s"]' % ( #[constraint=false]
                              moddyNameToDotName(portOrIoPortHierarchyName(port)),
                              moddyNameToDotName(peer.hierarchyName()),
                              p2pPortMsgTypes(port._ioPort._outPort, peer._outPort) 
                            )] )

                        # These ports are already connected, ignore them in the rest of the scan
                        ignOutPorts.append(port)
                        ignOutPorts.append(peer._outPort)
                        ignInPorts.append(port._ioPort._inPort)
                        ignInPorts.append(peer._inPort)
                    
                for inPort in port._listInPorts:
                    if not inPort in ignInPorts:
                        lines.append( [level, '%s -> %s [label="%s"]' % ( #[constraint=false]
                              moddyNameToDotName(portOrIoPortHierarchyName(port)),
                              moddyNameToDotName(portOrIoPortHierarchyName(inPort)),
                              portMsgTypesToLabel(port.learnedMsgTypes()) ) ] )
                         
         
        return lines
    
    def schedulerRelationsGen(self, level):
        lines = []
        for sched in self._listSchedulers:
            for thread in sched._listVThreads:
                # Dot allows only edges between nodes, so take the first port of that part
                # if the part has no port, issue warning
                if len(thread._listPorts) > 0:
                    if thread != sched._parentObj:
                        firstPort = thread._listPorts[0]
    
                        prio = thread._scPrio
                        destNode = moddyNameToDotName(firstPort.hierarchyName())
    
                        lines.append( [level, 
                                       '%s -> %s [lhead=%s label="%s" color=lightblue fontsize=8 fontcolor=lightblue ]' % 
                                       ( moddyNameToDotName(sched.hierarchyName()),
                                         destNode,
                                         "cluster_" + moddyNameToDotName(thread.hierarchyName()),
                                         prio ) ] )
                else:
                    print("WARNING: Thread %s has no ports. Scheduler connection cannot be shown in structure" % 
                          thread.hierarchyName())
        return lines
        
    def dotGen(self, fileName, keepGvFile):
        level = 0
        lines=[]
        lines.append( [level, 'digraph G {'] )
        lines.append( [level+1, 'rankdir=LR;'] )
        lines.append( [level+1, 'compound=true;'] )
        lines.append( [level+1, 'graph [fontname = "helvetica" fontsize=10 fontnodesep=0.1];'] )
        lines.append( [level+1, 'node [fontname = "helvetica" fontsize=10 shape=box color=lightblue height=.1];'] )
        lines.append( [level+1, 'edge [fontname = "helvetica" color=red fontsize=8 fontcolor=red];'] )

        # Structure
        for part in self._topLevelParts:
            lines += self.partStructureGen(part, level+1)
        
        # Bindings
        lines += self.bindingsGen(level+1)
        
        # Scheduler relations
        lines += self.schedulerRelationsGen(level+1)
        
        # finish
        lines.append( [level, '}' ])
        
        # Output the DOT file as filename.dot e.g. test.svg.gv
        dotFile = "%s.gv" % fileName
        #print("fileName=%s" % dotFile )
        f = moddyCreateDirsAndOpenOutputFile(dotFile)
        for line in lines:
            f.write("%s%s\n" % (space(line[0]), line[1]))
        f.close()
        subprocess.check_call(['dot', '-Tsvg', dotFile, '-o%s' % fileName])
        print("Saved structure graph to %s"  % fileName)
        if not keepGvFile:
            os.unlink(dotFile)

        
#
# Test Code
#    
if __name__ == '__main__':
    from moddy.vtSchedRtos import vtSchedRtos
    from moddy.vthread import vThread

    
    class Cpu(simPart):
        def __init__(self, sim, objName, parentObj = None):
            super().__init__(sim, objName, parentObj)
            self.sched = vtSchedRtos(sim, "schedCpu", self)
            self.app1 = App(sim,"App1", self)
            self.app2 = App(sim,"App2", self)
            
            self.sched.addVThread(self.app1, 1)
            self.sched.addVThread(self.app2, 2)
            
    class App(vThread):
        def __init__(self, sim, objName, parentObj = None):
            super().__init__(sim, objName, parentObj )
    
            self.createPorts('SamplingIO', ['ecmPort'])

        def runVThread(self):
            while True:
                pass
        
            
    class EcMaster(simPart):
        
        def __init__(self, sim, objName, parentObj = None):
            super().__init__(sim, objName, parentObj)
    
            self.createPorts('io', ['appPort','ecPort'])
            
    
        def appPortRecv(self, port, msg):
            pass    
        def ecPortRecv(self, port, msg):
            pass    
    

    class EcDevice(simPart):
        
        def __init__(self, sim, objName, parentObj = None):
            super().__init__(sim, objName, parentObj)
    
            self.createPorts('io', ['ecPort','ucPort'])
            
            self.uc = self.EcUc(sim, self)
            self.fpga = self.EcFpga(sim, self)
            self.ucPort.bind(self.uc.escPort)
            self.uc.fpgaPort.bind(self.fpga.ucPort)
    
        def ecPortRecv(self, port, msg):
            pass    
    
        def ucPortRecv(self, port, msg):
            pass
    
        class EcUc(simPart):
            
            def __init__(self, sim, parentObj):
                super().__init__(sim, "uC", parentObj)
                self.createPorts('in', ['sensPort'])
                self.createPorts('io', ['escPort', 'fpgaPort'])

                
            def escPortRecv(self, port, msg):
                pass
                
            def fpgaPortRecv(self, port, msg):
                pass
                
            def sensPortRecv(self, port, msg):
                pass

        class EcFpga(simPart):
            
            def __init__(self, sim, parentObj):
                super().__init__(sim, "FPGA", parentObj)
                self.createPorts('io', ['ucPort'])
                
            def ucPortRecv(self, port, msg):
                pass

    class Sensor(simPart):
        
        def __init__(self, sim, objName, parentObj = None):
            super().__init__(sim, objName, parentObj)
    
            self.createPorts('out', ['outPort'])
            self.createPorts('in', ['pwrPort'])
            
        def pwrPortRecv(self, port, msg):
                pass
    
   
    simu = sim()
    cpu = Cpu(simu,"CPU")
    ecm = EcMaster(simu,"ECM")
    ecDev1 = EcDevice(simu,"DEV1")
    ecDev2 = EcDevice(simu,"DEV2")
    sensor = Sensor(simu,"SENSOR")
    cpu.app1.ecmPort.bind(ecm.appPort)
    ecm.ecPort._outPort.bind(ecDev1.ecPort._inPort)
    ecDev1.ecPort._outPort.bind(ecDev2.ecPort._inPort)
    ecDev2.ecPort._outPort.bind(ecm.ecPort._inPort)
    sensor.outPort.bind(ecDev1.uc.sensPort)
    sensor.outPort.bind(ecDev2.uc.sensPort)
    # sensless, but test that a peer-to-peer port can be bound to an additional input port
    ecDev1.uc.fpgaPort._outPort.bind(sensor.pwrPort)

    
    
    moddyGenerateStructureGraph(simu, 'struct', keepGvFile=True)
    