"""This will pull in all the linked resources into the file and make instances real"""

# The main complexity lies in recreating the collection hierarchy for instanced objects
# blender does not do natively.
# This might not recreate the hierarchy on nested instances for arbitrary depths.
# For now to support some nesting, all nested collections are made real first, this is just one pass.
# Other more complete Solutions:
#  - Overflow principle, move duplicate objects in a collection over to the next collection
#    Potential problems are objects from different collections being mixed
#  - Figure out recursion depth and call make real for each recursion layer once from the bottom up
#    Could be slower?
#    Non trivial graphs?

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_MAKE_REAL
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_name_parser import object_is_discard
from bake_v3.sbe_collection_util import get_collection_parent, is_scene_collection
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.properties.sbe_object_props import SBE_ObjectProperties


SBE_IS_INSTANCER_PROP="sbe_instance_source"
"""Empties/Instancers will be tagged beforehand, so they can be deleted after instances are real"""
SBE_CUSTOM_ID_PROP="sbe_custom_id"
"""Collections get IDs so the instance source can be tracked after making instances real"""
SBE_PARENT_COLLECTION_PROP="sbe_parent_collection"
"""All objects get track their direct parent and reference SBE_CUSTOM_ID_PROP collection"""
SBE_INSTANCE_SOURCE_PROP="sbe_instance_source"
"""Collections will have this attribute set so after make real, the original collection is known"""

current_custom_id = 0
def get_custom_id() -> int:
    global current_custom_id
    current_custom_id += 1
    return current_custom_id


def collection_by_custom_id(custom_id: int) -> bpy.types.Collection | None:
    """Get the collection by the custom id property"""
    for collection in bpy.data.collections:
        if SBE_CUSTOM_ID_PROP in collection:
            if collection[SBE_CUSTOM_ID_PROP] == custom_id:
                return collection
    return None

def restore_collection(target: bpy.types.Collection, reference: bpy.types.Collection, root: bpy.types.Collection):
    """Recursively walk the reference collection and recreate
    the collection structure in the target collection"""
    if reference is None:
        SBE_Logger.error(f"Reference Collection missing {target.name}")
        return
    if SBE_CUSTOM_ID_PROP not in reference:
        SBE_Logger.error(f"Reference Collection {reference.name} missing SBE_CUSTOM_ID_PROP")
        return
    reference_collection_id = reference[SBE_CUSTOM_ID_PROP]
    for j in root.objects:
        obj: bpy.types.Object = j
        if SBE_PARENT_COLLECTION_PROP not in obj:
            SBE_Logger.error(f"Object {obj.name} missing SBE_PARENT_COLLECTION_PROP")
            continue
        # Find all objects which belong to the current reference child collection
        if obj[SBE_PARENT_COLLECTION_PROP] == reference_collection_id:
            # don't like the name comparison here, but other ways are cumbersome
            if obj.name not in target.objects:
                target.objects.link(obj)
                root.objects.unlink(obj)

    for i in reference.children:
        reference_child: bpy.type.Collection = i
        # The double slash at the end prevents the duplicate post fix from
        # being applied before a comment, which could mess up number parameters
        target_child = bpy.data.collections.new(reference_child.name + "//")
        props: SBE_CollectionProperties = SBE_CollectionProperties.get(reference_child)
        SBE_CollectionProperties.set(col=target_child, props=props)

        target.children.link(target_child)
        # If we find a reference source in a reference collection, this means
        # we'll have to follow that sub hierarchy separately
        if SBE_INSTANCE_SOURCE_PROP in reference_child:
            sub_reference = collection_by_custom_id(reference_child[SBE_INSTANCE_SOURCE_PROP])
            restore_collection(target_child, sub_reference, root)
        restore_collection(target_child, reference_child, root)


def restore_hierarchy(target_collection: bpy.types.Collection) -> None:
    """Restore the original hierarchy for all instanced collections"""
    for i in target_collection.children_recursive[:]:
        target_collection: bpy.types.Collection = i
        if SBE_INSTANCE_SOURCE_PROP not in target_collection:
            continue

        reference_collection = collection_by_custom_id(target_collection[SBE_INSTANCE_SOURCE_PROP])
        if reference_collection is None:
            SBE_Logger.error(f"No reference collection exists for {target_collection.name}")
            continue
        restore_collection(target_collection, reference_collection, target_collection)


