import os
import subprocess
import tempfile
from pathlib import Path

# pylint: disable=import-error
import bpy
from bpy.app.handlers import persistent
import stuntboost_bpl_runtime
# pylint: enable=import-error

from bake_v3.sbe_util import get_filename_without_extension

is_windows = os.name == 'nt'
video_folder_name = os.path.join("stuntboost_video", "replays")
game_binary_relative  = os.path.join("SE", "bin", "Debug", "net8.0", "STUNTBOOST")
CHECK_INTERVAL_SEC = 3

def run_export(path: str):
    folder = os.path.dirname(path)
    Path(folder).mkdir(parents=True, exist_ok=True)

    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLTF_SEPARATE',
        use_active_collection=False,
        # use_active_collection_with_nested=True,
        use_selection=True,
        use_visible=False,
        use_renderable=False,

        # This is important, because otherwise
        # the active scene can be wrong and selected objects from others scenes will be exported too
        use_active_scene=True,

        export_yup=True,
        export_apply=True, # apply modifiers
        will_save_settings=False,
        export_cameras=True, # for exporting PreviewCameras
        export_keep_originals=True,
        export_materials='EXPORT',
        export_image_format='AUTO',
        export_force_sampling=True,
        # or 'NLA_TRACKS' or 'ACTIONS' 'SCENE' maybe we don't need to bake nla actions before then?
        export_animation_mode='ACTIONS',
        export_bake_animation=True,
        export_optimize_animation_size=False,
        export_lights=True,
        export_extras=True, # We want to move the name logic in here
        export_attributes=True, # this ensures exporting attributes starting with an '_'
        export_vertex_color='NONE', # we only need our custom _color_shift attribute, so disable this
        export_all_vertex_colors=False, # we only need our custom _color_shift attribute, so disable this 
        export_active_vertex_color_when_no_material=False, # we only need our custom _color_shift attribute, so disable this
        export_unused_images=False,
        export_unused_textures=False,
    )


class SB_ExportCameraAnim(bpy.types.Operator):
    """Export the selected camera animation"""
    bl_idname = "object.sb_export_camera_anim"
    bl_label = "Export camera anim"
    bpl_auto_load = True

    def execute(self, context: bpy.types.Context):
        if not context.active_object or context.active_object.type != 'CAMERA':
            return {'CANCELLED'}
        target_path = os.path.join(tempfile.gettempdir(), video_folder_name, "animation.camani.gltf")
        run_export(target_path)
        return {'FINISHED'}



def message_box(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

class SB_PollRenderQue():
    sub_processes: list[subprocess.Popen] = []
    handler_registered = False

    @staticmethod
    @persistent
    def poll_tasks():
        for i in SB_PollRenderQue.sub_processes[:]:
            result = i.poll()
            if result is not None:
                message = f"Done rendering video with exitcode {result}."
                
                SB_PollRenderQue.sub_processes.remove(i)
                if SB_PollRenderQue.sub_processes:
                    message += f" {len(SB_PollRenderQue.sub_processes)} video remaining."
                print(message)
                message_box(message, "Rendering Done")
        return CHECK_INTERVAL_SEC

    @staticmethod
    def add_task(sub_process: subprocess.Popen):
        if not SB_PollRenderQue.handler_registered:
            # lazy registration so there aren't 50 poll handlers going on from the other plugins
            bpy.app.timers.register(
                function=SB_PollRenderQue.poll_tasks,
                first_interval=CHECK_INTERVAL_SEC, persistent=True)
            SB_PollRenderQue.handler_registered = True
        SB_PollRenderQue.sub_processes.append(sub_process)
        print("Start rendering video...")


    @staticmethod
    def bpl_load():
        pass

    @staticmethod
    def bpl_unload():
        if bpy.app.background:
            return
        if SB_PollRenderQue.handler_registered:
            bpy.app.timers.unregister(SB_PollRenderQue.poll_tasks)


class SB_RenderCameraAnim(bpy.types.Operator):
    """Export the selected camera animation and render"""
    bl_idname = "object.sb_render_camera_anim"
    bl_label = "Render camera anim"
    bpl_auto_load = True

    def execute(self, context: bpy.types.Context):
        if not context.active_object or context.active_object.type != 'CAMERA':
            return {'CANCELLED'}
        current_level = get_filename_without_extension()
        current_level = current_level.replace("Level_", "")
        target_path = os.path.join(tempfile.gettempdir(), video_folder_name, f"{current_level}_{context.active_object.name}.camani.gltf")
        run_export(target_path)
        
        repo_path = stuntboost_bpl_runtime.get_repo_path()
        game_binary_path = os.path.join(repo_path, game_binary_relative)
        if is_windows:
            game_binary_path = game_binary_path + ".exe"
        
        command = [game_binary_path, target_path, current_level]
        print(command)
        sub = subprocess.Popen(command)
        SB_PollRenderQue.add_task(sub)

        return {'FINISHED'}


