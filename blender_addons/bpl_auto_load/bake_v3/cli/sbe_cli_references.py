"""
Help with managing referenced data block across all blend files in the repo
`blender -b -P ./sbe_cli_references.py -- --help`
"""

import os
import sys
import glob
import dataclasses
import datetime
import time
import argparse
import pathlib

# pylint: disable=import-error
import bpy
import stuntboost_bpl_runtime
# pylint: enable=import-error

parser = argparse.ArgumentParser(
    prog="sbe_cli_references",
    description="Manage or check references",
    epilog="See source for more info.")

parser.add_argument('-a', '--action', default='missing',
    help="""
    "list" to list all references,
    "list_blend" to only show which blends are referenced,
    "missing" to list all missing references, "remap" to remap references also needs "-s" and "",
    "move" to move files """)

parser.add_argument('-o', '--output',
    help='When set, will output result to file, recommended with "-a list"')

parser.add_argument('-d', '--dry_run', action='store_true',
    help='Will not save any changes to the blends and only report for "-a remap"')


parser.add_argument('-from', '--move_from',
    help='Input glob patter of files to move')

parser.add_argument('-to', '--move_to',
    help='Output folder, or single full path if renaming just one file')

parser.add_argument('-rbt', '--remap_block_type',
    help='Name of the member in bpy.data.* e.g. "objects" or "collections" when using "-a remap"')

parser.add_argument('-rnf', '--remap_new_file',
    help='Path to new *.blend file blend when using "-a remap"')
parser.add_argument('-rnb', '--remap_new_block',
    help='Name of the new data block in blend in "-remap_new_file"')

parser.add_argument('-rof', '--remap_old_file', default='',
    help='For safety "-a remap" can check whether the data block to be replaced actually references this blend when supplied')
parser.add_argument('-rob', '--remap_old_block',
    help='The old block to be remapped to --new_block when using "-a remap"')

args = parser.parse_args(args=sys.argv[sys.argv.index("--") + 1:])


def output(content: str) -> None:
    if args.output:
        with open(args.output, mode="w", encoding="utf-8") as f:
            f.write(content)
    else:
        if os.name == 'nt':
            os.system("cls")
        else:
            os.system("clear")
        print(content)


def gather_blends() -> list[str]:
    repo = stuntboost_bpl_runtime.get_repo_path()
    # no idea if the glob pattern is redundant
    blends = glob.glob(os.path.join(repo, "**", "*.blend"), recursive=True)
    filtered_blends = []
    for i in blends:
        if i.find(".blend1") != -1:
            continue
        if i.find("export.blend") != -1:
            continue
        filtered_blends.append(i)
    return filtered_blends


def gather_block_list_names() -> list[str]:
    """we only store the names not the collection objects because this crashes later"""
    result = []
    for i in dir(bpy.data):
        if i.find("rna") != -1:
            continue
        if i.find("id_") != -1:
            continue
        data = getattr(bpy.data, i)
        if not hasattr(data, "items"):
            continue
        result.append(i)
    return result


@dataclasses.dataclass
class BlockInfo():
    path: str
    """Internal blend path like "bpy.data.objects['name']" """
    library: str
    """Absolute file path to library blend"""

class BlendInfo():
    path: str
    """Absolute file path to blend the blocks belong to"""
    errors: list[str]
    blocks: list[BlockInfo]


def check_missing_in_current_blend(block_list_names: list[str], blend_path: str) -> BlendInfo:
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    blend = BlendInfo()
    blend.path = blend_path
    blend.blocks = []
    for block_list_name in block_list_names:
        for i in getattr(bpy.data, block_list_name):
            block: bpy.types.ID = i
            if not block.is_missing:
                continue
            if block.library:
                path = bpy.path.abspath(block.library.filepath)
                blend.blocks.append(BlockInfo(path=repr(block), library=path))
            else:
                blend.blocks.append(BlockInfo(path=repr(block), library=""))
    return blend


def check_missing_all():
    block_list_names = gather_block_list_names()
    blends: list[BlendInfo] = []
    for i in gather_blends():
        blends.append(check_missing_in_current_blend(block_list_names, i))

    result = "Missing blocks:"

    for i in blends:
        if not i.blocks:
            continue
        result += f"\n\n{i.path}"
        for j in i.blocks:
            result += f"\n\t{j.path} {j.library}"

    output(result)


def list_in_current_blend(block_list_names: list[str], blend_path: str) -> BlendInfo:
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    blend = BlendInfo()
    blend.path = blend_path
    blend.blocks = []
    for block_list_name in block_list_names:
        block_list = getattr(bpy.data, block_list_name)
        for i in block_list:
            block: bpy.types.ID = i
            if block.library:
                path = bpy.path.abspath(block.library.filepath)
                blend.blocks.append(BlockInfo(path=repr(block), library=path))
    return blend


def list_all():
    block_list_names = gather_block_list_names()
    blends: list[BlendInfo] = []
    for i in gather_blends():
        blends.append(list_in_current_blend(block_list_names, i))

    result = "All linked blocks:"
    for i in blends:
        if not i.blocks:
            continue
        result += f"\n\n{i.path}"
        for j in i.blocks:
            result += f"\n\t{j.path} {j.library}"

    output(result)

def list_blends(silent=False) -> list[BlendInfo]:
    blends: list[BlendInfo] = []
    for i in gather_blends():
        bpy.ops.wm.open_mainfile(filepath=i)
        blend = BlendInfo()
        blend.path = i
        blend.blocks = []
        for j in bpy.data.libraries:
            lib: bpy.types.Library = j
            path = bpy.path.abspath(lib.filepath)
            blend.blocks.append(BlockInfo(path="", library=path))
        blends.append(blend)

    if silent:
        return blends

    result = "All linked blends:"
    for i in blends:
        if not i.blocks:
            continue
        result += f"\n\n{i.path}"
        for j in i.blocks:
            result += f"\n\t{j.path} {j.library}"
    output(result)
    return blends


