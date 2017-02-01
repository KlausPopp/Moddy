'''

Export simulator results as a sequence diagram.
Use scalable vector graphics (svg) for sequence diagrams

Created on 18.12.2016

@author: Klaus Popp

TODO Inkskape Zoom factor wrong when no size in svg
TODO Auto place text to avoid overlap(!)
TODO Group the objects (e.g. message arrow)
'''
import svgwrite
from math import *
from moddy import ms,us,ns
from moddy.simulator import sim

_fontStyle = "font: 9pt Verdana, Helvetica, Arial, sans-serif"


def moddyGenerateSequenceDiagram( sim, fileName, fmt='svg', excludedElementList=[], **kwargs):
    '''
    Moddy high level function to create sequence diagrams.
    sim - the simulator object
    fileName - output filename (including .svg or .html)
    fmt - either 'svg' for pure SVG or 'svgInHtml' for SVG embedded in HTML
    excludedElementList - parts or timers that should be excluded from drawing
    
    **kwargs - further arguments, see svgSeqD constructor for details
     timePerDiv - time per time grid division
     pixPerDiv=25 - pixels per time grid division
     partSpacing=300 - pixels between parts
     partBoxSize = (100,60) - x,y pixel size of part box
     statusBoxWidth=20 - pixel width of status box on life line
    '''
    sd = svgSeqD( evList=sim.tracedEvents(), **kwargs )
    
    # Get all parts from simulator. Exlude only those in excludedElementList
    partsList = []
    for part in sim._listParts:
        if part not in excludedElementList:
            partsList.append(part)

    sd.addParts(partsList)
    
    for elem in excludedElementList:
        sd.hide(elem)
    
    sd.draw()
    sd.save(fileName, fmt)


class SdPart(object):
    ''' An object of this class is created for each part the user wants to show '''
    def __init__(self, simPart, sdAction ):
        self.simPart = simPart
        self.sdPos = None                  # Tuple (x,y) of the Parts Box upper left edge
        self.sdLifeLineX = None            # XPos of parts lifeline
        self.sdAction = sdAction
        self.sdActionTime = 0

        
