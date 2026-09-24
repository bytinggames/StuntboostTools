"""
This should allow for baking multiple levels from the command line.
A example on how to call this script from the CLI.
All script parameters are beyond the double dash (--)
`blender -b -P ./sbe_cli_bake.py -- --help`
"""

import sys
import glob
import datetime
import time
import signal
import argparse

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_util import store_temp, execute_by_idname, get_level_name, get_level_order
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_custom_properties import SBE_TEMP_CLI_BAKE_PROP
from bake_v3.sbe_operator_ids import (
    SBE_OP_CLEAR_LOGS, SBE_OP_SAVE_LOGS,
    SBE_OP_BUILD_LEVEL, SBE_OP_INSPECT_LEVEL
)
from bake_v3.properties.sbe_blend_props import SBE_BlendProperties
from bake_v3.sbe_sound import success_sound

parser = argparse.ArgumentParser(
    prog="sbe_cli_bake",
    description="This will allow command line batch baking of STUNTBOOST levels",
    epilog="See source for more info.")

parser.add_argument('-p', '--path',
    help=
"""File path passed to glob. E.g. "../SE/Content/Models/Level_0_*.blend"
or a list separated by "," like "Level_1.blend,Level_2.blend,*_test.blend" """)

parser.add_argument('-e', '--exclude',
    help=
"""File path passed to glob. E.g. "../SE/Content/Models/Level_0_Exclude.blend"
or a list separated by "," like "Level_1.blend,Level_2.blend,*_test.blend" """)

parser.add_argument('-r', '--recursive', action='store_true',
    help="Whether to glob files recursively")

parser.add_argument('-y', '--yes', action='store_true',
    help="Bake will ask for confirmation when using * wildcards, this will skip the prompt and bake directly.")

parser.add_argument('-i', '--inspect', action='store_true',
    help="Will run the inspection sequence instead of a bake.")

parser.add_argument('-s', '--setting', default='RELEASE',
    help='Enum name of the bake preset. Either "FAST" or "RELEASE" (default).')

args = parser.parse_args(args=sys.argv[sys.argv.index("--") + 1:])

def signal_handler(_sig, _frame):
    """Should allow for ctrl+c"""
    print("Stopping bake")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

start_time = time.time()


valid_blends = set()
for i in args.path.split(","):
    i: str = i.strip()
    globbed = glob.glob(i, recursive=args.recursive)
    for j in globbed:
        if j.find(".blend") == -1:
            continue
        if j.find(".blend1") != -1:
            continue
        # TODO regex matching
        if j.find(".blend2") != -1:
            continue
        if j.find("Empty.blend") != -1 and args.path.find("Empty.blend") == -1:
            # we allow explicit baking of the empty scene for testing
            # otherwise they will be skipped
            continue
        if j.find("export.blend") != -1:
            continue
        j = j.replace('\\', '/')
        valid_blends.add(j)

valid_blends = list(valid_blends)

if args.exclude:
    for i in args.exclude.split(","):
        i: str = i.strip()
        globbed = glob.glob(i, recursive=args.recursive)
        for j in globbed:
            j = j.replace('\\', '/')
            if j in valid_blends:
                valid_blends.remove(j)

valid_blends.sort()

# Sort all known levels according to the level order.
for i in reversed(get_level_order()):
    for j in valid_blends[:]:
        if i == get_level_name(j):
            valid_blends.remove(j)
            valid_blends.insert(0, j)

print(f"{len(valid_blends)} *.blend(s) queued for export:")
if not valid_blends:
    print("Exiting...")
    sys.exit(0)

for i in valid_blends:
    print(f"\t{i}")

if not args.yes and (1 < len(valid_blends) or args.path.find("*") != -1):
    # when using wild cards, or multiple blends ask before baking
    input("Press Enter to start export...")

errors = []

for i, blend in enumerate(valid_blends):
    SBE_Logger.SBE_EXTRA_TEXT = f"{i + 1} out of {len(valid_blends)} "
    try:
        bpy.ops.wm.open_mainfile(filepath=blend)
    except Exception as e:
        errors.append((blend, e))
        continue

    # Needs to be set after loading each blend, will change behavior slightly
    store_temp(SBE_TEMP_CLI_BAKE_PROP, True)

    # Set the desired bake preset
    blend_props: SBE_BlendProperties = SBE_BlendProperties.get()
    blend_props.bake_preset = args.setting

    try:
        if args.inspect:
            execute_by_idname(SBE_OP_INSPECT_LEVEL)
        else:
            execute_by_idname(SBE_OP_BUILD_LEVEL)
    except Exception as e:
        errors.append((blend, e))
        execute_by_idname(SBE_OP_SAVE_LOGS)
        execute_by_idname(SBE_OP_CLEAR_LOGS) # not needed?


delta = datetime.timedelta(seconds=time.time() - start_time)
print("")
print("FULL BAKE DONE")
print(f"Time {delta}")
print(f"Files {len(valid_blends)} Avg. Time {delta/len(valid_blends)}")

print(f"Errors: {len(errors)}")
for i in errors:
    print(f"{i[0]} failed with")
    print(str(i[1]))

print("")
success_sound()