def remap_in_current_blend(
        bpy_data_member: str,
        old_block: BlockInfo, new_block: BlockInfo,
        blend_path: str) -> BlendInfo:

    bpy.ops.wm.open_mainfile(filepath=blend_path)
    blend = BlendInfo()
    blend.errors = []
    blend.path = blend_path
    blend.blocks = []
    block_list: map = getattr(bpy.data, bpy_data_member)

    old: bpy.types.ID = None
    for i in block_list:
        id_block: bpy.types.ID = i
        if id_block.original.name != old_block.path:
            continue
        if not id_block.library:
            blend.errors.append(f"Old Block {repr(id_block)} is not a library!")
            return blend
        path = bpy.path.abspath(id_block.library.filepath)
        if path.find(old_block.library) == -1:
            blend.errors.append(f"Old Block {repr(id_block)} points to wrong library {path}!")
            return blend
        old = id_block

    if not old:
        # not present, nothing to do
        return blend

    new: bpy.types.ID = None
    for i in block_list:
        id_block: bpy.types.ID = i
        if id_block.original.name != new_block.path:
            continue
        if not id_block.library:
            blend.errors.append(f"New Block already present {repr(id_block)} but is not a library!")
            return blend
        path = bpy.path.abspath(id_block.library.filepath)
        if path.find(old_block.library) == -1:
            blend.errors.append(f"New Block {repr(id_block)} already present but points to wrong library {path}!")
            return blend
        new = id_block

    if new is None:
        # new block doesn't already exist so we need to link it in
        props_blend_path = bpy.path.abspath(new_block.new_block.library)
        if not os.path.isfile(props_blend_path):
            blend.errors.append(f"Could not find {props_blend_path}")
            return blend

        with bpy.data.libraries.load(filepath=props_blend_path, link=True, relative=True) as (data_from, data_to):
            source_block_list: list[str] = getattr(data_from, bpy_data_member)
            if new_block.path not in source_block_list:
                blend.errors.append(f"Could not append {new_block.path} from {props_blend_path}")
                return blend

            target_block_list: list[str] = getattr(data_to, bpy_data_member)
            target_block_list.append(new_block.path)
        # string gets replaced by newly linked data block after leaving the with block
        new = getattr(data_to, bpy_data_member)[0]
        assert new, "Logic error, linking failed"
        assert new.library, "Logic error, linking, should mean linking"
        assert new.library.filepath.find(new_block.library) != -1, "Logic error, should point to relevant lib"

    blend.blocks.append(BlockInfo(path=repr(old), library=old.library.filepath))
    old.user_remap(new)
    bpy.data.orphans_purge()

    # if not args.dry_run:
    #     bpy.ops.wm.save_as_mainfile()


def remap_all(bpy_data_member: str, old_block: BlockInfo, new_block: BlockInfo):
    blends: list[BlendInfo] = []

    for i in gather_blends():
        blends.extend(remap_in_current_blend(
            bpy_data_member=bpy_data_member,
            old_block=old_block, new_block=new_block, blend_path=i))
    result = ""
    for i in blends:
        if not i.blocks:
            continue
        result += f"\n\nReplaced in {i.path}"
        for j in i.blocks:
            result += f"\n\t{j.path} {j.library}"

    for i in blends:
        if not i.errors:
            continue
        result += f"\n\nERRORS in {i.path}"
        for j in i.errors:
            result += f"\n\t{j}"

    output(result)


def move_blends():
    references = list_blends(silent=True)
    blends = glob.glob(args.move_from, recursive=True)
    needs_ref_update = []
    print("Moving these files:")
    for i in blends:
        print(f"\t{i}")
        for j in references:
            for k in j.blocks:
                if k.library == i:
                    print(f"\t\tUsed in {j.path}")
                    needs_ref_update.append(j.path)
    if needs_ref_update:
        print("ERROR, moved files are referenced and path remapping not implemented yet")
        sys.exit(1)

    out_path = pathlib.Path(args.move_to)

    if out_path.suffix == ".blend":
        if len(blends) != 1:
            print("Can't rename multiple files")
            sys.exit(1)
    input("Press Enter to continue...")
    for i in blends:
        bpy.ops.wm.open_mainfile(filepath=i)
        if not args.dry_run:
            new_path = os.path.join(out_path, os.path.basename(i))
            bpy.ops.wm.save_as_mainfile(filepath=new_path)

    # TODO remapping
    # for i in needs_ref_update:
    #     bpy.ops.wm.open_mainfile(filepath=i)
    #     for j in bpy.data.libraries:
    #         lib: bpy.types.Library = j
    #         if lib.filepath

    if not args.dry_run:
        for i in blends:
            os.unlink(i)

    


start_time = time.time()

if args.action == 'list':
    list_all()
elif args.action == 'remap':
    remap_all(
        bpy_data_member=args.remap_block_type,
        old_block=BlockInfo(library=args.remap_new_file, path=args.remap_old_block),
        new_block=BlockInfo(library=args.remap_new_file, path=args.remap_new_block))
elif args.action == 'missing':
    check_missing_all()
elif args.action == 'list_blend':
    list_blends()
elif args.action == 'move':
    move_blends()
else:
    print(f"\nError, invalid action {args.action}")
    sys.exit(1)

delta = datetime.timedelta(seconds=time.time() - start_time)
print(f"\nTook: {delta}s")
