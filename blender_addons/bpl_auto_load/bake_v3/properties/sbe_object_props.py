"""
Custom properties attached to objects and empties.
There is some overlap with collection properties
"""

import typing

# pylint: disable=import-error
import bpy
# pylint: enable=import-error


class SBE_FunctionProperties(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Function Name",
        description="TODO not implemented",
        translation_context='*',
        default='', maxlen=0)

    # TODO function params etc


class SBE_ObjectProperties(bpy.types.PropertyGroup):
    visibility: bpy.props.EnumProperty(items=[
            ('VISIBLE', "Visible", "Visible in all aspects.", 'VIEW_CAMERA_UNSELECTED', 0),
            ('DISCARD', "Discard", "Removed at the beginning not part of bake or game. Use this for commenting out stuff.", 'CANCEL', 1),
            ('HIDDEN', "Hidden", "Not visible in game or bake, but other objects/modifiers depend on it. Or Physics?", 'GHOST_DISABLED', 2),
            ('ONLY_BAKE', "Only in Bake", "Not visible in game but affects bake by casting shadows etc.", 'OUTLINER_OB_LIGHT', 3),
            ('ONLY_GAME', "Only Game", "Visible in game but does not affect bake.", 'INTERNET_OFFLINE', 4),
        ],
        name='Visibility',
        description='TODO dont use this',
        default='VISIBLE')

    physics: bpy.props.EnumProperty(items=[
            ('COLLISION', "Collision", "Mesh will collide.", 'FILE_3D', 0),
            ('TRIGGER', "Trigger", "Mesh will can be used for triggers but will not collide.", 'FILE_VOLUME', 1),
            ('NONE', "No Collision", "Mesh won't interact with physics engine.", 'SELECT_SET', 2),
        ],
        name='Physics',
        description='TODO dont use this',
        default='NONE')

    uv_scale: bpy.props.FloatProperty(
        name="UV Scale", description="UV Scale multiplier",
        default=1.0,
        soft_min=0.01, soft_max=2,
        step=0.1, precision=3,
        subtype='FACTOR', unit='NONE',
        override={'LIBRARY_OVERRIDABLE'})

    skip_mesh_uv_scale: bpy.props.BoolProperty(
        name="Skip Mesh UV Scale", description="Ignore bake_size= vertex group on object",
        default=False,
        override={'LIBRARY_OVERRIDABLE'})

    functions: bpy.props.CollectionProperty(
        type=SBE_FunctionProperties,
        name="Functions",
        description="TODO not implemented")

    properties: bpy.props.CollectionProperty(
        type=SBE_FunctionProperties,
        name="Properties",
        description="TODO not implemented")

    @staticmethod
    def register_property() -> None:
        bpy.utils.register_class(SBE_FunctionProperties)
        bpy.utils.register_class(SBE_ObjectProperties)
        bpy.types.Object.sbe_properties = bpy.props.PointerProperty(
            type=SBE_ObjectProperties, name="SBE Object Properties",
            description="Contains ",
            override={'LIBRARY_OVERRIDABLE'})

    @staticmethod
    def unregister_property() -> None:
        del bpy.types.Object.sbe_properties
        bpy.utils.unregister_class(SBE_ObjectProperties)
        bpy.utils.unregister_class(SBE_FunctionProperties)

    @staticmethod
    def get(obj: bpy.types.Object) -> typing.Self:
        return obj.sbe_properties
