'''
Basic Moddy demo 

@author: klauspopp@gmx.de
'''

import moddy


class Bob(moddy.SimPart):
    def __init__(self, sim, obj_name):
        # Initialize the parent class
        super().__init__(sim=sim, obj_name=obj_name,
                         elems={'in': 'ears',
                                'out': 'mouth',
                                'tmr': 'think_tmr'})

        self.reply = ""

    def ears_recv(self, port, msg):
        if msg == "Hi, How are you?":
            self.reply = "How are you?"
        else:
            self.reply = "Hm?"

        self.think_tmr.start(1.4)
        self.set_state_indicator("Think")

    def think_tmr_expired(self, timer):
        self.set_state_indicator("")
        self.mouth.send(self.reply, 1)

    def start_sim(self):
        # Let Bob start talking
        self.mouth.send("Hi Joe", 1)


class Joe(moddy.SimPart):
    def __init__(self, sim, obj_name):
        # Initialize the parent class
        super().__init__(sim=sim, obj_name=obj_name,
                         elems={'in': 'ears',
                                'out': 'mouth',
                                'tmr': 'think_tmr'})

        self.reply = ""

    def ears_recv(self, port, msg):
        self.annotation('got message ' + msg)
        if msg == "Hi Joe":
            self.reply = "Hi, How are you?"
        elif msg == "How are you?":
            self.reply = "Fine"
        else:
            self.reply = "Hm?"

        self.think_tmr.start(2)
        self.set_state_indicator("Think")

    def think_tmr_expired(self, timer):
        self.set_state_indicator("")
        self.mouth.send(self.reply, 1.5)


if __name__ == '__main__':
    simu = moddy.Sim()

    bob = Bob(simu, "Bob")
    joe = Joe(simu, "Joe")

    # bind ports
    simu.smart_bind([['Bob.mouth', 'Joe.ears'], ['Bob.ears', 'Joe.mouth']])

    # let simulator run
    simu.run(stop_time=12.0)

    # Output sequence diagram
    moddy.gen_interactive_sequence_diagram(simu,
                                           file_name="output/1_hello.html",
                                           time_per_div=1.0,
                                           pix_per_div=30,
                                           title="Hello Demo")

    # Output model structure graph
    moddy.gen_dot_structure_graph(simu, 'output/1_hello_structure.svg')

    # Output trace table
    moddy.generate_trace_table(simu, 'output/1_hello.csv')
