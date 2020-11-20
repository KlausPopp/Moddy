"""
test binding of multiple output ports to a single input port
@author: klauspopp@gmx.de
"""

import moddy
from moddy import MS, US


def producer_prog(self):
    self.net_port2.set_color("blue")
    while True:
        self.wait(100 * US)
        self.net_port1.send("test1a", 100 * US)
        self.net_port2.send("test2a", 100 * US)
        self.busy(100 * US, "TX1", moddy.BC_WHITE_ON_BLUE)
        self.net_port1.send("test1b", 100 * US)
        self.busy(100 * US, "TX1", moddy.BC_WHITE_ON_BLUE)
        self.net_port2.send("test2b", 100 * US)


def consumer_prog(self):
    while True:
        msg = self.wait_for_msg(timeout=None, ports=self.net_port)
        self.annotation("got message " + msg)


if __name__ == "__main__":
    SIMU = moddy.Sim()
    SIMU.tracing.set_display_time_unit("us")

    PROD = moddy.VSimpleProg(
        sim=SIMU,
        obj_name="Producer",
        target=producer_prog,
        elems={"out": ["net_port1", "net_port2"]},
    )
    CONS = moddy.VSimpleProg(
        sim=SIMU,
        obj_name="Consumer",
        target=consumer_prog,
        elems={"QueuingIn": "net_port"},
    )

    # bind two output ports to same input port
    SIMU.smart_bind(
        [["Producer.net_port1", "Producer.net_port2", "Consumer.net_port"]]
    )

    # let simulator run
    try:
        SIMU.run(stop_time=3 * MS)

    except Exception:
        raise
    finally:
        # create sequence diagram
        moddy.gen_interactive_sequence_diagram(
            sim=SIMU,
            file_name="output/7_multiPortBinding.html",
            fmt="iaViewer",
            show_parts_list=["Producer", "Consumer"],
            excluded_element_list=["allTimers"],
            title="Multi Port Binding",
            time_per_div=50 * US,
            pix_per_div=30,
        )
        # Output model structure graph
        moddy.gen_dot_structure_graph(
            SIMU, "output/7_multiPortBinding_structure.svg"
        )
