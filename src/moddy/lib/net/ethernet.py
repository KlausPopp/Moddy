"""
:mod:`ethernet` -- Ethernet Helper Functions
======================================================

.. module:: ethernet
   :synopsis: Ethernet Helper Functions
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>
"""

from moddy.lib.pdu import Pdu


def eth_hdr_len():
    """
    :return: Ethernet header byte length
    """
    return 14


def eth_bcast_addr():
    """
    :return: Ethernet Broadcast MAC Address "FF:FF:FF:FF:FF:FF"
    """
    return "FF:FF:FF:FF:FF:FF"


def eth_flight_time(netSpeed, nBytes):
    """
    Compute flight time of an Ethernet frame
    If nBytes are below the minimum Ethernet frame length,
    the flight time of the minimum frame length is returned.
    :param netSpeed: physical link speed in bits/second
    :param nBytes: number of bytes to transmit
    :return: transmission time on wire in seconds
    """
    return ((max(64, nBytes) * 10) + 96) / netSpeed


def ethPdu(src, dst, ethType, payload):
    """
    Create an Ethernet Pdu
    :param str src: Source MAC address
    :param str dst: Destination MAC address
    :param ehtType: Ethernet type
    :param Pdu payload: Ethernet payload
    :return: filled Pdu
    """
    return Pdu(
        "Eth",
        {"src": src, "dst": dst, "type": ethType, "payld": payload},
        eth_hdr_len(),
    )
