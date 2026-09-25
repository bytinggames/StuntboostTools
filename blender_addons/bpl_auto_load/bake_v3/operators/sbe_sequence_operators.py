"""
Operators for exporting and inspecting the export.
Export operators are chained into a sequence which,
these are defined here and called from new "meta ops"
"""

import os
import sys
import subprocess
import datetime

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_custom_properties import SBE_TEMP_NO_SKIP_BAKE_PROP
from bake_v3.sbe_operator_ids import (
    SBE_OP_CLEAR_LOGS, SBE_OP_SHOW_LOGS, SBE_OP_SAVE_LOGS,
    SBE_OP_BUILD_LEVEL, SBE_OP_INSPECT_SCENE, SBE_OP_FAST_BUILD_SCENE,
    SBE_OP_BUILD_SELECTION, SBE_OP_TOGGLE_ORIGINAL, SBE_OP_FINALIZE,
    SBE_OP_INSPECT_LEVEL
)
from bake_v3.sbe_export_sequences import (
    FULL_BAKE_SEQUENCE, INSPECT_EXPORT, FAST_BAKE_SEQUENCE,
)
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_util import execute_by_idname, store_temp, ensure_saved_as_bake_blend
from bake_v3.properties.sbe_blend_props import SBE_BlendProperties
from bake_v3.sbe_sound import error_sound

def ensure_system_console():
    """Show the Windows console without hiding an already visible console."""
    if sys.platform != "win32" or bpy.app.background:
        return

    import ctypes
    from ctypes import wintypes

    get_console_window = ctypes.windll.kernel32.GetConsoleWindow
    get_console_window.restype = wintypes.HWND
    is_window_visible = ctypes.windll.user32.IsWindowVisible
    is_window_visible.argtypes = [wintypes.HWND]
    is_window_visible.restype = wintypes.BOOL
    if not is_window_visible(get_console_window()):
        bpy.ops.wm.console_toggle()



def defer_call(operator: bpy.types.Operator) -> bool:
    """When requested will run the operator in a new blender instance in the background"""
    if bpy.app.background:
        # We're in the deferred state so let's not defer further
        return False

    props: SBE_BlendProperties = SBE_BlendProperties.get()
    if not props.bake_own_process:
        return False

    if not os.access(bpy.data.filepath, os.W_OK):
        raise Exception("Can't bake in own process without write permissions")
    operator_id = type(operator).bl_idname

    text_block_name = "sbe_temp_script"
    text_block: bpy.types.Text = None
    if text_block_name in bpy.data.texts:
        text_block = bpy.data.texts[text_block_name]
    else:
        text_block = bpy.data.texts.new(text_block_name)
    script_text = f"""
import bpy
bpy.ops.{operator_id}()
    """
    text_block.from_string(script_text)
    bpy.ops.wm.save_as_mainfile()

    command = [bpy.app.binary_path, "-b", bpy.data.filepath, "--python-text", text_block.name]
    print(command)
    sub = subprocess.Popen(command)
    # TODO some polling and feedback when done
    return True

class SBE_FastBuildScene(bpy.types.Operator):
    """TODO tk not used!!! Export the whole level fast"""
    bl_idname = SBE_OP_FAST_BUILD_SCENE
    bl_label = "STUNTBOOST Export Scene Fast UNUSED!"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        execute_by_idname(SBE_OP_TOGGLE_ORIGINAL)
        execute_by_idname(SBE_OP_CLEAR_LOGS)
        # TODO this should not run the bake at all and export the visual geometry as is
        for i in FAST_BAKE_SEQUENCE:
            execute_by_idname(i)
        execute_by_idname(SBE_OP_SHOW_LOGS)
        execute_by_idname(SBE_OP_FINALIZE)
        return {"FINISHED"}


def build_scene():
    for i in FULL_BAKE_SEQUENCE:
        ret = execute_by_idname(i)
        if ret != {"FINISHED"}:
            return False
    return True


class SBE_FullBuildScene(bpy.types.Operator):
    """Export the currently selected bake groups"""
    bl_idname = SBE_OP_BUILD_SELECTION
    bl_label = "STUNTBOOST Export Selection"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        ensure_system_console()
        if defer_call(self):
            return {"FINISHED"}
        try:
            SBE_Logger.start_auto_update()
            execute_by_idname(SBE_OP_CLEAR_LOGS)
            store_temp(SBE_TEMP_NO_SKIP_BAKE_PROP, False)
            build_scene()
            execute_by_idname(SBE_OP_SHOW_LOGS)
            execute_by_idname(SBE_OP_FINALIZE)
        except Exception:
            error_sound()
            raise
        finally:
            SBE_Logger.stop_auto_update()

        return {"FINISHED"}


