"""Fast menu to open common scenes scene"""

import dataclasses
import typing
import glob
import os

# pylint: disable=import-error
import bpy
import stuntboost_bpl_runtime
# pylint: enable=import-error

from bake_v3.sbe_util import get_level_order, get_level_name

FAST_OPEN_OP="wm.sb_fast_open"
FAST_OPEN_NEXT_OP="wm.sb_fast_open_next"
FAST_OPEN_PREV_OP="wm.sb_fast_open_prev"

PREV_PREFIX="Previous Level"
NEXT_PREFIX="Next Level"

@dataclasses.dataclass
class MenuItem():
    name: str
    file_path: str
    children: list[typing.Self]

Current: list[MenuItem] = None
"""Currently selected sub list of items"""

def get_key_for_i(i: int) -> str:
    if 19 < i:
        return "" # keys over 20 don't have a blender default binding and also no hotkey from our mapping
    number = f"{(i + 1) % 10}"
    # skip z/y because of german keyboard layout, don't want to find out the current keyboard layout here
    mapping = ["U", "I", "O", "P", "J", "Q", "W", "E", "R", "T", "A", "S", "D", "F", "G", "X", "C", "V"]
    if i < len(mapping):
        return f"{number}  {mapping[i]}"
    return number

def get_title(key: str, name: str) -> str:
    pad = 10
    if key.find("alt"):
        pad += 5 #  font is not monospace
    return "\t" * max(1, (pad - len(key))) + key + "    " + name


def build_folder(path: str, key: str, level_oder: list[str] = [], recursive=False) -> MenuItem:
    if not os.path.isdir(path):
        return None
    if recursive:
        globbed = glob.glob(os.path.join(path, "**", "*.blend"), recursive=True)
    else:
        globbed = glob.glob(os.path.join(path, "*.blend"), recursive=False)
    globbed.sort()
    # Sort all known levels according to the level order.
    for i in reversed(level_oder):
        for j in globbed[:]:
            if i == get_level_name(j):
                globbed.remove(j)
                globbed.insert(0, j)

    result = MenuItem(name=get_title(key, os.path.basename(path)), file_path=path, children=[])
    for i, blend in enumerate(globbed):
        result.children.append(MenuItem(
            name=get_title(get_key_for_i(i), get_level_name(blend)),
            file_path=blend, children=None)
        )
    result.children.append(MenuItem(name=get_title("B", "Back"), file_path=None, children=None))
    return result

def build_items() -> list[MenuItem]:
    game_path = stuntboost_bpl_runtime.get_game_path()
    level_order = get_level_order()
    index = 0

    def add_item(path: str, recursive:bool=True):
        nonlocal index
        result = build_folder(path=path, key=get_key_for_i(index), level_oder=level_order, recursive=recursive)
        if result is not None:
            index += 1
        return result

    if stuntboost_bpl_runtime.is_repo():
        items = [
            add_item(os.path.join(game_path, "SE", "Content", "Models", "Sascha")),
            add_item(os.path.join(game_path, "SE", "Content", "Models", "New")),
            add_item(os.path.join(game_path, "SE", "Content", "Models", "Bonus")),
            add_item(os.path.join(game_path, "SE", "Content", "Models", "Unassigned")),
            add_item(os.path.join(game_path, "SE", "Content", "Models", "Test")),
            add_item(os.path.join(game_path, "SE", "Content", "Models", "Props")),
            add_item(os.path.join(game_path, "SE", "Content", "Models", "Rooms")),
            add_item(os.path.join(game_path, "SE", "Content", "Models"), False),
            add_item(os.path.join(game_path, "..", "SEMeta", "ArtSource")),
            add_item(os.path.join(game_path, "..", "SEMeta", "ArtDirection")),
            add_item(os.path.join(game_path, "..", "SEMeta", "PR")),
            add_item(os.path.join(game_path, "..", "SEMeta", "LevelDesign")),
        ]
    else:
        items = [
            add_item(os.path.join(os.path.dirname(bpy.app.binary_path), "levels")),
            add_item(os.path.join(game_path, "StuntboostTools", "assets")),
            add_item(os.path.join(game_path, "StuntboostTools", "examples")),
        ]

    items = [item for item in items if item is not None]

    if bpy.data.filepath:
        load_next = False
        last: MenuItem = None
        for i in items[:]:
            for j in i.children:
                item: MenuItem = j

                if load_next:
                    if item and item.file_path:
                        items.append(MenuItem(
                            name=get_title(get_key_for_i(16), f"{NEXT_PREFIX} {get_level_name(item.file_path)}"),
                            file_path=item.file_path, children=None))
                        return items

                if item.file_path == bpy.data.filepath:
                    load_next = True
                    if last and last.file_path:
                        items.append(MenuItem(
                            name=get_title(get_key_for_i(15), f"{PREV_PREFIX} {get_level_name(last.file_path)}"),
                            file_path=last.file_path, children=None))
                if item and item.file_path:
                    last = item
    return items


class SB_FastOpenMenu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_fast_open_menu"
    bl_label = "SB Fast Open"
    bpl_auto_load = True

    def draw(self, _context: bpy.types.Context):
        layout: bpy.types.UILayout = self.layout
        for i, item in enumerate(Current):
            op = layout.operator(FAST_OPEN_OP, text=item.name)
            op.menu_index = i


class SB_FastOpen(bpy.types.Operator):
    """Fast Open"""
    bl_idname = FAST_OPEN_OP
    bl_label = "Fast Open"
    bpl_auto_load = True
    menu_index: bpy.props.IntProperty(default=-1)

    def execute(self, _context: bpy.types.Context):
        global Current
        if Current is None:
            Current = build_items()
        if self.menu_index != -1:
            item = Current[self.menu_index]
            if item.children:
                Current = item.children
            else:
                self.menu_index = -1
                if item.file_path:
                    Current = None
                    if not bpy.data.is_saved and bpy.data.filepath != '':
                        bpy.ops.wm.save_as_mainfile()
                    bpy.ops.wm.open_mainfile(filepath=item.file_path)
                    return {'FINISHED'}
                Current = build_items()

        bpy.ops.wm.call_menu(name=SB_FastOpenMenu.bl_idname)
        return {'INTERFACE'}


class SB_FastOpenNext(bpy.types.Operator):
    """Fast Open Next"""
    bl_idname = FAST_OPEN_NEXT_OP
    bl_label = "Fast Open Next"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        if not bpy.data.filepath:
            return {'FINISHED'} # can't execute
        items = build_items()
        for i in items:
            if i.name.find(NEXT_PREFIX) != -1:
                if not bpy.data.is_saved and bpy.data.filepath != '':
                    bpy.ops.wm.save_as_mainfile()
                bpy.ops.wm.open_mainfile(filepath=i.file_path)
                break
        return {'FINISHED'}


class SB_FastOpenPrev(bpy.types.Operator):
    """Fast Open Previous"""
    bl_idname = FAST_OPEN_PREV_OP
    bl_label = "Fast Open Previous"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        if not bpy.data.filepath:
            return {'FINISHED'} # can't execute
        items = build_items()
        for i in items:
            if i.name.find(PREV_PREFIX) != -1:
                if not bpy.data.is_saved and bpy.data.filepath != '':
                    bpy.ops.wm.save_as_mainfile()
                bpy.ops.wm.open_mainfile(filepath=i.file_path)
                break
        return {'FINISHED'}