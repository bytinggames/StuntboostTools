"""
Most complex operator
it removes non export modifiers
applies all modifiers
assigns per vertex uv scaling respecting texture aspect ratio
applies outline shifting properties
joins meshes, but also remembers parts which need to
be split again after baking with their original names (not position however)
"""

# pylint: disable=import-error
import bpy
import bmesh
# pylint: enable=import-error


from bake_v3.sbe_operator_ids import SBE_OP_TARGET_MESHES
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_util import (
    store_temp, retrieve_temp, find_or_get_node_tree, set_node_group_value,
    version_has_new_geo_nodes_accessor
)
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.properties.sbe_object_props import SBE_ObjectProperties
from bake_v3.sbe_custom_properties import (
    SBE_OBJECT_BAKE_TARGET_PROP, SBE_MESH_UV_SCALE_ATTRIBUTE,
    SBE_MESH_UV_ASPECT_ATTRIBUTE, SBE_OBJ_SMART_PROJECT_ATTRIBUTE,
    SBE_VERTEX_SPLIT_ID, SBE_GLOBAL_SPLIT_ID_NAME_MAP
)
from bake_v3.sbe_name_parser import (
    in_bake_target, prevent_join, shadow_group_name,
    is_no_export_modifier, needs_physics_mesh, make_invisible_collision,
    is_sky_box, is_cutter, is_cut_collection
)
from bake_v3.sbe_mesh_util import (
    join_without_materials, split_by_material_indices, smart_project,
    convert_to_mesh, ensure_unique_data, find_physics_material_slot_indices,
    ensure_outside_normals
)
from bake_v3.sbe_collection_util import (
    get_bake_collections, get_all_bake_collections, get_all_scene_bake_collection,
    get_collections_parents
)
from bake_v3.sbe_outline_util import outline_apply_transform, setup_outlines
from bake_v3.sbe_paths import PROPS_BLEND_PATH, NODE_GROUP_IS_GAME_MESH

def make_invisible_collision_internal(obj: bpy.types.Object) -> None:
    make_invisible_collision(obj)
    props: SBE_ObjectProperties = SBE_ObjectProperties.get(obj)
    props.physics = 'COLLISION'
    props.visibility = 'HIDDEN'


def apply_uv_scale_property(obj: bpy.types.Object):
    """
    Each object has a calculated UV scale factor based on the collections its in, a object attribute
    and vertex group/attribute values.
    This step calculates the aspect ratio and final scale for all uv islands and stores it in in new
    attributes so there are no dependencies any more, and the objects can be joined later.
    """
    assert obj.data.users == 1, "There shouldn't be multiple use"
    assert obj.type == 'MESH', "Only meshes should end up here"
    parents = get_collections_parents(obj.users_collection[0])
    scale = 1.0
    for j in parents:
        col: bpy.types.Collection = j
        props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
        scale *= props.uv_scale

    props: SBE_ObjectProperties = SBE_ObjectProperties.get(obj)
    scale = scale * props.uv_scale

    # Look for images and their aspect ratio per material slot
    # use the first image with a connected output
    aspect_ratios: dict[int, float] = { }
    for i in obj.material_slots:
        slot: bpy.types.MaterialSlot = i
        if slot.material is None:
            continue
        if slot.material.node_tree is None:
            SBE_Logger.print("No Material node_tree set for " + slot.material.name + " Linked resources missing?")
            continue
        aspect_ratios[slot.slot_index] = float(1)
        for j in slot.material.node_tree.nodes:
            if not isinstance(j, bpy.types.ShaderNodeTexImage):
                continue
            img_node: bpy.types.ShaderNodeTexImage = j
            if img_node.mute or img_node.image is None:
                continue
            if not img_node.outputs['Color'].is_linked and not img_node.outputs['Alpha'].is_linked:
                continue
            img: bpy.types.Image = img_node.image
            if img.size[0] == 0 or img.size[1] == 0:
                SBE_Logger.error(f"Image {img.name} on object {obj.name} has dimensions {img.size[0]}x{img.size[1]}")
                continue
            aspect_ratio = float(img.size[0]) / float(img.size[1])
            aspect_ratios[slot.slot_index] = aspect_ratio

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    uv_aspect_layer: bmesh.types.BMLayerItem = bm.loops.layers.float.new(SBE_MESH_UV_ASPECT_ATTRIBUTE)
    if SBE_MESH_UV_SCALE_ATTRIBUTE not in bm.loops.layers.float:
        # create a new layer and set the current scale
        uv_scale_layer: bmesh.types.BMLayerItem = bm.loops.layers.float.new(SBE_MESH_UV_SCALE_ATTRIBUTE)
        for i in bm.faces:
            face: bmesh.types.BMFace = i
            aspect = float(1)
            if face.material_index in aspect_ratios:
                aspect = aspect_ratios[face.material_index]
            for j in face.loops:
                loop: bmesh.types.BMLoop = j
                loop[uv_scale_layer] = scale
                loop[uv_aspect_layer] = aspect
    else:
        # use an existing layer and multiply on top
        uv_scale_layer: bmesh.types.BMLayerItem = bm.loops.layers.float[SBE_MESH_UV_SCALE_ATTRIBUTE]
        for i in bm.faces:
            face: bmesh.types.BMFace = i
            aspect = float(1)
            if face.material_index in aspect_ratios:
                aspect = aspect_ratios[face.material_index]
            for j in face.loops:
                loop: bmesh.types.BMLoop = j
                loop[uv_scale_layer] *= scale
                loop[uv_aspect_layer] = aspect

    bm.to_mesh(obj.data)
    bm.free()


