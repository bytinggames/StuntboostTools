"""
Properties related to bake,
Attached to scene collections and normal top level collections.
They use a small inheritance system, so settings not set in collection will derive them
from scenes, which will derive them from the defaults set below.
There's also 2 instances of the properties, one for release bakes and one for fast bakes.
"""

from dataclasses import dataclass

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

@dataclass
class SBE_CalculatedBakeProperties():
    resolution: int
    resolution_relative: float
    samples: int
    margin: int
    post_process: bool
    post_process_node: str
    color_grade_node: str
    denoise: str
    cage_distance: float
    global_illumination: str
    passes: str

SBE_BakePropertiesDefault = SBE_CalculatedBakeProperties(
    resolution = 1024 * 4,
    resolution_relative = 1.0,
    samples = 64,
    margin = 4,
    post_process = True,
    post_process_node = "post_pro",
    color_grade_node = "color_grade",
    denoise = 'OPENIMAGEDENOISE',
    # denoise = 'OPTIX',
    cage_distance = 0.05,
    global_illumination = 'LIMITED',
    passes = 'COMBINED_AO_DIRECT')

SBE_BakePropertiesFast = SBE_CalculatedBakeProperties(
    resolution = 1024 * 2,
    resolution_relative = 1.0,
    samples = 8,
    margin = 4,
    post_process = False,
    post_process_node = "post_pro",
    color_grade_node = "color_grade", # also use color grade here so the preview command works
    denoise = 'OPTIX',
    cage_distance = 0.05,
    global_illumination = 'LIMITED',
    passes = 'COMBINED')


def post_process_node_suggestions(_self, _context: bpy.types.Context, edit_text: str) -> list[str]:
    """Function to provide auto complete suggestions for the drop down"""
    result: list[str] = []
    for i in bpy.data.node_groups:
        group: bpy.types.NodeGroup = i
        if group.type == 'COMPOSITING':
            if len(edit_text) != 0:
                if group.name.find(edit_text) == -1:
                    continue
            result.append(group.name)
    return result

