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
GAME_ESC_SETTINGS_KEY_CHART_VISUAL_OFFSET_MS = "谱面偏移毫秒"
GAME_ESC_SETTINGS_KEY_BPM_SCROLL_EFFECT = "BPM变速效果"
GAME_ESC_SETTINGS_KEY_IMAGE_SLIDESHOW = "图片幻灯片模式"

CHART_VISUAL_OFFSET_STEP_MS = 10
CHART_VISUAL_OFFSET_MIN_MS = -500
CHART_VISUAL_OFFSET_MAX_MS = 500

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

BindingToken = str

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


def _make_key_binding_token(keycode: object) -> Optional[BindingToken]:
    try:
        value = int(keycode)
    except Exception:
        return None
    aliases = _DIGIT_KEYCODE_ALIASES.get(int(value))
    if aliases:
        value = int(aliases[0])
    if value <= 0:
        return None
    return f"key:{int(value)}"


def _make_joy_button_binding_token(
    joy_index: object,
    button_index: object,
) -> Optional[BindingToken]:
    try:
        joy_number = int(joy_index)
        button_number = int(button_index)
    except Exception:
        return None
    if joy_number <= 0 or button_number < 0:
        return None
    return f"joy:{int(joy_number)}:{int(button_number)}"


DEFAULT_BINDINGS: Dict[str, Dict[str, BindingToken]] = {
    PROFILE_SINGLE: {
        "左下": str(_make_key_binding_token(pygame.K_1) or ""),
        "左上": str(_make_key_binding_token(pygame.K_7) or ""),
        "中间": str(_make_key_binding_token(pygame.K_5) or ""),
        "右上": str(_make_key_binding_token(pygame.K_9) or ""),
        "右下": str(_make_key_binding_token(pygame.K_3) or ""),
    },
    PROFILE_DOUBLE: {
        "左区左下": str(_make_key_binding_token(pygame.K_z) or ""),
        "左区左上": str(_make_key_binding_token(pygame.K_q) or ""),
        "左区中间": str(_make_key_binding_token(pygame.K_s) or ""),
        "左区右上": str(_make_key_binding_token(pygame.K_e) or ""),
        "左区右下": str(_make_key_binding_token(pygame.K_c) or ""),
        "右区左下": str(_make_key_binding_token(pygame.K_1) or ""),
        "右区左上": str(_make_key_binding_token(pygame.K_7) or ""),
        "右区中间": str(_make_key_binding_token(pygame.K_5) or ""),
        "右区右上": str(_make_key_binding_token(pygame.K_9) or ""),
        "右区右下": str(_make_key_binding_token(pygame.K_3) or ""),
    },
}


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


_扫描选项缓存: Dict[str, Tuple[Tuple[Tuple[object, ...], ...], Tuple[object, ...]]] = {}


def _is_stepmania_arrow_skin_dir(path: str) -> bool:
    root = os.path.abspath(str(path or "").strip())
    if not root or (not os.path.isdir(root)):
        return False
    try:
        for name in os.listdir(root):
            lower = str(name).lower()
            if lower.endswith(".png") and ("tap note" in lower):
                if os.path.isfile(os.path.join(root, str(name))):
                    return True
    except Exception:
        return False
    return False


def read_game_esc_settings_scope() -> Dict[str, object]:
    data = read_scope(SCOPE_GAME_ESC_MENU_SETTINGS)
    return dict(data) if isinstance(data, dict) else {}


def write_game_esc_settings_scope_patch(patch: Dict[str, object]) -> Dict[str, object]:
    data = write_scope_patch(SCOPE_GAME_ESC_MENU_SETTINGS, dict(patch or {}))
    return dict(data) if isinstance(data, dict) else {}


def clamp_chart_visual_offset_ms(value: object, default: int = 0) -> int:
    try:
        number = int(round(float(value)))
    except Exception:
        number = int(default)
    return int(
        max(
            int(CHART_VISUAL_OFFSET_MIN_MS),
            min(int(CHART_VISUAL_OFFSET_MAX_MS), int(number)),
        )
    )


def format_chart_visual_offset_ms(value: object) -> str:
    offset_ms = int(clamp_chart_visual_offset_ms(value, 0))
    if offset_ms > 0:
        return f"+{offset_ms} ms"
    return f"{offset_ms} ms"


def iter_profile_slots(profile_id: str) -> List[Tuple[str, str]]:
    if str(profile_id) == PROFILE_DOUBLE:
        return list(DOUBLE_SLOT_ORDER)
    return list(SINGLE_SLOT_ORDER)