def set_split_group(obj: bpy.types.Object, split_id: int) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    layer: bmesh.types.BMLayerItem = bm.verts.layers.int.new(SBE_VERTEX_SPLIT_ID)

    for i in bm.verts:
        vert: bmesh.types.BMVert = i
        vert[layer] = split_id

    bm.to_mesh(obj.data)
    bm.free()


def setup_split_groups(bake_group_name: str, objects: list[bpy.types.Object]) -> None:
    names: list[str] = retrieve_temp(SBE_GLOBAL_SPLIT_ID_NAME_MAP)
    if names is None:
        names = []
    else:
        # cast back to list, since blender uses its own array types which lack .append()
        names = list(names)
    name_id = len(names)
    for i in objects:
        obj: bpy.types.Object = i
        current_id: int = -1

        if prevent_join(obj):
            current_id = name_id
            names.append(obj.name)
            name_id += 1
        else:
            shadow_group = shadow_group_name(bake_group_name=bake_group_name, obj=obj)
            if shadow_group is not None:
                if shadow_group in names:
                    current_id = names.index(shadow_group)
                else:
                    current_id = name_id
                    names.append(shadow_group)
                    name_id += 1

        set_split_group(obj, current_id)

    store_temp(SBE_GLOBAL_SPLIT_ID_NAME_MAP, names)

def setup_cut(collections: list[bpy.types.Collection]):
    mod_name = 'Boolean Cut'
    find_or_get_node_tree(mod_name, PROPS_BLEND_PATH)
    cut_objects = []
    for i in collections:
        col: bpy.types.Collection = i
        if not is_cut_collection(col):
            continue
        cutter: bpy.types.Object = None
        for j in col.objects:
            obj: bpy.types.Object = j
            if is_cutter(obj):
                cutter = obj
                break
        if cutter is None:
            SBE_Logger.error(f"No cutter found for collection {col.name}")
            continue
        for j in col.all_objects:
            obj: bpy.types.Object = j
            if obj is cutter or not in_bake_target(obj):
                continue
            mod = obj.modifiers.new(mod_name, 'NODES')
            mod.node_group = bpy.data.node_groups[mod_name]
            if version_has_new_geo_nodes_accessor():
                mod.properties.inputs.Socket_2.value = cutter
            else:
                mod["Socket_2"] = cutter
            cut_objects.append(obj)


