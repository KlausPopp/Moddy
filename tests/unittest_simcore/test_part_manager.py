'''
@author: klauspopp@gmx.de
'''


import unittest
from moddy.sim_part import SimPart
from moddy.sim_parts_mgr import SimPartsManager

class TestPartsManager(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        part_mgr = SimPartsManager()
        self.part_mgr = part_mgr
        
        # use sim=None to avoid Sim instantiation
        self.part1 = SimPart(sim=None, obj_name="P1", parent_obj=None)
        self.part2 = SimPart(sim=None, obj_name="P2", parent_obj=None)
        part_mgr.add_top_level_part(self.part1)
        part_mgr.add_top_level_part(self.part2)
        self.subpart1_1 = SimPart(sim=None, obj_name="P1_1", 
                                  parent_obj=self.part1)
        self.subpart1_1_1 = SimPart(sim=None, obj_name="P1_1_1", 
                                    parent_obj=self.subpart1_1)


    def test_walk(self):
        part_mgr = self.part_mgr
        self.assertListEqual(part_mgr.top_level_parts(), [self.part1, 
                                                          self.part2])
        self.assertListEqual(list(part_mgr.walk_parts()), 
                             [self.part1, self.subpart1_1, 
                              self.subpart1_1_1, self.part2])
        
    def test_find(self):
        part_mgr = self.part_mgr

        self.assertEqual(part_mgr.find_part_by_name('P1'), self.part1 )
        self.assertEqual(part_mgr.find_part_by_name('P2'), self.part2 )
        
        self.assertEqual(part_mgr.find_part_by_name('P1.P1_1'), 
                         self.subpart1_1 )

        self.assertEqual(part_mgr.find_part_by_name('P1.P1_1.P1_1_1'), 
                         self.subpart1_1_1 )

        with self.assertRaises(ValueError):
            part_mgr.find_part_by_name('P3')

        with self.assertRaises(ValueError):
            part_mgr.find_part_by_name('P1.P2_1')

        
if __name__ == '__main__':
    unittest.main()