def backup_instance_source(obj: bpy.types.Object) -> bpy.types.Collection:
    if len(obj.users_collection) == 1:
        # We also create a new collection at the same spot in the hierarchy
        # and put the instance source in it so all the real instance will
        # end up in that collection
        parent_collection: bpy.types.Collection = obj.users_collection[0]
        instance_collection = bpy.data.collections.new(obj.name)
        col_props: SBE_CollectionProperties = SBE_CollectionProperties.get(instance_collection)
        obj_props: SBE_ObjectProperties = SBE_ObjectProperties.get(obj)
        # TODO transfer other props like visibility
        col_props.uv_scale = obj_props.uv_scale
        col_props.skip_mesh_uv_scale = obj_props.skip_mesh_uv_scale
        # TODO apply to all objects once they're real
        # remember what was instanced
        instance_collection[SBE_INSTANCE_SOURCE_PROP] = obj.instance_collection[SBE_CUSTOM_ID_PROP]
        instance_collection[SBE_CUSTOM_ID_PROP] = -1
        parent_collection.objects.unlink(obj)
        instance_collection.objects.link(obj)
        parent_collection.children.link(instance_collection) # link collection to old place
        return instance_collection
    else:
        SBE_Logger.error("Wrong amount of parent collections for " + obj.name)
        return None


def instance_referenced_collections(context: bpy.types.Context) -> None:
    """Look for all collections without a parent and append them to the current scene to call duplicates_make_real on them"""
    with SBE_Logger("instance_referenced_collections"):
        temp_col = bpy.data.collections.new("sbe_instance_referenced_collections")
        context.scene.collection.children.link(temp_col)

        for i in bpy.data.collections:
            collection: bpy.types.Collection = i
            if get_collection_parent(collection) is None and not is_scene_collection(collection):
                temp_col.children.link(collection)
        instancers = []
        for i in temp_col.all_objects:
            obj: bpy.types.Object = i
            if SBE_IS_INSTANCER_PROP in obj:
                instancers.append(obj)
        with context.temp_override(selected_editable_objects=instancers):
            # Internal hierarchy stuff is useless since it won't preserve collections
            bpy.ops.object.duplicates_make_real(
                use_base_parent=False, use_hierarchy=False)

        with SBE_Logger("cleanup"):
            # get rid of all the now useless instancer empties
            instance_sources = [i for i in temp_col.all_objects if SBE_IS_INSTANCER_PROP in i]
            bpy.data.batch_remove(instance_sources)

        # don't actually delete it, since contents are still referenced
        context.scene.collection.children.unlink(temp_col)

def prepare() -> list[bpy.types.Collection]:
    """Make sure all objects are visible and make real works properly"""
    with SBE_Logger("prepare"):
        for i in bpy.data.collections:
            collection: bpy.types.Collection = i
            # make sure they can be purged
            collection.use_fake_user = False
            collection.asset_clear()
            collection.hide_select = False
            # hidden children still get exported but are processed wrong
            # so unhide them instead.
            collection.hide_viewport = False

        instanced_collections = set()
        discarded_instances: list[bpy.types.Object] = []
        for i in bpy.data.objects:
            obj: bpy.types.Object = i

            obj.use_fake_user = False
            obj.asset_clear()
            # duplicates_make_real skips invisible objects, we need collisions etc.
            obj.hide_viewport = False
            # needs to be selectable as well
            obj.hide_select = False

            if obj.instance_type != 'COLLECTION':
                if obj.instance_type != 'NONE':
                    SBE_Logger.error("Unsupported instancing type for " + obj.name)
                continue

            if obj.instance_collection is None:
                SBE_Logger.error("instance_collection is None for " + obj.name)
                continue

            if object_is_discard(obj):
                discarded_instances.append(obj)
                continue

            # duplicates_make_real will leave the empty used to instance,
            # so we mark them for deletion afterwards
            obj[SBE_IS_INSTANCER_PROP] = True
            instanced_collections.add(obj.instance_collection)

        bpy.data.batch_remove(discarded_instances)
        return list(instanced_collections)


def assign_custom_id(col: bpy.types.Collection):
    """Recursively assign ids to collection and all children cols/objs"""
    custom_id = get_custom_id()
    col[SBE_CUSTOM_ID_PROP] = custom_id
    for j in col.objects:
        obj: bpy.types.Object = j
        obj[SBE_PARENT_COLLECTION_PROP] = custom_id
    for j in col.children:
        child: bpy.types.Collection = j
        child[SBE_PARENT_COLLECTION_PROP] = custom_id
        assign_custom_id(child)


def unhide_all(context: bpy.types.Context):
    """Some operators don't work properly on hidden objects, this state shouldn't affect the bake anyways"""
    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        obj.hide_set(state=False, view_layer=context.view_layer)
        obj.hide_viewport = False


def enable_all_collections(collections: list[bpy.types.LayerCollection]):
    """Walk all LayerCollection children and enable them"""
    for col in collections:
        col.exclude = False
        enable_all_collections(col.children)