def _binding_token_to_keycode(binding: object) -> Optional[int]:
    token = str(binding or "").strip().lower()
    if not token.startswith("key:"):
        return None
    try:
        return int(token.split(":", 1)[1])
    except Exception:
        return None


def _binding_token_to_joy_button(binding: object) -> Optional[Tuple[int, int]]:
    token = str(binding or "").strip().lower()
    if not token.startswith("joy:"):
        return None
    parts = token.split(":")
    if len(parts) != 3:
        return None
    try:
        joy_number = int(parts[1])
        button_index = int(parts[2])
    except Exception:
        return None
    if joy_number <= 0 or button_index < 0:
        return None
    return int(joy_number), int(button_index)


def _resolve_joystick_index_from_event(event: object) -> Optional[int]:
    try:
        instance_id = getattr(event, "instance_id", None)
    except Exception:
        instance_id = None
    if instance_id is not None:
        try:
            pygame.joystick.init()
            count = int(pygame.joystick.get_count() or 0)
        except Exception:
            count = 0
        for index in range(count):
            try:
                joystick = pygame.joystick.Joystick(index)
                if not bool(joystick.get_init()):
                    joystick.init()
                if int(joystick.get_instance_id()) == int(instance_id):
                    return int(index) + 1
            except Exception:
                continue
    try:
        joy = getattr(event, "joy", None)
        if joy is not None:
            return int(joy) + 1
    except Exception:
        pass
    return None


def normalize_binding(binding: object) -> Optional[BindingToken]:
    if isinstance(binding, dict):
        data = dict(binding)
        kind = str(data.get("kind", data.get("type", "")) or "").strip().lower()
        if kind in ("key", "keyboard"):
            return _make_key_binding_token(data.get("keycode", data.get("key", None)))
        if kind in ("joy", "joy_button", "joystick", "joystick_button"):
            button = data.get("button", data.get("button_index", data.get("btn", None)))
            joy_index = data.get("joy_index", data.get("joy", data.get("joystick", None)))
            return _make_joy_button_binding_token(joy_index, button)
        return None
    if isinstance(binding, int):
        return _make_key_binding_token(binding)

    text = str(binding or "").strip()
    if not text:
        return None

    token_match = re.fullmatch(r"(key|joy):(.+)", text, re.IGNORECASE)
    if token_match:
        kind = str(token_match.group(1) or "").strip().lower()
        payload = str(token_match.group(2) or "").strip()
        if kind == "key":
            try:
                return _make_key_binding_token(int(payload))
            except Exception:
                return None
        parts = [part.strip() for part in payload.split(":")]
        if len(parts) != 2:
            return None
        try:
            return _make_joy_button_binding_token(int(parts[0]), int(parts[1]))
        except Exception:
            return None

    text_lower = text.lower()
    joy_match = re.fullmatch(
        r"joy\s*(\d+)\s*(?:[:\s_-]*)\s*b(?:utton)?\s*(\d+)",
        text_lower,
        re.IGNORECASE,
    )
    if joy_match:
        try:
            joy_number = int(joy_match.group(1))
            button_number = int(joy_match.group(2))
        except Exception:
            return None
        return _make_joy_button_binding_token(joy_number, button_number - 1)

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
    if text_lower in digit_alias:
        return _make_key_binding_token(int(digit_alias[text_lower]))
    try:
        return _make_key_binding_token(pygame.key.key_code(text_lower))
    except Exception:
        return None


def normalize_keycode(keycode: object) -> Optional[int]:
    return _binding_token_to_keycode(normalize_binding(keycode))


def expand_keycode_aliases(keycode: object) -> List[int]:
    normalized = normalize_keycode(keycode)
    if normalized is None:
        return []
    aliases = _DIGIT_KEYCODE_ALIASES.get(int(normalized))
    if aliases:
        return [int(v) for v in aliases]
    return [int(normalized)]


def expand_binding_aliases(binding: object) -> List[BindingToken]:
    normalized = normalize_binding(binding)
    if normalized is None:
        return []
    keycode = _binding_token_to_keycode(normalized)
    if keycode is not None:
        result: List[BindingToken] = []
        for alias in expand_keycode_aliases(keycode):
            token = _make_key_binding_token(alias)
            if token and token not in result:
                result.append(str(token))
        return result
    return [str(normalized)]


