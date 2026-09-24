"""All export operators should derive from this class so timing and errors are logged properly"""


import dataclasses
import traceback

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_util import (
    retrieve_persistent, store_persistent, ensure_saved_as_bake_blend
)
from bake_v3.sbe_logger import SBE_Logger

@dataclasses.dataclass
class SBE_Operator_Start_Result():
    can_run: bool = False
    has_run: bool = False


class SBE_Operator_Start():
    """Should be called at the start of every operator related to the bake/export process,
    returns true if the operator should commence.
    TODO add a custom step operator which takes care of all this
    """
    operator_id: str
    def __init__(self, operator: bpy.types.Operator, context: bpy.types.Context):
        self.operator_id = type(operator).bl_idname
        ensure_saved_as_bake_blend()
        # make sure there's no selection or other implicit blender state
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        if not operator.keep_selection:
            context.view_layer.objects.active = None
            bpy.ops.object.select_all(action='DESELECT')
            if bpy.ops.object.hide_view_clear.poll():
                bpy.ops.object.hide_view_clear()

    def __enter__(self) -> SBE_Operator_Start_Result:
        result = SBE_Operator_Start_Result()
        if retrieve_persistent(self.operator_id) is not None:
            result.has_run = True
        SBE_Logger.print(f"Start operator {self.operator_id}", 2)
        SBE_Logger.start(self.operator_id)
        result.can_run = True
        return result

    def __exit__(self, *args):
        SBE_Logger.stop(self.operator_id)
        # SBE_Logger.print(f"Finished operator {self.operator_id}", cut_stack=2)
        execution_count = SBE_Operator_Start.run_count(self.operator_id)
        execution_count += 1
        store_persistent(self.operator_id, execution_count)

    @staticmethod
    def run_count(operator_id: str) -> int:
        """Return how often the operator has run"""
        execution_count = retrieve_persistent(operator_id)
        if execution_count is None:
            return 0
        return execution_count

class SBE_ExportOperatorBase(bpy.types.Operator):
    """Base class for all operators in ./export_operators"""

    keep_selection: bool = False
    bl_options = {'REGISTER', 'UNDO'}

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        """Function to implement in the derived operator"""

    def execute(self, context: bpy.types.Context):
        with SBE_Operator_Start(self, context) as result:
            if result.can_run:
                try:
                    self.execute_internal(context=context, start=result)
                except KeyboardInterrupt:
                    SBE_Logger.print("Aborted bake")
                    return {"CANCELLED"}
                except Exception as e:
                    SBE_Logger.error(str(e))
                    SBE_Logger.error(''.join(traceback.TracebackException.from_exception(e).format()))
                    raise e
        return {"FINISHED"}
