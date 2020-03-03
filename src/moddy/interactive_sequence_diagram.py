'''
:mod:`interactive_sequence_diagram` -- Interactive Sequence Diagram Generator
==============================================================================

.. module:: interactive_sequence_diagram
   :platform: Unix, Windows
   :synopsis: Moddy Interactive Sequence Diagram Generator
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>

'''

import os

from moddy import seq_diag_interactive_viewer
from moddy.constants import BC_WHITE_ON_BLACK
from .utils import create_dirs_and_open_output_file


def gen_interactive_sequence_diagram(sim,
                                     file_name,
                                     show_parts_list=None,
                                     excluded_element_list=None,
                                     show_var_list=None,
                                     refer_files=False,
                                     **kwargs):
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    '''
    Moddy function to create sequence diagrams.
    The function is supposed to be called after the simulator has stopped.
    It takes the recorded events from the simulator instance.

    Depending on the `fmt` parameter, either dynamic or static diagrams are
    generated.

    :param sim sim: Simulator instance
    :param str file_name: output filename (including filename extension \
        ``.html``)

    :param list show_parts_list: if given, show only the listed parts
                    in that order in sequence diagram.
                    Each element can be either a reference to the part or
                    a string with the
                    hierarchy name of the part.
                    if omitted, show all parts known by simulator,
                    in the order of their creation

    :param list show_var_list: List of watched variables to include in
                    the sequence diagram.
                    Each element must be a string with the variable hierarchy
                    name. event.g. "VC.var1".
                    If omitted, no variables are included.

    :param list excluded_element_list: parts or timers that should be
                    excluded from drawing
                    Each list element can be the object to exclude or one
                    of the following:
                    - 'allTimers' - exclude all timers

                    NOTE: Unlike in show_parts_list, strings with hierarchy
                    names are not yet supported

    :param refer_files: Include references to .css and .js file instead
                    of including them

    :param \\**kwargs: further arguments

         * title - Title text to be displayed above the sequence diagram
         * timePerDiv - time per "Time Div".

         * pixPerDiv=25 - pixels per time grid division. Optional, default:25.
           Note: The interactive viewer dynamically adjust the time scale
           depending on the current time
           scale factor and uses *
           timePerDiv* and *pixPerDiv* only as an
           hint for the initial scale factor.

         * partSpacing=300 - horizontal spacing in pixels between parts.
           (start value)

         * partBoxSize = (100,60) - Tupel with x,y pixel size of part box.
           Note: The interactive viewer dynamically adjust the part box
           size according
           to the length of the part names.

         * statusBoxWidth=20 - pixel width of status box on life line

         * variableBoxWidth=150 - pixel width of watched variable value box
           on life line

         * varSpacing = 180 - pixels between variables

    '''
    if excluded_element_list is None:
        excluded_element_list = []

    if show_var_list is None:
        show_var_list = []

    # Make list of parts to show
    if show_parts_list is None:
        all_parts = list(sim.parts_mgr.walk_parts())
    else:
        all_parts = show_parts_list

    parts_list = []
    for part in all_parts:
        if isinstance(part, str):
            part = sim.parts_mgr.find_part_by_name(part)
        if part not in excluded_element_list:
            parts_list.append(part)

    # Make list of variables to show
    var_list = []
    for var in show_var_list:
        if isinstance(var, str):
            var = sim.var_watch_mgr.find_watched_variable_by_name(var)
        var_list.append(var)

    out_dir = os.path.dirname(file_name)
    viewer = TraceGenDynamicViewer(out_dir, parts_list, var_list,
                                   excluded_element_list, refer_files,
                                   **kwargs)

    out = viewer.gen_html_head()
    out += viewer.get_html_style()
    out += viewer.get_html_mid_1()

    out += '<script>\n'
    out += viewer.gen_header()
    out += viewer.gen_trace_output(sim.tracing.traced_events())
    out += '</script>\n'

    out += viewer.gen_script()
    out += viewer.gen_html_tail()

    # write file
    file = create_dirs_and_open_output_file(file_name)
    file.write(out)
    file.close()
    print("saved sequence diagram in %s" % (file_name))


