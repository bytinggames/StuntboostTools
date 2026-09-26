"""Everyday tools shared by the STUNTBOOST sidebar and searchable menu."""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

# TODO tk see how we can make this reference constants to ensure proper reference, or maybe have them self register
_TOOL_GROUPS = (
    ("navigation", "Files", (
        ("wm.sb_fast_open", "Fast Open"),
        ("wm.sb_fast_open_prev", "Fast Open Previous"),
        ("wm.sb_fast_open_next", "Fast Open Next"),
    )),
    ("modeling", "Modeling", (
        ("object.sb_set_origin_to_selected", "Set Origin to Selected"),
        ("object.sb_copy_transform_from_active", "Copy Transform from Active"),
        ("object.sb_quick_bevel", "Add Bevel and Shade Smooth"),
    )),
    ("collision", "Collision & Visibility", (
        ("object.sb_make_collider", "Add Collider for Selection"),
        ("object.sb_show_colliders", "Show Colliders"),
        ("object.sb_hide_colliders", "Hide Colliders"),
        ("object.sb_show_all", "Unhide All (Including Linked)"),
    )),
    ("outlines", "Outlines", (
        ("object.sb_outline_shift", "Outline Shift"),
        ("object.sb_outline_shift_relative", "Outline Shift Relative"),
        ("object.sb_outline_shrink_relative", "Outline Shrink Relative"),
    )),
    ("assets", "Asset Authoring", (
        ("object.sb_create_collection_asset", "Create Asset Collection"),
        ("object.sb_collection_offset_to_selection", "Collection Offset to Active Object"),
        ("object.sb_refresh_library_previews", "Refresh Asset Previews"),
        ("object.sb_library_previews_from_viewport", "Asset Preview from Viewport"),
    )),
    ("viewport", "Viewport & Snapping", (
        ("wm.sb_toggle_snap_mode", "Toggle Custom Snap Mode"),
        ("object.sb_setup_viewport_cameras", "Set Up Units, Clipping and FOV"),
        ("object.sb_zoom_to_reallife", "Zoom to Real Life"),
    )),
    ("materials", "Materials & Diagnostics", (
        ("object.sb_sync_transparent_shadow", "Sync Transparent Shadows (All Materials)"),
        ("object.sb_print_by_vert_count", "Print Poly Counts to Console"),
    )),
    ("camera", "Camera Animation", (
        ("object.sb_export_camera_anim", "Export Camera Animation"),
        ("object.sb_render_camera_anim", "Render Camera Animation in Game"),
    )),
)


def _available_tools(tools):
    # Respect the loader's module blacklist without importing/registering operators.
    for operator, label in tools:
        namespace, name = operator.split(".", 1)
        if bpy.types.Operator.bl_rna_get_subclass_py(namespace.upper() + "_OT_" + name):
            yield operator, label


def _draw_tools(layout, tools, context, group):
    # Viewport operations need the WINDOW region, not the sidebar's UI region.
    layout.operator_context = 'INVOKE_REGION_WIN'
    if group == "camera":
        layout.enabled = context.active_object is not None and context.active_object.type == 'CAMERA'
    for operator, label in tools:
        layout.operator(operator, text=label)


class SB_LevelDesignPanel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_sb_level_design"
    bl_label = "Level Design"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "STUNTBOOST"
    bl_order = -1
    bpl_auto_load = True

    def draw(self, context: bpy.types.Context):
        for group, label, tools in _TOOL_GROUPS:
            available = tuple(_available_tools(tools))
            if not available:
                continue
            header, body = self.layout.panel("sb_" + group, default_closed=group not in {"navigation", "modeling", "collision"})
            header.label(text=label)
            if body is not None:
                _draw_tools(body.column(align=True), available, context, group)
