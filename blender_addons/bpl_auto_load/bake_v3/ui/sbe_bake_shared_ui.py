# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_util import nameof
from bake_v3.properties.sbe_bake_props import SBE_BakeProperties, SBE_CalculatedBakeProperties
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.properties.sbe_blend_props import SBE_BlendProperties

def draw_bake_prop(layout: bpy.types.UILayout, prop_name: str, current: SBE_BakeProperties, derived: SBE_CalculatedBakeProperties) -> None:
    is_set_prop_name = f"{prop_name}_set"
    enabled = getattr(current, is_set_prop_name)

    row: bpy.types.UILayout = layout.row(align=False)
    row.prop(current, is_set_prop_name)
    if enabled:
        row.prop(current, prop_name, text="")
        return
    derived_value = getattr(derived, prop_name)
    row.label(text=str(derived_value))


def draw_bake_properties(layout: bpy.types.UILayout, owner: bpy.types.Collection) -> None:
    props: SBE_CollectionProperties = SBE_CollectionProperties.get(owner)
    derived: SBE_CalculatedBakeProperties = SBE_CollectionProperties.evaluate_bake_prop(owner=owner)

    blend_data: SBE_BlendProperties = SBE_BlendProperties.get()
    current: SBE_BakeProperties
    if blend_data.bake_preset == 'FAST':
        current = props.bake_debug
    else:
        current = props.bake_settings
    layout.prop(data=blend_data, property=nameof(blend_data.bake_own_process), expand=True)
    layout.prop(data=blend_data, property=nameof(blend_data.bake_preset), expand=True)
    draw_bake_prop(layout, nameof(current.resolution), current, derived)
    draw_bake_prop(layout, nameof(current.resolution_relative), current, derived)
    draw_bake_prop(layout, nameof(current.samples), current, derived)
    draw_bake_prop(layout, nameof(current.margin), current, derived)
    draw_bake_prop(layout, nameof(current.post_process), current, derived)
    draw_bake_prop(layout, nameof(current.post_process_node), current, derived)
    draw_bake_prop(layout, nameof(current.color_grade_node), current, derived)
    draw_bake_prop(layout, nameof(current.cage_distance), current, derived)
    draw_bake_prop(layout, nameof(current.global_illumination), current, derived)
    draw_bake_prop(layout, nameof(current.passes), current, derived)
    draw_bake_prop(layout, nameof(current.denoise), current, derived)
