"""
Created on 28.03.2019

@author: klauspopp@gmx.de
"""
import unittest
import moddy
from tests.utils import searchAnn, baseFileName, funcName


class TestWaitForMsg(unittest.TestCase):
    def testMultiPort(self):
        class myThread1(moddy.VSimpleProg):
            def __init__(self, sim):
                super().__init__(sim=sim, obj_name="Thread", parent_obj=None)
                self.create_ports("QueuingIn", ["inP1", "inP2"])

            def run_vthread(self):
                while True:
                    self.busy(30, "DEL")

                    for _ in range(4):
                        rv = self.wait_for_msg(30, [self.inP1, self.inP2])
                        self.annotation(rv)

        class stimThread(moddy.VSimpleProg):
            def __init__(self, sim):
                super().__init__(sim=sim, obj_name="Stim", parent_obj=None)
                self.create_ports("out", ["port1", "port2"])
                self.port2.set_color("blue")

            def run_vthread(self):
                while True:
                    self.wait(15, [])
                    self.port1.send("hello1 a", 5)
                    self.wait(15, [])
                    self.port2.send("hello2 a", 5)
                    self.wait(15, [])
                    self.port1.send("hello1 b", 5)
                    self.port2.send("hello2 b", 5)
                    self.wait(None)

        simu = moddy.Sim()

        t1 = myThread1(simu)

        stim = stimThread(simu)
        stim.port1.bind(t1.inP1)
        stim.port2.bind(t1.inP2)

        simu.run(200)

        moddy.gen_interactive_sequence_diagram(
            sim=simu,
            file_name="output/%s_%s.html" % (baseFileName(), funcName()),
            show_parts_list=[stim, t1],
            excluded_element_list=["allTimers"],
            time_per_div=10,
            pix_per_div=30,
        )

        trc = simu.tracing.traced_events()

        self.assertEqual(
            searchAnn(trc, 30.0, t1), "('hello1 a', Thread.inP1(InPort))"
        )
        self.assertEqual(
            searchAnn(trc, 35.0, t1), "('hello2 a', Thread.inP2(InPort))"
        )
        self.assertEqual(
            searchAnn(trc, 50.0, t1), "('hello1 b', Thread.inP1(InPort))"
        )
        self.assertEqual(
            searchAnn(trc, 50.0, t1, 2), "('hello2 b', Thread.inP2(InPort))"
        )
        self.assertEqual(searchAnn(trc, 110.0, t1), "None")

    def testSinglePort(self):
        class myThread1(moddy.VSimpleProg):
            def __init__(self, sim):
                super().__init__(sim=sim, obj_name="Thread", parent_obj=None)
                self.create_ports("QueuingIn", ["inP1"])

            def run_vthread(self):
                while True:
                    self.busy(30, "DEL")

                    for _ in range(4):
                        rv = self.wait_for_msg(30, self.inP1)
                        self.annotation(rv)

        class stimThread(moddy.VSimpleProg):
            def __init__(self, sim):
                super().__init__(sim=sim, obj_name="Stim", parent_obj=None)
                self.create_ports("out", ["port1"])

            def run_vthread(self):
                while True:
                    self.wait(5, [])
                    self.port1.send("hello a", 5)
                    self.wait(15, [])
                    self.port1.send("hello b", 5)
                    self.wait(15, [])
                    self.port1.send("hello c", 5)
                    self.port1.send("hello d", 5)
                    self.wait(None)

        simu = moddy.Sim()

        t1 = myThread1(simu)

        stim = stimThread(simu)
        stim.port1.bind(t1.inP1)

        simu.run(200)

        moddy.gen_interactive_sequence_diagram(
            sim=simu,
            file_name="output/%s_%s.html" % (baseFileName(), funcName()),
            show_parts_list=[stim, t1],
            excluded_element_list=["allTimers"],
            time_per_div=10,
            pix_per_div=30,
        )

        trc = simu.tracing.traced_events()

        self.assertEqual(searchAnn(trc, 30.0, t1), "hello a")
        self.assertEqual(searchAnn(trc, 30.0, t1, 2), "hello b")
        self.assertEqual(searchAnn(trc, 40.0, t1), "hello c")
        self.assertEqual(searchAnn(trc, 45.0, t1), "hello d")
        self.assertEqual(searchAnn(trc, 105.0, t1), "None")


if __name__ == "__main__":
    unittest.main()
