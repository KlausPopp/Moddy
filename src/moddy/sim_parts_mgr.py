'''
:mod:`sim_parts_mgr` -- Parts manager
========================================

.. module:: sim_parts_mgr
   :synopsis: Parts manager
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''

from .sim_base import SimBaseElement
from .sim_part import SimPart
from .sim_base import add_elem_to_list
from .sim_ports import SimOutputPort, SimIOPort
from moddy.sim_ports import SimInputPort


class SimPartsManager:
    '''
    Manage the simulator parts
    '''

    def __init__(self):
        self._top_level_parts = []

    def add_top_level_part(self, part):
        '''Add part to simulators part list'''
        if not isinstance(part, SimPart):
            raise ValueError("part %s is not a SimPart" % (part))
        if part.parent_obj is not None:
            raise ValueError("part %s is not a top level part" % (part))

        add_elem_to_list(self._top_level_parts, part, "SimParts TL-Parts")

    def top_level_parts(self):
        ''' get list of top level parts '''
        return self._top_level_parts

    def walk_parts(self):
        ''' Generator to walk recoursively through all parts '''
        for part in self._top_level_parts:
            yield part
            yield from self._walk_sub_parts(part)

    def _walk_sub_parts(self, part):
        for sub_part in part.sub_parts():
            yield sub_part
            yield from self._walk_sub_parts(sub_part)

    def find_part_by_name(self, part_hierarchy_name, start_part=None):
        '''
        Find a part by its hierarchy name
        :param string part_hierarchy_name: e.g. "part1.subpart.subsubpart"
        :param start_part: part to start searching. If None, start from root.\
             (default:None)
        :return simPart part: the found part
        :raises ValueError: if part not found
        '''
        if start_part is None:
            lst_parts = self._top_level_parts
        else:
            lst_parts = start_part.sub_parts()

        path_elems = part_hierarchy_name.split('.')

        for part in lst_parts:
            if path_elems[0] == part.obj_name():
                if len(path_elems) > 1:
                    return self.find_part_by_name('.'.join(path_elems[1:]),
                                                  part)
                return part

        raise ValueError("Part not found %s" %
                         (start_part.hierarchy_name() if start_part
                          is not None else '' + '.' +
                          part_hierarchy_name))

    def walk_ports(self, port_class=SimBaseElement):
        '''
        Generator to walk recoursively through all ports.

        For SimIOPorts the in and out ports are returned separately
        (but not the ioport)

        :param port_class: only handle ports with this class or \
            a subclass of it. If None, handle all
        '''
        for part in self.walk_parts():
            for port in part.ports():
                if isinstance(port, SimIOPort):
                    sub_ports = [port.in_port(), port.out_port()]
                else:
                    sub_ports = [port]

                for sub_port in sub_ports:
                    if isinstance(sub_port, port_class):
                        yield sub_port

    def all_output_ports(self):
        ''' Return a list of all output ports '''
        return list(self.walk_ports(SimOutputPort))

    def check_unbound_ports(self):
        '''
        Check if all ports are connected
        print warnings for unconnected ports
        '''
        for port in self.walk_ports():
            if not port.is_bound():
                print("SIM: WARNING: Port %s not bound" %
                      (port.hierarchy_name_with_type()))

    def find_port_by_name(self, port_hierarchy_name):
        '''
        Find a port (input or output or IO) by its hierarchy name
        :param str port_hierarchy_name: e.g. \
            "part1.ioPort1" or "part1.ioPort1In"
        :return port: the found port
        :raises ValueError: if port not found
        '''

        for part in self.walk_parts():
            for port in part.ports():
                # print("findPortByName %s %s" % (port.hierarchy_name(),
                # port._typeStr ))
                if port.hierarchy_name() == port_hierarchy_name:
                    return port

                if isinstance(port, SimIOPort):
                    if port.in_port().hierarchy_name() == port_hierarchy_name:
                        return port.in_port()
                    if port.out_port().hierarchy_name() == port_hierarchy_name:
                        return port.out_port()

        raise ValueError("Port not found %s" % port_hierarchy_name)

    def smart_bind(self, bindings):
        '''
        Create many port bindings at once using simple lists.

        Example:

        .. code-block:: python

            simu.smartBind( [
                ['App.outPort1', 'Dev1.inPort', 'Dev2.inPort'],
                ['App.ioPort1', 'Server.netPort' ]  ])

        :param list bindings: Each list element must be a list of strings, \
            which specifies ports that shall be \
            connected to each other. \
            The strings must specify the hierarchy names of the ports.

        '''

        for binding in bindings:
            self._single_smart_bind(binding)

    def _single_smart_bind(self, binding):
        # determine output and input ports
        out_ports = []
        in_ports = []

        for port_name in binding:
            port = self.find_port_by_name(port_name)

            if isinstance(port, SimOutputPort):
                out_ports.append(port)
            elif isinstance(port, SimIOPort):
                out_ports.append(port.out_port())
                in_ports.append(port.in_port())
            elif isinstance(port, SimInputPort):
                in_ports.append(port)

        # bind all output ports to all input ports
        for out_port in out_ports:
            for in_port in in_ports:
                if out_port.io_port() is None or \
                        (out_port.io_port() != in_port.io_port()):

                    out_port.bind(in_port)
