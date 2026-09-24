"""
Operators to clear, view and save the export log output from blender
"""

import os
import platform

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_paths import LOG_FOLDER, ensure_folder
from bake_v3.sbe_operator_ids import SBE_OP_CLEAR_LOGS, SBE_OP_SHOW_LOGS, SBE_OP_SAVE_LOGS
from bake_v3.sbe_util import is_export_file

class SBE_ClearLogs(bpy.types.Operator):
    """Clear the timer + logger"""
    bl_idname = SBE_OP_CLEAR_LOGS
    bl_label = "SBE Clear Logs"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        SBE_Logger.clear()
        return {'FINISHED'}


class SBE_SaveLogs(bpy.types.Operator):
    """Save the current timer + logger in a file next to the blend"""
    bl_idname = SBE_OP_SAVE_LOGS
    bl_label = "SBE Save Logs"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        ensure_folder(LOG_FOLDER)
        log_file_name = os.path.basename(bpy.data.filepath)
        pc_name = platform.node()
        pc_name = "".join(x for x in pc_name if x.isalnum())

        # .log files are in gitignore
        log_file_name = log_file_name.replace(".blend", f"_{pc_name}.txt")
        log_path = os.path.join(LOG_FOLDER, log_file_name)

        log = SBE_Logger.get_log_text()
        with open(log_path, mode="w", encoding="utf-8") as f:
            f.write(log)
        return {'FINISHED'}


class SBE_ShowLog(bpy.types.Operator):
    """Open entire build log in text editor"""
    bl_idname = SBE_OP_SHOW_LOGS
    bl_label = "SBE Show build log"
    bpl_auto_load = True

    def execute(self, context: bpy.types.Context):
        if not is_export_file():
            # TODO go load the written log file from disk
            raise Exception("Can only show logs in export file")

        text_data = bpy.data.texts.new("export_log.txt")
        log = SBE_Logger.get_log_text()
        text_data.from_string(log)
        for i in context.screen.areas:
            area: bpy.types.Area = i
            if area.type != 'TEXT_EDITOR':
                continue
            for j in area.spaces:
                space: bpy.types.Space = j
                if space.type != 'TEXT_EDITOR':
                    continue
                text_space: bpy.types.SpaceTextEditor = space
                text_space.text = text_data
                return {'FINISHED'}

        # TODO warn about no text editor being open
        return {'FINISHED'}
