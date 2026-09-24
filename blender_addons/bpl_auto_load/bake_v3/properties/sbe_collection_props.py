"""
Properties attached to collections
There is some overlap with object properties, these will be derived to objects at export.
"""

import typing
import dataclasses

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.properties.sbe_bake_props import (
    SBE_BakeProperties, SBE_CalculatedBakeProperties,
    SBE_BakePropertiesDefault, SBE_BakePropertiesFast
)
from bake_v3.properties.sbe_blend_props import SBE_BlendProperties
from bake_v3.sbe_collection_util import get_collection_parent

class SBE_CollectionProperties(bpy.types.PropertyGroup):
    bake_settings: bpy.props.PointerProperty(
        type=SBE_BakeProperties, name="Release Bake Settings",
        description="Settings used for CLI bake")

    bake_debug: bpy.props.PointerProperty(
        type=SBE_BakeProperties, name="Debug Bake Settings",
        description="Settings used for testing")

    is_bake_group: bpy.props.BoolProperty(
        name="Is Bake Group",
        description="Top level collection which should get own bake map.",
        default=False)

    skip_bake: bpy.props.BoolProperty(
        name="Skip Bake",
        description="Collection will be skipped when baking. This setting will be ignored on CLI bake.",
        default=False)

    visibility: bpy.props.EnumProperty(items=[
            ('VISIBLE', "Visible", "Visible in all aspects.", 'VIEW_CAMERA_UNSELECTED', 0),
            ('DISCARD', "Discard", "Removed at the beginning. Use this for commenting out stuff.", 'CANCEL', 1),
            ('HIDDEN', "Hidden", "Not visible in game or bake, but other objects/modifiers depend on it.", 'GHOST_DISABLED', 2),
            ('ONLY_BAKE', "Only in Bake", "Not visible in game but affects bake by casting shadows etc.", 'OUTLINER_OB_LIGHT', 3),
            ('ONLY_GAME', "Only Game", "Visible in game but does not affect bake.", 'INTERNET_OFFLINE', 4),
        ],
        name='Visibility',
        description='TODO The visibility system is not ready for use yet',
        default='VISIBLE')

    uv_scale: bpy.props.FloatProperty(
        name="UV Scale",
        description="Scale multiplier applied to all collection children",
        default=1.0,
        soft_min=0.01, soft_max=2,
        step=0.1, precision=3,
        subtype='FACTOR', unit='NONE',
        override={'LIBRARY_OVERRIDABLE'})

    skip_mesh_uv_scale: bpy.props.BoolProperty(
        name="Skip Mesh UV Scales", description="TODO NOT IMPLEMENTED Ignore bake_size= vertex group on objects",
        default=False,
        override={'LIBRARY_OVERRIDABLE'})

    @staticmethod
    def register_property() -> None:
        bpy.utils.register_class(SBE_CollectionProperties)
        bpy.types.Collection.sbe_properties = bpy.props.PointerProperty(
            type=SBE_CollectionProperties, name="SBE Collection Properties",
            description="STUNTBOOST collection properties",
            override={'LIBRARY_OVERRIDABLE'})

    @staticmethod
    def unregister_property() -> None:
        del bpy.types.Collection.sbe_properties
        bpy.utils.unregister_class(SBE_CollectionProperties)

    @staticmethod
    def get(col: bpy.types.Collection) -> typing.Self:
        return col.sbe_properties

    @staticmethod
    def set(col: bpy.types.Collection, props: typing.Self) -> None:
        target = SBE_CollectionProperties.get(col)
        # Not copying bake settings because bake groups aren't instanced for now
        # target.bake_settings = props.bake_settings
        # target.bake_debug = props.bake_debug
        target.is_bake_group = props.is_bake_group
        target.skip_bake = props.skip_bake
        target.visibility = props.visibility
        target.uv_scale = props.uv_scale

    @staticmethod
    def evaluate_bake_prop(owner: bpy.types.Collection) -> SBE_CalculatedBakeProperties:
        """Evaluates the hierarchy and returns the final bake values."""
        blend_props: SBE_BlendProperties = SBE_BlendProperties.get()
        fast = blend_props.bake_preset == 'FAST'
        result = SBE_CalculatedBakeProperties
        if fast:
            # gets a copy of the default obj
            result = dataclasses.replace(SBE_BakePropertiesFast)
        else:
            # gets a copy of the default obj
            result = dataclasses.replace(SBE_BakePropertiesDefault)

        while True:
            sbe_prop: SBE_CollectionProperties = SBE_CollectionProperties.get(owner)
            bake_prop: SBE_BakeProperties
            if fast:
                bake_prop = sbe_prop.bake_debug
            else:
                bake_prop = sbe_prop.bake_settings
            result = bake_prop.fill(result)
            owner = get_collection_parent(owner)
            if owner is None:
                return result
        return result
