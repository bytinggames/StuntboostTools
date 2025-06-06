"""
Basic git lfs integration.
Adds a new button in the top bar showing the LFS locking status and allows
locking and unlocking of the current file as well a unlocking for all
committed/unchanged files.
"""

import sys
import os
import subprocess
import json
import enum

# pylint: disable=import-error
import bpy
from bpy.app.handlers import persistent
# pylint: enable=import-error

CHECK_INTERVAL_SEC = 60 * 1
"""Don't check too often as this blocks the ui and will cause a little stutter"""


SB_LOCK_OPERATOR = "wm.sb_lfs_lock"
SB_UNLOCK_OPERATOR = "wm.sb_lfs_unlock"
SB_UNLOCK_ALL_OPERATOR = "wm.sb_lfs_unlock_all"


SB_RED_ICON_NAME = ""
SB_GREEN_ICON_NAME = ""

if bpy.app.version[0] <= 4 and bpy.app.version[1] <= 3:
    SB_RED_ICON_NAME = 'SEQUENCE_COLOR_01'
    SB_GREEN_ICON_NAME = 'SEQUENCE_COLOR_04'
else:
    SB_RED_ICON_NAME = 'COLORSET_01_VEC'
    SB_GREEN_ICON_NAME = 'COLORSET_03_VEC'


def message_box(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, _context: bpy.types.Context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

class LockStatus(enum.Enum):
    NO_LOCK = 1
    LOCKED_BY_US = 2
    LOCKED_BY_OTHER = 3
    INVALID = 4
    NOT_TRACKED = 5

class GitStatus(enum.Enum):
    UNCHANGED = 1
    CHANGED = 2
    UNKNOWN = 3

CURRENT_STATE = LockStatus.NOT_TRACKED

def ignore_file() -> bool:
    """true for STUNTBOOST specific files which don't need locking"""
    # TODO maybe rely on .gitignore instead, so this is more general
    return bpy.data.filepath and bpy.data.filepath.find(".export") != -1


GIT_ROOT = None
def get_git_root(file: str) -> str:
    global GIT_ROOT
    if GIT_ROOT and file.find(GIT_ROOT):
        return GIT_ROOT
    path = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=os.path.dirname(file))
    path = path.decode(sys.stdout.encoding).strip()
    GIT_ROOT = path
    return path


class SB_LocksNotTrackedTopBarMenu(bpy.types.Menu):
    bl_idname = "SB_MT_locks_not_tracked_topbar_menu"
    bl_label = "LFS: Not Tracked"
    bpl_auto_load = True
    def draw(self, _context: bpy.types.Context) -> None:
        pass

class SB_LocksNotLockTopBarMenu(bpy.types.Menu):
    bl_idname = "SB_MT_locks_no_lock_topbar_menu"
    bl_label = "LFS: NOT LOCKED"
    bpl_auto_load = True
    def draw(self, _context: bpy.types.Context) -> None:
        self.layout.operator(SB_LOCK_OPERATOR)
        self.layout.operator(SB_UNLOCK_ALL_OPERATOR)

class SB_LocksLockedTopBarMenu(bpy.types.Menu):
    bl_idname = "SB_MT_locks_locked_topbar_menu"
    bl_label = "LFS: LOCKED BY OTHER!"
    bpl_auto_load = True
    def draw(self, _context: bpy.types.Context) -> None:
        self.layout.operator(SB_UNLOCK_ALL_OPERATOR)


class SB_LocksOwnLockTopBarMenu(bpy.types.Menu):
    bl_idname = "SB_MT_locks_own_lock_topbar_menu"
    bl_label = "LFS: LOCKED BY US"
    bpl_auto_load = True
    def draw(self, _context: bpy.types.Context) -> None:
        self.layout.operator(SB_UNLOCK_OPERATOR)
        self.layout.operator(SB_UNLOCK_ALL_OPERATOR)

class SB_LocksInvalidTopBarMenu(bpy.types.Menu):
    bl_idname = "SB_MT_locks_inclaid_lock_topbar_menu"
    bl_label = "LFS: ERROR, check manually"
    bpl_auto_load = True
    def draw(self, _context: bpy.types.Context) -> None:
        pass

