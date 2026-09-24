"""
Since there might be dependencies between prop, they are registered here
so we have control of the order.
"""

from bake_v3.properties.sbe_bake_props import SBE_BakeProperties
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.properties.sbe_modifier_props import SBE_ModifierProperties
from bake_v3.properties.sbe_object_props import SBE_ObjectProperties
from bake_v3.properties.sbe_blend_props import SBE_BlendProperties


class SBE_RegisterProperties():
    @staticmethod
    def bpl_load() -> None:
        SBE_BakeProperties.register_property()
        SBE_CollectionProperties.register_property()
        SBE_ModifierProperties.register_property()
        SBE_ObjectProperties.register_property()
        SBE_BlendProperties.register_property()

    @staticmethod
    def bpl_unload() -> None:
        SBE_BakeProperties.unregister_property()
        SBE_CollectionProperties.unregister_property()
        SBE_ModifierProperties.unregister_property()
        SBE_ObjectProperties.unregister_property()
        SBE_BlendProperties.unregister_property()
