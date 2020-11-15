"""
Created on 08.04.2019

@author: klauspopp@gmx.de
"""

import unittest
import moddy
from moddy import US, MS
from moddy.lib.net.ethernet import eth_bcast_addr, eth_flight_time, eth_pdu
from moddy.lib.net.ethUnmanagedSwitch import EthUnmanagedSwitch
from moddy.lib.pdu import Pdu
from tests.utils import baseFileName, funcName


class TestEthUnmanagedSwitch1GB(unittest.TestCase):
    net_speed = 1e9  # 1GBit/s

    @classmethod
    def eth_pdu_send(cls, port, src, dst, payload):
        pdu = eth_pdu(src, dst, eth_type=0x0800, payload=payload)
        port.send(pdu, eth_flight_time(cls.net_speed, pdu.byte_len()))

    @classmethod
    def eth_client1_prog(cls, self: moddy.VThread):
        src = "00:c0:3a:00:00:01"
        while True:
            self.wait_until(20 * US)
            # client2 not yet known, switch will send message to all ports
            cls.eth_pdu_send(
                self.net_port,
                src,
                "00:c0:3a:00:00:02",
                Pdu("Data", {"stream": "Hello from Client1"}, 1000),
            )

            # send broadcast
            self.wait_until(140 * US)
            cls.eth_pdu_send(
                self.net_port,
                src,
                eth_bcast_addr(),
                Pdu("Data", {"stream": "Hello to all"}, 1000),
            )

            # simulate incoming traffic on all ports
            self.wait_until(200 * US)
            cls.eth_pdu_send(
                self.net_port,
                src,
                "00:c0:3a:00:00:02",
                Pdu("Data", {"stream": "Hello from Client1"}, 1000),
            )

            self.wait(None)

    @classmethod
    def eth_client2_prog(cls, self: moddy.VThread):
        src = "00:c0:3a:00:00:02"
        while True:
            self.wait_until(60 * US)
            # client1 already known, switch will send message only to client1
            cls.eth_pdu_send(
                self.net_port,
                src,
                "00:c0:3a:00:00:01",
                Pdu("Data", {"stream": "Hello from Client2"}, 1500),
            )

            # simulate incoming traffic on all ports
            self.wait_until(200 * US)
            cls.eth_pdu_send(
                self.net_port,
                src,
                "00:c0:3a:00:00:01",
                Pdu("Data", {"stream": "Hello from Client2"}, 1000),
            )

            self.wait(None)

    @classmethod
    def eth_client3_prog(cls, self: moddy.VThread):
        src = "00:c0:3a:00:00:03"
        while True:
            self.wait_until(100 * US)
            # client2 already known, switch will send message only to client2
            cls.eth_pdu_send(
                self.net_port,
                src,
                "00:c0:3a:00:00:02",
                Pdu("Data", {"stream": "Hello from Client3"}, 500),
            )
            # simulate incoming traffic on all ports
            self.wait_until(200 * US)
            cls.eth_pdu_send(
                self.net_port,
                src,
                eth_bcast_addr(),
                Pdu("Data", {"stream": "Hello to all"}, 1500),
            )
            self.wait(None)

    def test_basic_switch_functions(self):

        simu = moddy.Sim()

        EthUnmanagedSwitch(
            simu, "SWITCH", num_ports=3, net_speed=self.__class__.net_speed
        )
        moddy.VSimpleProg(
            sim=simu,
            obj_name="Comp1",
            target=self.__class__.eth_client1_prog,
            elems={"QueuingIO": "net_port"},
        )
        moddy.VSimpleProg(
            sim=simu,
            obj_name="Comp2",
            target=self.__class__.eth_client2_prog,
            elems={"QueuingIO": "net_port"},
        )
        moddy.VSimpleProg(
            sim=simu,
            obj_name="Comp3",
            target=self.__class__.eth_client3_prog,
            elems={"QueuingIO": "net_port"},
        )

        simu.smart_bind(
            [
                ["SWITCH.Port0", "Comp1.net_port"],
                ["SWITCH.Port1", "Comp2.net_port"],
                ["SWITCH.Port2", "Comp3.net_port"],
            ]
        )

        simu.tracing.set_display_time_unit("US")
        # let simulator run
        simu.run(stop_time=10 * MS)

        # Output sequence diagram
        moddy.gen_interactive_sequence_diagram(
            sim=simu,
            file_name="output/%s_%s.html" % (baseFileName(), funcName()),
            show_parts_list=["Comp1", "Comp2", "Comp3", "SWITCH"],
            excluded_element_list=["allTimers"],
            time_per_div=10 * US,
            pix_per_div=30,
        )


if __name__ == "__main__":
    unittest.main()
