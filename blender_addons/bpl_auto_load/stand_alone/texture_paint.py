# pylint: disable=import-error
import bpy
# pylint: enable=import-error

class SB_HardBrush(bpy.types.Operator):
    bl_idname = "view3d.sb_select_brush_hard"
    bl_label = "Simple operator"
    bl_description = "Hard Brush"
    bpl_auto_load = True

    def execute(self, context: bpy.types.Context):
        if context.object.mode == 'TEXTURE_PAINT':
            if context.tool_settings.image_paint.brush.image_tool != 'DRAW':
                bpy.ops.paint.brush_select(image_tool='DRAW')
            bpy.context.tool_settings.image_paint.brush.use_pressure_size = True
            bpy.context.tool_settings.image_paint.brush.use_pressure_strength = False
        return {'FINISHED'}

class SB_SoftBrush(bpy.types.Operator):
    bl_idname = "view3d.sb_select_brush_soft"
    bl_label = "Simple operator"
    bl_description = "Soft Brush"
    bpl_auto_load = True

    def execute(self, context: bpy.types.Context):
        if context.object.mode == 'TEXTURE_PAINT':
            if context.tool_settings.image_paint.brush.image_tool != 'DRAW':
                bpy.ops.paint.brush_select(image_tool='DRAW')
            bpy.context.tool_settings.image_paint.brush.use_pressure_size = False
            bpy.context.tool_settings.image_paint.brush.use_pressure_strength = True
        return {'FINISHED'}


class SB_PT_TexturePaintPanel(bpy.types.Panel):
    bl_idname = "SB_PT_texture_paint_panel" # naming convention from blender
    bl_label = "Byting Brush Panel"
    bl_category = "STUNTBOOST"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bpl_auto_load = True

    def draw(self, _context: bpy.types.Context):
        layout = self.layout
        row = layout.row()
        row.operator(SB_HardBrush.bl_idname, text=SB_HardBrush.bl_description)
        row = layout.row()
        row.operator(SB_SoftBrush.bl_idname, text=SB_SoftBrush.bl_description)