class TraceGenDynamicViewer:
    # pylint: disable=too-many-instance-attributes
    '''
    Class to generate the different elements of the HTML file
    for the dynamic viewer
    '''

    def __init__(self, outDir, parts_list, var_list,
                 excluded_element_list, refer_files, **kwargs):
        # pylint: disable=too-many-arguments
        self._list_parts = parts_list
        self._list_vars = var_list
        self._list_excluded_elements = excluded_element_list
        self._refer_files = refer_files
        self._list_all_parts = self._list_parts + self._list_vars
        self._kwargs = kwargs
        self._part_shadow = []

        if refer_files:
            # files are embedded in HTML. reference from HTML output
            self._out_dir = outDir
        else:
            # files are embedded in HTML. reference from current dir
            self._out_dir = ""

        # create object for each part to record current STA/VC values
        for part in self._list_all_parts:
            self._part_shadow.append(
                {
                    'current': '',
                    'lastChange': None,
                    'action': "VC" if part in self._list_vars else "STA"
                })

    def has_part(self, part):
        ''' Test if simPart is in Drawing '''
        return part in self._list_all_parts

    def part_no(self, part):
        '''
        Raises ValueError if the part is not present.
        '''
        return self._list_all_parts.index(part)

    def _shall_event_be_shown(self, trace_ev):
        if trace_ev.action == ">MSG" or trace_ev.action == "T-START":
            return False
        if trace_ev.part is None:
            return True  # global event
        if trace_ev.action == "VC":
            if not self.has_part(trace_ev.sub_obj):
                return False
        else:
            if not self.has_part(trace_ev.part):
                return False
        if trace_ev.action == "<MSG":
            if not self.has_part(trace_ev.sub_obj.parent_obj):
                return False
        return True

    def gen_header(self):
        '''
        Generate js header with moddyDiagramArgs and
        moddyDiagramParts
        '''
        camel_case_map = {
            'time_per_div': 'timePerDiv',
            'pix_per_div': 'pixPerDiv',
            'part_spacing': 'partSpacing',
            'part_box_size': 'partBoxSize',
            'status_box_width': 'statusBoxWidth',
            'variable_box_width': 'variableBoxWidth',
            'var_spacing': 'varSpacing',
        }

        out = "g_moddyDiagramArgs = {"
        for key, value in self._kwargs.items():
            # convert to camelcase key (js program still uses camel case)
            key = camel_case_map.get(key, key)

            if isinstance(value, str):
                out += '%s: "%s", ' % (key, value)
            else:
                out += '%s: %s, ' % (key, value)

        out += '};\n'

        out += "g_moddyDiagramParts = [\n"
        for part in self._list_all_parts:
            out += '{ name: "%s", tp: "%s" },\n' % \
                (part.hierarchy_name(),
                 "Part" if part in self._list_parts else "Var")
        out += '];\n'

        return out

    def gen_trace_output(self, ev_list):
        '''
        generate js array with traced events
        events belonging to parts which are not shown are omitted

        General format
        { tp: <typeofentry>, t: <time>, p: <part> }

        Types:
        { tp: "<MSG",    t:<end-time>, p: <srcPart#>, s: <dstPart#>,
            b: <begin-time>, txt: <text>, l:t/f c:<color>}
        { tp: "T-EXP",   t:<time>, p: <part#>, txt: <timername> }
        { tp: "ANN",     t:<time>, p: <part#>, txt: <text> }
        { tp: "ASSFAIL", t:<time>, p: <part#>, txt: <text> }
        { tp: "STA",     t:<time>, p: <part#>, b: <begin-time>,
            txt: <sta>, c:<color>, sc:<color>, fc:<color>  }
        { tp: "VC",      t:<time>, p: <part#>, b: <begin-time>,
            txt: <val>, c:<color>, sc:<color>, fc:<color> }

        part_no: 0..n->index of parts from left to right, -1: global
        c: text color (for messages also message color)
        sc: box stroke color
        fc: box fill color

        '''
        out = "g_moddyTracedEvents = [\n"
        last_event_ts = None

        for event in ev_list:
            if self._shall_event_be_shown(event):
                last_event_ts = event.trace_time

                output = self._gen_output_for_event(event)
                if output is not None:
                    out += output

        # generate a final status event for all parts
        out += self._gen_closing_sta(last_event_ts)
        out += '];\n'
        return out

    def _gen_output_for_event(self, event):
        if event.action == "VC":
            part_no = self.part_no(event.sub_obj)
        else:
            part_no = self.part_no(event.part)

        hdr = '{ tp: "%s", t: %g, p: %d, ' % (
            event.action, event.trace_time, part_no)

        mid = None

        dispatch = {
            '<MSG':     self._gen_output_for_msg_event,
            'T-EXP':    self._gen_output_for_tmr_event,
            'ANN':      self._gen_output_for_ann_event,
            'ASSFAIL':  self._gen_output_for_ann_event,
            'STA':      self._gen_output_for_sta_event,
            'VC':       self._gen_output_for_sta_event,
        }

        try:
            mid = dispatch[event.action](event, part_no)
        except KeyError:
            mid = None

        if mid:
            out = hdr + mid + '}, \n'
            return out
        return None

    def _gen_output_for_msg_event(self, event, _):
        fire_event = event.trans_val
        mid = 's: %d, b: %g, txt: "%s", l:%s' % (
            self.part_no(event.sub_obj.parent_obj),
            fire_event.exec_time - fire_event.flight_time,
            fire_event.msg_text(),
            '"t"' if fire_event.is_lost else '"f"')

        # generate colored messages
        msg_color = None
        if fire_event.port.color is not None:
            msg_color = fire_event.port.color

        if fire_event.msg_color is not None:
            msg_color = fire_event.msg_color

        if msg_color is not None:
            mid += ', c:"%s"' % msg_color

        return mid

    def _gen_output_for_tmr_event(self, event, _):
        mid = None
        tmr = event.sub_obj
        if tmr not in self._list_excluded_elements and \
                'allTimers' not in self._list_excluded_elements:
            mid = 'txt: "%s"' % (event.sub_obj.obj_name())
        return mid

    @staticmethod
    def _gen_output_for_ann_event(event, _):
        return 'txt: "%s"' % (event.trans_val.__str__())

    def _gen_output_for_sta_event(self, event, part_no):
        vc_appearance = BC_WHITE_ON_BLACK
        mid = None
        shadow = self._part_shadow[part_no]
        current_val = shadow['current']

        trans_val = event.trans_val.__str__() if event.trans_val is not None \
            else ''

        if current_val != trans_val:
            # generate box for just ended period
            if current_val != "":
                # print(shadow['currentApp'])
                mid = self._sta_vc_output(shadow['lastChange'],
                                          current_val,
                                          shadow['currentApp'])
            # print("%f: p=%d trans_val=%s current_val=%s do_output %s"
            # %(event.trace_time, part_no, trans_val, current_val, do_output))
            shadow['current'] = trans_val
            shadow['currentApp'] = event.trans_val.appearance \
                if event.action == "STA" else vc_appearance
            shadow['lastChange'] = event.trace_time
        return mid

    def _gen_closing_sta(self, last_event_ts):
        out = "// close STA/VC\n"
        idx = 0
        for shadow in self._part_shadow:
            if shadow['current'] != "" and \
                 shadow['lastChange'] < last_event_ts:

                out += '{ tp: "%s", t: %g, p: %d, ' % (
                    shadow["action"], last_event_ts, idx)
                out += self._sta_vc_output(shadow['lastChange'],
                                           shadow['current'],
                                           shadow['currentApp'])
                out += '}, \n'
            idx += 1
        return out

    def _sta_vc_output(self, begin, status, appearance):
        mid = 'b: %g, txt: "%s"' % (begin, status)
        app = self._box_appearance(appearance)
        mid += ', c:"%s", fc:"%s", sc:"%s"' % app
        return mid

    def seq_diag_interactive_viewer_path(self):
        '''
        get path relative to output directory to the
        seq_diag_interactive_viewer directory
        '''
        path = os.path.dirname(
            os.path.relpath(seq_diag_interactive_viewer.__file__,
                            self._out_dir))
        return path

    def readseq_diag_interactive_viewer_file(self, file_name):
        '''
        read file_name from seq_diag_interactive_viewer directory and
        return its content
        '''
        path = os.path.join(self.seq_diag_interactive_viewer_path(), file_name)
        file = open(path, 'r')
        text = file.read()
        file.close()
        return text

    @staticmethod
    def gen_html_head():
        ''' return HTML fixed header '''
        return '<html>\n<head>\n<script src=' + \
               '"https://d3js.org/d3.v5.min.js">' + \
               '</script>\n'

    def get_html_style(self):
        ''' return HTML code for CSS '''
        css_file = "seq_diag_interactive_viewer.css"
        out = ""

        if self._refer_files:
            out += '<link rel="stylesheet" type="text/css" href="%s">\n' % \
                (os.path.join(self.seq_diag_interactive_viewer_path(),
                              css_file))
        else:
            out += "<style>\n"
            out += self.readseq_diag_interactive_viewer_file(css_file)
            out += "</style>\n"
        return out

    @staticmethod
    def get_html_mid_1():
        ''' return HTML code for fixed elements '''
        return '''</head>
            <body>
            <div id="controls">
                <div class="slider-wrapper">
                  <input id="ScaleSlider" type="range" min="-2"
                   max="2" value="0" step="any">
                </div>
                <div>
                 <output id="T-Scale">1.00</output>
                </div>
            </div>
            <div id="scrollDummy"></div>
            <div id="title"></div>
            <div id="parts"></div>
            <div id='diagram'></div>\n'''

    def gen_script(self):
        ''' return HTML code for JS code '''
        script_file = "seq_diag_interactive_viewer.js"
        out = ""

        if self._refer_files:
            out += '<script src="%s"></script>\n' % \
                (os.path.join(self.seq_diag_interactive_viewer_path(),
                              script_file))
        else:
            out += "<script>\n"
            out += self.readseq_diag_interactive_viewer_file(script_file)
            out += "</script>\n"

        # generate code to check alert if browser is not compatible with ECMA6
        out += '''<script>
                if (typeof getDiagramArgs !== "function") {
                    alert("Sorry, your browser does not support ecmascript 6.
                     Please use Chrome, Firefox, Edge...");
                }
                </script>\n'''
        return out

    @staticmethod
    def gen_html_tail():
        ''' return HTML fixed tail '''
        return '</body></html>\n'

    @staticmethod
    def _box_appearance(appearance):
        try:
            box_stroke_color = appearance['boxStrokeColor']
        except KeyError:
            box_stroke_color = 'orange'
        try:
            box_fill_color = appearance['boxFillColor']
        except KeyError:
            box_fill_color = 'white'
        try:
            text_color = appearance['textColor']
        except KeyError:
            text_color = 'orange'
        return (box_stroke_color, box_fill_color, text_color)
