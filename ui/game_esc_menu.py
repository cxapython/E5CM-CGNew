from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pygame

from core.game_esc_menu_settings import (
    PROFILE_DOUBLE,
    PROFILE_LABELS,
    PROFILE_SINGLE,
    binding_from_event,
    format_chart_visual_offset_ms,
    iter_profile_slots,
    keycode_to_display_name,
)
from core.select_speed_settings import format_select_scroll_speed
from core.工具 import 获取字体


Color = Tuple[int, int, int]
GridPoint = Tuple[int, int]


@dataclass(frozen=True)
class MenuTab:
    tab_id: str
    title: str
    subtitle: str
    accent: Color
    danger: bool = False


@dataclass
class MenuRow:
    row_id: str
    title: str
    value: str = ""
    description: str = ""
    accent: Color = (0, 239, 251)
    adjustable: bool = True
    preview_kind: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)


class EscMenuController:
    def __init__(self, host: Any):
        self._host = host
        self._open = False
        self._current_tab_id = "chart"
        self._selected_rows: Dict[str, int] = {
            "chart": 0,
            "background": 0,
            "game": 0,
        }
        self._binding_profile_id = PROFILE_SINGLE
        self._binding_focus_id = "profile"
        self._waiting_binding: Optional[Tuple[str, str]] = None
        self._hover_tab_id: Optional[str] = None
        self._hover_row_id: Optional[str] = None
        self._hover_binding_id: Optional[str] = None
        self._tab_rects: Dict[str, pygame.Rect] = {}
        self._row_hitboxes: Dict[str, Dict[str, pygame.Rect]] = {}
        self._binding_hitboxes: Dict[str, pygame.Rect] = {}
        self._profile_prev_rect = pygame.Rect(0, 0, 0, 0)
        self._profile_next_rect = pygame.Rect(0, 0, 0, 0)
        self._profile_label_rect = pygame.Rect(0, 0, 0, 0)
        self._danger_button_rect = pygame.Rect(0, 0, 0, 0)
        self._font_cache: Dict[Tuple[int, bool, bool], pygame.font.Font] = {}

    def open(self):
        self._open = True
        self._hover_tab_id = None
        self._hover_row_id = None
        self._hover_binding_id = None
        self._waiting_binding = None
        self._binding_profile_id = (
            PROFILE_DOUBLE
            if bool(getattr(self._host, "_是否双踏板模式", False))
            else PROFILE_SINGLE
        )
        self._binding_focus_id = "profile"
        tab_ids = [tab.tab_id for tab in self._tabs()]
        if self._current_tab_id not in tab_ids:
            self._current_tab_id = tab_ids[0] if tab_ids else "chart"

    def close(self):
        self._open = False
        self._hover_tab_id = None
        self._hover_row_id = None
        self._hover_binding_id = None
        self._waiting_binding = None
        self._tab_rects = {}
        self._row_hitboxes = {}
        self._binding_hitboxes = {}
        self._profile_prev_rect = pygame.Rect(0, 0, 0, 0)
        self._profile_next_rect = pygame.Rect(0, 0, 0, 0)
        self._profile_label_rect = pygame.Rect(0, 0, 0, 0)
        self._danger_button_rect = pygame.Rect(0, 0, 0, 0)

    def is_open(self) -> bool:
        return bool(self._open)

    def handle_event(self, event: pygame.event.Event) -> Optional[dict]:
        if not self._open:
            return None
        if self._waiting_binding is not None:
            return self._handle_binding_capture(event)
        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)
        if event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and int(getattr(event, "button", 0)) == 1:
            return self._handle_left_click(event)
        return None

    def draw(self, screen: pygame.Surface):
        if not self._open or not isinstance(screen, pygame.Surface):
            return
        self._tab_rects = {}
        self._row_hitboxes = {}
        self._binding_hitboxes = {}
        self._profile_prev_rect = pygame.Rect(0, 0, 0, 0)
        self._profile_next_rect = pygame.Rect(0, 0, 0, 0)
        self._profile_label_rect = pygame.Rect(0, 0, 0, 0)
        self._danger_button_rect = pygame.Rect(0, 0, 0, 0)
        self._draw_root(screen)

    def _tabs(self) -> List[MenuTab]:
        tabs = [
            MenuTab("chart", "谱面设置", "CHART", (0, 239, 251)),
            MenuTab("background", "背景设置", "BACKGROUND", (110, 197, 255)),
            MenuTab("game", "游戏设置", "SYSTEM", (0, 239, 251)),
            MenuTab("bindings", "键位设置", "BINDINGS", (104, 208, 255)),
        ]
        tabs.append(
            MenuTab("reload_song", "重新载入歌曲", "RELOAD SONG", (255, 198, 104), True)
        )
        if self._supports_exit_match():
            tabs.append(
                MenuTab("exit_match", "退出本局", "RETURN TO SELECT", (255, 164, 72), True)
            )
        tabs.append(
            MenuTab("exit_desktop", "退出到桌面", "EXIT TO DESKTOP", (255, 72, 72), True)
        )
        return tabs

    def _supports_exit_match(self) -> bool:
        checker = getattr(self._host, "_esc_menu_should_show_exit_match", None)
        if callable(checker):
            try:
                return bool(checker())
            except Exception:
                return False
        return False

    def _rows_for_tab(self, tab_id: Optional[str] = None) -> List[MenuRow]:
        current_tab = str(tab_id or self._current_tab_id)
        if current_tab == "chart":
            return self._chart_rows()
        if current_tab == "background":
            return self._background_rows()
        if current_tab == "game":
            return self._game_rows()
        return []

    def _chart_rows(self) -> List[MenuRow]:
        host = self._host
        visual_offset_text = format_chart_visual_offset_ms(
            getattr(host, "_谱面视觉偏移毫秒", 0)
        )
        formatter = getattr(host, "_取谱面偏移菜单文本", None)
        if callable(formatter):
            try:
                visual_offset_text = str(formatter())
            except Exception:
                visual_offset_text = format_chart_visual_offset_ms(
                    getattr(host, "_谱面视觉偏移毫秒", 0)
                )
        return [
            MenuRow(
                "scroll_speed",
                "调速",
                format_select_scroll_speed(
                    getattr(host, "_卷轴速度倍率", 4.0),
                    prefix="X",
                ),
                "调整谱面滚动速度",
            ),
            MenuRow(
                "bpm_scroll_effect",
                "变速效果",
                "开启" if bool(getattr(host, "_BPM变速效果开启", False)) else "关闭",
                "常速歌额外加瞬间加速；谱面自带 BPMS 变速始终生效",
            ),
            MenuRow(
                "chart_visual_offset",
                "谱面偏移",
                str(visual_offset_text),
                "按 10ms 调整视觉偏移，不影响判定",
            ),
            MenuRow("hidden", "隐藏", str(getattr(host, "_隐藏模式", "关闭") or "关闭"), "切换隐藏方式"),
            MenuRow("track", "轨迹", str(getattr(host, "_轨迹模式", "正常") or "正常"), "切换轨迹动画"),
            MenuRow("direction", "方向", str(getattr(host, "_方向模式", "关闭") or "关闭"), "切换谱面方向"),
            MenuRow("size", "大小", str(host._取当前大小选项文本()), "调整箭头尺寸"),
            MenuRow(
                "arrow_skin",
                "箭头",
                str(self._resolve_arrow_label()),
                "切换箭头皮肤并同步游戏内渲染",
                preview_kind="arrow",
            ),
        ]

    def _background_rows(self) -> List[MenuRow]:
        host = self._host
        return [
            MenuRow(
                "background_mode",
                "背景",
                str(host._取背景渲染模式()),
                "切换图片 / 视频 / 动态背景",
                preview_kind="current",
            ),
            MenuRow(
                "image_slideshow_mode",
                "每个关卡自动换下一张背景图",
                "开启" if bool(getattr(host, "_图片幻灯片模式开启", True)) else "关闭",
                "仅图片背景生效；关闭后使用当前选择的图片背景",
                (104, 208, 255),
            ),
            self._current_background_detail_row(),
            MenuRow(
                "brightness",
                "背景亮度切换",
                str(host._取背景亮度菜单文本()),
                "调整背景亮度蒙版",
                preview_kind="current",
            ),
        ]

    def _current_background_detail_row(self) -> MenuRow:
        host = self._host
        mode = self._resolve_preview_kind("current")
        if mode == "dynamic":
            options = list(getattr(host, "_菜单动态背景选项", []) or [])
            return MenuRow(
                "background_detail",
                "动态背景",
                str(getattr(host, "_动态背景模式", "关闭") or "关闭"),
                "切换动态背景样式",
                (0, 239, 251),
                bool(options),
                "dynamic",
                {"adjust_row_id": "dynamic_background"},
            )
        if mode == "video":
            options = list(getattr(host, "_菜单视频背景选项", []) or [])
            return MenuRow(
                "background_detail",
                "视频背景",
                self._resolve_video_label(),
                "扫描 backmovies\\游戏中 后切换单个 mp4 并循环预览",
                (126, 176, 225),
                bool(options),
                "video",
                {"adjust_row_id": "video_background"},
            )
        options = list(getattr(host, "_菜单背景选项", []) or [])
        return MenuRow(
            "background_detail",
            "图片背景",
            self._resolve_background_label(),
            "切换图片 / GIF 背景",
            (0, 239, 251),
            bool(options),
            "image",
            {"adjust_row_id": "image_background"},
        )

    def _game_rows(self) -> List[MenuRow]:
        host = self._host
        return [
            MenuRow(
                "performance_mode",
                "极简性能模式",
                "开启" if bool(getattr(host, "_性能模式", False)) else "关闭",
                "关闭重型效果，优先保证帧率",
            ),
            MenuRow(
                "autoplay",
                "自动播放",
                "开启" if bool(getattr(host, "_是否自动模式", False)) else "关闭",
                "切换自动判定 / 演示模式",
            ),
        ]

    def _resolve_background_label(self) -> str:
        current_file = str(getattr(self._host, "_载荷", {}).get("背景文件名", "") or "")
        for option in list(getattr(self._host, "_菜单背景选项", []) or []):
            if str(getattr(option, "file_name", "")) == current_file:
                return str(getattr(option, "label", "") or current_file or "未选择")
        return current_file or "未选择"

    def _resolve_arrow_label(self) -> str:
        current_file = str(getattr(self._host, "_载荷", {}).get("箭头文件名", "") or "")
        for option in list(getattr(self._host, "_菜单箭头选项", []) or []):
            if str(getattr(option, "file_name", "")) == current_file:
                return str(getattr(option, "label", "") or current_file or "默认")
        return current_file or "默认"

    def _resolve_video_label(self) -> str:
        current_option = getattr(self._host, "_当前视频背景选项", None)
        if current_option is not None:
            label = str(getattr(current_option, "label", "") or "").strip()
            if label:
                return label
        current_file = str(getattr(self._host, "_载荷", {}).get("视频背景文件名", "") or "")
        for option in list(getattr(self._host, "_菜单视频背景选项", []) or []):
            if str(getattr(option, "file_name", "")) == current_file:
                return str(getattr(option, "label", "") or current_file or "未选择")
        return current_file or "未选择"

    def _handle_binding_capture(self, event: pygame.event.Event) -> Optional[dict]:
        if event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event)
            return None
        if event.type == pygame.KEYDOWN:
            if int(getattr(event, "key", 0)) == pygame.K_ESCAPE:
                self._waiting_binding = None
                self._feedback("已取消键位修改")
                return None
        if event.type in (pygame.KEYDOWN, pygame.JOYBUTTONDOWN):
            binding = binding_from_event(event)
            waiting = self._waiting_binding
            self._waiting_binding = None
            if waiting is None or binding is None:
                return None
            profile_id, slot_id = waiting
            applier = getattr(self._host, "_esc_menu_apply_binding", None)
            if callable(applier):
                try:
                    applier(str(profile_id), str(slot_id), binding)
                except Exception:
                    pass
            self._binding_focus_id = str(slot_id)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and int(getattr(event, "button", 0)) == 1:
            pos = getattr(event, "pos", None)
            if pos and (
                self._profile_label_rect.collidepoint(pos)
                or self._profile_prev_rect.collidepoint(pos)
                or self._profile_next_rect.collidepoint(pos)
            ):
                self._waiting_binding = None
                return self._handle_left_click(event)
            for slot_id, rect in self._binding_hitboxes.items():
                if rect.collidepoint(pos):
                    self._waiting_binding = None
                    self._binding_focus_id = str(slot_id)
                    self._begin_binding_capture(str(slot_id))
                    return None
            self._waiting_binding = None
            self._feedback("已取消键位修改")
        return None

    def _handle_keydown(self, event: pygame.event.Event) -> Optional[dict]:
        key = int(getattr(event, "key", 0))
        mod = int(getattr(event, "mod", 0))

        if key == pygame.K_ESCAPE:
            return {"close_menu": True}

        if key == pygame.K_TAB:
            self._change_tab(-1 if (mod & pygame.KMOD_SHIFT) else 1)
            return None
        if key == pygame.K_q:
            self._change_tab(-1)
            return None
        if key == pygame.K_e:
            self._change_tab(1)
            return None

        if self._current_tab_id in ("chart", "background", "game"):
            if key in (pygame.K_w, pygame.K_UP):
                self._move_list_selection(-1)
                return None
            if key in (pygame.K_s, pygame.K_DOWN):
                self._move_list_selection(1)
                return None
            if key in (pygame.K_a, pygame.K_LEFT):
                self._apply_active_row(-1)
                return None
            if key in (pygame.K_d, pygame.K_RIGHT):
                self._apply_active_row(1)
                return None
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._apply_active_row(1)
                return None
            return None

        if self._current_tab_id == "bindings":
            return self._handle_bindings_keydown(event)

        if self._current_tab_id in ("reload_song", "exit_match", "exit_desktop"):
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._confirm_danger_action()
            return None

        return None

    def _handle_bindings_keydown(self, event: pygame.event.Event) -> Optional[dict]:
        key = int(getattr(event, "key", 0))
        if self._binding_focus_id == "profile":
            if key in (pygame.K_a, pygame.K_LEFT):
                self._toggle_binding_profile(-1)
                return None
            if key in (pygame.K_d, pygame.K_RIGHT):
                self._toggle_binding_profile(1)
                return None
            if key in (pygame.K_s, pygame.K_DOWN):
                self._binding_focus_id = self._binding_default_focus()
                return None
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._toggle_binding_profile(1)
                return None
            return None

        if key in (pygame.K_w, pygame.K_UP):
            self._move_binding_focus(0, -1)
            return None
        if key in (pygame.K_s, pygame.K_DOWN):
            self._move_binding_focus(0, 1)
            return None
        if key in (pygame.K_a, pygame.K_LEFT):
            self._move_binding_focus(-1, 0)
            return None
        if key in (pygame.K_d, pygame.K_RIGHT):
            self._move_binding_focus(1, 0)
            return None
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._begin_binding_capture(self._binding_focus_id)
            return None
        return None

    def _handle_mouse_motion(self, event: pygame.event.Event):
        pos = getattr(event, "pos", None)
        self._hover_tab_id = None
        self._hover_row_id = None
        self._hover_binding_id = None
        if pos is None:
            return
        for tab_id, rect in self._tab_rects.items():
            if rect.collidepoint(pos):
                self._hover_tab_id = str(tab_id)
                break
        for hitboxes in self._row_hitboxes.values():
            for row_key, rect in hitboxes.items():
                if rect.collidepoint(pos):
                    self._hover_row_id = str(row_key)
                    break
            if self._hover_row_id:
                break
        for binding_id, rect in self._binding_hitboxes.items():
            if rect.collidepoint(pos):
                self._hover_binding_id = str(binding_id)
                break

    def _handle_left_click(self, event: pygame.event.Event) -> Optional[dict]:
        pos = getattr(event, "pos", None)
        if pos is None:
            return None

        for tab_id, rect in self._tab_rects.items():
            if rect.collidepoint(pos):
                self._change_tab(str(tab_id))
                return None

        if self._current_tab_id == "bindings":
            if self._profile_prev_rect.collidepoint(pos):
                self._toggle_binding_profile(-1)
                return None
            if self._profile_next_rect.collidepoint(pos):
                self._toggle_binding_profile(1)
                return None
            if self._profile_label_rect.collidepoint(pos):
                self._binding_focus_id = "profile"
                return None
            for slot_id, rect in self._binding_hitboxes.items():
                if rect.collidepoint(pos):
                    self._binding_focus_id = str(slot_id)
                    self._begin_binding_capture(str(slot_id))
                    return None
            return None

        if self._current_tab_id in ("reload_song", "exit_match", "exit_desktop"):
            if self._danger_button_rect.collidepoint(pos):
                return self._confirm_danger_action()
            return None

        row_hitboxes = self._row_hitboxes.get(self._current_tab_id, {})
        for row in self._rows_for_tab():
            body_rect = row_hitboxes.get(f"{row.row_id}:body")
            if body_rect is not None and body_rect.collidepoint(pos):
                self._set_active_row(str(row.row_id))
                return None
            if row.adjustable:
                left_rect = row_hitboxes.get(f"{row.row_id}:left")
                if left_rect is not None and left_rect.collidepoint(pos):
                    self._set_active_row(str(row.row_id))
                    self._apply_row(str(row.row_id), -1)
                    return None
                right_rect = row_hitboxes.get(f"{row.row_id}:right")
                if right_rect is not None and right_rect.collidepoint(pos):
                    self._set_active_row(str(row.row_id))
                    self._apply_row(str(row.row_id), 1)
                    return None
        return None

    def _change_tab(self, target: object):
        tab_ids = [tab.tab_id for tab in self._tabs()]
        if not tab_ids:
            return
        if isinstance(target, str):
            if target not in tab_ids:
                return
            self._current_tab_id = str(target)
        else:
            step = int(target or 0)
            if step == 0:
                return
            try:
                index = tab_ids.index(self._current_tab_id)
            except Exception:
                index = 0
            self._current_tab_id = str(tab_ids[(index + step) % len(tab_ids)])
        self._waiting_binding = None
        if self._current_tab_id == "bindings":
            self._binding_focus_id = "profile"

    def _move_list_selection(self, step: int):
        rows = self._rows_for_tab()
        if not rows:
            return
        current_index = int(self._selected_rows.get(self._current_tab_id, 0) or 0)
        self._selected_rows[self._current_tab_id] = (current_index + int(step)) % len(rows)

    def _active_row(self) -> Optional[MenuRow]:
        rows = self._rows_for_tab()
        if not rows:
            return None
        index = int(self._selected_rows.get(self._current_tab_id, 0) or 0)
        return rows[max(0, min(len(rows) - 1, index))]

    def _set_active_row(self, row_id: str):
        rows = self._rows_for_tab()
        for index, row in enumerate(rows):
            if str(row.row_id) == str(row_id):
                self._selected_rows[self._current_tab_id] = int(index)
                return

    def _apply_active_row(self, step: int):
        row = self._active_row()
        if row is not None:
            self._apply_row(str(row.row_id), int(step))

    def _apply_row(self, row_id: str, step: int):
        row = next((item for item in self._rows_for_tab() if item.row_id == row_id), None)
        if row is None or not bool(row.adjustable):
            return
        target_row_id = str(
            (
                dict(row.meta).get("adjust_row_id", row_id)
                if isinstance(row.meta, dict)
                else row_id
            )
            or row_id
        )
        adjust = getattr(self._host, "_esc_menu_adjust", None)
        if callable(adjust):
            try:
                adjust(str(target_row_id), int(step))
            except Exception:
                pass

    def _toggle_binding_profile(self, step: int):
        profiles = [PROFILE_SINGLE, PROFILE_DOUBLE]
        try:
            index = profiles.index(self._binding_profile_id)
        except Exception:
            index = 0
        self._binding_profile_id = str(profiles[(index + int(step)) % len(profiles)])
        if self._binding_focus_id != "profile" and self._binding_focus_id not in {
            slot_id for slot_id, _ in self._binding_slot_order()
        }:
            self._binding_focus_id = self._binding_default_focus()

    def _binding_slot_order(self, profile_id: Optional[str] = None) -> List[Tuple[str, str]]:
        return list(iter_profile_slots(str(profile_id or self._binding_profile_id)))

    def _binding_default_focus(self) -> str:
        return "左区中间" if self._binding_profile_id == PROFILE_DOUBLE else "中间"

    def _binding_grid_points(self, profile_id: Optional[str] = None) -> Dict[str, GridPoint]:
        active_profile = str(profile_id or self._binding_profile_id)
        if active_profile == PROFILE_DOUBLE:
            return {
                "左区左上": (0, 0),
                "左区右上": (2, 0),
                "左区中间": (1, 1),
                "左区左下": (0, 2),
                "左区右下": (2, 2),
                "右区左上": (4, 0),
                "右区右上": (6, 0),
                "右区中间": (5, 1),
                "右区左下": (4, 2),
                "右区右下": (6, 2),
            }
        return {
            "左上": (0, 0),
            "右上": (2, 0),
            "中间": (1, 1),
            "左下": (0, 2),
            "右下": (2, 2),
        }

    def _binding_positions(
        self,
        canvas_rect: pygame.Rect,
        profile_id: Optional[str] = None,
    ) -> Dict[str, pygame.Rect]:
        active_profile = str(profile_id or self._binding_profile_id)
        positions: Dict[str, pygame.Rect] = {}

        def _group_slots(group_rect: pygame.Rect, prefix: str = "") -> Dict[str, pygame.Rect]:
            cell_gap = max(16, int(min(group_rect.w, group_rect.h) * 0.06))
            cell_w = max(90, int((group_rect.w - cell_gap * 2) / 3))
            cell_h = max(72, int((group_rect.h - cell_gap * 2) / 3))
            card_w = max(88, int(cell_w * 0.94))
            card_h = max(64, int(cell_h * 0.88))
            layout = {
                "左上": (0, 0),
                "右上": (2, 0),
                "中间": (1, 1),
                "左下": (0, 2),
                "右下": (2, 2),
            }
            result: Dict[str, pygame.Rect] = {}
            for local_slot, (column, row) in layout.items():
                left = int(group_rect.x + column * (cell_w + cell_gap) + (cell_w - card_w) * 0.5)
                top = int(group_rect.y + row * (cell_h + cell_gap) + (cell_h - card_h) * 0.5)
                slot_id = f"{prefix}{local_slot}" if prefix else local_slot
                result[slot_id] = pygame.Rect(left, top, card_w, card_h)
            return result

        if active_profile == PROFILE_DOUBLE:
            group_gap = max(28, int(canvas_rect.w * 0.035))
            group_w = max(280, int(min((canvas_rect.w - group_gap) * 0.5, canvas_rect.h * 0.9)))
            group_h = int(min(canvas_rect.h * 0.78, group_w * 0.62))
            total_w = group_w * 2 + group_gap
            start_x = int(canvas_rect.centerx - total_w * 0.5)
            start_y = int(canvas_rect.centery - group_h * 0.5)
            positions.update(_group_slots(pygame.Rect(start_x, start_y, group_w, group_h), "左区"))
            positions.update(
                _group_slots(
                    pygame.Rect(start_x + group_w + group_gap, start_y, group_w, group_h),
                    "右区",
                )
            )
            return positions

        group_w = max(360, int(min(canvas_rect.w * 0.74, canvas_rect.h * 1.12)))
        group_h = int(min(canvas_rect.h * 0.8, group_w * 0.62))
        positions.update(
            _group_slots(
                pygame.Rect(
                    int(canvas_rect.centerx - group_w * 0.5),
                    int(canvas_rect.centery - group_h * 0.5),
                    group_w,
                    group_h,
                )
            )
        )
        return positions

    def _move_binding_focus(self, dx: int, dy: int):
        if self._binding_focus_id == "profile":
            if dy > 0:
                self._binding_focus_id = self._binding_default_focus()
            return

        points = self._binding_grid_points()
        current = points.get(self._binding_focus_id)
        if current is None:
            self._binding_focus_id = self._binding_default_focus()
            return
        if dy < 0 and current[1] == 0:
            self._binding_focus_id = "profile"
            return

        candidates: List[Tuple[int, int, str]] = []
        for slot_id, point in points.items():
            if slot_id == self._binding_focus_id:
                continue
            delta_x = int(point[0] - current[0])
            delta_y = int(point[1] - current[1])
            if dx < 0 and delta_x >= 0:
                continue
            if dx > 0 and delta_x <= 0:
                continue
            if dy < 0 and delta_y >= 0:
                continue
            if dy > 0 and delta_y <= 0:
                continue
            primary = abs(delta_x) if dx else abs(delta_y)
            secondary = abs(delta_y) if dx else abs(delta_x)
            candidates.append((primary, secondary, str(slot_id)))

        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1], item[2]))
            self._binding_focus_id = str(candidates[0][2])

    def _begin_binding_capture(self, slot_id: str):
        if not slot_id:
            return
        self._waiting_binding = (str(self._binding_profile_id), str(slot_id))
        self._binding_focus_id = str(slot_id)
        label = dict(self._binding_display_labels()).get(str(slot_id), str(slot_id))
        profile_text = PROFILE_LABELS.get(str(self._binding_profile_id), str(self._binding_profile_id))
        self._feedback(f"{profile_text} {label}：等待按键输入")

    def _binding_values(self, profile_id: Optional[str] = None) -> Dict[str, str]:
        active_profile = str(profile_id or self._binding_profile_id)
        values = (
            dict(getattr(self._host, "_菜单双踏板键位", {}) or {})
            if active_profile == PROFILE_DOUBLE
            else dict(getattr(self._host, "_菜单单踏板键位", {}) or {})
        )
        return {
            slot_id: keycode_to_display_name(values.get(slot_id))
            for slot_id, _label in self._binding_slot_order(active_profile)
        }

    def _binding_display_labels(self, profile_id: Optional[str] = None) -> Dict[str, str]:
        return {slot_id: label for slot_id, label in self._binding_slot_order(profile_id)}

    def _confirm_danger_action(self) -> Optional[dict]:
        action = ""
        if self._current_tab_id == "reload_song":
            action = "reload_song"
        elif self._current_tab_id == "exit_match":
            action = "match"
        if self._current_tab_id == "exit_desktop":
            action = "desktop"
        if not action:
            return None
        confirm = getattr(self._host, "_esc_menu_confirm_exit", None)
        if callable(confirm):
            try:
                return confirm(str(action))
            except Exception:
                return None
        return None

    def _feedback(self, text: str):
        setter = getattr(self._host, "_设置操作反馈", None)
        if callable(setter):
            try:
                setter(str(text or ""))
            except Exception:
                pass

    def _draw_root(self, screen: pygame.Surface):
        width, height = screen.get_size()
        mouse_pos = pygame.mouse.get_pos()
        margin = max(28, int(min(width, height) * 0.03))
        gap = max(18, int(width * 0.012))
        nav_width = max(270, min(360, int(width * 0.22)))
        nav_rect = pygame.Rect(margin, margin, nav_width, max(200, height - margin * 2))
        content_rect = pygame.Rect(
            nav_rect.right + gap,
            margin,
            max(300, width - nav_rect.width - gap - margin * 2),
            nav_rect.height,
        )

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((2, 8, 16, 210))
        screen.blit(overlay, (0, 0))
        vignette = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0, 0, 0, 70), vignette.get_rect(), width=max(80, int(width * 0.08)))
        screen.blit(vignette, (0, 0))

        self._draw_nav(screen, nav_rect, mouse_pos)
        self._draw_content(screen, content_rect, mouse_pos)

    def _draw_nav(self, screen: pygame.Surface, rect: pygame.Rect, mouse_pos: Tuple[int, int]):
        self._draw_panel(screen, rect, (9, 15, 28), (54, 87, 138), 22, 2)
        inner = rect.inflate(-28, -28)
        screen.blit(self._font(36, True).render("ESC MENU", True, (238, 246, 255)), (inner.x, inner.y))
        screen.blit(
            self._font(18, False).render("FULL SCENE SETTING PANEL", True, (102, 132, 182)),
            (inner.x, inner.y + 44),
        )

        tab_top = inner.y + 94
        tab_height = max(72, int(rect.h * 0.09))
        self._tab_rects = {}
        for index, tab in enumerate(self._tabs()):
            tab_rect = pygame.Rect(inner.x, tab_top + index * (tab_height + 12), inner.w, tab_height)
            self._tab_rects[tab.tab_id] = tab_rect
            hovered = tab_rect.collidepoint(mouse_pos)
            active = str(tab.tab_id) == str(self._current_tab_id)
            accent = tuple(int(v) for v in tab.accent)
            fill_color = (18, 29, 46)
            border_color = (63, 93, 138)
            subtitle_color = (130, 151, 184)
            if tab.danger and hovered:
                fill_color = (44, 16, 18) if tab.tab_id == "exit_desktop" else (46, 28, 16)
                border_color = (255, 72, 72) if tab.tab_id == "exit_desktop" else accent
                subtitle_color = (255, 170, 170) if tab.tab_id == "exit_desktop" else (255, 206, 166)
            elif active:
                fill_color = tuple(min(255, int(v * 0.22) + 12) for v in accent)
                border_color = accent
                subtitle_color = tuple(min(255, int(v * 0.78) + 40) for v in accent)
            elif hovered:
                fill_color = tuple(min(255, int(v * 0.12) + 18) for v in accent)
                border_color = tuple(min(255, int(v * 0.58) + 58) for v in accent)
            self._draw_panel(screen, tab_rect, fill_color, border_color, 16, 2)
            if active:
                pygame.draw.rect(
                    screen,
                    accent,
                    pygame.Rect(tab_rect.x, tab_rect.y + 14, 5, max(18, tab_rect.h - 28)),
                    border_radius=4,
                )
            screen.blit(self._font(18, True).render(tab.title, True, (235, 244, 255)), (tab_rect.x + 18, tab_rect.y + 14))
            screen.blit(self._font(15, False).render(tab.subtitle, True, subtitle_color), (tab_rect.x + 18, tab_rect.y + 40))

    def _draw_content(self, screen: pygame.Surface, rect: pygame.Rect, mouse_pos: Tuple[int, int]):
        current_tab = self._current_tab()
        if current_tab is None:
            return
        self._draw_panel(screen, rect, (9, 14, 26), (42, 71, 114), 22, 2)
        inner = rect.inflate(-26, -24)
        screen.blit(self._font(34, True).render(current_tab.title, True, (241, 247, 255)), (inner.x, inner.y))
        accent = current_tab.accent if not current_tab.danger else (
            (255, 120, 120) if current_tab.tab_id == "exit_desktop" else current_tab.accent
        )
        screen.blit(self._font(22, False).render(current_tab.subtitle, True, accent), (inner.x, inner.y + 42))
        divider_y = inner.y + 84
        pygame.draw.line(screen, (33, 54, 86), (inner.x, divider_y), (inner.right, divider_y), 1)

        body_rect = pygame.Rect(inner.x, divider_y + 18, inner.w, max(200, inner.bottom - divider_y - 18))
        if current_tab.tab_id == "chart":
            self._draw_chart_tab(screen, body_rect, mouse_pos)
        elif current_tab.tab_id == "background":
            self._draw_background_tab(screen, body_rect, mouse_pos)
        elif current_tab.tab_id == "game":
            self._draw_game_tab(screen, body_rect, mouse_pos)
        elif current_tab.tab_id == "bindings":
            self._draw_bindings_tab(screen, body_rect, mouse_pos)
        else:
            self._draw_exit_tab(screen, body_rect, current_tab, mouse_pos)

    def _current_tab(self) -> Optional[MenuTab]:
        for tab in self._tabs():
            if str(tab.tab_id) == str(self._current_tab_id):
                return tab
        return None

    def _draw_chart_tab(self, screen: pygame.Surface, rect: pygame.Rect, mouse_pos: Tuple[int, int]):
        list_width = max(360, int(rect.w * 0.47))
        gap = max(20, int(rect.w * 0.018))
        list_rect = pygame.Rect(rect.x, rect.y, list_width, rect.h)
        preview_rect = pygame.Rect(list_rect.right + gap, rect.y, rect.w - list_width - gap, rect.h)
        self._draw_settings_list(screen, list_rect, self._rows_for_tab("chart"), mouse_pos)
        row = self._active_row()
        title = "箭头预览"
        description = "箭头切换会立即刷新预览，并同步到对局中的实际渲染。"
        if row is not None and row.row_id != "arrow_skin":
            title = f"{row.title}说明"
            description = str(row.description or description)
        self._draw_preview_shell(screen, preview_rect, title, description, "arrow")

    def _draw_background_tab(self, screen: pygame.Surface, rect: pygame.Rect, mouse_pos: Tuple[int, int]):
        list_width = max(380, int(rect.w * 0.43))
        gap = max(20, int(rect.w * 0.018))
        list_rect = pygame.Rect(rect.x, rect.y, list_width, rect.h)
        preview_rect = pygame.Rect(list_rect.right + gap, rect.y, rect.w - list_width - gap, rect.h)
        self._draw_settings_list(screen, list_rect, self._rows_for_tab("background"), mouse_pos)
        row = self._active_row()
        title = "统一背景预览"
        description = "当前选中的背景类型会占用右侧唯一大画布，预览尽量贴近对局实际效果。"
        preview_kind = "current"
        if row is not None:
            preview_kind = str(row.preview_kind or "current")
            title = {
                "current": "当前背景预览",
                "dynamic": "动态背景预览",
                "image": "图片背景预览",
                "video": "视频背景预览",
            }.get(preview_kind, title)
            description = str(row.description or description)
        self._draw_preview_shell(screen, preview_rect, title, description, preview_kind)

    def _draw_game_tab(self, screen: pygame.Surface, rect: pygame.Rect, mouse_pos: Tuple[int, int]):
        list_width = max(360, int(rect.w * 0.47))
        gap = max(20, int(rect.w * 0.018))
        list_rect = pygame.Rect(rect.x, rect.y, list_width, rect.h)
        info_rect = pygame.Rect(list_rect.right + gap, rect.y, rect.w - list_width - gap, rect.h)
        self._draw_settings_list(screen, list_rect, self._rows_for_tab("game"), mouse_pos)
        status_lines = [
            f"极简性能模式：{'开启' if bool(getattr(self._host, '_性能模式', False)) else '关闭'}",
            f"自动播放：{'开启' if bool(getattr(self._host, '_是否自动模式', False)) else '关闭'}",
            f"谱面偏移：{format_chart_visual_offset_ms(getattr(self._host, '_谱面视觉偏移毫秒', 0))}",
            f"当前对局模式：{'双踏板' if bool(getattr(self._host, '_是否双踏板模式', False)) else '单踏板'}",
            "所有修改都会立即落到运行逻辑，并持久化到 ESC 菜单配置存储。",
        ]
        self._draw_preview_shell(screen, info_rect, "系统状态", "\n".join(status_lines), "")

    def _draw_bindings_tab(self, screen: pygame.Surface, rect: pygame.Rect, mouse_pos: Tuple[int, int]):
        selector_height = max(110, int(rect.h * 0.16))
        gap = max(18, int(rect.h * 0.02))
        selector_rect = pygame.Rect(rect.x, rect.y, rect.w, selector_height)
        canvas_rect = pygame.Rect(rect.x, selector_rect.bottom + gap, rect.w, rect.h - selector_height - gap)
        self._draw_binding_selector(screen, selector_rect, mouse_pos)
        self._draw_binding_canvas(screen, canvas_rect, mouse_pos)

    def _draw_exit_tab(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        tab: MenuTab,
        mouse_pos: Tuple[int, int],
    ):
        fill = (25, 14, 16) if tab.tab_id == "exit_desktop" else (25, 18, 12)
        border = (255, 86, 86) if tab.tab_id == "exit_desktop" else tab.accent
        self._draw_panel(screen, rect, fill, border, 24, 2)
        inner = rect.inflate(-34, -30)
        if tab.tab_id == "reload_song":
            question = "你确定要重新载入歌曲吗？"
            body = "会立即重开当前谱面并重新开始播放。"
        elif tab.tab_id == "exit_match":
            question = "你确定要退出本局吗？"
            body = "退出本局会直接返回选歌界面。"
        else:
            question = "你确定要退出到桌面吗？"
            body = "退出到桌面会关闭整个程序。"
        screen.blit(self._font(34, True).render(question, True, (245, 248, 255)), (inner.x, inner.y))
        self._draw_text_block(
            screen,
            f"{body}\n如果只是继续游戏，按 ESC 关闭菜单即可。",
            pygame.Rect(inner.x, inner.y + 56, inner.w, 110),
            self._font(20, False),
            (214, 223, 236),
            8,
        )

        button_width = max(280, int(inner.w * 0.32))
        self._danger_button_rect = pygame.Rect(inner.x, inner.bottom - 72, button_width, 72)
        hovered = self._danger_button_rect.collidepoint(mouse_pos)
        if tab.tab_id == "exit_desktop":
            button_fill = (145, 30, 30) if hovered else (96, 24, 24)
            button_border = (255, 88, 88)
        else:
            button_fill = (112, 66, 28) if hovered else (85, 52, 24)
            button_border = tab.accent
        self._draw_panel(screen, self._danger_button_rect, button_fill, button_border, 18, 2)
        if tab.tab_id == "reload_song":
            label = "确认重新载入歌曲"
        elif tab.tab_id == "exit_match":
            label = "确认退出本局"
        else:
            label = "确认退出到桌面"
        screen.blit(self._font(20, True).render(label, True, (255, 247, 240)), (self._danger_button_rect.x + 20, self._danger_button_rect.y + 14))
        screen.blit(self._font(18, False).render("ENTER 或点击此按钮执行", True, (255, 218, 206)), (self._danger_button_rect.x + 20, self._danger_button_rect.y + 40))

    def _draw_settings_list(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        rows: List[MenuRow],
        mouse_pos: Tuple[int, int],
    ):
        self._draw_panel(screen, rect, (8, 14, 24), (37, 62, 97), 20, 2)
        inner = rect.inflate(-16, -18)
        row_gap = 10
        row_height = min(92, max(72, int((inner.h - row_gap * max(0, len(rows) - 1)) / max(1, len(rows)))))
        selected_index = int(self._selected_rows.get(self._current_tab_id, 0) or 0)
        hitboxes: Dict[str, pygame.Rect] = {}

        for index, row in enumerate(rows):
            row_rect = pygame.Rect(inner.x, inner.y + index * (row_height + row_gap), inner.w, row_height)
            is_selected = index == selected_index
            is_hovered = row_rect.collidepoint(mouse_pos)
            accent = tuple(int(v) for v in row.accent)
            fill_color = (17, 24, 37)
            border_color = (56, 84, 128)
            if is_selected:
                fill_color = tuple(min(255, int(v * 0.18) + 16) for v in accent)
                border_color = accent
            elif is_hovered:
                fill_color = tuple(min(255, int(v * 0.1) + 18) for v in accent)
                border_color = tuple(min(255, int(v * 0.54) + 52) for v in accent)
            self._draw_panel(screen, row_rect, fill_color, border_color, 14, 2)

            title_font = self._font(19, False)
            body_font = self._font(16, False)
            value_font = self._font(18, False)
            button_side = max(28, min(40, int(row_rect.h * 0.5))) if row.adjustable else 0
            button_gap = 8 if row.adjustable else 0
            buttons_width = (button_side * 2 + button_gap + 16) if row.adjustable else 0
            value_max_w = max(90, row_rect.w - buttons_width - 220)
            value_text = self._truncate_text(str(row.value or ""), value_font, value_max_w)
            value_surface = value_font.render(value_text, True, (136, 217, 255))
            value_x = row_rect.right - 18 - buttons_width - value_surface.get_width()
            screen.blit(title_font.render(row.title, True, (242, 247, 255)), (row_rect.x + 16, row_rect.y + 12))
            screen.blit(body_font.render(row.description, True, (130, 150, 182)), (row_rect.x + 16, row_rect.y + 42))
            screen.blit(value_surface, (value_x, row_rect.y + 16))

            hitboxes[f"{row.row_id}:body"] = pygame.Rect(row_rect.x, row_rect.y, row_rect.w - buttons_width, row_rect.h)
            if row.adjustable:
                buttons_right = row_rect.right - 10
                top = int(row_rect.centery - button_side * 0.5)
                right_rect = pygame.Rect(buttons_right - button_side, top, button_side, button_side)
                left_rect = pygame.Rect(right_rect.x - button_gap - button_side, top, button_side, button_side)
                hitboxes[f"{row.row_id}:left"] = left_rect
                hitboxes[f"{row.row_id}:right"] = right_rect
                self._draw_arrow_button(screen, left_rect, -1, accent, left_rect.collidepoint(mouse_pos), is_selected)
                self._draw_arrow_button(screen, right_rect, 1, accent, right_rect.collidepoint(mouse_pos), is_selected)

        self._row_hitboxes[self._current_tab_id] = hitboxes

    def _draw_binding_selector(self, screen: pygame.Surface, rect: pygame.Rect, mouse_pos: Tuple[int, int]):
        self._draw_panel(screen, rect, (10, 15, 26), (39, 66, 106), 20, 2)
        inner = rect.inflate(-20, -16)
        screen.blit(self._font(22, False).render("键位选项", True, (241, 247, 255)), (inner.x, inner.y))

        selector_w = max(280, int(rect.w * 0.28))
        selector_x = inner.right - selector_w
        self._profile_prev_rect = pygame.Rect(selector_x, inner.y + 6, 44, 44)
        self._profile_label_rect = pygame.Rect(selector_x + 52, inner.y + 4, selector_w - 104, 48)
        self._profile_next_rect = pygame.Rect(selector_x + selector_w - 44, inner.y + 6, 44, 44)

        profile_focus = self._binding_focus_id == "profile"
        self._draw_arrow_button(screen, self._profile_prev_rect, -1, (104, 208, 255), self._profile_prev_rect.collidepoint(mouse_pos), profile_focus)
        self._draw_panel(
            screen,
            self._profile_label_rect,
            (20, 29, 43) if not profile_focus else (17, 50, 67),
            (67, 98, 146) if not profile_focus else (0, 239, 251),
            14,
            2,
        )
        profile_text = PROFILE_LABELS.get(self._binding_profile_id, self._binding_profile_id)
        label_surface = self._font(22, False).render(profile_text, True, (234, 246, 255))
        screen.blit(label_surface, (int(self._profile_label_rect.centerx - label_surface.get_width() * 0.5), int(self._profile_label_rect.centery - label_surface.get_height() * 0.5)))
        self._draw_arrow_button(screen, self._profile_next_rect, 1, (104, 208, 255), self._profile_next_rect.collidepoint(mouse_pos), profile_focus)

        current_mode = "双踏板" if bool(getattr(self._host, "_是否双踏板模式", False)) else "单踏板"
        waiting_text = "等待按键输入" if self._waiting_binding is not None else "点击踏板或回车开始修改"
        self._draw_text_block(
            screen,
            f"当前对局模式：{current_mode}   当前编辑模式：{profile_text}\n{waiting_text}",
            pygame.Rect(inner.x, inner.y + 38, max(260, selector_x - inner.x - 18), inner.h - 34),
            self._font(18, False),
            (170, 190, 224),
            5,
        )

    def _draw_binding_canvas(self, screen: pygame.Surface, rect: pygame.Rect, mouse_pos: Tuple[int, int]):
        self._draw_panel(screen, rect, (8, 13, 22), (37, 60, 95), 24, 2)
        canvas_rect = rect.inflate(-20, -20)
        positions = self._binding_positions(canvas_rect, self._binding_profile_id)
        labels = self._binding_display_labels(self._binding_profile_id)
        values = self._binding_values(self._binding_profile_id)
        self._binding_hitboxes = dict(positions)

        if self._binding_profile_id == PROFILE_DOUBLE:
            self._draw_binding_group(screen, positions["左区左上"].union(positions["左区右下"]).inflate(70, 70), "左区", positions, labels, values, mouse_pos)
            self._draw_binding_group(screen, positions["右区左上"].union(positions["右区右下"]).inflate(70, 70), "右区", positions, labels, values, mouse_pos)
        else:
            self._draw_binding_group(screen, positions["左上"].union(positions["右下"]).inflate(90, 80), "单踏板", positions, labels, values, mouse_pos)

    def _draw_binding_group(
        self,
        screen: pygame.Surface,
        group_rect: pygame.Rect,
        title: str,
        positions: Dict[str, pygame.Rect],
        labels: Dict[str, str],
        values: Dict[str, str],
        mouse_pos: Tuple[int, int],
    ):
        self._draw_panel(screen, group_rect, (9, 16, 28), (33, 56, 92), 22, 2)
        screen.blit(self._font(20, True).render(title, True, (120, 212, 255)), (group_rect.x + 18, group_rect.y + 16))

        if title == "单踏板":
            slot_ids = [slot_id for slot_id in positions if "区" not in slot_id]
        elif title == "左区":
            slot_ids = [slot_id for slot_id in positions if slot_id.startswith("左区")]
        else:
            slot_ids = [slot_id for slot_id in positions if slot_id.startswith("右区")]

        for slot_id in slot_ids:
            rect = positions.get(slot_id)
            if rect is None:
                continue
            hovered = rect.collidepoint(mouse_pos)
            focused = str(slot_id) == str(self._binding_focus_id)
            waiting = self._waiting_binding == (self._binding_profile_id, slot_id)
            fill_color = (21, 29, 44)
            border_color = (67, 95, 138)
            glow_color = (0, 239, 251)
            if waiting:
                fill_color = (38, 57, 26)
                border_color = (184, 255, 105)
                glow_color = (184, 255, 105)
            elif focused:
                fill_color = (18, 47, 60)
                border_color = (0, 239, 251)
            elif hovered:
                fill_color = (23, 38, 58)
                border_color = (104, 208, 255)

            points = self._pedal_points(rect)
            pygame.draw.polygon(screen, fill_color, points)
            pygame.draw.polygon(screen, border_color, points, 2)
            pygame.draw.lines(screen, glow_color if (focused or waiting) else (94, 132, 182), False, points[:4], 2)

            label = str(labels.get(slot_id, slot_id))
            value = "等待按键输入" if waiting else str(values.get(slot_id, "未绑定"))
            hint = "按 ESC 取消" if waiting else "点击或回车修改"
            screen.blit(self._font(16, True).render(label, True, (242, 247, 255)), (rect.x + 18, rect.y + 12))
            screen.blit(self._font(22, True).render(value, True, (136, 225, 255)), (rect.x + 18, rect.y + 34))
            screen.blit(self._font(14, False).render(hint, True, (138, 157, 190)), (rect.x + 18, rect.bottom - 22))

    def _draw_preview_shell(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        title: str,
        description: str,
        preview_kind: str,
    ):
        self._draw_panel(screen, rect, (8, 14, 24), (38, 61, 95), 20, 2)
        inner = rect.inflate(-18, -18)
        screen.blit(self._font(22, True).render(title, True, (245, 248, 255)), (inner.x, inner.y))
        self._draw_text_block(screen, description, pygame.Rect(inner.x, inner.y + 32, inner.w, 54), self._font(17, False), (152, 173, 204), 4)

        canvas_rect = pygame.Rect(inner.x, inner.y + 88, inner.w, max(120, inner.bottom - (inner.y + 88)))
        self._draw_panel(screen, canvas_rect, (4, 7, 14), (54, 84, 126), 16, 2)
        draw_rect = canvas_rect.inflate(-14, -14)
        resolved_kind = self._resolve_preview_kind(preview_kind) if preview_kind else ""
        preview_rect = self._resolve_preview_rect(draw_rect, resolved_kind)
        preview_drawn = False
        if preview_kind:
            preview_drawn = self._call_preview(screen, preview_rect, preview_kind)
            if preview_drawn and resolved_kind in ("dynamic", "image", "video"):
                self._apply_background_overlay(screen, preview_rect)

        if not preview_drawn:
            message = "当前设置没有可用预览。"
            if resolved_kind == "video":
                message = "未检测到可预览的视频背景。"
            elif resolved_kind == "arrow":
                message = "未检测到可用的箭头皮肤资源。"
            self._draw_text_block(screen, message, preview_rect, self._font(20, False), (145, 165, 196), 6)

    def _resolve_preview_rect(self, rect: pygame.Rect, preview_kind: str) -> pygame.Rect:
        if preview_kind not in ("dynamic", "image", "video"):
            return rect
        width = int(max(1, rect.w))
        height = int(max(1, round(float(width) * 3.0 / 4.0)))
        if height > rect.h:
            height = int(max(1, rect.h))
            width = int(max(1, round(float(height) * 4.0 / 3.0)))
        preview_rect = pygame.Rect(0, 0, width, height)
        preview_rect.center = rect.center
        return preview_rect

    def _call_preview(self, screen: pygame.Surface, rect: pygame.Rect, preview_kind: str) -> bool:
        method_name = {
            "dynamic": "_esc_menu_draw_dynamic_preview",
            "image": "_esc_menu_draw_image_preview",
            "video": "_esc_menu_draw_video_preview",
            "arrow": "_esc_menu_draw_arrow_preview",
        }.get(self._resolve_preview_kind(preview_kind), "")
        if not method_name:
            return False
        drawer = getattr(self._host, method_name, None)
        if not callable(drawer):
            return False
        old_clip = screen.get_clip()
        try:
            screen.set_clip(rect)
            return bool(drawer(screen, rect))
        except Exception:
            return False
        finally:
            screen.set_clip(old_clip)

    def _resolve_preview_kind(self, preview_kind: str) -> str:
        preview_kind = str(preview_kind or "").strip().lower()
        if preview_kind != "current":
            return preview_kind
        getter = getattr(self._host, "_取背景渲染模式", None)
        if callable(getter):
            try:
                mode = str(getter() or "图片")
            except Exception:
                mode = "图片"
        else:
            mode = str(getattr(self._host, "_背景模式", "图片") or "图片")
        if mode == "视频":
            return "video"
        if mode == "动态背景":
            return "dynamic"
        return "image"

    def _apply_background_overlay(self, screen: pygame.Surface, rect: pygame.Rect):
        try:
            alpha = int(max(0, min(255, int(getattr(self._host, "_背景暗层alpha", 0) or 0))))
        except Exception:
            alpha = 0
        if alpha <= 0:
            return
        overlay = pygame.Surface((max(1, rect.w), max(1, rect.h)), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, rect.topleft)

    def _draw_text_block(
        self,
        screen: pygame.Surface,
        text: str,
        rect: pygame.Rect,
        font: pygame.font.Font,
        color: Color,
        line_gap: int = 4,
    ):
        line_y = rect.y
        for line in self._wrap_text(str(text or ""), font, rect.w):
            if line_y + font.get_linesize() > rect.bottom:
                break
            screen.blit(font.render(line, True, color), (rect.x, line_y))
            line_y += font.get_linesize() + int(line_gap)

    def _draw_arrow_button(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        direction: int,
        accent: Color,
        hovered: bool,
        active: bool,
    ):
        fill_color = (21, 31, 48)
        border_color = (72, 101, 145)
        if active:
            fill_color = tuple(min(255, int(v * 0.16) + 18) for v in accent)
            border_color = accent
        elif hovered:
            fill_color = tuple(min(255, int(v * 0.12) + 20) for v in accent)
            border_color = tuple(min(255, int(v * 0.54) + 60) for v in accent)
        self._draw_panel(screen, rect, fill_color, border_color, 12, 2)
        center_x = rect.centerx
        center_y = rect.centery
        arrow_w = max(10, int(rect.w * 0.4))
        arrow_h = max(11, int(rect.h * 0.32))
        if int(direction) < 0:
            points = [(center_x + arrow_w // 2, center_y - arrow_h), (center_x - arrow_w // 2, center_y), (center_x + arrow_w // 2, center_y + arrow_h)]
        else:
            points = [(center_x - arrow_w // 2, center_y - arrow_h), (center_x + arrow_w // 2, center_y), (center_x - arrow_w // 2, center_y + arrow_h)]
        pygame.draw.polygon(screen, (238, 246, 255), points)

    def _draw_panel(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        fill_color: Color,
        border_color: Color,
        radius: int,
        border_width: int,
    ):
        pygame.draw.rect(screen, fill_color, rect, border_radius=int(radius))
        pygame.draw.rect(screen, border_color, rect, width=int(border_width), border_radius=int(radius))

    def _pedal_points(self, rect: pygame.Rect) -> List[Tuple[int, int]]:
        cut = max(10, int(min(rect.w, rect.h) * 0.18))
        return [
            (rect.x + cut, rect.y),
            (rect.right - 6, rect.y),
            (rect.right, rect.y + cut),
            (rect.right, rect.bottom - 6),
            (rect.x + 6, rect.bottom),
            (rect.x, rect.y + rect.h - cut),
            (rect.x, rect.y + cut),
        ]

    def _font(self, size: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
        bold = False
        key = (int(size), bool(bold), bool(italic))
        cached = self._font_cache.get(key)
        if cached is not None:
            return cached
        if not pygame.font.get_init():
            pygame.font.init()
        try:
            font = 获取字体(int(size), 是否粗体=bool(bold))
        except Exception:
            font = pygame.font.Font(None, int(size))
            font.set_bold(bool(bold))
        try:
            font.set_italic(bool(italic))
        except Exception:
            pass
        self._font_cache[key] = font
        return font

    def _truncate_text(self, text: str, font: pygame.font.Font, max_width: int) -> str:
        text = str(text or "")
        if max_width <= 0 or font.size(text)[0] <= max_width:
            return text
        trimmed = text
        while trimmed and font.size(f"{trimmed}...")[0] > max_width:
            trimmed = trimmed[:-1]
        return f"{trimmed}..." if trimmed else "..."

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        max_width = max(40, int(max_width))
        lines: List[str] = []
        for paragraph in str(text or "").splitlines() or [""]:
            if not paragraph:
                lines.append("")
                continue
            current = ""
            for char in paragraph:
                trial = f"{current}{char}"
                if current and font.size(trial)[0] > max_width:
                    lines.append(current)
                    current = str(char)
                else:
                    current = trial
            if current or not lines:
                lines.append(current)
        return lines or [""]


GameEscMenuController = EscMenuController
