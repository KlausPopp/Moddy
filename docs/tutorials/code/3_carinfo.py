"""
Simulate the behavior of a (extremely simplified) car infotainment system.

The main state is simulated with a Moddy Finite state machine.
(off, booting, normal   op etc).
The normal state has several nested sub-state machines, such as

 'Apps' (Radio, Navi) - jumps between the different applications
   (in this simulation, the apps have no function)

 'Volume' - manages the audio volume

The Stim part simulates user events.

@author: klauspopp@gmx.de

"""

import moddy


class CarInfoSystem(moddy.SimFsmPart):
    """ Simulation of Car infotainment """

    def __init__(self, sim, obj_name):
        status_box_repr_map = {
            "off": (None, moddy.BC_BLACK_ON_WHITE),
            "standby": ("SBY", moddy.BC_WHITE_ON_RED),
            "booting": ("BOOT", moddy.BC_WHITE_ON_BLUE),
            "normal_op": ("NORM", moddy.BC_WHITE_ON_GREEN),
            "shutdown": ("SD", moddy.BC_WHITE_ON_RED),
        }

        super().__init__(
            sim=sim,
            obj_name=obj_name,
            fsm=self.FSM(),
            status_box_repr_map=status_box_repr_map,
        )

        # Ports & Timers
        self.create_ports("in", ["power_port", "ignition_port", "button_port"])
        self.create_ports("out", ["audio_port", "visual_port"])
        self.create_timers(["boot_tmr", "shutdown_tmr", "clock_tmr"])

    class FSM(moddy.Fsm):
        """ State machine of car infotainment """

        def __init__(self):

            transitions = {
                "": [("INITIAL", "off")],  # FSM uninitialized
                "off": [("PowerApplied", "standby")],
                # This transition is triggered whenever ANY message arrives
                # on the powerButtonPort
                "standby": [
                    ("PowerButton", "booting"),
                    ("IgnitionOn", "booting"),
                ],
                "booting": [("boot_tmr_expired", "normal_op")],
                "normal_op":
                # The following two lines specify nested state machines,
                # executing in parallel
                [
                    ("Apps", CarInfoSystem.FSM.ApplicationsFsm),
                    ("Vol", CarInfoSystem.FSM.VolumeFsm),
                    # This transition is triggered whenever ANY message
                    # arrives on the powerButtonPort
                    ("PowerButton", "shutdown"),
                    ("IgnitionOff", "shutdown"),
                    # This transition is triggered whenever clockTmr expires,
                    # transition to self,
                    # executes the 'Do' methode
                    ("clock_tmr_expired", "normal_op"),
                ],
                "shutdown": [("shutdown_tmr_expired", "standby")],
                "any": [("PowerRemoved", "off")],
            }

            super().__init__(dict_transitions=transitions)

        # off actions
        def state_off_entry(self):
            print("state_off_entry")
            self.moddy_part().boot_tmr.stop()
            self.moddy_part().shutdown_tmr.stop()
            self.moddy_part().clock_tmr.stop()

        # booting actions
        def state_booting_entry(self):
            print("booting_entry")
            self.moddy_part().boot_tmr.start(5)

        # shutdown actions
        def state_shutdown_entry(self):
            self.moddy_part().shutdown_tmr.start(2)
            self.moddy_part().clock_tmr.stop()

        # Cursor Blink in normal_op state
        def state_normal_op_entry(self):
            self._clockTime = 100

        def state_normal_op_do(self):
            self.moddy_part().clock_tmr.start(5)
            self.moddy_part().visual_port.send(
                "time %d" % self._clockTime, 0.1
            )
            self._clockTime += 5

        # Message handlers
        def state_any_power_port_msg(self, msg):
            if msg == "on":
                self.event("PowerApplied")
            elif msg == "off":
                self.event("PowerRemoved")

        def state_any_ignition_port_msg(self, msg):
            if msg == "on":
                self.event("IgnitionOn")
            elif msg == "off":
                self.event("IgnitionOff")

        def state_any_button_port_msg(self, msg):
            self.event(msg)  # Message are directly the event names

        # Nested state machine CarInfo System Applications
        class ApplicationsFsm(moddy.Fsm):
            def __init__(self, parentFsm):

                transitions = {
                    "": [("INITIAL", "radio")],
                    "radio": [("NaviButton", "navi")],
                    "navi": [("RadioButton", "radio")],
                }

                super().__init__(
                    dict_transitions=transitions, parent_fsm=parentFsm
                )

            def state_radio_entry(self):
                self.moddy_part().annotation("Radio activated")

            def state_navi_entry(self):
                self.moddy_part().annotation("Navi activated")

        class VolumeFsm(moddy.Fsm):
            def __init__(self, parentFsm):
                self._volume = 50

                transitions = {
                    "": [("INITIAL", "on")],
                    "on": [
                        ("MuteButton", "mute"),
                        ("VolKnobRight", "incvol"),
                        ("VolKnobLeft", "decvol"),
                    ],
                    "incvol": [("VolChangeDone", "on")],
                    "decvol": [("VolChangeDone", "on")],
                    "mute": [("MuteButton", "on"), ("VolKnobRight", "on")],
                }

                super().__init__(
                    dict_transitions=transitions, parent_fsm=parentFsm
                )

            def state_on_do(self):
                self.moddy_part().audio_port.send(
                    "volume=%d" % self._volume, 0.1
                )

            def state_mute_do(self):
                self.moddy_part().audio_port.send("volume=%d" % 0, 0.1)

            def state_incvol_entry(self):
                self._volume += 1
                self.top_fsm().event("VolChangeDone")

            def state_decvol_entry(self):
                self._volume -= 1
                self.top_fsm().event("VolChangeDone")


