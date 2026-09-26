r"""
CLI Blender reference helper
THIS ISN'T TESTED VERY WELL.
Keep backups of your blends!


blender \
    --background --factory-startup --disable-autoexec --python-exit-code 2 \
    --python ./sbe_cli_references.py \
    -- --directory /path/to/blends" 

Run through Blender, not Python directly. Tool options after "--" (use "--help" for help).
--directory scans all .blend files recursively, including exports, not blend1-10.
Omit it to scan the configured game link's repository
root or shipped StuntboostTools folder, with legacy export exclusions.

Actions (--action):
  missing     Default, read-only. Reports missing libraries, linked datablocks,
              and Blender-registered external files.
              Resolves library-relative paths and skips packed assets.
              Skips after unreadable files.
  list        Read-only inventory of linked datablocks and their library paths.
  list_blend  Read-only inventory of linked libraries per scanned blend.
  remap       Replaces direct linked datablocks and saves affected files.
              Use --remap_old_file to differentiate data blocks with name collisions.
              Paths are exact (relative to the CLI working directory).
  move        Moves .blend files/ordinary images and rewrites library/image
              datablock paths in scanned blends. Preserves relative paths.
              --move_from is a glob
              --move_to is an existing directory or a new
              same-extension filename for one source. No overwrites/collisions.
              Blend sources and linked-image owners must be in the scan.
              Rejects cycles, other reference types, and image moves from folders
              containing image-sequence references. Packed data is left alone.
              Preview: --action move --directory "C:\assets" --move_from "C:\assets\old.png"
                       --move_to "C:\assets\textures\new.png" --dry_run

--output writes a UTF-8 report. Missing/move also print it to stdout.
--dry_run previews remap/move without modifying assets, move skips confirmation.
Close blends and keep backups. Sources are deleted only after all saves succeed.
Batches are not transactional: failures may leave saved dependents/new destinations.
Exit codes: 0 success, 1 missing references, 2 invalid/incomplete operation.
Keep --python-exit-code 2. The launch flags disable add-ons/automatic scripts.
"""

import os
import sys
import glob
import dataclasses
import datetime
import time
import argparse
import pathlib
import shutil
from graphlib import CycleError, TopologicalSorter
from collections import Counter
from contextlib import contextmanager, nullcontext

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

