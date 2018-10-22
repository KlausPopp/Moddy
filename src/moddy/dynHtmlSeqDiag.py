'''
Created on 15.10.2018

@author: klauspopp@gmx.de
'''



def moddyGenerateDynamicSequenceDiagram( sim, 
                                         fileName, 
                                         showPartsList=None, 
                                         excludedElementList=[],
                                         showVarList=[],
                                         **kwargs):
    '''
    Moddy high level function to create dynamic sequence diagrams.
    Dynamic sequence diagrams are generated as HTML files containing javascript code
    to dynamically zoom and arrange sequence diagram
    
    sim - the simulator object
    fileName - output filename (including .html)

    showPartsList - if given, show only the listed parts in that order in sequence diagram.
                    Each element can be either a reference to the part or a string with the
                    hierarchy name of the part 
                    if omitted, show all parts known by simulator, in the order of their creation
    
    showVarList -   List of watched variables: Strings with the variable hierarchy name
                    
    excludedElementList - 
                    parts or timers that should be excluded from drawing
                    Each list element can be the object to exclude or one of the following:
                    - 'allTimers' - exclude all timers
                    NOTE: Unlike in showPartsList, strings with hierarchy names are not yet supported

    timeRange - tuple with start and end time. Everything before start and after end is not drawn
    
    **kwargs - further arguments
     title = Sequence Diagram title
     timePerDiv - time per time grid division
     pixPerDiv=25 - pixels per time grid division (start value)
     partSpacing=300 - pixels between parts (start value)
     partBoxSize = (100,60) - x,y pixel size of part box
     statusBoxWidth=20 - pixel width of status box on life line
     variableBoxWidth=150 - pixel width of watched variable value box on life line
     varSpacing = 180 - pixels between variables
    '''
    # Make list of parts to show
    if showPartsList is None:
        allParts = sim._listParts
    else:
        allParts = showPartsList 
    
    partsList = []
    for part in allParts:
        if type(part) is str:
            part = sim.findPartByName(part)
        if part not in excludedElementList:
            partsList.append(part)


    # Make list of variables to show
    varList = []
    for var in showVarList:
        if type(var) is str:
            var = sim.findWatchedVariableByName(var)
        varList.append(var)

    dv = TraceGenDynamicViewer( partsList, varList, **kwargs)
    out = dv.genHeader()
    print(out)
    out = dv.genTraceOutput(sim.tracedEvents())
    print(out)
    
    
    
class TraceGenDynamicViewer(object):
    def __init__(self, partsList, varList, **kwargs ):
        self._listParts = partsList
        self._listVars = varList
        self._listAllParts = self._listParts + self._listVars
        self._kwargs = kwargs;
        self._partShadow = []

        # create object for each part to record current STA/VC values
        for part in self._listAllParts:
            self._partShadow.append( {'current': '', 'lastChange': None})
        
        
        
    def hasPart(self, part):
        ''' Test if simPart is in Drawing '''
        return part in self._listAllParts
    
    def partNo(self, part):
        '''
        Raises ValueError if the part is not present.
        '''
        return self._listAllParts.index( part )

    def shallEventBeShown(self, te):
        if te.action == ">MSG" or te.action == "T-START": return False
        if te.part is None: return True     # global event
        if not self.hasPart(te.part): return False
        if te.action == "<MSG":
            if not self.hasPart(te.subObj._parentObj): return False
        return True     
    
    def genHeader(self):
        out = "g_moddyDiagramArgs = {"
        for key, value in self._kwargs.items():
            out += '%s: %s, ' %(key,value)
        out += '};\n'

        out += "g_moddyDiagramParts = [\n"
        for part in self._listAllParts:
            out += '{ name: "%s", tp: "%s" },\n' % (part.hierarchyName(), 
                                              "Part" if part in self._listParts else "Var")
        out += '];\n'
        
        
        return out
        
            
            
    
    def genTraceOutput(self, evList):
        ''' 
        generate js array with traced events 
        events belonging to parts which are not shown are omitted
        
        General format
        { tp: <typeofentry>, t: <time>, p: <part> } 

        Types:
        { tp: "<MSG",    t:<end-time>, p: <srcPart#>, s: <dstPart#>, b: <begin-time>, txt: <text>, l:t/f}
        { tp: "T-EXP",   t:<time>, p: <part#>, txt: <timername> }
        { tp: "ANN",     t:<time>, p: <part#>, txt: <text> }
        { tp: "ASSFAIL", t:<time>, p: <part#>, txt: <text> }
        { tp: "STA",     t:<time>, p: <part#>, b: <begin-time>, txt: <sta> }
        { tp: "VC",      t:<time>, p: <part#>, b: <begin-time>, txt: <val> }
        
        partNo: 0..n->index of parts from left to right, -1: global
        
         
        '''
        out = "g_moddyTracedEvents = [\n"
        
        for e in evList:
            
            if self.shallEventBeShown(e):
                partNo = self.partNo(e.part)
                
                hdr = '{ tp: "%s", t: %g, p: %d, ' % (
                    e.action, e.traceTime, partNo)
                
                doOutput = False
                mid = ''
            
                if e.action == "<MSG":
                    fireEvent = e.transVal
                    mid = 's: %d, b: %g, txt: "%s", l:%s' % (
                        self.partNo(e.subObj._parentObj),
                        fireEvent.execTime - fireEvent._flightTime,
                        fireEvent._msg,
                        '"t"' if fireEvent._isLost else '"f"')
                    doOutput = True
                        
                elif e.action == "T-EXP":
                    mid = 'txt: "%s"' % (e.subObj.objName())
                    doOutput = True
         
                elif e.action == "ANN" or e.action == "ASSFAIL":
                    mid = 'txt: "%s"' % (e.transVal.__str__())
                    doOutput = True
                    
                elif e.action == "VC" or e.action == "STA":
                    ps = self._partShadow[partNo]
                    currentVal = ps['current']
                    tv = e.transVal.__str__() if e.transVal is not None else ''
                    if currentVal != tv:
                        # generate box for just ended period
                        if currentVal != "" :
                            mid = 'b: %g, txt: "%s"' % (ps['lastChange'], currentVal)
                            doOutput = True
                        #print("%f: p=%d tv=%s currentVal=%s doOutput %s" %(e.traceTime, partNo, tv, currentVal, doOutput))
                        ps['current'] = tv
                        ps['lastChange'] = e.traceTime
                        
                if doOutput:
                    out += hdr + mid + '}, \n'    
        out += '];\n'
        return out
    
            
        
        
        
        
    
    
    