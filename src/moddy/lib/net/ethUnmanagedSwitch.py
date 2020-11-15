"""
:mod:`ethUnmanagedSwitch` -- Unmanaged Ehternet Switch
======================================================

.. module:: ethUnmanagedSwitch
   :synopsis: Unmanaged Ehternet Switch
.. moduleauthor:: Klaus Popp <klauspopp@gmx.de>
"""

from moddy import SimPart
from moddy.lib.net.ethernet import eth_bcast_addr, eth_flight_time, eth_hdr_len


class EthUnmanagedSwitch(SimPart):
    def __init__(self, sim, obj_name, num_ports, net_speed):
        super().__init__(sim=sim, obj_name=obj_name)

        self._num_ports = num_ports
        self._net_speed = net_speed
        self._lookup_table = {}  # key=macAddr, value=NetPort

        self._net_ports = []

        for port_num in range(num_ports):
            self._net_ports.append(self.NetPort(self, port_num))

    def lookup_mac_addr(self, mac_addr):
        """
        lookup macAddr in lookupTable.
        :param str macAddr: address to lookup (e.g. '00:11:22:33:44:55')
        :return: NetPort where macAddr is known. None if not found or if it
        macAddr is broadcast
        """
        if mac_addr != eth_bcast_addr() and mac_addr in self._lookup_table:
            return self._lookup_table[mac_addr]
        else:
            return None

    def add_mac_to_lookup_table(self, net_port, mac_addr):
        """
        Add macAddr tp lookupTable. Update if it is already in lookup Table
        :param NetPort netPort: netPort where this macAddr is attached to
        :param str macAddr: address to addr (e.g. '00:11:22:33:44:55')
        """
        self._lookup_table[mac_addr] = net_port

    class NetPort:
        def __init__(self, switch, port_num):

            self._switch = switch
            self._net_speed = switch._net_speed

            # create network port
            self._net_port = switch.new_io_port("Port%d" % port_num, None)
            self._net_port.set_msg_started_func(self.net_port_recv_start)

            # create a port that simulates the cut-through delay
            self._cut_through_del_port = switch.new_io_port(
                "CutThroughDelPort%d" % port_num,
                self.cut_through_del_port_recv,
            )
            self._cut_through_del_port.loop_bind()

        def net_port_recv_start(self, in_port, pdu, out_port, flight_time):
            self._cut_through_del_port.send(
                pdu, eth_flight_time(self._net_speed, eth_hdr_len())
            )

        def cut_through_del_port_recv(self, in_port, pdu):
            dst_addr = pdu["dst"]
            src_addr = pdu["src"]

            # Add source addr to lookupTable
            self._switch.add_mac_to_lookup_table(self, src_addr)

            # check which port has destination address
            dst_port = self._switch.lookup_mac_addr(dst_addr)

            if src_addr != dst_addr:
                if dst_port is None:
                    # forward to all ports (except my own)
                    for net_port in self._switch._net_ports:
                        if net_port is not self:
                            net_port.send_pdu(pdu)
                else:
                    # forward to specific port
                    dst_port.send_pdu(pdu)

        def send_pdu(self, pdu):
            self._net_port.send(
                pdu, eth_flight_time(self._net_speed, pdu.byte_len())
            )
