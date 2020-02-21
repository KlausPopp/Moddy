'''
Basic Moddy demo 

@author: klauspopp@gmx.de
'''

import moddy


class Bob(moddy.simPart):
    def __init__(self, sim, objName):
        # Initialize the parent class
        super().__init__(sim=sim, objName=objName,
                         elems={'in': 'ears',
                                'out': 'mouth',
                                'tmr': 'thinkTmr'})

        self.reply = ""

    def earsRecv(self, port, msg):
        if msg == "Hi, How are you?":
            self.reply = "How are you?"
        else:
            self.reply = "Hm?"

        self.thinkTmr.start(1.4)
        self.setStateIndicator("Think")

    def thinkTmrExpired(self, timer):
        self.setStateIndicator("")
        self.mouth.send(self.reply, 1)

    def startSim(self):
        # Let Bob start talking
        self.mouth.send("Hi Joe", 1)


class Joe(moddy.simPart):
    def __init__(self, sim, objName):
        # Initialize the parent class
        super().__init__(sim=sim, objName=objName,
                         elems={'in': 'ears',
                                'out': 'mouth',
                                'tmr': 'thinkTmr'})

        self.reply = ""

    def earsRecv(self, port, msg):
        self.addAnnotation('got message ' + msg)
        if msg == "Hi Joe":
            self.reply = "Hi, How are you?"
        elif msg == "How are you?":
            self.reply = "Fine"
        else:
            self.reply = "Hm?"

        self.thinkTmr.start(2)
        self.setStateIndicator("Think")

    def thinkTmrExpired(self, timer):
        self.setStateIndicator("")
        self.mouth.send(self.reply, 1.5)


if __name__ == '__main__':
    simu = moddy.sim()

    bob = Bob(simu, "Bob")
    joe = Joe(simu, "Joe")

    # bind ports
    simu.smartBind([['Bob.mouth', 'Joe.ears'], ['Bob.ears', 'Joe.mouth']])

    # let simulator run
    simu.run(stopTime=12.0)

    # Output sequence diagram
    moddy.moddyGenerateSequenceDiagram(sim=simu,
                                 fileName="output/1_hello.html",
                                 fmt="iaViewer",
                                 excludedElementList=[],
                                 timePerDiv=1.0,
                                 pixPerDiv=30,
                                 title="Hello Demo")

    # Output model structure graph
    moddy.moddyGenerateStructureGraph(simu, 'output/1_hello_structure.svg')

    # Output trace table
    moddy.moddyGenerateTraceTable(simu, 'output/1_hello.csv')
