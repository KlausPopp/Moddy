"""
:mod:`trace_to_csv` -- Export simulator trace to csv
=======================================================================

.. module:: trace_to_csv
   :synopsis: Export simulator trace to csv
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

"""

import csv
from .sim_base import time_unit_to_factor
from .utils import create_dirs_and_open_output_file


def gen_trace_table(sim, file_name, **kwargs):
    """
    Moddy high level function to create trace tables as .csv.

    :param sim sim: Simulator instance
    :param file_name: output filename (including .csv)

    :param \*\*kwargs: further arguments

     * time_unit="s" - time unit for all time stamps in table \
         ('s', 'ms', 'us', 'ns')
     * float_comma=',' - Comma character for float numbers
    
    """
    trc = TraceToCsv(sim.tracing.traced_events(), **kwargs)
    trc.save(file_name)


class TraceToCsv:
    # pylint: disable=too-few-public-methods
    """ class to generate csv trace table """

    def __init__(self, ev_list, time_unit="s", float_comma=","):
        self._ev_list = ev_list
        self._time_unit = time_unit
        self._time_unit_factor = time_unit_to_factor(time_unit)
        self._float_comma = float_comma

    def _time_fmt(self, time):
        return ("%.6f" % (time / self._time_unit_factor)).replace(
            ".", self._float_comma
        )

    def save(self, file_name):
        """ save the trace file """
        trace_file = create_dirs_and_open_output_file(file_name)

        csv.register_dialect(
            "mydialect",
            delimiter=";",
            quotechar='"',
            doublequote=True,
            skipinitialspace=True,
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )

        writer = csv.writer(trace_file, dialect="mydialect")

        # Write Comment row
        row = [
            "#time",
            "Action",
            "Object",
            "Port/Tmr",
            "Value",
            "requestTime",
            "startTime",
            "endTime",
            "flightTime",
        ]
        writer.writerow(row)

        for trace_ev in self._ev_list:
            row = [self._time_fmt(trace_ev.trace_time), trace_ev.action]
            if trace_ev.part is None:
                part = "Global"
            else:
                part = trace_ev.part.hierarchy_name()
            row.append(part)

            if trace_ev.sub_obj is not None:
                row.append(trace_ev.sub_obj.hierarchy_name_with_type())
            else:
                row.append("")
            if trace_ev.trans_val is not None:
                if trace_ev.action.find("MSG") != -1:
                    # print request, begin, end, flightTime and
                    # msg in separate columns
                    fire_event = trace_ev.trans_val
                    row.append(
                        "(***LOST***)"
                        if fire_event.is_lost
                        else fire_event.msg_text()
                    )
                    row.append(self._time_fmt(fire_event.request_time))
                    row.append(
                        self._time_fmt(
                            fire_event.exec_time - fire_event.flight_time
                        )
                    )
                    row.append(self._time_fmt(fire_event.exec_time))
                    row.append(self._time_fmt(fire_event.flight_time))
                elif trace_ev.action.find("T-") != -1:
                    timeout_fmt = trace_ev.trans_val
                    row.append(self._time_fmt(timeout_fmt.timeout))
                else:
                    row.append(trace_ev.trans_val.__str__())
            else:
                row.append("")

            # print("ROW=", row)

            writer.writerow(row)
        trace_file.close()
        print("saved trace table to %s" % file_name)
