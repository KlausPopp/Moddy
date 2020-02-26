'''
:mod:`dotStructure` -- Generate a graph of the model structure
=======================================================================

.. module:: dotStructure
   :synopsis: Generate a graph of the model structure
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
import subprocess
import os

from .sim_core import Sim
from .sim_part import SimPart
from .utils import moddyCreateDirsAndOpenOutputFile



def moddyGenerateStructureGraph( sim, fileName, keepGvFile=False ):
    ''' 
    Generate a graph of the model structure using the GraphViz dot tool
    
    :param sim sim: Simulator instance
    :param fileName: the relative filename including '.svg'
    :param keepGvFile: if True, don't delete graphviz input file
    '''
    ds = DotStructure(sim.parts_mgr.top_level_parts(), 
                      sim.parts_mgr.all_output_ports())
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
    if port.io_port() is not None:
        return port.io_port().hierarchy_name()
    else:
        return port.hierarchy_name()
    
def portOrIoPortObjName(port):
    ''' return port name or if port is part of IOPort, the IOPorts Name'''
    if port._ioPort is not None:
        return port._ioPort.obj_name()
    else:
        return port.obj_name()

def p2pPortMsgTypes(port1,port2):
    ''' join the message types of the two ports '''
    msgTypes = port1.learned_msg_types() + port2.learned_msg_types()
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
        
                    
    def showPart(self, part, level):
        lstr = "%" + str(3*level) + "s%s"
        print(lstr % ("", part._objName))
        for port in part._listPorts:
            print(lstr % ("", " P:" + port._objName))
        
        for subPart in part._listSubParts:
            self.showPart(subPart, level+1)
        
    def partStructureGen(self, part, level):
        lines = []
        
        if part.type_str == "scheduler":
            # show schedulers as an ellipse-node, and without subparts
            lines.append( [level, '%s [label=%s shape=ellipse];' % 
                           (moddyNameToDotName(part.hierarchy_name()), moddyNameToDotName(part.obj_name()))])
            self._listSchedulers.append(part)
            
        else:
            # normal part is shown as a subgraph
            lines.append( [level, 'subgraph %s {' % subgraphName(part.hierarchy_name())])
            lines.append( [level+1, 'label=<<B>%s</B>>' % part.obj_name()] )
            
            # now the ports
            listPorts = part.ports()
            if len(listPorts) > 0:
                for port in listPorts:
                    lines.append( [level+1, '%s [label=%s];' % 
                                   (moddyNameToDotName(port.hierarchy_name()), 
                                    moddyNameToDotName(port.obj_name()))  ])
                
                    
            # now the subparts
            for subPart in part.sub_parts():
                lines += self.partStructureGen(subPart, level+1)
    
            lines.append( [level, '}' ])
        
        return lines
            
    def bindingsGen(self, level):
        lines = []
        knownBindings = []
        
        for port in self._outputPorts:
            ioPort = None
            # test if IOPort 
            if port.io_port() is not None:
                ioPort = port._ioPort 
                peers = ioPort.peerPorts()
                
                for peer in peers:
                    #print( "port %s peer %s" % (ioPort, peer))
                    if not ( ioPort._out_port, peer._in_port ) in knownBindings and not ( peer._out_port, ioPort._in_port ) in knownBindings:
                        
                        # Has a peer port, make bidirectional connection
                        lines.append( [level, '%s -> %s  [dir=none penwidth=3 label="%s"]' % ( #[constraint=false]
                              moddyNameToDotName(portOrIoPortHierarchyName(port)),
                              moddyNameToDotName(peer.hierarchy_name()),
                              p2pPortMsgTypes(port._ioPort._out_port, peer._out_port) 
                            )] )
    
                        # These ports are already connected, ignore them in the rest of the scan
                        knownBindings.append( ( ioPort._out_port, peer._in_port ))
                        knownBindings.append( ( peer._out_port, ioPort._in_port ))
                        
                    
            for inPort in port._list_in_ports:
                if ioPort is None or not ( ioPort._out_port, inPort ) in knownBindings:
                    lines.append( [level, '%s -> %s [label="%s"]' % ( #[constraint=false]
                          moddyNameToDotName(portOrIoPortHierarchyName(port)),
                          moddyNameToDotName(portOrIoPortHierarchyName(inPort)),
                          portMsgTypesToLabel(port.learned_msg_types()) ) ] )
                         
         
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
                        destNode = moddyNameToDotName(firstPort.hierarchy_name())
    
                        lines.append( [level, 
                                       '%s -> %s [lhead=%s label="%s" color=lightblue fontsize=8 fontcolor=lightblue ]' % 
                                       ( moddyNameToDotName(sched.hierarchy_name()),
                                         destNode,
                                         "cluster_" + moddyNameToDotName(thread.hierarchy_name()),
                                         prio ) ] )
                else:
                    print("WARNING: Thread %s has no ports. Scheduler connection cannot be shown in structure" % 
                          thread.hierarchy_name())
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

    
    class Cpu(SimPart):
        def __init__(self, sim, obj_name, parent_obj = None):
            super().__init__(sim, obj_name, parent_obj)
            self.sched = vtSchedRtos(sim, "schedCpu", self)
            self.app1 = App(sim,"App1", self)
            self.app2 = App(sim,"App2", self)
            
            self.sched.add_vthread(self.app1, 1)
            self.sched.add_vthread(self.app2, 2)
            
    class App(vThread):
        def __init__(self, sim, obj_name, parent_obj = None):
            super().__init__(sim, obj_name, parent_obj )
    
            self.create_ports('SamplingIO', ['ecmPort'])

        def run_vthread(self):
            while True:
                pass
        
            
    class EcMaster(SimPart):
        
        def __init__(self, sim, obj_name, parent_obj = None):
            super().__init__(sim, obj_name, parent_obj)
    
            self.create_ports('io', ['appPort','ecPort'])
            
    
        def appPortRecv(self, port, msg):
            pass    
        def ecPortRecv(self, port, msg):
            pass    
    

    class EcDevice(SimPart):
        
        def __init__(self, sim, obj_name, parent_obj = None):
            super().__init__(sim, obj_name, parent_obj)
    
            self.create_ports('io', ['ecPort','ucPort'])
            
            self.uc = self.EcUc(sim, self)
            self.fpga = self.EcFpga(sim, self)
            self.ucPort.bind(self.uc.escPort)
            self.uc.fpgaPort.bind(self.fpga.ucPort)
    
        def ecPortRecv(self, port, msg):
            pass    
    
        def ucPortRecv(self, port, msg):
            pass
    
        class EcUc(SimPart):
            
            def __init__(self, sim, parent_obj):
                super().__init__(sim, "uC", parent_obj)
                self.create_ports('in', ['sensPort'])
                self.create_ports('io', ['escPort', 'fpgaPort'])

                
            def escPortRecv(self, port, msg):
                pass
                
            def fpgaPortRecv(self, port, msg):
                pass
                
            def sensPortRecv(self, port, msg):
                pass

        class EcFpga(SimPart):
            
            def __init__(self, sim, parent_obj):
                super().__init__(sim, "FPGA", parent_obj)
                self.create_ports('io', ['ucPort'])
                
            def ucPortRecv(self, port, msg):
                pass

    class Sensor(SimPart):
        
        def __init__(self, sim, obj_name, parent_obj = None):
            super().__init__(sim, obj_name, parent_obj)
    
            self.create_ports('out', ['outPort'])
            self.create_ports('in', ['pwrPort'])
            
        def pwrPortRecv(self, port, msg):
                pass
    
   
    simu = Sim()
    cpu = Cpu(simu,"CPU")
    ecm = EcMaster(simu,"ECM")
    ecDev1 = EcDevice(simu,"DEV1")
    ecDev2 = EcDevice(simu,"DEV2")
    sensor = Sensor(simu,"SENSOR")
    ecm.ecPort._out_port.bind(ecDev1.ecPort._in_port)
    ecDev1.ecPort._out_port.bind(ecDev2.ecPort._in_port)
    ecDev2.ecPort._out_port.bind(ecm.ecPort._in_port)
    sensor.outPort.bind(ecDev1.uc.sensPort)
    sensor.outPort.bind(ecDev2.uc.sensPort)
    # sensless, but test that a peer-to-peer port can be bound to an additional input port
    ecDev1.uc.fpgaPort._out_port.bind(sensor.pwrPort)
    
    # test 3 IO ports bound together (mesh)
    cpu.app1.ecmPort.bind(ecm.appPort)
    cpu.app2.ecmPort.bind(ecm.appPort)
    cpu.app1.ecmPort.bind(cpu.app2.ecmPort)

    #print("app1 in outports %s Peers %s" %  (cpu.app1.ecmPort._in_port._outPorts, cpu.app1.ecmPort.peerPorts()))
    #print("app2 in outports %s" %  cpu.app2.ecmPort._in_port._outPorts)
    #print("ecm in outports %s" %  ecm.appPort._in_port._outPorts)
    
    for pName in ['SENSOR.outPort', 'DEV2.FPGA.ucPort', 'CPU.App1.ecmPort']:
        print("findPortByName %s = %s" % (pName, simu.find_port_by_name(pName)))
    
    moddyGenerateStructureGraph(simu, 'output/structTest.svg', keepGvFile=True)
    