parser = argparse.ArgumentParser(
    prog="sbe_cli_references",
    description="Manage Blender references. default: scan for missing references.",
    epilog=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument('-a', '--action', default='missing',
    choices=('missing', 'list', 'list_blend', 'remap', 'move'),
    help='Action to perform (default: missing). Remap and move modify files unless --dry_run.')

parser.add_argument('--directory',
    help='Recursively scan all .blend files, including exports, without add-on setup. '
         "Omit to scan the configured game link's repository root or shipped "
         'StuntboostTools folder, with legacy export exclusions.')

parser.add_argument('-o', '--output',
    help='Overwrite a UTF-8 report. Missing/move also print the report to stdout '
         'list/list_blend/remap write only to the report.')

parser.add_argument('-d', '--dry_run', action='store_true',
    help='Validate and report remap/move without modifying assets. Move does not prompt.')


parser.add_argument('-from', '--move_from',
    help='Glob pattern for move (quote it). Independent of --directory, '
         'which selects files scanned for references.')

parser.add_argument('-to', '--move_to',
    help='Existing destination directory, or a new filename for one source. '
         'Keep the same extension, never overwrites.')

parser.add_argument('-rbt', '--remap_block_type',
    help='Name of the member in bpy.data.* e.g. "objects" or "collections" when using "-a remap"')

parser.add_argument('-rnf', '--remap_new_file',
    help='Path to new *.blend file blend when using "-a remap"')
parser.add_argument('-rnb', '--remap_new_block',
    help='Name of the new data block in blend in "-remap_new_file"')

parser.add_argument('-rof', '--remap_old_file', default='',
    help='Exact old-library path for remap. Omit only when the old name identifies one linked datablock.')
parser.add_argument('-rob', '--remap_old_block',
    help='Name of the old linked datablock to replace with --remap_new_block.')

args = parser.parse_args(args=sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
if args.directory and not os.path.isdir(args.directory):
    parser.error(f"Not a directory: {args.directory}")
if args.action == 'remap':
    for option in ('remap_block_type', 'remap_old_block', 'remap_new_file', 'remap_new_block'):
        if not getattr(args, option):
            parser.error(f"--{option} is required for remap")
if args.action == 'move' and (not args.move_from or not args.move_to):
    parser.error("--move_from and --move_to are required for move")


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


@contextmanager
def report_lines():
    """Stream a report to stdout and, when requested, an overwritten UTF-8 file."""
    with (open(args.output, "w", encoding="utf-8") if args.output else nullcontext()) as report:
        def emit(line):
            print(line, flush=True)
            if report is not None:
                report.write(line + "\n")
                report.flush()

        yield emit


def gather_blends() -> list[str]:
    if args.directory:
        def walk_error(error):
            raise error

        return sorted(
            os.path.join(root, name)
            for root, _, names in os.walk(os.path.abspath(args.directory), onerror=walk_error)
            for name in names if name.lower().endswith(".blend"))

    import stuntboost_bpl_runtime

    scan_root = stuntboost_bpl_runtime.get_game_path()
    if not stuntboost_bpl_runtime.is_repo():
        scan_root = os.path.join(scan_root, "StuntboostTools")
    blends = glob.glob(os.path.join(scan_root, "**", "*.blend"), recursive=True)
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
    # Do not run embedded scripts or replace the CLI's UI settings.
    bpy.ops.wm.open_mainfile(filepath=blend_path, load_ui=False, use_scripts=False)
    blend = BlendInfo()
    blend.path = blend_path
    blend.blocks = []
    blend.errors = []
    for block_list_name in block_list_names:
        for block in getattr(bpy.data, block_list_name):
            if not block.is_missing:
                continue
            library = bpy.path.abspath(block.library.filepath) if block.library else ""
            blend.blocks.append(BlockInfo(path=repr(block), library=library))

    # In Blender 4.3.2, packed=False excludes packed files (despite the API
    # docstring saying the opposite). Blender resolves linked assets relative
    # to their owning library and enumerates images, sounds, fonts, caches, etc.
    paths = set(bpy.utils.blend_paths(absolute=True, packed=False, local=False))
    for path in sorted(paths):
        if path and not os.path.exists(path):
            blend.errors.append(path)
    return blend


def check_missing_all() -> int:
    block_list_names = gather_block_list_names()
    affected = 0
    missing = 0
    failed = 0
    blends = gather_blends()
    with report_lines() as emit:
        for index, path in enumerate(blends, 1):
            emit(f"\n[{index}/{len(blends)}] {path}")
            try:
                blend = check_missing_in_current_blend(block_list_names, path)
            except Exception as error:
                failed += 1
                emit(f"  ERROR: Could not check file: {error}")
                continue
            if not blend.blocks and not blend.errors:
                emit("  OK")
                continue
            affected += 1
            missing += len(blend.blocks) + len(blend.errors)
            for block in blend.blocks:
                emit(f"  MISSING DATABLOCK: {block.path} | library: {block.library}")
            for path in blend.errors:
                emit(f"  MISSING FILE: {path}")

        emit(f"\nChecked {len(blends)} blend file(s): {affected} with missing references, "
             f"{missing} missing reference(s), {failed} file(s) could not be checked.")
        if not blends:
            emit("No .blend files found.")
    return 2 if failed or not blends else 1 if missing else 0


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
        bpy.ops.wm.open_mainfile(filepath=i, load_ui=False, use_scripts=False)
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


def canonical_path(path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def remap_in_current_blend(
        bpy_data_member: str,
        old_block: BlockInfo, new_block: BlockInfo,
        blend_path: str) -> BlendInfo:
    bpy.ops.wm.open_mainfile(filepath=blend_path, load_ui=False, use_scripts=False)
    blend = BlendInfo()
    blend.path = blend_path
    blend.blocks = []
    blend.errors = []
    block_list = getattr(bpy.data, bpy_data_member)
    candidates = [
        block for block in block_list
        if block.name == old_block.path and block.library
        and (not old_block.library
             or canonical_path(bpy.path.abspath(block.library.filepath)) == old_block.library)]
    if not candidates:
        return blend
    if len(candidates) != 1:
        raise ValueError("Ambiguous old datablock, specify --remap_old_file")
    old = candidates[0]
    if old.is_library_indirect:
        raise ValueError("Indirect datablocks are unsupported, remap their owning library instead")
    if canonical_path(blend_path) == new_block.library:
        raise ValueError("Cannot link a replacement from the file being edited")

    new = next((
        block for block in block_list
        if block.name == new_block.path and block.library
        and canonical_path(bpy.path.abspath(block.library.filepath)) == new_block.library), None)
    if new is old:
        raise ValueError("Old and replacement datablocks are identical")
    if new is None:
        with bpy.data.libraries.load(new_block.library, link=True, relative=True) as (_, data_to):
            setattr(data_to, bpy_data_member, [new_block.path])
        new = getattr(data_to, bpy_data_member)[0]
    if new is None or new.is_missing:
        raise ValueError("Replacement datablock could not be loaded")
    if new.is_library_indirect:
        raise ValueError("Indirect replacement datablocks are unsupported")

    replacement = BlockInfo(path=repr(old), library=bpy.path.abspath(old.library.filepath))
    if not args.dry_run:
        old.user_remap(new)
        # Remove only the replaced ID, never purge unrelated orphaned assets.
        bpy.data.batch_remove(ids=(old,))
        if bpy.ops.wm.save_as_mainfile(filepath=blend_path) != {'FINISHED'}:
            raise RuntimeError("Blender did not finish saving")
    blend.blocks.append(replacement)
    return blend


def remap_all(bpy_data_member: str, old_block: BlockInfo, new_block: BlockInfo) -> int:
    if not os.path.isfile(new_block.library):
        parser.error(f"Replacement library does not exist: {new_block.library}")
    with bpy.data.libraries.load(new_block.library, link=True) as (data_from, _):
        if not hasattr(data_from, bpy_data_member):
            parser.error(f"Unsupported datablock collection: {bpy_data_member}")
        if new_block.path not in getattr(data_from, bpy_data_member):
            parser.error(f"Replacement datablock not found: {new_block.path}")
    paths = gather_blends()
    if not paths:
        parser.error("No .blend files found")
    blends: list[BlendInfo] = []
    for path in paths:
        try:
            blends.append(remap_in_current_blend(bpy_data_member, old_block, new_block, path))
        except Exception as error:
            blend = BlendInfo()
            blend.path = path
            blend.blocks = []
            blend.errors = [str(error)]
            blends.append(blend)

    result = []
    for blend in blends:
        for block in blend.blocks:
            verb = "Would replace" if args.dry_run else "Replaced"
            result.append(f"{verb} in {blend.path}: {block.path} | {block.library}")
        for error in blend.errors:
            result.append(f"ERROR in {blend.path}: {error}")
    changed = sum(bool(blend.blocks) for blend in blends)
    failed = sum(bool(blend.errors) for blend in blends)
    result.append(f"Checked {len(blends)} file(s): {changed} "
                  f"{'would change' if args.dry_run else 'changed'}, {failed} failed.")
    output("\n".join(result))
    return 2 if failed else 0


def rewrite_move_references(relocations: dict[str, str], scanned: set[str], apply=False):
    """Inspect one loaded blend, only keep Blender ID references within this call."""
    edits = []
    handled = Counter()
    dependencies = set()
    image_directories = {
        os.path.dirname(source) for source in relocations
        if pathlib.Path(source).suffix.lower() != '.blend'}
    for library in bpy.data.libraries:
        source = canonical_path(bpy.path.abspath(library.filepath))
        handled[source] += 1
        dependencies.add(source)
        if source not in relocations or library.packed_file:
            continue
        if library.parent:
            owner = canonical_path(bpy.path.abspath(library.parent.filepath))
            if owner not in scanned:
                raise ValueError(f"Library owner is outside the scan: {owner}")
        edits.append((library, relocations[source], library.filepath.startswith("//")))

    for image in bpy.data.images:
        if image.packed_file or image.source in {'GENERATED', 'VIEWER'} or not image.filepath:
            continue
        source = canonical_path(bpy.path.abspath(image.filepath, library=image.library))
        if image.source == 'SEQUENCE' and os.path.dirname(source) in image_directories:
            raise ValueError(f"Cannot move images from a directory used by an image sequence: "
                             f"{image.name} ({source})")
        if source not in relocations:
            continue
        handled[source] += 1
        if image.library:
            owner = canonical_path(bpy.path.abspath(image.library.filepath))
            if owner not in scanned:
                raise ValueError(f"Image owner is outside the scan: {owner}")
            # Linked image paths must be saved in their owning library, not here.
            continue
        edits.append((image, relocations[source], image.filepath.startswith("//")))

    for path in bpy.utils.blend_paths(absolute=True, packed=False):
        source = canonical_path(path)
        if source in relocations:
            handled[source] -= 1
            if handled[source] < 0:
                raise ValueError(f"Unsupported reference in {bpy.data.filepath}: {path}")
    if apply:
        for block, target, relative in edits:
            block.filepath = bpy.path.relpath(target) if relative else target
    return len(edits), dependencies


def move_blends() -> int:
    sources = sorted({os.path.abspath(path) for path in glob.glob(args.move_from, recursive=True)})
    if not sources:
        parser.error("No files matched --move_from")
    destination = os.path.abspath(args.move_to)
    is_directory = os.path.isdir(destination)
    if not is_directory and len(sources) != 1:
        parser.error("--move_to must be an existing directory when moving multiple files")

    moves = []
    destinations = set()
    relocations = {}
    for source in sources:
        extension = pathlib.Path(source).suffix.lower()
        if not os.path.isfile(source) or extension not in bpy.path.extensions_image | {'.blend'}:
            parser.error(f"Only .blend files and images can be moved: {source}")
        if os.path.islink(source):
            parser.error(f"Moving symbolic links is unsupported: {source}")
        target = os.path.join(destination, os.path.basename(source)) if is_directory else destination
        if pathlib.Path(target).suffix.lower() != extension:
            parser.error(f"Moving cannot change the file format/extension: {target}")
        target_key = canonical_path(target)
        if target_key == canonical_path(source):
            parser.error(f"Source and destination are identical: {source}")
        if os.path.lexists(target) or target_key in destinations:
            parser.error(f"Destination exists or collides with another move: {target}")
        if not os.path.isdir(os.path.dirname(target)):
            parser.error(f"Destination directory does not exist: {os.path.dirname(target)}")
        destinations.add(target_key)
        moves.append((source, target))
        source_key = canonical_path(source)
        if source_key in relocations:
            parser.error(f"Source matched through multiple paths: {source}")
        relocations[source_key] = target

    paths = {canonical_path(path): path for path in gather_blends()}
    scanned = set(paths)
    for source, _ in moves:
        if pathlib.Path(source).suffix.lower() == '.blend' and canonical_path(source) not in scanned:
            parser.error(f"Source blend is outside the scan, widen --directory: {source}")
    owners = scanned | {canonical_path(target) for source, target in moves
                        if pathlib.Path(source).suffix.lower() == '.blend'}
    changed = {}
    dependencies = {}
    for key, path in paths.items():
        bpy.ops.wm.open_mainfile(filepath=path, load_ui=False, use_scripts=False)
        count, libraries = rewrite_move_references(relocations, owners)
        if count or key in relocations:
            changed[key] = count
            dependencies[key] = libraries
    graph = {key: libraries & changed.keys() for key, libraries in dependencies.items()}
    try:
        order = list(TopologicalSorter(graph).static_order())
    except CycleError:
        parser.error("Cyclic library dependencies are unsupported. No files were changed")

    with report_lines() as emit:
        for source, target in moves:
            emit(f"{'Would move' if args.dry_run else 'Move'}: {source} -> {target}")
        for key in order:
            emit(f"{'Would save' if args.dry_run else 'Save'}: {paths[key]} "
                 f"({changed[key]} reference(s) to update)")
        if args.dry_run:
            return 0
        input("Press Enter to move assets and update these blends (Ctrl+C to cancel)...")
        try:
            # Images must exist before saved blends can reference them. Libraries
            # are saved dependency-first so consumers load the updated dependencies.
            for source, target in moves:
                if pathlib.Path(source).suffix.lower() != '.blend':
                    shutil.copy2(source, target)
            for key in order:
                bpy.ops.wm.open_mainfile(filepath=paths[key], load_ui=False, use_scripts=False)
                rewrite_move_references(relocations, owners, apply=True)
                target = relocations.get(key, paths[key])
                if bpy.ops.wm.save_as_mainfile(filepath=target, relative_remap=True) != {'FINISHED'}:
                    raise RuntimeError(f"Blender did not finish saving {target}")
                emit(f"Saved: {target}")
        except Exception as error:
            emit(f"Move incomplete: {error}. Source assets retained, but some destinations or "
                 "dependent blends may already be saved. Restore backups before retrying.")
            raise
        # Keep every source asset until all dependent saves have succeeded.
        for source, target in moves:
            try:
                os.unlink(source)
            except OSError as error:
                emit(f"ERROR removing original {source}: {error}. Saved destination retained at {target}.")
                raise
            emit(f"Moved: {source} -> {target}")
    return 0


start_time = time.time()
exit_code = 0

if args.action == 'list':
    list_all()
elif args.action == 'remap':
    exit_code = remap_all(
        bpy_data_member=args.remap_block_type,
        old_block=BlockInfo(library=canonical_path(args.remap_old_file) if args.remap_old_file else "",
                            path=args.remap_old_block),
        new_block=BlockInfo(library=canonical_path(args.remap_new_file), path=args.remap_new_block))
elif args.action == 'missing':
    exit_code = check_missing_all()
elif args.action == 'list_blend':
    list_blends()
elif args.action == 'move':
    exit_code = move_blends()

delta = datetime.timedelta(seconds=time.time() - start_time)
print(f"\nTook: {delta}s")
sys.exit(exit_code)
