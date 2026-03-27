from __future__ import annotations

from typing import List, Tuple


def _format_speed_option(value: float) -> str:
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    if "." not in text:
        text = f"{text}.0"
    return text


SELECT_SCROLL_SPEED_OPTIONS: Tuple[str, ...] = tuple(
    _format_speed_option(float(scaled) / 4.0) for scaled in range(4, 29)
)
DEFAULT_SELECT_SCROLL_SPEED_OPTION = "4.0"
DEFAULT_SELECT_SCROLL_SPEED = float(DEFAULT_SELECT_SCROLL_SPEED_OPTION)


def get_select_scroll_speed_options() -> List[str]:
    return list(SELECT_SCROLL_SPEED_OPTIONS)


def get_default_select_scroll_speed_index() -> int:
    try:
        return int(SELECT_SCROLL_SPEED_OPTIONS.index(DEFAULT_SELECT_SCROLL_SPEED_OPTION))
    except Exception:
        return 0


def parse_select_scroll_speed(
    value: object,
    default: float = DEFAULT_SELECT_SCROLL_SPEED,
) -> float:
    text = str(value or "").strip()
    if not text:
        return float(default)
    if text[:1] in ("X", "x", "*"):
        text = text[1:].strip()
    try:
        parsed = float(text)
    except Exception:
        return float(default)
    return max(0.1, float(parsed))


def nearest_select_scroll_speed_option(
    value: object,
    default: str = DEFAULT_SELECT_SCROLL_SPEED_OPTION,
) -> str:
    options = SELECT_SCROLL_SPEED_OPTIONS
    if not options:
        return str(default)
    target = parse_select_scroll_speed(value, float(default))
    return min(options, key=lambda option: abs(float(option) - target))


def get_select_scroll_speed_index(
    value: object,
    default: str = DEFAULT_SELECT_SCROLL_SPEED_OPTION,
) -> int:
    option = nearest_select_scroll_speed_option(value, default=default)
    try:
        return int(SELECT_SCROLL_SPEED_OPTIONS.index(option))
    except Exception:
        return 0


def format_select_scroll_speed(
    value: object,
    prefix: str = "X",
    default: str = DEFAULT_SELECT_SCROLL_SPEED_OPTION,
) -> str:
    option = nearest_select_scroll_speed_option(value, default=default)
    return f"{str(prefix or '')}{option}"
