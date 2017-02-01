'''
Created on 23.12.2016

@author: klaus
'''

from moddy import *

class Bob(simPart):
    def __init__(self, sim, objName):
        # Initialize the parent class
        super().__init__(sim=sim, objName=objName)

        # Ports
        self.createPorts('in', ['ears'])
        self.createPorts('out', ['mouth'])

        # Timers
        self.createTimers(['thinkTmr'])
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


class Joe(simPart):
    def __init__(self, sim, objName):
        # Initialize the parent class
        super().__init__(sim=sim, objName=objName)

        # Ports
        self.createPorts('in', ['ears'])
        self.createPorts('out', ['mouth'])

        # Timers
        self.createTimers(['thinkTmr'])    
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
    simu = sim()
    
    bob    = Bob( simu, "Bob" )
    joe    = Joe( simu, "Joe" )
    
    # bind ports
    bob.mouth.bind(joe.ears)
    joe.mouth.bind(bob.ears)

    # Let Bob start talking
    bob.mouth.send("Hi Joe", 1)
    
    # let simulator run
    simu.run(stopTime=12.0)
    
    # create SVG drawing
    moddyGenerateSequenceDiagram( sim=simu, 
                                  fileName="1_hello.html", 
                                  fmt="svgInHtml", 
                                  excludedElementList=[], 
                                  timePerDiv = 1.0, 
                                  pixPerDiv = 30)    

    # Output model structure graph
    moddyGenerateStructureGraph(simu, '1_hello_structure.svg')
    
    # Output trace table
    moddyGenerateTraceTable(simu, '1_hello.csv' )

