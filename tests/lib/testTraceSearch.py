"""
Created on 16.09.2019

@author: klauspopp@gmx.de
"""
import unittest
import moddy
from moddy.lib.trace_search import TraceSearch


class TestTraceSearch(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.simu = simu = moddy.Sim()

        moddy.VSimpleProg(
            sim=simu,
            obj_name="Bob",
            target=self.bob_prog,
            elems={"QueuingIO": "head"},
        )
        moddy.VSimpleProg(
            sim=simu,
            obj_name="Joe",
            target=self.joe_prog,
            elems={"QueuingIO": "head"},
        )

        simu.smart_bind([["Bob.head", "Joe.head"]])

        # let simulator run
        simu.run(
            stop_time=12.0,
            enable_trace_printing=False,
            stop_on_assertion_failure=False,
        )

        self.ts = TraceSearch(simu)
        idx = 0
        for te in self.ts.traced_events:
            print("#%d: %s" % (idx, te))
            idx += 1

    def test_find_ann(self):
        ts = self.ts

        # find any ANN
        rv = ts.find_ann("Bob", None, 0)
        self.assertEqual(rv[0], 16)
        self.assertEqual(rv[1].trans_val, "got message Hi, How are you?")

        rv = ts.find_ann("Bob", None)
        self.assertEqual(rv[0], 34)
        self.assertEqual(rv[1].trans_val, "got message Fine")

        # find with wildcard match
        rv = ts.find_ann("Bob", "*Fine", 15)
        self.assertEqual(rv[0], 34)
        self.assertEqual(rv[1].trans_val, "got message Fine")

    def test_find_sta(self):
        ts = self.ts

        rv = ts.find_sta("Joe", "Think", 0)
        self.assertEqual(rv[0], 9)
        rv = ts.find_sta("Joe", "")
        self.assertEqual(rv[0], 13)

    def test_find_rcv_msg(self):
        ts = self.ts

        rv = ts.find_rcv_msg("Joe", None, 0)
        self.assertEqual(rv[0], 5)

    def test_find_snd_msg(self):
        ts = self.ts

        rv = ts.find_snd_msg("Bob", "Hi*", 0)
        self.assertEqual(rv[0], 1)

        rv = ts.find_snd_msg("Bob", "How*")
        self.assertEqual(rv[0], 21)

    def test_find_ass_fail(self):
        ts = self.ts

        rv = ts.find_ass_fail("Bob", "Unknown*", 0)
        self.assertEqual(rv[0], 39)

        rv = ts.find_ass_fail("Joe", None, 0)
        self.assertEqual(rv, None)

    @staticmethod
    def bob_prog(self: moddy.VSimpleProg):
        # bob starts talking
        self.head.send("Hi Joe", 1)

        while True:
            msg = self.wait_for_msg(None, self.head)
            self.annotation("got message " + msg)

            self.busy(1.4, "Think")

            if msg == "Hi, How are you?":
                reply = "How are you?"
            else:
                self.assertion_failed("Unknown msg %s" % msg)

            self.head.send(reply, 1)

    @staticmethod
    def joe_prog(self: moddy.VSimpleProg):
        while True:
            msg = self.wait_for_msg(None, self.head)
            self.annotation("got message " + msg)

            self.busy(2, "Think")

            if msg == "Hi Joe":
                reply = "Hi, How are you?"
            elif msg == "How are you?":
                reply = "Fine"
            else:
                reply = "Hm?"

            self.head.send(reply, 1.5)


if __name__ == "__main__":
    unittest.main()
