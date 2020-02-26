'''
:mod:`traceToCsv` -- Export simulator trace to csv 
=======================================================================

.. module:: traceToCsv
   :synopsis: Export simulator trace to csv
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''

import csv
from .sim_base import time_unit_to_factor
from .utils import create_dirs_and_open_output_file


def moddyGenerateTraceTable( sim, fileName, **kwargs):
    '''
    Moddy high level function to create trace tables as .csv.
    
    :param sim sim: Simulator instance
    :param fileName: output filename (including .csv)
    
    :param \**kwargs: further arguments
     
     * timeUnit="s" - time unit for all time stamps in table ('s', 'ms', 'us', 'ns')
     * floatComma=',' - Comma character for float numbers
    '''
    trc = TraceToCsv(sim.tracing.traced_events(),**kwargs)
    trc.save(fileName)


class TraceToCsv():

    def __init__(self, evList, timeUnit="s", floatComma="," ):
        self._evList = evList
        self._timeUnit = timeUnit
        self._timeUnitFactor = time_unit_to_factor(timeUnit)
        self._floatComma = floatComma
         
    def timeFmt(self, time):
        return ("%.6f" % (time / self._timeUnitFactor )).replace(".",self._floatComma)
                 
    def save(self, fileName):
        f = create_dirs_and_open_output_file(fileName)
        
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
            row = [self.timeFmt(te.trace_time), te.action]
            if te.part is None:
                p = 'Global'
            else:
                p = te.part.hierarchy_name()
            row.append(p)
            
            if te.sub_obj is not None:
                row.append(te.sub_obj.hierarchy_name_with_type())
            else:
                row.append('')
            if te.trans_val is not None:
                if(te.action.find('MSG') != -1):
                    # print request, begin, end, flightTime and msg in separate columns
                    fireEvent = te.trans_val
                    row.append("(***LOST***)" if fireEvent.is_lost else 
                               fireEvent.msg_text())
                    row.append(self.timeFmt(fireEvent._request_time))
                    row.append(self.timeFmt(fireEvent.exec_time - 
                                            fireEvent.flight_time))
                    row.append(self.timeFmt(fireEvent.exec_time))
                    row.append(self.timeFmt(fireEvent.flight_time))
                elif(te.action.find('T-') != -1):
                    timeoutFmt = te.trans_val
                    row.append(self.timeFmt(timeoutFmt._timeout))
                else:
                    row.append(te.trans_val.__str__())
            else:
                row.append('')
            
            #print("ROW=", row)
            
            
            writer.writerow(row)    
        f.close
        print("saved %s as CSV" % fileName)        
        
        
