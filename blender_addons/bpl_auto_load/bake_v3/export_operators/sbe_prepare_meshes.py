"""
Basic preparation before mesh generation steps
Does some magic on object names, boosters, physics material replacement etc.
"""


# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_collection_util import get_bake_collections
from bake_v3.sbe_util import (
    set_node_group_value, find_or_get_material, find_or_get_node_tree,
    version_has_new_geo_nodes_accessor
)
from bake_v3.sbe_paths import (
    PROPS_BLEND_PATH, NODE_GROUP_IS_PREVIEW,
    NODE_GROUP_IS_RELEASE_BAKE, NODE_GROUP_IS_GAME_MESH
)
from bake_v3.sbe_mesh_util import convert_to_mesh, ensure_unique_data
from bake_v3.sbe_operator_ids import SBE_OP_PREPARE_MESHES
from bake_v3.properties.sbe_object_props import SBE_ObjectProperties
from bake_v3.properties.sbe_blend_props import SBE_BlendProperties
from bake_v3.sbe_name_parser import (
    get_name_replacer, get_append_string, append_property,
    object_is_only_game, strip_comment_and_post_fix, is_physics_material,
    object_is_solid_collision, is_no_export_modifier
)


def replace_names(collections: list[bpy.types.Collection]) -> None:
    """Replace strings in objects names within a collection"""
    with SBE_Logger("replace_names"):
        for i in collections:
            col: bpy.types.Collection = i
            replacer = get_name_replacer(col)
            if replacer is None:
                continue
            rename_from = replacer[0]
            rename_to = replacer[1]
            for j in col.all_objects:
                obj: bpy.types.Object = j
                name = obj.name
                name: str = strip_comment_and_post_fix(name)
                if rename_from == '':
                    obj.name = name + rename_to
                else:
                    obj.name = name.replace(rename_from, rename_to)


def append_properties(collections: list[bpy.types.Collection]) -> None:
    with SBE_Logger("append_properties"):
        for i in collections:
            col: bpy.types.Collection = i
            prop = get_append_string(col)
            if prop is None:
                continue
            for j in col.all_objects:
                obj: bpy.types.Object = j
                append_property(obj, prop)


def sync_booster_text(objects: list[bpy.types.Object]) -> None:
    """Syncs booster names and visual speed, naming unmarked objects from their modifier."""
    with SBE_Logger("sync_booster_text"):
        booster_group_name = 'Booster'
        if booster_group_name not in bpy.data.node_groups:
            return
        booster_text_socket = bpy.data.node_groups[booster_group_name].nodes['Group Input'].outputs['CM/S'].identifier
        for obj in objects:
            if "#=Booster" not in obj.name:
                for mod in obj.modifiers:
                    if mod.type != 'NODES' or mod.node_group != bpy.data.node_groups[booster_group_name]:
                        continue
                    if version_has_new_geo_nodes_accessor():
                        if booster_text_socket not in mod.properties.inputs:
                            continue
                        booster_val = getattr(mod.properties.inputs, booster_text_socket).value
                    else:
                        if booster_text_socket not in mod:
                            continue
                        booster_val = mod[booster_text_socket]
                    obj.name = f"#=Booster({booster_val})"
                    break
                continue
            if obj.name.find("=Booster") != -1:
                # TODO name parser edge case
                value_index = obj.name.find("(") + 1
                booster_val = obj.name[value_index : obj.name.find(")")]
                if booster_val:
                    try:
                        booster_val = float(booster_val)
                    except ValueError:
                        continue
                    for j in obj.modifiers:
                        if version_has_new_geo_nodes_accessor():
                            if booster_text_socket in j.properties.inputs:
                                getattr(j.properties.inputs, booster_text_socket).value = booster_val
                        else:
                            if booster_text_socket in j:
                                j[booster_text_socket] = booster_val
                else:
                    # case =Booster()
                    # take the CM/S value from the geometry node and insert it between the brackets
                    booster_val = None
                    for j in obj.modifiers:
                        mod: bpy.types.Modifier = j
                        if version_has_new_geo_nodes_accessor():
                            if booster_text_socket in mod.properties.inputs:
                                booster_val = getattr(mod.properties.inputs, booster_text_socket).value
                                break
                        else:
                            if booster_text_socket in mod:
                                booster_val = mod[booster_text_socket]
                                break
                    if booster_val != None:
                        obj.name = obj.name[:value_index] + str(booster_val) + obj.name[value_index:]


