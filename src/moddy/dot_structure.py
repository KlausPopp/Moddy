'''
:mod:`dot_structure` -- Generate a graph of the model structure
=======================================================================

.. module:: dot_structure
   :synopsis: Generate a graph of the model structure
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''
import subprocess
import os

from .utils import create_dirs_and_open_output_file


def gen_dot_structure_graph(sim, file_name, keep_gv_file=False):
    '''
    Generate a graph of the model structure using the GraphViz dot tool

    :param sim sim: Simulator instance
    :param file_name: the relative filename including '.svg'
    :param keep_gv_file: if True, don't delete graphviz input file
    '''
    dot = DotStructure(sim.parts_mgr.top_level_parts(),
                       sim.parts_mgr.all_output_ports())
    dot.dot_gen(file_name, keep_gv_file)


def _space(indent):
    istr = "%" + str(3 * indent) + "s"
    return istr % ""


def _moddy_name_to_dot_name(hierarchy_name):
    ret_val = hierarchy_name.replace(".", "__")
    ret_val = ret_val.replace("-", "_")
    return ret_val


def _subgraph_name(part_hierarchy_name):
    return "cluster_" + _moddy_name_to_dot_name(part_hierarchy_name)


def _port_or_io_port_hierarchy_name(port):
    ''' return port name or if port is part of IOPort, the IOPorts Name'''
    if port.io_port() is not None:
        return port.io_port().hierarchy_name()
    return port.hierarchy_name()


def _port_or_io_port_obj_name(port):
    ''' return port name or if port is part of IOPort, the IOPorts Name'''
    if port.io_port() is not None:
        return port.io_port().obj_name()
    return port.obj_name()


def _p2p_port_msg_types(port1, port2):
    ''' join the message types of the two ports '''
    msg_types = port1.learned_msg_types() + port2.learned_msg_types()
    lst = []
    for msg_type in msg_types:
        if msg_type not in lst:
            lst.append(msg_type)
    return _port_msg_types_to_label(lst)


def _port_msg_types_to_label(msg_types):
    ret_val = ""
    for msg_type in msg_types:
        if ret_val != "":
            ret_val += ", "
        ret_val += msg_type
    return ret_val


class DotStructure:
    # pylint: disable=too-few-public-methods
    '''
    Display the model structure via the DOT language (Graphviz)
    Parts are vizualized as subgraphs
    Ports are vizualized as nodes
    Parts that have no ports will be invisible
    '''

    def __init__(self, top_level_parts, output_ports):
        '''
        <top_level_parts> must be the list of top level parts in the model
        <output_ports> must a list of all output ports in the model

        '''
        self._top_level_parts = top_level_parts
        self._output_ports = output_ports
        self._list_schedulers = []

    def _part_structure_gen(self, part, level):
        lines = []

        if hasattr(part, 'add_vthread'):
            # show schedulers as an ellipse-node, and without subparts
            lines.append([level, '%s [label=%s shape=ellipse];' %
                         (_moddy_name_to_dot_name(part.hierarchy_name()),
                          _moddy_name_to_dot_name(part.obj_name()))])
            self._list_schedulers.append(part)

        else:
            # normal part is shown as a subgraph
            lines.append([level, 'subgraph %s {' %
                          _subgraph_name(part.hierarchy_name())])
            lines.append([level + 1, 'label=<<B>%s</B>>' % part.obj_name()])

            # now the ports
            list_ports = part.ports()
            if len(list_ports) > 0:
                for port in list_ports:
                    lines.append(
                        [level + 1, '%s [label=%s];' %
                         (_moddy_name_to_dot_name(
                             port.hierarchy_name()),
                          _moddy_name_to_dot_name(
                              port.obj_name()))])

            # now the subparts
            for sub_part in part.sub_parts():
                lines += self._part_structure_gen(sub_part, level + 1)

            lines.append([level, '}'])

        return lines

    def _bindings_gen(self, level):
        lines = []
        known_bindings = []

        for port in self._output_ports:
            io_port = None
            # test if IOPort
            if port.io_port() is not None:
                io_port = port.io_port()
                peers = io_port.peer_ports()

                for peer in peers:
                    # print( "port %s peer %s" % (io_port, peer))
                    if (io_port.out_port(), peer.in_port()) not in \
                        known_bindings and \
                        (peer.out_port(), io_port.in_port()) not in \
                            known_bindings:

                        # Has a peer port, make bidirectional connection
                        lines.append(
                            [level,
                             '%s -> %s  [dir=none penwidth=3 label="%s"]' %
                             (
                                 _moddy_name_to_dot_name(
                                     _port_or_io_port_hierarchy_name(port)),
                                 _moddy_name_to_dot_name(
                                     peer.hierarchy_name()),
                                 _p2p_port_msg_types(
                                     port.io_port().out_port(),
                                     peer.out_port())
                             )])

                        # These ports are already connected,
                        # ignore them in the rest of the scan
                        known_bindings.append(
                            (io_port.out_port(), peer.in_port()))
                        known_bindings.append(
                            (peer.out_port(), io_port.in_port()))

            for in_port in port.in_ports():
                if io_port is None or \
                        (io_port.out_port(), in_port) not in known_bindings:
                    lines.append(
                        [level,
                         '%s -> %s [label="%s"]' % (
                             _moddy_name_to_dot_name(
                                 _port_or_io_port_hierarchy_name(port)),
                             _moddy_name_to_dot_name(
                                 _port_or_io_port_hierarchy_name(in_port)),
                             _port_msg_types_to_label(
                                 port.learned_msg_types())
                             )])

        return lines

    def _scheduler_relations_gen(self, level):
        lines = []
        for sched in self._list_schedulers:
            for thread in sched.threads():
                # Dot allows only edges between nodes,
                # so take the first port of that part
                # if the part has no port, issue warning
                if len(thread.ports()) > 0:
                    if thread != sched.parent_obj:
                        first_port = thread.ports()[0]

                        prio = thread.sched_data.prio
                        dest_node = _moddy_name_to_dot_name(
                            first_port.hierarchy_name())

                        lines.append(
                            [level,
                             '%s -> %s [lhead=%s label="%s" '
                             'color=lightblue fontsize=8 '
                             'fontcolor=lightblue ]' %
                                (_moddy_name_to_dot_name(
                                    sched.hierarchy_name()),
                                 dest_node,
                                 "cluster_" + _moddy_name_to_dot_name(
                                     thread.hierarchy_name()),
                                 prio)])
                else:
                    print("WARNING: Thread %s has no ports. Scheduler "
                          "connection cannot be shown in structure" %
                          thread.hierarchy_name())
        return lines

    def dot_gen(self, file_name, keep_gv_file):
        ''' generate the dot file '''
        level = 0
        lines = []
        lines.append([level, 'digraph G {'])
        lines.append([level + 1, 'rankdir=LR;'])
        lines.append([level + 1, 'compound=true;'])
        lines.append([level + 1,
                      'graph [fontname = "helvetica" fontsize=10 '
                      'fontnodesep=0.1];'])
        lines.append([level + 1, 'node [fontname = "helvetica" fontsize=10 '
                      'shape=box color=lightblue height=.1];'])
        lines.append([level + 1, 'edge [fontname = "helvetica" color=red '
                      'fontsize=8 fontcolor=red];'])

        # Structure
        for part in self._top_level_parts:
            lines += self._part_structure_gen(part, level + 1)

        # Bindings
        lines += self._bindings_gen(level + 1)

        # Scheduler relations
        lines += self._scheduler_relations_gen(level + 1)

        # finish
        lines.append([level, '}'])

        # Output the DOT file as filename.dot e.g. test.svg.gv
        dot_file = "%s.gv" % file_name
        # print("file_name=%s" % dot_file )
        file_desc = create_dirs_and_open_output_file(dot_file)
        for line in lines:
            file_desc.write("%s%s\n" % (_space(line[0]), line[1]))
        file_desc.close()
        subprocess.check_call(['dot', '-Tsvg', dot_file, '-o%s' % file_name])
        print("Saved structure graph to %s" % file_name)
        if not keep_gv_file:
            os.unlink(dot_file)
