import textwrap

# pylint: disable=import-error
import bpy
from bpy.app.handlers import persistent
# pylint: enable=import-error

from check_blend.check_blend_types import ProblemItem
from check_blend.check_blend_checks import ALL_CHECKS
from check_blend.check_blend_navigation import navigate_to_problem


_problems: list[ProblemItem] = []
_SEVERITY_ORDER = {'ERROR': 0, 'WARNING': 1, 'INFO': 2}
_SEVERITY_ICONS = {'ERROR': 'CANCEL', 'WARNING': 'ERROR', 'INFO': 'INFO'}


class ProblemListItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(options={'SKIP_SAVE'})
    message: bpy.props.StringProperty(options={'SKIP_SAVE'})
    solution: bpy.props.StringProperty(options={'SKIP_SAVE'})
    icon: bpy.props.StringProperty(default='OBJECT_DATA', options={'SKIP_SAVE'})
    category: bpy.props.StringProperty(options={'SKIP_SAVE'})
    severity: bpy.props.StringProperty(default='WARNING', options={'SKIP_SAVE'})
    result_index: bpy.props.IntProperty(default=-1, options={'SKIP_SAVE'})


class CheckBlendState(bpy.types.PropertyGroup):
    problems: bpy.props.CollectionProperty(type=ProblemListItem, options={'SKIP_SAVE'})
    selected: bpy.props.IntProperty(default=-1, min=-1, options={'SKIP_SAVE'})
    has_run: bpy.props.BoolProperty(default=False, options={'SKIP_SAVE'})
    severity: bpy.props.EnumProperty(
        name="Severity", options={'SKIP_SAVE'},
        items=[('ALL', "All severities", "Show every finding"),
               ('ERROR', "Errors", "Show errors only"),
               ('WARNING', "Warnings", "Show warnings only"),
               ('INFO', "Information", "Show information only")])


@persistent
def clear_results(_unused=None):
    _problems.clear()
    for manager in bpy.data.window_managers:
        state = manager.sb_check_blend
        state.problems.clear()
        state.selected = -1
        state.has_run = False


class LIST_UL_sb_errors(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname):
        if self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon=_SEVERITY_ICONS[item.severity])
        else:
            row = layout.row(align=True)
            row.label(text="", icon=_SEVERITY_ICONS[item.severity])
            row.label(text=f"{item.name}: {item.message}", icon=item.icon)

    def draw_filter(self, _context, layout):
        layout.prop(self, "filter_name", text="", icon='VIEWZOOM')

    def filter_items(self, _context, data, propname):
        search = self.filter_name.casefold()
        flags = []
        for item in getattr(data, propname):
            matches_severity = data.severity == 'ALL' or item.severity == data.severity
            matches_search = search in " ".join((
                item.name, item.message, item.solution, item.category)).casefold()
            flags.append(self.bitflag_filter_item if matches_severity and matches_search else 0)
        return flags, []


def _draw_text(layout, context, text):
    width = max(20, int(context.region.width / (7 * context.preferences.system.ui_scale)) - 5)
    column = layout.column(align=True)
    for paragraph in text.splitlines():
        for line in textwrap.wrap(paragraph, width=width) or [""]:
            column.label(text=line)


class SB_CheckBlendResultPanel(bpy.types.Panel):
    bl_label = "Check Blend"
    bl_idname = "OBJECT_PT_sb_error_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "STUNTBOOST"

    def draw(self, context):
        state = context.window_manager.sb_check_blend
        row = self.layout.row(align=True)
        row.operator("object.sb_check_blend", icon='VIEWZOOM')
        if state.has_run:
            row.operator("object.sb_clear_blend_results", text="", icon='X')
        if not state.has_run:
            _draw_text(self.layout, context, "Audit the whole blend file without changing its content.")
            return
        if not state.problems:
            self.layout.label(text="No problems found.", icon='CHECKMARK')
            return

        errors = sum(item.severity == 'ERROR' for item in state.problems)
        warnings = sum(item.severity == 'WARNING' for item in state.problems)
        _draw_text(self.layout, context,
                   f"{len(state.problems)} findings: {errors} errors, {warnings} warnings")
        self.layout.prop(state, "severity", text="")
        self.layout.template_list(
            "LIST_UL_sb_errors", "", state, "problems", state, "selected", rows=6)
        _draw_text(self.layout, context, "Results are a snapshot. Recheck after editing.")
        if not 0 <= state.selected < len(state.problems):
            return
        active = state.problems[state.selected]
        if state.severity != 'ALL' and active.severity != state.severity:
            return
        box = self.layout.box()
        box.label(text=f"{active.category} / {active.severity.title()}",
                  icon=_SEVERITY_ICONS[active.severity])
        _draw_text(box, context, active.name)
        _draw_text(box, context, active.message)
        box.separator()
        _draw_text(box, context, active.solution)
        box.operator("object.sb_locate_blend_problem", icon='RESTRICT_SELECT_OFF')


