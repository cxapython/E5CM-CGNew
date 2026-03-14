from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pygame

from core.动态背景 import DynamicBackgroundManager
from core.sqlite_store import (
    SCOPE_GAME_ESC_MENU_SETTINGS,
    read_scope,
    write_scope_patch,
)


GAME_ESC_SETTINGS_KEY_AUTOPLAY = "自动播放"
GAME_ESC_SETTINGS_KEY_BINDINGS = "键位绑定"

PROFILE_SINGLE = "single"
PROFILE_DOUBLE = "double"

PROFILE_LABELS: Dict[str, str] = {
    PROFILE_SINGLE: "单踏板",
    PROFILE_DOUBLE: "双踏板",
}

SINGLE_SLOT_ORDER: List[Tuple[str, str]] = [
    ("左下", "左下"),
    ("左上", "左上"),
    ("中间", "中间"),
    ("右上", "右上"),
    ("右下", "右下"),
]

DOUBLE_SLOT_ORDER: List[Tuple[str, str]] = [
    ("左区左下", "左区 左下"),
    ("左区左上", "左区 左上"),
    ("左区中间", "左区 中间"),
    ("左区右上", "左区 右上"),
    ("左区右下", "左区 右下"),
    ("右区左下", "右区 左下"),
    ("右区左上", "右区 左上"),
    ("右区中间", "右区 中间"),
    ("右区右上", "右区 右上"),
    ("右区右下", "右区 右下"),
]

DEFAULT_BINDINGS: Dict[str, Dict[str, int]] = {
    PROFILE_SINGLE: {
        "左下": int(pygame.K_1),
        "左上": int(pygame.K_7),
        "中间": int(pygame.K_5),
        "右上": int(pygame.K_9),
        "右下": int(pygame.K_3),
    },
    PROFILE_DOUBLE: {
        "左区左下": int(pygame.K_z),
        "左区左上": int(pygame.K_q),
        "左区中间": int(pygame.K_s),
        "左区右上": int(pygame.K_e),
        "左区右下": int(pygame.K_c),
        "右区左下": int(pygame.K_1),
        "右区左上": int(pygame.K_7),
        "右区中间": int(pygame.K_5),
        "右区右上": int(pygame.K_9),
        "右区右下": int(pygame.K_3),
    },
}

_REVERSE_TRACK_ORDER = [3, 4, 2, 0, 1]
_DIGIT_KEYCODE_ALIASES: Dict[int, Tuple[int, int]] = {
    int(pygame.K_1): (int(pygame.K_1), int(pygame.K_KP1)),
    int(pygame.K_3): (int(pygame.K_3), int(pygame.K_KP3)),
    int(pygame.K_5): (int(pygame.K_5), int(pygame.K_KP5)),
    int(pygame.K_7): (int(pygame.K_7), int(pygame.K_KP7)),
    int(pygame.K_9): (int(pygame.K_9), int(pygame.K_KP9)),
}
for _primary, _aliases in list(_DIGIT_KEYCODE_ALIASES.items()):
    for _alias in _aliases:
        _DIGIT_KEYCODE_ALIASES[int(_alias)] = tuple(int(v) for v in _aliases)


@dataclass(frozen=True)
class ArrowSkinOption:
    skin_id: str
    label: str
    file_name: str
    skin_dir: str
    preview_path: str = ""


@dataclass(frozen=True)
class BackgroundOption:
    file_name: str
    label: str
    path: str


@dataclass(frozen=True)
class VideoBackgroundOption:
    file_name: str
    label: str
    path: str


def read_game_esc_settings_scope() -> Dict[str, object]:
    data = read_scope(SCOPE_GAME_ESC_MENU_SETTINGS)
    return dict(data) if isinstance(data, dict) else {}


def write_game_esc_settings_scope_patch(patch: Dict[str, object]) -> Dict[str, object]:
    data = write_scope_patch(SCOPE_GAME_ESC_MENU_SETTINGS, dict(patch or {}))
    return dict(data) if isinstance(data, dict) else {}


