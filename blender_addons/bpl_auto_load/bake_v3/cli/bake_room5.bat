@echo off

blender -b -P "./sbe_cli_bake.py" -- --setting "RELEASE" -p "../../../../SE/Content/Models/Bonus/Level_*.blend" -y

set /p DUMMY=Hit ENTER to continue...