def sb_locks_top_bar_menu_draw(self: bpy.types.Menu, _context: bpy.types.Context) -> None:
    if ignore_file():
        return

    match CURRENT_STATE:
        case LockStatus.NO_LOCK:
            self.layout.menu(SB_LocksNotLockTopBarMenu.bl_idname)
            # this will become STRIP_COLOR_01 in blender 4.4
            self.layout.label(text="", icon=SB_RED_ICON_NAME)
        case LockStatus.LOCKED_BY_OTHER:
            self.layout.menu(SB_LocksLockedTopBarMenu.bl_idname)
            self.layout.label(text="", icon=SB_RED_ICON_NAME)
        case LockStatus.LOCKED_BY_US:
            self.layout.menu(SB_LocksOwnLockTopBarMenu.bl_idname)
            self.layout.label(text="", icon=SB_GREEN_ICON_NAME)
        case LockStatus.INVALID:
            self.layout.menu(SB_LocksInvalidTopBarMenu.bl_idname)
            self.layout.label(text="", icon=SB_RED_ICON_NAME)
        case LockStatus.NOT_TRACKED:
            self.layout.menu(SB_LocksNotTrackedTopBarMenu.bl_idname)



def git_status(file: str) -> GitStatus:
    result = subprocess.check_output(['git', 'status', '--porcelain=v1', file], cwd=get_git_root(file))
    if len(result) == 0:
        return GitStatus.UNCHANGED
    result = result.decode(sys.stdout.encoding)
    if result[1] == 'M':
        return GitStatus.CHANGED
    return GitStatus.UNKNOWN

def is_up_to_date(file: str) -> bool:
    # branch = subprocess.check_output(['git' 'rev-parse' '--abbrev-ref' 'HEAD'], cwd=os.path.dirname(file))
    # branch = result.decode(sys.stdout.encoding)
    # subprocess.check_output(['git', 'remote', 'update'], cwd=os.path.dirname(file))
    subprocess.check_output(['git', 'fetch'], cwd=get_git_root(file))

    # bogus path so no files are returned, only how many commits remote is ahead
    result = subprocess.check_output(['git', 'status', '-sb', '-uno', '.asdsdasd'], cwd=get_git_root(file))
    result = result.decode(sys.stdout.encoding)
    return result.find("behind") == -1

def run_lfs_command(command: str, file: str) -> None:
    command_array = ['git', 'lfs', command, '--json', file]
    try:
        subprocess.check_output(command_array, cwd=get_git_root(file))
    except Exception as e:
        print(f"{e}")


def get_locks_to_free(file: str) -> list[str]:
    file = file.replace('\\', '/')
    result = subprocess.check_output(['git', 'lfs', 'locks', '--json', '--verify', file], cwd=get_git_root(file))
    result = json.loads(result)

    status = subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=get_git_root(file))
    status = status.decode(sys.stdout.encoding)

    ours = []
    for i in result['ours']:
        path = i['path']
        if path.find(".blend") == -1:
            continue
        # make sure the file doesn't show up in git status as changed/staged
        if status.find(path) == -1:
            ours.append(os.path.join(get_git_root(file), path))
    return ours



def update_lock_status(file: str) -> None:
    global CURRENT_STATE
    if not os.path.exists(file):
        CURRENT_STATE = LockStatus.NOT_TRACKED
        return

    try:
        git_status(file)
    except:
        # don't run without git repo
        CURRENT_STATE = LockStatus.NOT_TRACKED
        return

    file = file.replace('\\', '/')
    result = subprocess.check_output(['git', 'lfs', 'locks', '--json', '--verify', file], cwd=get_git_root(file))
    result = json.loads(result)

    theirs = []
    for i in result['theirs']:
        path = i['path']
        if file.find(path) != -1:
            theirs.append(i)

    ours = []
    for i in result['ours']:
        path = i['path']
        if file.find(path) != -1:
            ours.append(i)
    
    if 0 < len(theirs):
        if not os.access(file, os.W_OK):
            CURRENT_STATE = LockStatus.LOCKED_BY_OTHER
            return
        print("File is not readonly, but some else owns the lock, something is wrong...")
        CURRENT_STATE = LockStatus.INVALID
        return
    if 0 < len(ours):
        if os.access(file, os.W_OK):
            CURRENT_STATE = LockStatus.LOCKED_BY_US
            return
        print("We hold the lock but can't edit the file, something is wrong...")
        CURRENT_STATE = LockStatus.INVALID
        return
    CURRENT_STATE = LockStatus.NO_LOCK


