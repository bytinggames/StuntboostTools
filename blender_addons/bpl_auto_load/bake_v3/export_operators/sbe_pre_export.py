"""
Does the remaining processing of objects needed in game, like replacing materials etc.
These don't affect the bake, so this is the last step before export.
"""

import math

# pylint: disable=import-error
import bpy
import bmesh
# pylint: enable=import-error

from bake_v3.sbe_util import get_bake_target_objects
from bake_v3.sbe_temp_storage import retrieve_temp
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_collection_util import (
    get_bake_collections, get_all_bake_collections, get_collection_parent
)
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_operator_ids import SBE_OP_PRE_EXPORT
from bake_v3.sbe_name_parser import (
    is_no_export_modifier, is_physics_material,
    get_physics_replacement_material, is_delete_physics,
    collection_is_only_bake, object_is_discard, object_is_only_bake
)
from bake_v3.sbe_custom_properties import (
    SBE_MESH_UV_SCALE_ATTRIBUTE, SBE_IMG_BAKE_COMBINED_PROP,
    SBE_IMG_BAKE_AO_PROP, SBE_IMG_BAKE_DIRECT_PROP,
    SBE_IMG_BAKE_COMBINED_PROCESSED_PROP, SBE_IMG_BAKE_DIRECT_PROCESSED_PROP,
    SBE_OBJECT_BAKE_TARGET_PROP, SBE_OBJECT_BAKE_SOURCE_PROP,
    SBE_VERTEX_SPLIT_ID, SBE_GLOBAL_SPLIT_ID_NAME_MAP,
    SBE_VERTEX_SHIFT_ATTRIBUTE, SBE_EXPORT_VERTEX_SHIFT_ATTRIBUTE
)
from bake_v3.properties.sbe_object_props import SBE_ObjectProperties
from bake_v3.sbe_mesh_util import ensure_unique_data, ensure_outside_normals

def create_sun(context: bpy.types.Context,
    bake_collection: list[bpy.types.Collection],
    all_bake_collections: list[bpy.types.Collection]):
    """Creates the sun light based on the current sky texture so in game, shadows can be cast."""

    if len(all_bake_collections) == 0:
        SBE_Logger.print("Warning, Need at least one bake collection in file. No Sun created.")
        return

    target_collection: bpy.types.Collection = all_bake_collections[0]
    # I assume the sun needs to be in collection 0?

    if target_collection not in bake_collection:
        # If we're not baking that collection, bail
        return

    world: bpy.types.World = context.scene.world

    sky: bpy.types.ShaderNodeTexSky = None
    for i in world.node_tree.nodes:
        if isinstance(i, bpy.types.ShaderNodeTexSky):
            if sky is not None:
                SBE_Logger.print(f"Warning multiple Sky Texture in  World data block {world.name}.")
            sky = i

    if sky is None:
        SBE_Logger.print(f"Can't find Sky Texture in  World data block {world.name}.")
        SBE_Logger.print("No sun will be created. In game shadow might be off")
        return

    rotation = sky.sun_rotation
    elevation = sky.sun_elevation
    sun = bpy.data.objects.new(name="_=Sun()", object_data=None)
    target_collection.objects.link(sun)
    sun.show_axis = True
    sun.rotation_euler = (-elevation, 0, -rotation + math.pi)

def create_baked_lighting_marker(bake_collection: list[bpy.types.Collection],
    all_bake_collections: list[bpy.types.Collection]):
    """Creates an empty that tells the game that this level uses baked lighting."""

    if len(all_bake_collections) == 0:
        SBE_Logger.print("Warning, Need at least one bake collection in file. No SetBakedLighting object created.")
        return

    target_collection: bpy.types.Collection = all_bake_collections[0]

    if target_collection not in bake_collection:
        # If we're not baking that collection, bail
        return

    obj = bpy.data.objects.new(name="=SetBakedLighting()", object_data=None)
    target_collection.objects.link(obj)


