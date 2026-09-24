# TODO this needs testing

import os
import shutil
import time

# pylint: disable=import-error
import bpy
from bpy.app.handlers import persistent
# pylint: enable=import-error



class SBE_BackUpMover(bpy.types.Operator):
    """
        Move the blend1-9 backup files to a subfolder
        By Jonathan Stroem GPLv3
    """
    bl_idname = "wm.sb_move_backups"
    bl_label = "Move the blend1-9 backup files"

    def execute(self, _context: bpy.types.Context):
        backup_folder_name = "BlendBackup" # backup files will end up here
        extension = ".blend"
        backup_amount = int(bpy.context.preferences.filepaths.save_version) # can be changed in the user preferences

        current_full_path =  bpy.data.filepath
        current_folder =  os.path.dirname(current_full_path)
        name =  bpy.path.display_name_from_filepath(bpy.data.filepath)
        full_name = name + extension
        backup_folder = os.path.join(current_folder, backup_folder_name)

        all_files = os.listdir(current_folder)

        if backup_folder not in all_files:
            os.mkdir(backup_folder)
        
        #Get current save files from the backup directory.
        backup_files = []
        for f in all_files:
            for c in range(1, backup_amount + 1):
                if os.path.isfile(os.path.join(backup_folder, full_name + str(c))):
                    backup_files.append(f)

        #All this is moving the correct file.
        if len(backup_files) < 1: #If no files, then no need to check.
            if os.path.isfile(current_full_path + "1"):
                shutil.move(current_full_path + "1", os.path.join(backup_folder, full_name + "1"))
        else: #If the max backup amount has been reached, then check for the oldest file and overwrite that one.
            if backup_amount <= len(backup_files):
                replaceFile = {"modified_date":None, "fullname":""}
                for f in backup_files:
                    stats = os.stat(os.path.join(backup_folder, f)) #Get attributes from a file.
                    if replace_full_name == "": #This will happen only the first time.
                        replace_full_name = f
                        replace_modified_date = time.asctime(time.localtime(stats[ST_MTIME]))
                    else: # Is the previous file older or newer? If it's older, then you'd want to overwrite that one instead. Go through all backup-files.
                        temp_modified = time.asctime(time.localtime(stats[ST_MTIME]))
                        if replace_modified_date > temp_modified :
                            replace_full_name = f
                            replace_modified_date = temp_modified

                #When the loop is finished, the oldest file has been found, and will be overwritten.
                shutil.move(current_full_path + "1", os.path.join(backup_folder, replace_full_name))
            else : #If the max backup amount hasn't been reached, and the folder isn't empty.
                #Then check for the next number, and then just move the file over with the correct number.
                replaceFile = "" #Location.
                for f in backup_files :
                    for c in range(1, int(backup_amount) + 1) :
                        if not os.path.isfile(os.path.join(backup_folder, full_name + str(c))):
                            shutil.move(current_full_path + "1", os.path.join(backup_folder, full_name + str(c)))
                            replaceFile = f
                            break
                    if replaceFile != "" : #File to replace has been found, break out.
                        break

    @staticmethod
    @persistent
    def handler(_scene: bpy.types.Scene):
        bpy.ops.wm.sb_move_backups()

    # TODO test this thoroughly before using since I've moved it over to os.path.join
    # TODO don't want any lost data due to it misbehaving
    # @staticmethod
    # def bpl_load():
    #     bpy.utils.register_class(BackUpMover)
    #     bpy.app.handlers.save_post.append(BackUpMover.handler)

    # @staticmethod
    # def bpl_unload():
    #     bpy.app.handlers.save_post.remove(BackUpMover.handler)
    #     bpy.utils.unregister_class(BackUpMover)
