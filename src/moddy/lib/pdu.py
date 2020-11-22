"""
Created on 27.04.2018

@author: klauspopp@gmx.de
"""


def empty_pdu(pdu_type):
    """ return a empty PDU """
    return Pdu(pdu_type, {}, 0)


class Pdu(dict):
    """
    Representation of a protocol data unit

    The Pdu is represented as a dictionary, containing the modelled protocol
    pdu fields.
    The additional member '_byte_len' represents the real byte length of
    all pdu fields

    .. code-block::

        dict={ 'm1': m1value, 'm2': m2value }, _byte_len=10

    Pdus can be nested.

    :param str pdu_type: A string describing the type of the Pdu \
      (without 'Pdu'), e.g. 'Eth'
    :param dict mapping: dictionary with member:value pairs, value can be \
         a sub-Pdu
    :param byte_len: top level byte Len - subPdus len will be added
    """

    def __init__(self, pdu_type, mapping, byte_len):
        if type(mapping) is Pdu:
            raise ValueError(
                "Pdu cannot be initialized with mapping of type Pdu"
            )

        self.pdu_type = pdu_type
        dict.__init__(self, mapping)

        # set top level bitLen
        self._byte_len = byte_len

    @classmethod
    def is_pdu(cls, obj):
        """
        Check if obj is a Pdu or a subclass of Pdu
        """
        return issubclass(obj.__class__, cls)

    def byte_len(self):
        """
        Return the length of the Pdu in bytes, including
        all its nested PDUs
        """
        byte_len = self._byte_len
        for value in self.values():
            if Pdu.is_pdu(value):
                byte_len += value.byte_len()
        return byte_len

    def fill_up(self, n_bytes):
        """
        Fill top level PDU up, so it has a byte_len of n_bytes
        if PDU already larger, raise Attribute error
        """
        if self.byte_len() > n_bytes:
            raise AttributeError(
                "Pdu is longer than fillup value %d/%d"
                % (self.byte_len(), n_bytes)
            )
        self._byte_len = n_bytes - self.byte_len() + self._byte_len

    def __repr__(self):
        """
        Return a string showing the top level items in a PDU
        """

        s = "%sPdu(%d)" % (self.pdu_type, self.byte_len())

        for key, value in self.items():
            if s != "":
                s += " "
            if Pdu.is_pdu(value):
                s += (
                    key
                    + "="
                    + "%sPdu(%d)" % (value.pdu_type, value.byte_len())
                )
            else:
                s += key + "=" + value.__str__()

        return s

    def dump(self):
        """
        Return a string as __repr()__, but also dump sub-pdus in separated,
        intended lines, e.g.:

        .. code-block::

            IpPdu(1220) ihl=14 flags=0 src=192.1.1.2 dst=192.1.1.8
            payld=RawPdu(1000) payld2=RawPdu(200)
                payld:RawPdu(1000) raw=IPPAYLOAD
                payld2:RawPdu(200) raw=AnotherPayld

        """
        return self._dump("", self, 0)

    def _dump(self, key, value, level):
        indent_fmt = "%" + ("%d" % (3 * level)) + "s"
        indent = indent_fmt % ""
        s = indent + ("" if key == "" else key + ":") + value.__repr__() + "\n"
        for key, value in value.items():
            if Pdu.is_pdu(value):
                s += self._dump(key, value, level + 1)
        return s

    def split_to_fragments(self, pdu_type, max_frag_byte_len):
        """
        Split the Pdu into fragments and return list of fragments
        Each fragment is represented as a Pdu

        .. code-block::

            Pdu( "<orgtype>Frag", { 'fr': (<offset of fragment>,
            <len of fragment>), 'org'=[<original Pdu>], fraglen )

        Note: the 'org' member is transferred with every fragment.
        It is enclosed in a list, so that it
        is not included in the fragment's byte length.

        The PduDefragmenter class can be used to defragment the fragments

        :param string pdu_type: pdu_type to set for fragments
        :param int max_frag_byte_len: maximum bytes per fragment
        :return list: list of fragments
        """
        frags = []
        frag_off = 0
        org_pdu_len = self.byte_len()

        while True:
            frag_len = org_pdu_len - frag_off
            if frag_len > max_frag_byte_len:
                frag_len = max_frag_byte_len

            frag = Pdu(
                pdu_type, {"fr": (frag_off, frag_len), "org": [self]}, frag_len
            )
            frags.append(frag)

            frag_off += frag_len
            if frag_off >= org_pdu_len:
                break

        return frags


class PduDefragmenter(object):
    """
    Class to defragment a PDU that has been fragmented with
    split_to_fragments().

    Create an instance of this class and add all received fragments
    with add_fragment(). Fragments may be received in any order.

    Whether the defragmentation is complete, can be checked by
    calling the_pdu() or defrag_complete_info().

    """

    def __init__(self):
        self.pdu = None
        self.frags = []  # list with tuples (off,len) of received fragments

    def add_fragment(self, frag):
        """
        Add a received fragment
        """
        self.frags.append(frag["fr"])
        self.pdu = frag["org"][0]

    def the_pdu(self):
        """
        Return the complete defragmented PDU. If fragments are missing,
        return None.
        """
        if self.defrag_complete_info() is None:
            return self.pdu
        else:
            return None

    def defrag_complete_info(self):
        """
        Check if defragmentation complete.

        :return string: None if complete or string with info with \
        first missing frag
        """
        off = 0

        while True:
            frag = self.has_offs(off)
            if frag is None:
                return "missing frag at offs %d" % off
            off += frag[1]

            if off >= self.pdu.byte_len():
                break
        return None

    def has_offs(self, off):
        for frag in self.frags:
            if frag[0] == off:
                return frag
        return None
