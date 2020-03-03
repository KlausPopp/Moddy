'''
:mod:`dotFsm` -- Generate a graph of a moddy finite state machine
=======================================================================

.. module:: dotFsm
   :synopsis: Generate a graph of a moddy finite state machine
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
import subprocess
import os

from .fsm import is_sub_fsm_specification
from .utils import create_dirs_and_open_output_file


def gen_fsm_graph(fsm, file_name, keep_gv_file=False):
    '''
    Generate a Fsm Graph of an fsm using the GraphViz dot tool

    :param fsm: an instance of the fsm
    :param file_name: the relative filename including '.svg'
    :param keep_gv_file: if True, don't delete graphviz input file
    '''
    dot_fsm = DotFsm(fsm)
    dot_fsm.dot_gen(file_name, keep_gv_file)


def _space(indent):
    istr = "%" + str(3 * indent) + "s"
    return istr % ""


def map_state_names(name, state):
    if state == '':
        s = 'INIT'
    else:
        s = state

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

    def fsm_gen(self, level, fsm, name='', is_sub_fsm=False):
        '''
        generate the dot language statements for a (sub)fsm
        return lines,initial_state
        initial_state is only valid on subFsms
        '''
        lines = []
        initial_state = None

        dict_transitions = fsm.get_dict_transitions()
        # States
        for state, list_trans in dict_transitions.items():
            if state == '':
                sstr = '%sstr [style=invisible];' % \
                    map_state_names(name, state)
                if is_sub_fsm:
                    sstr = None
            elif state == 'ANY':
                sstr = '%sstr [label="from any state" shape=none];' % \
                    map_state_names(name, state)
            else:
                sstr = '%sstr [label=%sstr];' % \
                    (map_state_names(name, state), state)
            if sstr is not None:
                lines.append([level, sstr])

        # Transitions
        for from_state, list_trans in dict_transitions.items():
            for trans in list_trans:
                sub_fsm_cls = is_sub_fsm_specification(trans)
                if sub_fsm_cls is not None:
                    sub_fsm_name, cls = trans
                    # subfsm specification, instantiate subfsm
                    sub_fsm = sub_fsm_cls(parentFsm=fsm)
                    lines.append([level, 'subgraph cluster_%s {  ' %
                                  (sub_fsm_name)])
                    lines.append([level + 1, 'label="%s";' %
                                  (sub_fsm_name)])

                    # draw subfsm
                    sub_lines, sub_initial_state = \
                        self.fsm_gen(level + 1, sub_fsm,
                                     name=sub_fsm_name, is_sub_fsm=True)
                    lines += sub_lines
                    lines.append([level, '}' ])

                    # draw edge from main state to subfsm initial state
                    lines.append([level, '%s -> %s [color=lightgrey];' %
                                  (map_state_names(name, from_state),
                                   sub_initial_state)])
                else:
                    # normal transition
                    event, to_state = trans
                    if is_sub_fsm and event == 'INITIAL':
                        initial_state = map_state_names(name, to_state)
                    else:
                        lines.append([level, '%s -> %s [label="%s"];' %
                                      (map_state_names(name, from_state),
                                       map_state_names(name, to_state),
                                       event)])
        return lines, initial_state

    def dot_gen(self, file_name, keep_gv_file):
        level = 0
        lines = []
        lines.append([level, 'digraph G {'])
        lines.append([level + 1, 'rankdir=TB;'])
        lines.append([level + 1,
                      'graph [fontname = "helvetica" fontsize=10 '
                      'fontnodesep=0.1];'])
        lines.append([level + 1,
                      'node [fontname = "helvetica" fontsize=10 '
                      'shape=ellipse color=black height=.1];'])
        lines.append([level + 1,
                      'edge [fontname = "helvetica" color=black fontsize=8 '
                      'fontcolor=black];'])

        sub_lines, _ = self.fsm_gen(level + 1, self._fsm)
        lines += sub_lines

        # finish
        lines.append([level, '}'])

        # Output the DOT file as filename.dot e.g. test.svg.gv
        dot_file = "%s.gv" % file_name
        file_desc = create_dirs_and_open_output_file(dot_file)
        for line in lines:
            file_desc.write("%s%s\n" % (_space(line[0]), line[1]))
        file_desc.close()
        subprocess.check_call(['dot', '-Tsvg', dot_file, '-o%s' % file_name])
        print("Saved FSM graph to %s" % file_name)
        if not keep_gv_file:
            os.unlink(dot_file)

