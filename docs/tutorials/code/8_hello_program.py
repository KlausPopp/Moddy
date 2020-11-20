"""
@author: klauspopp@gmx.de

The Moddy 1_hello demo modelled using Moddy sequential programs
"""

import moddy


def bob_prog(self: moddy.VSimpleProg):
    # bob starts talking
    self.head.send("Hi Joe", 1)

    while True:
        msg = self.wait_for_msg(None, self.head)
        self.anotation("got message " + msg)

        self.busy(1.4, "Think")

        if msg == "Hi, How are you?":
            reply = "How are you?"
        else:
            reply = "Hm?"

        self.head.send(reply, 1)


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
    SIMU = moddy.Sim()

    moddy.VSimpleProg(
        sim=SIMU, obj_name="Bob", target=bob_prog, elems={"QueuingIO": "head"}
    )
    moddy.VSimpleProg(
        sim=SIMU, obj_name="Joe", target=joe_prog, elems={"QueuingIO": "head"}
    )

    SIMU.smart_bind([["Bob.head", "Joe.head"]])

    # let simulator run
    SIMU.run(stop_time=12.0)

    # Output sequence diagram
    moddy.gen_interactive_sequence_diagram(
        sim=SIMU,
        file_name="output/8_helloProgram.html",
        show_parts_list=["Bob", "Joe"],
        time_per_div=1.0,
        pix_per_div=30,
        title="Hello Program Demo",
    )

    # Output model structure graph
    moddy.gen_dot_structure_graph(SIMU, "output/8_hello_structure.svg")