def apply_physics_mods(context: bpy.types.Context, objects: list[bpy.types.Object]) -> None:
    with SBE_Logger("apply_physics_mods"):
        physics = []
        for obj in objects:
            if obj.name.find("=Booster") != -1:
                # TODO name parser edge case
                continue
            props: SBE_ObjectProperties = SBE_ObjectProperties.get(obj)
            if props.physics != 'NONE' and (obj.type == 'MESH' or obj.type == 'CURVE'):
                skip = False
                for j in obj.modifiers:
                    mod: bpy.types.Modifier = j
                    if is_no_export_modifier(mod):
                        # TODO tk there was a reason for this, i just can't remember
                        # mod.show_viewport = False
                        # mod.show_render = False
                        # We can't apply the mods if the result differ for bake source/target
                        skip = True
                if not skip:
                    physics.append(obj)
        convert_to_mesh(context=context, objects=physics)


def clear_parents(objects: list[bpy.types.Object]) -> None:
    """Clears the parents of objects while maintaining their transform"""
    with SBE_Logger("clear_parents"):
        for i in objects:
            obj: bpy.types.Object = i
            if obj.parent is None:
                continue
            mat = obj.matrix_world
            obj.parent = None
            obj.matrix_local = mat


def remap_random_node():
    # One time Setup materials so they source the randomness from a vertex attribute
    # instead a per object random source used in the viewport before joining
    random_nodes = 0
    for i in bpy.data.node_groups:
        if not isinstance(i, bpy.types.ShaderNodeTree):
            continue
        tree: bpy.types.ShaderNodeTree = i
        if not tree.name.startswith('IsPreviewMaterial'):
            continue
        random_nodes += 1
        tree.nodes['sbe_value'].outputs[0].default_value = 0.0
    if 1 < random_nodes:
        SBE_Logger.print("Warning, multiple random nodes, consider remapping.")


def object_has_any_of_material_kind(obj: bpy.types.Object, physics = True) -> bool:
    for mat_slot in obj.material_slots:
        if is_physics_material(mat_slot.material) == physics:
            return True
    return False


def create_default_visual_mesh(objects: list[bpy.types.Object]) -> None:
    """
    For blockouts, some object might only have a physics material assigned, but are marked as
    visual + collision so we need to create a duplicate for rendering.
    Could use some refactoring
    """
    for i in objects:
        obj: bpy.types.Object = i

        # check if it really is a collision object (because we also search for that < character later on)
        if not object_is_solid_collision(obj): # if "<" not in obj.name:
            continue

        # check if object is ONLY used for collision
        if object_is_only_game(obj): # similar to: if "_<" in obj.name:
            continue
        # otherwise it's a collision object that's also used for visual representation (<)

        has_physics_material = False
        has_visual_material = False
        for mat_slot in obj.material_slots:
            if is_physics_material(mat_slot.material):
                has_physics_material = True
            else:
                has_visual_material = True

        if has_physics_material and has_visual_material:
            # If both materials are present, nothing to do
            continue

        if has_visual_material:
            # for visual only, the split will happen when generating the target mesh
            # There are modifiers depending on flags that are only set during that step.
            continue

        nameIndex = obj.name.index("<")
        visual_obj = obj.copy()
        ensure_unique_data(visual_obj)
        for collection in obj.users_collection:
            collection.objects.link(visual_obj)

        # remove < from name
        visual_obj.name = obj.name[:nameIndex] + obj.name[nameIndex + 1:]

        if has_visual_material is False:
            # assign_default_materials will assign checker texture
            visual_obj.data.materials.clear()
        else:
            # TODO tk remove physics materials
            pass
        visual_obj.sbe_properties.physics = 'NONE'

        if has_physics_material is False:
            # TODO tk add default physics material
            pass

        # rename old object, so it's a collision without visuals (_< instead of a <)
        obj.name = obj.name[:nameIndex] + "_" + obj.name[nameIndex:]
        obj.sbe_properties.visibility = 'HIDDEN'