def remove_attributes(obj: bpy.types.Object) -> None:
    if hasattr(obj.data, "attributes"):
        if SBE_MESH_UV_SCALE_ATTRIBUTE in obj.data.attributes:
            obj.data.attributes.remove(obj.data.attributes[SBE_MESH_UV_SCALE_ATTRIBUTE])
            attribute_names_to_remove = []
            for attribute in obj.data.attributes[:]:
                if not attribute.is_internal:
                    if attribute.name.startswith('/') or attribute.name in ["UVMap.001", "source"]:
                        attribute_names_to_remove.append(attribute.name)
                        obj.data.attributes.remove(attribute)
    custom_props = [
        SBE_IMG_BAKE_COMBINED_PROP, SBE_IMG_BAKE_AO_PROP, SBE_IMG_BAKE_DIRECT_PROP,
        SBE_IMG_BAKE_COMBINED_PROCESSED_PROP, SBE_IMG_BAKE_DIRECT_PROCESSED_PROP,
        SBE_OBJECT_BAKE_TARGET_PROP, SBE_OBJECT_BAKE_SOURCE_PROP, SBE_VERTEX_SPLIT_ID
    ]
    for i in custom_props:
        if i in obj:
            del obj[i]


def remove_modifiers(obj: bpy.types.Object) -> None:
    if hasattr(obj, "modifiers"):
        for modifier in obj.modifiers:
            if is_no_export_modifier(modifier):
                # Modifiers get applied on export, these will be ignored then
                modifier.show_viewport = False # this is faster than removing but same result
                modifier.show_render = False
            elif modifier.show_viewport != modifier.show_render:
                # the actual export only cares about the view port, sync over the render visibility
                # so we can have editor only modifiers
                modifier.show_viewport = modifier.show_render


def remove_materials(obj: bpy.types.Object) -> None:
    props: SBE_ObjectProperties = SBE_ObjectProperties.get(obj)
    if props.physics == 'NONE':
        return
    if props.physics == 'TRIGGER':
        return
    if obj.type != 'MESH':
        return
    for i in obj.material_slots:
        mat_slot: bpy.types.MaterialSlot = i
        if not is_physics_material(mat_slot.material):
            mat_slot.material = None

    for i, _mat in enumerate(obj.data.materials):
        if not is_physics_material(obj.data.materials[i]):
            # TODO this might need a unique data block?
            # the object might link to a physics material, while the mesh is not
            # so we need to check here as well
            obj.data.materials[i] = None

def exchange_collision_materials(collection: bpy.types.Collection) -> None:
    with SBE_Logger("exchange_collision_materials"):
        for i in collection.children_recursive:
            col: bpy.types.Collection = i
            mat = get_physics_replacement_material(col)
            if mat is None:
                continue
            for j in col.all_objects:
                obj: bpy.types.Object = j
                ensure_unique_data(obj)
                for k in obj.material_slots:
                    slot: bpy.types.MaterialSlot = k
                    if is_physics_material(slot.material):
                        slot.material = mat

def remove_collision(collection: bpy.types.Collection):
    with SBE_Logger("remove_collision"):
        remove = []
        for i in collection.children_recursive:
            col: bpy.types.Collection = i
            if not is_delete_physics(col):
                continue
            for j in col.all_objects:
                obj: bpy.types.Object = j
                for k in obj.material_slots:
                    mat_slot: bpy.types.MaterialSlot = k
                    if not is_physics_material(mat_slot.material):
                        continue
                    remove.append(obj)
                    break
        bpy.data.batch_remove(remove)


