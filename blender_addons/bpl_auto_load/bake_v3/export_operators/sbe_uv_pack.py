# pylint: disable=import-error
import bpy
import bmesh
import mathutils
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_PACK_UVS
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_util import get_bake_target_objects
from bake_v3.sbe_custom_properties import (
    SBE_MESH_UV_SCALE_ATTRIBUTE, SBE_MESH_UV_ASPECT_ATTRIBUTE
)
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties

def smart_project(context: bpy.types.Context, obj: bpy.types.Object):
    bpy.ops.object.select_all(action='DESELECT')
    context.view_layer.objects.active = obj
    obj.select_set(state=True, view_layer=context.view_layer)
    bpy.ops.object.mode_set(mode='EDIT')
    context.scene.tool_settings.use_uv_select_sync = False # Maybe faster?
    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(
        margin_method='FRACTION',
        island_margin=0,
        rotate_method='AXIS_ALIGNED',
    )
    bpy.ops.object.mode_set(mode='OBJECT')


def minimum_primitive_size(obj: bpy.types.Object, resolution: int):
    # Round up all the faces to occupy at least one pixel on the bake map
    # TODO This isn't good and won't work on very long faces
    bm = bmesh.from_edit_mesh(obj.data)

    uv_layer = bm.loops.layers.uv.active

    for i in bm.faces:
        face: bmesh.types.BMFace = i

        face_count = int(0)
        center = mathutils.Vector((0, 0))
        last_vert = None
        corner_length = 0

        for j in face.loops:
            loop: bmesh.types.BMLoop = j
            uv_access: bmesh.types.BMLayerAccessLoop = loop[uv_layer]
            uv: mathutils.Vector = uv_access.uv.copy()
            # if 1 < uv.x or 1 < uv.y or uv.x < 0 or uv.y < 0:
            #     SBE_Logger.print("Packed UVs out of range")
            center = center + uv
            face_count += 1
            if last_vert:
                diff = last_vert - uv
                corner_length += diff.length
                last_vert = uv

        if face_count != 4:
            continue

        if (4.0 / float(resolution)) < corner_length:
            center_x = center.x / float(face_count)
            center_y = center.y / float(face_count)
            center_x = round(center_x * float(resolution))
            center_y = round(center_y * float(resolution))
            corners: list[bmesh.types.BMLayerAccessLoop] = []
            for j in face.loops:
                loop: bmesh.types.BMLoop = j
                uv: bmesh.types.BMLayerAccessLoop = loop[uv_layer]
                corners.append(uv)
            corners[0].uv.x = center_x / resolution
            corners[0].uv.y = center_y / resolution

            corners[1].uv.x = (center_x + 1) / resolution
            corners[1].uv.y = center_y / resolution

            corners[2].uv.x = (center_x + 1) / resolution
            corners[2].uv.y = (center_y + 1) / resolution

            corners[3].uv.x = center_x / resolution
            corners[3].uv.y = (center_y + 1) / resolution

    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)


def scale_uvs(obj: bpy.types.Object):
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    uv_layer = bm.loops.layers.uv.active
    uv_scale_layer = bm.loops.layers.float[SBE_MESH_UV_SCALE_ATTRIBUTE]
    uv_aspect_layer = bm.loops.layers.float[SBE_MESH_UV_ASPECT_ATTRIBUTE]

    has_warned = False

    # Apply scaling from the collection and vertex groups
    for i in bm.faces:
        face: bmesh.types.BMFace = i
        for j in face.loops:
            loop: bmesh.types.BMLoop = j
            uv: bmesh.types.BMLayerAccessLoop = loop[uv_layer]
            scale: float = loop[uv_scale_layer]
            aspect: float = loop[uv_aspect_layer]
            if  scale < 0.0001:
                if not has_warned:
                    SBE_Logger.print(f"Warning, {obj.name} no uv scale present while unwrapping.")
                    has_warned = True
                continue
            uv.uv *= scale
            uv.uv.x *= aspect
    # bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    bm.to_mesh(obj.data)
    bm.free()


def pack_uvs(resolution: int, bake_margin: int):
    bpy.ops.uv.pack_islands(
        # margin_method='FRACTION', # this one leaves large spaces free but the margins seem precise
        # margin=((bake_margin / 2.0) / resolution),

        # margin_method='ADD', # margin should be larger because this behaves weird
        # margin=0.01,

        margin_method='SCALED',
        # margins are too large by default, but this wastes less space
        margin=((bake_margin / 4.0) / resolution),

        rotate=True,
        rotate_method='CARDINAL', # important to keep the flow of pixels along the edges

        scale=True, # important to make it fit

        # shape_method='CONCAVE', # this seems buggy when called from the here and not the UI, maybe works on CLOSEST_UDIM? Still far from optimal
        # shape_method='CONVEX', # This works, but takes 10x as long, and results are probably like AABB
        shape_method='AABB', # good enough and fast

        merge_overlap=False, # TOOD what does this do?
        udim_source='CLOSEST_UDIM' # there should only be one
    )

def setup_uvs(context: bpy.types.Context, obj: bpy.types.Object, resolution: int, bake_margin: int) -> None:
    if len(obj.data.vertices) == 0:
        return
    if len(obj.data.uv_layers) == 0:
        obj.data.uv_layers.new()

    bpy.ops.object.select_all(action='DESELECT')
    context.view_layer.objects.active = obj
    obj.select_set(state=True, view_layer=context.view_layer)

    bpy.ops.object.mode_set(mode='EDIT')
    context.scene.tool_settings.use_uv_select_sync = False # Maybe faster?
    context.scene.tool_settings.uv_sticky_select_mode = 'DISABLED'
    # bpy.ops.uv.select_mode(type='VERTEX')
    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')

    # smart_project(context=context, obj=obj)

    bpy.ops.uv.average_islands_scale()

    # If we do it in one go the packer fucks up sometimes
    # so we leave edit mode here to scale the uvs
    bpy.ops.object.mode_set(mode='OBJECT')

    scale_uvs(obj=obj)
    # context.view_layer.update()
    # context.view_layer.depsgraph.update()
    bpy.ops.object.mode_set(mode='EDIT')
    pack_uvs(resolution=resolution, bake_margin=bake_margin)
    bpy.ops.object.mode_set(mode='OBJECT')

    # minimum_primitive_size(obj=obj, resolution=resolution)



class SBE_PackUVs(SBE_ExportOperatorBase):
    """Setup the uvs for the generated bake mesh"""
    bl_idname = SBE_OP_PACK_UVS
    bl_label = "Pack UVs"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        targets: list[bpy.types.Object] = get_bake_target_objects(context)
        for target in targets:
            collection = target.users_collection[0]
            bake_props = SBE_CollectionProperties.evaluate_bake_prop(owner=collection)
            resolution = int(bake_props.resolution * bake_props.resolution_relative)
            setup_uvs(context=context, obj=target, resolution=resolution, bake_margin=bake_props.margin)
