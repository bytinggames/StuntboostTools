"""
Logic related to shifting objects around to make space for thick outlines.
"""


import sys

# pylint: disable=import-error
import bpy
import bmesh
import mathutils
# pylint: enable=import-error

from bake_v3.sbe_custom_properties import (
    SBE_VERTEX_SHIFT_ATTRIBUTE, SBE_FORCE_VERTEX_SHIFT_ATTRIBUTE
)
from bake_v3.sbe_name_parser import get_function_arguments, name_starts_with_independent_of_comment
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_collection_util import get_collections_parents

def _get_outline_shift(args, collection, obj_name="outline_shift"):
    shift = [0.0, 0.0, 0.0]
    if len(args) == 0:
        # when no values are passed as an argument, use the first outline_shift node in this collection
        for obj in collection.objects:
            if name_starts_with_independent_of_comment(obj.name, obj_name):
                up = mathutils.Vector((0,0,1))
                rotation = obj.matrix_world.to_quaternion().inverted().to_matrix()
                up = up @ rotation
                up.normalize()
                shift[0] += up.x
                shift[1] += up.y
                shift[2] += up.z
    else:
        for i in range(min(3, len(args))):
            shift[i] = float(args[i])
    return shift

# apply shrink to all vertex colors
# shrinking is like shifting, but with the difference, that the shift
# fades out towards the end of the object, making the object shrink
def _shrink_outline_shift_vertex_colors(bm: bmesh.types.BMesh,
    layer: bmesh.types.BMLayerItem,  shrink: list[float], first_shrink: bool):

    shrink = [shrink[0] * 0.1, shrink[1] * 0.1, shrink[2] * 0.1]
    # get highest and lowest vertex (in regards to shrink direction)
    min_h = sys.float_info.max
    max_h = -min_h
    shrink_dir = mathutils.Vector((shrink[0], shrink[1], shrink[2]))

    if not first_shrink:
        shrink_dir = -shrink_dir

    for i in bm.verts:
        vert: bmesh.types.BMVert = i
        height = vert.co.dot(shrink_dir)
        max_h = max(max_h, height)
        min_h = min(min_h, height)

    height_range = max_h - min_h
    if height_range > 0: # no need to shrink if all vertices have the same height
        if first_shrink:
            # negative, as we expect that the shift already happened
            shrink_colors = [-shrink[0], -shrink[1], -shrink[2]]
        else:
            shrink_colors = [shrink[0], shrink[1], shrink[2]]

        for i in bm.verts:
            vert: bmesh.types.BMVert = i
            height = vert.co.dot(shrink_dir)
            lerp = (height - min_h) / height_range
            vert[layer][0] += shrink_colors[0] * lerp
            vert[layer][1] += shrink_colors[1] * lerp
            vert[layer][2] += shrink_colors[2] * lerp


