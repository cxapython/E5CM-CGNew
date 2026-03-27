from __future__ import annotations

import os
import time
from typing import Dict, List, Optional, Tuple

import pygame

from core.动态背景 import DynamicBackgroundManager
from core.game_esc_menu_settings import (
    GAME_ESC_SETTINGS_KEY_AUTOPLAY,
    GAME_ESC_SETTINGS_KEY_BINDINGS,
    GAME_ESC_SETTINGS_KEY_BPM_SCROLL_EFFECT,
    GAME_ESC_SETTINGS_KEY_CHART_VISUAL_OFFSET_MS,
    GAME_ESC_SETTINGS_KEY_IMAGE_SLIDESHOW,
    PROFILE_DOUBLE,
    PROFILE_SINGLE,
    ArrowSkinOption,
    BackgroundOption,
    CHART_VISUAL_OFFSET_STEP_MS,
    VideoBackgroundOption,
    assign_profile_key,
    clamp_chart_visual_offset_ms,
    format_chart_visual_offset_ms,
    get_dynamic_background_modes,
    load_key_binding_profiles,
    read_saved_bpm_scroll_effect,
    read_saved_chart_visual_offset_ms,
    resolve_arrow_skin_option,
    resolve_background_option,
    resolve_video_background_option,
    scan_arrow_skin_options,
    scan_background_options,
    scan_video_background_options,
    serialize_key_binding_profiles,
    write_game_esc_settings_scope_patch,
)
from core.select_speed_settings import (
    DEFAULT_SELECT_SCROLL_SPEED,
    DEFAULT_SELECT_SCROLL_SPEED_OPTION,
    format_select_scroll_speed,
    get_select_scroll_speed_index,
    get_select_scroll_speed_options,
    parse_select_scroll_speed,
)
from core.select_scene_settings_layout import (
    build_select_settings_param_text,
)
from core.sqlite_store import (
    SCOPE_GAME_ESC_MENU_SETTINGS,
    SCOPE_SELECT_SETTINGS,
    read_scope,
    write_scope_patch,
)
from core.工具 import 获取字体
from ui.game_esc_menu import GameEscMenuController
from ui.谱面渲染器 import _皮肤包


