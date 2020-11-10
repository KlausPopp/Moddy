"""
Created on 17.12.2018

@author: klauspopp@gmx.de

Demonstrate remote controlable vThreads

NOTE: It is intended that this demo reports
1) an assertion
2) an exception
To demonstrate what happens if threads throw exceptions or model assertions
"""
import moddy


class myRcThread(moddy.VThread):
    def __init__(self, sim):
        super().__init__(
            sim=sim,
            obj_name="rcThread",
            parent_obj=None,
            remote_controlled=True,
        )
        self.create_ports("QueingIn", ["from_util_port"])
        self.thread_invocation_count = 0

    def run_vthread(self):
        # variables stored in the simPart object (self) are
        # persistant through thread restarts
        self.thread_invocation_count += 1

        self.annotation("invocation %d" % self.thread_invocation_count)
        self.busy(20, "1", moddy.BC_WHITE_ON_GREEN)

        # This shows that arriving messages are lost while the thread is dead
        for _ in range(20):
            self.wait(2)
            while self.from_util_port.n_msg() > 0:
                self.annotation("Got %s" % self.from_util_port.read_msg())

        # In the 4th invocation generate a model assertion failure
        if self.thread_invocation_count == 4:
            self.assertion_failed("4rd invocation assertion")

        # In the 5th invocation simulate an exception.
        # This terminates the thread and the simulator
        if self.thread_invocation_count == 5:
            raise ValueError("Test what happens in case of thread exceptions")

        self.busy(20, "2", moddy.BC_WHITE_ON_BLUE)


def utilThread(self):
    count = 0
    while True:
        self.busy(10, "1", moddy.BC_WHITE_ON_RED)
        self.to_rc_port.send(count, 1)
        count += 1


def stimProg(self):

    # @2s: initial start of rcTread
    self.wait_until(2)
    self.rc_port.send("start", 0)

    # @5s: kill rcThread
    self.wait_until(5)
    self.rc_port.send("kill", 0)

    # @7s: restart rcThread
    self.wait_until(7)
    self.rc_port.send("start", 0)

    # @130s: restart rcThread, it has terminated,
    # because it finished its main loop
    self.wait_until(130)
    self.rc_port.send("start", 0)

    # @180s: kill rcThread
    self.wait_until(180)
    self.rc_port.send("kill", 0)

    # @200s: restart rcThread, it has terminated because it has been killed
    self.wait_until(200)
    self.rc_port.send("start", 0)

    # @290s: restart rcThread, it has terminated because
    # it finished its main loop
    self.wait_until(290)
    self.rc_port.send("start", 0)
    self.wait(70)


if __name__ == "__main__":
    SIMU = moddy.Sim()
    SIMU.tracing.set_display_time_unit("s")

    SCHED = moddy.VtSchedRtos(sim=SIMU, obj_name="sched", parent_obj=None)
    rcThread = myRcThread(SIMU)
    utilThread = moddy.VThread(
        sim=SIMU,
        obj_name="utilThread",
        target=utilThread,
        elems={"out": "to_rc_port"},
    )
    SCHED.add_vthread(rcThread, 0)
    SCHED.add_vthread(utilThread, 1)

    STIM = moddy.VSimpleProg(
        sim=SIMU, obj_name="Stim", target=stimProg, elems={"out": "rc_port"}
    )

    SIMU.smart_bind(
        [
            ["rcThread._thread_control_port", "Stim.rc_port"],
            ["utilThread.to_rc_port", "rcThread.from_util_port"],
        ]
    )

    # let simulator run
    try:
        SIMU.run(stop_time=400, stop_on_assertion_failure=False)

    except Exception:
        raise
    finally:
        # create SVG drawing
        moddy.gen_interactive_sequence_diagram(
            sim=SIMU,
            file_name="output/6_vthread_remote_controlled.html",
            show_parts_list=["utilThread", "rcThread", "Stim"],
            excluded_element_list=["allTimers"],
            title="remote controlled vThreads Demo",
            time_per_div=10,
            pix_per_div=30,
        )
