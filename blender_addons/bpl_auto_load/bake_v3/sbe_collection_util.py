"""
Collection related functionality
"""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_custom_properties import SBE_TEMP_NO_SKIP_BAKE_PROP
from bake_v3.sbe_util import retrieve_temp

def get_collection_parent(collection: bpy.types.Collection) -> bpy.types.Collection | None:
    """Get the direct parent of a collection, including the scene collection!"""
    for i in bpy.data.collections:
        col: bpy.types.Collection = i
        if collection.name in col.children:
            return col
    for i in bpy.data.scenes:
        scene: bpy.types.Scene = i
        if collection.name in scene.collection.children:
            return scene.collection
    return None


def get_collections_parents(collection: bpy.types.Collection) -> list[bpy.types.Collection]:
    """Returns all the parent collections INCLUDING itself."""
    result: list[bpy.types.Collection] = []

    while collection:
        result.append(collection)
        collection = get_collection_parent(collection)

    return result


def is_top_level_collection(collection: bpy.types.Collection) -> bool:
    """Returns true if the collection is a direct child of the scene collection."""
    for i in bpy.data.scenes:
        scene: bpy.types.Scene = i
        if collection.name in scene.collection.children:
            return True
    return False


def is_scene_collection(collection: bpy.types.Collection) -> bool:
    """Whether a collection is the scene collection."""
    for i in bpy.data.scenes:
        scene: bpy.types.Scene = i
        if scene.collection == collection:
            return True
    return False


def delete_collection_hierarchy(collections: list[bpy.types.Collection]) -> None:
    """Delete collections and all of its child objects and collections safely"""
    children = set()
    # delete the objects now
    for collection in collections:
        bpy.data.batch_remove(collection.all_objects)
        children.add(collection)
        for child in collection.children:
            children.add(child)
    # but the child collections later
    bpy.data.batch_remove(children)


def get_all_bake_collections() -> list[bpy.types.Collection]:
    """Returns all top level collections across scenes so the ids generated are stable"""
    result = []
    for i in bpy.data.scenes:
        scene: bpy.types.Scene = i
        for j in scene.collection.children:
            col: bpy.types.Collection = j
            # This is not properly type referenced because
            # this would create a circular dependency
            if col.sbe_properties.is_bake_group:
                result.append(col)
    return result


def get_all_scene_bake_collection(context: bpy.types.Context) -> list[bpy.types.Collection]:
    """Returns all top level collections of the current scene"""
    all_collections = get_all_bake_collections()
    result = []
    scene_collection = context.scene.collection

    for i in all_collections:
        col: bpy.types.Collection = i
        if col.name in scene_collection.children:
            result.append(col)
    return result


def get_bake_collections(context: bpy.types.Context) -> list[bpy.types.Collection]:
    """Returns all top level collections marked for baking of the current scene"""
    result = get_all_scene_bake_collection(context)
    if retrieve_temp(SBE_TEMP_NO_SKIP_BAKE_PROP) is not True:
        for i in result[:]:
            col: bpy.types.Collection = i
            # This is not properly type referenced because
            # this would create a circular dependency
            if col.sbe_properties.skip_bake:
                result.remove(col)
    return result
