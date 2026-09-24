"""
TODO not used at the moment
Modifiers also can have visibility properties, but theres's no nice way of
displaying them, so for now we still use the name convention.
"""

import typing

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

class SBE_ModifierProperties(bpy.types.PropertyGroup):
    visibility = bpy.props.EnumProperty([
        ('NORMAL', "Normal", "Modifier will be applied and is always visible.", 'FILE_3D', 0),
        ('BAKE', "Only Bake", "Modifier will be visible during bake, exported mesh will not have modifier applied.", 'FILE_VOLUME', 1),
        ('HIDDEN', "Modifier is never visible", 'SELECT_SET', 2),
    ],
    name='Visibility',
    description='TODO',
    default=None)

    @staticmethod
    def register_property() -> None:
        bpy.utils.register_class(SBE_ModifierProperties)
        bpy.types.Modifier.sbe_properties = bpy.props.PointerProperty(
            type=SBE_ModifierProperties, name="SBE Modifier Properties",
            description="TODO")

    @staticmethod
    def unregister_property() -> None:
        del bpy.types.Modifier.sbe_properties
        bpy.utils.unregister_class(SBE_ModifierProperties)

    @staticmethod
    def get(mod: bpy.types.Modifier)  -> typing.Self:
        return mod.sbe_properties
