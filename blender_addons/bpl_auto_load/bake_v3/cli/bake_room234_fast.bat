@echo off

echo "Hit enter twice!"

REM set FASTBLENDS=../../../../SE/Content/Models/New/Level_GrindTut.blend,../../../../SE/Content/Models/New/Level_TimeTravel.blend,../../../../SE/Content/Models/New/Level_GrindPark.blend,../../../../SE/Content/Models/New/Level_IceSlide.blend,../../../../SE/Content/Models/New/Level_IceBasics.blend,../../../../SE/Content/Models/New/Level_FullPipe.blend

REM blender -b -P "./sbe_cli_bake.py" -- --setting "FAST" -p "%FASTBLENDS%"

blender -b -P "./sbe_cli_bake.py" -- --setting "FAST" -p "../../../../SE/Content/Models/New/Level_*.blend" -y
REM --exclude "%FASTBLENDS%"

set /p DUMMY=Hit ENTER to continue...