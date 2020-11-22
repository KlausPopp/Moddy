"""
@author: klauspopp@gmx.de
"""

import moddy


def var_changer_prog(self):
    self.var1 = 0
    # self.var2 is created during execution
    while True:
        self.var1 = 1
        self.wait(2)

        self.var1 = 2
        self.var2 = "ABC"

        self.wait(2)
        self.var2 = "DEF"

        self.busy(2, "WAIT")
        self.var1 = 3

        self.wait(3)


if __name__ == "__main__":
    SIMU = moddy.Sim()
    VC = moddy.VSimpleProg(sim=SIMU, obj_name="VC", target=var_changer_prog)

    VC.new_var_watcher("var1", "0x%08x")
    VC.new_var_watcher("var2", "%s")

    SIMU.run(10)
    moddy.gen_trace_table(SIMU, "output/4_varwatch.csv")

    moddy.gen_interactive_sequence_diagram(
        sim=SIMU,
        file_name="output/4_varwatch.html",
        show_parts_list=["VC"],
        show_var_list=["VC.var1", "VC.var2"],
        excluded_element_list=["allTimers"],
        time_per_div=0.5,
        pix_per_div=30,
        title="Variable Watcher Demo",
    )
