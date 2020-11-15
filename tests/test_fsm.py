"""
Created on 25.12.2018

@author: klauspopp@gmx.de
"""
import unittest
import moddy
from tests.utils import (
    searchInMsg,
    searchAnn,
    searchSta,
    baseFileName,
    funcName,
)


class TestFsm(unittest.TestCase):
    """
    Test the moddy FSM with sub-fsms
    """

    class CarInfoSystem(moddy.SimFsmPart):
        def __init__(self, sim, obj_name):
            status_box_repr_map = {
                "Off": (None, moddy.BC_BLACK_ON_WHITE),
                "Standby": ("SBY", moddy.BC_WHITE_ON_RED),
                "Booting": ("BOOT", moddy.BC_WHITE_ON_BLUE),
                "NormalOp": ("NORM", moddy.BC_WHITE_ON_GREEN),
                "Shutdown": ("SD", moddy.BC_WHITE_ON_RED),
            }

            super().__init__(
                sim=sim,
                obj_name=obj_name,
                fsm=self.FSM(),
                status_box_repr_map=status_box_repr_map,
            )

            # Ports & Timers
            self.create_ports(
                "in", ["powerPort", "ignitionPort", "buttonPort"]
            )
            self.create_ports("out", ["audioPort", "visualPort"])
            self.create_timers(["bootTmr", "shutdownTmr", "clockTmr"])

        class FSM(moddy.Fsm):
            def __init__(self):

                transitions = {
                    "": [("INITIAL", "Off")],  # FSM uninitialized
                    "Off": [("PowerApplied", "Standby")],
                    "Standby":
                    # This transition is triggered whenever ANY message arrives on the powerButtonPort
                    [("PowerButton", "Booting"), ("IgnitionOn", "Booting")],
                    "Booting": [("bootTmr_expired", "NormalOp")],
                    "NormalOp":
                    # The following two lines specify nested state machines, executing in parallel
                    [
                        ("Apps", TestFsm.CarInfoSystem.FSM.ApplicationsFsm),
                        ("Vol", TestFsm.CarInfoSystem.FSM.VolumeFsm),
                        # This transition is triggered whenever ANY message arrives on the powerButtonPort
                        ("PowerButton", "Shutdown"),
                        ("IgnitionOff", "Shutdown"),
                        # This transition is triggered whenever clockTmr expires, transition to self,
                        # executes the 'Do' methode
                        ("clockTmr_expired", "NormalOp"),
                    ],
                    "Shutdown": [("shutdownTmr_expired", "Standby")],
                    "ANY": [("PowerRemoved", "Off")],
                }

                super().__init__(dict_transitions=transitions)

            # Off actions
            def state_Off_entry(self):
                print("State_Off_Entry")
                self.moddy_part().bootTmr.stop()
                self.moddy_part().shutdownTmr.stop()
                self.moddy_part().clockTmr.stop()

            # Booting actions
            def state_Booting_entry(self):
                print("Booting_Entry")
                self.moddy_part().bootTmr.start(5)

            # Shutdown actions
            def state_Shutdown_entry(self):
                self.moddy_part().shutdownTmr.start(2)

            # Cursor Blink in NormalOp state
            def state_NormalOp_entry(self):
                self._clockTime = 100

            def state_NormalOp_do(self):
                self.moddy_part().clockTmr.start(5)
                self.moddy_part().visualPort.send(
                    "time %d" % self._clockTime, 0.1
                )
                self._clockTime += 5

            # Message handlers
            def state_any_powerPort_msg(self, msg):
                if msg == "on":
                    self.event("PowerApplied")
                elif msg == "off":
                    self.event("PowerRemoved")

            def state_any_ignitionPort_msg(self, msg):
                if msg == "on":
                    self.event("IgnitionOn")
                elif msg == "off":
                    self.event("IgnitionOff")

            def state_any_buttonPort_msg(self, msg):
                self.event(msg)  # Message are directly the event names

            # Nested state machine CarInfo System Applications
            class ApplicationsFsm(moddy.Fsm):
                def __init__(self, parentFsm):

                    transitions = {
                        "": [("INITIAL", "Radio")],
                        "Radio": [("NaviButton", "Navi")],
                        "Navi": [("RadioButton", "Radio")],
                    }

                    super().__init__(
                        dict_transitions=transitions, parent_fsm=parentFsm
                    )

                def state_Radio_entry(self):
                    self.moddy_part().annotation("Radio activated")

                def state_Navi_entry(self):
                    self.moddy_part().annotation("Navi activated")

            class VolumeFsm(moddy.Fsm):
                def __init__(self, parentFsm):
                    self._volume = 50

                    transitions = {
                        "": [("INITIAL", "On")],
                        "On": [
                            ("MuteButton", "Mute"),
                            ("VolKnobRight", "IncVol"),
                            ("VolKnobLeft", "DecVol"),
                        ],
                        "IncVol": [("VolChangeDone", "On")],
                        "DecVol": [("VolChangeDone", "On")],
                        "Mute": [("MuteButton", "On"), ("VolKnobRight", "On")],
                    }

                    super().__init__(
                        dict_transitions=transitions, parent_fsm=parentFsm
                    )

                def state_On_do(self):
                    self.moddy_part().audioPort.send(
                        "volume=%d" % self._volume, 0.1
                    )

                def state_Mute_do(self):
                    self.moddy_part().audioPort.send("volume=%d" % 0, 0.1)

                def state_IncVol_entry(self):
                    self._volume += 1
                    self.top_fsm().event("VolChangeDone")

                def state_DecVol_entry(self):
                    self._volume -= 1
                    self.top_fsm().event("VolChangeDone")

    class Stim(moddy.VSimpleProg):
        def __init__(self, sim):
            super().__init__(sim=sim, obj_name="Stim", parent_obj=None)
            self.create_ports(
                "out", ["powerPort", "ignitionPort", "buttonPort"]
            )
            self.create_ports("SamplingIn", ["audioPort", "visualPort"])
            self.ignitionPort.set_color("red")
            self.buttonPort.set_color("blue")

        def run_vthread(self):
            while True:
                self.powerPort.send("on", 1)
                self.wait(2)
                self.buttonPort.send("PowerButton", 1)
                self.wait(8)
                self.buttonPort.send("NaviButton", 0.5)
                self.wait(2)
                self.buttonPort.send("VolKnobRight", 0.5)
                self.buttonPort.send("VolKnobRight", 0.5)
                self.wait(1)
                self.buttonPort.send("VolKnobLeft", 0.5)
                self.wait(1)
                self.buttonPort.send("MuteButton", 0.5)
                self.wait(1)
                self.buttonPort.send("VolKnobRight", 0.5)
                self.wait(5)
                self.ignitionPort.send("off", 1)
                self.wait(2)
                self.powerPort.send("off", 1)
                self.wait(None)

    def testCarInfo(self):
        simu = moddy.Sim()
        cis = TestFsm.CarInfoSystem(simu, "CarInfoSys")
        stim = TestFsm.Stim(simu)

        # bind ports
        stim.powerPort.bind(cis.powerPort)
        stim.ignitionPort.bind(cis.ignitionPort)
        stim.buttonPort.bind(cis.buttonPort)
        cis.visualPort.bind(stim.visualPort)
        cis.audioPort.bind(stim.audioPort)

        simu.run(100)

        moddy.gen_interactive_sequence_diagram(
            sim=simu,
            file_name="output/%s_%s.html" % (baseFileName(), funcName()),
            show_parts_list=[stim, cis],
            time_per_div=0.3,
            pix_per_div=30,
            title="Car Info FSM Test",
        )

        trc = simu.tracing.traced_events()

        # check CarInfo Main states
        self.assertEqual(searchSta(trc, 1.0, cis), "SBY")
        self.assertEqual(searchSta(trc, 3.0, cis), "BOOT")
        self.assertEqual(searchSta(trc, 8.0, cis), "NORM")
        self.assertEqual(searchSta(trc, 21.0, cis), "SD")

        self.assertEqual(searchAnn(trc, 8.0, cis), "Radio activated")
        self.assertEqual(searchAnn(trc, 10.5, cis), "Navi activated")

        self.assertEqual(searchInMsg(trc, 12.6, stim.audioPort), "volume=51")
        self.assertEqual(searchInMsg(trc, 13.1, stim.audioPort), "volume=52")
        self.assertEqual(searchInMsg(trc, 14.6, stim.audioPort), "volume=0")

        self.assertEqual(searchInMsg(trc, 18.1, stim.visualPort), "time 110")


if __name__ == "__main__":
    unittest.main()