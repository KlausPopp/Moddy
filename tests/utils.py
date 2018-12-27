'''
Created on 26.12.2018

@author: klauspopp@gmx.de

Some utils used in tests
'''

import traceback
def funcName():
    stack = traceback.extract_stack()
    filename, codeline, funcName, text = stack[-2]
    return funcName
def searchTrc( trc, time, subObj, action, nthMatch=1):
    nMatches = 0
    for e in trc:
        #print("searchTrc %f %s %s" % (e.traceTime, e.subObj.hierarchyName(), e.action))
        if e.traceTime == time and e.subObj == subObj and e.action == action:
            nMatches += 1
            if nMatches == nthMatch:
                return e
    return None    
    
def searchInMsg(trc, time, port, nthMatch=1):
    e = searchTrc( trc, time, port, "<MSG", nthMatch)
    if e is None: raise RuntimeError("searchInMsg not found")
    return e.transVal.msgText()

def searchAnn(trc, time, part, nthMatch=1):
    e = searchTrc( trc, time, part, "ANN", nthMatch)
    if e is None: raise RuntimeError("searchAnn not found")
    return e.transVal.__str__()

def searchSta(trc, time, part, nthMatch=1):
    e = searchTrc( trc, time, part, "STA", nthMatch)
    if e is None: raise RuntimeError("searchSta not found")
    return e.transVal.__str__()

def searchTExp(trc, time, subObj, nthMatch=1):
    e = searchTrc( trc, time, subObj, "T-EXP", nthMatch)
    if e is None: raise RuntimeError("searchTExp not found")
    return True
        