class SelectSceneEscMenuHost:
    def __init__(self, context: dict):
        self._context = context if isinstance(context, dict) else {}
        self._controller = GameEscMenuController(self)
        self._project_root = str(self._context.get("项目根目录", "") or os.getcwd())
        self._默认背景视频目录 = os.path.join(self._project_root, "backmovies", "游戏中")
        self._载荷: Dict[str, object] = {}
        self._菜单背景选项: List[BackgroundOption] = []
        self._菜单视频背景选项: List[VideoBackgroundOption] = []
        self._菜单箭头选项: List[ArrowSkinOption] = []
        self._菜单动态背景选项: List[str] = []
        self._菜单单踏板键位: Dict[str, str] = {}
        self._菜单双踏板键位: Dict[str, str] = {}
        self._当前背景选项: Optional[BackgroundOption] = None
        self._当前视频背景选项: Optional[VideoBackgroundOption] = None
        self._当前箭头选项: Optional[ArrowSkinOption] = None
        self._动态背景管理器 = DynamicBackgroundManager()
        self._菜单视频预览播放器 = None
        self._菜单视频预览路径 = ""
        self._背景预览缓存: Dict[str, pygame.Surface] = {}
        self._箭头预览缓存: Dict[str, pygame.Surface] = {}
        self._箭头皮肤包缓存: Dict[str, object] = {}
        self._卷轴速度倍率 = DEFAULT_SELECT_SCROLL_SPEED
        self._隐藏模式 = "关闭"
        self._轨迹模式 = "正常"
        self._方向模式 = "关闭"
        self._尺寸倍率 = 0.8
        self._背景模式 = "图片"
        self._动态背景模式 = "唱片"
        self._背景文件名按关卡: Dict[str, str] = {}
        self._视频背景关闭 = True
        self._性能模式 = False
        self._是否自动模式 = False
        self._图片幻灯片模式开启 = True
        self._是否双踏板模式 = False
        self._谱面视觉偏移毫秒 = 0
        self._BPM变速效果开启 = False
        self._背景暗层alpha = 179
        self._refresh_from_storage()

    def open(self):
        self._refresh_from_storage()
        self._controller.open()

    def close(self):
        self._controller.close()
        self._close_video_preview_player()

    def is_open(self) -> bool:
        return bool(self._controller.is_open())

    def handle_event(self, event: pygame.event.Event):
        return self._controller.handle_event(event)

    def draw(self, screen: pygame.Surface):
        self._controller.draw(screen)

    def _esc_menu_should_show_exit_match(self) -> bool:
        return False

    def _取当前大小选项文本(self) -> str:
        return "放大" if float(self._尺寸倍率 or 0.8) >= 0.95 else "正常"

    def _取背景渲染模式(self) -> str:
        return str(getattr(self, "_背景模式", "图片") or "图片")

    def _背景亮度档位alpha(self) -> List[int]:
        return [179, 128, 77, 26, 0]

    def _取背景亮度菜单文本(self) -> str:
        档位 = list(self._背景亮度档位alpha())
        当前 = int(max(0, min(255, int(getattr(self, "_背景暗层alpha", 0) or 0))))
        try:
            索引 = min(range(len(档位)), key=lambda i: abs(int(档位[i]) - 当前))
        except Exception:
            索引 = 0
        标签 = ["默认", "较亮", "明亮", "最亮", "关闭"]
        return str(标签[int(max(0, min(len(标签) - 1, 索引)))])

    def _设置操作反馈(self, _文本: str):
        return

    def _取谱面偏移菜单文本(self) -> str:
        return format_chart_visual_offset_ms(getattr(self, "_谱面视觉偏移毫秒", 0))

    def _取当前关卡(self) -> int:
        状态 = self._context.get("状态", {}) if isinstance(self._context, dict) else {}
        if not isinstance(状态, dict):
            return 1
        try:
            数值 = int(状态.get("对局_当前把数", 1) or 1)
        except Exception:
            数值 = 1
        return max(1, int(数值))

    def _规范化关卡背景映射(self, 原始映射: object) -> Dict[str, str]:
        if not isinstance(原始映射, dict):
            return {}
        可用集合 = {
            str(getattr(选项, "file_name", "") or "").strip()
            for 选项 in list(self._菜单背景选项 or [])
            if str(getattr(选项, "file_name", "") or "").strip()
        }
        输出: Dict[str, str] = {}
        for 原键, 原值 in 原始映射.items():
            try:
                关卡 = max(1, int(原键))
            except Exception:
                continue
            文件名 = str(原值 or "").strip()
            if not 文件名:
                continue
            if 可用集合 and 文件名 not in 可用集合:
                continue
            输出[str(int(关卡))] = 文件名
        return 输出

    def _同步关卡背景状态(self):
        if not isinstance(self._context, dict):
            return
        状态 = self._context.get("状态", {})
        if not isinstance(状态, dict):
            return
        状态["对局_关卡背景图"] = dict(
            self._规范化关卡背景映射(getattr(self, "_背景文件名按关卡", {}))
        )

    def _refresh_from_storage(self):
        select_data = read_scope(SCOPE_SELECT_SETTINGS)
        esc_data = read_scope(SCOPE_GAME_ESC_MENU_SETTINGS)
        select_data = dict(select_data) if isinstance(select_data, dict) else {}
        esc_data = dict(esc_data) if isinstance(esc_data, dict) else {}
        params = dict(select_data.get("设置参数", {}) or {})

        self._菜单背景选项 = scan_background_options(self._project_root)
        self._菜单视频背景选项 = scan_video_background_options(self._project_root)
        self._菜单箭头选项 = scan_arrow_skin_options(self._project_root)
        self._菜单动态背景选项 = get_dynamic_background_modes(include_off=False) or ["唱片"]
        bindings = load_key_binding_profiles(esc_data)
        self._菜单单踏板键位 = dict(bindings.get(PROFILE_SINGLE, {}) or {})
        self._菜单双踏板键位 = dict(bindings.get(PROFILE_DOUBLE, {}) or {})

        self._卷轴速度倍率 = parse_select_scroll_speed(
            params.get("调速", f"X{DEFAULT_SELECT_SCROLL_SPEED_OPTION}"),
            default=DEFAULT_SELECT_SCROLL_SPEED,
        )
        self._隐藏模式 = str(params.get("隐藏", "关闭") or "关闭")
        self._轨迹模式 = str(params.get("轨迹", "正常") or "正常")
        self._方向模式 = str(params.get("方向", "关闭") or "关闭")
        self._尺寸倍率 = 1.0 if str(params.get("大小", "正常") or "正常") == "放大" else 0.8
        self._背景模式 = str(params.get("背景模式", "图片") or "图片")
        self._动态背景模式 = str(params.get("动态背景", "唱片") or "唱片")
        self._性能模式 = bool(esc_data.get("性能模式", False))
        self._是否自动模式 = bool(esc_data.get(GAME_ESC_SETTINGS_KEY_AUTOPLAY, False))
        self._图片幻灯片模式开启 = bool(
            esc_data.get(GAME_ESC_SETTINGS_KEY_IMAGE_SLIDESHOW, True)
        )
        self._谱面视觉偏移毫秒 = int(read_saved_chart_visual_offset_ms(esc_data))
        self._BPM变速效果开启 = bool(
            read_saved_bpm_scroll_effect(esc_data) or False
        )
        self._背景暗层alpha = int(max(0, min(255, int(esc_data.get("背景遮罩alpha", 179) or 179))))

        当前关卡键 = str(int(self._取当前关卡()))
        self._背景文件名按关卡 = self._规范化关卡背景映射(
            select_data.get("背景文件名_按关卡", {})
        )
        当前背景文件名 = str(
            self._背景文件名按关卡.get(
                当前关卡键, select_data.get("背景文件名", "")
            )
            or ""
        ).strip()
        self._当前背景选项 = resolve_background_option(
            self._菜单背景选项, 当前背景文件名
        )
        self._当前视频背景选项 = resolve_video_background_option(
            self._菜单视频背景选项, select_data.get("视频背景文件名", "")
        )
        self._当前箭头选项 = resolve_arrow_skin_option(
            self._菜单箭头选项, select_data.get("箭头文件名", "")
        )
        if self._当前背景选项 is not None:
            当前背景文件名 = str(
                getattr(self._当前背景选项, "file_name", "") or 当前背景文件名
            ).strip()
        if 当前背景文件名:
            self._背景文件名按关卡[当前关卡键] = str(当前背景文件名)
        self._同步关卡背景状态()
        self._载荷 = {
            "背景文件名": str(当前背景文件名 or getattr(self._当前背景选项, "file_name", "") or ""),
            "背景文件名_按关卡": dict(self._背景文件名按关卡),
            "视频背景文件名": str(getattr(self._当前视频背景选项, "file_name", "") or ""),
            "箭头文件名": str(getattr(self._当前箭头选项, "file_name", "") or ""),
            "关闭视频背景": bool(self._背景模式 != "视频"),
            "背景遮罩alpha": int(self._背景暗层alpha),
        }
        self._视频背景关闭 = bool(self._背景模式 != "视频")

    def _save_select_visual_settings(self):
        动态背景模式 = str(self._动态背景模式 or "关闭")
        if str(self._背景模式 or "图片") == "动态背景":
            动态背景模式 = DynamicBackgroundManager.normalize_mode(动态背景模式)
            if 动态背景模式 == "关闭":
                动态背景模式 = str((self._菜单动态背景选项 or ["唱片"])[0])
        else:
            动态背景模式 = "关闭"
        params = {
            "调速": format_select_scroll_speed(self._卷轴速度倍率, prefix="X"),
            "背景模式": str(self._背景模式 or "图片"),
            "动态背景": str(动态背景模式 or "关闭"),
            "隐藏": str(self._隐藏模式 or "关闭"),
            "轨迹": str(self._轨迹模式 or "正常"),
            "方向": str(self._方向模式 or "关闭"),
            "大小": self._取当前大小选项文本(),
        }
        背景文件名 = str(getattr(self._当前背景选项, "file_name", "") or "")
        视频背景文件名 = str(getattr(self._当前视频背景选项, "file_name", "") or "")
        箭头文件名 = str(getattr(self._当前箭头选项, "file_name", "") or "")
        当前关卡键 = str(int(self._取当前关卡()))
        背景文件名按关卡 = self._规范化关卡背景映射(
            getattr(self, "_背景文件名按关卡", {})
        )
        if 背景文件名:
            背景文件名按关卡[当前关卡键] = str(背景文件名)
        self._背景文件名按关卡 = dict(背景文件名按关卡)
        self._同步关卡背景状态()
        参数文本 = build_select_settings_param_text(
            settings_params=params,
            background_filename=背景文件名,
            arrow_filename=箭头文件名,
        )
        patch = {
            "设置参数": dict(params),
            "设置参数文本": str(参数文本 or ""),
            "动态背景": str(动态背景模式 or "关闭"),
            "背景文件名": str(背景文件名),
            "背景文件名_按关卡": dict(背景文件名按关卡),
            "视频背景文件名": str(视频背景文件名),
            "箭头文件名": str(箭头文件名),
        }
        write_scope_patch(SCOPE_SELECT_SETTINGS, patch)
        self._载荷.update(patch)
        self._载荷["设置参数"] = dict(params)
        self._载荷["关闭视频背景"] = bool(self._背景模式 != "视频")

    def _save_esc_scope_patch(self, patch: Dict[str, object]):
        write_scope_patch(SCOPE_GAME_ESC_MENU_SETTINGS, dict(patch or {}))

    def _apply_video_option(self, file_name: str) -> bool:
        option = resolve_video_background_option(self._菜单视频背景选项, file_name)
        if option is None:
            return False
        self._当前视频背景选项 = option
        self._载荷["视频背景文件名"] = str(option.file_name or "")
        self._close_video_preview_player()
        self._save_select_visual_settings()
        return True

    def _esc_menu_adjust(self, row_key: str, step: int = 1):
        step = 1 if int(step or 0) >= 0 else -1
        key = str(row_key or "").strip()
        if not key:
            return None

        if key == "scroll_speed":
            options = get_select_scroll_speed_options()
            if not options:
                return None
            index = get_select_scroll_speed_index(
                self._卷轴速度倍率,
                default=DEFAULT_SELECT_SCROLL_SPEED_OPTION,
            )
            self._卷轴速度倍率 = float(options[(index + step) % len(options)])
            self._save_select_visual_settings()
            return None

        if key == "bpm_scroll_effect":
            self._BPM变速效果开启 = not bool(
                getattr(self, "_BPM变速效果开启", False)
            )
            self._save_esc_scope_patch(
                {
                    GAME_ESC_SETTINGS_KEY_BPM_SCROLL_EFFECT: bool(
                        self._BPM变速效果开启
                    )
                }
            )
            return None

        if key == "background_mode":
            options = ["图片", "视频", "动态背景"]
            current = str(self._背景模式 or "图片")
            index = options.index(current) if current in options else 0
            self._背景模式 = str(options[(index + step) % len(options)])
            self._视频背景关闭 = bool(self._背景模式 != "视频")
            if self._背景模式 == "动态背景" and self._动态背景模式 == "关闭":
                self._动态背景模式 = str((self._菜单动态背景选项 or ["唱片"])[0])
            self._save_select_visual_settings()
            return None

        if key == "image_slideshow_mode":
            self._图片幻灯片模式开启 = not bool(
                getattr(self, "_图片幻灯片模式开启", True)
            )
            self._save_esc_scope_patch(
                {
                    GAME_ESC_SETTINGS_KEY_IMAGE_SLIDESHOW: bool(
                        self._图片幻灯片模式开启
                    )
                }
            )
            return None

        if key == "dynamic_background":
            options = list(self._菜单动态背景选项 or ["唱片"])
            current = str(self._动态背景模式 or options[0])
            index = options.index(current) if current in options else 0
            self._动态背景模式 = str(options[(index + step) % len(options)])
            try:
                self._动态背景管理器.reset()
            except Exception:
                pass
            self._save_select_visual_settings()
            return None

        if key == "image_background":
            options = list(self._菜单背景选项 or [])
            if not options:
                return None
            current = resolve_background_option(options, getattr(self._当前背景选项, "file_name", ""))
            try:
                index = options.index(current)
            except Exception:
                index = 0
            self._当前背景选项 = options[(index + step) % len(options)]
            self._save_select_visual_settings()
            return None

        if key == "video_background":
            options = list(self._菜单视频背景选项 or [])
            if not options:
                return None
            current = resolve_video_background_option(options, getattr(self._当前视频背景选项, "file_name", ""))
            try:
                index = options.index(current)
            except Exception:
                index = 0
            self._apply_video_option(str(options[(index + step) % len(options)].file_name or ""))
            return None

        if key == "hidden":
            options = ["关闭", "半隐", "全隐"]
            current = str(self._隐藏模式 or "关闭")
            index = options.index(current) if current in options else 0
            self._隐藏模式 = str(options[(index + step) % len(options)])
            self._save_select_visual_settings()
            return None

        if key == "track":
            options = ["正常", "摇摆", "旋转"]
            current = str(self._轨迹模式 or "正常")
            index = options.index(current) if current in options else 0
            self._轨迹模式 = str(options[(index + step) % len(options)])
            self._save_select_visual_settings()
            return None

        if key == "direction":
            options = ["关闭", "反向"]
            current = str(self._方向模式 or "关闭")
            index = options.index(current) if current in options else 0
            self._方向模式 = str(options[(index + step) % len(options)])
            self._save_select_visual_settings()
            return None

        if key == "size":
            self._尺寸倍率 = 1.0 if float(self._尺寸倍率 or 0.8) < 0.95 else 0.8
            self._save_select_visual_settings()
            return None

        if key == "arrow_skin":
            options = list(self._菜单箭头选项 or [])
            if not options:
                return None
            current = resolve_arrow_skin_option(options, getattr(self._当前箭头选项, "file_name", ""))
            try:
                index = options.index(current)
            except Exception:
                index = 0
            self._当前箭头选项 = options[(index + step) % len(options)]
            self._save_select_visual_settings()
            return None

        if key == "brightness":
            levels = self._背景亮度档位alpha()
            current = int(self._背景暗层alpha or 0)
            try:
                index = min(range(len(levels)), key=lambda i: abs(int(levels[i]) - current))
            except Exception:
                index = 0
            self._背景暗层alpha = int(levels[(index + step) % len(levels)])
            self._载荷["背景遮罩alpha"] = int(self._背景暗层alpha)
            self._save_esc_scope_patch({"背景遮罩alpha": int(self._背景暗层alpha)})
            return None

        if key == "chart_visual_offset":
            current = int(getattr(self, "_谱面视觉偏移毫秒", 0) or 0)
            new_value = int(
                clamp_chart_visual_offset_ms(
                    current + int(step) * int(CHART_VISUAL_OFFSET_STEP_MS),
                    current,
                )
            )
            self._谱面视觉偏移毫秒 = int(new_value)
            self._save_esc_scope_patch(
                {GAME_ESC_SETTINGS_KEY_CHART_VISUAL_OFFSET_MS: int(self._谱面视觉偏移毫秒)}
            )
            return None

        if key == "performance_mode":
            self._性能模式 = not bool(self._性能模式)
            self._save_esc_scope_patch({"性能模式": bool(self._性能模式)})
            return None

        if key == "autoplay":
            self._是否自动模式 = not bool(self._是否自动模式)
            write_game_esc_settings_scope_patch({GAME_ESC_SETTINGS_KEY_AUTOPLAY: bool(self._是否自动模式)})
            return None

    def _esc_menu_apply_binding(self, profile_id: str, slot_id: str, keycode: object):
        profiles = {
            PROFILE_SINGLE: dict(self._菜单单踏板键位),
            PROFILE_DOUBLE: dict(self._菜单双踏板键位),
        }
        updated = assign_profile_key(profiles, str(profile_id), str(slot_id), keycode)
        self._菜单单踏板键位 = dict(updated.get(PROFILE_SINGLE, {}) or {})
        self._菜单双踏板键位 = dict(updated.get(PROFILE_DOUBLE, {}) or {})
        write_game_esc_settings_scope_patch(
            {
                GAME_ESC_SETTINGS_KEY_BINDINGS: serialize_key_binding_profiles(
                    {
                        PROFILE_SINGLE: self._菜单单踏板键位,
                        PROFILE_DOUBLE: self._菜单双踏板键位,
                    }
                )
            }
        )

    def _esc_menu_confirm_exit(self, target: str):
        self.close()
        if str(target) == "desktop":
            return {"退出程序": True}
        return None

    def _esc_menu_draw_dynamic_preview(self, screen: pygame.Surface, rect: pygame.Rect) -> bool:
        mode = str(self._动态背景模式 or "关闭")
        if mode == "关闭":
            return False
        try:
            return bool(
                self._动态背景管理器.render_preview_surface(
                    mode,
                    screen,
                    rect,
                    now=float(time.perf_counter()),
                )
            )
        except Exception:
            return False

    def _load_surface(self, cache: Dict[str, pygame.Surface], path: str, alpha: bool) -> Optional[pygame.Surface]:
        key = str(path or "").strip()
        cached = cache.get(key)
        if isinstance(cached, pygame.Surface):
            return cached
        if not key or (not os.path.isfile(key)):
            return None
        try:
            surface = pygame.image.load(key)
            surface = surface.convert_alpha() if alpha else surface.convert()
            cache[key] = surface
            return surface
        except Exception:
            return None

    def _blit_cover(self, screen: pygame.Surface, image: pygame.Surface, rect: pygame.Rect):
        iw, ih = image.get_size()
        scale = max(float(rect.w) / float(max(1, iw)), float(rect.h) / float(max(1, ih)))
        size = (max(1, int(round(iw * scale))), max(1, int(round(ih * scale))))
        frame = pygame.transform.smoothscale(image, size)
        screen.blit(frame, (int(rect.centerx - frame.get_width() * 0.5), int(rect.centery - frame.get_height() * 0.5)))

    def _blit_contain(self, screen: pygame.Surface, image: pygame.Surface, rect: pygame.Rect):
        iw, ih = image.get_size()
        scale = min(float(rect.w) / float(max(1, iw)), float(rect.h) / float(max(1, ih)))
        size = (max(1, int(round(iw * scale))), max(1, int(round(ih * scale))))
        frame = pygame.transform.smoothscale(image, size)
        screen.blit(frame, (int(rect.centerx - frame.get_width() * 0.5), int(rect.centery - frame.get_height() * 0.5)))

    def _esc_menu_draw_image_preview(self, screen: pygame.Surface, rect: pygame.Rect) -> bool:
        path = str(getattr(self._当前背景选项, "path", "") or "")
        image = self._load_surface(self._背景预览缓存, path, True)
        if not isinstance(image, pygame.Surface):
            return False
        self._blit_contain(screen, image, rect)
        return True

    def _close_video_preview_player(self):
        player = getattr(self, "_菜单视频预览播放器", None)
        try:
            if player is not None and hasattr(player, "关闭"):
                player.关闭()
        except Exception:
            pass
        self._菜单视频预览播放器 = None
        self._菜单视频预览路径 = ""

    def _get_video_preview_player(self):
        target_path = str(getattr(self._当前视频背景选项, "path", "") or self._默认背景视频目录 or "").strip()
        if not target_path:
            self._close_video_preview_player()
            return None
        if getattr(self, "_菜单视频预览播放器", None) is not None and str(self._菜单视频预览路径 or "") == target_path:
            return self._菜单视频预览播放器
        self._close_video_preview_player()
        try:
            if os.path.isdir(target_path):
                from core.视频 import 全局视频顺序循环播放器

                player = 全局视频顺序循环播放器(target_path)
            else:
                from core.视频 import 全局视频循环播放器

                player = 全局视频循环播放器(target_path)
            player.打开(是否重置进度=True)
            self._菜单视频预览播放器 = player
            self._菜单视频预览路径 = target_path
            return player
        except Exception:
            self._close_video_preview_player()
            return None

    def _esc_menu_draw_video_preview(self, screen: pygame.Surface, rect: pygame.Rect) -> bool:
        player = self._get_video_preview_player()
        if player is None:
            return False
        try:
            frame = player.读取帧() if hasattr(player, "读取帧") else None
        except Exception:
            frame = None
        if not isinstance(frame, pygame.Surface):
            return False
        self._blit_contain(screen, frame, rect)
        return True

    def _get_arrow_preview_atlas(self):
        option = self._当前箭头选项
        if option is None:
            return None
        skin_dir = os.path.abspath(str(getattr(option, "skin_dir", "") or "").strip())
        if (not skin_dir) or (not os.path.isdir(skin_dir)):
            return None
        cached = self._箭头皮肤包缓存.get(skin_dir)
        if cached is None:
            try:
                package = _皮肤包()
                package.加载(skin_dir)
                cached = package
            except Exception:
                cached = False
            self._箭头皮肤包缓存[skin_dir] = cached
        if cached is False:
            return None
        return getattr(cached, "arrow", None)

    def _draw_five_lane_arrow_preview(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        atlas,
        fallback_image: Optional[pygame.Surface],
    ) -> bool:
        inner = rect.inflate(-18, -18)
        if inner.w <= 0 or inner.h <= 0:
            return False
        lane_gap = max(6, int(inner.w * 0.02))
        lane_width = max(12, int((inner.w - lane_gap * 4) / 5))
        codes = ("lb", "lt", "cc", "rt", "rb")
        has_preview = False
        for index, code in enumerate(codes):
            lane_x = inner.x + index * (lane_width + lane_gap)
            lane_rect = pygame.Rect(lane_x, inner.y, lane_width, inner.h)
            pygame.draw.rect(screen, (16, 24, 38), lane_rect, border_radius=10)
            pygame.draw.rect(screen, (38, 58, 90), lane_rect, width=1, border_radius=10)
            source = atlas.取(f"arrow_body_{code}.png") if atlas is not None else None
            if not isinstance(source, pygame.Surface):
                source = fallback_image
            if not isinstance(source, pygame.Surface):
                continue
            image_rect = lane_rect.inflate(
                -max(4, int(lane_rect.w * 0.18)),
                -max(10, int(lane_rect.h * 0.18)),
            )
            if image_rect.w <= 0 or image_rect.h <= 0:
                image_rect = lane_rect
            self._blit_contain(screen, source, image_rect)
            has_preview = True
        return has_preview

    def _esc_menu_draw_arrow_preview(self, screen: pygame.Surface, rect: pygame.Rect) -> bool:
        option = self._当前箭头选项
        if option is None:
            return False
        atlas = self._get_arrow_preview_atlas()
        preview_path = str(getattr(option, "preview_path", "") or "")
        image = self._load_surface(self._箭头预览缓存, preview_path, True)
        if self._draw_five_lane_arrow_preview(screen, rect, atlas, image):
            return True
        font = 获取字体(20, 是否粗体=False)
        label = font.render(str(getattr(option, "label", "箭头") or "箭头"), True, (220, 235, 255))
        screen.blit(label, (int(rect.centerx - label.get_width() * 0.5), int(rect.centery - label.get_height() * 0.5)))
        return True
