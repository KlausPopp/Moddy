'''
Created on 15.09.2019

@author: klauspopp@gmx.de
'''
from moddy.simulator import sim, simTraceEvent
import fnmatch
from reportlab.platypus import para

class TraceSearch(object):
    '''
    Class to search moddy traced events
    '''


    def __init__(self, sim):
        self.sim = sim
        self.tracedEvents = sim.tracedEvents()
        self.curIdx = 0
        



    
    def findAnn(self, part, textPat, startIdx=None):
        '''
        find next Annotation 
        :param string textPat: text pattern with wildcards. If None, matches any text
        other parameters and return, see findEvent
        '''
        return self.findEvent(part, startIdx, self.tvStrMatch, ("ANN",textPat))
            
    def findAssFail(self, part, textPat, startIdx=None):
        '''
        find next Assertion Failure 
        :param string textPat: text pattern with wildcards. If None, matches any text
        other parameters and return, see findEvent
        '''
        return self.findEvent(part, startIdx, self.tvStrMatch, ("ASSFAIL",textPat))

    def findSta(self, part, textPat, startIdx=None):
        '''
        find next Status event 
        :param string textPat: text pattern with wildcards. If None, matches any text
        other parameters and return, see findEvent
        '''
        return self.findEvent(part, startIdx, self.tvStrMatch, ("STA",textPat))

    def findRcvMsg(self, part, textPat, startIdx=None):
        '''
        find next received message by text pattern on message string representation 
        "part" is the part receiving the message
        :param string textPat: message text with wildcards. If None, matches any 
        other parameters and return, see findEvent
        '''
        return self.findEvent(part, startIdx, self.msgMatch, ("<MSG", textPat), 
                              partMatcher=self.subPartParentMatch)

    def findSndMsg(self, part, textPat, startIdx=None):
        '''
        find next sent message by text pattern on message string representation 
        "part" is the part sending the message
        :param string textPat: message text with wildcards. If None, matches any 
        other parameters and return, see findEvent
        '''
        return self.findEvent(part, startIdx, self.msgMatch, (">MSG", textPat),
                              partMatcher=self.subPartParentMatch)
    
    def findVc(self, varWatcher, textPat, startIdx=None):
        '''
        find next value change event by text pattern 
        "varChanger" must be the varWatcher instance (hierarchy name not supported!)
        :param string textPat: message text with wildcards. If None, matches any 
        other parameters and return, see findEvent
        '''
        return self.findEvent(varWatcher, startIdx, self.tvStrMatch, ("VC", textPat),
                              partMatcher=self.subPartMatch)
    
    
    def tvStrMatch(self, para, te):
        mType, textPat = para
        rv = False
        if te.action == mType:
            if self.wildcardMatch(te.transVal.__str__(), textPat):
                rv = True
        return rv

    def msgMatch(self, para, te):
        mType, textPat = para
        rv = False
        if te.action == mType:
            if self.wildcardMatch(te.transVal.msgText(), textPat):
                rv = True
        return rv
        
    def findEvent(self, part, startIdx, matchFunc, matchFuncPara, partMatcher=None):
        '''
        find next traced event
        :param part: part hierarchy name or instance. If None, match any part
            This is passed to partMatcher. So, depending on partMatcher, it can be
            a part, a part hierarchy name, or a subpart
        :param startIdx: index in tracedEvents to start with (use curIdx if None)
        :param partMatcher: function to call to check if trace event matches part
            if None, use partMatch(te,p)
        :return: idx, te=the index and found event or None 
        :raises ValueError: if part name not found
        '''
        if partMatcher is None: partMatcher = self.partMatch
        idx = startIdx if startIdx is not None else self.curIdx
        part = self.partTranslate(part)

        rv = None
        for idx in range(idx, len(self.tracedEvents)):
            te = self.tracedEvents[idx]
            #print("COMPARING te %d: %s" % (idx, te))
            #if te.part == part or self.subPartMatch(part, te):
            if partMatcher(te, part):
                if matchFunc( matchFuncPara, te ):
                    rv = (idx,te)
                    break
        self.curIdx = idx + 1    
        return rv
    
    @staticmethod
    def partMatch(te, p):
        return te.part == p
        
    @staticmethod
    def subPartParentMatch( te, p):
        subpart = te.subObj
        if subpart is None: return False
        
        return subpart._parentObj == p

    @staticmethod
    def subPartMatch( te, p):
        return te.subObj == p
        
    def partTranslate(self, part):
        '''
        :param part: part hierarchy name or instance. If None, match any part
        :return part instance
        :raises ValueError: if part name not found
        '''
        if type(part) is str:
            part = self.sim.findPartByName(part)
        return part
        
    def wildcardMatch(self, txt, pattern):
        return pattern is None or fnmatch.fnmatch(txt, pattern)


    