'''
Export simulator trace to csv

Created on 26.12.2016

@author: Klaus Popp
'''

import csv
from moddy.simulator import timeUnit2Factor

def moddyGenerateTraceTable( sim, fileName, **kwargs):
    '''
    Moddy high level function to create trace tables as .csv.
    sim - the simulator object
    fileName - output filename (including .csv)
    
    **kwargs - further arguments
     timeUnit="s" - time unit for all time stamps in table ('s', 'ms', 'us', 'ns')
     floatComma=',' - Comma character for float numbers
    '''
    trc = TraceToCsv(sim.tracedEvents(),**kwargs)
    trc.save(fileName)


class TraceToCsv():

    def __init__(self, evList, timeUnit="s", floatComma="," ):
        self._evList = evList
        self._timeUnit = timeUnit
        self._timeUnitFactor = timeUnit2Factor(timeUnit)
        self._floatComma = floatComma
         
    def timeFmt(self, time):
        return ("%.6f" % (time / self._timeUnitFactor )).replace(".",self._floatComma)
                 
    def save(self, fileName):
        f = open(fileName, "w")
        
        csv.register_dialect(
            'mydialect',
            delimiter = ';',
            quotechar = '"',
            doublequote = True,
            skipinitialspace = True,
            lineterminator = '\n',
            quoting = csv.QUOTE_MINIMAL)
        
        writer = csv.writer(f, dialect='mydialect')
        
        
        # Write Comment row
        row = ['#time','Action','Object','Port/Tmr','Value','requestTime','startTime','endTime','flightTime']
        writer.writerow(row)
        
        for te in self._evList:
            row = [self.timeFmt(te.traceTime), te.action, te.part.hierarchyName()]
            if te.subObj is not None:
                row.append(te.subObj.hierarchyNameWithType())
            else:
                row.append('')
            if te.transVal is not None:
                if(te.action.find('MSG') != -1):
                    # print request, begin, end, flightTime and msg in separate columns
                    fireEvent = te.transVal
                    row.append(fireEvent._msg)
                    row.append(self.timeFmt(fireEvent._requestTime))
                    row.append(self.timeFmt(fireEvent.execTime - fireEvent._flightTime))
                    row.append(self.timeFmt(fireEvent.execTime))
                    row.append(self.timeFmt(fireEvent._flightTime))
                elif(te.action.find('T-') != -1):
                    timeoutFmt = te.transVal
                    row.append(self.timeFmt(timeoutFmt._timeout))
                else:
                    row.append(te.transVal.__str__())
            else:
                row.append('')
            
            #print("ROW=", row)
            
            
            writer.writerow(row)    
        f.close
        print("saved %s as CSV" % fileName)        
        
        
