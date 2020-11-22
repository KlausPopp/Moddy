"""
Created on 15.09.2019

@author: klauspopp@gmx.de
"""
# import moddy
import fnmatch


class TraceSearch(object):
    """
    Class to search moddy traced events
    """

    def __init__(self, sim):
        self.sim = sim
        self.traced_events = sim.tracing.traced_events()
        self.curIdx = 0

    def find_ann(self, part, text_pat, start_idx=None):
        """
        find next Annotation
        :param string textPat: text pattern with wildcards. \
            If None, matches any text
        other parameters and return, see findEvent
        """
        return self.find_event(
            part, start_idx, self.tv_str_match, ("ANN", text_pat)
        )

    def find_ass_fail(self, part, text_pat, start_idx=None):
        """
        find next Assertion Failure
        :param string textPat: text pattern with wildcards. \
            If None, matches any text
        other parameters and return, see findEvent
        """
        return self.find_event(
            part, start_idx, self.tv_str_match, ("ASSFAIL", text_pat)
        )

    def find_sta(self, part, text_pat, start_idx=None):
        """
        find next Status event
        :param string textPat: text pattern with wildcards. \
            If None, matches any text
        other parameters and return, see findEvent
        """
        return self.find_event(
            part, start_idx, self.tv_str_match, ("STA", text_pat)
        )

    def find_rcv_msg(self, part, textPat, start_idx=None):
        """
        find next received message by text pattern on message
        string representation
        "part" is the part receiving the message
        :param string textPat: message text with wildcards. \
            If None, matches any
        other parameters and return, see findEvent
        """
        return self.find_event(
            part,
            start_idx,
            self.msg_match,
            ("<MSG", textPat),
            part_matcher=self.sub_part_parent_match,
        )

    def find_snd_msg(self, part, text_pat, start_idx=None):
        """
        find next sent message by text pattern on message string representation
        "part" is the part sending the message
        :param string textPat: message text with wildcards.
        If None, matches any other parameters and return, see findEvent
        """
        return self.find_event(
            part,
            start_idx,
            self.msg_match,
            (">MSG", text_pat),
            part_matcher=self.sub_part_parent_match,
        )

    def find_vc(self, var_watcher, text_pat, start_idx=None):
        """
        find next value change event by text pattern
        "varChanger" must be the varWatcher instance
        (hierarchy name not supported!)
        :param string textPat: message text with wildcards.
        If None, matches any other parameters and return, see findEvent
        """
        return self.find_event(
            var_watcher,
            start_idx,
            self.tv_str_match,
            ("VC", text_pat),
            part_matcher=self.sub_part_match,
        )

    def tv_str_match(self, para, te):
        m_type, text_pat = para
        rv = False
        if te.action == m_type:
            if self.wildcard_match(te.trans_val.__str__(), text_pat):
                rv = True
        return rv

    def msg_match(self, para, te):
        m_type, text_pat = para
        rv = False
        if te.action == m_type:
            if self.wildcard_match(te.trans_val.msg_text(), text_pat):
                rv = True
        return rv

    def find_event(
        self, part, start_idx, match_func, match_func_para, part_matcher=None
    ):
        """
        find next traced event
        :param part: part hierarchy name or instance. If None, match any part
            This is passed to partMatcher. So, depending on partMatcher,
            it can be a part, a part hierarchy name, or a subpart
        :param startIdx: index in tracedEvents to start with \
            (use curIdx if None)
        :param partMatcher: function to call to check if trace event \
            matches part
            if None, use partMatch(te,p)
        :return: idx, te=the index and found event or None
        :raises ValueError: if part name not found
        """
        if part_matcher is None:
            part_matcher = self.part_match
        idx = start_idx if start_idx is not None else self.curIdx
        part = self.part_translate(part)

        rv = None
        for idx in range(idx, len(self.traced_events)):
            te = self.traced_events[idx]
            # print("COMPARING te %d: %s" % (idx, te))
            # if te.part == part or self.subPartMatch(part, te):
            if part_matcher(te, part):
                if match_func(match_func_para, te):
                    rv = (idx, te)
                    break
        self.curIdx = idx + 1
        return rv

    @staticmethod
    def part_match(te, p):
        return te.part == p

    @staticmethod
    def sub_part_parent_match(te, p):
        subpart = te.sub_obj
        if subpart is None:
            return False

        return subpart.parent_obj == p

    @staticmethod
    def sub_part_match(te, p):
        return te.sub_obj == p

    def part_translate(self, part):
        """
        :param part: part hierarchy name or instance. If None, match any part
        :return part instance
        :raises ValueError: if part name not found
        """
        if type(part) is str:
            part = self.sim.parts_mgr.find_part_by_name(part)
        return part

    def wildcard_match(self, txt, pattern):
        return pattern is None or fnmatch.fnmatch(txt, pattern)
