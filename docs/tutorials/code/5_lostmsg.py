"""
@author: klauspopp@gmx.de

Demo for lost messages
"""

import moddy
from moddy import US, MS


def producer_prog(self):
    self.net_port.inject_lost_message_error_by_sequence(2)
    self.net_port.inject_lost_message_error_by_sequence(5)
    self.net_port.inject_lost_message_error_by_sequence(6)
    while True:
        self.wait(100 * US)
        self.net_port.send("test", 100 * US)
        self.busy(100 * US, "TX1", moddy.BC_WHITE_ON_BLUE)
        self.net_port.send("test1", 100 * US)
        self.busy(100 * US, "TX2", moddy.BC_WHITE_ON_RED)
        self.wait(100 * US)
        self.net_port.send("Data1", 100 * US)
        self.busy(100 * US, "TX3", moddy.BC_WHITE_ON_GREEN)


class Consumer(moddy.SimPart):
    def __init__(self, sim):
        super().__init__(sim=sim, obj_name="Consumer", parent_obj=None)
        self.create_ports("in", ["net_port"])

    def net_port_recv(self, port, msg):
        self.annotation("got message " + msg)


if __name__ == "__main__":
    SIMU = moddy.Sim()
    SIMU.tracing.set_display_time_unit("us")

    PROD = moddy.VSimpleProg(
        sim=SIMU,
        obj_name="Producer",
        target=producer_prog,
        elems={"out": "net_port"},
    )
    CONS = Consumer(SIMU)

    PROD.net_port.bind(CONS.net_port)

    # let simulator run
    try:
        SIMU.run(stop_time=3 * MS)

    except Exception:
        raise
    finally:
        # create SVG drawing
        moddy.gen_interactive_sequence_diagram(
            sim=SIMU,
            file_name="output/5_lostMsg.html",
            show_parts_list=["Producer", "Consumer"],
            excluded_element_list=["allTimers"],
            title="Lost Message Demo",
            time_per_div=50 * US,
            pix_per_div=30,
        )

        # Output trace table
        moddy.gen_trace_table(SIMU, "output/5_lostMsg.csv", time_unit="us")
