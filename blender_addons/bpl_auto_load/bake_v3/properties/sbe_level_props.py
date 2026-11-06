"""
Custom map metadata written to the `<level>_.json` custom level exports.
Blend wide, attached to the same text data block as SBE_BlendProperties.

Since this is new, old levels without the data migrate once and load the data from the json.
"""

import json
import os
import typing
import uuid

# pylint: disable=import-error
import bpy
from bpy.app.handlers import persistent
# pylint: enable=import-error

from bake_v3.sbe_util import get_persistent_data_block, get_filename_without_extension, SBE_PERSISTENT_DATA_BLOCK
from bake_v3.sbe_paths import get_export_folder, use_custom_map_export, is_custom_level_blend
from bake_v3.sbe_logger import SBE_Logger

BOARD_TYPES = ['Normal', 'Longboard', 'Car', 'Scooter', 'CarScooter']
"""Names of SE.BoardType"""

ABILITIES = ['None', 'Jump', 'Crouch', 'JumpAndCrouch', 'Grind', 'AirMovement']
"""Names of SE.TutorialAbility"""

MEDALS = ['silver', 'gold', 'diamond', 'obsidian', 'developer']
"""Keys of medalTimesSeconds"""

SETTINGS: list[tuple[str, str, str]] = [
    ("version", "version", 'INT'),
    ("spawn", "spawn", 'STRING'),
    ("boardType", "board_type", 'ENUM'),
    ("maxAbility", "max_ability", 'ENUM'),
    ("tiltCamToGround", "tilt_cam_to_ground", 'INT'),
    ("shadowColor", "shadow_color", 'COLOR'),
    ("ambientLightInShadow", "ambient_light_in_shadow", 'FLOAT'),
    ("fogColor", "fog_color", 'COLOR'),
    ("fogStart", "fog_start", 'FLOAT'),
    ("fogLength", "fog_length", 'FLOAT'),
    ("godRayColor", "god_ray_color", 'COLOR'),
    ("godRayIntensity", "god_ray_intensity", 'FLOAT'),
]
"""(sidecar key, property name, kind) of the single value fields"""

GAMEPLAY_PROPS = ["spawn", "board_type", "max_ability", "tilt_cam_to_ground"]
"""Affect gameplay, changing them keeps the records unless Version is bumped"""

MANAGED_KEYS = ["id", "name", "author", "preview", "medalTimesSeconds"] + [key for key, _, _ in SETTINGS]
"""Sidecar keys owned by the properties. Other keys in an existing sidecar are preserved."""

PREVIEW_SUFFIX = "_preview.png"
"""The preview is copied to `<level><PREVIEW_SUFFIX>` in the map folder"""


def get_sidecar_folder() -> str:
    return bpy.path.abspath(get_export_folder(get_filename_without_extension()))


def get_sidecar_path() -> str:
    return os.path.join(get_sidecar_folder(), get_filename_without_extension() + "_.json")


def read_sidecar(path: str) -> dict:
    """Returns the sidecar content, an empty dict if it doesn't exist yet."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    if not isinstance(metadata, dict):
        raise ValueError("Level sidecar must contain a JSON object")
    return metadata


def migrate_sidecar() -> None:
    """
    Load properties from json file.
    """
    if not use_custom_map_export() or not is_custom_level_blend(bpy.data.filepath):
        return
    path = get_sidecar_path()
    sidecar_exists = os.path.exists(path)
    if not sidecar_exists and SBE_PERSISTENT_DATA_BLOCK not in bpy.data.texts:
        return
    props: SBE_LevelProperties = SBE_LevelProperties.get()
    if props.sidecar_migrated:
        return
    if sidecar_exists:
        try:
            metadata = read_sidecar(path)
        except (OSError, ValueError) as e:
            SBE_Logger.error(f"Could not migrate level sidecar {path}: {e}")
            return
        props.load_metadata(metadata, get_sidecar_folder())
    props.sidecar_migrated = True


def new_map_id() -> str:
    return str(uuid.uuid4())


def ensure_map_id() -> None:
    """Generates the map ID of a custom level blend if missing"""
    if bpy.app.background or not use_custom_map_export() or not is_custom_level_blend(bpy.data.filepath):
        return
    migrate_sidecar() # adopt the ID of an existing sidecar instead of replacing it
    props: SBE_LevelProperties = SBE_LevelProperties.get()
    if props.map_id.strip():
        return
    props.map_id = new_map_id()
    SBE_Logger.print(f"Generated map ID {props.map_id}")


@persistent
def _migrate_on_load(_blend_path: str) -> None:
    migrate_sidecar()


def _migrate_after_register() -> None:
    """load_post doesn't fire for the blend already open when the addon is (re)loaded"""
    migrate_sidecar()


