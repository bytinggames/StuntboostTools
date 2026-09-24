# TODO Proper UI
# store problem source path properly
# Allow direct selection of the problem source
# Auto resolve options for trivial problems?
import re

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from check_blend.check_blend_types import ProblemItem
from check_blend.check_blend_checks import ALL_CHECKS

PATH_SPLIT_PATTERN = re.compile(r'''((?:[^."']|"[^"]*"|'[^']*')+)''')

class ProblemListItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Name", description="A name for this item", default="Untitled")
    message: bpy.props.StringProperty(
        name="Message", description="Problem for this item", default="")
    solution: bpy.props.StringProperty(
        name="Solution", description="Solution for this item", default="")
    icon: bpy.props.StringProperty(name="Icon", default="OBJECT_DATA")
    path: bpy.props.StringProperty(
        name="Path", description="Contains json of path data to locate the object", default="")


class LIST_UL_sb_errors(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item: ProblemListItem, _icon, _active_data, _active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=f'"{item.name}": {item.message}', icon=item.icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon=item.icon)


def select_obj(obj: bpy.types.Object, context: bpy.types.Context) -> bpy.types.Object:
    context.view_layer.objects.active = obj
    obj.select_set(state=True, view_layer=context.view_layer)
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            with context.temp_override(area=area, region=area.regions[-1]):
                bpy.ops.view3d.view_selected()
    return obj

def bring_node_into_view():
    context = bpy.context
    for area in context.screen.areas:
        if area.type == 'NODE_EDITOR':
            with context.temp_override(area=area, region=area.regions[-1]):
                if bpy.ops.node.view_selected.poll():
                    bpy.ops.node.view_selected()


def select_from_path(path: str, context: bpy.types.Context) -> None:
    bpy.ops.object.select_all(action='DESELECT')
    context.view_layer.objects.active = None

    parts = PATH_SPLIT_PATTERN.split(path)[1::2]
    current: str = None
    mesh: bpy.types.Mesh = None
    obj: bpy.types.Object = None
    material: bpy.types.Material = None
    node_tree: bpy.types.ShaderNodeTree = None
    user_map = bpy.data.user_map()
    for i in parts:
        if current:
            current += f".{i}"
        else:
            current = i
        result = eval(current)
        if isinstance(result, bpy.types.Object):
            obj = select_obj(result, context)
            continue
        if isinstance(result, bpy.types.Material):
            if not mesh or not obj:
                users = user_map[result]
                for j in users:
                    if isinstance(j, bpy.types.Mesh):
                        mesh = j
                        continue
                    if isinstance(j, bpy.types.Object):
                        obj = select_obj(j, context)
                        continue
            if not obj:
                users = user_map[mesh]
                for j in users:
                    if isinstance(j, bpy.types.Object):
                        obj = select_obj(j, context)
                        break
            material = result
            for j in obj.material_slots:
                material_slot: bpy.types.MaterialSlot = j
                if material_slot.material == material:
                    obj.active_material_index = material_slot.slot_index
                    break
            continue
        if isinstance(result, bpy.types.ShaderNodeTree):
            node_tree = result
            continue
        if hasattr(result, "bl_idname") and result.bl_idname.startswith("ShaderNode"):
            node_tree.nodes.active = result
            for j in node_tree.nodes:
                j.select = False
            result.select = True
            bpy.app.timers.register(function=bring_node_into_view, first_interval=0.1)


def problem_list_selected_get(scene: bpy.types.Scene) -> int:
    if "ProblemListSelected" in scene:
        return scene["ProblemListSelected"]
    return 0

def problem_list_selected_set(scene: bpy.types.Scene, value: int):
    if len(scene.ProblemList) != 0:
        active: ProblemListItem = scene.ProblemList[value]
        select_from_path(path=active.path, context=bpy.context)
    scene["ProblemListSelected"] = value

class SB_CheckBlendResultPanel(bpy.types.Panel):
    """Creates a Panel in Item the Object properties window"""
    bl_label = "Problems"
    bl_idname = "OBJECT_PT_sb_error_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = "UI"
    bl_category = "STUNTBOOST"

    def draw(self: bpy.types.Panel, context: bpy.types.Context):
        self.layout.operator("object.sb_check_blend", icon='ERROR')
        self.layout.template_list(
            listtype_name="LIST_UL_sb_errors",
            list_id="",
            dataptr=context.scene, # list owner
            propname="ProblemList", # name of list property on owner
            active_dataptr=context.scene, # owner of active_propname
            active_propname="ProblemListSelected")
        if len(context.scene.ProblemList) == 0:
            return
        active: ProblemListItem = context.scene.ProblemList[context.scene.ProblemListSelected]
        if active:
            self.layout.label(text=active.name)
            self.layout.label(text=active.message)
            self.layout.label(text=active.solution)
            self.layout.label(text=active.path)


class SB_CheckBlend(bpy.types.Operator):
    """Checks the blend file content for any potential problems"""
    bl_idname = "object.sb_check_blend"
    bl_label = "Checks the blend file content for any potential problems"

    def execute(self, context):
        problems: list[ProblemItem] = []
        for check in ALL_CHECKS:
            problems.extend(check())

        # TODO check for shadow casters & other invisible object materials
        # TODO check object uvs
        # TODO check if there are loose object on the top level not belonging to a bake collection
        # TODO check missing uvs


        print("===================================================")
        print("================== Check Results ==================")
        print("===================================================")
        context.scene.ProblemList.clear()
        for i in problems:
            list_item: ProblemListItem = context.scene.ProblemList.add()
            list_item.name = i.name
            list_item.icon = i.icon
            list_item.message = i.message
            list_item.solution = i.solution
            list_item.path = i.path
            print(f"{i.path} {i.message} {i.solution}")
        print("===================================================")
        print("=================== Results END ===================")
        print("===================================================")
        return {'FINISHED'}

    @staticmethod
    def bpl_load():
        bpy.utils.register_class(ProblemListItem)
        # don't store in scene maye? don't want it saved in blend
        bpy.types.Scene.ProblemList = bpy.props.CollectionProperty(type=ProblemListItem)
        bpy.types.Scene.ProblemListSelected = bpy.props.IntProperty(
            name="Selected Problem", default = 0, set=problem_list_selected_set, get=problem_list_selected_get)
        bpy.utils.register_class(SB_CheckBlend)
        bpy.utils.register_class(SB_CheckBlendResultPanel)
        bpy.utils.register_class(LIST_UL_sb_errors)

    @staticmethod
    def bpl_unload():
        del bpy.types.Scene.ProblemList
        del bpy.types.Scene.ProblemListSelected
        bpy.utils.unregister_class(ProblemListItem)
        bpy.utils.unregister_class(SB_CheckBlend)
        bpy.utils.unregister_class(SB_CheckBlendResultPanel)
        bpy.utils.unregister_class(LIST_UL_sb_errors)
