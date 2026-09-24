"""Does some compatibility conversion from the olf bake script before the new logic runs"""

# pylint: disable=import-error
import bpy
import bmesh
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_COMPATIBILITY
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_name_parser import (
    get_bake_collection_scale, is_bake_group,
    collection_is_discard, collection_is_only_bake,
    object_is_only_bake, object_is_discard,
    object_is_only_game, object_is_solid_collision,
    object_is_trigger_collision, get_bake_scale_vertex_groups,
    scene_is_discard
)
from bake_v3.sbe_mesh_util import ensure_unique_data

from bake_v3.sbe_collection_util import get_collections_parents

from bake_v3.sbe_custom_properties import (
    SBE_MESH_UV_SCALE_ATTRIBUTE,
    SBE_OBJ_SMART_PROJECT_ATTRIBUTE
)

from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.properties.sbe_bake_props import SBE_BakeProperties
from bake_v3.properties.sbe_object_props import SBE_ObjectProperties

def setup_skybox_bake_group(bake_props: SBE_BakeProperties) -> None:
    bake_props.passes = 'COMBINED'
    bake_props.passes_set = True
    bake_props.resolution = 512
    bake_props.resolution_set = True
    bake_props.post_process = True
    bake_props.post_process_set = True
    bake_props.post_process_node = 'post_pro_sky_box'
    bake_props.post_process_node_set = True
    bake_props.margin = 32
    bake_props.margin_set = True

def put_sky_box_in_bake_group():
    """The new code expects sky boxes to be in bake collections also."""
    for i in bpy.data.scenes:
        scene: bpy.types.Scene = i
        if scene.name.find("Skybox") == -1:
            continue
        for j in scene.collection.children:
            col: bpy.types.Collection = j
            props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
            try:
                if props.is_bake_group:
                    return # at least one bake collection, we'll ignore the rest
            except Exception:
                SBE_Logger.print(f"Failed to check {col.name}")

        SBE_Logger.print("Warning, Skybox scene has no bake group, creating one")
        sky_box = bpy.data.collections.new("skybox")
        props: SBE_CollectionProperties = SBE_CollectionProperties.get(sky_box)
        props.is_bake_group = True

        setup_skybox_bake_group(props.bake_debug)
        setup_skybox_bake_group(props.bake_settings)

        for j in scene.collection.objects:
            obj: bpy.types.Object = j
            scene.collection.objects.unlink(obj)
            sky_box.objects.link(obj)
        for j in scene.collection.children:
            collection: bpy.types.Collection = j
            scene.collection.children.unlink(collection)
            sky_box.children.link(collection)
        scene.collection.children.link(sky_box)
        return
    SBE_Logger.print("Warning, scene has no sky box scene")


def put_strays_in_bake_group():
    for i in bpy.data.scenes:
        scene: bpy.types.Scene = i
        if scene_is_discard(scene):
            continue
        if len(scene.collection.objects) == 0:
            continue
        SBE_Logger.print(f"Warning, stray objects at top level in scene {scene.name}, putting them in new bake group")
        new_group = bpy.data.collections.new("stray_holder")
        props: SBE_CollectionProperties = SBE_CollectionProperties(new_group)
        props.is_bake_group = True
        for j in scene.collection.objects:
            obj: bpy.types.Object = j
            scene.collection.objects.unlink(obj)
            new_group.objects.link(obj)
        scene.collection.children.link(new_group)


def parse_names():
    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        props: SBE_ObjectProperties = SBE_ObjectProperties.get(obj)
        if object_is_discard(obj):
            props.visibility = 'DISCARD'
        elif object_is_only_bake(obj):
            props.visibility = 'ONLY_BAKE'
        elif object_is_only_game(obj):
            props.visibility = 'ONLY_GAME'

        if object_is_solid_collision(obj):
            props.physics = 'COLLISION'
        elif object_is_trigger_collision(obj):
            props.physics = 'TRIGGER'

    for i in bpy.data.collections:
        col: bpy.types.Collection = i
        if col.name.find("merge_by_distance") != -1:
            SBE_Logger.error(f"No distance merge implemented {col.name}")
        props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
        props.is_bake_group = props.is_bake_group or is_bake_group(col)
        scale = get_bake_collection_scale(col)
        if props.is_bake_group:
            bake_props: SBE_BakeProperties = props.bake_settings
            bake_props.resolution_relative = scale
            bake_props.resolution_relative_set = True
            bake_props: SBE_BakeProperties = props.bake_debug
            bake_props.resolution_relative = scale
            bake_props.resolution_relative_set = True
        else:
            props.uv_scale *= scale
        
        if collection_is_discard(col):
            # TODO this also looks like it could be derived like bake props
            for j in col.all_objects:
                obj: bpy.types.Object = j
                obj_props: SBE_ObjectProperties = SBE_ObjectProperties.get(obj)
                obj_props.visibility = 'DISCARD'
            props.visibility = 'DISCARD'
        elif collection_is_only_bake(col):
            for j in col.all_objects:
                obj: bpy.types.Object = j
                obj_props: SBE_ObjectProperties = SBE_ObjectProperties.get(obj)
                obj_props.visibility = 'ONLY_BAKE'
            props.visibility = 'ONLY_BAKE'