def assign_default_materials(context: bpy.types.Context) -> None:
    """Ensures all objects have some material and UV map so bakes work for blockouts"""
    with SBE_Logger("assign_default_materials"):
        context.view_layer.update() # needed to sync the changes from steps before
        checker_material = find_or_get_material('checker512', PROPS_BLEND_PATH)
        smart_project_name = 'SmartProject'
        find_or_get_node_tree(smart_project_name, PROPS_BLEND_PATH)
        objects_ids_with_no_material = []

        # we need to check the deps graph in case any of the
        # modifiers add materials
        # We can't modify the deps graph object, so we just remember the name
        for i in context.view_layer.depsgraph.objects:
            obj: bpy.types.Object = i
            if not hasattr(obj.data, "materials"):
                continue
            if obj.type == 'CURVE':
                # We can't evaluate materials on curve modifiers because we've
                # hidden the modifiers on curves
                # in sbe_make_real.py (curve_modifier_fix) due to a bug in blender.
                # https://projects.blender.org/blender/blender/issues/99088
                continue
            only_in_game = object_is_only_game(obj)
            if only_in_game:
                # don't care about only in game objects
                continue
            has_material = object_has_any_of_material_kind(obj, physics=False)
            if has_material:
                # don't care if at least one non physics material
                continue
            objects_ids_with_no_material.append(obj.name)

        for i in objects_ids_with_no_material:
            obj: bpy.types.Object = context.view_layer.objects[i]
            ensure_unique_data(obj)
            # Append default material and auto unwrap to the real object
            obj.data.materials.append(material=checker_material)
            SBE_Logger.print(f"Adding placeholder material to {i}")
            # TODO maybe check if unwrap modifier is already on there so we don't unwrap twice
            mod = obj.modifiers.new(smart_project_name, 'NODES')
            mod.node_group = bpy.data.node_groups[smart_project_name]


class SBE_PrepareMeshes(SBE_ExportOperatorBase):
    """Prepare meshes before generating bake meshes"""
    bl_idname = SBE_OP_PREPARE_MESHES
    bl_label = "Prepare Meshes"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        if (not start.has_run):
            set_node_group_value(NODE_GROUP_IS_PREVIEW, False)

            blend_props: SBE_BlendProperties = SBE_BlendProperties.get()
            set_node_group_value(NODE_GROUP_IS_RELEASE_BAKE, blend_props.bake_preset == 'RELEASE')

        # We need to set this every time, since we evaluate the deps graph
        # and the value set to true from the last exported scenes messes this up.
        set_node_group_value(NODE_GROUP_IS_GAME_MESH, False)

        bake_collections = get_bake_collections(context)

        all_collections: list[bpy.types.Collection] = []
        all_objects: list[bpy.types.Object] = []

        for i in bake_collections:
            col: bpy.types.Collection = i
            all_objects.extend(col.all_objects)
            all_collections.extend(col.children_recursive)

        clear_parents(all_objects)


        replace_names(all_collections)
        append_properties(all_collections)
        sync_booster_text(all_objects)
        apply_physics_mods(context=context, objects=all_objects)
        create_default_visual_mesh(all_objects)
        assign_default_materials(context=context)

        remap_random_node()