def geo_nodes_outputs_instances(context: bpy.types.Context):
    dependency_graph = context.evaluated_depsgraph_get()
    names_to_delete = []
    for i in dependency_graph.object_instances:
        instance: bpy.types.DepsgraphObjectInstance = i
        if not instance.is_instance:
            continue

        if instance.parent.name.find("make_real_and_delete") == -1:
            continue

        names_to_delete.append(instance.parent.name)

        if instance.instance_object.instance_type == 'NONE':
            continue

        real_instance = bpy.data.objects.new(f"INST{instance.instance_object.name}", None)
        real_instance.empty_display_type = 'PLAIN_AXES'

        # copy just to be save
        real_instance.matrix_world = instance.matrix_world.copy()
        real_instance.instance_type = instance.instance_object.instance_type
        # important to use original here so we don't reference temporary depsgraph state
        real_instance.instance_collection = instance.instance_object.instance_collection.original
        instance.parent.original.users_collection[0].objects.link(real_instance)

    to_delete = []
    for i in names_to_delete:
        obj: bpy.types.Object = bpy.data.objects[i]
        if obj:
            to_delete.append(obj)
    bpy.data.batch_remove(to_delete)


class SBE_MakeReal(SBE_ExportOperatorBase):
    """Make all instances real"""
    bl_idname = SBE_OP_MAKE_REAL
    bl_label = "Make all instances real"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):

        # We don't care about linked collections here, since collection visibility is
        # decided by view layer
        enable_all_collections(context.view_layer.layer_collection.children)

        # Initial unhide in case there are no collections to resolve
        unhide_all(context=context)

        context.view_layer.update()
        geo_nodes_outputs_instances(context=context)

        if start.has_run:
            # The rest of logic resolve the entire blend, so no need
            # to run this per scene
            return

        # Animations should be baked from frame 1
        context.scene.frame_current = 1

        # https://projects.blender.org/blender/blender/issues/99088
        # curves with modifiers get duplicated when calling duplicates_make_real
        # If this ever gets fixed, we can also remove the workaround in
        # sbe_make_real.py assign_default_materials
        with SBE_Logger("curve_modifier_fix"):
            for i in bpy.data.objects:
                obj: bpy.types.Object = i
                if obj.type != 'CURVE':
                    continue
                for j in obj.modifiers:
                    mod: bpy.types.Modifier = j
                    # gets turned on again later when generating the meshes for bake/game
                    mod.show_viewport = False

        # all collections which are references for instancing
        instanced_collections: list[bpy.types.Collection] = prepare()

        for attempts in range(0, 10):
            if not instanced_collections:
                # clear the orphans on the way out
                bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
                SBE_Logger.print(f"Resolved collection dependencies with {attempts} attempts.")
                # unhide_all(context=context) # TODO tk not needded?
                return

            # go look for collections which don't instance any other collections
            leaf_source_collections = []
            for i in instanced_collections[:]:
                col: bpy.types.Collection = i
                leaf = True
                for j in col.all_objects:
                    obj: bpy.types.Object = j
                    if SBE_IS_INSTANCER_PROP in obj:
                        leaf = False
                        break
                if leaf:
                    leaf_source_collections.append(col)
                    instanced_collections.remove(col)

            # assign ids for reconstruction
            with SBE_Logger("assign_custom_id"):
                for i in leaf_source_collections:
                    col: bpy.types.Collection = i
                    assign_custom_id(col)

            # make sure the collections can be made real by linking them to the current scene
            temp_col = bpy.data.collections.new("sbe_instance_referenced_collections")
            context.scene.collection.children.link(temp_col)

            # find any instancers instancing the leaf collections
            leaf_instancers = []
            leaf_collections = []

            with SBE_Logger("backup_instance_source"):
                for i in bpy.data.objects:
                    obj: bpy.types.Object = i
                    if obj.instance_collection not in leaf_source_collections:
                        continue
                    leaf_instancers.append(obj)
                    col = backup_instance_source(obj)
                    leaf_collections.append(col)
                    # add to temp collection to make real
                    temp_col.children.link(obj.users_collection[0])

            # make those real
            with SBE_Logger("duplicates_make_real"):
                with context.temp_override(selected_editable_objects=leaf_instancers):
                    bpy.ops.object.duplicates_make_real(
                        use_base_parent=False, use_hierarchy=False)

            # do the reconstruction
            bpy.data.batch_remove(leaf_instancers)
            with SBE_Logger("restore_hierarchy"):
                restore_hierarchy(temp_col)

            bpy.data.collections.remove(temp_col)

        SBE_Logger.error("Ran out of attempts to resolved collection dependencies!")
