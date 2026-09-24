"""
Blend wide properties.
There's no proper way of attaching custom data to blends (only scene, object etc. data blocks)
We abuse the text data block for this.
"""

import typing

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_util import get_persistent_data_block

class SBE_BlendProperties(bpy.types.PropertyGroup):
    bake_preset: bpy.props.EnumProperty(items=[
            ('FAST', "Fast Bake", "Fast Bake"),
            ('RELEASE', "Release Bake", "Release Bake"),
        ],
        name='Bake Preset',
        description='The bake quality preset used when exporting from the UI.',
        default='RELEASE')

    # TODO this should probably be a addon preference, not per blend
    bake_own_process: bpy.props.BoolProperty(
        name='Bake in own Process',
        description='Bake in separate process',
        default=False)


    @staticmethod
    def register_property() -> None:
        bpy.utils.register_class(SBE_BlendProperties)
        bpy.types.Text.sbe_properties = bpy.props.PointerProperty(
            type=SBE_BlendProperties, name="SBE Blend Properties",
            description="Blend wide properties for STUNTBOOST Export")

    @staticmethod
    def unregister_property() -> None:
        del bpy.types.Text.sbe_properties
        bpy.utils.unregister_class(SBE_BlendProperties)

    @staticmethod
    def get() -> typing.Self:
        block = get_persistent_data_block()
        return block.sbe_properties
