"""Move selected objects into outline_shift// collections."""

# pylint: disable=import-error
import re

import bpy
from mathutils import Vector

from bake_v3.sbe_collection_util import get_collection_parent
# pylint: enable=import-error


COLLECTION_NAME = "outline_shift//"
COLLECTION_NAME_RELATIVE = "outline_shift_relative//"
COLLECTION_NAME_SHRINK_RELATIVE = "outline_shrink_relative//"
EMPTY_NAME = "//outline_shift"
EMPTY_NAME_SHRINK = "//outline_shrink"

OUTLINE_SHIFT_ZERO_NAME = "outline_shift=0"
_DUPLICATE_SUFFIX_RE = re.compile(r"\.\d{3}$")


def _get_view_spawn_location(context: bpy.types.Context, fallback_location):
    """Return a point close in front of the 3D viewport's camera
    (not the view's focus point, which may be behind obstructing
    geometry), so a newly created object is immediately visible.
    Falls back to `fallback_location` when not called from a 3D
    viewport."""

    region_3d = getattr(context.space_data, 'region_3d', None)

    if region_3d is None:
        return fallback_location.copy()

    view_matrix_inv = region_3d.view_matrix.inverted()
    eye = view_matrix_inv.translation
    forward = view_matrix_inv.to_3x3() @ Vector((0.0, 0.0, -1.0))

    # Scale the distance with the current zoom level, so the arrow
    # ends up close to the camera regardless of scene/view scale.
    distance = max(region_3d.view_distance * 0.5, 0.1)

    return eye + forward * distance


def _is_outline_shift_zero_collection(name: str) -> bool:
    """True for a collection named "outline_shift=0", optionally with a
    Blender duplicate-name suffix (e.g. ".001") and/or a "//comment"
    suffix, e.g. "outline_shift=0", "outline_shift=0//unused" or
    "outline_shift=0.001"."""

    name = _DUPLICATE_SUFFIX_RE.sub("", name, count=1)

    if not name.startswith(OUTLINE_SHIFT_ZERO_NAME):
        return False

    rest = name[len(OUTLINE_SHIFT_ZERO_NAME):]
    return rest == "" or rest.startswith("//")


def _resolve_source_collection(operator: bpy.types.Operator, collection: bpy.types.Collection):
    """Returns the collection that new outline_shift// collections should
    be nested in for objects directly in `collection`.

    If `collection` is itself "outline_shift=0" (optionally nested in
    further consecutive "outline_shift=0" collections), this walks up
    past all of them and returns the first ancestor that isn't one.

    If an "outline_shift=0" collection sits further up the hierarchy
    without the object being *directly* nested in it (i.e. there's a
    non "outline_shift=0" collection in between), a warning is reported
    and None is returned, so the caller can abort.
    """

    current = collection

    while current is not None and _is_outline_shift_zero_collection(current.name):
        current = get_collection_parent(current)

    if current is None:
        operator.report(
            {'WARNING'},
            f'"{collection.name}" is nested only in "{OUTLINE_SHIFT_ZERO_NAME}" collections '
            "all the way to the scene root."
        )
        return None

    # make sure no other "outline_shift=0" collection sits further up the
    # hierarchy - that would mean the object isn't *directly* nested in it
    ancestor = get_collection_parent(current)
    while ancestor is not None:
        if _is_outline_shift_zero_collection(ancestor.name):
            operator.report(
                {'WARNING'},
                f'"{collection.name}" is nested inside "{OUTLINE_SHIFT_ZERO_NAME}" collection '
                f'"{ancestor.name}", but not directly - aborting.'
            )
            return None
        ancestor = get_collection_parent(ancestor)

    return current


def _outline_shift(
    operator: bpy.types.Operator,
    context: bpy.types.Context,
    collection_name: str,
    empty_name: str = EMPTY_NAME,
):

    selected_objects = context.selected_objects[:]

    if not selected_objects:
        operator.report({'WARNING'}, "No objects selected")
        return {'CANCELLED'}

    cursor = context.scene.cursor
    spawn_location = _get_view_spawn_location(context, cursor.location)

    # ---------------------------------------------------------
    # Find the original collections of the selected objects,
    # resolving "outline_shift=0" collections out of the way first
    # (see _resolve_source_collection). Each resolved collection
    # gets its own outline_shift// collection. Aborts (without
    # changing anything) if an object is only indirectly nested in
    # an "outline_shift=0" collection.
    # ---------------------------------------------------------

    source_collections = {}

    for obj in selected_objects:
        for collection in obj.users_collection:

            resolved_collection = _resolve_source_collection(operator, collection)
            if resolved_collection is None:
                return {'CANCELLED'}

            if resolved_collection not in source_collections:
                source_collections[resolved_collection] = []

            source_collections[resolved_collection].append((obj, collection))

    # ---------------------------------------------------------
    # Create an outline_shift// collection for each source
    # collection.
    # ---------------------------------------------------------

    created_empties = []

    for source_collection, objects in source_collections.items():

        outline_collection = bpy.data.collections.new(
            collection_name
        )

        # Put the new collection inside the (possibly resolved) source collection.
        source_collection.children.link(outline_collection)

        # -----------------------------------------------------
        # Move selected objects from their original collection
        # into the new outline collection.
        # -----------------------------------------------------

        for obj, original_collection in objects:

            outline_collection.objects.link(obj)
            original_collection.objects.unlink(obj)

        # -----------------------------------------------------
        # Create the arrow, right in front of the view so it's
        # immediately visible to the user.
        # -----------------------------------------------------

        empty = bpy.data.objects.new(
            empty_name,
            None
        )

        empty.empty_display_type = 'SINGLE_ARROW'
        empty.matrix_world = cursor.matrix
        empty.location = spawn_location

        outline_collection.objects.link(empty)
        created_empties.append(empty)

    # ---------------------------------------------------------
    # Select only the newly created arrows, and set up snapping
    # so they can be snapped onto a surface by hand (move + Ctrl).
    # ---------------------------------------------------------

    for obj in context.selected_objects:
        obj.select_set(False)

    for empty in created_empties:
        empty.select_set(True)

    context.view_layer.objects.active = created_empties[-1]

    tool_settings = context.scene.tool_settings
    tool_settings.transform_pivot_point = 'MEDIAN_POINT'
    tool_settings.snap_target = 'CENTER'
    tool_settings.use_snap_align_rotation = True

    if hasattr(tool_settings, 'snap_elements_base'):
        tool_settings.snap_elements_base = {'FACE'}
    else:
        tool_settings.snap_elements = {'FACE'}

    operator.report(
        {'INFO'},
        f"Created {len(source_collections)} {collection_name} collection(s)"
    )

    return {'FINISHED'}


class SB_OutlineShift(bpy.types.Operator):
    """Move selected objects into outline_shift// collections"""
    bl_idname = "object.sb_outline_shift"
    bl_label = "Outline Shift"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        return _outline_shift(self, context, COLLECTION_NAME)


class SB_OutlineShiftRelative(bpy.types.Operator):
    """Move selected objects into outline_shift_relative// collections"""
    bl_idname = "object.sb_outline_shift_relative"
    bl_label = "Outline Shift Relative"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        return _outline_shift(self, context, COLLECTION_NAME_RELATIVE)


class SB_OutlineShrinkRelative(bpy.types.Operator):
    """Move selected objects into outline_shrink_relative// collections"""
    bl_idname = "object.sb_outline_shrink_relative"
    bl_label = "Outline Shrink Relative"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        return _outline_shift(self, context, COLLECTION_NAME_SHRINK_RELATIVE, EMPTY_NAME_SHRINK)