def iter_profile_slots(profile_id: str) -> List[Tuple[str, str]]:
    if str(profile_id) == PROFILE_DOUBLE:
        return list(DOUBLE_SLOT_ORDER)
    return list(SINGLE_SLOT_ORDER)


def normalize_keycode(keycode: object) -> Optional[int]:
    try:
        value = int(keycode)
    except Exception:
        return None
    aliases = _DIGIT_KEYCODE_ALIASES.get(int(value))
    if aliases:
        return int(aliases[0])
    if value <= 0:
        return None
    return int(value)


def expand_keycode_aliases(keycode: object) -> List[int]:
    normalized = normalize_keycode(keycode)
    if normalized is None:
        return []
    aliases = _DIGIT_KEYCODE_ALIASES.get(int(normalized))
    if aliases:
        return [int(v) for v in aliases]
    return [int(normalized)]


def keycode_to_storage_name(keycode: object) -> str:
    normalized = normalize_keycode(keycode)
    if normalized is None:
        return ""
    try:
        name = str(pygame.key.name(int(normalized)) or "").strip()
    except Exception:
        name = ""
    return name


def keycode_to_display_name(keycode: object) -> str:
    normalized = normalize_keycode(keycode)
    if normalized is None:
        return "未绑定"
    if int(normalized) in _DIGIT_KEYCODE_ALIASES:
        return str(pygame.key.name(int(normalized)) or "").upper() or "?"
    try:
        text = str(pygame.key.name(int(normalized)) or "").strip()
    except Exception:
        text = ""
    if not text:
        return "?"
    special = {
        "space": "SPACE",
        "return": "ENTER",
        "escape": "ESC",
        "left shift": "LSHIFT",
        "right shift": "RSHIFT",
        "left ctrl": "LCTRL",
        "right ctrl": "RCTRL",
        "left alt": "LALT",
        "right alt": "RALT",
        "tab": "TAB",
        "backspace": "BACKSPACE",
        "delete": "DELETE",
        "insert": "INSERT",
        "home": "HOME",
        "end": "END",
        "page up": "PGUP",
        "page down": "PGDN",
        "up": "UP",
        "down": "DOWN",
        "left": "LEFT",
        "right": "RIGHT",
    }
    return str(special.get(text.lower(), text.upper()))


def _parse_saved_key(value: object) -> Optional[int]:
    if isinstance(value, int):
        return normalize_keycode(value)
    text = str(value or "").strip()
    if not text:
        return None
    text = text.lower()
    digit_alias = {
        "kp1": int(pygame.K_1),
        "[1]": int(pygame.K_1),
        "kp3": int(pygame.K_3),
        "[3]": int(pygame.K_3),
        "kp5": int(pygame.K_5),
        "[5]": int(pygame.K_5),
        "kp7": int(pygame.K_7),
        "[7]": int(pygame.K_7),
        "kp9": int(pygame.K_9),
        "[9]": int(pygame.K_9),
    }
    if text in digit_alias:
        return int(digit_alias[text])
    try:
        return normalize_keycode(pygame.key.key_code(text))
    except Exception:
        return None


def load_key_binding_profiles(scope_data: Optional[Dict[str, object]] = None) -> Dict[str, Dict[str, int]]:
    data = dict(scope_data or {}) if isinstance(scope_data, dict) else read_game_esc_settings_scope()
    saved = data.get(GAME_ESC_SETTINGS_KEY_BINDINGS, {})
    saved = dict(saved) if isinstance(saved, dict) else {}

    profiles: Dict[str, Dict[str, int]] = {}
    for profile_id, defaults in DEFAULT_BINDINGS.items():
        current = dict(defaults)
        profile_label = PROFILE_LABELS.get(profile_id, profile_id)
        raw_profile = saved.get(profile_id, saved.get(profile_label, {}))
        raw_profile = dict(raw_profile) if isinstance(raw_profile, dict) else {}
        for slot_id, _slot_label in iter_profile_slots(profile_id):
            parsed = _parse_saved_key(raw_profile.get(slot_id))
            if parsed is not None:
                current[slot_id] = int(parsed)
        profiles[profile_id] = current
    return profiles