def keycode_to_storage_name(keycode: object) -> str:
    normalized = normalize_binding(keycode)
    if normalized is None:
        return ""
    joy_binding = _binding_token_to_joy_button(normalized)
    if joy_binding is not None:
        joy_number, button_index = joy_binding
        return f"joy{int(joy_number)}:b{int(button_index) + 1}"
    normalized_keycode = _binding_token_to_keycode(normalized)
    if normalized_keycode is None:
        return ""
    try:
        name = str(pygame.key.name(int(normalized_keycode)) or "").strip()
    except Exception:
        name = ""
    return name


def keycode_to_display_name(keycode: object) -> str:
    normalized = normalize_binding(keycode)
    if normalized is None:
        return "未绑定"
    joy_binding = _binding_token_to_joy_button(normalized)
    if joy_binding is not None:
        joy_number, button_index = joy_binding
        return f"Joy{int(joy_number)} B{int(button_index) + 1}"
    normalized_keycode = _binding_token_to_keycode(normalized)
    if normalized_keycode is None:
        return "?"
    if int(normalized_keycode) in _DIGIT_KEYCODE_ALIASES:
        return str(pygame.key.name(int(normalized_keycode)) or "").upper() or "?"
    try:
        text = str(pygame.key.name(int(normalized_keycode)) or "").strip()
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


def binding_from_event(event: object) -> Optional[BindingToken]:
    try:
        event_type = getattr(event, "type", None)
    except Exception:
        event_type = None
    if event_type == pygame.KEYDOWN:
        return _make_key_binding_token(getattr(event, "key", None))
    if event_type == pygame.JOYBUTTONDOWN:
        joy_number = _resolve_joystick_index_from_event(event)
        if joy_number is None:
            return None
        return _make_joy_button_binding_token(joy_number, getattr(event, "button", None))
    return None


def is_binding_pressed(binding: object, keyboard_state: object = None) -> bool:
    normalized = normalize_binding(binding)
    if normalized is None:
        return False
    normalized_keycode = _binding_token_to_keycode(normalized)
    if normalized_keycode is not None:
        if keyboard_state is None:
            try:
                keyboard_state = pygame.key.get_pressed()
            except Exception:
                keyboard_state = None
        if keyboard_state is None:
            return False
        for alias in expand_keycode_aliases(normalized_keycode):
            try:
                if bool(keyboard_state[int(alias)]):
                    return True
            except Exception:
                continue
        return False

    joy_binding = _binding_token_to_joy_button(normalized)
    if joy_binding is None:
        return False
    joy_number, button_index = joy_binding
    try:
        pygame.joystick.init()
        joystick_index = int(joy_number) - 1
        if joystick_index < 0 or joystick_index >= int(pygame.joystick.get_count() or 0):
            return False
        joystick = pygame.joystick.Joystick(joystick_index)
        if not bool(joystick.get_init()):
            joystick.init()
        return bool(joystick.get_button(int(button_index)))
    except Exception:
        return False


def load_key_binding_profiles(
    scope_data: Optional[Dict[str, object]] = None,
) -> Dict[str, Dict[str, BindingToken]]:
    data = dict(scope_data or {}) if isinstance(scope_data, dict) else read_game_esc_settings_scope()
    saved = data.get(GAME_ESC_SETTINGS_KEY_BINDINGS, {})
    saved = dict(saved) if isinstance(saved, dict) else {}

    profiles: Dict[str, Dict[str, BindingToken]] = {}
    for profile_id, defaults in DEFAULT_BINDINGS.items():
        current = dict(defaults)
        profile_label = PROFILE_LABELS.get(profile_id, profile_id)
        raw_profile = saved.get(profile_id, saved.get(profile_label, {}))
        raw_profile = dict(raw_profile) if isinstance(raw_profile, dict) else {}
        for slot_id, _slot_label in iter_profile_slots(profile_id):
            parsed = normalize_binding(raw_profile.get(slot_id))
            if parsed is not None:
                current[slot_id] = str(parsed)
        profiles[profile_id] = current
    return profiles