def generate_target_object(
    context: bpy.types.Context,
    collection: bpy.types.Collection,
    index: int) -> bpy.types.Object:

    objects: list[bpy.types.Object] = [i for i in collection.all_objects if in_bake_target(i)]

    target_name = f"bake_{index}_object"

    with SBE_Logger("hide_modifiers"):
        for i in objects:
            obj: bpy.types.Object = i
            if is_sky_box(obj):
                # skybox name will be parsed in game, so pass it through
                target_name = obj.name

            # just to be sure nothing fucky happens on object.convert
            ensure_unique_data(obj)

            for j in obj.modifiers:
                modifier: bpy.types.Modifier = j
                if is_no_export_modifier(modifier):
                    # this is faster than removing but same result
                    modifier.show_viewport = False
                    modifier.show_render = False

    with SBE_Logger("setup_cut"):
        setup_cut(collections=collection.children_recursive)

    convert_to_mesh(context, objects)

    with SBE_Logger("ensure_outside_normals"):
        for i in objects:
            obj: bpy.types.Object = i
            ensure_outside_normals(obj)

    with SBE_Logger("Collision split"):
    # Split away any collision meshes if they are mixed in with visuals
        for i in objects:
            obj: bpy.types.Object = i
            physics_materials = find_physics_material_slot_indices(obj)
            if len(obj.material_slots) != 0 and len(physics_materials) == len(obj.material_slots):
                SBE_Logger.print(f"{obj.name} should not be in bake target with only collision materials")
            physics_obj: bpy.types.Object = split_by_material_indices(obj=obj, indices=physics_materials)
            if physics_obj is not None:
                make_invisible_collision_internal(physics_obj)
            elif needs_physics_mesh(obj):
                physics_obj = obj.copy()
                physics_obj.data = physics_obj.data.copy()
                physics_obj.data.materials.clear()
                make_invisible_collision_internal(physics_obj)
                obj.users_collection[0].objects.link(physics_obj)

    with SBE_Logger("outline_apply_transform"):
        for i in objects:
            obj: bpy.types.Object = i
            outline_apply_transform(obj)

    with SBE_Logger("transform_apply"):
        with context.temp_override(selected_editable_objects=objects):
            # this is important for outline shifting
            # But needs to happen after collision are split off because
            # boosters draw numbers based on the collision and depend on the object origin
            bpy.ops.object.transform_apply()

    with SBE_Logger("uv_smart_project and auto_unwrap"):
        for i in objects:
            obj: bpy.types.Object = i
            if SBE_OBJ_SMART_PROJECT_ATTRIBUTE in obj:
                smart_project(context=context, obj=obj, unwrap_method=obj[SBE_OBJ_SMART_PROJECT_ATTRIBUTE])

    with SBE_Logger("setup_uv_scale"):
        for i in objects:
            obj: bpy.types.Object = i
            apply_uv_scale_property(obj)

    with SBE_Logger("setup_outlines"):
        for i in objects:
            obj: bpy.types.Object = i
            setup_outlines(obj)

    with SBE_Logger("setup_split_groups"):
        setup_split_groups(collection.name, objects)

    # make a new mesh, one per bake collection containing all the geometry
    target_mesh = bpy.data.meshes.new(f"bake_{index}_mesh")
    target_object = bpy.data.objects.new(name=target_name, object_data=target_mesh)
    target_object[SBE_OBJECT_BAKE_TARGET_PROP] = index
    collection.objects.link(target_object)

    join_without_materials(target_object, objects)

    with SBE_Logger("remove_uv_layers"):
        for i in target_object.data.uv_layers[:]:
            if not i.active:
                target_object.data.uv_layers.remove(i)

    return target_object


class SBE_GenerateTargetMesh(SBE_ExportOperatorBase):
    """Generate bake target meshes"""
    bl_idname = SBE_OP_TARGET_MESHES
    bl_label = "Generate bake meshes"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        set_node_group_value(NODE_GROUP_IS_GAME_MESH, True)
        bake_collections = get_bake_collections(context)
        all_bake_collections_scene = get_all_scene_bake_collection(context)
        all_bake_collections = get_all_bake_collections()

        for i, collection in enumerate(all_bake_collections):
            if collection not in all_bake_collections_scene:
                continue # skip over bake collections in another scene, can't bake across scenes

            if collection in bake_collections:
                # Generate target meshes for all scheduled collections
                generate_target_object(context=context, collection=collection, index=i)