def setup_outlines(obj: bpy.types.Object) -> None:
    if "custom_normal" in obj.data.attributes:
        # Remote custom normals, since they cause issues when shifting in blender 4.5 and upwards
        obj.data.attributes.remove(obj.data.attributes["custom_normal"])

    if SBE_FORCE_VERTEX_SHIFT_ATTRIBUTE in obj.data.attributes:
        obj.data.attributes[SBE_FORCE_VERTEX_SHIFT_ATTRIBUTE].name = SBE_VERTEX_SHIFT_ATTRIBUTE
        return

    shift: list[float] = [0, 0, 1] # default to up
    shrinks = [] # don't shrink by default
    thickness = 1.0 # default thickness
    shift_modified = False
    if obj.matrix_world[0][0] != 1 or\
        obj.matrix_world[1][1] != 1 or\
        obj.matrix_world[1][1] != 1:
        SBE_Logger.print(f"Warning: outline shift for {obj.name} might be wrong without transform applied")
    assert len(obj.users_collection) == 1, "No multiple collection parents supported! Object: " + obj.name
    parent_collections = get_collections_parents(obj.users_collection[0])


    for i in parent_collections:
        col: bpy.types.Collection = i
        # outline_shift_relative
        args = get_function_arguments(col.name, "outline_shift_relative")
        if args is not None:
            current_shift = _get_outline_shift(args, col)
            shift[0] += current_shift[0]
            shift[1] += current_shift[1]
            shift[2] += current_shift[2]
            shift_modified = True

        # outline_shift
        args = get_function_arguments(col.name, "outline_shift")
        if args is not None:
            current_shift = _get_outline_shift(args, col)
            shift[0] = current_shift[0]
            shift[1] = current_shift[1]
            shift[2] = current_shift[2]
            shift_modified = True

        # outline_shrink_relative
        args = get_function_arguments(col.name, "outline_shrink_relative")
        if args is not None:
            shrink = _get_outline_shift(args, col, "outline_shrink")
            if shrink[0] == 0 and shrink[1] == 0 and shrink[2] == 0:
                # set up vector as default shrink, when nothing else is specified
                shrink[2] = 1
            if len(shrinks) == 0:
                # shrink all objects per default. that way every object is stackable.
                shrinks = [[0,0,1]]
            shrinks.append(shrink)

        # outline_shrink
        args = get_function_arguments(col.name, "outline_shrink")
        if args is not None:
            shrink = _get_outline_shift(args, col, "outline_shrink")
            if shrink[0] == 0 and shrink[1] == 0 and shrink[2] == 0:
                # set up vector as default shrink, when nothing else is specified
                shrink[2] = 1
            shrinks = [shrink]

        # outline_thickness
        args = get_function_arguments(col.name, "outline_max_thickness")
        if args is not None and len(args) > 0:
            thickness = float(args[0])

    # if shift was not specified, but shrink was. take shrink
    if not shift_modified and len(shrinks) > 0:
        shift = [f for f in shrinks[0]] # copy

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    target_attribute_layer: bmesh.types.BMLayerItem = None
    if SBE_VERTEX_SHIFT_ATTRIBUTE not in bm.verts.layers.float_color:
        # converting shift vector [-5,5] to color range [0,1]
        # a color channel of 0.5 means no shift is applied
        shift[0] = shift[0] * 0.1 + 0.5
        shift[1] = shift[1] * 0.1 + 0.5
        shift[2] = shift[2] * 0.1 + 0.5

        target_attribute_layer = bm.verts.layers.float_color.new(SBE_VERTEX_SHIFT_ATTRIBUTE)
        for i in bm.verts:
            vert: bmesh.types.BMVert = i
            vert[target_attribute_layer][0] = shift[0]
            vert[target_attribute_layer][1] = shift[1]
            vert[target_attribute_layer][2] = shift[2]
            vert[target_attribute_layer][3] = thickness

    elif shift[0] != 0 or shift[1] != 0 or shift[2] != 0:
        target_attribute_layer = bm.verts.layers.float_color[SBE_VERTEX_SHIFT_ATTRIBUTE]
        # converting shift vector [-5,5] to relative color range [-0.5,0.5] that is added to the already existing outline shift attribute. That's why we don't need to add 0.5 here
        shift2 = [shift[0] * 0.1, shift[1] * 0.1, shift[2] * 0.1]
        for i in bm.verts:
            vert: bmesh.types.BMVert = i
            vert[target_attribute_layer][0] += shift2[0]
            vert[target_attribute_layer][1] += shift2[1]
            vert[target_attribute_layer][2] += shift2[2]
        
    if len(shrinks) == 0 and not shift_modified:
        # shrink all objects per default. that way every object is stackable.
        shrinks = [[0,0,1]]

    first_shrink = True
    for shrink in shrinks:
        # apply shrink to all vertex colors
        # shrinking is like shifting, but with the difference, that the
        # shift fades out towards the end of the object, making the object shrink
        _shrink_outline_shift_vertex_colors(
            bm=bm, layer=target_attribute_layer,
            shrink=shrink,
            first_shrink=first_shrink)
        first_shrink = False

    bm.to_mesh(obj.data)
    bm.free()


def outline_apply_transform(obj: bpy.types.Object):
    """
    If there are already outlines shifts defined on an object,
    they need to be adjusted for the object transform
    """
    if not SBE_VERTEX_SHIFT_ATTRIBUTE in obj.data.color_attributes:
        return

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    # get matrix without translation
    #mat = obj.matrix_world.to_3x3()
    #mat = mat.inverted()
    # get inverted rotation+scale matrix
    rotation = obj.matrix_world.to_quaternion().inverted().to_matrix()

    # get scale sign
    scale = mathutils.Vector((1.0, 1.0, 1.0))
    unsigned_scale = obj.matrix_world.to_scale()
    if unsigned_scale.x < 0:
        scale.x = -1
    if unsigned_scale.y < 0:
        scale.y = -1
    if unsigned_scale.z < 0:
        scale.z = -1
    
    target_attribute_layer = bm.verts.layers.float_color[SBE_VERTEX_SHIFT_ATTRIBUTE]
    for i in bm.verts:
        vert: bmesh.types.BMVert = i
        vector = mathutils.Vector((
            vert[target_attribute_layer][0] - 0.5,
            vert[target_attribute_layer][1] - 0.5,
            vert[target_attribute_layer][2] - 0.5))
        
        vector = vector @ rotation
        vector *= scale

        vert[target_attribute_layer][0] = vector.x + 0.5
        vert[target_attribute_layer][1] = vector.y + 0.5
        vert[target_attribute_layer][2] = vector.z + 0.5

    bm.to_mesh(obj.data)
    bm.free()
