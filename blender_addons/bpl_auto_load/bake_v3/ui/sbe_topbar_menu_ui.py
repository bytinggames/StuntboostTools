"""Adds the menu in the top bar between the menues and workspaces"""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import (
    SBE_OP_BUILD_LEVEL, SBE_OP_SHOW_LOGS, SBE_OP_INSPECT_SCENE,
    SBE_OP_BUILD_SELECTION, SBE_OP_TOGGLE_ORIGINAL
)

from bake_v3.sbe_util import is_export_file

def sbe_top_bar_menu_draw(self: bpy.types.Menu, _context: bpy.types.Context) -> None:
    layout: bpy.types.UILayout = self.layout
    layout.menu(SBE_TopBarMenu.bl_idname)


class SBE_TopBarMenu(bpy.types.Menu):
    bl_idname = "SBE_MT_topbar_menu"
    bl_label = "STUNTBOOST"

    def draw(self, _context: bpy.types.Context) -> None:
        layout: bpy.types.UILayout = self.layout
        if not is_export_file():
            layout.operator(SBE_OP_BUILD_LEVEL)
            layout.operator(SBE_OP_BUILD_SELECTION)

            # TODO
            # layout.separator()
            # layout.operator(SBE_OP_FAST_BUILD_SCENE)

            layout.separator()
            layout.operator(SBE_OP_INSPECT_SCENE)
        
        layout.operator(SBE_OP_TOGGLE_ORIGINAL)
        layout.operator(SBE_OP_SHOW_LOGS)

    @staticmethod
    def bpl_load() -> None:
        bpy.utils.register_class(SBE_TopBarMenu)
        bpy.types.TOPBAR_MT_editor_menus.append(sbe_top_bar_menu_draw)

    @staticmethod
    def bpl_unload() -> None:
        bpy.types.TOPBAR_MT_editor_menus.remove(sbe_top_bar_menu_draw)
        bpy.utils.unregister_class(SBE_TopBarMenu)