def stimProg(self):
    self.ignition_port.set_color("red")
    self.button_port.set_color("blue")
    while True:
        self.power_port.send("on", 1)
        self.wait(2)
        self.button_port.send("PowerButton", 1)
        self.wait(8)
        self.button_port.send("NaviButton", 0.5)
        self.wait(2)
        self.button_port.send("VolKnobRight", 0.5)
        self.button_port.send("VolKnobRight", 0.5)
        self.wait(1)
        self.button_port.send("VolKnobLeft", 0.5)
        self.wait(1)
        self.button_port.send("MuteButton", 0.5)
        self.wait(1)
        self.button_port.send("VolKnobRight", 0.5)
        self.wait(5)
        self.ignition_port.send("off", 1)
        self.wait(4)
        self.power_port.send("off", 1)
        self.wait(None)


if __name__ == "__main__":
    SIMU = moddy.Sim()
    CIS = CarInfoSystem(SIMU, "CarInfoSys")
    STIM = moddy.VSimpleProg(
        sim=SIMU,
        obj_name="Stim",
        target=stimProg,
        elems={
            "out": ["power_port", "ignition_port", "button_port"],
            "SamplingIn": ["audio_port", "visual_port"],
        },
    )

    # bind ports
    SIMU.smart_bind(
        [
            ["Stim.power_port", "CarInfoSys.power_port"],
            ["Stim.ignition_port", "CarInfoSys.ignition_port"],
            ["Stim.button_port", "CarInfoSys.button_port"],
            ["Stim.visual_port", "CarInfoSys.visual_port"],
            ["Stim.audio_port", "CarInfoSys.audio_port"],
        ]
    )

    moddy.gen_fsm_graph(
        fsm=CIS.fsm, file_name="output/3_carinfo_fsm.svg", keep_gv_file=True
    )

    SIMU.run(30)

    moddy.gen_interactive_sequence_diagram(
        sim=SIMU,
        file_name="output/3_carinfo.html",
        show_parts_list=[STIM, CIS],
        time_per_div=0.3,
        pix_per_div=30,
        title="Car Info FSM Demo",
    )
