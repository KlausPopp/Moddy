'''
@author: klauspopp@gmx.de
'''
import unittest
import moddy

class TestDot(unittest.TestCase):
    class Cpu(moddy.SimPart):

        def __init__(self, sim, obj_name, parent_obj=None):
            super().__init__(sim, obj_name, parent_obj)
            self.sched = moddy.VtSchedRtos(sim, "schedCpu", self)
            self.app1 = TestDot.App(sim, "App1", self)
            self.app2 = TestDot.App(sim, "App2", self)

            self.sched.add_vthread(self.app1, 1)
            self.sched.add_vthread(self.app2, 2)

    class App(moddy.VThread):

        def __init__(self, sim, obj_name, parent_obj=None):
            super().__init__(sim, obj_name, parent_obj)

            self.create_ports('SamplingIO', ['ecmPort'])

        def run_vthread(self):
            while True:
                pass

    class EcMaster(moddy.SimPart):

        def __init__(self, sim, obj_name, parent_obj=None):
            super().__init__(sim, obj_name, parent_obj)

            self.create_ports('io', ['appPort', 'ecPort'])

        def appPort_recv(self, port, msg):
            pass

        def ecPort_recv(self, port, msg):
            pass

    class EcDevice(moddy.SimPart):

        def __init__(self, sim, obj_name, parent_obj=None):
            super().__init__(sim, obj_name, parent_obj)

            self.create_ports('io', ['ecPort', 'ucPort'])

            self.uc = self.EcUc(sim, self)
            self.fpga = self.EcFpga(sim, self)
            self.ucPort.bind(self.uc.escPort)
            self.uc.fpgaPort.bind(self.fpga.ucPort)

        def ecPort_recv(self, port, msg):
            pass

        def ucPort_recv(self, port, msg):
            pass

        class EcUc(moddy.SimPart):

            def __init__(self, sim, parent_obj):
                super().__init__(sim, "uC", parent_obj)
                self.create_ports('in', ['sensPort'])
                self.create_ports('io', ['escPort', 'fpgaPort'])

            def escPort_recv(self, port, msg):
                pass

            def fpgaPort_recv(self, port, msg):
                pass

            def sensPort_recv(self, port, msg):
                pass

        class EcFpga(moddy.SimPart):

            def __init__(self, sim, parent_obj):
                super().__init__(sim, "FPGA", parent_obj)
                self.create_ports('io', ['ucPort'])

            def ucPort_recv(self, port, msg):
                pass

    class Sensor(moddy.SimPart):

        def __init__(self, sim, obj_name, parent_obj=None):
            super().__init__(sim, obj_name, parent_obj)

            self.create_ports('out', ['outPort'])
            self.create_ports('in', ['pwrPort'])

        def pwrPort_recv(self, port, msg):
                pass

    
    def testDot(self):
        simu = moddy.Sim()
        cpu = self.Cpu(simu, "CPU")
        ecm = self.EcMaster(simu, "ECM")
        ecDev1 = self.EcDevice(simu, "DEV1")
        ecDev2 = self.EcDevice(simu, "DEV2")
        sensor = self.Sensor(simu, "SENSOR")
        ecm.ecPort.out_port().bind(ecDev1.ecPort.in_port())
        ecDev1.ecPort.out_port().bind(ecDev2.ecPort.in_port())
        ecDev2.ecPort.out_port().bind(ecm.ecPort.in_port())
        sensor.outPort.bind(ecDev1.uc.sensPort)
        sensor.outPort.bind(ecDev2.uc.sensPort)
        # sensless, but test that a peer-to-peer port can be bound to an 
        # additional input port
        ecDev1.uc.fpgaPort.out_port().bind(sensor.pwrPort)
    
        # test 3 IO ports bound together (mesh)
        cpu.app1.ecmPort.bind(ecm.appPort)
        cpu.app2.ecmPort.bind(ecm.appPort)
        cpu.app1.ecmPort.bind(cpu.app2.ecmPort)
    
        for pName in ['SENSOR.outPort', 'DEV2.FPGA.ucPort', 'CPU.App1.ecmPort']:
            print("findPortByName %s = %s" % (pName, simu.parts_mgr.find_port_by_name(pName)))
    
        moddy.gen_dot_structure_graph(simu, 'output/structTest.svg', keep_gv_file=True)

if __name__ == "__main__":
    unittest.main()