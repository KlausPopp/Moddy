'''
:mod:`dotFsm` -- Generate a graph of a moddy finite state machine
=======================================================================

.. module:: dotFsm
   :synopsis: Generate a graph of a moddy finite state machine
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
from moddy.fsm import isSubFsmSpecification
from moddy.utils import moddyCreateDirsAndOpenOutputFile

import subprocess
import os


def moddyGenerateFsmGraph( fsm, fileName, keepGvFile=False ):
    ''' 
    Generate a Fsm Graph of an fsm using the GraphViz dot tool
    
    :param fsm: an instance of the fsm
    :param fileName: the relative filename including '.svg'  
    :param keepGvFile: if True, don't delete graphviz input file
    '''
    df = DotFsm(fsm)
    df.dotGen(fileName, keepGvFile)

def space(indent):
    istr = "%" + str(3*indent) + "s"
    return istr % ""


def mapStateNames(name,state):
    if state == '': s = 'INIT'
    else: s = state
    if name != '':
        s = name + '_' + s
    return s

class DotFsm(object):
    '''
    Display the an fsm via the DOT language (Graphviz)
    States are vizualized as nodes
    Subfsms are drawn in separate subgraphs, an edge is drawn from the main state to the 
    initial state in the subfsm
    '''
    def __init__(self, fsm):
        self._fsm = fsm
    
    def fsmGen(self, level, fsm, name='', isSubFsm=False):
        '''
        generate the dot language statements for a (sub)fsm
        return lines,initialState
        initialState is only valid on subFsms
        '''
        lines = []
        initialState = None
        
        dictTransitions = fsm.getDictTransitions()
        # States
        for state, listTrans in dictTransitions.items():
            if state == '':
                s = '%s [style=invisible];' % mapStateNames(name,state)
                if isSubFsm:
                    s = None
            elif state == 'ANY':
                s = '%s [label="from any state" shape=none];' % mapStateNames(name,state)
            else:
                s = '%s [label=%s];' % (mapStateNames(name,state), state)
            if s is not None:
                lines.append( [level, s] )
        
        # Transitions
        for fromState, listTrans in dictTransitions.items():
            for trans in listTrans:
                subFsmCls = isSubFsmSpecification(trans)
                if subFsmCls is not None:
                    subFsmName, cls = trans
                    # subfsm specification, instantiate subfsm
                    subFsm = subFsmCls(parentFsm = fsm)
                    lines.append( [level, 'subgraph cluster_%s {  ' % (subFsmName)])
                    lines.append( [level+1, 'label="%s";' % (subFsmName)])

                    # draw subfsm
                    subLines, subInitialState = self.fsmGen( level+1, subFsm, 
                                                             name=subFsmName, isSubFsm=True )
                    lines += subLines
                    lines.append( [level, '}' ])
                    
                    # draw edge from main state to subfsm initial state
                    lines.append( [level, '%s -> %s [color=lightgrey];' % (mapStateNames(name,fromState),
                                                                           subInitialState)] )
                else:
                    # normal transition
                    event, toState = trans
                    if isSubFsm and event == 'INITIAL':
                        initialState = mapStateNames(name,toState)
                    else:
                        lines.append( [level, '%s -> %s [label="%s"];' % (mapStateNames(name,fromState), 
                                                                          mapStateNames(name,toState), event)] )
        return lines, initialState        
            
        
    def dotGen(self, fileName, keepGvFile):
        level = 0
        lines=[]
        lines.append( [level, 'digraph G {'] )
        lines.append( [level+1, 'rankdir=TB;'] )
        lines.append( [level+1, 'graph [fontname = "helvetica" fontsize=10 fontnodesep=0.1];'] )
        lines.append( [level+1, 'node [fontname = "helvetica" fontsize=10 shape=ellipse color=black height=.1];'] )
        lines.append( [level+1, 'edge [fontname = "helvetica" color=black fontsize=8 fontcolor=black];'] )

        subLines, initialState = self.fsmGen( level+1, self._fsm)
        lines += subLines
                 
        # finish
        lines.append( [level, '}' ])
        
        # Output the DOT file as filename.dot e.g. test.svg.gv
        dotFile = "%s.gv" % fileName
        f = moddyCreateDirsAndOpenOutputFile(dotFile)
        for line in lines:
            f.write("%s%s\n" % (space(line[0]), line[1]))
        f.close()
        subprocess.check_call(['dot', '-Tsvg', dotFile, '-o%s' % fileName])
        print("Saved FSM graph to %s"  % fileName)
        if not keepGvFile:
            os.unlink(dotFile)
            