def serialize_key_binding_profiles(profiles: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    for profile_id, slots in (profiles or {}).items():
        profile_map: Dict[str, str] = {}
        for slot_id, _slot_label in iter_profile_slots(profile_id):
            value = keycode_to_storage_name(dict(slots or {}).get(slot_id))
            if value:
                profile_map[slot_id] = value
        result[profile_id] = profile_map
    return result


def assign_profile_key(
    profiles: Dict[str, Dict[str, int]],
    profile_id: str,
    slot_id: str,
    keycode: object,
) -> Dict[str, Dict[str, int]]:
    normalized = normalize_keycode(keycode)
    if normalized is None:
        return profiles
    updated: Dict[str, Dict[str, int]] = {
        key: dict(value or {}) for key, value in dict(profiles or {}).items()
    }
    if profile_id not in updated:
        updated[profile_id] = dict(DEFAULT_BINDINGS.get(profile_id, {}))
    profile = updated[profile_id]
    previous = profile.get(slot_id)
    other_slot = None
    for current_slot, current_keycode in profile.items():
        if current_slot == slot_id:
            continue
        if normalize_keycode(current_keycode) == normalized:
            other_slot = current_slot
            break
    profile[slot_id] = int(normalized)
    if other_slot is not None and previous is not None:
        profile[other_slot] = int(previous)
    elif other_slot is not None:
        profile[other_slot] = int(DEFAULT_BINDINGS.get(profile_id, {}).get(other_slot, normalized))
    return updated


def build_track_key_maps(
    *,
    is_double: bool,
    reverse: bool,
    profiles: Dict[str, Dict[str, int]],
) -> Tuple[Dict[int, int], Dict[int, List[int]]]:
    key_to_track: Dict[int, int] = {}
    track_to_keys: Dict[int, List[int]] = {}

    if is_double:
        left_slots = [slot_id for slot_id, _ in DOUBLE_SLOT_ORDER[:5]]
        right_slots = [slot_id for slot_id, _ in DOUBLE_SLOT_ORDER[5:]]
        double_profile = dict((profiles or {}).get(PROFILE_DOUBLE, {}) or {})

        for index, slot_id in enumerate(left_slots):
            keys = expand_keycode_aliases(double_profile.get(slot_id))
            track = int(index)
            if keys:
                track_to_keys[track] = list(keys)
                for keycode in keys:
                    key_to_track[int(keycode)] = int(track)

        for index, slot_id in enumerate(right_slots):
            keys = expand_keycode_aliases(double_profile.get(slot_id))
            target_index = _REVERSE_TRACK_ORDER[index] if reverse else index
            track = int(5 + target_index)
            if keys:
                track_to_keys[track] = list(keys)
                for keycode in keys:
                    key_to_track[int(keycode)] = int(track)
        return key_to_track, track_to_keys

    single_profile = dict((profiles or {}).get(PROFILE_SINGLE, {}) or {})
    single_slots = [slot_id for slot_id, _ in SINGLE_SLOT_ORDER]
    for index, slot_id in enumerate(single_slots):
        keys = expand_keycode_aliases(single_profile.get(slot_id))
        track = int(_REVERSE_TRACK_ORDER[index] if reverse else index)
        if not keys:
            continue
        track_to_keys[track] = list(keys)
        for keycode in keys:
            key_to_track[int(keycode)] = int(track)
    return key_to_track, track_to_keys


def scan_arrow_skin_options(project_root: str) -> List[ArrowSkinOption]:
    root = os.path.join(str(project_root or ""), "UI-img", "游戏界面", "箭头")
    preview_root = os.path.join(
        str(project_root or ""),
        "UI-img",
        "选歌界面资源",
        "设置",
        "设置-箭头候选",
    )
    options: List[ArrowSkinOption] = []
    if not os.path.isdir(root):
        return options
    for name in sorted(os.listdir(root)):
        skin_dir = os.path.join(root, str(name))
        if not os.path.isdir(skin_dir):
            continue
        arrow_json = os.path.join(skin_dir, "arrow", "skin.json")
        key_json = os.path.join(skin_dir, "key", "skin.json")
        if not (os.path.isfile(arrow_json) and os.path.isfile(key_json)):
            continue
        skin_id = str(name).strip()
        if not skin_id:
            continue
        preview_path = ""
        preview_candidate = os.path.join(preview_root, f"{skin_id}.png")
        if os.path.isfile(preview_candidate):
            preview_path = preview_candidate
        options.append(
            ArrowSkinOption(
                skin_id=skin_id,
                label=skin_id,
                file_name=f"{skin_id}.png",
                skin_dir=skin_dir,
                preview_path=preview_path,
            )
        )
    return options


def scan_background_options(project_root: str) -> List[BackgroundOption]:
    root = os.path.join(str(project_root or ""), "冷资源", "backimages", "背景图")
    supported = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
    options: List[BackgroundOption] = []
    if not os.path.isdir(root):
        return options
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, str(name))
        if not os.path.isfile(path):
            continue
        if not str(name).lower().endswith(supported):
            continue
        label = os.path.splitext(str(name))[0]
        options.append(
            BackgroundOption(
                file_name=str(name),
                label=label,
                path=path,
            )
        )
    return options


