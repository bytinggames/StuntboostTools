import importlib.util
from pathlib import Path
import stat
import sys
import tempfile
import traceback

import bpy

bl_info = {
    "name": "STUNTBOOST Blender Plugin Loader",
    "blender": (4, 3, 0),
    "version": (0, 0, 1),
    "category": "Generic",
    "author": "tobi",
}

_runtime = None
_load_error = ""
_RUNTIME_FILE = Path("blender_addons") / "stuntboost_bpl_runtime.py"


def load_runtime():
    global _runtime, _load_error
    root = Path(bpy.app.binary_path).parent
    path = next((path for path in (
        root / "game" / "ModTools" / _RUNTIME_FILE,
        root / "repo" / _RUNTIME_FILE,
    ) if path.is_file()), None)
    if path is None:
        _load_error = "Tools not found. Choose the STUNTBOOST game folder below."
        return
    spec = importlib.util.spec_from_file_location("stuntboost_bpl_runtime", path)
    runtime = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runtime
    try:
        spec.loader.exec_module(runtime)
        runtime.register()
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        _load_error = f"Could not load {path}: {exc}"
        traceback.print_exc()
        return
    _runtime = runtime
    _load_error = ""


def is_directory_link(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or (
        sys.platform == "win32" and info.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
    )


class BPL_SetGamePath(bpy.types.Operator):
    """Create or update the game directory link beside Blender; restart to load its tools"""
    bl_idname = "wm.bpl_set_game_path"
    bl_label = "Choose STUNTBOOST Game Folder"

    directory: bpy.props.StringProperty(subtype='DIR_PATH', options={'SKIP_SAVE'})

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, _context):
        link = Path(bpy.app.binary_path).parent / "game"
        try:
            if not self.directory:
                raise ValueError("Choose the STUNTBOOST installation folder.")
            target = Path(bpy.path.abspath(self.directory)).resolve(strict=True)
            tools = target / "ModTools" / "blender_addons"
            if not (tools / _RUNTIME_FILE.name).is_file() or not (tools / "bpl_auto_load").is_dir():
                raise ValueError("Choose a game folder containing ModTools/blender_addons and its runtime and plugins.")
            if link.resolve() != target:
                if link.exists() and not is_directory_link(link):
                    raise ValueError(f"Refusing to replace an existing file or directory: {link}")
                # Create first so a permissions failure leaves the existing link intact.
                with tempfile.TemporaryDirectory(prefix=".stuntboost-link-", dir=link.parent) as temporary:
                    replacement = Path(temporary) / "game"
                    if sys.platform == "win32":
                        import _winapi
                        _winapi.CreateJunction(str(target), str(replacement))
                    else:
                        replacement.symlink_to(target, target_is_directory=True)
                    # Windows cannot replace a directory link directly.
                    previous = Path(temporary) / "previous"
                    if is_directory_link(link):
                        link.rename(previous)
                    try:
                        replacement.rename(link)
                    except OSError:
                        if is_directory_link(previous):
                            previous.rename(link)
                        raise
        except (OSError, ValueError) as exc:
            if isinstance(exc, PermissionError):
                message = f"Cannot write beside Blender. Use a writable Blender installation folder. {exc}"
            else:
                message = str(exc)
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
        self.report({'INFO'}, "Game folder linked. Restart Blender to load its tools.")
        return {'FINISHED'}


class BPL_Preferences(bpy.types.AddonPreferences):
    bl_idname = "stuntboost_bpl"

    def update_hot_reload(self, _context):
        if _runtime is not None:
            _runtime.set_file_watching(self.watch_python_files)

    watch_python_files: bpy.props.BoolProperty(
        name="Python Hot Reload",
        description="Watch plugin files for changes; when disabled, plugins only load when BPL starts",
        default=True,
        update=update_hot_reload,
    )

    revert_on_reload: bpy.props.BoolProperty(
        name="Revert File on Hot Reload",
        description="Restore original blend state when a python module is reloaded for faster debugging.",
    )

    def draw(self, context):
        layout = self.layout
        if _load_error:
            layout.label(text=_load_error, icon='ERROR')
        layout.label(text=f"Game: {(Path(bpy.app.binary_path).parent / 'game').resolve()}")
        layout.operator(BPL_SetGamePath.bl_idname, icon='FILE_FOLDER')
        layout.label(text="Restart Blender after changing the game folder.")
        layout.prop(self, "watch_python_files")
        if _runtime is not None:
            layout.separator()
            layout.label(text=f"Runtime: {_runtime.__file__}")
            _runtime.draw_preferences(self, context)


def register():
    bpy.utils.register_class(BPL_SetGamePath)
    bpy.utils.register_class(BPL_Preferences)
    load_runtime()


def unregister():
    global _runtime, _load_error
    if _runtime is not None:
        _runtime.unregister()
        sys.modules.pop(_runtime.__name__, None)
        _runtime = None
    _load_error = ""
    bpy.utils.unregister_class(BPL_Preferences)
    bpy.utils.unregister_class(BPL_SetGamePath)