class svgSeqD(object):
    '''
    Create a Sequence Diagram with SVG 
    '''
    #
    # Public methods
    #
    
    def __init__(self, evList, 
                 timePerDiv, 
                 pixPerDiv=25, 
                 partSpacing=300, 
                 partBoxSize = (100,60),
                 statusBoxWidth=20 ):  
        '''
        Create SVG sequence diagram
        '''
        self.partBoxSize = partBoxSize
        self.partSpacing = partSpacing  # horizontal space between block object rects
        self.firstPartOffset = (100,10)
        self.statusBoxWidth = statusBoxWidth
        self._disTimeScale = 1
        self._listParts = []
        self._dictParts = {}            # dictionary that maps the simulator part name to SdParts
        self._listHiddenElements = []    # list of hidden elements (timers, ports)   
        self._evList = evList
         
        self._rightMostPartX = 0           # right border of rightmost part. Computed by drawparts
        self._maxY = 0
   
        
        self.pixPerSecond = pixPerDiv / timePerDiv                # pixels per second
        self.timeMarkEach = timePerDiv                 # draw time mark each ...                     

        if( timePerDiv >= 1.0): unit="s"
        elif(timePerDiv >= ms): unit="ms"
        elif(timePerDiv >= us): unit="ms"
        else: unit="ns" 
        self.setTimeUnit(unit)

        #print("timePerDiv", timePerDiv, "pixPerSecond", self.pixPerSecond)

        d = svgwrite.Drawing()
        self._d = d
    
        
    def save(self, fileName, fmt="svg"):
        ''' 
        Save the drawing to <fileName> with <fmt>
        Supported values for <fmt>:
        "svg" - pure svg
        'svgInHtml" - svg embedded in HTML
        '''
        if(fmt=="svg"): self.saveSvg(fileName)
        elif(fmt=="svgInHtml"): self.saveSvgInHtml(fileName)
        else: raise AttributeError("format %s not supported." % fmt)
        print("saved %s as %s" % (fileName, fmt))

    def hasPart(self, simPart):
        ''' Test if simPart is in Drawing '''
        return simPart in self._listParts
    
    def simPartMap(self, simPart):
        ''' Map simPart to sdPart. Raise KeyError if simPart is not in drawing '''
        return self._dictParts[simPart.hierarchyName()]

    def addParts(self, partList):
        ''' add list of parts to drawing. '''
        for part in partList:
            self._listParts.append(part)
            self._dictParts[part.hierarchyName()] = SdPart( part, sim.StateIndTransVal("",{})) 
        
    def currentDrawingYPos(self):
        ''' return the highest Y Pos on cancas that was used for drawing so far '''
        return self._maxY
    
    def drawParts(self):
        '''
        Draw the part boxes for all registered parts
        return lower right corner of drawn area
        '''
        x = self.firstPartOffset[0]
        for b in self._listParts:
            sdPart = self.simPartMap(b)
            sdPart.sdPos = ( x, self.firstPartOffset[1] )
            sdPart.sdLifeLineX = x + self.partBoxSize[0]/2
            x += self.partSpacing
            self.partBox(sdPart.sdPos, b.hierarchyName())
            
        self._rightMostPartX = x
        self._maxY = self.partBoxSize[1] + self.firstPartOffset[1]

    def drawTimeRange(self, startTime, endTime, areaStartY):
        '''
        Draw the events that are between <startTime> and <endTime>
        <endTime> can be None, then endTime goes to last event
        Drawing begins on canvas at areaStartY
        '''
        endTime = self.latestEvent(endTime)
        #print("endTime", endTime)
        
        assert(endTime >= startTime)
        areaHeight = (endTime - startTime) * self.pixPerSecond
         
        # draw life lines
        for b in self._listParts:
            self.lifeLine((self.simPartMap(b).sdLifeLineX, areaStartY) , areaHeight)
        
        # draw time markers
        self.drawTimeMarkers(startTime, endTime, areaStartY)
            
        # draw events (in right order, so that most important info is in front
        self.drawAllSelectedEvents(startTime, endTime, areaStartY, 'STA');
        self.drawEndObjStatus(startTime,endTime,areaStartY) # draw 
        self.drawAllSelectedEvents(startTime, endTime, areaStartY, '<MSG');
        self.drawAllSelectedEvents(startTime, endTime, areaStartY, 'T-EXP');
        self.drawAllSelectedEvents(startTime, endTime, areaStartY, 'ANN');
        
        self._maxY = self.timeYPos( endTime, startTime, areaStartY )
        
    def draw(self, startTime=0, endTime=None):
        ''' Draw the parts and the specified time range '''
        self.drawParts()
        self.drawTimeRange(startTime, endTime, self.currentDrawingYPos())

    def hide(self, element):
        '''Exclude an element from being drawn. E.g. timer'''
        self._listHiddenElements.append(element)
        
    #
    # Internal methods
    #
    def saveSvg(self, fileName):
        '''Save drawing as pure SVG file. This enables you to modify the drawing via inkscape or visio'''
        self._d.filename = fileName
        self._d.save()

    def saveSvgInHtml(self, fileName):
        '''Save drawing to HTML file which embedds the SVG in a <div>. This enables browsers to scroll the svg drawing'''
        htmlHead = """
        <html>
        <style type="text/css">
        #divid
        {
         position:absolute;
         overflow:scroll;
         width: %d;
         height: %d;
        }
        </style>
            <body>
                <div id="divid">
        """
        htmlTail = """
                </div>
            </body>
        </html>
        """
        f = open(fileName, 'w')
        f.write(htmlHead %(self._rightMostPartX + 200, self.currentDrawingYPos() + 200) + self._d.tostring() + htmlTail)
        f.close()
    
    def setTimeUnit(self,unit):
        """Define how the simulator prints/displays time units
        scale can be "s", "ms", "us", "ns"
        """
        if unit=="s":      self._disTimeScale = 1
        elif unit == "ms": self._disTimeScale = ms
        elif unit == "us": self._disTimeScale = us
        elif unit == "ns": self._disTimeScale = ns
        else: assert(False),"Illegal time unit"
        self._disTimeUnit = unit

    def partBox(self, insertPos, partName):
        '''
        Create a swim lane for part with <partName>
        Create Box with name and life line
        <insertPos> is the left upper absolute position on the canvas
        '''
        d = self._d
        
        d.add( d.rect(insert = insertPos,
                            size = (str(self.partBoxSize[0]), str(self.partBoxSize[1])),
                            stroke_width = "1",
                            stroke = "black",
                            fill = "none"))
        d.add(d.text(partName, insert = (insertPos[0]+10, insertPos[1]+20), style=_fontStyle))

    def annotation(self,insertPos, text):
        d = self._d
        d.add(d.text(text, insert = (insertPos[0]+22,insertPos[1]), fill="red", style=_fontStyle))
        d.add(d.line(start=insertPos, end=(insertPos[0]+20,insertPos[1]-4), stroke="red"))

    def lifeLine(self, insertPos, height):
        '''
        Create life line 
        insertPos is the absolute upper pos on the canvas.  
        '''
        d = self._d
        d.add( d.line(start=insertPos, end=(insertPos[0], insertPos[1]+height)).stroke("black").dasharray([5,5])) 

    def _arrowHeadLine(self, startPos, endPos, angle, length):
        
        x0 = startPos[0]
        y0 = startPos[1]
        x1 = endPos[0]
        y1 = endPos[1]

        dx = x1 - x0
        dy = y1 - y0
        
        theta = atan2(dy, dx)
        rad = radians(angle)
        x = x1 - length * cos(theta + rad)
        y = y1 - length * sin(theta + rad)
         
        return (x,y)

    def msgLine(self, startPos, endPos, msgText, color="black", showText=True, showLine=True):
        '''
        Create a message line with an arrow at the end
        startPos and endPos are absolute on canvas
        '''
        d = self._d
        if showLine is True:
            l= d.line(start=startPos, end=endPos).stroke(color)  
            d.add(l)
            
            # compute the arrow 
            angle = 18
            arrowLen = 15
            d.add(d.line(start=endPos, end=self._arrowHeadLine(startPos, endPos, angle, arrowLen)).stroke(color))  
            d.add(d.line(start=endPos, end=self._arrowHeadLine(startPos, endPos, -angle, arrowLen)).stroke(color))  
                
        if showText is True:
            # compute text position
            yOffs = +5
    
            dx = endPos[0]-startPos[0]
            dy = endPos[1]-startPos[1]
            textPos = (startPos[0] + dx/2, (startPos[1] + dy/2) - yOffs)
            t = d.text(msgText, insert = textPos, fill=color, text_anchor="middle", style=_fontStyle)
            alpha= degrees(atan(dy/dx))
            t.rotate(str(alpha) + "," + str(textPos[0]) + "," + str(textPos[1]))
            d.add(t)
        
    def timeMarkerLine(self, startPos, width, timeText):
        '''
        Create a horizontal time marker line
        startPos is absolute on canvas
        '''
        d = self._d
        d.add(d.line(start=(startPos[0]+self.firstPartOffset[0],startPos[1]), end=(startPos[0]+width, startPos[1]), stroke_width = "0.2").stroke("grey"))
        d.add(d.text(timeText, insert = (startPos[0]+self.firstPartOffset[0]-10, startPos[1]+4), style=_fontStyle, text_anchor="end"))

    def statusBox(self, upperLeft, size, text, appearance={}):
        '''
        Draw status indicator box on life line with the text in vertical direction
        
        The default appearance is orange border, solid white background and orange text.
        You can override with <appearance> as dictionary. e.g.{ 'boxFillColor':'blue', 'textColor': 'white'} 
        '''
        try:                boxStrokeColor  = appearance['boxStrokeColor']  
        except KeyError:    boxStrokeColor  = 'orange'
        try:                boxFillColor    = appearance['boxFillColor']    
        except KeyError:    boxFillColor    = 'white'
        try:                textColor       = appearance['textColor']       
        except KeyError:    textColor       = 'orange'
        
        d = self._d
        
        d.add( d.rect(insert = upperLeft,
                            size = size,
                            stroke_width = "1",
                            stroke = boxStrokeColor,
                            fill = boxFillColor))
        textPos = (upperLeft[0]+5, upperLeft[1] )
        if size[1] > 15:
            # only add text if there is a miminum of space
            t = d.text(text, insert = textPos, style=_fontStyle)
            t.rotate(str("90") + "," + str(textPos[0]) + "," + str(textPos[1]))
            t.fill(textColor)
            d.add(t)
        #print(t.tostring())
        

        
    def timeStr(self,time):
        """return a formatted time string of <time> based on the display scale"""
        tmfmt = "%.1f" % (time / self._disTimeScale)
        return tmfmt + self._disTimeUnit

    
    def timeYPos(self, time, areaStartTime, areaStartY):
        return ((time - areaStartTime) * self.pixPerSecond)+areaStartY
    

    def drawMsg(self, e, areaStartTime, areaStartY):
        fromPart = e.part
        toPart = e.subObj._parentObj
        assert(fromPart != toPart)
        #print("drawMsg", e.traceTime, fromPart.objName(), toPart.objName())
        # draw only if both Parts have been added to sd
        if self.hasPart(fromPart) and self.hasPart(toPart):
            msgColor = "black"
            # Take the color of the output port sending this message
            if e.subObj._outPort._color is not None:
                msgColor = e.subObj._outPort._color
                        
            fireEvent = e.transVal
            # if message specifies a specific color, take this color
            if hasattr(fireEvent._msg, 'msgColor'):
                msgColor = fireEvent._msg.msgColor
            
            start = ( self.simPartMap(fromPart).sdLifeLineX, self.timeYPos( fireEvent.execTime - fireEvent._flightTime, areaStartTime, areaStartY ))
            end = ( self.simPartMap(toPart).sdLifeLineX, self.timeYPos( fireEvent.execTime, areaStartTime, areaStartY ))
            if( start[1] >= areaStartY):
                # only show line if it begins within the current area
                self.msgLine(start, end, fireEvent._msg.__str__(), color=msgColor)
            elif end[1] >= areaStartY:
                # message line only Partly on the area. Show only the Part in the area
                # Don't show message text
                dx = end[0]-start[0]
                dy = end[1]-start[1]
                start = (end[0] - ( ((end[1]-areaStartY)/dy) * dx), areaStartY)
                self.msgLine(start, end, fireEvent._msg.__str__(), showText=False, color=msgColor)
    
    def drawTmrExp(self, e, areaStartTime, areaStartY):
        part = e.part
        tmr = e.subObj
        #print("drawTmrExp", e.traceTime, part.objName())
        # draw only if both parts have been added to sd
        if self.hasPart(part) and not tmr in self._listHiddenElements: 
            end = ( self.simPartMap(part).sdLifeLineX, self.timeYPos( e.traceTime, areaStartTime, areaStartY ))
            start = ( end[0]-50, end[1])
            if( start[1] >= areaStartY):
                self.msgLine(start, end, tmr.objName(), color="blue")
        
    def drawAnnotation(self, e, areaStartTime, areaStartY):
        part = e.part
        #print("drawAnn", e.traceTime, e.transVal)
        if self.hasPart(part):
            pos = ( self.simPartMap(part).sdLifeLineX, self.timeYPos( e.traceTime, areaStartTime, areaStartY ))
            if( pos[1] >= areaStartY):
                self.annotation(pos, e.transVal)
        
    def drawObjStatus(self, e, areaStartTime, areaStartY):
        part = e.part
        #print("drawAct", e.traceTime, e.transVal)
        if self.hasPart(part):
            sdPart = self.simPartMap(part)
            ind = sdPart.sdAction
            if ind.text != "":
                minTime = sdPart.sdActionTime
                if( minTime < areaStartTime):
                    minTime = areaStartTime
                upperLeft = ( sdPart.sdLifeLineX - self.statusBoxWidth/2, self.timeYPos( minTime, areaStartTime, areaStartY ))
                size = (self.statusBoxWidth, (e.traceTime - minTime) * self.pixPerSecond)
                self.statusBox(upperLeft, size, ind.text, ind.appearance)
            sdPart.sdAction = e.transVal
            sdPart.sdActionTime = e.traceTime
    
    def drawEndObjStatus(self,areaStartTime,areaEndTime,areaStartY):
        # on each part, draw a status box from the last event to the end of the area
        for part in self._listParts:
            sdPart = self.simPartMap(part)
            #print("drawEndObjStatus %s %s" % (part.objName(), sdPart.sdAction))
            ind = sdPart.sdAction
            if ind.text != "":
                minTime = sdPart.sdActionTime
                if( minTime < areaStartTime):
                    minTime = areaStartTime
                upperLeft = ( sdPart.sdLifeLineX - self.statusBoxWidth/2, self.timeYPos( minTime, areaStartTime, areaStartY ))
                size = (self.statusBoxWidth, (areaEndTime - minTime) * self.pixPerSecond)
                self.statusBox(upperLeft, size, ind.text, ind.appearance)
             
    
    def drawEvent(self, e, areaStartTime, areaStartY):
        #print("drawEvent", e.action)
        if e.action == "<MSG": self.drawMsg(e, areaStartTime, areaStartY )
        elif e.action == "T-EXP": self.drawTmrExp(e, areaStartTime, areaStartY )
        elif e.action == "ANN": self.drawAnnotation(e, areaStartTime, areaStartY)
        elif e.action == "STA": self.drawObjStatus(e, areaStartTime, areaStartY)
    
    def drawAllSelectedEvents(self, startTime, endTime, areaStartY, action):
        print( "Drawing", action, "events") 
        for e in self._evList:
            if e.traceTime <= endTime and e.action == action:
                self.drawEvent( e, startTime, areaStartY)        
        
    def drawTimeMarkers(self, startTime, endTime, areaStartY):
        # draw time markers scale
        if (startTime % self.timeMarkEach) == 0:
            startMarkers = startTime
        else:
            startMarkers = startTime + self.timeMarkEach - (startTime % self.timeMarkEach)
        t = startMarkers
        assert(self._rightMostPartX != 0),"drawParts not called yet?"
        assert(self.timeMarkEach * self.pixPerSecond > 20),"Time markers too tight"
        while t <= endTime:
            self.timeMarkerLine((0, self.timeYPos( t, startTime, areaStartY )), self._rightMostPartX, self.timeStr(t))
            t += self.timeMarkEach
         
         
    def latestEvent(self, endTime):
        '''find the latest event <= endTime. If endTime is None, find last event'''
        if endTime is None:
            last = self._evList[-1].traceTime
        else:
            last = None
            for e in self._evList:
                if e.traceTime <= endTime:
                    last = e.traceTime
            if last is None:
                last = self._evList[-1].traceTime
        return last 
            
            
    