def scan_video_background_options(project_root: str) -> List[VideoBackgroundOption]:
    root = os.path.join(str(project_root or ""), "backmovies", "游戏中")
    supported = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v")
    options: List[VideoBackgroundOption] = []
    if not os.path.isdir(root):
        return options
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, str(name))
        if (not os.path.isfile(path)) or (not str(name).lower().endswith(supported)):
            continue
        label = os.path.splitext(str(name))[0]
        options.append(
            VideoBackgroundOption(
                file_name=str(name),
                label=label,
                path=path,
            )
        )
    return options


def get_dynamic_background_modes(include_off: bool = False) -> List[str]:
    modes = [str(mode or "").strip() for mode in DynamicBackgroundManager.get_candidate_modes()]
    modes = [mode for mode in modes if mode]
    if include_off:
        return modes
    return [mode for mode in modes if mode != "关闭"]


def resolve_arrow_skin_option(
    options: Iterable[ArrowSkinOption],
    selected_value: object,
) -> Optional[ArrowSkinOption]:
    option_list = list(options or [])
    if not option_list:
        return None
    selected = str(selected_value or "").strip()
    if selected:
        digits = ""
        matched = re.search(r"(\d{1,3})", selected)
        if matched:
            try:
                digits = f"{int(matched.group(1)):02d}"
            except Exception:
                digits = ""
        for option in option_list:
            if selected in (option.file_name, option.skin_id, option.label):
                return option
            if digits and digits == option.skin_id:
                return option
    return option_list[0]


def resolve_background_option(
    options: Iterable[BackgroundOption],
    selected_value: object,
) -> Optional[BackgroundOption]:
    option_list = list(options or [])
    if not option_list:
        return None
    selected = str(selected_value or "").strip()
    if selected:
        for option in option_list:
            if selected in (option.file_name, option.label, option.path):
                return option
    return option_list[0]


def resolve_video_background_option(
    options: Iterable[VideoBackgroundOption],
    selected_value: object,
) -> Optional[VideoBackgroundOption]:
    option_list = list(options or [])
    if not option_list:
        return None
    selected = str(selected_value or "").strip()
    if selected:
        for option in option_list:
            if selected in (option.file_name, option.label, option.path):
                return option
    return option_list[0]


def read_saved_autoplay(scope_data: Optional[Dict[str, object]] = None) -> Optional[bool]:
    data = dict(scope_data or {}) if isinstance(scope_data, dict) else read_game_esc_settings_scope()
    if GAME_ESC_SETTINGS_KEY_AUTOPLAY in data:
        try:
            return bool(data.get(GAME_ESC_SETTINGS_KEY_AUTOPLAY))
        except Exception:
            return None
    return None