class SBE_BakeProperties(bpy.types.PropertyGroup):
    """
    Bake properties, To retrieve them use SBE_CollectionProperties.evaluate_bake_prop
    since these values are derived through the collection hierarchy.
    """
    resolution_set: bpy.props.BoolProperty(name="Resolution set", default=False)
    resolution: bpy.props.IntProperty(
        name="Resolution", description="Bake resolution in pixels.",
        default=SBE_BakePropertiesDefault.resolution,
        min=4, max=1024 * 8,
        soft_min=4, soft_max=1024 * 4,
        step=1, subtype='PIXEL')

    resolution_relative_set: bpy.props.BoolProperty(name="Relative Resolution set", default=False)
    resolution_relative: bpy.props.FloatProperty(
        name="Relative Resolution", description="TODO",
        default=SBE_BakePropertiesDefault.cage_distance,
        soft_min=0.1, soft_max=4,
        step=0.01, precision=3,
        subtype='FACTOR', unit='NONE') # or maybe 'PERCENTAGE'

    samples_set: bpy.props.BoolProperty(name="Samples set", default=False)
    samples: bpy.props.IntProperty(
        name="Samples",
        description="Ray tracing sample count, higher values take more time but produce better results. 0 will skip the bake entirely.",
        default=SBE_BakePropertiesDefault.samples,
        soft_min=0, soft_max=1024,
        step=1, subtype='NONE')

    margin_set: bpy.props.BoolProperty(name="Margin set", default=False)
    margin: bpy.props.IntProperty(
        name="Margin",
        description="Margin size the bake texture is extended. 0 might produce black seams with denoising or MIP mapping in game.",
        default=SBE_BakePropertiesDefault.margin,
        soft_min=0, soft_max=64,
        step=1, subtype='PIXEL')

    post_process_set: bpy.props.BoolProperty(name="Post Processing set", default=False)
    post_process: bpy.props.BoolProperty(
        name="Post Processing",
        description="Enable Post processing of the baked textures before saving",
        default=SBE_BakePropertiesDefault.post_process)

    post_process_node_set: bpy.props.BoolProperty(name="Post Processing Node set", default=False)
    post_process_node: bpy.props.StringProperty(
        name="Post Processing Node", description="The name of the post processing node group used in the compositor, needs to either exist in this file or /Props/PostProcessing.blend (PostProcessing_blender_5.blend on Blender 5+)",
        default=SBE_BakePropertiesDefault.post_process_node,
        search=post_process_node_suggestions, search_options={'SUGGESTION'})

    color_grade_node_set: bpy.props.BoolProperty(name="Color Grade Node set", default=False)
    color_grade_node: bpy.props.StringProperty(
        name="Color Grade Node", description="The name of the color grade node group used in the compositor after post processing, needs to either exist in this file or /Props/PostProcessing.blend (PostProcessing_blender_5.blend on Blender 5+)",
        default=SBE_BakePropertiesDefault.color_grade_node,
        search=post_process_node_suggestions, search_options={'SUGGESTION'})

    cage_distance_set: bpy.props.BoolProperty(name="Cage distance set", default=False)
    cage_distance: bpy.props.FloatProperty(
        name="Cage distance", description="TODO",
        default=SBE_BakePropertiesDefault.cage_distance,
        soft_min=0.001, soft_max=1,
        step=0.01, precision=3,
        subtype='DISTANCE', unit='LENGTH')

    denoise_set: bpy.props.BoolProperty(name="Denoise set", default=False)
    denoise: bpy.props.EnumProperty(items=[
            ('NONE', "No denoising", "Disable denoising completely", 'OUTLINER_OB_LIGHT', 0),
            ('OPTIX', "OptiX Denoising", "nVidia Optix denoising", 'OUTLINER_DATA_LIGHT', 1),
            ('OPENIMAGEDENOISE', "Open Image Denoise", "Intel Open Image Denoise", 'LIGHT_POINT', 2),
        ],
        name="Denoise",
        description="Enable Cycles Denoise",
        default=SBE_BakePropertiesDefault.denoise)

    global_illumination_set: bpy.props.BoolProperty(name="Global Illumination set", default=False)
    global_illumination: bpy.props.EnumProperty(items=[
            ('FULL', "Full GI", "Full Global Illumination Preset", 'OUTLINER_OB_LIGHT', 0),
            ('LIMITED', "Limited GI", "Limited Global Illumination Preset", 'OUTLINER_DATA_LIGHT', 1),
            ('DIRECT', "Direct Light", "Direct Light Preset", 'LIGHT_POINT', 2),
        ],
        name="Global Illumination",
        description="",
        default=SBE_BakePropertiesDefault.global_illumination)

    passes_set: bpy.props.BoolProperty(name="Passes set", default=False)
    passes: bpy.props.EnumProperty(items=[
            ('COMBINED_AO_DIRECT', "Combined + AO + Direct", "Bake Combined + Ambient Occlusion + Direct Light", 'OUTLINER_OB_LIGHT', 0),
            ('COMBINED', "Combined", "Only bake combined pass", 'OUTLINER_DATA_LIGHT', 1),
        ],
        name="Bake Passes",
        description="",
        default=SBE_BakePropertiesDefault.passes)

    def fill(self, last_layer: SBE_CalculatedBakeProperties) -> SBE_CalculatedBakeProperties:
        # TODO probably a nice way to iterate this similar to dataclasses
        if self.resolution_set:
            last_layer.resolution = self.resolution
        if self.resolution_relative_set:
            last_layer.resolution_relative = self.resolution_relative
        if self.samples_set:
            last_layer.samples = self.samples
        if self.margin_set:
            last_layer.margin = self.margin
        if self.post_process_set:
            last_layer.post_process = self.post_process
        if self.cage_distance_set:
            last_layer.cage_distance = self.cage_distance
        if self.global_illumination_set:
            last_layer.global_illumination = self.global_illumination
        if self.passes_set:
            last_layer.passes = self.passes
        if self.post_process_node_set:
            last_layer.post_process_node = self.post_process_node
        if self.color_grade_node_set:
            last_layer.color_grade_node = self.color_grade_node
        if self.denoise_set:
            last_layer.denoise = self.denoise
        return last_layer

    @staticmethod
    def register_property() -> None:
        bpy.utils.register_class(SBE_BakeProperties)

    @staticmethod
    def unregister_property() -> None:
        bpy.utils.unregister_class(SBE_BakeProperties)
