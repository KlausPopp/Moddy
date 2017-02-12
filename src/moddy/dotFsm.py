'''
Created on 12.02.2017

@author: Klaus Popp
'''

from moddy.fsm import Fsm
import subprocess
import os


def moddyGenerateFsmGraph( fsm, fileName, keepGvFile=False ):
    ''' 
    Generate a Fsm Graph of an fsm using the GraphViz dot tool
    <fileName> should be the relative filename including '.svg'  
    <keepGvFile> if True, don't delete graphviz input file
    '''
    df = DotFsm(fsm.getDictTransitions())
    df.dotGen(fileName, keepGvFile)

def space(indent):
    istr = "%" + str(3*indent) + "s"
    return istr % ""


def mapStateNames(state):
    if state == '': return 'INIT'
    else: return state
 
class DotFsm(object):
    '''
    Display the model structure via the DOT language (Graphviz)
    States are vizualized as nodes
    '''
    def __init__(self, dictTransitions):
        self._dictTransitions = dictTransitions
        
        
    def dotGen(self, fileName, keepGvFile):
        level = 0
        lines=[]
        lines.append( [level, 'digraph G {'] )
        lines.append( [level+1, 'rankdir=TB;'] )
        lines.append( [level+1, 'graph [fontname = "helvetica" fontsize=10 fontnodesep=0.1];'] )
        lines.append( [level+1, 'node [fontname = "helvetica" fontsize=10 shape=ellipse color=black height=.1];'] )
        lines.append( [level+1, 'edge [fontname = "helvetica" color=black fontsize=8 fontcolor=black];'] )

        # States
        for state, listTrans in self._dictTransitions.items():
            if state == '':
                s = '%s [style=invisible];' % mapStateNames(state)
            elif state == 'ANY':
                s = '%s [label="from any state" shape=none];' % mapStateNames(state)
            else:
                s = '%s;' % mapStateNames(state)
            lines.append( [level+1, s] )
        
        # Tranisitions
        for fromState, listTrans in self._dictTransitions.items():
            for trans in listTrans:
                event, toState = trans
                
                lines.append( [level+1, '%s -> %s [label="%s"];' % (mapStateNames(fromState), 
                                                                    mapStateNames(toState), event)] )
                
                
        # finish
        lines.append( [level, '}' ])
        
        # Output the DOT file as filename.dot e.g. test.svg.gv
        dotFile = "%s.gv" % fileName
        f = open(dotFile, 'w')
        for line in lines:
            f.write("%s%s\n" % (space(line[0]), line[1]))
        f.close()
        subprocess.check_call(['dot', '-Tsvg', dotFile, '-o%s' % fileName])
        print("Saved FSM graph to %s"  % fileName)
        if not keepGvFile:
            os.unlink(dotFile)
            
#
#
#
if __name__ == '__main__':

    transitions = { 
        '': # FSM uninitialized
            [('INITIAL', 'Off')],                
        'Off': 
            [('PowerApplied', 'Standby')],
        'Standby':
            [('powerButtonPort_Msg', 'Booting')],
        'Booting':
            [('bootTmr_Expired', 'NormalOp')],
        'NormalOp':
            [('powerButtonPort_Msg', 'Shutdown'),
             ('osPort_Msg', 'Shutdown')],
        'Shutdown':
            [('shutdownTmr_Expired', 'Standby')],
        'ANY':
            [('PowerRemoved', 'Off')]
    }
    df = DotFsm(transitions)
    df.dotGen('dotFsm.svg', keepGvFile=True)