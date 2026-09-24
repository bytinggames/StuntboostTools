@echo off

blender -b -P "./sbe_cli_bake.py" -- --setting "RELEASE" -p "../../../../SE/Content/Models/New/Level_*.blend" -y
blender -b -P "./sbe_cli_bake.py" -- --setting "RELEASE" -p "../../../../SE/Content/Models/Sascha/Level_*.blend" -y

set /p DUMMY=Hit ENTER to continue...