def move_uv_scale_group_to_attribute():
    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        scale_groups = get_bake_scale_vertex_groups(obj)
        if len(scale_groups) == 0:
            continue
        props: SBE_ObjectProperties = SBE_ObjectProperties.get(obj)

        skip_vertex_group_uv_scale = props.skip_mesh_uv_scale

        if not skip_vertex_group_uv_scale:
            parents = get_collections_parents(obj.users_collection[0])
            for j in parents:
                col: bpy.types.Collection = j
                props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
                skip_vertex_group_uv_scale = skip_vertex_group_uv_scale or props.skip_mesh_uv_scale

        if not skip_vertex_group_uv_scale:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            vertex_group_layer: bmesh.types.BMLayerItem = bm.verts.layers.deform.verify()
            if SBE_MESH_UV_SCALE_ATTRIBUTE in bm.loops.layers.float:
                SBE_Logger.print(f"Warning, UV Scale attribute and vertex group set {obj.name}. Only use one.")
                continue
            target_attribute_layer: bmesh.types.BMLayerItem = bm.loops.layers.float.new(SBE_MESH_UV_SCALE_ATTRIBUTE)

            for scale_group in scale_groups:
                for i in bm.faces:
                    face: bmesh.types.BMFace = i

                    verts = 0
                    ingroup = 0
                    for j in face.loops:
                        loop: bmesh.types.BMLoop = j
                        loop[target_attribute_layer] = float(1) # set a default
                        verts += 1
                        if scale_group.index in loop.vert[vertex_group_layer]:
                            ingroup += 1

                    if verts != ingroup:
                        # Faces with different scales are at the border of a
                        # vertex group and will be ignored
                        continue

                    for j in face.loops:
                        loop: bmesh.types.BMLoop = j
                        loop[target_attribute_layer] *= scale_group.scale

            bm.to_mesh(obj.data)
            bm.free()
        # Don't need the vertex groups any longer
        for scale_group in scale_groups:
            obj.vertex_groups.remove(scale_group.group)


def smart_project():
    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        if obj.type != 'MESH':
            continue
        has_projection = None
        for j in obj.data.uv_layers:
            uv_layer: bpy.types.MeshUVLoopLayer = j
            if uv_layer.name.find("smart_project") != -1:
                if len(obj.data.uv_layers) != 1:
                    SBE_Logger.print(f"Warning, {obj.name} don't use multiple uvs when smart_project is used")
                has_projection = "smart_project"
                break
            elif uv_layer.name.find("unwrap") != -1:
                if len(obj.data.uv_layers) != 1:
                    SBE_Logger.print(f"Warning, {obj.name} don't use multiple uvs when unwrap is used")
                has_projection = "unwrap"
                break
        if not has_projection:
            continue
        SBE_Logger.print(f"{obj.name} has {has_projection}")
        # We rename the uv layer, later, which would mean other
        # users don't get the SBE_OBJ_SMART_PROJECT_ATTRIBUTE attribute
        # so this should be unique so changes don't propagate
        ensure_unique_data(obj)
        for j in obj.data.uv_layers:
            uv_layer: bpy.types.MeshUVLoopLayer = j
            obj[SBE_OBJ_SMART_PROJECT_ATTRIBUTE] = has_projection
            uv_layer.name = 'UVMap'



class SBE_Compatibility(SBE_ExportOperatorBase):
    """Correct some crutches from the old bake script so these problems don't leak into the new one."""
    bl_idname = SBE_OP_COMPATIBILITY
    bl_label = "Convert from old bake script"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        if start.has_run:
            return # Only should run once

        with SBE_Logger("parse_names"):
            parse_names()

        with SBE_Logger("put_strays_in_bake_group"):
            put_strays_in_bake_group()

        with SBE_Logger("put_sky_box_in_bake_group"):
            put_sky_box_in_bake_group()

        with SBE_Logger("move_uv_scale_group_to_attribute"):
            move_uv_scale_group_to_attribute()

        with SBE_Logger("smart_project"):
            smart_project()
        return {"FINISHED"}
