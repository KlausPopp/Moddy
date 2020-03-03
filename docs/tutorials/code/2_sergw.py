'''
2_sergw: A tutorial that models a serial GATEWAY to show the use of moddy
VThreads

@author: Klaus Popp
'''
# because the filename doesn't conform to snake case style ...
# pylint: disable=C0103

import moddy
from moddy import US, MS


class Gateway(moddy.SimPart):
    ''' Model of the Gateway '''

    def __init__(self, sim):
        # Initialize the parent class
        super().__init__(sim=sim, obj_name="GW")

        # Create a scheduler
        self.sched = moddy.VtSchedRtos(sim=sim, obj_name="sched",
                                       parent_obj=self)

        # Create a Rx and a Tx thread
        self.rx_thread = moddy.VThread(sim=sim, obj_name="RxThr",
                                       target=self.rx_thread_task,
                                       parent_obj=self,
                                       elems={'QueuingIn': 'ser_port',
                                              'out': 'net_port'})
        self.tx_thread = moddy.VThread(sim=sim, obj_name="TxThr",
                                       target=self.tx_thread_task,
                                       parent_obj=self,
                                       elems={'QueuingIn': 'net_port',
                                              'out': 'ser_port'})

        # add threads to scheduler
        self.sched.add_vthread(self.rx_thread, prio=1)
        self.sched.add_vthread(self.tx_thread, prio=2)

    @staticmethod
    def rx_thread_task(v_thead: moddy.VThread):
        ''' Gateway receive thread '''
        # note: v_thead is the instance of the vThread
        while True:
            # Wait until serial data available
            if v_thead.ser_port.n_msg() == 0:
                v_thead.wait(timeout=None, ev_list=[v_thead.ser_port])

            # Read serial data. Simulate read from HW Fifo
            # (each message is only one char)
            # Simulate fifo depth of 8 (if more than 8 messages received,
            # Fifo overflow)
            n_chars = v_thead.ser_port.n_msg()

            msg_str = ''
            for _ in range(n_chars):
                msg_str += v_thead.ser_port.read_msg()

            if n_chars > 8:
                v_thead.annotation('FIFO overflow!')
                n_chars = 8
                msg_str = msg_str[:n_chars]

            # Simulate reading from HW Fifo takes time
            # (20us per char, really slow CPU...)
            v_thead.busy(n_chars * 20 * US, 'RFIFO', moddy.BC_WHITE_ON_RED)

            # push data to network
            v_thead.busy(150 * US, 'TXNET', moddy.BC_WHITE_ON_GREEN)

            v_thead.net_port.send(msg_str, 100 * US)

    @staticmethod
    def tx_thread_task(v_thread: moddy.VThread):
        ''' Gateway transmit thread '''
        # note: v_thread is the instance of the vThread
        while True:
            if v_thread.net_port.n_msg() == 0:
                v_thread.wait(timeout=None, ev_list=[v_thread.net_port])

            v_thread.busy(100 * US, 'RXNET', moddy.BC_WHITE_ON_GREEN)

            # read one message
            msg = v_thread.net_port.read_msg()

            v_thread.busy(len(msg) * 20 * US, 'TXFIFO', moddy.BC_WHITE_ON_RED)

            # push to serial port
            for c in msg:
                v_thread.ser_port.send(c, ser_flight_time(c))


def client_prog(v_thread: moddy.VThread):
    ''' Network CLIENT '''
    # note: v_thread is the instance of the vThread
    while True:
        v_thread.wait(1.2 * MS)
        v_thread.net_port.send('test', 100 * US)
        v_thread.busy(100 * US, 'TX1', moddy.BC_WHITE_ON_BLUE)
        v_thread.net_port.send('test1', 100 * US)
        v_thread.busy(100 * US, 'TX2', moddy.BC_WHITE_ON_RED)
        v_thread.wait(2.3 * MS)
        v_thread.net_port.send('Data1', 100 * US)
        v_thread.busy(100 * US, 'TX3', moddy.BC_WHITE_ON_GREEN)


def ser_dev_prog(v_thread: moddy.VThread):
    ''' Serial Device '''
    # note: v_thread is the instance of the vThread

    # set blue color for messages from SerDev
    v_thread.ser_port.out_port().set_color('blue')
    while True:
        # Generate some serial output
        v_thread.wait(2 * MS)

        msg_str = 'abc'
        for c in msg_str:
            v_thread.ser_port.send(c, ser_flight_time(c))

        v_thread.wait(1 * MS)

        msg_str = 'Hello-World'
        for c in msg_str:
            v_thread.ser_port.send(c, ser_flight_time(c))


def ser_flight_time(tx_string):
    ''' Compute flight time for tx_string (baudrate=115200) '''
    time_per_char = (1.0 / 115200) * 10
    return time_per_char * len(tx_string)


if __name__ == '__main__':
    SIMU = moddy.Sim()
    SIMU.tracing.set_display_time_unit('US')

    CLIENT = moddy.VSimpleProg(sim=SIMU, obj_name="Client",
                               target=client_prog,
                               elems={'QueuingIO': 'net_port'})
    SERDEV = moddy.VSimpleProg(sim=SIMU, obj_name="SerDev",
                               target=ser_dev_prog,
                               elems={'QueuingIO': 'ser_port'})
    GATEWAY = Gateway(SIMU)

    # Bind ports
    SIMU.smart_bind([
        ['SerDev.ser_port_out', 'GW.RxThr.ser_port'],
        ['SerDev.ser_port_in', 'GW.TxThr.ser_port'],
        ['Client.net_port_in', 'GW.RxThr.net_port'],
        ['Client.net_port_out', 'GW.TxThr.net_port'],
    ])

    # let simulator run
    try:
        SIMU.run(stop_time=12 * MS)

    except Exception as exception:
        raise exception
    finally:
        # create sequence diagram
        moddy.gen_interactive_sequence_diagram(
            sim=SIMU,
            file_name="output/2_sergw.html",
            show_parts_list=["Client", "GW.RxThr",
                             "GW.TxThr", "SerDev"],
            excluded_element_list=['allTimers'],
            time_per_div=50 * US,
            pix_per_div=30,
            title="Serial Gateway Demo")

    # Output model structure graph
    moddy.gen_dot_structure_graph(SIMU, 'output/2_sergw_structure.svg')
