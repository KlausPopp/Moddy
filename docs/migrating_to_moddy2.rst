Porting from Moddy 1 to 2
=========================

Moddy 2 has been completely reworked to comply with pep8 conventions.


No wildcard import
------------------

Instead of 
.. code-block:: python
        
        from moddy import *

        class MyClass(simPart)
                ...
        
use

.. code-block:: python
        
        import moddy

        class MyClass(moddy.SimPart)
        
        
Rename all moddy parameters to snake_case
-----------------------------------------------------------

Parameters to the __init__ method
        objName -> obj_name
        parentObj -> parent_obj
        
Rename all moddy methods to names to snake_case
-----------------------------------------------------------


e.g. scheduler addVThread -> add_vthread
readMsg -> read_msg
nMsg -> n_msg
smartBind -> smart_bind

Rename changed/moved moddy methods
-----------------------------------------------------------

addAnnotation -> annotation
sim:setDisplayTimeUnit -> Sim.tracing:set_display_time_unit

moddyGenerateSequenceDiagram -> moddy.gen_gen_interactive_sequence_diagram
Note: fmt parameter has been removed  

moddyGenerateStructureGraph -> moddy.gen_dot_structure_graph()

Rename constants
-----------------------------------------------------------

ns -> NS (or moddy.NS)
us -> US
ms -> MS

bcWhiteOnGreen -> BC_WHITE_ON_GREEN (or moddy.BC_WHITE_ON_GREEN)

Rename your message and timer callbacks
-----------------------------------------------------------

<port>Recv -> port_recv
<tmr>Expired -> tmr_expired


Rename to new class names
-----------------------------------------------------------

sim -> Sim
simPart -> SimPart
vtSchedRtos -> VtSchedRtos
vThread -> VThread
vSimpleProg -> VSimpleProg

Rename your ports (optional)
-----------------------------------------------------------

Recommended, so that port callbacks are snake_case named.

e.g. "serPort" -> "ser_port"

Rename your state callbacks in FSMs 
-----------------------------------------------------------

State_xxx_Entry -> state_xxx_entry
State_xxx_Exit -> state_xxx_exit
State_xxx_Do -> state_xxx_do
State_ANY_xxx -> state_any_xxx


Rename message and timer callbacks
-----------------------------------------------------------

xxx_Msg -> xxx_msg
xxx_Expired -> xxx_expired

Rename your states in FSMs (optional)
-----------------------------------------------------------

Recommended, so that fsm callbacks are snake_case named.

e.g. "Off" -> "off"