def _on_edit(self: "SBE_LevelProperties", _context: bpy.types.Context) -> None:
    if not self.sidecar_migrated:
        # once edited, never migrate again
        self.sidecar_migrated = True


def _medal(name: str, default: float, description: str) -> bpy.props.FloatProperty:
    return bpy.props.FloatProperty(name=name, description=description, min=0.001, default=default,
                                   precision=3, unit='TIME_ABSOLUTE', update=_on_edit)


def _color(name: str, default: tuple[float, ...]) -> bpy.props.FloatVectorProperty:
    return bpy.props.FloatVectorProperty(name=name, subtype='COLOR_GAMMA', size=len(default),
                                         min=0.0, max=1.0, default=default, update=_on_edit)


def _float(name: str, default: float, description: str = "") -> bpy.props.FloatProperty:
    return bpy.props.FloatProperty(name=name, description=description, default=default, update=_on_edit)


_MEDAL = "Medal time in seconds"


class SBE_LevelProperties(bpy.types.PropertyGroup):
    sidecar_migrated: bpy.props.BoolProperty(
        name="Sidecar Migrated",
        description="Migrated flag to prevent stomping user data set in the UI",
        default=False)

    map_id: bpy.props.StringProperty(
        name="ID", update=_on_edit,
        description="UUID identifying the map locally, keep it so local records survive renames etc. Not used online! Workshop maps are identified by their item. Empty: generated on the next export")
    map_name: bpy.props.StringProperty(
        name="Name", description="Displayed title. Empty: the file name", update=_on_edit)
    author: bpy.props.StringProperty(
        name="Author", description="Displayed author. Empty: Unknown", update=_on_edit)
    preview: bpy.props.StringProperty(
        name="Preview", subtype='FILE_PATH', update=_on_edit,
        options={'PATH_SUPPORTS_BLEND_RELATIVE'} if bpy.app.version >= (4, 5, 0) else set(), # untested on higher versions
        description="PNG shown in the level selection. Copied into the map folder on export. Empty: no preview")

    version: bpy.props.IntProperty(
        name="Version", description="Increase to start a new record version and an empty leaderboard.", min=0, default=1, update=_on_edit)

    silver: _medal("Silver", 60.0, _MEDAL)
    gold: _medal("Gold", 45.0, _MEDAL)
    diamond: _medal("Diamond", 35.0, _MEDAL)
    obsidian: _medal("Obsidian", 30.0, _MEDAL)
    developer: _medal("Developer", 28.0, _MEDAL)

    spawn: bpy.props.StringProperty(
        name="Spawn", description="Name of the spawn point to start at", default="start", update=_on_edit)
    board_type: bpy.props.EnumProperty(
        name="Vehicle", items=[(name, name, "") for name in BOARD_TYPES], default='Normal', update=_on_edit)
    max_ability: bpy.props.EnumProperty(
        name="Max Ability", description="Abilities available to the player",
        items=[(name, name, "") for name in ABILITIES], default='Grind', update=_on_edit)
    tilt_cam_to_ground: bpy.props.IntProperty(
        name="Tilt Camera to Ground", description="Above 0 tilts the camera with the ground",
        default=0, update=_on_edit)

    shadow_color: _color("Shadow Color", (0.0, 0.0, 0.0))
    ambient_light_in_shadow: _float("Ambient Light in Shadow", 0.5)
    fog_color: _color("Fog Color", (0.8, 0.8, 0.6, 1.0))
    fog_start: _float("Fog Start", 100.0)
    fog_length: _float("Fog Length", 2000.0)
    god_ray_color: _color("God Ray Color", (1.0, 0.9, 0.8))
    god_ray_intensity: _float("God Ray Intensity", 1.0)

    def medal_order_error(self) -> typing.Optional[str]:
        """Checks for valid times silver >= gold >= diamond >= obsidian >= developer"""
        times = [getattr(self, medal) for medal in MEDALS]
        if any(easier < harder for easier, harder in zip(times, times[1:])):
            return "Medal times must satisfy silver >= gold >= diamond >= obsidian >= developer"
        return None

    def to_metadata(self, preview_file: typing.Optional[str]) -> dict:
        """Sidecar fields. `preview_file` is the preview path relative to the map folder."""
        metadata: dict = {}
        for key, value in (("id", self.map_id), ("name", self.map_name), ("author", self.author)):
            if value.strip():
                metadata[key] = value.strip()
        if preview_file:
            metadata["preview"] = preview_file
        metadata["medalTimesSeconds"] = {medal: round(getattr(self, medal), 3) for medal in MEDALS}
        for key, prop, kind in SETTINGS:
            value = getattr(self, prop)
            if kind == 'COLOR':
                value = [round(c, 4) for c in value]
            elif kind == 'FLOAT':
                value = round(value, 4)
            metadata[key] = value
        return metadata

    def load_metadata(self, metadata: dict, map_folder: str) -> None:
        """
        Fill the properties from a json.
        """
        for prop, key in (("map_id", "id"), ("map_name", "name"), ("author", "author")):
            value = metadata.get(key)
            if isinstance(value, str):
                setattr(self, prop, value)
        preview = metadata.get("preview")
        if isinstance(preview, str) and preview:
            self.preview = os.path.join(map_folder, preview)
        medals = metadata.get("medalTimesSeconds")
        medals = medals if isinstance(medals, dict) else {}
        inherited: typing.Any = None
        for medal in MEDALS:
            value = medals.get(medal, inherited)
            self._load(medal, 'FLOAT', value)
            if value is not None:
                inherited = getattr(self, medal)
        for key, prop, kind in SETTINGS:
            self._load(prop, kind, metadata.get(key))

    def _load(self, prop: str, kind: str, value: typing.Any) -> None:
        if value is None:
            return
        try:
            if kind == 'COLOR':
                if isinstance(value, str):
                    hex_value = value.lstrip('#')
                    value = [int(hex_value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
                size = len(getattr(self, prop))
                value = (list(value) + [1.0] * size)[:size]
            elif kind == 'INT' and (isinstance(value, bool) or not isinstance(value, int)):
                raise ValueError()
            elif kind == 'FLOAT' and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise ValueError()
            elif kind in ('STRING', 'ENUM') and not isinstance(value, str):
                raise ValueError()
            setattr(self, prop, value)
        except (ValueError, TypeError):
            SBE_Logger.print(f"Skipping malformed sidecar value for {prop}: {value!r}")

    @staticmethod
    def register_property() -> None:
        bpy.utils.register_class(SBE_LevelProperties)
        bpy.types.Text.sbe_level_properties = bpy.props.PointerProperty(
            type=SBE_LevelProperties, name="SBE Level Properties",
            description="Custom map metadata for the STUNTBOOST export")
        bpy.app.handlers.load_post.append(_migrate_on_load)
        bpy.app.timers.register(_migrate_after_register, first_interval=0)

    @staticmethod
    def unregister_property() -> None:
        if bpy.app.timers.is_registered(_migrate_after_register):
            bpy.app.timers.unregister(_migrate_after_register)
        bpy.app.handlers.load_post.remove(_migrate_on_load)
        del bpy.types.Text.sbe_level_properties
        bpy.utils.unregister_class(SBE_LevelProperties)

    @staticmethod
    def get() -> typing.Self:
        return get_persistent_data_block().sbe_level_properties