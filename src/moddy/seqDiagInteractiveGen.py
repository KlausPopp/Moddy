'''
Created on 15.10.2018

@author: klauspopp@gmx.de

TODO 
- timeRange support warning
- support old svg output
'''

import seqDiagInteractiveViewer
from moddy.svgSeqD import moddyGenerateSvgSequenceDiagram
from moddy.utils import moddyCreateDirsAndOpenOutputFile
import os
import sys

def moddyGenerateSequenceDiagram( sim, 
                                  fileName, 
                                  fmt='iaViewer', 
                                  showPartsList=None, 
                                  excludedElementList=[],
                                  showVarList=[],
                                  timeRange=(0,None),
                                  **kwargs):
    '''
    Moddy high level function to create dynamic sequence diagrams.
    Dynamic sequence diagrams are generated as HTML files containing javascript code
    to dynamically zoom and arrange sequence diagram
    
    sim - the simulator object
    fileName - output filename (including .html)
    fmt -         iaViewer         - moddy interactive viewer: HTML with javascript/css embedded
                  iaViewerRef      - moddy interactive viewer: HTML with javascript/css referenced
                  svg              - static SVG (using code in svgSeqD)
                  svgInHtml        - static SVG embedded in HTML (using code in svgSeqD)
                

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
                - currently supported only for svg/svgInHtml
    
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
    
    # call old generator if output shall be svg
    if fmt.startswith( "svg"):
        moddyGenerateSvgSequenceDiagram( sim, fileName, fmt, showPartsList, excludedElementList, showVarList, timeRange, **kwargs) 
        return
    
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


    if timeRange != (0,None):
        print("WARNING: Interactive Viewer does not yet support parameter timeRange", file=sys.stderr)

    outDir = os.path.dirname( fileName )
    dv = TraceGenDynamicViewer( outDir, fmt, partsList, varList, excludedElementList, **kwargs)

    out = dv.genHtmlHead()
    out += dv.getHtmlStyle()
    out += dv.getHtmlMid1()
    
    out += '<script>\n'
    out += dv.genHeader()
    out += dv.genTraceOutput(sim.tracedEvents())
    out += '</script>\n'
    
    out += dv.genScript()
    out += dv.genHtmlTail()
    
    # write file
    f = moddyCreateDirsAndOpenOutputFile(fileName)
    f.write(out)
    f.close()
    print("saved sequence diagram in %s as %s" % (fileName, fmt))


    
class TraceGenDynamicViewer(object):
    def __init__(self, outDir, fmt, partsList, varList, excludedElementList, **kwargs ):
        self._listParts = partsList
        self._listVars = varList
        self._listExcludedElements = excludedElementList
        self._listAllParts = self._listParts + self._listVars
        self._kwargs = kwargs;
        self._partShadow = []
        
        if fmt.endswith("Ref"):
            self.referFiles = True
            self._outDir = outDir       # files are embedded in HTML. reference from HTML output    
        else:
            self.referFiles = False
            self._outDir = ""           # files are embedded in HTML. reference from current dir           

        # create object for each part to record current STA/VC values
        for part in self._listAllParts:
            self._partShadow.append( {'current': '', 'lastChange': None, 
                                      'action': "VC" if part in self._listVars else "STA"})
            
        
        
        
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
        if te.action == "VC":
            if not self.hasPart(te.subObj): return False
        else:    
            if not self.hasPart(te.part): return False
        if te.action == "<MSG":
            if not self.hasPart(te.subObj._parentObj): return False
        return True     
    
    def genHeader(self):
        out = "g_moddyDiagramArgs = {"
        for key, value in self._kwargs.items():
            if type(value) is str:
                out += '%s: "%s", ' %(key,value)
            else:
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
        { tp: "<MSG",    t:<end-time>, p: <srcPart#>, s: <dstPart#>, b: <begin-time>, txt: <text>, l:t/f c:<color>}
        { tp: "T-EXP",   t:<time>, p: <part#>, txt: <timername> }
        { tp: "ANN",     t:<time>, p: <part#>, txt: <text> }
        { tp: "ASSFAIL", t:<time>, p: <part#>, txt: <text> }
        { tp: "STA",     t:<time>, p: <part#>, b: <begin-time>, txt: <sta>, c:<color>, sc:<color>, fc:<color>  }
        { tp: "VC",      t:<time>, p: <part#>, b: <begin-time>, txt: <val>, c:<color>, sc:<color>, fc:<color> }
        
        partNo: 0..n->index of parts from left to right, -1: global
        c: text color (for messages also message color)
        sc: box stroke color
        fc: box fill color 
         
        '''
        vcAppearance = {'boxFillColor':'black', 'boxStrokeColor':'white', 'textColor': 'white'}
        out = "g_moddyTracedEvents = [\n"
        lastEventTs =  None
        
        for e in evList:
            if self.shallEventBeShown(e):
                if e.action == "VC": 
                    partNo = self.partNo(e.subObj)
                else:
                    partNo = self.partNo(e.part)

                hdr = '{ tp: "%s", t: %g, p: %d, ' % (
                    e.action, e.traceTime, partNo)
                
                lastEventTs = e.traceTime
                
                doOutput = False
                mid = ''
            
                # Messages
                if e.action == "<MSG":
                    fireEvent = e.transVal
                    mid = 's: %d, b: %g, txt: "%s", l:%s' % (
                        self.partNo(e.subObj._parentObj),
                        fireEvent.execTime - fireEvent._flightTime,
                        fireEvent.msgText(),
                        '"t"' if fireEvent._isLost else '"f"')
                    
                    # generate colored messages
                    msgColor = None
                    if e.subObj._outPort._color is not None: msgColor = e.subObj._outPort._color
                    if fireEvent._msgColor is not None:
                        msgColor = fireEvent._msgColor
                    if msgColor is not None: mid += ', c:"%s"' % msgColor 
                    
                    doOutput = True
                        
                # Timer event
                elif e.action == "T-EXP":
                    tmr = e.subObj
                    if not tmr in self._listExcludedElements and not 'allTimers' in self._listExcludedElements:
                        mid = 'txt: "%s"' % (e.subObj.objName())
                        doOutput = True
         
                # Annotations
                elif e.action == "ANN" or e.action == "ASSFAIL":
                    mid = 'txt: "%s"' % (e.transVal.__str__())
                    doOutput = True
                    
                # Status
                elif e.action == "VC" or e.action == "STA":

                    ps = self._partShadow[partNo]
                    currentVal = ps['current']
                     
                    
                    tv = e.transVal.__str__() if e.transVal is not None else ''
                    if currentVal != tv:
                        # generate box for just ended period
                        if currentVal != "" :
                            mid = self.staVcOutput(ps['lastChange'], currentVal, ps['currentApp'])
                            doOutput = True
                        #print("%f: p=%d tv=%s currentVal=%s doOutput %s" %(e.traceTime, partNo, tv, currentVal, doOutput))
                        ps['current'] = tv
                        ps['currentApp'] = e.transVal.appearance if e.action == "STA" else vcAppearance
                        ps['lastChange'] = e.traceTime
                        
                if doOutput:
                    out += hdr + mid + '}, \n'    
                    
        # generate a final status event for all parts
        out += "// close STA/VC\n"
        idx = 0
        for ps in self._partShadow:
            if ps['current'] != "" and ps['lastChange'] < lastEventTs:
                out += '{ tp: "%s", t: %g, p: %d, ' % (
                    ps["action"], lastEventTs, idx)
                out += self.staVcOutput(ps['lastChange'], ps['current'], ps['currentApp'])
                out += '}, \n'    
            idx += 1
                    
        out += '];\n'
        return out
    
    def staVcOutput(self, begin, status, appearance ):
        mid = 'b: %g, txt: "%s"' % (begin, status)
        sc,fc,tc = self.boxAppearance(appearance)
        mid += ', c:"%s", fc:"%s", sc:"%s"'%(tc, fc, sc) 
        return mid
    
    def seqDiagInteractiveViewerPath(self):
        ''' get path relative to output directory to the seqDiagInteractiveViewer directory '''
        return os.path.dirname(os.path.relpath(seqDiagInteractiveViewer.__file__, self._outDir))
    
    def readseqDiagInteractiveViewerFile(self, fileName):
        ''' read fileName from seqDiagInteractiveViewer directory and return its content '''
        path = os.path.join(self.seqDiagInteractiveViewerPath(), fileName) 
        file = open( path, 'r' )
        text = file.read()
        file.close
        return text
    
    def genHtmlHead(self):
        return '<html>\n<head>\n<script src="https://d3js.org/d3.v5.min.js"></script>\n';

    def getHtmlStyle(self):
        cssFile = "seqDiagInteractiveViewer.css"
        out = ""
        
        if self.referFiles:
            out += '<link rel="stylesheet" type="text/css" href="%s">\n' % \
            (os.path.join(self.seqDiagInteractiveViewerPath(), cssFile))
        else:
            out += "<style>\n"
            out += self.readseqDiagInteractiveViewerFile(cssFile)
            out += "</style>\n"
        return out

    def getHtmlMid1(self):
        return '''</head>
            <body>
            <div id="controls">
                <div class="slider-wrapper">
                  <input id="ScaleSlider" type="range" min="-2" max="2" value="0" step="any">
                </div>
                <div>
                 <output id="T-Scale">1.00</output>
                </div>
            </div>
            <div id="scrollDummy"></div>
            <div id="title"></div>
            <div id="parts"></div>
            <div id='diagram'></div>\n'''
    
    def genScript(self):
        scriptFile = "seqDiagInteractiveViewer.js"
        out = ""
        
        if self.referFiles:
            out += '<script src="%s"></script>\n' % \
            (os.path.join(self.seqDiagInteractiveViewerPath(), scriptFile))
        else:
            out += "<script>\n"
            out += self.readseqDiagInteractiveViewerFile(scriptFile)
            out += "</script>\n"
            
        # generate code to check alert if browser is not compatible with ECMA6
        out += '''<script>
                if (typeof getDiagramArgs !== "function") {
                    alert("Sorry, your browser does not support ecmascript 6. Please use Chrome, Firefox, Edge...");
                }
                </script>\n'''
        return out
        
    
    def genHtmlTail(self):
        return '</body></html>\n';
    
    def boxAppearance(self, appearance):
        try:                boxStrokeColor  = appearance['boxStrokeColor']  
        except KeyError:    boxStrokeColor  = 'orange'
        try:                boxFillColor    = appearance['boxFillColor']    
        except KeyError:    boxFillColor    = 'white'
        try:                textColor       = appearance['textColor']       
        except KeyError:    textColor       = 'orange'
        return (boxStrokeColor, boxFillColor, textColor)

    
        
        
        
    
    
    