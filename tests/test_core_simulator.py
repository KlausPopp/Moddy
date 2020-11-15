"""
Created on 23.12.2018

@author: klauspopp@gmx.de
"""


import unittest
import moddy

from tests.utils import (
    searchInMsg,
    searchAnn,
    searchTExp,
    baseFileName,
    funcName,
)


class TestSimulatorMsgPassing(unittest.TestCase):
    """
    Test the simulator core
    """

    # pylint: disable=no-member
    class Consumer(moddy.SimPart):
        def __init__(self, sim, objName):
            super().__init__(sim=sim, obj_name=objName)

            self.create_ports("in", ["cons_port"])
            self.create_timers(["timeout_tmr"])
            self.timeout_tmr.restart(5.1)

        def cons_port_recv(self, _, msg):
            self.annotation(msg.__str__())
            # damage msg
            msg["submsg"] = "ABC"
            self.timeout_tmr.restart(5)

        def timeout_tmr_expired(self, _):
            self.annotation("Timeout")

    class Producer(moddy.VSimpleProg):
        def __init__(self, sim, objName):
            # Initialize the parent class
            super().__init__(sim=sim, obj_name=objName, parent_obj=None)

            # Ports
            self.create_ports("out", ["prodPort"])

        def run_vthread(self):
            print("rvt")
            submsg = {"subattr": 123}
            msg = {"submsg": submsg}

            self.wait_until(2)
            self.prodPort.send(msg, 3)
            # manipulate msg to test if deepcopy works
            submsg["subattr"] = 234
            self.prodPort.send(msg, 3)
            submsg["subattr"] = 567
            self.prodPort.send(msg, 0.0)

    def test_simulator_msg_passing(self):
        simu = moddy.Sim()

        prod = TestSimulatorMsgPassing.Producer(simu, "Prod")
        cons1 = TestSimulatorMsgPassing.Consumer(simu, "Cons1")
        cons2 = TestSimulatorMsgPassing.Consumer(simu, "Cons2")

        prod.prodPort.bind(cons1.cons_port)
        prod.prodPort.bind(cons2.cons_port)

        # let simulator run
        simu.run(stop_time=100)

        moddy.gen_interactive_sequence_diagram(
            sim=simu,
            show_parts_list=["Prod", "Cons1", "Cons2"],
            file_name="output/%s_%s.html" % (baseFileName(), funcName()),
            fmt="iaViewerRef",
            time_per_div=1.0,
            pix_per_div=30,
        )

        trc = simu.tracing.traced_events()

        # check if first message is correctly received on both consumers
        # in trace
        self.assertEqual(
            searchInMsg(trc, 5.0, cons1.cons_port),
            "{'submsg': {'subattr': 123}}",
        )
        self.assertEqual(
            searchInMsg(trc, 5.0, cons2.cons_port),
            "{'submsg': {'subattr': 123}}",
        )

        # check if first message is correctly received on both consumers as ANN
        self.assertEqual(
            searchAnn(trc, 5.0, cons1), "{'submsg': {'subattr': 123}}"
        )
        self.assertEqual(
            searchAnn(trc, 5.0, cons2), "{'submsg': {'subattr': 123}}"
        )

        # check if second and third message is correctly received on both
        # consumers in trace
        self.assertEqual(
            searchInMsg(trc, 8.0, cons1.cons_port),
            "{'submsg': {'subattr': 234}}",
        )
        self.assertEqual(
            searchInMsg(trc, 8.0, cons2.cons_port),
            "{'submsg': {'subattr': 234}}",
        )
        self.assertEqual(
            searchInMsg(trc, 8.0, cons1.cons_port, 2),
            "{'submsg': {'subattr': 567}}",
        )
        self.assertEqual(
            searchInMsg(trc, 8.0, cons2.cons_port, 2),
            "{'submsg': {'subattr': 567}}",
        )

        # check if second and third message is correctly received on
        # both consumers as ANN
        self.assertEqual(
            searchAnn(trc, 8.0, cons1), "{'submsg': {'subattr': 234}}"
        )
        self.assertEqual(
            searchAnn(trc, 8.0, cons2), "{'submsg': {'subattr': 234}}"
        )
        self.assertEqual(
            searchAnn(trc, 8.0, cons1, 2), "{'submsg': {'subattr': 567}}"
        )
        self.assertEqual(
            searchAnn(trc, 8.0, cons2, 2), "{'submsg': {'subattr': 567}}"
        )

        # check timeouts
        self.assertEqual(searchTExp(trc, 13.0, cons1.timeout_tmr), True)
        self.assertEqual(searchTExp(trc, 13.0, cons2.timeout_tmr), True)
        self.assertEqual(searchAnn(trc, 13.0, cons1), "Timeout")
        self.assertEqual(searchAnn(trc, 13.0, cons2), "Timeout")


if __name__ == "__main__":
    unittest.main()
