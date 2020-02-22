'''
:mod:`sim_parts_mgr` -- Parts manager
========================================

.. module:: sim_parts_mgr
   :synopsis: Parts manager
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''

from .sim_part import SimPart
from .sim_base import add_elem_to_list

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
                          is not None else '' + '.'
                          + part_hierarchy_name))
