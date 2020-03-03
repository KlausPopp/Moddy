'''
Basic Moddy demo

@author: klauspopp@gmx.de

Note: the "pylint: disable=no-member" are necessary because moddy creates
port/timer members automatically, so they are not visible to pylint
'''
# because the filename doesn't conform to snake case style ...
# pylint: disable=C0103

import moddy


class Bob(moddy.SimPart):
    ''' Model of Bob '''
    def __init__(self, sim, obj_name):
        # Initialize the parent class
        super().__init__(sim=sim, obj_name=obj_name,
                         elems={'in': 'ears',
                                'out': 'mouth',
                                'tmr': 'think_tmr'})

        self.reply = ""

    def ears_recv(self, _, msg):
        ''' Callback for message reception on ears port '''
        if msg == "Hi, How are you?":
            self.reply = "How are you?"
        else:
            self.reply = "Hm?"

        # pylint: disable=no-member
        self.think_tmr.start(1.4)
        self.set_state_indicator("Think")

    def think_tmr_expired(self, _):
        ''' Callback for think_tmr expiration '''
        self.set_state_indicator("")
        # pylint: disable=no-member
        self.mouth.send(self.reply, 1)

    def start_sim(self):
        # Let Bob start talking
        # pylint: disable=no-member
        self.mouth.send("Hi Joe", 1)


class Joe(moddy.SimPart):
    ''' Model of Joe '''
    def __init__(self, sim, obj_name):
        # Initialize the parent class
        super().__init__(sim=sim, obj_name=obj_name,
                         elems={'in': 'ears',
                                'out': 'mouth',
                                'tmr': 'think_tmr'})

        self.reply = ""

    def ears_recv(self, _, msg):
        ''' Callback for message reception on ears port '''
        self.annotation('got message ' + msg)
        if msg == "Hi Joe":
            self.reply = "Hi, How are you?"
        elif msg == "How are you?":
            self.reply = "Fine"
        else:
            self.reply = "Hm?"

        # pylint: disable=no-member
        self.think_tmr.start(2)
        self.set_state_indicator("Think")

    def think_tmr_expired(self, _):
        ''' Callback for think_tmr expiration '''
        self.set_state_indicator("")
        # pylint: disable=no-member
        self.mouth.send(self.reply, 1.5)


if __name__ == '__main__':
    SIMU = moddy.Sim()

    Bob(SIMU, "Bob")
    Joe(SIMU, "Joe")

    # bind ports
    SIMU.smart_bind([['Bob.mouth', 'Joe.ears'], ['Bob.ears', 'Joe.mouth']])

    # let simulator run
    SIMU.run(stop_time=12.0)

    # Output sequence diagram
    moddy.gen_interactive_sequence_diagram(SIMU,
                                           file_name="output/1_hello.html",
                                           time_per_div=1.0,
                                           pix_per_div=30,
                                           title="Hello Demo")

    # Output model structure graph
    moddy.gen_dot_structure_graph(SIMU, 'output/1_hello_structure.svg')

    # Output trace table
    moddy.gen_trace_table(SIMU, 'output/1_hello.csv')