def delete_by_id(obj: bpy.types.Object, value: int, invert=False) -> bool:
    """Deletes vertices by SBE_VERTEX_SPLIT_ID int id, return True if something was deleted"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    if SBE_VERTEX_SPLIT_ID not in bm.verts.layers.int:
        return False

    layer: bmesh.types.BMLayerItem = bm.verts.layers.int[SBE_VERTEX_SPLIT_ID]
    bm.verts.ensure_lookup_table()
    delete_verts: list[bmesh.types.BMVert] = []
    total = len(bm.verts)
    if invert:
        for i in bm.verts:
            vert: bmesh.types.BMVert = i
            if vert[layer] != value:
                delete_verts.append(vert)
    else:
        for i in bm.verts:
            vert: bmesh.types.BMVert = i
            if vert[layer] == value:
                delete_verts.append(vert)
    if total == len(delete_verts):
        bm.free()
        return False

    bmesh.ops.delete(bm, geom=delete_verts, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    return True


def split_groups(context: bpy.types.Context, obj: bpy.types.Object, name_lookup: list[str]) -> None:
    temp_obj: bpy.types.Object = obj.copy()
    temp_obj.data = temp_obj.data.copy()
    temp_obj.name = temp_obj.name

    # Clear out all split geometry from original
    delete_by_id(obj, value=-1, invert=True)
    # Temporary object with only split geo so the loop is faster
    delete_by_id(temp_obj, value=-1, invert=False)

    to_delete: list[bpy.types.Object] = [temp_obj]
    for i, name in enumerate(name_lookup):
        split_obj = temp_obj.copy()
        split_obj.data = split_obj.data.copy()
        if not delete_by_id(split_obj, value=i, invert=True):
            to_delete.append(split_obj)
            continue
        split_obj.name = name
        obj.users_collection[0].objects.link(split_obj)
        with context.temp_override(selected_editable_objects=[split_obj]):
            # Was needed for boosters, could probably go now
            # BUT we might also need to restore the original orientation at some point.
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    bpy.data.batch_remove(to_delete)


def fix_object_linked_materials(objects: list[bpy.types.Object]):
    """
    When a object has more than one material slot, and all of them link
    materials to object data, not mesh data, no materials get exported.
    This seems like a blender/gltf exporter bug.
    As a workaround, we simply copy material data to the mesh.
    """
    for i in objects:
        obj: bpy.types.Object = i
        if len(obj.material_slots) <= 1:
            continue
        for j in obj.material_slots:
            mat_slot: bpy.types.MaterialSlot = j
            if mat_slot.link != 'OBJECT':
                continue
            ensure_unique_data(obj)
            obj.data.materials[mat_slot.slot_index] = mat_slot.material
            mat_slot.link = 'DATA'


class SBE_PreExportLevel(SBE_ExportOperatorBase):
    """Prepare the level export"""
    bl_idname = SBE_OP_PRE_EXPORT
    bl_label = "Pre-Export STUNTBOOST level"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        # Visible in bake but hidden in game
        for i in context.scene.collection.children_recursive[:]:
            col: bpy.types.Collection = i
            if not collection_is_only_bake(col):
                continue
            parent = get_collection_parent(col)
            if parent:
                parent.children.unlink(col)

        delete = []
        for i in context.scene.collection.all_objects[:]:
            obj: bpy.types.Object = i
            if object_is_discard(obj) or object_is_only_bake(obj):
                delete.append(obj)
                # We don't delete them so any references kept to these objects in a modifier will still work
                # obj.users_collection[0].objects.unlink(obj)
        bpy.data.batch_remove(delete)


        bake_targets = get_bake_target_objects(context)
        if len(bake_targets) != 0:
            with context.temp_override(selected_editable_objects=bake_targets):
                bpy.ops.object.shade_smooth(keep_sharp_edges=False)

        bake_collection = get_bake_collections(context)
        all_bake_collections = get_all_bake_collections()

        create_sun(context=context, all_bake_collections=all_bake_collections, bake_collection=bake_collection)

        create_baked_lighting_marker(all_bake_collections=all_bake_collections, bake_collection=bake_collection)

        for i in bake_collection:
            collection: bpy.types.Collection = i

            for obj in collection.all_objects:
                # TODO rename for export
                if hasattr(obj.data, "attributes") and SBE_VERTEX_SHIFT_ATTRIBUTE in obj.data.attributes:
                    obj.data.attributes[SBE_VERTEX_SHIFT_ATTRIBUTE].name = SBE_EXPORT_VERTEX_SHIFT_ATTRIBUTE

            exchange_collision_materials(collection)
            remove_collision(collection)
            with SBE_Logger("remove_modifiers"):
                for obj in collection.all_objects:
                    remove_modifiers(obj)
            with SBE_Logger("remove_materials"):
                for obj in collection.all_objects:
                    remove_materials(obj)
            with SBE_Logger("split_by_groups"):
                name_lookup: list[str] = retrieve_temp(SBE_GLOBAL_SPLIT_ID_NAME_MAP)
                for obj in collection.all_objects[:]:
                    if SBE_OBJECT_BAKE_TARGET_PROP not in obj:
                        continue
                    split_groups(
                        context=context, obj=obj,
                        name_lookup=name_lookup)
            with SBE_Logger("remove_attributes"):
                for obj in collection.all_objects:
                    remove_attributes(obj)

            with SBE_Logger("ensure_outside_normals"):
                for obj in collection.all_objects:
                    ensure_outside_normals(obj)

            with SBE_Logger("fix_object_linked_materials"):
                fix_object_linked_materials(collection.all_objects)

        # TODO bake NLA actions, maybe?
        # TODO remove unneeded attributes and custom props