class SBE_FullBuildLevel(bpy.types.Operator):
    """Export the whole level/all scenes containing a bake group"""
    bl_idname = SBE_OP_BUILD_LEVEL
    bl_label = "STUNTBOOST Export"
    bpl_auto_load = True

    def execute(self, context: bpy.types.Context):
        ensure_system_console()
        if defer_call(self):
            return {"FINISHED"}

        # we do this manually here because
        # we flip through the scenes before calling any of the
        # export operators which all call this as well
        ensure_saved_as_bake_blend()

        scenes: list[bpy.types.Scene] = bpy.data.scenes[:]
        # make sure current scene is baked last
        # so the export.blend file is saved with it active
        scenes.remove(context.scene)
        scenes.append(context.scene)

        execute_by_idname(SBE_OP_CLEAR_LOGS)
        try:
            SBE_Logger.start_auto_update()
            store_temp(SBE_TEMP_NO_SKIP_BAKE_PROP, True)
            # We don't want to clear logs between scenes
            SBE_Logger.SBE_SKIP_LOG_CLEAR = True
            SBE_Logger.print(datetime.datetime.now())
            SBE_Logger.print(f"Export Scenes: {len(scenes)}")
            for scene in scenes:
                SBE_Logger.print(f"\t{scene.name}")
            for scene in scenes:
                bpy.context.window.scene = scene
                if not build_scene():
                    SBE_Logger.error(f"Failed to build scene {scene.name}")
            execute_by_idname(SBE_OP_FINALIZE)
        except:
            error_sound()
            raise
        finally:
            SBE_Logger.stop_auto_update()
            execute_by_idname(SBE_OP_SAVE_LOGS)
            execute_by_idname(SBE_OP_SHOW_LOGS)
            SBE_Logger.SBE_SKIP_LOG_CLEAR = False

        return {"FINISHED"}


class SBE_FullInspectLevel(bpy.types.Operator):
    """Inspect the whole level/all scenes containing a bake group, same as SBE_OP_BUILD_LEVEL"""
    bl_idname = SBE_OP_INSPECT_LEVEL
    bl_label = "STUNTBOOST Inspect Level"
    bpl_auto_load = True

    def execute(self, context: bpy.types.Context):
        if defer_call(self):
            return {"FINISHED"}

        # we do this manually here because
        # we flip through the scenes before calling any of the
        # export operators which all call this as well
        ensure_saved_as_bake_blend()

        scenes: list[bpy.types.Scene] = bpy.data.scenes[:]
        # make sure current scene is baked last
        # so the export.blend file is saved with it active
        scenes.remove(context.scene)
        scenes.append(context.scene)

        execute_by_idname(SBE_OP_CLEAR_LOGS)
        try:
            SBE_Logger.start_auto_update()
            store_temp(SBE_TEMP_NO_SKIP_BAKE_PROP, True)
            # We don't want to clear logs between scenes
            SBE_Logger.SBE_SKIP_LOG_CLEAR = True
            SBE_Logger.print(datetime.datetime.now())
            SBE_Logger.print(f"Export Scenes: {len(scenes)}")
            for scene in scenes:
                SBE_Logger.print(f"\t{scene.name}")
            for scene in scenes:
                bpy.context.window.scene = scene
                for i in INSPECT_EXPORT:
                    ret = execute_by_idname(i)
                    if ret != {"FINISHED"}:
                        SBE_Logger.error(f"Failed to inspect scene {scene.name} {i}")
            execute_by_idname(SBE_OP_FINALIZE)
        except:
            error_sound()
            raise
        finally:
            SBE_Logger.stop_auto_update()
            execute_by_idname(SBE_OP_SAVE_LOGS)
            execute_by_idname(SBE_OP_SHOW_LOGS)
            SBE_Logger.SBE_SKIP_LOG_CLEAR = False

        return {"FINISHED"}


class SBE_InspectExport(bpy.types.Operator):
    """This will skip the bake and export leaving the scene for inspection to help with debugging"""
    bl_idname = SBE_OP_INSPECT_SCENE
    bl_label = "Inspect STUNTBOOST Scene"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        execute_by_idname(SBE_OP_CLEAR_LOGS)
        store_temp(SBE_TEMP_NO_SKIP_BAKE_PROP, False)
        # TODO tk force release mode so we can see UV grids
        for i in INSPECT_EXPORT:
            execute_by_idname(i)
        execute_by_idname(SBE_OP_SHOW_LOGS)
        execute_by_idname(SBE_OP_FINALIZE)
        return {"FINISHED"}