class SB_LockLfsFile(bpy.types.Operator):
    """Tries to acquire the git LFS lock for the current file"""
    bl_idname = SB_LOCK_OPERATOR
    bl_label = "Lock the current file in git LFS"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        if not bpy.data.filepath:
            return {'FINISHED'} # new unsaved file
        if ignore_file():
            raise Exception("We don't allow locking export files since they aren't in the repo.")
        if not is_up_to_date(bpy.data.filepath):
            raise Exception("Repo not up to date, run git pull first.")
        run_lfs_command('lock', bpy.data.filepath)
        update_lock_status(bpy.data.filepath)
        if CURRENT_STATE == LockStatus.LOCKED_BY_US:
            return {'FINISHED'}
        if CURRENT_STATE == LockStatus.LOCKED_BY_OTHER:
            raise Exception("File already locked.")
        if CURRENT_STATE == LockStatus.NO_LOCK:
            raise Exception("Failed to acquire lock.")
        if CURRENT_STATE == LockStatus.INVALID:
            raise Exception("Failed to acquire lock.")
        return {'FINISHED'}


class SB_UnlockLfsFile(bpy.types.Operator):
    """Releases the git LFS lock for the current file"""
    bl_idname = SB_UNLOCK_OPERATOR
    bl_label = "Unlock the current file in git LFS"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        if not bpy.data.filepath:
            return {'FINISHED'} # new unsaved file
        status = git_status(bpy.data.filepath)
        if status != GitStatus.UNCHANGED:
            raise Exception("File is not unchanged, commit and push before releasing lock.")
        run_lfs_command('unlock', bpy.data.filepath)
        update_lock_status(bpy.data.filepath)
        if CURRENT_STATE == LockStatus.NO_LOCK:
            return {'FINISHED'}
        if CURRENT_STATE == LockStatus.LOCKED_BY_OTHER:
            raise Exception("File already locked.")
        if CURRENT_STATE == LockStatus.LOCKED_BY_US:
            raise Exception("Failed to release lock.")
        if CURRENT_STATE == LockStatus.INVALID:
            raise Exception("Failed to release lock. unknown status")
        return {'FINISHED'}

class SB_UnlockAllLfsFiles(bpy.types.Operator):
    """Releases the git LFS lock on all files"""
    bl_idname = SB_UNLOCK_ALL_OPERATOR
    bl_label = "Unlock all files in git LFS"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        if not bpy.data.filepath:
            return {'FINISHED'} # new unsaved file
        if not is_up_to_date(bpy.data.filepath):
            raise Exception("Repo not up to date, run git pull first.")
        locked = get_locks_to_free(bpy.data.filepath)
        for i in locked:
            run_lfs_command('unlock', i)
            print(f"Unlocked {i}")
        update_lock_status(bpy.data.filepath)
        msg = f"Done unlocking {len(locked)} file(s)"
        message_box(msg)
        print(msg)
        return {'FINISHED'}


class SB_FileLocking:
    @staticmethod
    @persistent
    def load_post_handler(blend_path: str) -> None:
        update_lock_status(blend_path)


    @staticmethod
    @persistent
    def poll_file_locked():
        if not bpy.data.filepath:
            return CHECK_INTERVAL_SEC # new unsaved file
        SB_FileLocking.load_post_handler(bpy.data.filepath)
        return CHECK_INTERVAL_SEC


    @staticmethod
    def bpl_load():
        if bpy.app.background:
            return
        bpy.app.handlers.load_post.append(SB_FileLocking.load_post_handler)
        bpy.app.timers.register(
            function=SB_FileLocking.poll_file_locked,
            first_interval=CHECK_INTERVAL_SEC, persistent=True)
        
        bpy.types.TOPBAR_MT_editor_menus.append(sb_locks_top_bar_menu_draw)

    @staticmethod
    def bpl_unload():
        if bpy.app.background:
            return
        bpy.app.handlers.load_post.remove(SB_FileLocking.load_post_handler)
        bpy.app.timers.unregister(SB_FileLocking.poll_file_locked)
        
        bpy.types.TOPBAR_MT_editor_menus.remove(sb_locks_top_bar_menu_draw)
