'''
@author: klauspopp@gmx.de

The Moddy 1_hello demo modelled using Moddy sequential programs
'''

from moddy import *

def bobProg(self: vSimpleProg):
    # bob starts talking
    self.head.send("Hi Joe", 1)
    
    while True:
        msg = self.waitForMsg(None, self.head)
        self.addAnnotation('got message ' + msg)
        
        self.busy( 1.4, 'Think')
        
        if msg == "Hi, How are you?":
            reply = "How are you?"
        else:
            reply = "Hm?"

        self.head.send(reply, 1)
        
        
def joeProg(self: vSimpleProg):
    while True:
        msg = self.waitForMsg(None, self.head)
        self.addAnnotation('got message ' + msg)
        
        self.busy( 2, 'Think')
        
        if msg == "Hi Joe":
            reply = "Hi, How are you?"
        elif msg == "How are you?":
            reply = "Fine"
        else:
            reply = "Hm?"


        self.head.send(reply, 1.5)


if __name__ == '__main__':
    SIMU = sim()
    
    vSimpleProg( sim=SIMU, objName="Bob", target=bobProg, elems={ 'QueuingIO': 'head' } )
    vSimpleProg( sim=SIMU, objName="Joe", target=joeProg, elems={ 'QueuingIO': 'head' } )
    
    SIMU.smartBind([ ['Bob.head', 'Joe.head'] ])

    # let simulator run
    SIMU.run(stopTime=12.0)
    
    # Output sequence diagram
    moddyGenerateSequenceDiagram( sim=SIMU, 
                                  fileName="output/8_helloProgram.html", 
                                  fmt="iaViewer", 
                                  showPartsList=['Bob', 'Joe'], 
                                  timePerDiv = 1.0, 
                                  pixPerDiv = 30,
                                  title = "Hello Program Demo")    

    # Output model structure graph
    moddyGenerateStructureGraph(SIMU, 'output/8_hello_structure.svg')

