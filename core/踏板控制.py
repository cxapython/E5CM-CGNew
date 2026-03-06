from __future__ import annotations

from typing import Optional

import pygame


踏板动作_左 = "LEFT"
踏板动作_右 = "RIGHT"
踏板动作_确认 = "CONFIRM"


def 解析踏板动作(事件) -> Optional[str]:
    if 事件 is None or 事件.type != pygame.KEYDOWN:
        return None

    try:
        按键 = int(getattr(事件, "key", -1))
    except Exception:
        return None

    if 按键 in (int(pygame.K_1), int(pygame.K_KP1)):
        return 踏板动作_左
    if 按键 in (int(pygame.K_3), int(pygame.K_KP3)):
        return 踏板动作_右
    if 按键 in (int(pygame.K_5), int(pygame.K_KP5)):
        return 踏板动作_确认
    return None


def 循环切换索引(
    当前索引: Optional[int],
    总数: int,
    步进: int,
    *,
    初始索引: int = 0,
) -> int:
    try:
        总数 = int(总数)
    except Exception:
        总数 = 0
    if 总数 <= 0:
        return 0

    try:
        步进 = int(步进)
    except Exception:
        步进 = 0
    if 步进 == 0:
        步进 = 1

    if 当前索引 is None:
        return max(0, min(int(总数) - 1, int(初始索引)))

    try:
        当前索引 = int(当前索引)
    except Exception:
        当前索引 = int(初始索引)
    return int((当前索引 + 步进) % max(1, 总数))