class SB_LocateBlendProblem(bpy.types.Operator):
    """Locate the source without changing modes or unhiding objects"""
    bl_idname = "object.sb_locate_blend_problem"
    bl_label = "Locate Source"

    @classmethod
    def poll(cls, context):
        state = context.window_manager.sb_check_blend
        return 0 <= state.selected < len(state.problems)

    def execute(self, context):
        state = context.window_manager.sb_check_blend
        index = state.problems[state.selected].result_index
        if not 0 <= index < len(_problems):
            self.report({'WARNING'}, "Results are no longer available. Run Check Blend again.")
            return {'CANCELLED'}
        success, message = navigate_to_problem(_problems[index], context)
        self.report({'INFO'} if success else {'WARNING'}, message)
        return {'FINISHED'} if success else {'CANCELLED'}


class SB_ClearBlendResults(bpy.types.Operator):
    """Discard this audit's temporary findings"""
    bl_idname = "object.sb_clear_blend_results"
    bl_label = "Clear Results"

    def execute(self, _context):
        clear_results()
        return {'FINISHED'}


class SB_CheckBlend(bpy.types.Operator):
    """Audit materials, UVs, names, libraries and collection membership in the whole file"""
    bl_idname = "object.sb_check_blend"
    bl_label = "Check Blend"

    def execute(self, context):
        clear_results()
        problems = []
        for check in ALL_CHECKS:
            problems.extend(check())
        problems.sort(key=lambda item: (
            _SEVERITY_ORDER[item.severity], item.category, item.name, item.message))
        _problems.extend(problems)
        state = context.window_manager.sb_check_blend
        state.severity = 'ALL'
        for index, problem in enumerate(problems):
            item = state.problems.add()
            item.name = problem.name
            item.message = problem.message
            item.solution = problem.solution
            item.icon = problem.icon
            item.category = problem.category
            item.severity = problem.severity
            item.result_index = index
            print(f"[Check Blend/{problem.severity}/{problem.category}] "
                  f"{problem.path}: {problem.message} {problem.solution}")
        state.selected = 0 if problems else -1
        state.has_run = True
        self.report({'INFO'}, f"Check Blend: {len(problems)} findings. See the STUNTBOOST sidebar.")
        return {'FINISHED'}

    @staticmethod
    def bpl_load():
        for cls in _CLASSES:
            bpy.utils.register_class(cls)
        bpy.types.WindowManager.sb_check_blend = bpy.props.PointerProperty(
            type=CheckBlendState, options={'SKIP_SAVE'})
        for handlers in (bpy.app.handlers.load_post, bpy.app.handlers.undo_post, bpy.app.handlers.redo_post):
            handlers.append(clear_results)

    @staticmethod
    def bpl_unload():
        for handlers in (bpy.app.handlers.load_post, bpy.app.handlers.undo_post, bpy.app.handlers.redo_post):
            handlers.remove(clear_results)
        clear_results()
        del bpy.types.WindowManager.sb_check_blend
        for cls in reversed(_CLASSES):
            bpy.utils.unregister_class(cls)


_CLASSES = (
    ProblemListItem, CheckBlendState, LIST_UL_sb_errors, SB_LocateBlendProblem,
    SB_ClearBlendResults, SB_CheckBlend, SB_CheckBlendResultPanel)