def serialize_key_binding_profiles(
    profiles: Dict[str, Dict[str, BindingToken]],
) -> Dict[str, Dict[str, str]]:
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
    profiles: Dict[str, Dict[str, BindingToken]],
    profile_id: str,
    slot_id: str,
    keycode: object,
) -> Dict[str, Dict[str, BindingToken]]:
    normalized = normalize_binding(keycode)
    if normalized is None:
        return profiles
    updated: Dict[str, Dict[str, BindingToken]] = {
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
        if normalize_binding(current_keycode) == normalized:
            other_slot = current_slot
            break
    profile[slot_id] = str(normalized)
    if other_slot is not None and previous is not None:
        previous_normalized = normalize_binding(previous)
        if previous_normalized is not None:
            profile[other_slot] = str(previous_normalized)
    elif other_slot is not None:
        profile[other_slot] = str(
            normalize_binding(DEFAULT_BINDINGS.get(profile_id, {}).get(other_slot, normalized))
            or normalized
        )
    return updated


def _取文件条目签名(路径: str) -> Tuple[str, float, int]:
    名称 = os.path.basename(str(路径 or ""))
    try:
        修改时间 = float(os.path.getmtime(路径))
    except Exception:
        修改时间 = 0.0
    try:
        文件大小 = int(os.path.getsize(路径))
    except Exception:
        文件大小 = 0
    return (str(名称), float(修改时间), int(文件大小))


def _读取扫描选项缓存(缓存键: str, 签名: Tuple[Tuple[object, ...], ...]) -> Optional[list]:
    命中 = _扫描选项缓存.get(str(缓存键))
    if not isinstance(命中, tuple) or len(命中) != 2:
        return None
    旧签名, 旧结果 = 命中
    if tuple(旧签名) != tuple(签名):
        return None
    return list(旧结果 or [])


def _写入扫描选项缓存(缓存键: str, 签名: Tuple[Tuple[object, ...], ...], 结果列表: List[object]) -> None:
    _扫描选项缓存[str(缓存键)] = (
        tuple(签名 or ()),
        tuple(结果列表 or ()),
    )


def _构建背景目录签名(目录路径: str, 扩展名列表: Tuple[str, ...]) -> Tuple[Tuple[object, ...], ...]:
    if not os.path.isdir(目录路径):
        return ()
    条目列表: List[Tuple[object, ...]] = []
    try:
        for 名称 in sorted(os.listdir(目录路径)):
            路径 = os.path.join(目录路径, str(名称))
            if (not os.path.isfile(路径)) or (not str(名称).lower().endswith(扩展名列表)):
                continue
            条目列表.append(tuple(_取文件条目签名(路径)))
    except Exception:
        return ()
    return tuple(条目列表)


def _构建箭头皮肤目录签名(project_root: str) -> Tuple[Tuple[object, ...], ...]:
    root = os.path.join(str(project_root or ""), "UI-img", "游戏界面", "箭头")
    preview_root = os.path.join(
        str(project_root or ""),
        "UI-img",
        "选歌界面资源",
        "设置",
        "设置-箭头候选",
    )
    if not os.path.isdir(root):
        return ()

    条目列表: List[Tuple[object, ...]] = []
    try:
        for name in sorted(os.listdir(root)):
            skin_dir = os.path.join(root, str(name))
            if not os.path.isdir(skin_dir):
                continue

            try:
                目录修改时间 = float(os.path.getmtime(skin_dir))
            except Exception:
                目录修改时间 = 0.0

            preview_candidate = os.path.join(preview_root, f"{str(name).strip()}.png")
            preview签名 = (
                tuple(_取文件条目签名(preview_candidate))
                if os.path.isfile(preview_candidate)
                else ("", 0.0, 0)
            )
            条目列表.append(
                (
                    str(name),
                    float(目录修改时间),
                    tuple(preview签名),
                )
            )
    except Exception:
        return ()
    return tuple(条目列表)


def build_track_key_maps(
    *,
    is_double: bool,
    reverse: bool,
    profiles: Dict[str, Dict[str, BindingToken]],
) -> Tuple[Dict[BindingToken, int], Dict[int, List[BindingToken]]]:
    key_to_track: Dict[BindingToken, int] = {}
    track_to_keys: Dict[int, List[BindingToken]] = {}

    if is_double:
        left_slots = [slot_id for slot_id, _ in DOUBLE_SLOT_ORDER[:5]]
        right_slots = [slot_id for slot_id, _ in DOUBLE_SLOT_ORDER[5:]]
        double_profile = dict((profiles or {}).get(PROFILE_DOUBLE, {}) or {})

        for index, slot_id in enumerate(left_slots):
            keys = expand_binding_aliases(double_profile.get(slot_id))
            track = int(index)
            if keys:
                track_to_keys[track] = list(keys)
                for keycode in keys:
                    key_to_track[str(keycode)] = int(track)

        for index, slot_id in enumerate(right_slots):
            keys = expand_binding_aliases(double_profile.get(slot_id))
            target_index = _REVERSE_TRACK_ORDER[index] if reverse else index
            track = int(5 + target_index)
            if keys:
                track_to_keys[track] = list(keys)
                for keycode in keys:
                    key_to_track[str(keycode)] = int(track)
        return key_to_track, track_to_keys

    single_profile = dict((profiles or {}).get(PROFILE_SINGLE, {}) or {})
    single_slots = [slot_id for slot_id, _ in SINGLE_SLOT_ORDER]
    for index, slot_id in enumerate(single_slots):
        keys = expand_binding_aliases(single_profile.get(slot_id))
        track = int(_REVERSE_TRACK_ORDER[index] if reverse else index)
        if not keys:
            continue
        track_to_keys[track] = list(keys)
        for keycode in keys:
            key_to_track[str(keycode)] = int(track)
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
    缓存签名 = _构建箭头皮肤目录签名(project_root)
    缓存键 = f"arrow_skin_options::{os.path.abspath(str(project_root or ''))}"
    缓存命中 = _读取扫描选项缓存(缓存键, 缓存签名)
    if 缓存命中 is not None:
        return [option for option in 缓存命中 if isinstance(option, ArrowSkinOption)]
    for name in sorted(os.listdir(root)):
        skin_dir = os.path.join(root, str(name))
        if not os.path.isdir(skin_dir):
            continue
        arrow_json = os.path.join(skin_dir, "arrow", "skin.json")
        key_json = os.path.join(skin_dir, "key", "skin.json")
        key_1p_json = os.path.join(skin_dir, "key", "1p", "skin.json")
        key_2p_json = os.path.join(skin_dir, "key", "2p", "skin.json")
        is_native = os.path.isfile(arrow_json) and (
            os.path.isfile(key_json)
            or (os.path.isfile(key_1p_json) and os.path.isfile(key_2p_json))
        )
        is_stepmania = _is_stepmania_arrow_skin_dir(skin_dir)
        if not (is_native or is_stepmania):
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
    _写入扫描选项缓存(缓存键, 缓存签名, options)
    return options


def scan_background_options(project_root: str) -> List[BackgroundOption]:
    root = os.path.join(str(project_root or ""), "冷资源", "backimages", "背景图")
    supported = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
    options: List[BackgroundOption] = []
    if not os.path.isdir(root):
        return options
    缓存签名 = _构建背景目录签名(root, supported)
    缓存键 = f"background_options::{os.path.abspath(str(project_root or ''))}"
    缓存命中 = _读取扫描选项缓存(缓存键, 缓存签名)
    if 缓存命中 is not None:
        return [option for option in 缓存命中 if isinstance(option, BackgroundOption)]
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
    _写入扫描选项缓存(缓存键, 缓存签名, options)
    return options


def scan_video_background_options(project_root: str) -> List[VideoBackgroundOption]:
    root = os.path.join(str(project_root or ""), "backmovies", "游戏中")
    supported = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v")
    options: List[VideoBackgroundOption] = []
    if not os.path.isdir(root):
        return options
    缓存签名 = _构建背景目录签名(root, supported)
    缓存键 = f"video_background_options::{os.path.abspath(str(project_root or ''))}"
    缓存命中 = _读取扫描选项缓存(缓存键, 缓存签名)
    if 缓存命中 is not None:
        return [option for option in 缓存命中 if isinstance(option, VideoBackgroundOption)]
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
    _写入扫描选项缓存(缓存键, 缓存签名, options)
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
        if digits:
            for option in option_list:
                if digits == option.skin_id:
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


def read_saved_chart_visual_offset_ms(
    scope_data: Optional[Dict[str, object]] = None,
) -> int:
    data = dict(scope_data or {}) if isinstance(scope_data, dict) else read_game_esc_settings_scope()
    return int(
        clamp_chart_visual_offset_ms(
            data.get(GAME_ESC_SETTINGS_KEY_CHART_VISUAL_OFFSET_MS, 0),
            0,
        )
    )


def read_saved_bpm_scroll_effect(
    scope_data: Optional[Dict[str, object]] = None,
) -> Optional[bool]:
    data = dict(scope_data or {}) if isinstance(scope_data, dict) else read_game_esc_settings_scope()
    if GAME_ESC_SETTINGS_KEY_BPM_SCROLL_EFFECT in data:
        try:
            return bool(data.get(GAME_ESC_SETTINGS_KEY_BPM_SCROLL_EFFECT))
        except Exception:
            return None
    return None
