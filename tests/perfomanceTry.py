'''
Created on 25.12.2018

@author: 

Results: (100000 iterations)

    submsg = Pdu({ "subattr" : 123 }, 10 )
    copyObj = { "submsg": submsg, "idx":0 }
        Test DeepCopy
        Elapsed Time (hh:mm:ss.ms) 0:00:01.222740
        Test Pickle
        Elapsed Time (hh:mm:ss.ms) 0:00:00.523585
        
    submsg = 1
    copyObj = { "submsg": submsg, "idx":0 }
        Test DeepCopy
        Elapsed Time (hh:mm:ss.ms) 0:00:00.449827
        Test Pickle
        Elapsed Time (hh:mm:ss.ms) 0:00:00.191457

'''
import pickle
from datetime import datetime
from collections import deque  
from copy import deepcopy
from models.pacyIon.pdu import Pdu

def copyToFuncPickle( orgObj ):
    return pickle.dumps(orgObj, pickle.HIGHEST_PROTOCOL)

def copyFromFuncPickle( marshalled ):
    return pickle.loads(marshalled)

def copyToFuncDeepCopy( orgObj ):
    return deepcopy(orgObj)

def copyFromFuncDeepCopy( marshalled ):
    return marshalled


def doPerfTestCopy( copyObj, copyToFunc, copyFromFunc ):
    n = 100000
    startTime = datetime.now()
    
    q = deque();
    for _ in range(n):
        copyObj["idx"] += 1
        
        newObj = copyToFunc(copyObj)
        q.append(newObj)
        
    for _ in range(n):
        marshalled = q.popleft()
        resObj = copyFromFunc(marshalled)
        #print("resObj", resObj)
        
    elapsedTime = datetime.now() - startTime
    print("Elapsed Time (hh:mm:ss.ms) {}".format(elapsedTime))
        

if __name__ == '__main__':
    
    #submsg = { "subattr" : 123 }
    #submsg = Pdu({ "subattr" : 123 }, 10 )
    submsg = "Hello World"
    copyObj = { "submsg": submsg, "idx":0 }

    print("Test DeepCopy")
    doPerfTestCopy(copyObj, copyToFuncDeepCopy, copyFromFuncDeepCopy)

    copyObj = { "submsg": submsg, "idx":0 }

    print("Test Pickle")
    doPerfTestCopy(copyObj, copyToFuncPickle, copyFromFuncPickle)
        
        