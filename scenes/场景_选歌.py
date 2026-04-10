
import os
import json
import re
import math
import time
import gc
import sys
import threading
from collections import deque
from dataclasses import dataclass
from functools import wraps
from typing import Dict, List, Optional, Tuple, Set, Callable
from core.常量与路径 import (
    取冷资源路径 as _公共取冷资源路径,
    取项目根目录 as _公共取项目根目录,
    取布局配置路径 as _公共取布局配置路径,
    取首个存在路径 as _公共取首个存在路径,
    取资源路径 as _公共取资源路径,
    取运行根目录 as _公共取运行根目录,
    取选歌封面缓存目录 as _公共取选歌封面缓存目录,
    取songs根目录 as _公共取songs根目录,
    取调试配置路径 as _公共取调试配置路径,
)
from core.日志 import (
    取日志器 as _取日志器,
    记录异常 as _记录异常日志,
    记录信息 as _记录信息日志,
    记录警告 as _记录警告日志,
)
from core.动态背景 import DynamicBackgroundContext, DynamicBackgroundManager
from core.音频 import 确保pygame基础模块已初始化 as _确保pygame基础模块已初始化
from core.音频 import 确保混音器已初始化 as _确保混音器已初始化
from core.game_esc_menu_settings import (
    GAME_ESC_SETTINGS_KEY_IMAGE_SLIDESHOW as _游戏esc图片幻灯片模式键,
)
from core.工具 import 获取字体 as _公共获取字体
from core.图片缓存 import 本地图片缓存 as _本地图片缓存
from core.sqlite_store import (
    SCOPE_FAVORITES as _收藏夹存储作用域,
    SCOPE_GAME_ESC_MENU_SETTINGS as _游戏esc菜单设置存储作用域,
    SCOPE_LOADING_PAYLOAD as _加载页存储作用域,
    SCOPE_SELECT_SETTINGS as _选歌设置存储作用域,
    get_runtime_store_path as _取运行存储路径,
    read_scope as _读取存储作用域,
    replace_scope as _覆盖存储作用域,
    write_scope_patch as _写入存储作用域,
)
from core.select_speed_settings import (
    DEFAULT_SELECT_SCROLL_SPEED_OPTION,
    format_select_scroll_speed,
    get_default_select_scroll_speed_index,
    nearest_select_scroll_speed_option,
)
from core.select_scene_layout import (
    compute_frame_slot_layout as _计算框体槽位布局模块,
    compute_thumbnail_card_layout as _计算缩略图卡片布局模块,
    compute_thumbnail_frame_rect as _计算缩略图小框矩形模块,
)
from core.select_scene_preload import (
    build_preload_page_order as _构建预加载页顺序模块,
    collect_preload_cover_keys as _收集预加载封面键列表模块,
)
from core.select_scene_card_fx import (
    draw_card_hover_overlay as _绘制卡片悬停叠层,
    draw_card_hover_underlay as _绘制卡片悬停底层,
)
from core.select_scene_card_renderer import (
    build_song_card_cache_key as _构建歌曲卡片缓存键,
    render_song_card_static_surface as _渲染歌曲卡片静态图,
)
from core.select_scene_badges import draw_mv_badge as _绘制MV角标模块
from core.select_scene_detail_renderer import (
    draw_detail_star_gloss as _绘制详情浮层星光模块,
    render_detail_panel_content as _渲染详情浮层面板内容模块,
)
from core.select_scene_detail_badges import (
    render_detail_corner_badges as _渲染详情角标模块,
)
from core.select_scene_grid import (
    CardGridConfig as _卡片网格配置模块,
    build_card_grid_rects as _构建卡片网格矩形模块,
)
from core.select_scene_host_adapter import (
    bind_select_scene_host_adapter as _绑定选歌场景化方法模块,
)
from core.select_scene_settings_layout import (
    SettingsLayoutDebugger as 设置页布局调试器,
    build_select_settings_param_text as 构建设置参数文本,
    draw_cover_crop_preview as 绘制_cover裁切预览,
    extract_select_settings_param_value as 设置参数文本提取值,
    get_default_select_menu_speed_options as 设置菜单默认调速选项,
    get_select_menu_row_label as 设置菜单行显示名,
    get_select_menu_row_value as 设置菜单行值,
    recompute_select_settings_layout as 重算设置页布局,
)
from core.歌曲记录 import 读取歌曲记录索引, 取歌曲记录键
from core.对局状态 import 取当前关卡, 取累计S数, 是否赠送第四把, 重置游戏流程状态
from core.踏板控制 import 踏板动作_左, 踏板动作_右, 踏板动作_确认
from ui.top栏 import 生成top栏
import pygame
from scenes.场景基类 import 场景基类

try:
    from pygame._sdl2 import video as _sdl2_video
except Exception:
    _sdl2_video = None

_日志器 = _取日志器("scene.选歌")


def 确保项目根目录在模块路径里():
    return

确保项目根目录在模块路径里()

_项目根目录_缓存: str | None = None
_运行根目录_缓存: str | None = None
_songs根目录_缓存: str | None = None
_歌曲扫描缓存: Dict[Tuple[object, ...], dict] = {}
_歌曲扫描缓存顺序: List[Tuple[object, ...]] = []
_歌曲扫描缓存上限 = 8
_歌曲扫描缓存锁 = threading.RLock()
_歌曲扫描执行锁 = threading.Lock()
_懒解析模式标记缓存: Dict[Tuple[str, int], dict] = {}
_懒解析模式标记缓存顺序: List[Tuple[str, int]] = []
_懒解析模式标记缓存上限 = 1024
_懒解析模式标记缓存锁 = threading.RLock()
_稳定谱面解析模式日志已输出 = False
_稳定NEW标记模式日志已输出 = False
_稳定场景初始化模式日志已输出 = False
_懒解析模式标记日志已输出 = False
_最近扫描谱面路径 = ""
_候选谱面扩展名集合 = {".json", ".ssc", ".sm", ".sma"}


def _进入稳定GC区间(需要关闭: bool) -> bool:
    if (not bool(需要关闭)) or (not bool(gc.isenabled())):
        return False
    try:
        gc.disable()
        return True
    except Exception:
        return False


def _离开稳定GC区间(曾关闭GC: bool) -> None:
    if (not bool(曾关闭GC)) or bool(gc.isenabled()):
        return
    try:
        gc.enable()
    except Exception:
        pass


def _串行化歌曲扫描(函数):
    @wraps(函数)
    def _包装(*args, **kwargs):
        with _歌曲扫描执行锁:
            需要关闭GC = bool(_启用稳定谱面解析模式())
            曾关闭GC = _进入稳定GC区间(需要关闭GC)
            try:
                return 函数(*args, **kwargs)
            finally:
                _离开稳定GC区间(曾关闭GC)

    return _包装


def _启用稳定谱面解析模式() -> bool:
    环境值 = str(os.environ.get("E5CM_SAFE_SM_PARSE", "") or "").strip().lower()
    if 环境值 in ("1", "true", "yes", "on"):
        return True
    if 环境值 in ("0", "false", "no", "off"):
        return False
    # 默认始终使用完整谱面扫描；仅在显式开启时才走稳定/保守解析模式。
    return False


def _启用懒解析模式标记() -> bool:
    环境值 = str(os.environ.get("E5CM_LAZY_MODE_TAG", "") or "").strip().lower()
    if 环境值 in ("1", "true", "yes", "on"):
        return True
    if 环境值 in ("0", "false", "no", "off"):
        return False
    return bool(_启用稳定谱面解析模式())


def _启用稳定NEW标记模式() -> bool:
    环境值 = str(os.environ.get("E5CM_SAFE_NEW_TAG", "") or "").strip().lower()
    if 环境值 in ("1", "true", "yes", "on"):
        return True
    if 环境值 in ("0", "false", "no", "off"):
        return False
    return bool(getattr(sys, "frozen", False))


def _启用稳定场景初始化模式() -> bool:
    环境值 = str(os.environ.get("E5CM_SAFE_SCENE_INIT", "") or "").strip().lower()
    if 环境值 in ("1", "true", "yes", "on"):
        return True
    if 环境值 in ("0", "false", "no", "off"):
        return False
    return bool(getattr(sys, "frozen", False))


def _记录扫描谱面路径(sm路径: str, 类型名: str, 模式名: str) -> None:
    global _最近扫描谱面路径
    if not bool(_启用稳定谱面解析模式()):
        return
    路径 = os.path.abspath(str(sm路径 or "").strip()) if str(sm路径 or "").strip() else ""
    if (not 路径) or 路径 == str(_最近扫描谱面路径):
        return
    _最近扫描谱面路径 = str(路径)
    try:
        _记录信息日志(
            _日志器,
            f"扫描谱面文件 类型={str(类型名 or '')} 模式={str(模式名 or '')} 路径={路径}",
        )
    except Exception:
        pass


def _取项目根目录() -> str:
    global _项目根目录_缓存
    _项目根目录_缓存 = _公共取项目根目录()
    return _项目根目录_缓存


def _取运行根目录() -> str:
    global _运行根目录_缓存
    _运行根目录_缓存 = _公共取运行根目录()
    return _运行根目录_缓存


def _取songs根目录(资源: Optional[dict] = None, 状态: Optional[dict] = None) -> str:
    global _songs根目录_缓存
    _songs根目录_缓存 = _公共取songs根目录(资源=资源, 状态=状态)
    return _songs根目录_缓存


def 获取字体(
    字号: int, 是否粗体: bool = False, 字体文件路径: Optional[str] = None, **额外参数
) -> pygame.font.Font:
    return _公共获取字体(
        字号,
        是否粗体=False,
        字体文件路径=字体文件路径,
        **额外参数,
    )


def _归一化目录名(名称: str) -> str:
    return re.sub(r"[\s_\-]+", "", str(名称 or "")).strip().lower()


def _取目录修改时间秒(目录路径: str) -> int:
    try:
        return int(os.path.getmtime(str(目录路径 or "")))
    except Exception:
        return 0


def _取文件修改时间秒(文件路径: str) -> int:
    try:
        return int(os.path.getmtime(str(文件路径 or "")))
    except Exception:
        return 0


def _读取懒解析模式标记缓存(缓存键: Tuple[str, int]) -> Optional[dict]:
    if (not isinstance(缓存键, tuple)) or len(缓存键) != 2:
        return None
    with _懒解析模式标记缓存锁:
        命中 = _懒解析模式标记缓存.get(缓存键)
        if not isinstance(命中, dict):
            return None
        try:
            if 缓存键 in _懒解析模式标记缓存顺序:
                _懒解析模式标记缓存顺序.remove(缓存键)
        except Exception:
            pass
        _懒解析模式标记缓存顺序.append(缓存键)
        return dict(命中)


def _写入懒解析模式标记缓存(缓存键: Tuple[str, int], 值: dict) -> None:
    if (not isinstance(缓存键, tuple)) or len(缓存键) != 2:
        return
    if not isinstance(值, dict):
        return
    with _懒解析模式标记缓存锁:
        _懒解析模式标记缓存[缓存键] = dict(值)
        try:
            if 缓存键 in _懒解析模式标记缓存顺序:
                _懒解析模式标记缓存顺序.remove(缓存键)
        except Exception:
            pass
        _懒解析模式标记缓存顺序.append(缓存键)
        while len(_懒解析模式标记缓存顺序) > _懒解析模式标记缓存上限:
            最旧键 = _懒解析模式标记缓存顺序.pop(0)
            _懒解析模式标记缓存.pop(最旧键, None)


def _目录含候选谱面文件(目录路径: str, 最大命中数: int = 1) -> bool:
    根目录 = os.path.abspath(str(目录路径 or "").strip()) if str(目录路径 or "").strip() else ""
    if (not 根目录) or (not os.path.isdir(根目录)):
        return False
    try:
        已命中数 = 0
        for 当前根, _目录列表, 文件列表 in os.walk(根目录):
            for 文件名 in 文件列表:
                扩展名 = os.path.splitext(str(文件名 or ""))[1].lower()
                if 扩展名 not in _候选谱面扩展名集合:
                    continue
                已命中数 += 1
                if 已命中数 >= max(1, int(最大命中数 or 1)):
                    return True
    except Exception:
        return False
    return False


def _统计数据树歌曲总数(数据树: Dict[str, Dict[str, List["歌曲信息"]]]) -> int:
    if not isinstance(数据树, dict):
        return 0
    总数 = 0
    for 模式映射 in 数据树.values():
        if not isinstance(模式映射, dict):
            continue
        for 列表 in 模式映射.values():
            if isinstance(列表, list):
                总数 += int(len(列表))
    return int(max(0, 总数))


def _数子目录数量(目录路径: str) -> int:
    if not os.path.isdir(目录路径):
        return 0
    try:
        return int(
            sum(
                1
                for 名称 in os.listdir(目录路径)
                if os.path.isdir(os.path.join(目录路径, 名称))
            )
        )
    except Exception:
        return 0


def _构建全量扫描缓存键(songs根目录: str) -> Tuple[object, ...]:
    根目录 = os.path.abspath(str(songs根目录 or "").strip())
    类型目录列表 = _列出一级子目录(根目录)
    模式总数 = 0
    for 类型名 in 类型目录列表:
        模式总数 += _数子目录数量(os.path.join(根目录, str(类型名)))
    return (
        "all",
        根目录,
        _取目录修改时间秒(根目录),
        int(len(类型目录列表)),
        int(模式总数),
    )


def _构建指定扫描缓存键(
    songs根目录: str,
    类型目录: str,
    模式目录: str,
    类型名: str,
    模式名: str,
) -> Tuple[object, ...]:
    根目录 = os.path.abspath(str(songs根目录 or "").strip())
    return (
        "specified",
        根目录,
        _归一化目录名(类型名),
        _归一化目录名(模式名),
        _取目录修改时间秒(str(类型目录 or "")),
        _取目录修改时间秒(str(模式目录 or "")),
        _数子目录数量(str(模式目录 or "")),
    )


def _列出一级子目录(目录路径: str) -> List[str]:
    结果: List[str] = []
    if not os.path.isdir(目录路径):
        return 结果

    try:
        for 名称 in os.listdir(目录路径):
            完整路径 = os.path.join(目录路径, 名称)
            if os.path.isdir(完整路径):
                结果.append(str(名称))
    except Exception:
        return []

    结果.sort()
    return 结果


def _在现有名称中匹配(现有名称列表: List[str], 候选名称: str) -> str:
    if not 现有名称列表:
        return ""

    目标 = str(候选名称 or "").strip()
    if not 目标:
        return ""

    if 目标 in 现有名称列表:
        return 目标

    目标归一 = _归一化目录名(目标)
    for 现有名称 in 现有名称列表:
        if _归一化目录名(现有名称) == 目标归一:
            return 现有名称

    return ""

def _解析选歌入口参数(状态: dict, songs根目录: str) -> Tuple[str, str]:
    if not isinstance(状态, dict):
        状态 = {}

    加载页载荷 = 状态.get("加载页_载荷", {})
    if not isinstance(加载页载荷, dict):
        加载页载荷 = {}

    def _转文本(值) -> str:
        try:
            return str(值 or "").strip()
        except Exception:
            return ""

    def _取首个非空(*候选值) -> str:
        for 候选值 in 候选值:
            文本 = _转文本(候选值)
            if 文本:
                return 文本
        return ""

    def _生成别名列表(名称: str) -> List[str]:
        原始名称 = _转文本(名称)
        if not 原始名称:
            return []

        归一名称 = _归一化目录名(原始名称)
        别名列表: List[str] = [原始名称]

        if ("竞" in 原始名称) or ("speed" in 归一名称):
            别名列表.extend(["竞速", "speed", "Speed"])
        if ("花" in 原始名称) or ("fancy" in 归一名称):
            别名列表.extend(["花式", "fancy", "Fancy"])
        if ("派对" in 原始名称) or ("party" in 归一名称):
            别名列表.extend(["派对", "party", "Party"])
        if ("表演" in 原始名称) or ("show" in 归一名称):
            别名列表.extend(["表演", "show", "Show"])
        if ("学习" in 原始名称) or ("easy" in 归一名称) or ("learn" in 归一名称):
            别名列表.extend(["学习", "easy", "learn", "Easy", "Learn"])
        if ("疯狂" in 原始名称) or ("crazy" in 归一名称):
            别名列表.extend(["疯狂", "crazy", "Crazy"])
        if ("混音" in 原始名称) or ("mix" in 归一名称) or ("remix" in 归一名称):
            别名列表.extend(["混音", "mix", "remix", "Mix", "Remix"])
        if ("情侣" in 原始名称) or ("lover" in 归一名称):
            别名列表.extend(["情侣", "lover", "Lover"])
        if ("双踏板" in 原始名称) or ("club" in 归一名称):
            别名列表.extend(["双踏板", "club", "Club"])

        去重后列表: List[str] = []
        已出现集合: Set[str] = set()
        for 别名 in 别名列表:
            归一键 = _归一化目录名(别名)
            if (not 归一键) or (归一键 in 已出现集合):
                continue
            已出现集合.add(归一键)
            去重后列表.append(str(别名))
        return 去重后列表

    def _尝试修复songs根目录(原始songs根目录: str) -> str:
        try:
            路径文本 = os.path.abspath(str(原始songs根目录 or "").strip())
        except Exception:
            路径文本 = ""
        if 路径文本 and os.path.isdir(路径文本):
            return 路径文本
        return _取songs根目录(状态=状态)

    def _匹配目录名_支持别名(
        父目录: str, 候选名称列表: List[str]
    ) -> Tuple[str, List[str]]:
        子目录列表 = _列出一级子目录(父目录)
        if not 子目录列表:
            return "", []

        for 候选名称 in 候选名称列表:
            for 别名 in _生成别名列表(候选名称):
                匹配结果 = _在现有名称中匹配(子目录列表, 别名)
                if 匹配结果:
                    return 匹配结果, 子目录列表

        return "", 子目录列表

    songs根目录 = _尝试修复songs根目录(songs根目录)

    类型候选列表 = [
        状态.get("选歌_类型", ""),
        状态.get("大模式", ""),
        状态.get("songs子文件夹", ""),
        状态.get("选歌类型", ""),
        加载页载荷.get("选歌类型", ""),
        加载页载荷.get("类型", ""),
        加载页载荷.get("大模式", ""),
    ]

    模式候选列表 = [
        状态.get("选歌_模式", ""),
        状态.get("子模式", ""),
        状态.get("选歌模式", ""),
        加载页载荷.get("选歌模式", ""),
        加载页载荷.get("模式", ""),
        加载页载荷.get("子模式", ""),
    ]

    原始类型候选 = _取首个非空(*类型候选列表)
    原始模式候选 = _取首个非空(*模式候选列表)

    类型名, 所有类型列表 = _匹配目录名_支持别名(
        songs根目录, [str(x or "") for x in 类型候选列表]
    )
    if not 类型名 and len(所有类型列表) == 1:
        类型名 = 所有类型列表[0]
    elif not 类型名 and 所有类型列表:
        类型名 = 所有类型列表[0]

    模式父目录 = os.path.join(songs根目录, 类型名) if 类型名 else ""
    模式名, 所有模式列表 = _匹配目录名_支持别名(
        模式父目录, [str(x or "") for x in 模式候选列表]
    )
    if not 模式名 and len(所有模式列表) == 1:
        模式名 = 所有模式列表[0]
    elif not 模式名 and 所有模式列表:
        模式名 = 所有模式列表[0]

    最终类型名 = str(类型名 or 原始类型候选 or "")
    最终模式名 = str(模式名 or 原始模式候选 or "")

    if 最终类型名:
        状态["选歌_类型"] = 最终类型名
        if not _转文本(状态.get("大模式", "")):
            状态["大模式"] = 最终类型名
        if not _转文本(状态.get("songs子文件夹", "")):
            状态["songs子文件夹"] = 最终类型名
        if 类型名:
            状态["大模式"] = 类型名
            状态["songs子文件夹"] = 类型名
    else:
        状态.pop("选歌_类型", None)

    if 最终模式名:
        状态["选歌_模式"] = 最终模式名
        if not _转文本(状态.get("子模式", "")):
            状态["子模式"] = 最终模式名
        if 模式名:
            状态["子模式"] = 模式名
    else:
        状态.pop("选歌_模式", None)

    return 最终类型名, 最终模式名


class 场景_选歌(场景基类):
    名称 = "选歌"

    def __init__(self, 上下文: dict):
        super().__init__(上下文)
        self._选歌实例: 选歌游戏 | None = None

    def 进入(self, 载荷=None):
        资源 = self.上下文.get("资源", {})
        状态 = self.上下文.get("状态", {})
        if not isinstance(状态, dict):
            状态 = {}
            self.上下文["状态"] = 状态

        进入载荷 = dict(载荷) if isinstance(载荷, dict) else {}

        def _转文本(值) -> str:
            try:
                return str(值 or "").strip()
            except Exception:
                return ""

        def _写入状态(键名: str, 值):
            if 键名 == "加载页_载荷":
                if isinstance(值, dict):
                    状态[键名] = dict(值)
                return

            if 键名 in ("选歌原始索引", "选歌_恢复原始索引"):
                try:
                    状态[键名] = int(值)
                except Exception:
                    pass
                return

            if 键名 in ("选歌恢复详情页", "选歌_恢复详情页"):
                状态[键名] = bool(值)
                return

            if 键名 in ("选歌收藏夹模式", "选歌恢复收藏夹模式", "选歌_恢复收藏夹模式"):
                状态[键名] = bool(值)
                return

            if 键名 in ("选歌收藏夹页码", "选歌恢复收藏夹页码", "选歌_恢复收藏夹页码"):
                try:
                    状态[键名] = max(0, int(值))
                except Exception:
                    pass
                return

            文本 = _转文本(值)
            if 文本:
                状态[键名] = 文本

        if 进入载荷:
            _写入状态("songs根目录", 进入载荷.get("songs根目录", ""))
            _写入状态("外置songs根目录", 进入载荷.get("外置songs根目录", ""))
            _写入状态("选歌_BGM", 进入载荷.get("选歌_BGM", ""))
            _写入状态("加载页_载荷", 进入载荷.get("加载页_载荷", {}))
            _写入状态("选歌_恢复原始索引", 进入载荷.get("选歌原始索引", None))
            _写入状态("选歌_恢复详情页", 进入载荷.get("选歌恢复详情页", False))
            _写入状态(
                "选歌_恢复收藏夹模式",
                进入载荷.get(
                    "选歌收藏夹模式",
                    进入载荷.get("选歌恢复收藏夹模式", False),
                ),
            )
            _写入状态(
                "选歌_恢复收藏夹页码",
                进入载荷.get(
                    "选歌收藏夹页码",
                    进入载荷.get("选歌恢复收藏夹页码", None),
                ),
            )

            载荷选歌类型 = _转文本(进入载荷.get("选歌类型", ""))
            载荷选歌模式 = _转文本(进入载荷.get("选歌模式", ""))
            载荷类型 = _转文本(进入载荷.get("类型", ""))
            载荷模式 = _转文本(进入载荷.get("模式", ""))
            载荷大模式 = _转文本(进入载荷.get("大模式", ""))
            载荷子模式 = _转文本(进入载荷.get("子模式", ""))
            载荷songs子文件夹 = _转文本(进入载荷.get("songs子文件夹", ""))

            最终类型 = 载荷选歌类型 or 载荷大模式 or 载荷类型 or 载荷songs子文件夹
            最终模式 = 载荷选歌模式 or 载荷子模式 or 载荷模式

            if 最终类型:
                状态["选歌_类型"] = 最终类型
                状态["大模式"] = 最终类型
                状态["songs子文件夹"] = 最终类型

            if 最终模式:
                状态["选歌_模式"] = 最终模式
                状态["子模式"] = 最终模式

        songs根目录 = _取songs根目录(资源, 状态)
        运行根songs目录 = _公共取songs根目录(资源=资源, 状态={})
        if (
            songs根目录
            and os.path.isdir(str(songs根目录))
            and (not _目录含候选谱面文件(str(songs根目录), 最大命中数=1))
            and _目录含候选谱面文件(str(运行根songs目录), 最大命中数=1)
        ):
            _记录警告日志(
                _日志器,
                (
                    "选歌入口检测到状态中的songs根目录为空目录，已自动回退到运行根songs目录 "
                    f"原路径={songs根目录} 回退路径={运行根songs目录}"
                ),
            )
            songs根目录 = str(运行根songs目录)
        玩家数 = int(状态.get("玩家数", 1) or 1)

        类型名, 模式名 = _解析选歌入口参数(状态, songs根目录)

        def _取第一个存在的文件(*候选路径: str) -> str:
            return _公共取首个存在路径(*候选路径)

        try:
            状态["songs根目录"] = songs根目录
        except Exception:
            pass

        try:
            _记录信息日志(
                _日志器,
                (
                    "进入选歌场景 "
                    f"渲染后端={str(os.environ.get('E5CM_RENDER_BACKEND', '') or '-')} "
                    f"songs根目录={songs根目录} 类型={类型名 or '-'} 模式={模式名 or '-'}"
                ),
            )
        except Exception:
            pass

        try:
            self.上下文["音乐"].停止()
        except Exception:
            pass

        背景音乐路径 = str(状态.get("选歌_BGM", "") or "")
        if not os.path.isfile(背景音乐路径):
            背景音乐路径 = ""

        类型小写 = 类型名.strip().lower()
        模式小写 = 模式名.strip().lower()

        学习路径 = _取第一个存在的文件(
            str(资源.get("音乐_easy", "") or ""),
            _公共取冷资源路径("backsound", "easy.mp3"),
        )
        情侣路径 = _取第一个存在的文件(
            str(资源.get("音乐_lover", "") or ""),
            _公共取冷资源路径("backsound", "lover.mp3"),
        )

        if (("学习" in 模式名) or ("easy" in 模式小写)) and 学习路径:
            背景音乐路径 = 学习路径
        elif (("情侣" in 模式名) or ("lover" in 模式小写)) and 情侣路径:
            背景音乐路径 = 情侣路径

        if not 背景音乐路径:
            表演路径 = _取第一个存在的文件(
                str(资源.get("音乐_show", "") or ""),
                _公共取冷资源路径("backsound", "show.mp3"),
            )
            疯狂路径 = _取第一个存在的文件(
                str(资源.get("音乐_devil", "") or ""),
                _公共取冷资源路径("backsound", "devil.mp3"),
            )
            混音路径 = _取第一个存在的文件(
                str(资源.get("音乐_remix", "") or ""),
                _公共取冷资源路径("backsound", "remix.mp3"),
            )
            club路径 = _取第一个存在的文件(
                str(资源.get("音乐_club", "") or ""),
                _公共取冷资源路径("backsound", "club.mp3"),
            )

            if "表演" in 模式名 and 表演路径:
                背景音乐路径 = 表演路径
            elif "疯狂" in 模式名 and 疯狂路径:
                背景音乐路径 = 疯狂路径
            elif "混音" in 模式名 and 混音路径:
                背景音乐路径 = 混音路径
            elif (("club" in 模式小写) or ("双踏板" in 模式名)) and club路径:
                背景音乐路径 = club路径
            elif 类型小写 == "diy" and 表演路径:
                背景音乐路径 = 表演路径

        if not 背景音乐路径:
            背景音乐路径 = _取第一个存在的文件(
                str(资源.get("音乐_UI", "") or ""),
                str(资源.get("back_music_ui", "") or ""),
                str(资源.get("投币_BGM", "") or ""),
            )

        已启用稳定场景初始化模式 = bool(_启用稳定场景初始化模式())
        if 已启用稳定场景初始化模式:
            global _稳定场景初始化模式日志已输出
            if not bool(_稳定场景初始化模式日志已输出):
                try:
                    _记录信息日志(
                        _日志器,
                        "已启用稳定场景初始化模式：选歌实例创建期间暂时关闭循环GC",
                    )
                except Exception:
                    pass
                _稳定场景初始化模式日志已输出 = True
        曾关闭GC = _进入稳定GC区间(已启用稳定场景初始化模式)
        try:
            self._选歌实例 = 选歌游戏(
                songs根目录=songs根目录,
                背景音乐路径=背景音乐路径,
                指定类型名=类型名,
                指定模式名=模式名,
                玩家数=玩家数,
                是否继承已有窗口=True,
            )
        except Exception as 异常:
            _记录异常日志(
                _日志器,
                f"创建选歌实例失败 songs根目录={songs根目录} 类型={类型名} 模式={模式名}",
                异常,
            )
            self._选歌实例 = None
            raise
        finally:
            _离开稳定GC区间(曾关闭GC)
        try:
            self._选歌实例.上下文 = self.上下文
        except Exception:
            pass

        try:
            setattr(self._选歌实例, "_全局点击特效", None)
        except Exception:
            pass

        try:
            if hasattr(self._选歌实例, "绑定外部屏幕"):
                self._选歌实例.绑定外部屏幕(self.上下文["屏幕"])
        except Exception:
            pass

        try:
            恢复原始索引 = 状态.pop("选歌_恢复原始索引", None)
        except Exception:
            恢复原始索引 = None
        try:
            恢复详情页 = bool(状态.pop("选歌_恢复详情页", False))
        except Exception:
            恢复详情页 = False
        try:
            恢复收藏夹模式 = bool(状态.pop("选歌_恢复收藏夹模式", False))
        except Exception:
            恢复收藏夹模式 = False
        try:
            恢复收藏夹页码 = 状态.pop("选歌_恢复收藏夹页码", None)
            if 恢复收藏夹页码 is not None:
                恢复收藏夹页码 = max(0, int(恢复收藏夹页码))
        except Exception:
            恢复收藏夹页码 = None

        if (
            恢复收藏夹模式
            and self._选歌实例 is not None
            and hasattr(self._选歌实例, "_切换收藏夹模式")
        ):
            try:
                if not bool(getattr(self._选歌实例, "是否收藏夹模式", False)):
                    self._选歌实例._切换收藏夹模式()
            except Exception:
                pass

        if 恢复原始索引 is not None and self._选歌实例 is not None:
            try:
                原始列表 = self._选歌实例.当前原始歌曲列表()
            except Exception:
                原始列表 = []
            if 原始列表:
                try:
                    if int(恢复原始索引) < 0:
                        raise ValueError("restore index disabled")
                    恢复原始索引 = int(
                        max(0, min(int(恢复原始索引), len(原始列表) - 1))
                    )
                    self._选歌实例.当前选择原始索引 = 恢复原始索引
                    if 恢复详情页 and hasattr(self._选歌实例, "进入详情_原始索引"):
                        self._选歌实例.进入详情_原始索引(int(恢复原始索引))
                    else:
                        列表, 映射 = self._选歌实例.当前歌曲列表与映射()
                        if 映射:
                            try:
                                视图索引 = 映射.index(int(恢复原始索引))
                            except Exception:
                                视图索引 = 0
                            self._选歌实例.当前页 = max(
                                0, int(视图索引 // max(1, int(self._选歌实例.每页数量)))
                            )
                        self._选歌实例.是否详情页 = False
                        self._选歌实例.当前页卡片 = self._选歌实例.生成指定页卡片(
                            int(self._选歌实例.当前页)
                        )
                        self._选歌实例.安排预加载(基准页=int(self._选歌实例.当前页))
                except Exception:
                    pass

        if (
            恢复收藏夹模式
            and (not bool(恢复详情页))
            and (恢复收藏夹页码 is not None)
            and self._选歌实例 is not None
        ):
            try:
                总页数 = int(max(1, int(self._选歌实例.总页数())))
            except Exception:
                总页数 = 1
            目标页码 = max(0, min(int(恢复收藏夹页码), 总页数 - 1))
            try:
                self._选歌实例.当前页 = int(目标页码)
                self._选歌实例.当前页卡片 = self._选歌实例.生成指定页卡片(
                    int(self._选歌实例.当前页)
                )
                self._选歌实例.安排预加载(基准页=int(self._选歌实例.当前页))
                self._选歌实例._同步踏板卡片高亮()
            except Exception:
                pass

    def 退出(self):
        # ✅ 停止选歌里的 pygame.mixer.music，避免回到其它场景仍在播
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

        self._选歌实例 = None

    # ---- 帧更新 ----
    def 更新(self):
        if self._选歌实例 is None:
            return {"切换到": "子模式", "禁用黑屏过渡": True}

        # 同步屏幕（main.py resize 后会换 surface）
        try:
            if hasattr(self._选歌实例, "绑定外部屏幕"):
                self._选歌实例.绑定外部屏幕(self.上下文["屏幕"])
        except Exception:
            pass

        退出状态 = None
        try:
            if hasattr(self._选歌实例, "帧更新"):
                退出状态 = self._选歌实例.帧更新()
        except Exception as 异常:
            _记录异常日志(_日志器, "选歌场景帧更新异常", 异常)
            退出状态 = None

        if 退出状态:
            return self._根据退出状态切场景(str(退出状态))

        return None

    def 绘制(self):
        if self._选歌实例 is None:
            return
        try:
            if hasattr(self._选歌实例, "帧绘制"):
                self._选歌实例.帧绘制()
        except Exception as 异常:
            _记录异常日志(_日志器, "选歌场景帧绘制异常", 异常)
            # 防御：别让选歌绘制崩全局
            pass

    def 绘制GPU背景(self, 显示后端):
        if self._选歌实例 is None:
            return
        try:
            绘制方法 = getattr(self._选歌实例, "绘制GPU背景", None)
            if callable(绘制方法):
                绘制方法(显示后端)
        except Exception:
            pass

    def 绘制GPU中层(self, 显示后端):
        if self._选歌实例 is None:
            return
        try:
            绘制方法 = getattr(self._选歌实例, "绘制GPU中层", None)
            if callable(绘制方法):
                绘制方法(显示后端)
        except Exception:
            pass

    def 处理全局踏板(self, 动作: str):
        if self._选歌实例 is None:
            return None

        退出状态 = None
        try:
            if hasattr(self._选歌实例, "处理全局踏板"):
                退出状态 = self._选歌实例.处理全局踏板(动作)
        except Exception as 异常:
            _记录异常日志(_日志器, "选歌场景处理全局踏板异常", 异常)
            退出状态 = None

        if 退出状态:
            return self._根据退出状态切场景(str(退出状态))
        return None

    def 处理事件(self, 事件):
        if self._选歌实例 is None:
            return None

        退出状态 = None
        try:
            if hasattr(self._选歌实例, "处理事件_外部"):
                退出状态 = self._选歌实例.处理事件_外部(事件)
        except Exception as 异常:
            _记录异常日志(_日志器, "选歌场景处理事件异常", 异常)
            退出状态 = None

        if 退出状态:
            return self._根据退出状态切场景(str(退出状态))
        return None

    def _根据退出状态切场景(self, 退出状态: str):
        状态 = self.上下文.get("状态", {})
        if not isinstance(状态, dict):
            状态 = {}
            self.上下文["状态"] = 状态

        载荷 = {}
        if 退出状态 == "GO_LOADING":
            try:
                if self._选歌实例 is not None and hasattr(
                    self._选歌实例, "_加载页_载荷"
                ):
                    临时载荷 = getattr(self._选歌实例, "_加载页_载荷", None)
                    if isinstance(临时载荷, dict):
                        载荷 = dict(临时载荷)
            except Exception:
                载荷 = {}

            try:
                状态.pop("加载页_载荷", None)
            except Exception:
                pass

            try:
                载荷类型 = str(载荷.get("类型", "") or "").strip()
            except Exception:
                载荷类型 = ""
            try:
                载荷模式 = str(载荷.get("模式", "") or "").strip()
            except Exception:
                载荷模式 = ""

            if 载荷类型:
                状态["选歌_类型"] = 载荷类型
                状态["大模式"] = 载荷类型
                状态["songs子文件夹"] = 载荷类型

            if 载荷模式:
                状态["选歌_模式"] = 载荷模式
                状态["子模式"] = 载荷模式

            try:
                状态.pop("选歌_BGM", None)
            except Exception:
                pass

            return {"切换到": "加载页", "禁用黑屏过渡": True}

        if 退出状态 == "RESELECT_MAIN":
            try:
                # 明确“重选模式”语义：结束当前局流程，避免旧局数/奖励状态残留到新模式。
                重置游戏流程状态(状态)
                状态["songs子文件夹"] = ""
                状态.pop("选歌_恢复收藏夹模式", None)
                状态.pop("选歌_恢复收藏夹页码", None)
            except Exception:
                pass
            return {"切换到": "大模式", "禁用黑屏过渡": True}

        try:
            状态.pop("选歌_BGM", None)
        except Exception:
            pass

        return {"切换到": "子模式", "禁用黑屏过渡": True}


@dataclass
class 歌曲信息:
    序号: int
    类型: str
    模式: str
    歌曲文件夹: str
    歌曲路径: str
    sm路径: str
    mp3路径: Optional[str]
    封面路径: Optional[str]
    歌名: str
    星级: int
    bpm: Optional[int]
    是否VIP: bool = False
    游玩次数: int = 0
    是否NEW: bool = False
    是否HOT: bool = False
    是否收藏: bool = False
    是否带MV: bool = False
    谱面charttype: str = ""
    谱面模式标记: str = ""
    记录键sm路径: str = ""
    是否10位复合谱: bool = False


def _克隆歌曲信息对象(歌: 歌曲信息) -> 歌曲信息:
    return 歌曲信息(
        序号=int(getattr(歌, "序号", 0) or 0),
        类型=str(getattr(歌, "类型", "") or ""),
        模式=str(getattr(歌, "模式", "") or ""),
        歌曲文件夹=str(getattr(歌, "歌曲文件夹", "") or ""),
        歌曲路径=str(getattr(歌, "歌曲路径", "") or ""),
        sm路径=str(getattr(歌, "sm路径", "") or ""),
        mp3路径=str(getattr(歌, "mp3路径", "") or "") or None,
        封面路径=str(getattr(歌, "封面路径", "") or "") or None,
        歌名=str(getattr(歌, "歌名", "") or ""),
        星级=int(max(1, int(getattr(歌, "星级", 1) or 1))),
        bpm=getattr(歌, "bpm", None),
        是否VIP=bool(getattr(歌, "是否VIP", False)),
        游玩次数=int(max(0, int(getattr(歌, "游玩次数", 0) or 0))),
        是否NEW=bool(getattr(歌, "是否NEW", False)),
        是否HOT=bool(getattr(歌, "是否HOT", False)),
        是否收藏=bool(getattr(歌, "是否收藏", False)),
        是否带MV=bool(getattr(歌, "是否带MV", False)),
        谱面charttype=str(getattr(歌, "谱面charttype", "") or ""),
        谱面模式标记=str(getattr(歌, "谱面模式标记", "") or ""),
        记录键sm路径=str(getattr(歌, "记录键sm路径", "") or ""),
        是否10位复合谱=bool(getattr(歌, "是否10位复合谱", False)),
    )


def _克隆数据树(数据树: Dict[str, Dict[str, List[歌曲信息]]]) -> Dict[str, Dict[str, List[歌曲信息]]]:
    结果: Dict[str, Dict[str, List[歌曲信息]]] = {}
    if not isinstance(数据树, dict):
        return 结果
    for 类型名, 模式表 in 数据树.items():
        if not isinstance(模式表, dict):
            continue
        结果[str(类型名)] = {}
        for 模式名, 列表 in 模式表.items():
            if not isinstance(列表, list):
                continue
            结果[str(类型名)][str(模式名)] = [
                _克隆歌曲信息对象(歌)
                for 歌 in 列表
                if isinstance(歌, 歌曲信息)
            ]
    return 结果


def _读取歌曲扫描缓存(缓存键: Tuple[object, ...]) -> Optional[Dict[str, Dict[str, List[歌曲信息]]]]:
    if not isinstance(缓存键, tuple):
        return None
    with _歌曲扫描缓存锁:
        缓存值 = _歌曲扫描缓存.get(缓存键)
        if not isinstance(缓存值, dict):
            return None
        try:
            if 缓存键 in _歌曲扫描缓存顺序:
                _歌曲扫描缓存顺序.remove(缓存键)
        except Exception:
            pass
        _歌曲扫描缓存顺序.append(缓存键)
        return _克隆数据树(缓存值)


def _按前缀读取歌曲扫描缓存(
    键前缀: Tuple[object, ...]
) -> Optional[Dict[str, Dict[str, List[歌曲信息]]]]:
    if not isinstance(键前缀, tuple) or (not 键前缀):
        return None
    with _歌曲扫描缓存锁:
        候选键列表 = list(_歌曲扫描缓存顺序 or [])
    for 候选键 in reversed(候选键列表):
        if not isinstance(候选键, tuple):
            continue
        if len(候选键) < len(键前缀):
            continue
        if tuple(候选键[: len(键前缀)]) != tuple(键前缀):
            continue
        命中 = _读取歌曲扫描缓存(tuple(候选键))
        if 命中 is not None:
            return 命中
    return None


def _写入歌曲扫描缓存(缓存键: Tuple[object, ...], 数据树: Dict[str, Dict[str, List[歌曲信息]]]) -> None:
    if not isinstance(缓存键, tuple):
        return
    if not isinstance(数据树, dict):
        return
    with _歌曲扫描缓存锁:
        _歌曲扫描缓存[缓存键] = _克隆数据树(数据树)
        try:
            if 缓存键 in _歌曲扫描缓存顺序:
                _歌曲扫描缓存顺序.remove(缓存键)
        except Exception:
            pass
        _歌曲扫描缓存顺序.append(缓存键)
        while len(_歌曲扫描缓存顺序) > max(1, int(_歌曲扫描缓存上限)):
            旧键 = _歌曲扫描缓存顺序.pop(0)
            _歌曲扫描缓存.pop(旧键, None)


def 安全加载图片(路径: str, 透明: bool = True) -> Optional[pygame.Surface]:
    try:
        if (not 路径) or (not os.path.isfile(路径)):
            return None
        图 = pygame.image.load(路径)
        return 图.convert_alpha() if 透明 else 图.convert()
    except Exception:
        return None


def 处理透明像素_用左上角作为背景(原图: pygame.Surface) -> pygame.Surface:
    """
    用左上角像素颜色当背景色，做“色键抠图”，输出带 alpha 的新 Surface。
    适合：素材 PNG 没有透明通道，但背景是纯色（常见黑底/白底）。
    风险：如果左上角颜色属于有效内容，也会被误抠。
    """
    try:
        if 原图 is None:
            return 原图
        背景色 = 原图.get_at((0, 0))
        背景rgb = (int(背景色.r), int(背景色.g), int(背景色.b))

        临时 = 原图.convert()
        临时.set_colorkey(背景rgb)

        结果 = pygame.Surface(原图.get_size(), pygame.SRCALPHA)
        结果.fill((0, 0, 0, 0))
        结果.blit(临时, (0, 0))
        return 结果.convert_alpha()
    except Exception:
        try:
            return 原图.convert_alpha()
        except Exception:
            return 原图


_UI原图缓存: Dict[str, Optional[pygame.Surface]] = {}
# _UI缩放缓存: Dict[Tuple[str, int, int, bool], Optional[pygame.Surface]] = {}

_缩略图_序号背景_缩放 = 1.5  
_缩略图_序号背景_x偏移 = 20  
_缩略图_序号背景_y偏移 = -20  
_缩略图_序号数字_缩放 = 1.6  
_缩略图_序号数字_x偏移 = -20 
_缩略图_序号数字_y偏移 = -20 
_缩略图_序号数字_右内边距占比 = 0.12  
_缩略图_序号数字_下内边距占比 = 0.12  
_大图_序号背景_缩放 = 1.70
_大图_序号背景_x偏移 = 0
_大图_序号背景_y偏移 = 0
_大图_序号数字_缩放 = 1.00
_大图_序号数字_x偏移 = 10
_大图_序号数字_y偏移 = 10
_详情大框贴图_宽缩放 = 1.07
_详情大框贴图_高缩放 = 1.02
_详情大框贴图_x偏移 = 0
_详情大框贴图_y偏移 = 0.01
_序号显示格式_缩略图 = "{:02d}"  # 01 02 03...
_序号显示格式_大图 = "{:02d}"  # 想大图显示不一样也行
_缩略图槽位参数 = {
    "封面左占比": 0.10,
    "封面上占比": 0.045,
    "封面宽占比": 0.845,
    "封面高占比": 0.940,
    "信息条高占比": 0.315,
    "信息条左右内边距占比": 0.035,
    "星区上内边距占比": 0.0,
    "星区高占比": 0.34,
    "文本区左右内边距占比": 0.040,
    "底栏高占比": 0.22,
    "底栏底部留白占比": 0.18,
}
_大图槽位参数 = {
    "封面左占比": 0.05,
    "封面上占比": 0.02,
    "封面宽占比": 0.95,
    "封面高占比": 1.0,
    "信息条高占比": 0.35,
    "信息条左右内边距占比": 0.040,
    "星区上内边距占比": 0.050,
    "星区高占比": 0.3,
    "文本区左右内边距占比": 0.050,
    "底栏高占比": 0.245,
    "底栏底部留白占比": 0.06,
}
_缩略图可视底设计像素 = 231.0
_缩略图框体设计高 = 256.0
_缩略图信息条锚点 = "visible"
_小图文字样式参数 = {
    "歌名字号占框高比": 0.10,
    "歌名最小字号": 8.0,
    "歌名字号相对BPM增量": 2.0,
    "游玩次数标签字号占信息条高比": 0.16,
    "游玩次数数字字号占信息条高比": 0.18,
    "BPM字号占信息条高比": 0.20,
    "游玩次数最小字号": 7.0,
    "BPM最小字号": 8.0,
}
_大图文字样式参数 = {
    "歌名字号占信息条高比": 0.22,
    "歌名最小字号": 16.0,
    "底栏字号占信息条高比": 0.13,
    "底栏最小字号": 12.0,
}


def _设置页_配置项定义() -> Dict[str, Dict[str, str]]:
    return {
        "调速": {
            "索引属性": "设置_调速索引",
            "选项属性": "设置_调速选项",
            "参数键": "调速",
            "值前缀": "X",
        },
        "变速": {
            "索引属性": "设置_变速索引",
            "选项属性": "设置_变速选项",
            "参数键": "背景模式",
            "兼容参数键": "变速",
        },
        "变速类型": {
            "索引属性": "设置_谱面索引",
            "选项属性": "设置_谱面选项",
            "参数键": "谱面",
            "兼容参数键": "变速类型",
        },
        "隐藏": {
            "索引属性": "设置_隐藏索引",
            "选项属性": "设置_隐藏选项",
            "参数键": "隐藏",
        },
        "轨迹": {
            "索引属性": "设置_轨迹索引",
            "选项属性": "设置_轨迹选项",
            "参数键": "轨迹",
        },
        "方向": {
            "索引属性": "设置_方向索引",
            "选项属性": "设置_方向选项",
            "参数键": "方向",
        },
        "大小": {
            "索引属性": "设置_大小索引",
            "选项属性": "设置_大小选项",
            "参数键": "大小",
        },
        "箭头": {
            "索引属性": "设置_箭头索引",
            "选项属性": "设置_箭头候选路径列表",
            "参数键": "箭头",
            "值类型": "文件名",
        },
        "背景": {
            "索引属性": "设置_背景索引",
            "选项属性": "设置_背景大图文件名列表",
            "参数键": "背景",
            "值类型": "原值",
        },
    }

def _设置页_持久化文件路径(self) -> str:
    return _取运行存储路径()

def _设置页_从参数文本提取(参数文本: str, 键名: str) -> str:
    return 设置参数文本提取值(str(参数文本 or ""), str(键名 or ""))

def _取当前对局关卡(self, 默认值: int = 1) -> int:
    try:
        上下文 = getattr(self, "上下文", {})
    except Exception:
        上下文 = {}
    状态 = {}
    if isinstance(上下文, dict):
        值 = 上下文.get("状态", {})
        if isinstance(值, dict):
            状态 = 值
    try:
        当前关卡 = int(取当前关卡(状态, int(默认值 or 1)) or 默认值)
    except Exception:
        当前关卡 = int(默认值 or 1)
    return max(1, int(当前关卡))

def _规范化关卡背景映射(
    原始映射: Optional[dict],
    可用背景文件名列表: Optional[List[str]] = None,
) -> Dict[str, str]:
    if not isinstance(原始映射, dict):
        return {}
    可用集合: Optional[Set[str]] = None
    if isinstance(可用背景文件名列表, list) and 可用背景文件名列表:
        可用集合 = {
            str(文件名 or "").strip()
            for 文件名 in 可用背景文件名列表
            if str(文件名 or "").strip()
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
        if 可用集合 is not None and 文件名 not in 可用集合:
            continue
        输出[str(int(关卡))] = 文件名
    return 输出

def _同步关卡背景状态(self, 关卡背景映射: Optional[dict] = None):
    try:
        上下文 = getattr(self, "上下文", {})
    except Exception:
        上下文 = {}
    if not isinstance(上下文, dict):
        return
    状态 = 上下文.get("状态", {})
    if not isinstance(状态, dict):
        return
    if not isinstance(关卡背景映射, dict):
        关卡背景映射 = getattr(self, "设置_背景文件名按关卡", {})
    状态["对局_关卡背景图"] = _规范化关卡背景映射(关卡背景映射)

def _读取关卡背景映射(
    self,
    持久化数据: Optional[dict] = None,
    可用背景文件名列表: Optional[List[str]] = None,
) -> Dict[str, str]:
    候选映射 = getattr(self, "设置_背景文件名按关卡", {})
    if not isinstance(候选映射, dict):
        候选映射 = {}
    if (not 候选映射) and isinstance(持久化数据, dict):
        try:
            值 = 持久化数据.get("背景文件名_按关卡", {})
            if isinstance(值, dict):
                候选映射 = dict(值)
        except Exception:
            候选映射 = {}
    if not 候选映射:
        try:
            上下文 = getattr(self, "上下文", {})
        except Exception:
            上下文 = {}
        if isinstance(上下文, dict):
            状态 = 上下文.get("状态", {})
            if isinstance(状态, dict):
                值 = 状态.get("对局_关卡背景图", {})
                if isinstance(值, dict):
                    候选映射 = dict(值)
    关卡背景映射 = _规范化关卡背景映射(
        候选映射,
        可用背景文件名列表=可用背景文件名列表,
    )
    self.设置_背景文件名按关卡 = dict(关卡背景映射)
    _同步关卡背景状态(self, 关卡背景映射)
    return dict(关卡背景映射)

def _图片幻灯片模式是否开启(self, 默认值: bool = True) -> bool:
    try:
        esc数据 = _读取存储作用域(_游戏esc菜单设置存储作用域)
    except Exception:
        esc数据 = {}
    if not isinstance(esc数据, dict):
        return bool(默认值)
    if _游戏esc图片幻灯片模式键 not in esc数据:
        return bool(默认值)
    return bool(esc数据.get(_游戏esc图片幻灯片模式键))

def _按关卡解析图片背景文件名(
    self,
    背景文件名: str,
    背景模式: str,
    持久化数据: Optional[dict] = None,
    自动补全: bool = False,
    可用背景文件名列表: Optional[List[str]] = None,
) -> str:
    模式文本 = str(背景模式 or "图片").strip()
    if 模式文本 != "图片":
        return str(背景文件名 or "").strip()

    if isinstance(可用背景文件名列表, list):
        可用背景文件名列表 = [
            str(文件名 or "").strip()
            for 文件名 in 可用背景文件名列表
            if str(文件名 or "").strip()
        ]
    else:
        可用背景文件名列表 = list(getattr(self, "设置_背景大图文件名列表", []) or [])
    关卡背景映射 = _读取关卡背景映射(
        self,
        持久化数据=持久化数据,
        可用背景文件名列表=可用背景文件名列表 if 可用背景文件名列表 else None,
    )
    当前关卡 = _取当前对局关卡(self, 1)
    关卡键 = str(int(当前关卡))
    图片幻灯片模式开启 = bool(_图片幻灯片模式是否开启(self, 默认值=True))

    # 图片模式下按关卡轮询背景图：第N局使用列表中的第N张（超出后循环）
    if bool(图片幻灯片模式开启) and 可用背景文件名列表:
        轮询背景 = str(
            可用背景文件名列表[
                int((int(当前关卡) - 1) % len(可用背景文件名列表))
            ]
            or ""
        ).strip()
        if 轮询背景:
            已更新 = str(关卡背景映射.get(关卡键, "") or "").strip() != 轮询背景
            if 已更新:
                关卡背景映射[关卡键] = str(轮询背景)
                self.设置_背景文件名按关卡 = dict(关卡背景映射)
                _同步关卡背景状态(self, 关卡背景映射)
                if bool(自动补全):
                    try:
                        _写入存储作用域(
                            _选歌设置存储作用域,
                            {
                                "背景文件名_按关卡": dict(关卡背景映射),
                                "背景文件名": str(轮询背景),
                            },
                        )
                    except Exception:
                        pass
            return 轮询背景

    选中背景 = str(关卡背景映射.get(关卡键, "") or "").strip()
    if not bool(图片幻灯片模式开启):
        选中背景 = str(背景文件名 or "").strip() or 选中背景
        if (not 选中背景) and 可用背景文件名列表:
            选中背景 = str(可用背景文件名列表[0] or "").strip()
        if bool(自动补全) and 选中背景:
            已更新 = str(关卡背景映射.get(关卡键, "") or "").strip() != 选中背景
            if 已更新:
                关卡背景映射[关卡键] = str(选中背景)
                self.设置_背景文件名按关卡 = dict(关卡背景映射)
                _同步关卡背景状态(self, 关卡背景映射)
                try:
                    _写入存储作用域(
                        _选歌设置存储作用域,
                        {
                            "背景文件名_按关卡": dict(关卡背景映射),
                            "背景文件名": str(选中背景),
                        },
                    )
                except Exception:
                    pass
    if (not 选中背景) and bool(自动补全):
        候选背景 = str(背景文件名 or "").strip()
        if 可用背景文件名列表 and 候选背景 not in 可用背景文件名列表:
            候选背景 = ""
        if (not 候选背景) and 可用背景文件名列表:
            候选背景 = str(
                可用背景文件名列表[
                    int((int(当前关卡) - 1) % len(可用背景文件名列表))
                ]
                or ""
            ).strip()
        if 候选背景:
            关卡背景映射[关卡键] = 候选背景
            self.设置_背景文件名按关卡 = dict(关卡背景映射)
            _同步关卡背景状态(self, 关卡背景映射)
            try:
                _写入存储作用域(
                    _选歌设置存储作用域,
                    {
                        "背景文件名_按关卡": dict(关卡背景映射),
                        "背景文件名": str(候选背景),
                    },
                )
            except Exception:
                pass
            选中背景 = 候选背景

    if 选中背景:
        return 选中背景
    return str(背景文件名 or "").strip()

def _关卡背景映射签名(关卡背景映射: Optional[dict]) -> str:
    try:
        return json.dumps(
            _规范化关卡背景映射(关卡背景映射),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except Exception:
        return ""

def _设置页_构建参数文本(
    self,
    设置参数: Optional[dict] = None,
    背景文件名: str = "",
    箭头文件名: str = "",
) -> str:
    return 构建设置参数文本(
        settings_params=设置参数,
        background_filename=背景文件名,
        arrow_filename=箭头文件名,
    )

def _设置页_读取持久化设置(self) -> dict:
    数据 = _读取存储作用域(_选歌设置存储作用域)
    return dict(数据) if isinstance(数据, dict) else {}

def _设置页_写入持久化设置(self, 数据: dict) -> bool:
    try:
        新数据 = _写入存储作用域(_选歌设置存储作用域, dict(数据 or {}))
        return isinstance(新数据, dict)
    except Exception:
        return False


def _设置页_提取同步快照(数据: Optional[dict]) -> dict:
    原始 = dict(数据 or {}) if isinstance(数据, dict) else {}
    参数 = 原始.get("设置参数", {})
    if not isinstance(参数, dict):
        参数 = {}
    索引 = 原始.get("索引", {})
    if not isinstance(索引, dict):
        索引 = {}
    return {
        "设置参数": dict(参数),
        "设置参数文本": str(原始.get("设置参数文本", "") or ""),
        "动态背景": str(原始.get("动态背景", "") or ""),
        "背景文件名": str(原始.get("背景文件名", "") or ""),
        "背景文件名_按关卡": _规范化关卡背景映射(
            原始.get("背景文件名_按关卡", {})
        ),
        "视频背景文件名": str(原始.get("视频背景文件名", "") or ""),
        "箭头文件名": str(原始.get("箭头文件名", "") or ""),
        "索引": dict(索引),
    }


def _设置页_计算同步签名(数据: Optional[dict]) -> str:
    try:
        return json.dumps(
            _设置页_提取同步快照(数据),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except Exception:
        return ""


def _设置页_同步外部持久化设置(
    self,
    强制: bool = False,
    刷新界面: bool = True,
) -> bool:
    if not hasattr(self, "设置_调速选项"):
        return False

    try:
        当前秒 = float(time.perf_counter())
    except Exception:
        当前秒 = 0.0

    if (not bool(强制)) and (
        当前秒
        - float(getattr(self, "_设置页_同步最近读取时间", -999.0) or -999.0)
    ) < 0.20:
        return False
    self._设置页_同步最近读取时间 = 当前秒

    try:
        数据 = _设置页_读取持久化设置(self)
    except Exception:
        数据 = {}

    新签名 = _设置页_计算同步签名(数据)
    旧签名 = str(getattr(self, "_设置页_最近持久化签名", "") or "")
    if (not bool(强制)) and 新签名 == 旧签名:
        return False

    try:
        旧参数 = dict(getattr(self, "设置_参数", {}) or {})
    except Exception:
        旧参数 = {}
    旧背景状态 = (
        str(旧参数.get("背景模式", 旧参数.get("变速", "图片")) or "图片").strip(),
        str(旧参数.get("动态背景", "关闭") or "关闭").strip(),
        str(getattr(self, "设置_背景大图文件名", "") or "").strip(),
        _关卡背景映射签名(getattr(self, "设置_背景文件名按关卡", {})),
    )
    旧箭头文件名 = str(getattr(self, "设置_箭头文件名", "") or "").strip()

    try:
        self._设置页_加载持久化设置()
    except Exception:
        pass
    try:
        self._设置页_同步参数()
    except Exception:
        pass

    self._设置页_最近持久化签名 = str(新签名 or "")

    try:
        新参数 = dict(getattr(self, "设置_参数", {}) or {})
    except Exception:
        新参数 = {}
    新背景状态 = (
        str(新参数.get("背景模式", 新参数.get("变速", "图片")) or "图片").strip(),
        str(新参数.get("动态背景", "关闭") or "关闭").strip(),
        str(getattr(self, "设置_背景大图文件名", "") or "").strip(),
        _关卡背景映射签名(getattr(self, "设置_背景文件名按关卡", {})),
    )
    新箭头文件名 = str(getattr(self, "设置_箭头文件名", "") or "").strip()

    背景已变更 = 旧背景状态 != 新背景状态
    展示已变更 = bool(背景已变更 or 旧箭头文件名 != 新箭头文件名)

    if 背景已变更:
        try:
            self._加载背景图()
        except Exception:
            pass

    if bool(刷新界面) and 展示已变更:
        try:
            self._设置页_上次屏幕尺寸 = (0, 0)
            self._设置页_最后绘制表面 = None
            self._设置页_最后缩放 = 1.0
        except Exception:
            pass
        if bool(getattr(self, "是否设置页", False)):
            try:
                self._重算设置页布局(强制=True)
            except Exception:
                pass

    return True

def _设置页_加载持久化设置(self):
    数据 = _设置页_读取持久化设置(self)
    if not isinstance(数据, dict) or (not 数据):
        return

    配置定义 = _设置页_配置项定义()
    索引表 = 数据.get("索引", {})
    if not isinstance(索引表, dict):
        索引表 = {}

    参数 = 数据.get("设置参数", {})
    if not isinstance(参数, dict):
        参数 = {}

    参数文本 = str(数据.get("设置参数文本", "") or "")
    背景文件名 = str(数据.get("背景文件名", 参数.get("背景", "")) or "")
    箭头文件名 = str(数据.get("箭头文件名", 参数.get("箭头", "")) or "")
    背景模式 = str(
        参数.get(
            "背景模式",
            参数.get("变速", _设置页_从参数文本提取(参数文本, "背景模式")),
        )
        or "图片"
    ).strip()
    关卡背景映射 = _规范化关卡背景映射(
        数据.get("背景文件名_按关卡", {}),
        可用背景文件名列表=list(getattr(self, "设置_背景大图文件名列表", []) or []),
    )
    self.设置_背景文件名按关卡 = dict(关卡背景映射)
    if 背景模式 == "图片":
        当前关卡键 = str(int(_取当前对局关卡(self, 1)))
        背景文件名 = str(关卡背景映射.get(当前关卡键, 背景文件名) or 背景文件名)
    _同步关卡背景状态(self, 关卡背景映射)

    if not 背景文件名:
        背景文件名 = _设置页_从参数文本提取(参数文本, "背景")
    if not 箭头文件名:
        箭头文件名 = _设置页_从参数文本提取(参数文本, "箭头")

    for 行键, 定义 in 配置定义.items():
        索引属性 = str(定义.get("索引属性", "") or "")
        选项属性 = str(定义.get("选项属性", "") or "")
        参数键 = str(定义.get("参数键", "") or "")
        兼容参数键 = str(定义.get("兼容参数键", "") or "")
        值类型 = str(定义.get("值类型", "") or "")

        选项列表 = list(getattr(self, 选项属性, []) or [])
        if (not 索引属性) or (not 选项列表):
            continue

        默认索引 = int(getattr(self, 索引属性, 0) or 0)

        try:
            索引值 = int(索引表.get(参数键, 索引表.get(兼容参数键, 默认索引)) or 默认索引)
        except Exception:
            索引值 = 默认索引
        索引值 = max(0, min(len(选项列表) - 1, 索引值))
        setattr(self, 索引属性, 索引值)

        候选值 = ""
        if 值类型 == "文件名":
            候选值 = 箭头文件名
        elif 值类型 == "原值":
            候选值 = 背景文件名
        elif 参数键 == "背景模式":
            候选值 = 背景模式
        else:
            候选值 = str(参数.get(参数键, 参数.get(兼容参数键, "")) or "").strip()

        if 参数键 == "调速" and 候选值:
            候选值 = nearest_select_scroll_speed_option(
                候选值,
                default=DEFAULT_SELECT_SCROLL_SPEED_OPTION,
            )

        if not 候选值:
            continue

        if 值类型 == "文件名":
            for 序号, 路径 in enumerate(选项列表):
                if os.path.basename(str(路径 or "")) == 候选值:
                    setattr(self, 索引属性, int(序号))
                    break
            continue

        try:
            命中索引 = 选项列表.index(候选值)
            setattr(self, 索引属性, int(命中索引))
        except Exception:
            pass

def _设置页_保存持久化设置(self) -> bool:
    try:
        self._设置页_同步外部持久化设置(强制=False, 刷新界面=False)
    except Exception:
        pass

    配置定义 = _设置页_配置项定义()

    设置参数 = dict(getattr(self, "设置_参数", {}) or {})
    背景文件名 = str(getattr(self, "设置_背景大图文件名", "") or "")
    箭头文件名 = str(getattr(self, "设置_箭头文件名", "") or "")
    背景文件名按关卡 = _规范化关卡背景映射(
        getattr(self, "设置_背景文件名按关卡", {}),
        可用背景文件名列表=list(getattr(self, "设置_背景大图文件名列表", []) or []),
    )
    self.设置_背景文件名按关卡 = dict(背景文件名按关卡)
    _同步关卡背景状态(self, 背景文件名按关卡)

    索引表: Dict[str, int] = {}
    for _行键, 定义 in 配置定义.items():
        索引属性 = str(定义.get("索引属性", "") or "")
        参数键 = str(定义.get("参数键", "") or "")
        兼容参数键 = str(定义.get("兼容参数键", "") or "")
        if (not 索引属性) or (not 参数键):
            continue

        try:
            当前索引 = int(getattr(self, 索引属性, 0) or 0)
        except Exception:
            当前索引 = 0

        索引表[参数键] = 当前索引
        if 兼容参数键:
            索引表[兼容参数键] = 当前索引

    数据 = {
        "设置参数": 设置参数,
        "动态背景": str(设置参数.get("动态背景", "关闭") or "关闭"),
        "背景文件名": 背景文件名,
        "背景文件名_按关卡": dict(背景文件名按关卡),
        "箭头文件名": 箭头文件名,
        "设置参数文本": _设置页_构建参数文本(
            self,
            设置参数=设置参数,
            背景文件名=背景文件名,
            箭头文件名=箭头文件名,
        ),
        "索引": 索引表,
    }
    结果 = _设置页_写入持久化设置(self, 数据)
    if bool(结果):
        try:
            self._设置页_最近持久化签名 = _设置页_计算同步签名(
                _设置页_读取持久化设置(self)
            )
        except Exception:
            self._设置页_最近持久化签名 = _设置页_计算同步签名(数据)
    return bool(结果)


def _确保设置页资源(self):
    if getattr(self, "_设置页_资源已初始化", False):
        return
    self._设置页_资源已初始化 = True

    self.是否设置页 = False
    self._设置页_打开开始时间 = 0.0
    self._设置页_关闭开始时间 = 0.0
    self._设置页_打开动画时长 = 0.28
    self._设置页_关闭动画时长 = 0.22
    self._设置页_动画状态 = "closed"
    self._设置页_面板基础矩形 = pygame.Rect(0, 0, 10, 10)
    self._设置页_面板绘制矩形 = pygame.Rect(0, 0, 10, 10)
    self._设置页_最后绘制表面 = None
    self._设置页_最后缩放 = 1.0
    self._设置页_上次屏幕尺寸 = (0, 0)
    self._设置页_布局缩放 = 1.0

    self.设置_调速选项 = 设置菜单默认调速选项()
    self.设置_变速选项 = ["图片", "视频", "动态背景"]
    self.设置_谱面选项 = ["正常", "未知"]
    self.设置_隐藏选项 = ["关闭", "半隐", "全隐"]
    self.设置_轨迹选项 = ["正常", "摇摆", "旋转"]
    self.设置_方向选项 = ["关闭", "反向"]
    self.设置_大小选项 = ["正常", "放大"]

    self.设置_调速索引 = get_default_select_scroll_speed_index()
    self.设置_变速索引 = 0
    self.设置_谱面索引 = 0
    self.设置_隐藏索引 = 0
    self.设置_轨迹索引 = 0
    self.设置_方向索引 = 0
    self.设置_大小索引 = 0
    self.设置_箭头索引 = 0
    self.设置_背景索引 = 0

    self.设置_箭头候选路径列表 = []
    self._设置页_箭头候选原图缓存 = {}
    箭头候选目录 = _资源路径("UI-img", "选歌界面资源", "设置", "设置-箭头候选")
    if os.path.isdir(箭头候选目录):
        for 文件名 in sorted(os.listdir(箭头候选目录)):
            if str(文件名 or "").lower().endswith(".png"):
                self.设置_箭头候选路径列表.append(os.path.join(箭头候选目录, 文件名))

    self.设置_背景缩略图路径列表 = []
    self.设置_背景大图文件名列表 = []
    self._设置页_背景缩略图原图缓存 = {}

    背景目录 = _资源路径("冷资源", "backimages", "背景图")
    if os.path.isdir(背景目录):
        支持后缀 = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
        for 文件名 in sorted(os.listdir(背景目录)):
            小写名 = str(文件名 or "").lower()
            if not 小写名.endswith(支持后缀):
                continue
            绝对路径 = os.path.join(背景目录, 文件名)
            if not os.path.isfile(绝对路径):
                continue
            self.设置_背景缩略图路径列表.append(绝对路径)
            self.设置_背景大图文件名列表.append(str(文件名))

    self.设置_参数 = {}
    self.设置_背景大图文件名 = ""
    self.设置_背景文件名按关卡 = {}
    self.设置_箭头文件名 = ""
    self._设置页_同步最近读取时间 = -999.0
    self._设置页_最近持久化签名 = ""

    try:
        self._设置页_加载持久化设置()
    except Exception:
        pass

    self._设置页_同步参数()

    try:
        self._设置页_保存持久化设置()
    except Exception:
        pass
    try:
        self._设置页_最近持久化签名 = _设置页_计算同步签名(
            self._设置页_读取持久化设置()
        )
    except Exception:
        self._设置页_最近持久化签名 = ""

    self._设置页_缩放缓存 = {}
    self._设置页_背景图原图 = 安全加载图片(
        _资源路径("UI-img", "选歌界面资源", "设置", "设置背景图.png"),
        透明=True,
    )
    self._设置页_动态背景预览原图 = 安全加载图片(
        _资源路径("UI-img", "动态背景", "唱片", "素材", "唱片.png"),
        透明=True,
    )

    self._设置页_左小箭头原图 = 安全加载图片(
        _资源路径("UI-img", "选歌界面资源", "设置", "左小箭头.png"),
        透明=True,
    )
    self._设置页_右小箭头原图 = 安全加载图片(
        _资源路径("UI-img", "选歌界面资源", "设置", "右小箭头.png"),
        透明=True,
    )
    if self._设置页_右小箭头原图 is None and self._设置页_左小箭头原图 is not None:
        try:
            self._设置页_右小箭头原图 = pygame.transform.flip(
                self._设置页_左小箭头原图, True, False
            )
        except Exception:
            self._设置页_右小箭头原图 = None

    self._设置页_左大箭头原图 = 安全加载图片(
        _资源路径("UI-img", "选歌界面资源", "设置", "左大箭头.png"),
        透明=True,
    )
    self._设置页_右大箭头原图 = 安全加载图片(
        _资源路径("UI-img", "选歌界面资源", "设置", "右大箭头.png"),
        透明=True,
    )
    if self._设置页_右大箭头原图 is None and self._设置页_左大箭头原图 is not None:
        try:
            self._设置页_右大箭头原图 = pygame.transform.flip(
                self._设置页_左大箭头原图, True, False
            )
        except Exception:
            self._设置页_右大箭头原图 = None

    self._设置页_行矩形表 = {}
    self._设置页_控件矩形表 = {}
    self._设置页_背景区矩形 = pygame.Rect(0, 0, 10, 10)
    self._设置页_背景控件矩形 = {
        "左": pygame.Rect(0, 0, 1, 1),
        "右": pygame.Rect(0, 0, 1, 1),
        "预览": pygame.Rect(0, 0, 1, 1),
    }
    self._设置页_箭头预览矩形 = pygame.Rect(0, 0, 10, 10)
    self._设置页_箭头预览控件矩形 = {
        "左": pygame.Rect(0, 0, 1, 1),
        "右": pygame.Rect(0, 0, 1, 1),
    }

    self._设置页_背景缩放缓存图 = None
    self._设置页_背景缩放缓存尺寸 = (0, 0)

    设置页调试路径 = _公共取布局配置路径(
        "选歌设置页调试.json", 根目录=_取运行根目录()
    )
    if not os.path.isfile(设置页调试路径):
        设置页调试路径 = _公共取调试配置路径(
            "选歌设置页调试.json", 根目录=_取运行根目录()
        )
    self._设置页_调试器 = 设置页布局调试器(设置页调试路径, 获取字体)
    

def _设置页_同步参数(self):
    配置定义 = _设置页_配置项定义()
    输出参数: Dict[str, str] = {}

    for 行键, 定义 in 配置定义.items():
        索引属性 = str(定义.get("索引属性", "") or "")
        选项属性 = str(定义.get("选项属性", "") or "")
        参数键 = str(定义.get("参数键", "") or "")
        值前缀 = str(定义.get("值前缀", "") or "")
        值类型 = str(定义.get("值类型", "") or "")

        选项列表 = list(getattr(self, 选项属性, []) or [])
        if (not 参数键) or (not 选项列表):
            continue

        try:
            当前索引 = int(getattr(self, 索引属性, 0) or 0)
        except Exception:
            当前索引 = 0
        当前索引 = max(0, min(len(选项列表) - 1, 当前索引))

        当前值 = 选项列表[当前索引]

        if 值类型 == "文件名":
            当前值 = os.path.basename(str(当前值 or ""))
        else:
            当前值 = str(当前值 or "")

        if 参数键 == "箭头":
            self.设置_箭头文件名 = 当前值
        elif 参数键 == "背景":
            self.设置_背景大图文件名 = 当前值
            关卡背景映射 = _规范化关卡背景映射(
                getattr(self, "设置_背景文件名按关卡", {}),
                可用背景文件名列表=list(getattr(self, "设置_背景大图文件名列表", []) or []),
            )
            当前关卡键 = str(int(_取当前对局关卡(self, 1)))
            if 当前值:
                关卡背景映射[当前关卡键] = str(当前值)
            else:
                关卡背景映射.pop(当前关卡键, None)
            self.设置_背景文件名按关卡 = dict(关卡背景映射)
        elif 参数键 == "背景模式":
            旧参数 = getattr(self, "设置_参数", {})
            if not isinstance(旧参数, dict):
                旧参数 = {}
            输出参数["背景模式"] = 当前值
            if 当前值 == "动态背景":
                动态背景模式 = DynamicBackgroundManager.normalize_mode(
                    str(旧参数.get("动态背景", "关闭") or "关闭")
                )
                输出参数["动态背景"] = (
                    动态背景模式 if 动态背景模式 != "关闭" else "唱片"
                )
            else:
                输出参数["动态背景"] = "关闭"
        elif 参数键 == "调速":
            输出参数[参数键] = format_select_scroll_speed(当前值, prefix=值前缀 or "X")
        else:
            输出参数[参数键] = f"{值前缀}{当前值}" if 值前缀 else 当前值

    if not hasattr(self, "设置_箭头文件名"):
        self.设置_箭头文件名 = ""
    if not hasattr(self, "设置_背景大图文件名"):
        self.设置_背景大图文件名 = ""
    if not hasattr(self, "设置_背景文件名按关卡"):
        self.设置_背景文件名按关卡 = {}

    self.设置_参数 = 输出参数
    _同步关卡背景状态(self)

def _设置页_取缩放图(
    self, 缓存键前缀: str, 原图: Optional[pygame.Surface], 目标宽: int, 目标高: int
) -> Optional[pygame.Surface]:
    if 原图 is None:
        return None
    目标宽 = max(1, int(目标宽))
    目标高 = max(1, int(目标高))
    缓存键 = (str(缓存键前缀), 目标宽, 目标高)

    if 缓存键 in self._设置页_缩放缓存:
        return self._设置页_缩放缓存.get(缓存键)

    try:
        缩放图 = pygame.transform.smoothscale(原图, (目标宽, 目标高)).convert_alpha()
    except Exception:
        缩放图 = None

    self._设置页_缩放缓存[缓存键] = 缩放图
    return 缩放图

def _设置页_缓出(self, 进度: float) -> float:
    try:
        进度 = float(进度)
    except Exception:
        进度 = 1.0
    if 进度 < 0.0:
        进度 = 0.0
    if 进度 > 1.0:
        进度 = 1.0
    # easeOutQuad
    return 1.0 - (1.0 - 进度) * (1.0 - 进度)

def _设置页_缓入(self, 进度: float) -> float:
    try:
        进度 = float(进度)
    except Exception:
        进度 = 1.0
    if 进度 < 0.0:
        进度 = 0.0
    if 进度 > 1.0:
        进度 = 1.0
    return 进度 * 进度 * 进度

def _设置页_立即隐藏(self):
    self.是否设置页 = False
    self._设置页_动画状态 = "closed"
    self._设置页_最后绘制表面 = None

def _设置页_取动画参数(self) -> dict:
    if not bool(getattr(self, "是否设置页", False)):
        return {"是否可见": False}

    现在 = time.time()
    状态 = str(getattr(self, "_设置页_动画状态", "open") or "open")

    if 状态 == "closing":
        开始 = float(getattr(self, "_设置页_关闭开始时间", 0.0) or 0.0)
        时长 = float(getattr(self, "_设置页_关闭动画时长", 0.22) or 0.22)
        if 开始 <= 0.0 or 时长 <= 0.0:
            _设置页_立即隐藏(self)
            return {"是否可见": False}

        进度 = (现在 - 开始) / max(0.001, 时长)
        if 进度 >= 1.0:
            _设置页_立即隐藏(self)
            return {"是否可见": False}

        缓进度 = self._设置页_缓入(进度)
        return {
            "是否可见": True,
            "缩放": 1.0 - 0.05 * 缓进度,
            "透明度": 1.0 - 缓进度,
            "遮罩透明度": 170 * (1.0 - 缓进度),
            "y偏移": int(20 * 缓进度),
        }

    开始 = float(getattr(self, "_设置页_打开开始时间", 0.0) or 0.0)
    时长 = float(getattr(self, "_设置页_打开动画时长", 0.28) or 0.28)
    if 开始 <= 0.0 or 时长 <= 0.0:
        self._设置页_动画状态 = "open"
        return {
            "是否可见": True,
            "缩放": 1.0,
            "透明度": 1.0,
            "遮罩透明度": 170,
            "y偏移": 0,
        }

    进度 = (现在 - 开始) / max(0.001, 时长)
    if 进度 >= 1.0:
        self._设置页_动画状态 = "open"
        return {
            "是否可见": True,
            "缩放": 1.0,
            "透明度": 1.0,
            "遮罩透明度": 170,
            "y偏移": 0,
        }

    缓进度 = self._设置页_缓出(进度)
    return {
        "是否可见": True,
        "缩放": 0.94 + 0.06 * 缓进度,
        "透明度": 缓进度,
        "遮罩透明度": 170 * 缓进度,
        "y偏移": int((1.0 - 缓进度) * 24),
    }

def _设置页_点在有效面板区域(self, 屏幕点) -> bool:
    面板绘制矩形 = getattr(self, "_设置页_面板绘制矩形", None)
    if not isinstance(面板绘制矩形, pygame.Rect):
        return False
    if not 面板绘制矩形.collidepoint(屏幕点):
        return False

    面板表面 = getattr(self, "_设置页_最后绘制表面", None)
    if not isinstance(面板表面, pygame.Surface):
        return True

    局部x = int(屏幕点[0] - 面板绘制矩形.x)
    局部y = int(屏幕点[1] - 面板绘制矩形.y)
    if (
        局部x < 0
        or 局部y < 0
        or 局部x >= int(面板表面.get_width())
        or 局部y >= int(面板表面.get_height())
    ):
        return False

    try:
        return int(面板表面.get_at((局部x, 局部y)).a) > 12
    except Exception:
        return True

def 绘制设置页(self):
    self._确保设置页资源()
    self._重算设置页布局()

    动画参数 = _设置页_取动画参数(self)
    if not bool(动画参数.get("是否可见", False)):
        return

    视觉参数 = dict(getattr(self, "_设置页_视觉参数", {}) or {})
    箭头预览内边距 = max(0, int(视觉参数.get("箭头预览内边距", 0) or 0))

    遮罩 = pygame.Surface((self.宽, self.高), pygame.SRCALPHA)
    遮罩.fill(
        (
            0,
            0,
            0,
            int(max(0, min(255, 动画参数.get("遮罩透明度", 170)))),
        )
    )
    self.屏幕.blit(遮罩, (0, 0))

    面板矩形 = self._设置页_面板基础矩形
    面板画布 = pygame.Surface((面板矩形.w, 面板矩形.h), pygame.SRCALPHA)

    if self._设置页_背景图原图 is not None:
        目标尺寸 = (面板矩形.w, 面板矩形.h)
        if (
            self._设置页_背景缩放缓存图 is None
            or self._设置页_背景缩放缓存尺寸 != 目标尺寸
        ):
            try:
                self._设置页_背景缩放缓存图 = pygame.transform.smoothscale(
                    self._设置页_背景图原图, 目标尺寸
                ).convert_alpha()
                self._设置页_背景缩放缓存尺寸 = 目标尺寸
            except Exception:
                self._设置页_背景缩放缓存图 = None
                self._设置页_背景缩放缓存尺寸 = (0, 0)

        if self._设置页_背景缩放缓存图 is not None:
            面板画布.blit(self._设置页_背景缩放缓存图, (0, 0))
    else:
        面板画布.fill((10, 20, 40, 235))

    标签字号 = int(视觉参数.get("标签字号", 24) or 24)
    选项字号 = int(视觉参数.get("选项字号", 26) or 26)
    小字字号 = int(视觉参数.get("小字字号", 16) or 16)
    内容内边距 = int(视觉参数.get("内容内边距", 10) or 10)
    名称下移 = int(视觉参数.get("名称下移", 1) or 1)
    箭头名称上间距 = int(视觉参数.get("箭头名称上间距", 18) or 18)
    底部保护边距 = int(视觉参数.get("底部保护边距", 6) or 6)

    for 行键, 控件 in self._设置页_控件矩形表.items():
        左箭 = 控件["左"]
        右箭 = 控件["右"]
        内容 = 控件["内容"]

        行文字缩放 = 1.0
        try:
            if getattr(self, "_设置页_调试器", None) is not None:
                行文字缩放 = float(self._设置页_调试器.取行文字缩放(行键))
        except Exception:
            行文字缩放 = 1.0
        行文字缩放 = max(0.50, min(3.00, 行文字缩放))

        行标签字体 = 获取字体(max(8, int(round(标签字号 * 行文字缩放))), 是否粗体=False)
        行选项字体 = 获取字体(max(8, int(round(选项字号 * 行文字缩放))), 是否粗体=True)
        小字字体 = 获取字体(小字字号, 是否粗体=False)

        左箭图 = self._设置页_取缩放图(
            f"设置_左小_{行键}", self._设置页_左小箭头原图, 左箭.w, 左箭.h
        )
        右箭图 = self._设置页_取缩放图(
            f"设置_右小_{行键}", self._设置页_右小箭头原图, 右箭.w, 右箭.h
        )

        if 左箭图 is not None:
            面板画布.blit(左箭图, 左箭.topleft)
        if 右箭图 is not None:
            面板画布.blit(右箭图, 右箭.topleft)

        显示名 = 设置菜单行显示名(行键)
        值 = 设置菜单行值(行键, getattr(self, "设置_参数", {}))

        绘制文本(
            面板画布,
            显示名,
            行标签字体,
            (235, 245, 255),
            (内容.x + 内容内边距, 内容.centery + 名称下移),
            对齐="midleft",
        )

        绘制文本(
            面板画布,
            值,
            行选项字体,
            (255, 255, 255),
            (内容.right - 内容内边距, 内容.centery),
            对齐="midright",
        )

    预览框 = getattr(self, "_设置页_箭头预览矩形", pygame.Rect(0, 0, 10, 10))
    小字字体 = 获取字体(小字字号, 是否粗体=False)

    if isinstance(预览框, pygame.Rect) and 预览框.w > 10 and 预览框.h > 10:
        当前候选路径 = None
        if self.设置_箭头候选路径列表:
            当前候选路径 = self.设置_箭头候选路径列表[self.设置_箭头索引]

        候选图 = None
        if 当前候选路径:
            候选图 = self._设置页_箭头候选原图缓存.get(当前候选路径)
            if 候选图 is None:
                候选图 = 安全加载图片(当前候选路径, 透明=True)
                self._设置页_箭头候选原图缓存[当前候选路径] = 候选图

        if 候选图 is not None:
            内边距 = max(0, int(箭头预览内边距))
            可用 = 预览框.inflate(-内边距 * 2, -内边距 * 2)
            ow, oh = 候选图.get_size()
            比例 = min(可用.w / max(1, ow), 可用.h / max(1, oh))
            nw = max(1, int(ow * 比例))
            nh = max(1, int(oh * 比例))
            try:
                候选缩放 = pygame.transform.smoothscale(
                    候选图, (nw, nh)
                ).convert_alpha()
                x = 可用.centerx - nw // 2
                y = 可用.centery - nh // 2
                面板画布.blit(候选缩放, (x, y))
            except Exception:
                pass
        else:
            绘制文本(
                面板画布,
                "无箭头候选",
                小字字体,
                (255, 220, 120),
                预览框.center,
                对齐="center",
            )

        try:
            控件 = getattr(self, "_设置页_箭头预览控件矩形", None)
            if isinstance(控件, dict):
                左r = 控件.get("左", pygame.Rect(0, 0, 0, 0))
                右r = 控件.get("右", pygame.Rect(0, 0, 0, 0))
                左图 = self._设置页_取缩放图(
                    "设置_箭头预览_左", self._设置页_左大箭头原图, 左r.w, 左r.h
                )
                右图 = self._设置页_取缩放图(
                    "设置_箭头预览_右", self._设置页_右大箭头原图, 右r.w, 右r.h
                )
                if 左图 is not None and 左r.w > 2 and 左r.h > 2:
                    面板画布.blit(左图, 左r.topleft)
                if 右图 is not None and 右r.w > 2 and 右r.h > 2:
                    面板画布.blit(右图, 右r.topleft)
        except Exception:
            pass

        try:
            名称 = os.path.splitext(str(getattr(self, "设置_箭头文件名", "") or ""))[0]
            if 名称:
                绘制文本(
                    面板画布,
                    名称,
                    小字字体,
                    (220, 240, 255),
                    (
                        预览框.centerx,
                        min(
                            面板画布.get_height() - 底部保护边距,
                            预览框.bottom + 箭头名称上间距,
                        ),
                    ),
                    对齐="midtop",
                )
        except Exception:
            pass

    背景控件 = self._设置页_背景控件矩形
    左大箭 = 背景控件["左"]
    右大箭 = 背景控件["右"]
    预览区 = 背景控件["预览"]

    左大箭图 = self._设置页_取缩放图(
        "设置_左大", self._设置页_左大箭头原图, 左大箭.w, 左大箭.h
    )
    右大箭图 = self._设置页_取缩放图(
        "设置_右大", self._设置页_右大箭头原图, 右大箭.w, 右大箭.h
    )

    if 左大箭图 is not None:
        面板画布.blit(左大箭图, 左大箭.topleft)
    if 右大箭图 is not None:
        面板画布.blit(右大箭图, 右大箭.topleft)

    当前背景模式 = 设置菜单行值("变速", getattr(self, "设置_参数", {}))
    当前缩略图路径 = None
    if self.设置_背景缩略图路径列表:
        当前缩略图路径 = self.设置_背景缩略图路径列表[self.设置_背景索引]

    缩略图 = None
    if 当前背景模式 == "动态背景":
        缩略图 = getattr(self, "_设置页_动态背景预览原图", None)
    elif 当前缩略图路径:
        缩略图 = self._设置页_背景缩略图原图缓存.get(当前缩略图路径)
        if 缩略图 is None:
            缩略图 = 安全加载图片(当前缩略图路径, 透明=True)
            self._设置页_背景缩略图原图缓存[当前缩略图路径] = 缩略图

    if 缩略图 is not None:
        try:
            if 当前背景模式 == "动态背景":
                pygame.draw.rect(面板画布, (8, 14, 22), 预览区, border_radius=12)
                可用区 = 预览区.inflate(-24, -24)
                ow, oh = 缩略图.get_size()
                比例 = min(float(可用区.w) / float(max(1, ow)), float(可用区.h) / float(max(1, oh)))
                nw = max(1, int(round(float(ow) * 比例)))
                nh = max(1, int(round(float(oh) * 比例)))
                预览图 = pygame.transform.smoothscale(缩略图, (nw, nh)).convert_alpha()
                面板画布.blit(
                    预览图,
                    (
                        int(可用区.centerx - nw // 2),
                        int(可用区.centery - nh // 2),
                    ),
                )
            else:
                绘制_cover裁切预览(面板画布, 缩略图, 预览区)
        except Exception:
            pass
    else:
        绘制文本(
            面板画布,
            "无背景图",
            小字字体,
            (255, 220, 120),
            预览区.center,
            对齐="center",
        )

    try:
        if getattr(self, "_设置页_调试器", None) is not None:
            self._设置页_调试器.绘制覆盖(self, 面板画布)
    except Exception:
        pass

    动画缩放 = float(动画参数.get("缩放", 1.0) or 1.0)
    动画透明 = int(255 * float(动画参数.get("透明度", 1.0) or 1.0))
    动画透明 = max(0, min(255, 动画透明))

    self._设置页_最后缩放 = float(动画缩放)

    if 动画缩放 != 1.0:
        画宽 = max(1, int(面板画布.get_width() * 动画缩放))
        画高 = max(1, int(面板画布.get_height() * 动画缩放))
        try:
            面板画布2 = pygame.transform.smoothscale(
                面板画布, (画宽, 画高)
            ).convert_alpha()
        except Exception:
            面板画布2 = 面板画布
    else:
        面板画布2 = 面板画布

    try:
        面板画布2.set_alpha(动画透明)
    except Exception:
        pass

    绘制矩形 = 面板画布2.get_rect()
    绘制矩形.center = 面板矩形.center
    绘制矩形.y += int(动画参数.get("y偏移", 0) or 0)

    self._设置页_面板绘制矩形 = 绘制矩形
    self._设置页_最后绘制表面 = 面板画布2
    self.屏幕.blit(面板画布2, 绘制矩形.topleft)
    
def 打开设置页(self):
    self._确保设置页资源()
    try:
        self._设置页_同步外部持久化设置(强制=True, 刷新界面=True)
    except Exception:
        pass

    try:
        self.是否星级筛选页 = False
        self.是否模式选择页 = False
    except Exception:
        pass

    self._设置页_上次屏幕尺寸 = (0, 0)
    self._设置页_面板绘制矩形 = pygame.Rect(0, 0, 10, 10)
    self._设置页_最后绘制表面 = None
    self._设置页_最后缩放 = 1.0

    self._重算设置页布局(强制=True)
    self.是否设置页 = True
    self._设置页_动画状态 = "opening"
    self._设置页_打开开始时间 = time.time()
    self._设置页_关闭开始时间 = 0.0

def 关闭设置页(self, 立即: bool = False):
    self._确保设置页资源()
    if bool(立即):
        _设置页_立即隐藏(self)
        return
    if not bool(getattr(self, "是否设置页", False)):
        return
    if str(getattr(self, "_设置页_动画状态", "") or "") == "closing":
        return
    self._设置页_动画状态 = "closing"
    self._设置页_关闭开始时间 = time.time()

def _设置页_切换选项(self, 行键: str, 方向: int):
    self._确保设置页资源()

    try:
        方向 = int(方向)
    except Exception:
        方向 = 0
    if 方向 == 0:
        return

    配置定义 = _设置页_配置项定义()
    定义 = 配置定义.get(str(行键 or ""), None)
    if not isinstance(定义, dict):
        return

    索引属性 = str(定义.get("索引属性", "") or "")
    选项属性 = str(定义.get("选项属性", "") or "")
    if (not 索引属性) or (not 选项属性):
        return

    选项列表 = list(getattr(self, 选项属性, []) or [])
    总数 = len(选项列表)
    if 总数 <= 0:
        return

    try:
        当前索引 = int(getattr(self, 索引属性, 0) or 0)
    except Exception:
        当前索引 = 0

    当前索引 = (当前索引 + 方向) % 总数
    setattr(self, 索引属性, 当前索引)

    self._设置页_同步参数()

    try:
        self._设置页_保存持久化设置()
    except Exception:
        pass

    try:
        if str(定义.get("参数键", "") or "") == "背景模式":
            self._加载背景图()
    except Exception:
        pass

    self._设置页_上次屏幕尺寸 = (0, 0)
    self._设置页_最后绘制表面 = None
    self._设置页_最后缩放 = 1.0
    self._重算设置页布局(强制=True)

def _设置页_切换背景(self, 方向: int):
    self._确保设置页资源()

    try:
        方向 = int(方向)
    except Exception:
        方向 = 0
    if 方向 == 0:
        return

    总数 = len(self.设置_背景缩略图路径列表)
    if 总数 <= 0:
        return

    self.设置_背景索引 = (self.设置_背景索引 + 方向) % 总数
    self._设置页_同步参数()

    try:
        self._设置页_保存持久化设置()
    except Exception:
        pass

    try:
        self._加载背景图()
    except Exception:
        pass

    self._设置页_上次屏幕尺寸 = (0, 0)
    self._设置页_最后绘制表面 = None
    self._设置页_最后缩放 = 1.0
    self._重算设置页布局(强制=True)

def _设置页_处理事件(self, 事件):
    self._确保设置页资源()
    self._重算设置页布局()

    if 事件.type == pygame.KEYDOWN and 事件.key == pygame.K_F6:
        try:
            self._设置页_调试器.切换启用()
            if hasattr(self, "显示消息提示"):
                if bool(self._设置页_调试器.是否启用):
                    self.显示消息提示("设置页调试器：已开启", 持续秒=1.2)
                else:
                    self.显示消息提示("设置页调试器：已关闭", 持续秒=1.2)
        except Exception:
            pass
        return

    try:
        if getattr(self, "_设置页_调试器", None) is not None and bool(self._设置页_调试器.是否启用):
            if self._设置页_调试器.处理事件(self, 事件):
                return
    except Exception:
        pass

    if str(getattr(self, "_设置页_动画状态", "") or "") == "closing":
        return

    面板绘制矩形 = getattr(self, "_设置页_面板绘制矩形", None)
    if not isinstance(面板绘制矩形, pygame.Rect):
        面板绘制矩形 = self._设置页_面板基础矩形

    当前缩放 = float(getattr(self, "_设置页_最后缩放", 1.0) or 1.0)
    当前缩放 = max(0.001, 当前缩放)

    def _转局部坐标(屏幕点):
        局部x = int((屏幕点[0] - 面板绘制矩形.x) / 当前缩放)
        局部y = int((屏幕点[1] - 面板绘制矩形.y) / 当前缩放)
        return (局部x, 局部y)

    if 事件.type == pygame.KEYDOWN and 事件.key == pygame.K_ESCAPE:
        self.关闭设置页()
        return

    if 事件.type != pygame.MOUSEBUTTONDOWN or 事件.button != 1:
        return

    if not self._设置页_点在有效面板区域(事件.pos):
        self.关闭设置页()
        return

    局部点 = _转局部坐标(事件.pos)

    try:
        控件 = getattr(self, "_设置页_箭头预览控件矩形", None)
        if isinstance(控件, dict):
            if 控件.get("左", pygame.Rect(0, 0, 0, 0)).collidepoint(局部点):
                self._播放按钮音效()
                self._设置页_切换选项("箭头", -1)
                return
            if 控件.get("右", pygame.Rect(0, 0, 0, 0)).collidepoint(局部点):
                self._播放按钮音效()
                self._设置页_切换选项("箭头", +1)
                return
    except Exception:
        pass

    背景控件 = self._设置页_背景控件矩形
    if 背景控件["左"].collidepoint(局部点):
        self._播放按钮音效()
        self._设置页_切换背景(-1)
        return
    if 背景控件["右"].collidepoint(局部点):
        self._播放按钮音效()
        self._设置页_切换背景(+1)
        return

    for 行键, 控件 in self._设置页_控件矩形表.items():
        if 控件["左"].collidepoint(局部点):
            self._播放按钮音效()
            self._设置页_切换选项(行键, -1)
            return
        if 控件["右"].collidepoint(局部点):
            self._播放按钮音效()
            self._设置页_切换选项(行键, +1)
            return


def _资源路径(*片段: str) -> str:
    return _公共取资源路径(*片段)

def 获取UI原图(路径: str, 透明: bool = True) -> Optional[pygame.Surface]:
    if not 路径:
        return None
    key = f"{路径}|{'A' if 透明 else 'O'}"
    if key in _UI原图缓存:
        return _UI原图缓存[key]
    图 = 安全加载图片(路径, 透明=透明)
    _UI原图缓存[key] = 图
    return 图

_UI容器缓存: Dict[Tuple[str, int, int, bool, str], Optional[pygame.Surface]] = {}

def 获取UI容器图(
    路径: str, 目标宽: int, 目标高: int, 缩放模式: str = "stretch", 透明: bool = True
) -> Optional[pygame.Surface]:
    """
    返回一个“容器尺寸=目标宽高”的 Surface：
    - stretch：直接拉伸到容器
    - contain：等比完整展示，四周透明留边
    - cover  ：等比铺满容器，裁切超出部分
    """
    if (not 路径) or 目标宽 <= 0 or 目标高 <= 0:
        return None

    模式 = str(缩放模式 or "stretch").strip().lower()
    if 模式 not in ("stretch", "contain", "cover"):
        模式 = "stretch"

    key = (f"{路径}|{'A' if 透明 else 'O'}", int(目标宽), int(目标高), bool(透明), 模式)
    if key in _UI容器缓存:
        return _UI容器缓存.get(key)

    原图 = 获取UI原图(路径, 透明=透明)
    if 原图 is None:
        _UI容器缓存[key] = None
        return None

    ow, oh = 原图.get_size()
    if ow <= 0 or oh <= 0:
        _UI容器缓存[key] = None
        return None

    try:
        if 模式 == "stretch":
            out = pygame.transform.smoothscale(原图, (int(目标宽), int(目标高)))
            out = out.convert_alpha() if 透明 else out.convert()
            _UI容器缓存[key] = out
            return out

        # contain / cover 都做“先等比缩放 -> 再贴到容器画布”
        if 模式 == "contain":
            比例 = min(float(目标宽) / float(ow), float(目标高) / float(oh))
        else:  # cover
            比例 = max(float(目标宽) / float(ow), float(目标高) / float(oh))

        nw = max(1, int(ow * 比例))
        nh = max(1, int(oh * 比例))
        缩放图 = pygame.transform.smoothscale(原图, (nw, nh)).convert_alpha()

        画布 = pygame.Surface((int(目标宽), int(目标高)), pygame.SRCALPHA)
        画布.fill((0, 0, 0, 0))
        x = (int(目标宽) - nw) // 2
        y = (int(目标高) - nh) // 2
        # x/y 允许为负，pygame 会自动裁剪
        画布.blit(缩放图, (x, y))

        _UI容器缓存[key] = 画布.convert_alpha()
        return _UI容器缓存[key]
    except Exception:
        _UI容器缓存[key] = None
        return None

_选歌布局_缓存: dict | None = None
_选歌布局_修改时间: float = -1.0
_选歌布局_最近检查时刻: float = -999.0

def _选歌布局_文件路径() -> str:
    return _公共取布局配置路径("选歌布局.json", 根目录=_取项目根目录())

def _选歌布局_默认值() -> dict:
    return {
        "缩略图小框": {
            "_缩略图小框_宽缩放": 1.0,
            "_缩略图小框_高缩放": 1.0,
            "_缩略图小框_x偏移": 0.0,
            "_缩略图小框_y偏移": 0.2,
        },
        "缩略图大框": {
            "_缩略图大框_宽缩放": 1.1,
            "_缩略图大框_高缩放": 1.15,
            "_缩略图大框_x偏移": 0.0,
            "_缩略图大框_y偏移": 0.0,
        },
        "卡片槽位": {
            "小图": {
                "封面左占比": 0.10,
                "封面上占比": 0.045,
                "封面宽占比": 0.845,
                "封面高占比": 0.940,
                "信息条高占比": 0.315,
                "信息条左右内边距占比": 0.035,
                "星区上内边距占比": 0.0,
                "星区高占比": 0.34,
                "文本区左右内边距占比": 0.040,
                "底栏高占比": 0.22,
                "底栏底部留白占比": 0.18,
            },
            "大图": {
                "封面左占比": 0.05,
                "封面上占比": 0.02,
                "封面宽占比": 0.95,
                "封面高占比": 1.0,
                "信息条高占比": 0.35,
                "信息条左右内边距占比": 0.040,
                "星区上内边距占比": 0.050,
                "星区高占比": 0.3,
                "文本区左右内边距占比": 0.050,
                "底栏高占比": 0.245,
                "底栏底部留白占比": 0.06,
            },
            "小图可视裁切": {
                "框体设计高": 256.0,
                "可视底像素": 231.0,
                "信息条锚点": "visible",
            },
        },
        "文字样式": {
            "小图": {
                "歌名字号占框高比": 0.10,
                "歌名最小字号": 8.0,
                "歌名字号相对BPM增量": 2.0,
                "游玩次数标签字号占信息条高比": 0.16,
                "游玩次数数字字号占信息条高比": 0.18,
                "BPM字号占信息条高比": 0.20,
                "游玩次数最小字号": 7.0,
                "BPM最小字号": 8.0,
            },
            "大图": {
                "歌名字号占信息条高比": 0.22,
                "歌名最小字号": 16.0,
                "底栏字号占信息条高比": 0.13,
                "底栏最小字号": 12.0,
            },
        },
        "序号标签": {
            "_缩略图_序号背景_缩放": 1.5,
            "_缩略图_序号背景_x偏移": 20,
            "_缩略图_序号背景_y偏移": -20,
            "_缩略图_序号数字_缩放": 1.6,
            "_缩略图_序号数字_x偏移": -20,
            "_缩略图_序号数字_y偏移": -20,
            "_缩略图_序号数字_右内边距占比": 0.12,
            "_缩略图_序号数字_下内边距占比": 0.12,
            "_序号显示格式_缩略图": "{:02d}",
        },
    }

def _安全转浮点(值, 默认值: float) -> float:
    try:
        return float(值)
    except Exception:
        return float(默认值)

def _安全转整数(值, 默认值: int) -> int:
    try:
        return int(round(float(值)))
    except Exception:
        return int(默认值)


def _读取槽位参数(来源: object, 默认值: dict) -> dict:
    结果 = dict(默认值)
    if not isinstance(来源, dict):
        return 结果
    for 键, 默认 in 默认值.items():
        结果[键] = _安全转浮点(来源.get(键, 默认), float(默认))
    return 结果

def 读取选歌布局配置() -> dict:
    global _选歌布局_缓存, _选歌布局_修改时间, _选歌布局_最近检查时刻

    当前时刻 = float(time.perf_counter())
    if (
        _选歌布局_缓存 is not None
        and (当前时刻 - float(_选歌布局_最近检查时刻)) < 0.25
    ):
        return _选歌布局_缓存

    路径 = _选歌布局_文件路径()
    try:
        修改时间 = os.path.getmtime(路径) if os.path.isfile(路径) else 0.0
    except Exception:
        修改时间 = 0.0
    _选歌布局_最近检查时刻 = 当前时刻

    if _选歌布局_缓存 is not None and float(_选歌布局_修改时间) == float(修改时间):
        return _选歌布局_缓存

    数据 = _选歌布局_默认值()

    if os.path.isfile(路径):
        for 编码 in ("utf-8-sig", "utf-8", "gbk"):
            try:
                with open(路径, "r", encoding=编码) as 文件:
                    读取数据 = json.load(文件)
                if isinstance(读取数据, dict):
                    数据 = 读取数据
                break
            except Exception:
                continue

    if not isinstance(数据, dict):
        数据 = _选歌布局_默认值()

    _选歌布局_缓存 = 数据
    _选歌布局_修改时间 = float(修改时间)
    _应用选歌布局常量(数据)
    return 数据

def _应用选歌布局常量(配置: dict):
    global _缩略图小框_宽缩放
    global _缩略图小框_高缩放
    global _缩略图小框_x偏移
    global _缩略图小框_y偏移

    global _缩略图大框_宽缩放
    global _缩略图大框_高缩放
    global _缩略图大框_x偏移
    global _缩略图大框_y偏移

    global _缩略图槽位参数
    global _大图槽位参数
    global _缩略图可视底设计像素
    global _缩略图框体设计高
    global _缩略图信息条锚点
    global _小图文字样式参数
    global _大图文字样式参数

    global _缩略图_序号背景_缩放
    global _缩略图_序号背景_x偏移
    global _缩略图_序号背景_y偏移
    global _缩略图_序号数字_缩放
    global _缩略图_序号数字_x偏移
    global _缩略图_序号数字_y偏移
    global _缩略图_序号数字_右内边距占比
    global _缩略图_序号数字_下内边距占比
    global _序号显示格式_缩略图

    默认值 = _选歌布局_默认值()

    小框 = 配置.get("缩略图小框", {})
    if not isinstance(小框, dict):
        小框 = {}
    小框默认 = 默认值["缩略图小框"]

    _缩略图小框_宽缩放 = max(
        0.05,
        min(
            5.0,
            _安全转浮点(
                小框.get("_缩略图小框_宽缩放", 小框默认["_缩略图小框_宽缩放"]),
                小框默认["_缩略图小框_宽缩放"],
            ),
        ),
    )
    _缩略图小框_高缩放 = max(
        0.05,
        min(
            5.0,
            _安全转浮点(
                小框.get("_缩略图小框_高缩放", 小框默认["_缩略图小框_高缩放"]),
                小框默认["_缩略图小框_高缩放"],
            ),
        ),
    )
    _缩略图小框_x偏移 = _安全转整数(
        小框.get("_缩略图小框_x偏移", 小框默认["_缩略图小框_x偏移"]),
        int(小框默认["_缩略图小框_x偏移"]),
    )
    _缩略图小框_y偏移 = _安全转浮点(
        小框.get("_缩略图小框_y偏移", 小框默认["_缩略图小框_y偏移"]),
        float(小框默认["_缩略图小框_y偏移"]),
    )

    大框 = 配置.get("缩略图大框", {})
    if not isinstance(大框, dict):
        大框 = {}
    大框默认 = 默认值["缩略图大框"]

    _缩略图大框_宽缩放 = max(
        0.05,
        min(
            5.0,
            _安全转浮点(
                大框.get("_缩略图大框_宽缩放", 大框默认["_缩略图大框_宽缩放"]),
                大框默认["_缩略图大框_宽缩放"],
            ),
        ),
    )
    _缩略图大框_高缩放 = max(
        0.05,
        min(
            5.0,
            _安全转浮点(
                大框.get("_缩略图大框_高缩放", 大框默认["_缩略图大框_高缩放"]),
                大框默认["_缩略图大框_高缩放"],
            ),
        ),
    )
    _缩略图大框_x偏移 = _安全转整数(
        大框.get("_缩略图大框_x偏移", 大框默认["_缩略图大框_x偏移"]),
        int(大框默认["_缩略图大框_x偏移"]),
    )
    _缩略图大框_y偏移 = _安全转整数(
        大框.get("_缩略图大框_y偏移", 大框默认["_缩略图大框_y偏移"]),
        int(大框默认["_缩略图大框_y偏移"]),
    )

    卡片槽位 = 配置.get("卡片槽位", {})
    if not isinstance(卡片槽位, dict):
        卡片槽位 = {}
    卡片槽位默认 = 默认值["卡片槽位"]

    _缩略图槽位参数 = _读取槽位参数(
        卡片槽位.get("小图", {}), 卡片槽位默认["小图"]
    )
    _大图槽位参数 = _读取槽位参数(
        卡片槽位.get("大图", {}), 卡片槽位默认["大图"]
    )

    小图可视裁切 = 卡片槽位.get("小图可视裁切", {})
    if not isinstance(小图可视裁切, dict):
        小图可视裁切 = {}
    小图可视裁切默认 = 卡片槽位默认["小图可视裁切"]

    _缩略图框体设计高 = max(
        1.0,
        min(
            9999.0,
            _安全转浮点(
                小图可视裁切.get("框体设计高", 小图可视裁切默认["框体设计高"]),
                float(小图可视裁切默认["框体设计高"]),
            ),
        ),
    )
    _缩略图可视底设计像素 = max(
        1.0,
        min(
            9999.0,
            _安全转浮点(
                小图可视裁切.get("可视底像素", 小图可视裁切默认["可视底像素"]),
                float(小图可视裁切默认["可视底像素"]),
            ),
        ),
    )
    _缩略图信息条锚点 = str(
        小图可视裁切.get("信息条锚点", 小图可视裁切默认["信息条锚点"])
        or 小图可视裁切默认["信息条锚点"]
    )

    文字样式 = 配置.get("文字样式", {})
    if not isinstance(文字样式, dict):
        文字样式 = {}
    文字样式默认 = 默认值["文字样式"]
    _小图文字样式参数 = _读取槽位参数(
        文字样式.get("小图", {}), 文字样式默认["小图"]
    )
    _大图文字样式参数 = _读取槽位参数(
        文字样式.get("大图", {}), 文字样式默认["大图"]
    )

    序号 = 配置.get("序号标签", {})
    if not isinstance(序号, dict):
        序号 = {}
    序号默认 = 默认值["序号标签"]

    _缩略图_序号背景_缩放 = max(
        0.05,
        min(
            5.0,
            _安全转浮点(
                序号.get("_缩略图_序号背景_缩放", 序号默认["_缩略图_序号背景_缩放"]),
                序号默认["_缩略图_序号背景_缩放"],
            ),
        ),
    )
    _缩略图_序号背景_x偏移 = _安全转整数(
        序号.get("_缩略图_序号背景_x偏移", 序号默认["_缩略图_序号背景_x偏移"]),
        int(序号默认["_缩略图_序号背景_x偏移"]),
    )
    _缩略图_序号背景_y偏移 = _安全转整数(
        序号.get("_缩略图_序号背景_y偏移", 序号默认["_缩略图_序号背景_y偏移"]),
        int(序号默认["_缩略图_序号背景_y偏移"]),
    )
    _缩略图_序号数字_缩放 = max(
        0.05,
        min(
            5.0,
            _安全转浮点(
                序号.get("_缩略图_序号数字_缩放", 序号默认["_缩略图_序号数字_缩放"]),
                序号默认["_缩略图_序号数字_缩放"],
            ),
        ),
    )
    _缩略图_序号数字_x偏移 = _安全转整数(
        序号.get("_缩略图_序号数字_x偏移", 序号默认["_缩略图_序号数字_x偏移"]),
        int(序号默认["_缩略图_序号数字_x偏移"]),
    )
    _缩略图_序号数字_y偏移 = _安全转整数(
        序号.get("_缩略图_序号数字_y偏移", 序号默认["_缩略图_序号数字_y偏移"]),
        int(序号默认["_缩略图_序号数字_y偏移"]),
    )
    _缩略图_序号数字_右内边距占比 = max(
        0.0,
        min(
            1.0,
            _安全转浮点(
                序号.get(
                    "_缩略图_序号数字_右内边距占比",
                    序号默认["_缩略图_序号数字_右内边距占比"],
                ),
                序号默认["_缩略图_序号数字_右内边距占比"],
            ),
        ),
    )
    _缩略图_序号数字_下内边距占比 = max(
        0.0,
        min(
            1.0,
            _安全转浮点(
                序号.get(
                    "_缩略图_序号数字_下内边距占比",
                    序号默认["_缩略图_序号数字_下内边距占比"],
                ),
                序号默认["_缩略图_序号数字_下内边距占比"],
            ),
        ),
    )
    _序号显示格式_缩略图 = str(
        序号.get("_序号显示格式_缩略图", 序号默认["_序号显示格式_缩略图"])
        or 序号默认["_序号显示格式_缩略图"]
    )

def 刷新选歌布局常量():
    读取选歌布局配置()

刷新选歌布局常量()

_按高缩放缓存: Dict[Tuple[int, int], Optional[pygame.Surface]] = {}

def _按高等比缩放(图: pygame.Surface, 目标高: int) -> Optional[pygame.Surface]:
    if 图 is None:
        return None
    try:
        目标高 = int(目标高)
    except Exception:
        return None
    if 目标高 <= 0:
        return None

    try:
        ow, oh = 图.get_size()
    except Exception:
        return None
    if ow <= 0 or oh <= 0:
        return None

    缓存键 = (int(id(图)), int(目标高))
    if 缓存键 in _按高缩放缓存:
        return _按高缩放缓存.get(缓存键)

    比例 = float(目标高) / float(oh)
    nw = max(1, int(ow * 比例))

    try:
        缩放图 = pygame.transform.smoothscale(图, (nw, int(目标高))).convert_alpha()
    except Exception:
        缩放图 = None

    _按高缩放缓存[缓存键] = 缩放图

    # ✅ 防御：避免缓存无限增长（窗口频繁 resize 时尤其明显）
    if len(_按高缩放缓存) > 1800:
        _按高缩放缓存.clear()

    return 缩放图

def 绘制序号标签_图片(
    屏幕: pygame.Surface,
    锚点矩形: pygame.Rect,
    内部序号从0: int,
    是否大图: bool,
):
    """
    修复点：
    - ❌ 原来用 (format后)[-2:] 截断，100 变 00
    - ✅ 不截断，支持 2 位/3 位/更多位数字渲染
    - ✅ 数字过宽时自动缩小，尽量塞进标签纸
    """
    标签信息 = 计算序号标签信息(锚点矩形, 是否大图)
    if 标签信息 is None:
        return
    标签纸图 = 标签信息["标签纸图"]
    标签矩形 = 标签信息["标签矩形"]
    标签x = int(标签矩形.x)
    标签y = int(标签矩形.y)
    标签w = int(标签矩形.w)
    标签h = int(标签矩形.h)
    数字缩放 = float(标签信息["数字缩放"])
    数字x偏移 = int(标签信息["数字x偏移"])
    数字y偏移 = int(标签信息["数字y偏移"])
    显示格式 = str(标签信息["显示格式"])
    数字目录 = _资源路径("UI-img", "选歌界面资源", "数字-选歌序号")

    屏幕.blit(标签纸图, 标签矩形.topleft)

    # =========================
    # 3) 序号内容（✅ 不截断）
    # =========================
    显示值 = int(内部序号从0) + 1
    try:
        显示串 = str(显示格式.format(显示值))
    except Exception:
        显示串 = str(显示值)

    # 只保留数字（防御：万一 format 里带空格/其它符号）
    显示串 = "".join([ch for ch in 显示串 if ch.isdigit()])
    if not 显示串:
        return

    # =========================
    # 4) 数字缩放（先按标签高给一个基准）
    # =========================
    if 是否大图:
        数字基准高 = max(8, int(标签h / 3))
    else:
        数字基准高 = max(6, int(标签h / 6))

    初始数字高 = max(5, int(数字基准高 * 数字缩放))

    def _生成数字图列表(数字高: int):
        数字图列表_: List[pygame.Surface] = []
        for ch in 显示串:
            数字路径 = os.path.join(数字目录, f"{ch}.png")
            原 = 获取UI原图(数字路径, 透明=True)
            if 原 is None:
                return None
            缩 = _按高等比缩放(原, max(1, int(数字高)))
            if 缩 is None:
                return None
            数字图列表_.append(缩)
        return 数字图列表_

    # ✅ 自动缩小直到“宽度能塞进标签纸”
    数字高 = int(初始数字高)
    数字图列表 = _生成数字图列表(数字高)
    if not 数字图列表:
        return

    for _ in range(16):
        间距 = max(1, int(数字高 * 0.10))
        总宽 = (
            sum([d.get_width() for d in 数字图列表])
            + max(0, len(数字图列表) - 1) * 间距
        )

        # 可用宽：缩略图右下对齐要留边；大图居中也别贴边
        可用宽 = int(标签w * 0.86)
        if 总宽 <= 可用宽:
            break

        新数字高 = max(3, int(数字高 * 0.92))
        if 新数字高 == 数字高:
            break
        数字高 = 新数字高
        数字图列表 = _生成数字图列表(数字高)
        if not 数字图列表:
            return

    间距 = max(1, int(数字高 * 0.10))
    总宽 = sum([d.get_width() for d in 数字图列表]) + max(0, len(数字图列表) - 1) * 间距

    # =========================
    # 5) 数字定位
    # =========================
    if 是否大图:
        起始x = 标签x + (标签w - 总宽) // 2 + 数字x偏移
        起始y = 标签y + (标签h - 数字高) // 2 + 数字y偏移
    else:
        右内边距 = max(2, int(标签w * float(_缩略图_序号数字_右内边距占比)))
        下内边距 = max(2, int(标签h * float(_缩略图_序号数字_下内边距占比)))

        起始x = 标签x + 标签w - 右内边距 - 总宽 + 数字x偏移
        起始y = 标签y + 标签h - 下内边距 - 数字高 + 数字y偏移

        起始x = max(标签x, 起始x)
        起始y = max(标签y, 起始y)

    x = int(起始x)
    y = int(起始y)
    for i, 图 in enumerate(数字图列表):
        屏幕.blit(图, (x, y))
        x += 图.get_width()
        if i != len(数字图列表) - 1:
            x += 间距


def 计算序号标签信息(
    锚点矩形: pygame.Rect,
    是否大图: bool,
) -> Optional[dict]:
    标签纸路径 = _资源路径(
        "UI-img",
        "选歌界面资源",
        "数字-选歌序号",
        "大号标签纸.png" if 是否大图 else "小号标签纸.png",
    )
    标签纸原图 = 获取UI原图(标签纸路径, 透明=True)
    if 标签纸原图 is None:
        return None

    if 是否大图:
        背景缩放 = float(_大图_序号背景_缩放)
        背景x偏移 = int(_大图_序号背景_x偏移)
        背景y偏移 = int(_大图_序号背景_y偏移)
        数字缩放 = float(_大图_序号数字_缩放)
        数字x偏移 = int(_大图_序号数字_x偏移)
        数字y偏移 = int(_大图_序号数字_y偏移)
        显示格式 = str(_序号显示格式_大图)
        基准高占比 = 0.16
    else:
        背景缩放 = float(_缩略图_序号背景_缩放)
        背景x偏移 = int(_缩略图_序号背景_x偏移)
        背景y偏移 = int(_缩略图_序号背景_y偏移)
        数字缩放 = float(_缩略图_序号数字_缩放)
        数字x偏移 = int(_缩略图_序号数字_x偏移)
        数字y偏移 = int(_缩略图_序号数字_y偏移)
        显示格式 = str(_序号显示格式_缩略图)
        基准高占比 = 0.30

    背景缩放 = max(0.05, min(5.0, 背景缩放))
    数字缩放 = max(0.05, min(5.0, 数字缩放))
    基准高 = max(8, int(锚点矩形.h * 基准高占比))
    标签高 = max(8, int(基准高 * 背景缩放))

    标签纸图 = _按高等比缩放(标签纸原图, 标签高)
    if 标签纸图 is None:
        return None

    标签w, 标签h = 标签纸图.get_size()
    if 是否大图:
        基础偏移x = -int(标签w * 0.18)
        基础偏移y = -int(标签h * 0.12)
        标签x = 锚点矩形.left + 基础偏移x + 背景x偏移
        标签y = 锚点矩形.top + 基础偏移y + 背景y偏移
    else:
        标签x = int(锚点矩形.left - 标签w / 2) + 背景x偏移
        标签y = int(锚点矩形.top) + 背景y偏移

    return {
        "标签纸图": 标签纸图,
        "标签矩形": pygame.Rect(int(标签x), int(标签y), int(标签w), int(标签h)),
        "数字缩放": float(数字缩放),
        "数字x偏移": int(数字x偏移),
        "数字y偏移": int(数字y偏移),
        "显示格式": str(显示格式),
    }


def 绘制MV角标_文本(
    屏幕: pygame.Surface,
    封面矩形: pygame.Rect,
    参考矩形: pygame.Rect,
    是否大图: bool = False,
):
    try:
        标签信息 = 计算序号标签信息(参考矩形, bool(是否大图))
        _绘制MV角标模块(
            screen=屏幕,
            cover_rect=封面矩形,
            anchor_rect=参考矩形,
            is_large=bool(是否大图),
            get_font=获取字体,
            sequence_label_rect=(
                标签信息.get("标签矩形")
                if isinstance(标签信息, dict)
                else None
            ),
        )
    except Exception:
        pass

def 绘制星星行_图片(
    屏幕: pygame.Surface,
    区域: pygame.Rect,
    星数: int,
    星星路径: str,
    星星缩放倍数: float,
    每行最大: int = 10,
    动态光效路径: Optional[str] = None,
    光效周期秒: float = 2.0,
    基准高占比: float = 1.0,
    行间距占比: float = 0.35,
    仅绘制动态光效: bool = False,
    光效透明度: int = 255,
):
    """
    ✅ 规则改为：
    - 星数 <= 每行最大：单排居中
    - 星数 > 每行最大：下排固定放 每行最大(默认10)，超出的全部放上排
      （上排可能 >10，会自动缩小以塞进区域）
    """
    星数 = max(0, int(星数))
    if 星数 <= 0:
        return

    星原图 = 获取UI原图(星星路径, 透明=True)
    if 星原图 is None:
        return

    try:
        基准高占比 = float(基准高占比)
    except Exception:
        基准高占比 = 1.0
    基准高占比 = max(0.05, min(2.0, 基准高占比))

    try:
        行间距占比 = float(行间距占比)
    except Exception:
        行间距占比 = 0.35
    行间距占比 = max(0.0, min(2.0, 行间距占比))

    try:
        光效透明度 = int(光效透明度)
    except Exception:
        光效透明度 = 255
    光效透明度 = max(0, min(255, 光效透明度))

    def _按目标高生成星图(目标高_: int) -> Optional[pygame.Surface]:
        return _按高等比缩放(星原图, max(1, int(目标高_)))

    # ---------- 初算星星尺寸 ----------
    基准高 = max(6, int(区域.h * 基准高占比))
    目标高 = max(6, int(基准高 * float(星星缩放倍数)))

    星图 = _按目标高生成星图(目标高)
    if 星图 is None:
        return

    # ---------- 行分配：下10，上剩余 ----------
    if 星数 <= 每行最大:
        上排数 = 星数
        下排数 = 0
        行数 = 1
    else:
        下排数 = int(每行最大)
        上排数 = int(星数 - 每行最大)
        行数 = 2

    # ---------- 自动缩小：同时满足“高度”和“最大行宽” ----------
    for _ in range(18):
        星w, 星h = 星图.get_size()
        间距 = max(1, int(星w * 0.10))
        行距 = max(0, int(星h * 行间距占比))

        上排宽 = (上排数 * 星w + max(0, 上排数 - 1) * 间距) if 上排数 > 0 else 0
        下排宽 = (下排数 * 星w + max(0, 下排数 - 1) * 间距) if 下排数 > 0 else 0
        最大行宽 = max(上排宽, 下排宽, 1)

        总高 = 星h if 行数 == 1 else (星h * 2 + 行距)

        if (总高 <= 区域.h) and (最大行宽 <= 区域.w):
            break

        # 缩小一档
        新目标高 = max(3, int(星h * 0.92))
        星图2 = _按目标高生成星图(新目标高)
        if 星图2 is None:
            break
        星图 = 星图2

    星w, 星h = 星图.get_size()
    间距 = max(1, int(星w * 0.10))
    行距 = max(0, int(星h * 行间距占比))
    总高 = 星h if 行数 == 1 else (星h * 2 + 行距)

    起始y = 区域.y + (区域.h - 总高) // 2

    星矩形列表: List[pygame.Rect] = []

    def _绘制一行(数量: int, y: int):
        if 数量 <= 0:
            return pygame.Rect(区域.centerx, y, 1, 星h)
        总宽 = 数量 * 星w + (数量 - 1) * 间距
        x0 = 区域.centerx - 总宽 // 2
        for i in range(数量):
            星矩形 = pygame.Rect(x0 + i * (星w + 间距), y, 星w, 星h)
            星矩形列表.append(星矩形)
            if not 仅绘制动态光效:
                屏幕.blit(星图, 星矩形.topleft)
        return pygame.Rect(x0, y, 总宽, 星h)

    if 行数 == 1:
        行矩形 = _绘制一行(上排数, 起始y)
        # 单排：动态光效扫这一排
        光效行矩形 = 行矩形
    else:
        # ✅ 上排先画（超出的）
        上排y = 起始y
        上排矩形 = _绘制一行(上排数, 上排y)

        # ✅ 下排固定10颗
        下排y = 上排y + 星h + 行距
        下排矩形 = _绘制一行(下排数, 下排y)

        # 动态光效默认扫“下排”（更符合你说的“10颗在下”视觉中心）
        光效行矩形 = 下排矩形 if 下排数 > 0 else 上排矩形

    # ---------- 动态光效 ----------
    if 动态光效路径 and 光效透明度 > 0 and 星矩形列表:
        光效区域 = 星矩形列表[0].copy()
        for 星矩形 in 星矩形列表[1:]:
            光效区域.union_ip(星矩形)
        光效区域.inflate_ip(max(4, int(星w * 0.24)), max(4, int(星h * 0.32)))
        if 光效区域.w > 2 and 光效区域.h > 2:
            遮罩层 = pygame.Surface((光效区域.w, 光效区域.h), pygame.SRCALPHA)
            for 星矩形 in 星矩形列表:
                遮罩层.blit(星图, (星矩形.x - 光效区域.x, 星矩形.y - 光效区域.y))

            try:
                遮罩层 = pygame.mask.from_surface(遮罩层).to_surface(
                    setcolor=(255, 255, 255, 255),
                    unsetcolor=(0, 0, 0, 0),
                ).convert_alpha()
            except Exception:
                pass

            高光层 = pygame.Surface((光效区域.w, 光效区域.h), pygame.SRCALPHA)
            周期秒 = max(0.8, float(光效周期秒 or 1.6))
            t = (time.time() % 周期秒) / 周期秒
            斜向偏移 = max(6, int(光效区域.h * 0.42))
            基础带宽 = max(12, int(光效区域.w * 0.24))
            中心x = int(-基础带宽 + (光效区域.w + 基础带宽 * 2) * t)

            def _画高光带(宽度: int, alpha: int, 颜色: Tuple[int, int, int]):
                半宽 = max(2, int(宽度 // 2))
                多边形点 = [
                    (中心x - 半宽 - 斜向偏移, 0),
                    (中心x + 半宽 - 斜向偏移, 0),
                    (中心x + 半宽 + 斜向偏移, 光效区域.h),
                    (中心x - 半宽 + 斜向偏移, 光效区域.h),
                ]
                pygame.draw.polygon(高光层, (*颜色, alpha), 多边形点)

            _画高光带(int(基础带宽 * 1.85), 26, (255, 186, 58))
            _画高光带(int(基础带宽 * 1.10), 54, (255, 223, 132))
            _画高光带(int(基础带宽 * 0.48), 88, (255, 248, 226))

            try:
                高光层.blit(遮罩层, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            except Exception:
                pass

            try:
                高光层.set_alpha(光效透明度)
            except Exception:
                pass

            屏幕.blit(高光层, 光效区域.topleft, special_flags=pygame.BLEND_RGBA_ADD)

def 绘制圆角矩形(
    屏幕: pygame.Surface, 矩形: pygame.Rect, 颜色, 圆角: int, 线宽: int = 0
):
    pygame.draw.rect(屏幕, 颜色, 矩形, width=线宽, border_radius=圆角)

def 绘制超粗文本(
    屏幕: pygame.Surface,
    文本: str,
    字体: pygame.font.Font,
    颜色,
    位置: tuple,
    对齐: str = "topleft",
    粗细: int = 3,
):
    """
    用多次偏移叠加实现“很粗”的字，不依赖字体文件是否有 bold。
    粗细建议 2~5，太大可能发糊。
    """
    文本面 = 字体.render(文本, True, 颜色)
    文本矩形 = 文本面.get_rect()
    setattr(文本矩形, 对齐, 位置)

    # 叠加偏移：越多越粗
    for dx in range(-粗细, 粗细 + 1):
        for dy in range(-粗细, 粗细 + 1):
            if dx == 0 and dy == 0:
                continue
            屏幕.blit(文本面, (文本矩形.x + dx, 文本矩形.y + dy))

    # 最后绘制一次正位，保证清晰
    屏幕.blit(文本面, 文本矩形)
    return 文本矩形

def 绘制文本(
    屏幕: pygame.Surface,
    文本: str,
    字体: pygame.font.Font,
    颜色,
    位置: tuple,
    对齐: str = "topleft",
):
    文本面 = 字体.render(文本, True, 颜色)
    文本矩形 = 文本面.get_rect()
    setattr(文本矩形, 对齐, 位置)
    屏幕.blit(文本面, 文本矩形)
    return 文本矩形

def 渲染紧凑文本(
    文本: str,
    字体: pygame.font.Font,
    颜色,
    字符间距: int = 0,
) -> pygame.Surface:
    字符面列表: List[pygame.Surface] = []
    总宽 = 0
    最大高 = 0
    间距 = int(字符间距)

    for 字符 in str(文本 or ""):
        字符面 = 字体.render(str(字符), True, 颜色).convert_alpha()
        字符面列表.append(字符面)
        总宽 += int(字符面.get_width())
        最大高 = max(最大高, int(字符面.get_height()))

    if not 字符面列表:
        return pygame.Surface((1, 1), pygame.SRCALPHA)

    总宽 += 间距 * max(0, len(字符面列表) - 1)
    总宽 = max(1, int(总宽))
    最大高 = max(1, int(最大高))
    画布 = pygame.Surface((总宽, 最大高), pygame.SRCALPHA)

    当前x = 0
    for idx, 字符面 in enumerate(字符面列表):
        当前y = 最大高 - int(字符面.get_height())
        画布.blit(字符面, (当前x, 当前y))
        当前x += int(字符面.get_width())
        if idx < len(字符面列表) - 1:
            当前x += 间距

    return 画布


def _取游玩次数颜色(游玩次数: int) -> Tuple[int, int, int]:
    try:
        次数 = int(max(0, int(游玩次数 or 0)))
    except Exception:
        次数 = 0

    if 次数 >= 5:
        return (255, 96, 96)
    if 次数 >= 3:
        return (255, 214, 72)
    if 次数 >= 1:
        return (96, 232, 128)
    return (235, 235, 235)


def _需要HOT标记(游玩次数: int) -> bool:
    try:
        return int(max(0, int(游玩次数 or 0))) >= 2
    except Exception:
        return False


def _取歌曲模式标记文本(歌: Optional["歌曲信息"]) -> str:
    if 歌 is None:
        return ""
    try:
        _按需补全歌曲模式标记字段(歌)
    except Exception:
        pass
    try:
        文本 = str(getattr(歌, "谱面模式标记", "") or "").strip()
    except Exception:
        文本 = ""
    if 文本:
        return 文本
    try:
        谱面类型 = str(getattr(歌, "谱面charttype", "") or "").strip().lower()
    except Exception:
        谱面类型 = ""
    映射文本 = _推断谱面类型模式标记(谱面类型)
    if 映射文本:
        return 映射文本
    try:
        模式文本 = str(getattr(歌, "模式", "") or "").strip()
    except Exception:
        模式文本 = ""
    模式小写 = 模式文本.lower()
    if ("情侣" in 模式文本) or ("lover" in 模式小写):
        return "情侣"
    return ""


def _取歌曲模式标记配色(模式标记: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    文本 = str(模式标记 or "").strip()
    if 文本 == "疯狂":
        return (230, 96, 42), (255, 248, 238)
    if 文本 == "表演":
        return (45, 122, 222), (245, 250, 255)
    if 文本 == "混音":
        return (156, 72, 214), (251, 245, 255)
    if 文本 == "情侣":
        return (223, 82, 132), (255, 246, 250)
    if 文本 == "双踏板":
        return (34, 158, 150), (242, 255, 252)
    return (70, 70, 78), (255, 255, 255)


def _绘制歌曲模式标记(
    屏幕: pygame.Surface,
    锚点矩形: pygame.Rect,
    歌: Optional["歌曲信息"],
    *,
    是否大图: bool = False,
    透明度: int = 255,
) -> None:
    if not isinstance(屏幕, pygame.Surface):
        return
    if not isinstance(锚点矩形, pygame.Rect) or 锚点矩形.w <= 8 or 锚点矩形.h <= 8:
        return

    模式标记 = _取歌曲模式标记文本(歌)
    if not 模式标记:
        return

    透明度 = max(0, min(255, int(透明度 or 0)))
    if 透明度 <= 0:
        return

    最短边 = max(1, min(int(锚点矩形.w), int(锚点矩形.h)))
    目标字号 = int(round(最短边 * (0.12 if 是否大图 else 0.16)))
    最小字号 = 14 if bool(是否大图) else 10
    字号 = max(最小字号, 目标字号)
    最大宽 = max(28, int(round(float(锚点矩形.w) * (0.36 if 是否大图 else 0.54))))
    背景色, 文字色 = _取歌曲模式标记配色(模式标记)

    try:
        字体 = 获取字体(字号, 是否粗体=True)
        while 字号 > 最小字号 and 字体.size(模式标记)[0] > 最大宽:
            字号 -= 1
            字体 = 获取字体(字号, 是否粗体=True)
        文字面 = 字体.render(模式标记, True, 文字色)
    except Exception:
        return

    内边距x = max(6, int(round(字号 * (0.85 if 是否大图 else 0.70))))
    内边距y = max(3, int(round(字号 * 0.38)))
    圆角 = max(6, int(round(字号 * 0.48)))
    标记宽 = max(文字面.get_width() + 内边距x * 2, int(round(字号 * 2.4)))
    标记高 = max(文字面.get_height() + 内边距y * 2, int(round(字号 * 1.8)))
    外边距 = max(4, int(round(最短边 * (0.04 if 是否大图 else 0.03))))

    标记面 = pygame.Surface((标记宽, 标记高), pygame.SRCALPHA)
    pygame.draw.rect(
        标记面,
        (0, 0, 0, max(0, int(透明度 * 0.22))),
        pygame.Rect(2, 3, 标记宽 - 2, 标记高 - 2),
        border_radius=圆角,
    )
    pygame.draw.rect(
        标记面,
        (背景色[0], 背景色[1], 背景色[2], int(透明度)),
        pygame.Rect(0, 0, 标记宽, 标记高),
        border_radius=圆角,
    )
    pygame.draw.rect(
        标记面,
        (255, 255, 255, max(0, int(透明度 * 0.50))),
        pygame.Rect(0, 0, 标记宽, 标记高),
        width=max(1, int(round(字号 * 0.08))),
        border_radius=圆角,
    )

    文字矩形 = 文字面.get_rect(center=(标记宽 // 2, 标记高 // 2))
    标记面.blit(文字面, 文字矩形.topleft)

    绘制矩形 = 标记面.get_rect()
    绘制矩形.top = int(锚点矩形.top + 外边距)
    绘制矩形.right = int(锚点矩形.right - 外边距)
    屏幕.blit(标记面, 绘制矩形.topleft)


_支持背景视频扩展名 = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ogv")


def _归一化资源名(文本: str) -> str:
    基名 = os.path.splitext(os.path.basename(str(文本 or "")))[0]
    return re.sub(r"[\s_\-()\[\]{}]+", "", 基名).strip().lower()


def _查找歌曲目录背景视频(
    歌曲路径: str,
    sm路径: str = "",
    封面路径: str = "",
    sm文本: str = "",
) -> str:
    if not os.path.isdir(歌曲路径):
        return ""

    谱面基名 = _归一化资源名(sm路径)
    封面基名 = _归一化资源名(封面路径)
    文件夹基名 = _归一化资源名(歌曲路径)
    谱面文本小写 = str(sm文本 or "").lower()

    候选列表: List[Tuple[int, int, str]] = []
    try:
        文件名列表 = sorted(os.listdir(歌曲路径))
    except Exception:
        return ""

    for 文件名 in 文件名列表:
        路径 = os.path.join(歌曲路径, 文件名)
        扩展名 = os.path.splitext(str(文件名 or ""))[1].lower()
        if (not os.path.isfile(路径)) or 扩展名 not in _支持背景视频扩展名:
            continue

        文件名小写 = str(文件名 or "").lower()
        归一基名 = _归一化资源名(文件名)
        分数 = 0
        if 谱面文本小写 and 文件名小写 in 谱面文本小写:
            分数 += 400
        if 归一基名 and 谱面基名 and 归一基名 == 谱面基名:
            分数 += 220
        if 归一基名 and 封面基名 and 归一基名 == 封面基名:
            分数 += 120
        if 归一基名 and 文件夹基名 and 归一基名 == 文件夹基名:
            分数 += 80
        if any(关键字 in 文件名小写 for 关键字 in ("background", "bga", "bgmovie", "movie")):
            分数 += 90
        elif 文件名小写.startswith(("bg", "mv")):
            分数 += 55
        if any(关键字 in 文件名小写 for 关键字 in ("preview", "sample", "demo", "cut")):
            分数 -= 240
        try:
            文件大小 = int(os.path.getsize(路径))
        except Exception:
            文件大小 = 0
        分数 += min(60, int(文件大小 / (1024 * 1024)))
        候选列表.append((分数, 文件大小, 路径))

    if not 候选列表:
        return ""
    候选列表.sort(
        key=lambda 项: (int(项[0]), int(项[1]), str(项[2]).lower()),
        reverse=True,
    )
    return str(候选列表[0][2] or "")

def 安全读取文本(文件路径: str, 最大字符数: int = 0) -> str:
    读取长度 = int(最大字符数 or 0)
    for 编码 in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(文件路径, "r", encoding=编码, errors="strict") as f:
                return f.read(读取长度) if 读取长度 > 0 else f.read()
        except Exception:
            continue
    with open(文件路径, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(读取长度) if 读取长度 > 0 else f.read()


def 安全读取json(文件路径: str) -> Optional[dict]:
    for 编码 in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(文件路径, "r", encoding=编码, errors="strict") as f:
                return json.load(f)
        except Exception:
            continue
    try:
        with open(文件路径, "r", encoding="utf-8", errors="ignore") as f:
            return json.load(f)
    except Exception:
        return None

def _提取SM标签原始值(sm文本: str, 标签名: str) -> str:
    try:
        文本 = str(sm文本 or "").replace("\r\n", "\n").replace("\r", "\n")
        标签 = str(标签名 or "").strip()
        if (not 文本) or (not 标签):
            return ""

        匹配 = re.search(rf"(?im)^\s*#{re.escape(标签)}\s*:\s*", 文本)
        if not 匹配:
            return ""

        起始 = int(匹配.end())
        结束 = 起始
        总长 = len(文本)
        while 结束 < 总长:
            当前字符 = 文本[结束]
            if 当前字符 == ";":
                break
            if 当前字符 == "\n":
                下标 = 结束 + 1
                while 下标 < 总长 and 文本[下标] in (" ", "\t"):
                    下标 += 1
                if 下标 < 总长 and 文本[下标] == "#":
                    break
            结束 += 1

        return str(文本[起始:结束] or "").strip()
    except Exception:
        return ""


def _提取SM标签值(sm文本: str, 标签名: str) -> str:
    原始值 = _提取SM标签原始值(sm文本, 标签名)
    if not 原始值:
        return ""

    行列表 = str(原始值).split("\n")
    去注释后: List[str] = []
    for 行 in 行列表:
        if "//" in 行:
            行 = 行.split("//", 1)[0]
        去注释后.append(行)
    return "".join(去注释后).strip()

def _解析文本里的首个正数(文本: str) -> Optional[float]:
    if not 文本:
        return None
    for 匹配 in re.finditer(r"-?\d+(?:\.\d+)?", str(文本 or "")):
        try:
            数值 = float(匹配.group(0))
        except Exception:
            continue
        if 数值 > 0:
            return 数值
    return None

def _解析BPMS标签首个BPM(原始标签值: str) -> Optional[float]:
    文本 = str(原始标签值 or "").strip()
    if not 文本:
        return None

    for 片段 in 文本.split(","):
        if "=" not in 片段:
            continue
        _, bpm文本 = 片段.split("=", 1)
        数值 = _解析文本里的首个正数(bpm文本)
        if 数值 is not None and 数值 > 0:
            return 数值
    return None

def _规范化谱面文本(谱面文本: str) -> str:
    return str(谱面文本 or "").replace("\r\n", "\n").replace("\r", "\n")

def _提取SSC谱面块列表(谱面文本: str) -> List[str]:
    文本 = _规范化谱面文本(谱面文本)
    if not 文本:
        return []

    结果: List[str] = []
    for 匹配 in re.finditer(
        r"^\s*#NOTEDATA\s*:\s*;\s*(.*?)(?=^\s*#NOTEDATA\s*:\s*;|\Z)",
        文本,
        flags=re.IGNORECASE | re.DOTALL | re.MULTILINE,
    ):
        块文本 = str(匹配.group(1) or "").strip()
        if 块文本:
            结果.append(块文本)
    return 结果

def _计算谱面列数(谱面数据文本: str) -> int:
    try:
        纯文本 = _规范化谱面文本(谱面数据文本)
        for 小节 in 纯文本.split(","):
            行列表 = [
                行.strip()
                for 行 in 小节.split("\n")
                if 行.strip() and (not 行.strip().startswith("//"))
            ]
            if 行列表:
                return max(1, len(行列表[0]))
    except Exception:
        return 5
    return 5


def _解析SMNotes块字段(块文本: str) -> Optional[dict]:
    文本 = str(块文本 or "")
    if not 文本.strip():
        return None

    标准字段 = 文本.split(":", 5)
    if len(标准字段) >= 6:
        return {
            "charttype": str(标准字段[0] or "").strip().lower(),
            "description_text": str(标准字段[1] or "").strip(),
            "difficulty_text": str(标准字段[2] or "").strip(),
            "meter_text": str(标准字段[3] or "").strip(),
            "notes_text": str(标准字段[5] or ""),
        }

    舞推字段 = 文本.split(":", 4)
    if len(舞推字段) >= 5:
        return {
            "charttype": str(舞推字段[0] or "").strip().lower(),
            "description_text": str(舞推字段[1] or "").strip(),
            "difficulty_text": str(舞推字段[2] or "").strip(),
            "meter_text": str(舞推字段[3] or "").strip(),
            "notes_text": str(舞推字段[4] or ""),
        }

    return None


def _收集SM谱面候选信息(谱面文本: str) -> List[dict]:
    结果: List[dict] = []

    for 匹配 in re.finditer(r"#NOTES\s*:\s*(.*?);", 谱面文本, flags=re.IGNORECASE | re.DOTALL):
        字段 = _解析SMNotes块字段(str(匹配.group(1) or ""))
        if not isinstance(字段, dict):
            continue
        谱面类型 = str(字段.get("charttype", "") or "")
        星级文本 = str(字段.get("meter_text", "") or "")
        谱面数据文本 = str(字段.get("notes_text", "") or "")
        结果.append(
            {
                "charttype": 谱面类型,
                "description_text": str(字段.get("description_text", "") or ""),
                "difficulty_text": str(字段.get("difficulty_text", "") or ""),
                "meter_text": 星级文本,
                "notes_text": 谱面数据文本,
                "bpms_text": "",
                "offset_text": "",
                "columns": _计算谱面列数(谱面数据文本),
            }
        )

    for 块文本 in _提取SSC谱面块列表(谱面文本):
        谱面类型 = _提取SM标签值(块文本, "STEPSTYPE").lower()
        星级文本 = _提取SM标签值(块文本, "METER")
        谱面数据文本 = _提取SM标签值(块文本, "NOTES")
        if not 谱面数据文本:
            continue

        结果.append(
            {
                "charttype": 谱面类型,
                "description_text": "",
                "difficulty_text": "",
                "meter_text": 星级文本,
                "notes_text": 谱面数据文本,
                "bpms_text": _提取SM标签值(块文本, "BPMS"),
                "offset_text": _提取SM标签值(块文本, "OFFSET"),
                "columns": _计算谱面列数(谱面数据文本),
            }
        )

    return 结果

def _首选谱面优先级(charttype: str) -> int:
    谱面类型 = str(charttype or "").strip().lower()
    if "pump-single" in 谱面类型:
        return 50
    if "dance-single" in 谱面类型:
        return 45
    if 谱面类型 == "hard":
        return 42
    if "single" in 谱面类型:
        return 40
    if 谱面类型 == "remix":
        return 35
    if 谱面类型 in {"lover1", "lover2"}:
        return 18
    if "pump-double" in 谱面类型:
        return 30
    if "double" in 谱面类型:
        return 20
    return 10

def _选取首选谱面候选(候选列表: List[dict]) -> Optional[dict]:
    if not 候选列表:
        return None

    def _排序键(项: dict) -> Tuple[int, int]:
        优先级 = _首选谱面优先级(str(项.get("charttype", "") or ""))
        try:
            列数 = int(项.get("columns", 0) or 0)
        except Exception:
            列数 = 0
        return (优先级, 列数)

    return max(候选列表, key=_排序键)


_10位复合谱模式映射: Dict[str, str] = {
    "hard": "疯狂",
    "single": "表演",
    "remix": "混音",
    "double": "双踏板",
    "lover": "情侣",
}
_10位复合谱模式别名: Dict[str, str] = {"lover1": "lover", "lover2": "lover"}
_10位复合谱模式顺序: Dict[str, int] = {
    "hard": 0,
    "single": 1,
    "remix": 2,
    "double": 3,
    "lover": 4,
}


def _标准化谱面候选文本(文本: str) -> str:
    结果 = str(文本 or "").strip().lower()
    结果 = re.sub(r"[\s_\-]+", "", 结果)
    return str(结果)


def _解析10位复合谱模式键(
    charttype: str, description_text: str = "", difficulty_text: str = ""
) -> str:
    谱面类型 = str(charttype or "").strip().lower()
    if 谱面类型 in _10位复合谱模式映射:
        return str(谱面类型)
    别名模式 = str(_10位复合谱模式别名.get(谱面类型, "") or "")
    if 别名模式:
        return 别名模式

    描述标准 = _标准化谱面候选文本(description_text)
    难度标准 = _标准化谱面候选文本(difficulty_text)
    if any(
        关键词 in 描述标准 or 关键词 in 难度标准
        for 关键词 in ("lover1", "lover2", "lover", "情侣")
    ):
        return "lover"
    return ""


def _推断情侣模式charttype(
    charttype: str, description_text: str = "", difficulty_text: str = ""
) -> str:
    谱面类型 = str(charttype or "").strip().lower()
    if 谱面类型 in {"lover1", "lover2"}:
        return str(谱面类型)

    描述标准 = _标准化谱面候选文本(description_text)
    难度标准 = _标准化谱面候选文本(difficulty_text)
    if ("lover2" in 描述标准) or ("lover2" in 难度标准):
        return "lover2"
    return "lover1"


def _是否10位复合谱候选(
    charttype: str,
    列数: int,
    description_text: str = "",
    difficulty_text: str = "",
) -> bool:
    谱面类型 = str(charttype or "").strip().lower()
    try:
        总列数 = int(列数 or 0)
    except Exception:
        总列数 = 0
    模式键 = _解析10位复合谱模式键(
        谱面类型,
        description_text=description_text,
        difficulty_text=difficulty_text,
    )
    return 总列数 in (10, 20) and bool(模式键)


def _解析复合谱level星级(*候选文本: str) -> Optional[int]:
    for 文本 in 候选文本:
        匹配 = re.search(r"(?i)\blevel\s*([0-9]+)\b", str(文本 or "").strip())
        if not 匹配:
            continue
        try:
            星级 = int(匹配.group(1))
        except Exception:
            continue
        if 星级 > 0:
            return max(1, min(20, 星级))
    return None


def _解析谱面候选星级(谱面信息: dict) -> Optional[int]:
    if not isinstance(谱面信息, dict):
        return None

    谱面类型 = str(谱面信息.get("charttype", "") or "").strip().lower()
    try:
        列数 = int(谱面信息.get("columns", 0) or 0)
    except Exception:
        列数 = 0

    描述文本 = str(谱面信息.get("description_text", "") or "")
    难度文本 = str(谱面信息.get("difficulty_text", "") or "")
    if _是否10位复合谱候选(
        谱面类型,
        列数,
        description_text=描述文本,
        difficulty_text=难度文本,
    ):
        level星级 = _解析复合谱level星级(
            描述文本,
            难度文本,
        )
        if level星级 is not None:
            return int(level星级)

    星级数值 = _解析文本里的首个正数(str(谱面信息.get("meter_text", "") or ""))
    if 星级数值 is None:
        return None
    try:
        星级 = int(round(float(星级数值)))
    except Exception:
        return None
    if 星级 <= 0:
        return None
    return max(1, min(20, 星级))


def _提取10位复合谱模式条目(谱面候选列表: List[dict]) -> List[dict]:
    if not isinstance(谱面候选列表, list):
        return []

    模式最佳候选: Dict[str, dict] = {}
    for 谱面信息 in 谱面候选列表:
        if not isinstance(谱面信息, dict):
            continue
        谱面类型 = str(谱面信息.get("charttype", "") or "").strip().lower()
        描述文本 = str(谱面信息.get("description_text", "") or "")
        难度文本 = str(谱面信息.get("difficulty_text", "") or "")
        try:
            列数 = int(谱面信息.get("columns", 0) or 0)
        except Exception:
            列数 = 0
        模式键 = _解析10位复合谱模式键(
            谱面类型,
            description_text=描述文本,
            difficulty_text=难度文本,
        )
        if (not 模式键) or (
            not _是否10位复合谱候选(
                谱面类型,
                列数,
                description_text=描述文本,
                difficulty_text=难度文本,
            )
        ):
            continue

        模式标记 = _10位复合谱模式映射.get(模式键, "")
        if not 模式标记:
            continue

        记录charttype = (
            _推断情侣模式charttype(谱面类型, 描述文本, 难度文本)
            if 模式键 == "lover"
            else 谱面类型
        )
        星级 = _解析谱面候选星级(谱面信息)
        当前条目 = {
            "charttype": str(记录charttype),
            "模式键": str(模式键),
            "模式标记": 模式标记,
            "星级": int(星级) if 星级 is not None else None,
            "columns": int(列数),
            "meter_text": str(谱面信息.get("meter_text", "") or ""),
        }
        已有条目 = 模式最佳候选.get(模式键)
        if 已有条目 is None:
            模式最佳候选[模式键] = 当前条目
            continue

        旧星级 = 已有条目.get("星级")
        新星级 = 当前条目.get("星级")
        if int(新星级 or 0) > int(旧星级 or 0):
            模式最佳候选[模式键] = 当前条目
            continue
        if int(新星级 or 0) == int(旧星级 or 0) and int(列数) > int(
            已有条目.get("columns", 0) or 0
        ):
            模式最佳候选[模式键] = 当前条目
            continue
        if (
            str(模式键) == "lover"
            and int(新星级 or 0) == int(旧星级 or 0)
            and int(列数) == int(已有条目.get("columns", 0) or 0)
        ):
            旧charttype = str(已有条目.get("charttype", "") or "").strip().lower()
            新charttype = str(当前条目.get("charttype", "") or "").strip().lower()
            if 旧charttype == "lover2" and 新charttype == "lover1":
                模式最佳候选[模式键] = 当前条目

    return sorted(
        模式最佳候选.values(),
        key=lambda 项: (
            int(_10位复合谱模式顺序.get(str(项.get("模式键", "") or ""), 999)),
            str(项.get("模式键", "") or ""),
        ),
    )


def _解析模式文本到复合谱模式键(模式文本: str) -> str:
    文本 = str(模式文本 or "").strip().lower()
    if not 文本:
        return ""
    if ("疯狂" in 文本) or ("hard" in 文本):
        return "hard"
    if ("表演" in 文本) or ("single" in 文本):
        return "single"
    if ("混音" in 文本) or ("remix" in 文本):
        return "remix"
    if ("双踏板" in 文本) or ("double" in 文本):
        return "double"
    if ("情侣" in 文本) or ("lover" in 文本):
        return "lover"
    return ""


def _按模式键选取复合谱条目(条目列表: List[dict], 模式文本: str) -> Optional[dict]:
    if not isinstance(条目列表, list) or (not 条目列表):
        return None
    目标模式键 = _解析模式文本到复合谱模式键(模式文本)
    if 目标模式键:
        for 条目 in 条目列表:
            if not isinstance(条目, dict):
                continue
            if str(条目.get("模式键", "") or "").strip().lower() == 目标模式键:
                return 条目
    for 条目 in 条目列表:
        if isinstance(条目, dict):
            return 条目
    return None


def _推断谱面类型模式标记(
    charttype: str, description_text: str = "", difficulty_text: str = ""
) -> str:
    谱面类型 = str(charttype or "").strip().lower()
    模式键 = _解析10位复合谱模式键(
        谱面类型,
        description_text=description_text,
        difficulty_text=difficulty_text,
    )
    模式标记 = str(_10位复合谱模式映射.get(模式键, "") or "")
    if 模式标记:
        return 模式标记

    if 谱面类型 in {"lover1", "lover2"}:
        return "情侣"
    if "double" in 谱面类型:
        return "双踏板"
    if "remix" in 谱面类型:
        return "混音"
    if 谱面类型 == "hard":
        return "疯狂"
    if "single" in 谱面类型:
        return "表演"
    return ""


def _解析SM模式标记候选信息(sm路径: str) -> dict:
    空结果 = {"复合谱模式条目": [], "首选charttype": "", "首选模式标记": ""}
    路径 = os.path.abspath(str(sm路径 or "").strip()) if str(sm路径 or "").strip() else ""
    if (not 路径) or (not os.path.isfile(路径)):
        return dict(空结果)
    if os.path.splitext(路径)[1].lower() not in {".sm", ".ssc", ".sma"}:
        return dict(空结果)

    缓存键 = (路径, _取文件修改时间秒(路径))
    缓存命中 = _读取懒解析模式标记缓存(缓存键)
    if isinstance(缓存命中, dict):
        return dict(缓存命中)

    global _懒解析模式标记日志已输出
    if (not bool(_懒解析模式标记日志已输出)) and bool(_启用懒解析模式标记()):
        try:
            _记录信息日志(
                _日志器,
                "已启用懒解析模式标记：仅在绘制角标时按需解析SM谱面类型",
            )
        except Exception:
            pass
        _懒解析模式标记日志已输出 = True

    结果 = dict(空结果)
    需要关闭GC = bool(_启用稳定谱面解析模式())
    曾关闭GC = _进入稳定GC区间(需要关闭GC)
    try:
        sm文本 = 安全读取文本(
            路径,
            最大字符数=600000 if 需要关闭GC else 0,
        )
        if sm文本:
            谱面候选列表 = _收集SM谱面候选信息(sm文本)
            if 谱面候选列表:
                复合谱条目 = _提取10位复合谱模式条目(谱面候选列表)
                if 复合谱条目:
                    结果["复合谱模式条目"] = [
                        条目
                        for 条目 in 复合谱条目
                        if isinstance(条目, dict)
                    ]

                首选谱面 = _选取首选谱面候选(谱面候选列表)
                if isinstance(首选谱面, dict):
                    谱面类型 = str(首选谱面.get("charttype", "") or "").strip().lower()
                    if 谱面类型:
                        结果["首选charttype"] = 谱面类型
                        结果["首选模式标记"] = _推断谱面类型模式标记(
                            谱面类型,
                            description_text=str(
                                首选谱面.get("description_text", "") or ""
                            ),
                            difficulty_text=str(
                                首选谱面.get("difficulty_text", "") or ""
                            ),
                        )
    except Exception:
        pass
    finally:
        _离开稳定GC区间(曾关闭GC)

    _写入懒解析模式标记缓存(缓存键, 结果)
    return dict(结果)


def _按需补全歌曲模式标记字段(歌: Optional["歌曲信息"]) -> None:
    if 歌 is None:
        return
    if not bool(_启用懒解析模式标记()):
        return

    try:
        现有模式标记 = str(getattr(歌, "谱面模式标记", "") or "").strip()
    except Exception:
        现有模式标记 = ""
    if 现有模式标记:
        return

    try:
        现有谱面类型 = str(getattr(歌, "谱面charttype", "") or "").strip().lower()
    except Exception:
        现有谱面类型 = ""
    try:
        sm路径 = str(getattr(歌, "sm路径", "") or "").strip()
    except Exception:
        sm路径 = ""
    if (not sm路径) or (not os.path.isfile(sm路径)):
        return

    def _标记已尝试() -> None:
        try:
            setattr(歌, "_懒解析模式标记已尝试", True)
        except Exception:
            pass

    # 已有charttype时直接补记录键，避免重复读盘。
    if 现有谱面类型:
        try:
            现有记录键 = str(getattr(歌, "记录键sm路径", "") or "").strip()
        except Exception:
            现有记录键 = ""
        if (not 现有记录键) or ("::charttype=" not in 现有记录键.lower()):
            try:
                setattr(歌, "记录键sm路径", _构建谱面记录键路径(sm路径, 现有谱面类型))
            except Exception:
                pass
        _标记已尝试()
        return

    try:
        if bool(getattr(歌, "_懒解析模式标记已尝试", False)):
            return
    except Exception:
        pass

    _标记已尝试()

    if os.path.splitext(sm路径)[1].lower() not in {".sm", ".ssc", ".sma"}:
        return

    解析结果 = _解析SM模式标记候选信息(sm路径)
    if not isinstance(解析结果, dict):
        return

    目标条目 = _按模式键选取复合谱条目(
        解析结果.get("复合谱模式条目", []),
        str(getattr(歌, "模式", "") or ""),
    )

    解析谱面类型 = ""
    解析模式标记 = ""
    是否复合谱 = False
    if isinstance(目标条目, dict):
        解析谱面类型 = str(目标条目.get("charttype", "") or "").strip().lower()
        解析模式标记 = str(目标条目.get("模式标记", "") or "").strip()
        是否复合谱 = bool(解析谱面类型 and 解析模式标记)
    else:
        解析谱面类型 = str(解析结果.get("首选charttype", "") or "").strip().lower()
        解析模式标记 = str(解析结果.get("首选模式标记", "") or "").strip()

    if not 解析谱面类型 and not 解析模式标记:
        return

    try:
        if 解析谱面类型:
            setattr(歌, "谱面charttype", 解析谱面类型)
    except Exception:
        pass
    try:
        if 解析模式标记:
            setattr(歌, "谱面模式标记", 解析模式标记)
    except Exception:
        pass
    try:
        if 解析谱面类型:
            setattr(歌, "记录键sm路径", _构建谱面记录键路径(sm路径, 解析谱面类型))
    except Exception:
        pass
    if 是否复合谱:
        try:
            setattr(歌, "是否10位复合谱", True)
        except Exception:
            pass


def _构建谱面记录键路径(sm路径: str, charttype: str = "") -> str:
    路径文本 = str(sm路径 or "").strip()
    谱面类型 = str(charttype or "").strip().lower()
    if (not 路径文本) or (not 谱面类型):
        return 路径文本
    return f"{路径文本}::charttype={谱面类型}"


def _取歌曲记录路径源(歌: Optional["歌曲信息"]) -> str:
    if 歌 is None:
        return ""
    try:
        记录键路径 = str(getattr(歌, "记录键sm路径", "") or "").strip()
    except Exception:
        记录键路径 = ""
    if 记录键路径:
        return 记录键路径
    try:
        return str(getattr(歌, "sm路径", "") or "").strip()
    except Exception:
        return ""

def 解析显示BPM(sm文本: str) -> Optional[int]:
    显示BPM原始 = _提取SM标签值(sm文本, "DISPLAYBPM")
    数值 = _解析文本里的首个正数(显示BPM原始)
    if 数值 is None:
        bpms原始 = _提取SM标签值(sm文本, "BPMS")
        数值 = _解析BPMS标签首个BPM(bpms原始)
    if 数值 is None:
        return None
    try:
        return int(round(float(数值)))
    except Exception:
        return None

def 解析SM标题(sm文本: str) -> str:
    匹配 = re.search(r"#TITLE\s*:\s*([^;]+)\s*;", sm文本, flags=re.IGNORECASE)
    if not 匹配:
        return ""
    return str(匹配.group(1) or "").strip()


def 解析JSON显示BPM(谱面数据: dict) -> Optional[int]:
    try:
        bpms = (谱面数据 or {}).get("bpms", []) or []
        if not bpms:
            return None
        # 取 lineNo 最小的一条
        bpms_sorted = sorted(bpms, key=lambda x: int(x.get("lineNo", 0)))
        bpm = float(bpms_sorted[0].get("bpmVal", 0))
        if bpm <= 0:
            return None
        return int(round(bpm))
    except Exception:
        return None


def 解析JSON标题(谱面数据: dict) -> str:
    try:
        score = (谱面数据 or {}).get("scoreInfo", {}) or {}
        for key in ("title", "name", "songName"):
            v = str(score.get(key, "") or "").strip()
            if v:
                return v
    except Exception:
        return ""
    return ""

def 从文件夹名解析歌名星级(文件夹名: str) -> Tuple[str, int]:
    """
    严格按末尾 #数字 解析星级：#几 就画几颗星
    ✅ 规则：星级范围钳制到 1~20（你要求最大 20 星）
    示例：FANCY_CLUB#1+1=0_1706#4  => 星级=4，歌名=1+1=0_1706
    """
    星级 = 3
    末尾星级匹配 = re.search(r"#\s*(\d+)\s*$", 文件夹名)
    if 末尾星级匹配:
        try:
            星级 = int(末尾星级匹配.group(1))
        except Exception:
            星级 = 3
    else:
        前缀星级匹配 = re.match(r"^\(\s*(\d+)\s*\)\s*", 文件夹名)
        if 前缀星级匹配:
            try:
                星级 = int(前缀星级匹配.group(1))
            except Exception:
                星级 = 3

    parts = 文件夹名.split("#")
    if len(parts) >= 2:
        if 末尾星级匹配:
            中间 = "#".join(parts[1:-1]) if len(parts) > 2 else parts[1]
        else:
            中间 = "#".join(parts[1:])
    else:
        中间 = 文件夹名

    中间 = 中间.strip()
    中间 = re.sub(r"^\(\s*\d+\s*\)\s*", "", 中间)
    中间 = re.sub(r"^\d+\s*", "", 中间)
    中间 = re.sub(r"^[\-_ ]+", "", 中间)
    歌名 = 中间 if 中间 else 文件夹名

    # ✅ 星级钳制 1~20
    try:
        星级 = int(星级)
    except Exception:
        星级 = 3
    星级 = max(1, min(20, 星级))

    return 歌名, 星级

def _解析SM谱面星级(sm文本: str) -> Optional[int]:
    if not sm文本:
        return None

    候选列表: List[Tuple[int, int]] = []
    for 谱面信息 in _收集SM谱面候选信息(sm文本):
        谱面类型 = str(谱面信息.get("charttype", "") or "").strip().lower()
        星级 = _解析谱面候选星级(谱面信息)
        if 星级 is None:
            continue

        优先级 = 0
        if "pump-single" in 谱面类型:
            优先级 = 50
        elif "dance-single" in 谱面类型:
            优先级 = 45
        elif 谱面类型 == "hard":
            优先级 = 42
        elif "single" in 谱面类型:
            优先级 = 40
        elif 谱面类型 == "remix":
            优先级 = 35
        elif 谱面类型 in {"lover1", "lover2"}:
            优先级 = 18
        elif "pump-double" in 谱面类型:
            优先级 = 30
        elif "double" in 谱面类型:
            优先级 = 20
        else:
            优先级 = 10

        候选列表.append((优先级, 星级))

    if not 候选列表:
        return None

    最高优先级 = max(项[0] for 项 in 候选列表)
    同优先级候选 = [星级 for 优先级, 星级 in 候选列表 if 优先级 == 最高优先级]
    if not 同优先级候选:
        return None
    return max(1, min(20, max(同优先级候选)))

def _构建歌曲信息对象(
    *,
    类型名: str,
    模式名: str,
    歌曲文件夹: str,
    歌曲路径: str,
    sm路径: str,
    音频路径: Optional[str],
    封面路径: Optional[str],
    歌名: str,
    星级: int,
    bpm: Optional[int],
    背景视频路径: str,
    谱面charttype: str = "",
    谱面模式标记: str = "",
    是否10位复合谱: bool = False,
) -> "歌曲信息":
    谱面类型 = str(谱面charttype or "").strip().lower()
    return 歌曲信息(
        序号=0,
        类型=str(类型名 or ""),
        模式=str(模式名 or ""),
        歌曲文件夹=歌曲文件夹,
        歌曲路径=歌曲路径,
        sm路径=sm路径,
        mp3路径=音频路径,
        封面路径=封面路径,
        歌名=歌名,
        星级=max(1, int(星级 or 1)),
        bpm=bpm,
        是否VIP=bool(int(星级 or 0) >= 5),
        游玩次数=0,
        是否带MV=bool(str(背景视频路径 or "").strip()),
        谱面charttype=谱面类型,
        谱面模式标记=str(谱面模式标记 or ""),
        记录键sm路径=_构建谱面记录键路径(sm路径, 谱面类型),
        是否10位复合谱=bool(是否10位复合谱),
    )


def 解析歌曲元数据列表(sm路径: str, 类型名: str, 模式名: str) -> List["歌曲信息"]:
    global _稳定谱面解析模式日志已输出
    if (not sm路径) or (not os.path.isfile(sm路径)):
        return []
    _记录扫描谱面路径(sm路径, 类型名, 模式名)

    歌曲路径 = os.path.dirname(sm路径)
    歌曲文件夹 = os.path.basename(歌曲路径)
    if str(歌曲文件夹 or "").strip().lower() in {"backup", "backups"}:
        return []
    扩展名 = os.path.splitext(sm路径)[1].lower()
    sm文本 = ""
    json数据 = None
    稳定谱面解析模式 = bool((扩展名 != ".json") and _启用稳定谱面解析模式())
    if 扩展名 == ".json":
        json数据 = 安全读取json(sm路径)
        if (not isinstance(json数据, dict)) or (
            ("boards" not in json数据) and ("bpms" not in json数据)
        ):
            return []
    else:
        sm文本 = 安全读取文本(
            sm路径,
            最大字符数=600000 if 稳定谱面解析模式 else 0,
        )
        if 稳定谱面解析模式 and (not bool(_稳定谱面解析模式日志已输出)):
            try:
                _记录信息日志(
                    _日志器,
                    "已启用稳定谱面解析模式：打包环境跳过SM深度解析（列数/复合谱拆分）",
                )
            except Exception:
                pass
            _稳定谱面解析模式日志已输出 = True

    音频路径 = 找文件(歌曲路径, (".ogg", ".mp3", ".wav"))
    封面路径 = 找封面(歌曲路径)
    背景视频路径 = _查找歌曲目录背景视频(
        歌曲路径,
        sm路径=sm路径,
        封面路径=str(封面路径 or ""),
        sm文本=sm文本 if 扩展名 != ".json" else "",
    )
    if 扩展名 == ".json":
        bpm = 解析JSON显示BPM(json数据)
        if bpm is None:
            bpm = 120
    else:
        bpm = 解析显示BPM(sm文本)
    歌名, 星级 = 从文件夹名解析歌名星级(歌曲文件夹)
    复合谱模式条目: List[dict] = []
    if 扩展名 != ".json":
        if not 稳定谱面解析模式:
            try:
                谱面候选列表 = _收集SM谱面候选信息(sm文本)
                首选谱面 = _选取首选谱面候选(谱面候选列表)
                if 首选谱面 is not None:
                    谱面BPMS文本 = str(首选谱面.get("bpms_text", "") or "").strip()
                    if 谱面BPMS文本:
                        谱面BPM = _解析BPMS标签首个BPM(谱面BPMS文本)
                        if 谱面BPM is not None:
                            bpm = int(round(float(谱面BPM)))

                谱面星级 = _解析SM谱面星级(sm文本)
                if 谱面星级 is not None:
                    星级 = int(谱面星级)
                复合谱模式条目 = _提取10位复合谱模式条目(谱面候选列表)
            except Exception as 异常:
                _记录异常日志(
                    _日志器,
                    f"SM深度解析失败，已回退轻量解析 sm路径={sm路径}",
                    异常,
                )

    if "#" not in str(歌曲文件夹 or ""):
        if 扩展名 == ".json":
            json标题 = 解析JSON标题(json数据)
            if json标题:
                歌名 = json标题
        else:
            sm标题 = 解析SM标题(sm文本)
            if sm标题:
                歌名 = sm标题

    if 复合谱模式条目:
        结果列表: List[歌曲信息] = []
        for 条目 in 复合谱模式条目:
            try:
                条目星级 = int(条目.get("星级", 星级) or 星级)
            except Exception:
                条目星级 = int(星级)
            结果列表.append(
                _构建歌曲信息对象(
                    类型名=类型名,
                    模式名=模式名,
                    歌曲文件夹=歌曲文件夹,
                    歌曲路径=歌曲路径,
                    sm路径=sm路径,
                    音频路径=音频路径,
                    封面路径=封面路径,
                    歌名=歌名,
                    星级=条目星级,
                    bpm=bpm,
                    背景视频路径=str(背景视频路径 or ""),
                    谱面charttype=str(条目.get("charttype", "") or ""),
                    谱面模式标记=str(条目.get("模式标记", "") or ""),
                    是否10位复合谱=True,
                )
            )
        return 结果列表

    return [
        _构建歌曲信息对象(
            类型名=类型名,
            模式名=模式名,
            歌曲文件夹=歌曲文件夹,
            歌曲路径=歌曲路径,
            sm路径=sm路径,
            音频路径=音频路径,
            封面路径=封面路径,
            歌名=歌名,
            星级=max(1, int(星级 or 1)),
            bpm=bpm,
            背景视频路径=str(背景视频路径 or ""),
        )
    ]


def 解析歌曲元数据(sm路径: str, 类型名: str, 模式名: str) -> Optional["歌曲信息"]:
    结果列表 = 解析歌曲元数据列表(sm路径, 类型名, 模式名)
    if not 结果列表:
        return None
    return 结果列表[0]

def 找文件(目录: str, 扩展名集合: Tuple[str, ...]) -> Optional[str]:
    if not os.path.isdir(目录):
        return None
    for 文件名 in os.listdir(目录):
        低 = 文件名.lower()
        if any(低.endswith(ext) for ext in 扩展名集合):
            return os.path.join(目录, 文件名)
    return None

def 找封面(歌曲路径: str) -> Optional[str]:
    """
    优先 bann.*，找不到再退回任意 jpg/png/webp
    """
    if not os.path.isdir(歌曲路径):
        return None
    for 文件名 in os.listdir(歌曲路径):
        低 = 文件名.lower()
        if 低.startswith("bann.") and (
            低.endswith(".jpg")
            or 低.endswith(".jpeg")
            or 低.endswith(".png")
            or 低.endswith(".webp")
        ):
            return os.path.join(歌曲路径, 文件名)
    return 找文件(歌曲路径, (".jpg", ".jpeg", ".png", ".webp"))

def _谱面文件优先级(文件路径: str) -> int:
    扩展名 = os.path.splitext(str(文件路径 or ""))[1].lower()
    return {".json": 3, ".ssc": 2, ".sm": 1, ".sma": 1}.get(扩展名, 0)

def _收集候选谱面文件(根目录: str) -> List[str]:
    if not os.path.isdir(根目录):
        return []

    每目录最佳文件: Dict[str, str] = {}

    for 当前根, 目录列表, 文件列表 in os.walk(根目录):
        for 文件名 in 文件列表:
            扩展名 = os.path.splitext(str(文件名 or ""))[1].lower()
            if 扩展名 not in {".json", ".ssc", ".sm", ".sma"}:
                continue

            文件路径 = os.path.join(当前根, 文件名)
            目录键 = os.path.abspath(os.path.dirname(文件路径))
            已有文件 = 每目录最佳文件.get(目录键)
            if not 已有文件:
                每目录最佳文件[目录键] = 文件路径
                continue

            当前优先级 = _谱面文件优先级(文件路径)
            已有优先级 = _谱面文件优先级(已有文件)
            if 当前优先级 > 已有优先级:
                每目录最佳文件[目录键] = 文件路径
                continue

            if 当前优先级 == 已有优先级 and str(文件路径).casefold() < str(已有文件).casefold():
                每目录最佳文件[目录键] = 文件路径

    return [每目录最佳文件[k] for k in sorted(每目录最佳文件.keys(), key=str.casefold)]

@_串行化歌曲扫描
def 扫描songs目录(songs根目录: str) -> Dict[str, Dict[str, List[歌曲信息]]]:
    结果: Dict[str, Dict[str, List[歌曲信息]]] = {}
    根目录 = os.path.abspath(str(songs根目录 or "").strip())
    if not os.path.isdir(根目录):
        return 结果

    try:
        _记录信息日志(
            _日志器,
            (
                "开始全量扫描songs目录 "
                f"渲染后端={str(os.environ.get('E5CM_RENDER_BACKEND', '') or '-')} "
                f"根目录={根目录}"
            ),
        )
    except Exception:
        pass

    缓存键 = _构建全量扫描缓存键(根目录)
    缓存命中 = _读取歌曲扫描缓存(缓存键)
    if 缓存命中 is not None:
        命中歌曲数 = _统计数据树歌曲总数(缓存命中)
        if 命中歌曲数 > 0:
            try:
                _记录信息日志(
                    _日志器,
                    f"命中全量扫描缓存 songs根目录={根目录} 歌曲数={命中歌曲数}",
                )
            except Exception:
                pass
            return 缓存命中
        if not _目录含候选谱面文件(根目录, 最大命中数=1):
            try:
                _记录信息日志(
                    _日志器,
                    f"命中空扫描缓存且目录无谱面 songs根目录={根目录}",
                )
            except Exception:
                pass
            return 缓存命中
        try:
            _记录警告日志(
                _日志器,
                f"命中空扫描缓存但目录存在谱面，已忽略缓存并重新扫描 songs根目录={根目录}",
            )
        except Exception:
            pass

    缓存命中 = _按前缀读取歌曲扫描缓存(("all", 根目录))
    if 缓存命中 is not None:
        命中歌曲数 = _统计数据树歌曲总数(缓存命中)
        if 命中歌曲数 > 0:
            try:
                _记录信息日志(
                    _日志器,
                    (
                        "命中全量前缀缓存 "
                        f"songs根目录={根目录} 歌曲数={命中歌曲数}"
                    ),
                )
            except Exception:
                pass
            return 缓存命中
        if not _目录含候选谱面文件(根目录, 最大命中数=1):
            try:
                _记录信息日志(
                    _日志器,
                    f"命中全量前缀空缓存且目录无谱面 songs根目录={根目录}",
                )
            except Exception:
                pass
            return 缓存命中
        try:
            _记录警告日志(
                _日志器,
                (
                    "命中全量前缀空缓存但目录存在谱面，已忽略缓存并重新扫描 "
                    f"songs根目录={根目录}"
                ),
            )
        except Exception:
            pass

    临时收集: Dict[Tuple[str, str], List[歌曲信息]] = {}

    for sm路径 in _收集候选谱面文件(根目录):
        相对 = os.path.relpath(sm路径, 根目录)
        parts = 相对.split(os.sep)
        if len(parts) < 4:
            continue

        类型名 = parts[0]
        模式名 = parts[1]
        try:
            歌曲列表 = 解析歌曲元数据列表(sm路径, 类型名, 模式名)
        except Exception as 异常:
            _记录异常日志(
                _日志器,
                f"解析歌曲元数据失败，已跳过文件 sm路径={sm路径}",
                异常,
            )
            continue
        if not 歌曲列表:
            continue

        键 = (类型名, 模式名)
        if 键 not in 临时收集:
            临时收集[键] = []

        临时收集[键].extend(歌曲列表)

    def _排序键(歌: 歌曲信息):
        try:
            星 = int(getattr(歌, "星级", 0) or 0)
        except Exception:
            星 = 0
        名 = str(getattr(歌, "歌名", "") or "").strip().lower()
        夹 = str(getattr(歌, "歌曲文件夹", "") or "").strip().lower()
        smn = (
            str(os.path.basename(str(getattr(歌, "sm路径", "") or ""))).strip().lower()
        )
        return (星, 名, 夹, smn)

    for (类型名, 模式名), 列表 in 临时收集.items():
        # ✅ 你要求：默认按星级从少到多
        列表.sort(key=_排序键)

        # ✅ 内部序号从 0 开始（与显示顺序一致）
        for i, 歌 in enumerate(列表, start=0):
            歌.序号 = i

        if 类型名 not in 结果:
            结果[类型名] = {}
        结果[类型名][模式名] = 列表

    扫描歌曲数 = _统计数据树歌曲总数(结果)
    存在候选谱面 = _目录含候选谱面文件(根目录, 最大命中数=1)
    if 扫描歌曲数 > 0 or (not 存在候选谱面):
        _写入歌曲扫描缓存(缓存键, 结果)
    else:
        try:
            _记录警告日志(
                _日志器,
                (
                    "全量扫描结果为空但目录存在谱面，跳过写入空缓存以避免后续误命中 "
                    f"songs根目录={根目录}"
                ),
            )
        except Exception:
            pass

    try:
        _记录信息日志(
            _日志器,
            f"完成全量扫描songs目录 根目录={根目录} 歌曲数={扫描歌曲数}",
        )
    except Exception:
        pass
    return 结果

@_串行化歌曲扫描
def 扫描songs_指定路径(
    songs根目录: str, 类型名: str, 模式名: str
) -> Dict[str, Dict[str, List[歌曲信息]]]:
    结果: Dict[str, Dict[str, List[歌曲信息]]] = {}
    根目录 = os.path.abspath(str(songs根目录 or "").strip())
    if not os.path.isdir(根目录):
        return 结果

    def _归一(s: str) -> str:
        return re.sub(r"\s+", "", str(s or "")).strip().lower()

    目标类型 = 类型名.strip()
    目标模式 = 模式名.strip()

    类型目录 = os.path.join(根目录, 目标类型)
    if not os.path.isdir(类型目录):
        try:
            for 名 in os.listdir(根目录):
                if os.path.isdir(os.path.join(根目录, 名)) and _归一(名) == _归一(
                    目标类型
                ):
                    目标类型 = 名
                    类型目录 = os.path.join(根目录, 目标类型)
                    break
        except Exception:
            return 结果

    if not os.path.isdir(类型目录):
        return 结果

    模式目录 = os.path.join(类型目录, 目标模式)
    if not os.path.isdir(模式目录):
        try:
            for 名 in os.listdir(类型目录):
                if os.path.isdir(os.path.join(类型目录, 名)) and _归一(名) == _归一(
                    目标模式
                ):
                    目标模式 = 名
                    模式目录 = os.path.join(类型目录, 目标模式)
                    break
        except Exception:
            return 结果

    if not os.path.isdir(模式目录):
        return 结果

    try:
        _记录信息日志(
            _日志器,
            (
                "开始指定路径扫描 "
                f"渲染后端={str(os.environ.get('E5CM_RENDER_BACKEND', '') or '-')} "
                f"根目录={根目录} 类型={目标类型} 模式={目标模式}"
            ),
        )
    except Exception:
        pass

    缓存键 = _构建指定扫描缓存键(
        songs根目录=根目录,
        类型目录=类型目录,
        模式目录=模式目录,
        类型名=目标类型,
        模式名=目标模式,
    )
    缓存命中 = _读取歌曲扫描缓存(缓存键)
    if 缓存命中 is not None:
        命中歌曲数 = _统计数据树歌曲总数(缓存命中)
        if 命中歌曲数 > 0:
            try:
                _记录信息日志(
                    _日志器,
                    (
                        "命中指定扫描缓存 "
                        f"类型={目标类型} 模式={目标模式} 歌曲数={命中歌曲数}"
                    ),
                )
            except Exception:
                pass
            return 缓存命中
        if not _目录含候选谱面文件(模式目录, 最大命中数=1):
            return 缓存命中
        try:
            _记录警告日志(
                _日志器,
                (
                    "命中指定扫描空缓存但目录存在谱面，已忽略缓存并重新扫描 "
                    f"类型={目标类型} 模式={目标模式}"
                ),
            )
        except Exception:
            pass

    缓存命中 = _按前缀读取歌曲扫描缓存(
        ("specified", 根目录, _归一化目录名(目标类型), _归一化目录名(目标模式))
    )
    if 缓存命中 is not None:
        命中歌曲数 = _统计数据树歌曲总数(缓存命中)
        if 命中歌曲数 > 0:
            try:
                _记录信息日志(
                    _日志器,
                    (
                        "命中指定前缀缓存 "
                        f"类型={目标类型} 模式={目标模式} 歌曲数={命中歌曲数}"
                    ),
                )
            except Exception:
                pass
            return 缓存命中
        if not _目录含候选谱面文件(模式目录, 最大命中数=1):
            return 缓存命中
        try:
            _记录警告日志(
                _日志器,
                (
                    "命中指定前缀空缓存但目录存在谱面，已忽略缓存并重新扫描 "
                    f"类型={目标类型} 模式={目标模式}"
                ),
            )
        except Exception:
            pass

    收集: List[歌曲信息] = []

    for sm路径 in _收集候选谱面文件(模式目录):
        try:
            相对 = os.path.relpath(sm路径, 根目录)
            parts = 相对.split(os.sep)
        except Exception:
            continue

        if len(parts) < 4:
            continue

        类型名_实际 = parts[0]
        模式名_实际 = parts[1]
        try:
            歌曲列表 = 解析歌曲元数据列表(sm路径, 类型名_实际, 模式名_实际)
        except Exception as 异常:
            _记录异常日志(
                _日志器,
                f"解析歌曲元数据失败（指定路径扫描），已跳过文件 sm路径={sm路径}",
                异常,
            )
            continue
        if 歌曲列表:
            收集.extend(歌曲列表)

    def _排序键(歌: 歌曲信息):
        try:
            星 = int(getattr(歌, "星级", 0) or 0)
        except Exception:
            星 = 0
        名 = str(getattr(歌, "歌名", "") or "").strip().lower()
        夹 = str(getattr(歌, "歌曲文件夹", "") or "").strip().lower()
        smn = (
            str(os.path.basename(str(getattr(歌, "sm路径", "") or ""))).strip().lower()
        )
        return (星, 名, 夹, smn)

    收集.sort(key=_排序键)
    for i, 歌 in enumerate(收集, start=0):
        歌.序号 = i

    if 收集:
        结果[收集[0].类型] = {收集[0].模式: 收集}
    else:
        结果 = {}

    扫描歌曲数 = _统计数据树歌曲总数(结果)
    存在候选谱面 = _目录含候选谱面文件(模式目录, 最大命中数=1)
    if 扫描歌曲数 > 0 or (not 存在候选谱面):
        _写入歌曲扫描缓存(缓存键, 结果)
    else:
        try:
            _记录警告日志(
                _日志器,
                (
                    "指定扫描结果为空但目录存在谱面，跳过写入空缓存以避免后续误命中 "
                    f"类型={目标类型} 模式={目标模式} 模式目录={模式目录}"
                ),
            )
        except Exception:
            pass

    try:
        _记录信息日志(
            _日志器,
            (
                "完成指定路径扫描 "
                f"根目录={根目录} 类型={目标类型} 模式={目标模式} 歌曲数={扫描歌曲数}"
            ),
        )
    except Exception:
        pass
    return 结果

class 图像缓存(_本地图片缓存):
    def __init__(self, 缓存目录: str = ""):
        super().__init__(
            缓存目录=缓存目录 or _公共取选歌封面缓存目录(),
            名称空间="select_scene_cover_cache",
            内存上限=640,
        )

def 生成圆角蒙版(宽: int, 高: int, 圆角: int) -> pygame.Surface:
    蒙版 = pygame.Surface((宽, 高), pygame.SRCALPHA)
    蒙版.fill((0, 0, 0, 0))
    pygame.draw.rect(
        蒙版, (255, 255, 255, 255), pygame.Rect(0, 0, 宽, 高), border_radius=圆角
    )
    return 蒙版

def 载入并缩放封面(
    路径: str, 目标宽: int, 目标高: int, 圆角: int, 模式: str
) -> Optional[pygame.Surface]:
    """
    模式:
      - cover   : 等比铺满，超出裁切
      - contain : 等比完整显示，留透明边
      - stretch : 直接拉伸铺满
    """
    try:
        原图 = pygame.image.load(路径).convert_alpha()
    except Exception:
        return None

    try:
        目标宽 = max(1, int(目标宽))
        目标高 = max(1, int(目标高))
    except Exception:
        return None

    try:
        ow, oh = 原图.get_size()
    except Exception:
        return None

    if ow <= 0 or oh <= 0:
        return None

    模式 = str(模式 or "cover").strip().lower()
    if 模式 not in ("cover", "contain", "stretch"):
        模式 = "cover"

    try:
        if 模式 == "stretch":
            结果图 = pygame.transform.smoothscale(原图, (目标宽, 目标高)).convert_alpha()
            if 圆角 > 0:
                蒙版 = 生成圆角蒙版(目标宽, 目标高, 圆角)
                结果图.blit(蒙版, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            return 结果图

        if 模式 == "contain":
            比例 = min(目标宽 / ow, 目标高 / oh)
            新宽 = max(1, int(round(ow * 比例)))
            新高 = max(1, int(round(oh * 比例)))
            缩放图 = pygame.transform.smoothscale(原图, (新宽, 新高)).convert_alpha()

            结果图 = pygame.Surface((目标宽, 目标高), pygame.SRCALPHA)
            结果图.fill((0, 0, 0, 0))
            x = (目标宽 - 新宽) // 2
            y = (目标高 - 新高) // 2
            结果图.blit(缩放图, (x, y))

            if 圆角 > 0:
                蒙版 = 生成圆角蒙版(目标宽, 目标高, 圆角)
                结果图.blit(蒙版, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            return 结果图

        比例 = max(目标宽 / ow, 目标高 / oh)
        新宽 = max(1, int(round(ow * 比例)))
        新高 = max(1, int(round(oh * 比例)))
        缩放图 = pygame.transform.smoothscale(原图, (新宽, 新高)).convert_alpha()

        x = (新宽 - 目标宽) // 2
        y = (新高 - 目标高) // 2

        结果图 = pygame.Surface((目标宽, 目标高), pygame.SRCALPHA)
        结果图.fill((0, 0, 0, 0))
        结果图.blit(缩放图, (0, 0), area=pygame.Rect(x, y, 目标宽, 目标高))

        if 圆角 > 0:
            蒙版 = 生成圆角蒙版(目标宽, 目标高, 圆角)
            结果图.blit(蒙版, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        return 结果图
    except Exception:
        return None

def 计算框体槽位布局(框体矩形: pygame.Rect, 是否大图: bool) -> dict:
    if bool(是否大图):
        return _计算框体槽位布局模块(
            框体矩形,
            True,
            slot_params=dict(_大图槽位参数),
        )
    return _计算框体槽位布局模块(
        框体矩形,
        False,
        slot_params=dict(_缩略图槽位参数),
        small_visible_bottom_px=float(_缩略图可视底设计像素),
        small_frame_design_height=float(_缩略图框体设计高),
        small_info_anchor=str(_缩略图信息条锚点),
    )

def 计算缩略图小框矩形(
    基准矩形: pygame.Rect,
    框路径: str,
) -> pygame.Rect:
    return _计算缩略图小框矩形模块(
        base_rect=基准矩形,
        frame_path=框路径,
        get_ui_image=获取UI原图,
        frame_scale_x=_缩略图小框_宽缩放,
        frame_scale_y=_缩略图小框_高缩放,
        frame_x_offset=_缩略图小框_x偏移,
        frame_y_offset_ratio=_缩略图小框_y偏移,
        target_ratio=4.0 / 3.0,
    )


def 计算缩略图卡片布局(
    基准矩形: pygame.Rect,
    框路径: str,
) -> dict:
    return _计算缩略图卡片布局模块(
        base_rect=基准矩形,
        frame_path=框路径,
        get_ui_image=获取UI原图,
        frame_scale_x=_缩略图小框_宽缩放,
        frame_scale_y=_缩略图小框_高缩放,
        frame_x_offset=_缩略图小框_x偏移,
        frame_y_offset_ratio=_缩略图小框_y偏移,
        target_ratio=4.0 / 3.0,
        slot_params=dict(_缩略图槽位参数),
        small_visible_bottom_px=float(_缩略图可视底设计像素),
        small_frame_design_height=float(_缩略图框体设计高),
        small_info_anchor=str(_缩略图信息条锚点),
    )

class 渐隐放大点击特效:
    """
    0.5s 渐隐放大（alpha: 0->255），scale: 0.92 -> 1.06 -> 1.00
    兼容 _启动过渡() 的接口：
      - 触发()
      - 是否动画中()
      - 绘制按钮(屏幕, 原图, 基准矩形)
    """

    def __init__(self, 总时长: float = 0.5):
        self.总时长 = float(总时长)
        self._开始时间 = 0.0
        self._动画中 = False

    def 触发(self):
        self._开始时间 = time.time()
        self._动画中 = True

    def 是否动画中(self) -> bool:
        if not self._动画中:
            return False
        if (time.time() - self._开始时间) >= max(0.001, self.总时长):
            self._动画中 = False
            return False
        return True

    def _夹紧(self, x: float, a: float, b: float) -> float:
        return a if x < a else (b if x > b else x)

    def _缓出(self, t: float) -> float:
        # easeOutQuad
        t = self._夹紧(t, 0.0, 1.0)
        return 1.0 - (1.0 - t) * (1.0 - t)

    def 绘制按钮(
        self, 屏幕: pygame.Surface, 原图: pygame.Surface, 基准矩形: pygame.Rect
    ):
        if 原图 is None:
            return

        现在 = time.time()
        t = (现在 - self._开始时间) / max(0.001, self.总时长)
        t = self._夹紧(t, 0.0, 1.0)

        # scale：0.92 -> 1.06 -> 1.00
        if t < 0.6:
            k1 = t / 0.6
            scale = 0.92 + (1.06 - 0.92) * self._缓出(k1)
        else:
            k2 = (t - 0.6) / 0.4
            scale = 1.06 + (1.00 - 1.06) * self._缓出(k2)

        # alpha：0 -> 255
        alpha = int(255 * self._缓出(t))
        alpha = max(0, min(255, alpha))

        ww = max(1, int(基准矩形.w * scale))
        hh = max(1, int(基准矩形.h * scale))
        x = 基准矩形.centerx - ww // 2
        y = 基准矩形.centery - hh // 2

        try:
            图 = pygame.transform.smoothscale(原图, (ww, hh)).convert_alpha()
            图.set_alpha(alpha)
            屏幕.blit(图, (x, y))
        except Exception:
            # 兜底：不让异常打断主循环
            pass

class 按钮:
    def __init__(self, 名称: str, 矩形: pygame.Rect):
        self.名称 = 名称
        self.矩形 = 矩形
        self.悬停 = False
        self.按下 = False

        # === 按钮背景图：统一皮肤 ===
        self._背景图_原图: Optional[pygame.Surface] = None
        self._背景图_缓存: Optional[pygame.Surface] = None
        self._背景图_缓存尺寸: Tuple[int, int] = (0, 0)

        self._加载按钮背景图()

    def _加载按钮背景图(self):
        try:
            路径 = _资源路径("UI-img", "选歌界面资源", "默认按钮背景.png")
            if os.path.isfile(路径):
                self._背景图_原图 = pygame.image.load(路径).convert_alpha()
            else:
                self._背景图_原图 = None
        except Exception:
            self._背景图_原图 = None

        self._背景图_缓存 = None
        self._背景图_缓存尺寸 = (0, 0)

    def _获取缩放背景图(self) -> Optional[pygame.Surface]:
        if self._背景图_原图 is None:
            return None

        目标尺寸 = (max(1, int(self.矩形.w)), max(1, int(self.矩形.h)))
        if self._背景图_缓存 is None or self._背景图_缓存尺寸 != 目标尺寸:
            try:
                self._背景图_缓存 = pygame.transform.smoothscale(
                    self._背景图_原图, 目标尺寸
                )
                self._背景图_缓存尺寸 = 目标尺寸
            except Exception:
                self._背景图_缓存 = None
                self._背景图_缓存尺寸 = (0, 0)

        return self._背景图_缓存

    def 处理事件(self, 事件) -> bool:
        if 事件.type == pygame.MOUSEMOTION:
            self.悬停 = self.矩形.collidepoint(事件.pos)

        elif 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            if self.矩形.collidepoint(事件.pos):
                self.按下 = True

        elif 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            命中 = self.矩形.collidepoint(事件.pos)
            触发 = self.按下 and 命中
            self.按下 = False
            return 触发

        return False

    def 绘制(self, 屏幕: pygame.Surface, 字体: pygame.font.Font):
        圆角 = 18  # 仅用于回退绘制（不画边框）

        # 1) 背景（图片优先，失败回退纯色）
        背景图 = self._获取缩放背景图()
        if 背景图 is not None:
            屏幕.blit(背景图, self.矩形.topleft)

            # 状态反馈（不画边框）：悬停/按下加透明叠层
            if self.悬停 or self.按下:
                叠层 = pygame.Surface((self.矩形.w, self.矩形.h), pygame.SRCALPHA)
                if self.按下:
                    叠层.fill((0, 0, 0, 85))
                else:
                    叠层.fill((255, 255, 255, 18))
                屏幕.blit(叠层, self.矩形.topleft)
        else:
            # 回退：纯色底（不画边框）
            背景色 = (55, 120, 210)
            if self.悬停:
                背景色 = (70, 140, 240)
            if self.按下:
                背景色 = (35, 95, 180)
            绘制圆角矩形(屏幕, self.矩形, 背景色, 圆角=圆角)

        # 2) 文本：字体保留，颜色强制白色
        绘制文本(
            屏幕,
            self.名称,
            字体,
            (255, 255, 255),
            self.矩形.center,
            对齐="center",
        )

class 星级筛选按钮:
    """
    ✅ 星级筛选专用按钮（新样式）：
    - 只显示：数字 + 单颗星图标
    - 圆角卡片
    - 点击：触发过渡后立即应用筛选并关闭面板
    """

    def __init__(self, 宿主: "选歌游戏", 星级: int, 矩形: pygame.Rect):
        self.宿主 = 宿主
        self.星级 = int(星级)
        self.矩形 = 矩形

        self.悬停 = False
        self.按下 = False

    def 处理事件(self, 事件) -> bool:
        if 事件.type == pygame.MOUSEMOTION:
            self.悬停 = self.矩形.collidepoint(事件.pos)
            return False

        if 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            if self.矩形.collidepoint(事件.pos):
                self.按下 = True
            return False

        if 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            命中 = self.矩形.collidepoint(事件.pos)
            触发 = bool(self.按下 and 命中)
            self.按下 = False
            if 触发:
                self._触发选择()
            return False

        return False

    def _触发选择(self):
        if self.宿主 is None:
            return

        # 1) 先对“当前屏幕上的按钮区域截图”做 0.5s 渐隐放大
        try:
            特效 = getattr(self.宿主, "_特效_星级筛选", None)
            if 特效 is None:
                特效 = getattr(self.宿主, "_特效_按钮", None)
            self.宿主._启动过渡(特效, self.矩形, lambda: None)
        except Exception:
            pass

        # 2) 立刻应用筛选并关闭面板
        try:
            self.宿主.设置星级筛选(self.星级)
            self.宿主.关闭星级筛选页()
        except Exception:
            pass

    def _获取单星图(self, 目标高: int) -> Optional[pygame.Surface]:
        目标高 = max(8, int(目标高))
        try:
            缓存 = getattr(self.宿主, "_星级筛选_单星缓存", None)
            if not isinstance(缓存, dict):
                缓存 = {}
                setattr(self.宿主, "_星级筛选_单星缓存", 缓存)
        except Exception:
            缓存 = {}

        if 目标高 in 缓存:
            return 缓存.get(目标高)

        星星路径 = _资源路径("UI-img", "选歌界面资源", "小星星", "小星星.png")
        星原图 = 获取UI原图(星星路径, 透明=True)
        if 星原图 is None:
            缓存[目标高] = None
            return None

        星图 = _按高等比缩放(星原图, 目标高)
        缓存[目标高] = 星图
        return 星图

    def 绘制(self, 屏幕: pygame.Surface, _字体: pygame.font.Font):
        r = self.矩形

        # 背景（圆角）
        圆角 = max(14, int(min(r.w, r.h) * 0.18))
        if self.按下:
            背景色 = (10, 18, 30, 230)
        elif self.悬停:
            背景色 = (25, 45, 75, 235)
        else:
            背景色 = (18, 32, 55, 225)

        底 = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        底.fill((0, 0, 0, 0))
        pygame.draw.rect(底, 背景色, pygame.Rect(0, 0, r.w, r.h), border_radius=圆角)

        # 细边框（更像菜单按钮）
        边框色 = (180, 220, 255, 160) if not self.按下 else (255, 220, 120, 200)
        pygame.draw.rect(
            底, 边框色, pygame.Rect(0, 0, r.w, r.h), width=2, border_radius=圆角
        )

        屏幕.blit(底, r.topleft)

        # 内容：数字 + 单星（整体居中）
        数字字号 = max(24, int(r.h * 0.52))
        数字字体 = 获取字体(数字字号, 是否粗体=True)

        数字串 = str(self.星级)
        数字白 = 数字字体.render(数字串, True, (255, 255, 255))
        数字黑 = 数字字体.render(数字串, True, (0, 0, 0))

        星高 = max(12, int(r.h * 0.26))
        星图 = self._获取单星图(星高)

        间距 = max(6, int(r.w * 0.04))
        组宽 = 数字白.get_width()

        if 星图 is not None:
            组宽 = 组宽 + 间距 + 星图.get_width()

        起点x = r.centerx - 组宽 // 2
        中心y = r.centery

        # 数字（带阴影）
        数字r = 数字白.get_rect()
        数字r.midleft = (起点x, 中心y)
        屏幕.blit(数字黑, (数字r.x + 2, 数字r.y + 2))
        屏幕.blit(数字白, 数字r.topleft)

        # 星
        if 星图 is not None:
            星r = 星图.get_rect()
            星r.midleft = (数字r.right + 间距, 中心y)
            屏幕.blit(星图, 星r.topleft)
        else:
            # 兜底：没星图就画一个小五角星（非常简化）
            try:
                cx = 数字r.right + 间距 + int(星高 * 0.6)
                cy = 中心y
                半径 = int(星高 * 0.55)
                点 = []
                for i in range(10):
                    角 = math.pi / 2 + i * math.pi / 5
                    rr2 = 半径 if i % 2 == 0 else int(半径 * 0.45)
                    点.append(
                        (cx + int(math.cos(角) * rr2), cy - int(math.sin(角) * rr2))
                    )
                pygame.draw.polygon(屏幕, (255, 210, 80), 点)
            except Exception:
                pass

class 图片按钮:
    def __init__(
        self,
        图片路径: str,
        矩形: pygame.Rect,
        是否水平翻转: bool = False,
        是否垂直翻转: bool = False,
        透明度: int = 255,
    ):
        self.图片路径 = str(图片路径 or "")
        self.矩形 = 矩形
        self.是否水平翻转 = bool(是否水平翻转)
        self.是否垂直翻转 = bool(是否垂直翻转)
        try:
            self.透明度 = max(0, min(255, int(透明度)))
        except Exception:
            self.透明度 = 255

        self.悬停 = False
        self.按下 = False

        self._原图: Optional[pygame.Surface] = None
        self._缓存图: Optional[pygame.Surface] = None
        # ✅ 缓存键包含翻转状态
        self._缓存键: Tuple[int, int, bool, bool, int] = (0, 0, False, False, 255)

        self._加载原图()

    def _加载原图(self):
        try:
            图 = 安全加载图片(self.图片路径, 透明=True)
            self._原图 = 图
        except Exception:
            self._原图 = None

        self._缓存图 = None
        self._缓存键 = (0, 0, False, False, 255)

    def _获取缩放图(self) -> Optional[pygame.Surface]:
        if self._原图 is None:
            return None

        目标宽 = max(1, int(self.矩形.w))
        目标高 = max(1, int(self.矩形.h))
        键 = (
            目标宽,
            目标高,
            bool(self.是否水平翻转),
            bool(self.是否垂直翻转),
            int(self.透明度),
        )

        if self._缓存图 is not None and self._缓存键 == 键:
            return self._缓存图

        try:
            图 = self._原图
            # ✅ 先翻转（基于原图），再缩放（更清晰，方向也不会错）
            if self.是否水平翻转 or self.是否垂直翻转:
                图 = pygame.transform.flip(图, self.是否水平翻转, self.是否垂直翻转)

            缩放图 = pygame.transform.smoothscale(图, (目标宽, 目标高)).convert_alpha()
            if int(self.透明度) < 255:
                缩放图 = 缩放图.copy()
                缩放图.set_alpha(int(self.透明度))
        except Exception:
            缩放图 = None

        self._缓存图 = 缩放图
        self._缓存键 = 键
        return 缩放图

    def 处理事件(self, 事件) -> bool:
        if 事件.type == pygame.MOUSEMOTION:
            self.悬停 = self.矩形.collidepoint(事件.pos)

        elif 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            if self.矩形.collidepoint(事件.pos):
                self.按下 = True

        elif 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            命中 = self.矩形.collidepoint(事件.pos)
            触发 = self.按下 and 命中
            self.按下 = False
            return 触发

        return False

    def 绘制(self, 屏幕: pygame.Surface, *_忽略参数, **_忽略关键字):
        图 = self._获取缩放图()
        if 图 is not None:
            屏幕.blit(图, self.矩形.topleft)
        else:
            pygame.draw.rect(屏幕, (40, 80, 160), self.矩形, border_radius=14)

        if self.悬停 or self.按下:
            叠层 = pygame.Surface((self.矩形.w, self.矩形.h), pygame.SRCALPHA)
            叠层.fill((0, 0, 0, 85) if self.按下 else (255, 255, 255, 18))
            屏幕.blit(叠层, self.矩形.topleft)

class 底部图文按钮:
    def __init__(
        self,
        图片路径: str,
        矩形: pygame.Rect,
        底部文字: str,
        是否处理透明像素: bool = False,
    ):
        self.图片路径 = str(图片路径 or "")
        self.矩形 = 矩形
        self.底部文字 = str(底部文字 or "")
        self.是否处理透明像素 = bool(是否处理透明像素)

        # ✅ 新增：文字y偏移（负数=往上覆盖到图标上）
        self.文字y偏移 = 0

        self.悬停 = False
        self.按下 = False

        self._原图: Optional[pygame.Surface] = None
        self._缓存图: Optional[pygame.Surface] = None
        self._缓存尺寸: Tuple[int, int] = (0, 0)

        self._加载原图()

    def _加载原图(self):
        try:
            图 = 安全加载图片(self.图片路径, 透明=True)
            if 图 is None:
                self._原图 = None
                return

            # ✅ 你现在要求：不要去除透明像素
            # 这里保留能力，但只在你显式传 True 时才做（默认你会改成 False）
            if self.是否处理透明像素:
                图 = 处理透明像素_用左上角作为背景(图)

            self._原图 = 图
        except Exception:
            self._原图 = None

        self._缓存图 = None
        self._缓存尺寸 = (0, 0)

    def _获取缩放图_按区域contain(
        self, 区域w: int, 区域h: int, 放大倍率: float = 1.0
    ) -> Optional[pygame.Surface]:
        if self._原图 is None:
            return None

        区域w = max(1, int(区域w))
        区域h = max(1, int(区域h))

        try:
            放大倍率 = float(放大倍率)
        except Exception:
            放大倍率 = 1.0
        放大倍率 = max(0.50, min(2.00, 放大倍率))

        缓存键 = (区域w, 区域h, int(放大倍率 * 1000))
        if self._缓存图 is not None and self._缓存尺寸 == 缓存键:
            return self._缓存图

        try:
            ow, oh = self._原图.get_size()
            if ow <= 0 or oh <= 0:
                self._缓存图 = None
                self._缓存尺寸 = 缓存键
                return None

            # 先按 contain 放进区域
            比例 = min(区域w / ow, 区域h / oh)
            nw = max(1, int(ow * 比例))
            nh = max(1, int(oh * 比例))

            # 再“可控放大”，但绝不超过区域
            可再放大 = min(区域w / max(1, nw), 区域h / max(1, nh))
            最终放大 = min(放大倍率, 可再放大)
            nw2 = max(1, int(nw * 最终放大))
            nh2 = max(1, int(nh * 最终放大))

            缩放图 = pygame.transform.smoothscale(
                self._原图, (nw2, nh2)
            ).convert_alpha()
        except Exception:
            缩放图 = None

        self._缓存图 = 缩放图
        self._缓存尺寸 = 缓存键
        return 缩放图

    def 处理事件(self, 事件) -> bool:
        if 事件.type == pygame.MOUSEMOTION:
            self.悬停 = self.矩形.collidepoint(事件.pos)

        elif 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            if self.矩形.collidepoint(事件.pos):
                self.按下 = True

        elif 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            命中 = self.矩形.collidepoint(事件.pos)
            触发 = self.按下 and 命中
            self.按下 = False
            return 触发

        return False

    def 绘制(self, 屏幕: pygame.Surface, 字体: pygame.font.Font):
        总矩形 = self.矩形

        # ✅ 图标区：永远用“宽度”做正方形
        图标边长 = max(1, int(总矩形.w))
        图标区 = pygame.Rect(总矩形.x, 总矩形.y, 总矩形.w, 图标边长)

        # 1) 画图标（尽量填满）
        try:
            图 = self._获取缩放图_按区域contain(图标区.w, 图标区.h, 放大倍率=1.22)
        except TypeError:
            图 = self._获取缩放图_按区域contain(图标区.w, 图标区.h)

        if 图 is not None:
            gx = 图标区.centerx - 图.get_width() // 2
            gy = 图标区.centery - 图.get_height() // 2
            屏幕.blit(图, (gx, gy))
        else:
            pygame.draw.rect(屏幕, (40, 80, 160), 图标区, border_radius=14)

        # 2) 交互反馈（先盖一层，再画字）
        if self.悬停 or self.按下:
            叠层 = pygame.Surface((图标区.w, 图标区.h), pygame.SRCALPHA)
            叠层.fill((0, 0, 0, 85) if self.按下 else (255, 255, 255, 18))
            屏幕.blit(叠层, 图标区.topleft)

        # 3) ✅ 文字：覆盖在图标底部中间，并允许“往上挪”
        if self.底部文字:
            文本 = str(self.底部文字)

            try:
                白字 = 字体.render(文本, True, (255, 255, 255))
                黑影 = 字体.render(文本, True, (0, 0, 0))

                文高 = 白字.get_height()

                # ✅ 默认：往上覆盖一点点（负数=往上）
                默认上移 = -max(2, int(文高 * 0.25))

                # ✅ 手动偏移：你想再往上/往下，直接改 self.文字y偏移
                try:
                    手动偏移 = int(getattr(self, "文字y偏移", 0))
                except Exception:
                    手动偏移 = 0

                文矩形 = 白字.get_rect()
                文矩形.midbottom = (
                    图标区.centerx,
                    图标区.bottom + 默认上移 + 手动偏移,
                )

                # 防御：别掉出屏幕底部（否则你又说看不到）
                屏高 = int(屏幕.get_height())
                if 文矩形.bottom > 屏高 - 2:
                    文矩形.bottom = 屏高 - 2

                # 阴影 + 正文
                屏幕.blit(黑影, (文矩形.x + 2, 文矩形.y + 2))
                屏幕.blit(白字, 文矩形.topleft)
            except Exception:
                pass

class 歌曲卡片:
    def __init__(self, 歌曲: 歌曲信息, 矩形: pygame.Rect):
        self.歌曲 = 歌曲
        self.矩形 = 矩形
        self.悬停 = False
        self.踏板高亮 = False
        self.封面矩形 = pygame.Rect(0, 0, 1, 1)
        self._静态缓存键 = None
        self._静态缓存图: Optional[pygame.Surface] = None

    def 更新布局(self, 矩形: pygame.Rect):
        self.矩形 = 矩形
        self._静态缓存键 = None
        self._静态缓存图 = None

    def 处理事件(self, 事件):
        if 事件.type == pygame.MOUSEMOTION:
            self.悬停 = self.矩形.collidepoint(事件.pos)

    def 是否点击(self, 事件) -> bool:
        return (
            事件.type == pygame.MOUSEBUTTONDOWN
            and 事件.button == 1
            and self.矩形.collidepoint(事件.pos)
        )

    def 绘制(
        self,
        屏幕: pygame.Surface,
        小字体: pygame.font.Font,
        图缓存: "图像缓存",
        允许同步封面加载: bool = True,
    ):
        是否高亮 = bool(self.悬停 or self.踏板高亮)
        基准矩形 = self.矩形.copy()

        框路径 = _资源路径("UI-img", "选歌界面资源", "缩略图小.png")
        局部布局 = 计算缩略图卡片布局(基准矩形, 框路径)
        框矩形 = 局部布局["框矩形"]
        局部框矩形 = 局部布局["局部框矩形"]
        局部封面矩形 = 局部布局["封面矩形"]
        局部封面可视矩形 = 局部布局.get("封面可视矩形", 局部封面矩形)
        局部信息条 = 局部布局["信息条矩形"]
        局部星星区域 = 局部布局["星星区域"]
        局部游玩区域 = 局部布局["游玩区域"]
        局部bpm区域 = 局部布局["bpm区域"]

        self.封面矩形 = pygame.Rect(
            框矩形.x + 局部封面可视矩形.x,
            框矩形.y + 局部封面可视矩形.y,
            局部封面可视矩形.w,
            局部封面可视矩形.h,
        )

        try:
            游玩次数 = int(max(0, int(getattr(self.歌曲, "游玩次数", 0) or 0)))
        except Exception:
            游玩次数 = 0

        封面缩放模式 = "cover"
        封面圆角 = 0
        封面图 = None
        封面图已就绪 = False
        if self.歌曲.封面路径:
            封面图 = 图缓存.获取(
                self.歌曲.封面路径,
                局部封面矩形.w,
                局部封面矩形.h,
                int(封面圆角),
                封面缩放模式,
            )
            封面图已就绪 = isinstance(封面图, pygame.Surface)
            if (封面图 is None) and bool(允许同步封面加载):
                封面图 = 载入并缩放封面(
                    self.歌曲.封面路径,
                    局部封面矩形.w,
                    局部封面矩形.h,
                    int(封面圆角),
                    封面缩放模式,
                )
                if 封面图 is not None:
                    图缓存.写入(
                        self.歌曲.封面路径,
                        局部封面矩形.w,
                        局部封面矩形.h,
                        int(封面圆角),
                        封面缩放模式,
                        封面图,
                    )
                    封面图已就绪 = True

        缓存键 = _构建歌曲卡片缓存键(
            song=self.歌曲,
            frame_rect=框矩形,
            layout_version=float(_选歌布局_修改时间),
            cover_ready=bool(封面图已就绪),
            play_count=int(游玩次数),
        )
        局部画布 = self._静态缓存图 if self._静态缓存键 == 缓存键 else None
        if 局部画布 is None:
            局部画布 = _渲染歌曲卡片静态图(
                song=self.歌曲,
                frame_rect=框矩形,
                local_frame_rect=局部框矩形,
                local_cover_rect=局部封面矩形,
                local_cover_visible_rect=局部封面可视矩形,
                local_info_rect=局部信息条,
                local_star_rect=局部星星区域,
                local_play_rect=局部游玩区域,
                local_bpm_rect=局部bpm区域,
                cover_surface=封面图,
                play_count=int(游玩次数),
                frame_path=框路径,
                small_star_path=_资源路径("UI-img", "选歌界面资源", "小星星", "小星星.png"),
                vip_path=_资源路径("UI-img", "选歌界面资源", "vip.png"),
                hot_path=_资源路径("UI-img", "选歌界面资源", "热门.png"),
                new_path=_资源路径("UI-img", "选歌界面资源", "NEW绿色.png"),
                get_font=获取字体,
                render_compact_text=渲染紧凑文本,
                get_play_count_color=_取游玩次数颜色,
                get_ui_container_image=获取UI容器图,
                get_ui_image=获取UI原图,
                scale_to_height=_按高等比缩放,
                draw_star_row=绘制星星行_图片,
                draw_index_badge=绘制序号标签_图片,
                draw_mv_badge=绘制MV角标_文本,
                text_style=dict(_小图文字样式参数),
            )
            self._静态缓存键 = 缓存键
            self._静态缓存图 = 局部画布

        if 是否高亮:
            _绘制卡片悬停底层(
                屏幕,
                框矩形,
                pedal_highlight=bool(self.踏板高亮),
            )

        屏幕.blit(局部画布, 框矩形.topleft)
        if 是否高亮:
            _绘制卡片悬停叠层(
                屏幕,
                框矩形,
                pedal_highlight=bool(self.踏板高亮),
            )
        try:
            _绘制歌曲模式标记(
                屏幕,
                self.封面矩形,
                self.歌曲,
                是否大图=False,
                透明度=255,
            )
        except Exception:
            pass

class 选歌游戏:

    def __init__(
        self,
        songs根目录: str,
        背景音乐路径: str,
        指定类型名: str = "",
        指定模式名: str = "",
        玩家数: int = 1,
        是否继承已有窗口: Optional[bool] = None,
    ):
        _确保pygame基础模块已初始化()
        self.音频可用 = bool(_确保混音器已初始化())

        pygame.display.set_caption("e舞成名 选歌界面（Pygame）")

        self.上下文: dict = {}

        传入songs根目录 = (
            os.path.abspath(str(songs根目录 or "").strip())
            if str(songs根目录 or "").strip()
            else ""
        )
        if 传入songs根目录 and os.path.isdir(传入songs根目录):
            self.songs根目录 = 传入songs根目录
        else:
            self.songs根目录 = _取songs根目录()

        self.背景音乐路径 = 背景音乐路径
        self.玩家数 = 2 if 玩家数 == 2 else 1
        self.指定类型名 = str(指定类型名 or "").strip()
        self.指定模式名 = str(指定模式名 or "").strip()

        self._需要退出 = False
        self._返回状态 = "NORMAL"

        现有屏幕 = None
        try:
            if pygame.display.get_init():
                现有屏幕 = pygame.display.get_surface()
        except Exception:
            现有屏幕 = None

        if 是否继承已有窗口 is None:
            self._是否嵌入模式 = bool(现有屏幕 is not None)
        else:
            self._是否嵌入模式 = bool(是否继承已有窗口)

        if self._是否嵌入模式 and (现有屏幕 is not None):
            self.屏幕 = 现有屏幕
            self.宽, self.高 = self.屏幕.get_size()
        else:
            try:
                os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
            except Exception:
                pass

            信息 = pygame.display.Info()
            默认宽, 默认高 = self._计算默认窗口尺寸(信息)
            self.屏幕 = pygame.display.set_mode((默认宽, 默认高), pygame.RESIZABLE)
            self.宽, self.高 = self.屏幕.get_size()

        self._设计宽 = 2048
        self._设计高 = 1152

        self._top栏背景原图 = 安全加载图片(
            _资源路径("UI-img", "top栏", "top栏背景.png"), 透明=True
        )
        self._top_rect = pygame.Rect(0, 0, 1, 1)
        self._top图: Optional[pygame.Surface] = None
        self._top标题rect = pygame.Rect(0, 0, 1, 1)
        self._top标题图: Optional[pygame.Surface] = None
        self._top缓存尺寸 = (0, 0)

        self.标题字体 = 获取字体(40)
        self.标题粗体 = 获取字体(42)
        self.按钮字体 = 获取字体(30)
        self.按钮粗体 = 获取字体(32)
        self.正文字体 = 获取字体(24)
        self.正文字体粗 = 获取字体(26)
        self.小字体 = 获取字体(18)
        self.顶部高 = 78
        self.底部高 = 220
        self.当前页 = 0
        self.每页数量 = 8
        self.是否详情页 = False
        self.当前选择原始索引 = 0
        self.详情大框矩形 = pygame.Rect(0, 0, 0, 0)
        self.详情封面矩形 = pygame.Rect(0, 0, 0, 0)
        self.是否星级筛选页 = False
        self.当前筛选星级: Optional[int] = None
        self.星级按钮列表: List[Tuple[int, 按钮]] = []
        self.筛选页面板矩形 = pygame.Rect(0, 0, 0, 0)


        self.图缓存 = 图像缓存(_公共取选歌封面缓存目录())
        self.预加载队列 = deque()
        self._待清理保留key集合 = None
        self._页卡片缓存: Dict[Tuple[object, ...], List[歌曲卡片]] = {}
        self._页卡片缓存顺序: List[Tuple[object, ...]] = []
        self._页卡片缓存上限 = 10

        self.动画中 = False
        self.动画开始时间 = 0.0
        self.动画持续 = 0.35
        self.动画方向 = 0
        self.动画目标页 = 0
        self.动画旧页卡片 = []
        self.动画新页卡片 = []
        self.当前页卡片 = []
        self._踏板选中视图索引: Optional[int] = None

        self.按钮_歌曲分类 = 按钮("歌曲分类", pygame.Rect(0, 0, 0, 0))
        self.按钮_收藏夹 = 按钮("收藏夹", pygame.Rect(0, 0, 0, 0))
        self.按钮_ALL = 按钮("ALL", pygame.Rect(0, 0, 0, 0))
        self.按钮_2P加入 = 按钮("2P加入", pygame.Rect(0, 0, 0, 0))
        self.按钮_设置 = 按钮("设置", pygame.Rect(0, 0, 0, 0))
        self.按钮_重选模式 = 按钮("重选模式", pygame.Rect(0, 0, 0, 0))
        self.按钮_详情收藏 = 图片按钮("", pygame.Rect(0, 0, 1, 1))

        self.数据树 = {}
        if self.指定类型名 and self.指定模式名:
            try:
                self.数据树 = 扫描songs_指定路径(
                    self.songs根目录, self.指定类型名, self.指定模式名
                )
            except Exception as 异常:
                _记录异常日志(
                    _日志器,
                    (
                        "扫描songs_指定路径失败，已回退全量扫描 "
                        f"songs根目录={self.songs根目录} "
                        f"类型={self.指定类型名} 模式={self.指定模式名}"
                    ),
                    异常,
                )
                self.数据树 = {}

        if not self.数据树:
            try:
                self.数据树 = 扫描songs目录(self.songs根目录)
            except Exception as 异常:
                _记录异常日志(
                    _日志器,
                    f"扫描songs目录失败 songs根目录={self.songs根目录}",
                    异常,
                )
                self.数据树 = {}

        try:
            歌曲总数 = int(
                sum(
                    len(列表)
                    for 模式映射 in self.数据树.values()
                    if isinstance(模式映射, dict)
                    for 列表 in 模式映射.values()
                    if isinstance(列表, list)
                )
            )
            _记录信息日志(
                _日志器,
                (
                    "选歌扫描完成 "
                    f"songs根目录={self.songs根目录} "
                    f"类型数={len(self.数据树)} 歌曲数={歌曲总数} "
                    f"指定类型={self.指定类型名 or '-'} 指定模式={self.指定模式名 or '-'}"
                ),
            )
        except Exception:
            pass

        self._同步歌曲游玩记录()
        self._禁用NEW标记计算 = bool(_启用稳定NEW标记模式())
        if bool(self._禁用NEW标记计算):
            self._重置全部NEW标记()
            global _稳定NEW标记模式日志已输出
            if not bool(_稳定NEW标记模式日志已输出):
                try:
                    _记录信息日志(
                        _日志器,
                        "已启用稳定NEW标记模式：打包环境跳过NEW深度计算（全部按非NEW显示）",
                    )
                except Exception:
                    pass
                _稳定NEW标记模式日志已输出 = True
        else:
            self._同步全部NEW标记()
        self.是否收藏夹模式 = False
        self._全部歌曲缓存: Optional[List[歌曲信息]] = None
        self._收藏歌曲键集合: Set[str] = set()
        self._收藏夹修改序号 = 0
        self._收藏歌曲列表缓存版本 = -1
        self._收藏歌曲列表缓存: List[歌曲信息] = []
        self._加载收藏夹()

        self.类型列表 = sorted(self.数据树.keys())
        self.当前类型索引 = 0
        self.当前模式索引 = 0
        self.模式列表 = []

        匹配后的类型名 = _在现有名称中匹配(self.类型列表, self.指定类型名)
        if 匹配后的类型名:
            self.当前类型索引 = self.类型列表.index(匹配后的类型名)
            self.指定类型名 = 匹配后的类型名

        当前类型 = self.类型列表[self.当前类型索引] if self.类型列表 else ""
        self.模式列表 = sorted(self.数据树.get(当前类型, {}).keys())

        匹配后的模式名 = _在现有名称中匹配(self.模式列表, self.指定模式名)
        if 匹配后的模式名:
            self.当前模式索引 = self.模式列表.index(匹配后的模式名)
            self.指定模式名 = 匹配后的模式名
        else:
            self.当前模式索引 = 0

        self.背景图_原图 = None
        self.背景图_缩放缓存 = None
        self.背景图_缩放尺寸 = (0, 0)

        self._布局配置_缓存 = None
        self._布局配置_修改时间 = -1.0
        self._布局配置_最近检查时刻 = -999.0
        self._当前歌曲列表缓存键 = None
        self._当前歌曲列表缓存值: Tuple[List[歌曲信息], List[int]] = ([], [])
        self._背景暗层缓存: Optional[pygame.Surface] = None
        self._背景暗层缓存键: Tuple[int, int, int] = (0, 0, 0)
        self._背景遮罩alpha: int = 60
        self._背景遮罩设置最近读取时间: float = -999.0
        self._背景音乐路径存在缓存键 = ""
        self._背景音乐路径存在缓存值 = False
        self._详情浮层_alpha = 255
        self._详情浮层_最后缩放 = 1.0
        self._详情浮层面板缓存图: Optional[pygame.Surface] = None
        self._详情浮层面板缓存尺寸: Tuple[int, int] = (0, 0)
        self._详情浮层遮罩缓存图: Optional[pygame.Surface] = None
        self._详情浮层遮罩缓存键: Tuple[int, int, int] = (0, 0, 0)
        self._动态背景管理器 = DynamicBackgroundManager()
        self._动态背景上次刷新秒 = float(time.perf_counter())
        self._选歌场景强制CPU绘制 = True
        self._GPU背景纹理 = None
        self._GPU背景纹理键: Tuple[object, ...] = ()
        self._GPU背景遮罩纹理缓存: Dict[int, object] = {}
        self._GPU背景纹理渲染器id = 0
        self._GPU界面纹理缓存: Dict[Tuple[int, int, int, int], object] = {}
        self._GPU界面纹理渲染器id = 0
        self._GPU顶栏层缓存键 = None
        self._GPU顶栏层缓存图: Optional[pygame.Surface] = None
        self._GPU底栏层缓存键 = None
        self._GPU底栏层缓存图: Optional[pygame.Surface] = None
        self._GPU列表按钮层缓存键 = None
        self._GPU列表按钮层缓存图: Optional[pygame.Surface] = None
        self._GPU内容层缓存键 = None
        self._GPU内容层缓存图: Optional[pygame.Surface] = None
        self._GPU列表页缓存: Dict[Tuple[object, ...], pygame.Surface] = {}
        self._GPU列表页缓存顺序: List[Tuple[object, ...]] = []
        self._GPU列表页缓存上限 = 6
        self._GPU翻页旧页层图: Optional[pygame.Surface] = None
        self._GPU翻页新页层图: Optional[pygame.Surface] = None

        self._加载背景图()
        self._刷新背景遮罩设置(True)

        self.重算布局()
        self.确保播放背景音乐()
        self.安排预加载(基准页=self.当前页)

    def _布局配置文件路径(self) -> str:
        return _公共取布局配置路径("选歌布局.json", 根目录=_取项目根目录())

    def _加载布局配置(self, 是否提示: bool = False) -> dict:
        try:
            import json
        except Exception:
            return {}

        当前时刻 = float(time.perf_counter())
        if (
            getattr(self, "_布局配置_缓存", None) is not None
            and (当前时刻 - float(getattr(self, "_布局配置_最近检查时刻", -999.0) or -999.0))
            < 0.25
        ):
            return self._布局配置_缓存

        路径 = self._布局配置文件路径()
        try:
            修改时间 = os.path.getmtime(路径) if os.path.isfile(路径) else 0.0
        except Exception:
            修改时间 = 0.0
        self._布局配置_最近检查时刻 = 当前时刻

        if getattr(self, "_布局配置_缓存", None) is not None and float(
            getattr(self, "_布局配置_修改时间", 0.0) or 0.0
        ) == float(修改时间):
            return self._布局配置_缓存

        数据 = {}
        if os.path.isfile(路径):
            try:
                with open(路径, "r", encoding="utf-8") as 文件:
                    数据 = json.load(文件)
            except Exception:
                数据 = {}

        if not isinstance(数据, dict):
            数据 = {}

        self._布局配置_缓存 = 数据
        self._布局配置_修改时间 = float(修改时间)
        return 数据
    
    def _取底部布局像素(
        self, 键路径: str, 默认设计像素: int, 最小: int = None, 最大: int = None
    ) -> int:
        """
        底部按钮专用：
        - 如果 json 里写的是普通数字（如 164），按“设计稿像素”处理，再随窗口同比缩放
        - 如果 json 里写的是字符串单位（如 0.08w / 0.12h / 0.09min），直接走原有逻辑
        - 这样能兼容旧配置，又不会让底部按钮焊死
        """
        原值 = self._取布局值(键路径, 默认设计像素)

        try:
            设计宽 = float(getattr(self, "_设计宽", 2048) or 2048)
            设计高 = float(getattr(self, "_设计高", 1152) or 1152)
            当前宽 = float(getattr(self, "宽", 0) or 0)
            当前高 = float(getattr(self, "高", 0) or 0)
            缩放 = min(
                当前宽 / max(1.0, 设计宽),
                当前高 / max(1.0, 设计高),
            )
        except Exception:
            缩放 = 1.0

        缩放 = max(0.45, min(2.20, float(缩放)))

        if isinstance(原值, str):
            文本 = str(原值 or "").strip().lower()
            if 文本:
                try:
                    return self._取布局像素(键路径, 默认设计像素, 最小=最小, 最大=最大)
                except Exception:
                    pass

        try:
            值 = int(round(float(原值) * 缩放))
        except Exception:
            值 = int(round(float(默认设计像素) * 缩放))

        if 最小 is not None:
            值 = max(int(最小), 值)
        if 最大 is not None:
            值 = min(int(最大), 值)
        return 值
    
    def _取布局值(self, 键路径: str, 默认值):
        配置 = self._加载布局配置(是否提示=False)
        当前 = 配置
        for 片段 in str(键路径 or "").split("."):
            if not 片段:
                continue
            if not isinstance(当前, dict) or 片段 not in 当前:
                return 默认值
            当前 = 当前.get(片段)
        return 默认值 if 当前 is None else 当前

    def _取布局像素(
        self, 键路径: str, 默认像素: int, 最小: int = None, 最大: int = None
    ) -> int:
        原 = self._取布局值(键路径, 默认像素)

        def _解析成浮点(v) -> float:
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                s = v.strip().lower()
                m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(w|h|min)$", s)
                if m:
                    数 = float(m.group(1))
                    单位 = m.group(2)
                    if 单位 == "w":
                        基准 = float(getattr(self, "宽", 0) or 0)
                    elif 单位 == "h":
                        基准 = float(getattr(self, "高", 0) or 0)
                    else:
                        基准 = float(
                            min(
                                int(getattr(self, "宽", 0) or 0),
                                int(getattr(self, "高", 0) or 0),
                            )
                        )
                    return 数 * 基准
                return float(s)
            return float(默认像素)

        try:
            值 = int(round(_解析成浮点(原)))
        except Exception:
            值 = int(默认像素)

        if 最小 is not None:
            值 = max(int(最小), 值)
        if 最大 is not None:
            值 = min(int(最大), 值)
        return 值

    def _计算默认窗口尺寸(self, 信息: pygame.display.Info) -> Tuple[int, int]:
        """
        默认非满屏：按屏幕的 80% 开一个可视窗口，并限制上下界。
        """
        try:
            屏宽 = int(getattr(信息, "current_w", 1280) or 1280)
            屏高 = int(getattr(信息, "current_h", 720) or 720)
        except Exception:
            屏宽, 屏高 = 1280, 720

        默认宽 = int(屏宽 * 0.80)
        默认高 = int(屏高 * 0.80)

        默认宽 = max(1000, min(默认宽, 1500))
        默认高 = max(650, min(默认高, 950))

        # 防止超出屏幕
        默认宽 = min(默认宽, max(960, 屏宽))
        默认高 = min(默认高, max(600, 屏高))
        return 默认宽, 默认高

    def 当前类型名(self) -> str:
        if not self.类型列表:
            return "无类型"
        return self.类型列表[self.当前类型索引]

    def 当前模式名(self) -> str:
        if not self.模式列表:
            return "无模式"
        return self.模式列表[self.当前模式索引]

    def _失效歌曲视图缓存(self):
        self._当前歌曲列表缓存键 = None
        self._当前歌曲列表缓存值 = ([], [])
        self._清空页卡片缓存()
        self._失效GPU界面层缓存()

    def _清空页卡片缓存(self):
        self._页卡片缓存 = {}
        self._页卡片缓存顺序 = []
        self.动画旧页卡片 = []
        self.动画新页卡片 = []

    def _失效详情浮层缓存(self):
        self._详情浮层_alpha = 255
        self._详情浮层_最后缩放 = 1.0
        self.详情大框矩形 = pygame.Rect(0, 0, 0, 0)
        self.详情封面矩形 = pygame.Rect(0, 0, 0, 0)
        self._详情浮层面板缓存图 = None
        self._详情浮层面板缓存尺寸 = (0, 0)

    def _失效GPU界面层缓存(self):
        self._GPU顶栏层缓存图 = None
        self._GPU顶栏层缓存键 = None
        self._GPU底栏层缓存图 = None
        self._GPU底栏层缓存键 = None
        self._GPU列表按钮层缓存图 = None
        self._GPU列表按钮层缓存键 = None
        self._GPU内容层缓存图 = None
        self._GPU内容层缓存键 = None
        self._GPU翻页旧页层图 = None
        self._GPU翻页新页层图 = None
        for 图层 in list(getattr(self, "_GPU列表页缓存", {}).values()):
            self._清理GPU界面纹理(图层)
        self._GPU列表页缓存 = {}
        self._GPU列表页缓存顺序 = []

    def _取歌曲数据根目录(self) -> str:
        return os.path.abspath(
            os.path.dirname(self.songs根目录)
            if str(self.songs根目录 or "").strip()
            else _取运行根目录()
        )

    def _收藏夹文件路径(self) -> str:
        return _取运行存储路径()

    def _遍历全部歌曲(self) -> List[歌曲信息]:
        缓存 = getattr(self, "_全部歌曲缓存", None)
        if isinstance(缓存, list):
            return 缓存

        全部歌曲: List[歌曲信息] = []
        for 类型映射 in self.数据树.values():
            if not isinstance(类型映射, dict):
                continue
            for 列表 in 类型映射.values():
                if isinstance(列表, list):
                    全部歌曲.extend(列表)

        self._全部歌曲缓存 = 全部歌曲
        return 全部歌曲

    def _取歌曲收藏键(self, 歌: 歌曲信息) -> str:
        try:
            return 取歌曲记录键(
                _取歌曲记录路径源(歌), self._取歌曲数据根目录()
            )
        except Exception:
            return _取歌曲记录路径源(歌)

    def _同步歌曲收藏状态(self):
        收藏键集合 = set(getattr(self, "_收藏歌曲键集合", set()) or set())
        for 歌 in self._遍历全部歌曲():
            try:
                setattr(歌, "是否收藏", bool(self._取歌曲收藏键(歌) in 收藏键集合))
            except Exception:
                pass

    def _加载收藏夹(self):
        数据 = _读取存储作用域(_收藏夹存储作用域)
        if not isinstance(数据, dict):
            数据 = {}

        收藏列表 = []
        if isinstance(数据, dict):
            收藏列表 = 数据.get("收藏歌曲键列表", [])
        self._收藏歌曲键集合 = {
            str(键).strip() for 键 in list(收藏列表 or []) if str(键).strip()
        }
        self._收藏歌曲列表缓存版本 = -1
        self._收藏歌曲列表缓存 = []
        self._同步歌曲收藏状态()

    def _写入收藏夹数据(self) -> bool:
        try:
            载荷 = {
                "版本": 1,
                "收藏歌曲键列表": sorted(
                    str(键).strip()
                    for 键 in set(getattr(self, "_收藏歌曲键集合", set()) or set())
                    if str(键).strip()
                ),
            }
            _覆盖存储作用域(_收藏夹存储作用域, 载荷)
            return True
        except Exception:
            return False

    def _获取收藏歌曲列表(self) -> List[歌曲信息]:
        当前版本 = int(getattr(self, "_收藏夹修改序号", 0) or 0)
        if int(getattr(self, "_收藏歌曲列表缓存版本", -1) or -1) == 当前版本:
            return getattr(self, "_收藏歌曲列表缓存", []) or []

        列表 = [
            歌
            for 歌 in self._遍历全部歌曲()
            if bool(getattr(歌, "是否收藏", False))
        ]
        self._收藏歌曲列表缓存 = 列表
        self._收藏歌曲列表缓存版本 = 当前版本
        return 列表

    def _失效收藏夹缓存(self):
        self._收藏夹修改序号 = int(getattr(self, "_收藏夹修改序号", 0) or 0) + 1
        self._收藏歌曲列表缓存版本 = -1
        self._收藏歌曲列表缓存 = []
        self._失效歌曲视图缓存()
        self._失效详情浮层缓存()

    def _重置全部NEW标记(self):
        for 类型映射 in self.数据树.values():
            if not isinstance(类型映射, dict):
                continue
            for 列表 in 类型映射.values():
                if not isinstance(列表, list):
                    continue
                for 歌 in 列表:
                    try:
                        setattr(歌, "是否NEW", False)
                    except Exception:
                        pass

    def _同步全部NEW标记(self):
        if bool(getattr(self, "_禁用NEW标记计算", False)):
            self._NEW标记_缓存键 = ("__DISABLED__",)
            return
        for 类型映射 in self.数据树.values():
            if not isinstance(类型映射, dict):
                continue
            for 列表 in 类型映射.values():
                if not isinstance(列表, list) or not 列表:
                    continue
                try:
                    self._更新当前模式NEW标记(列表)
                except Exception:
                    pass

    def _刷新当前歌曲视图(
        self,
        *,
        保留歌曲键: str = "",
        强制返回列表: bool = False,
    ):
        原始 = self.当前原始歌曲列表()

        if 原始 and 保留歌曲键:
            for 索引, 歌 in enumerate(原始):
                if self._取歌曲收藏键(歌) == 保留歌曲键:
                    self.当前选择原始索引 = int(索引)
                    break
            else:
                self.当前选择原始索引 = 0
        elif 原始:
            self.当前选择原始索引 = max(
                0,
                min(int(getattr(self, "当前选择原始索引", 0) or 0), len(原始) - 1),
            )
        else:
            self.当前选择原始索引 = 0

        if 强制返回列表 or (bool(getattr(self, "是否详情页", False)) and not 原始):
            self.是否详情页 = False
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            self.确保播放背景音乐()

        列表, 映射 = self.当前歌曲列表与映射()
        if 映射:
            try:
                视图索引 = int(
                    映射.index(int(getattr(self, "当前选择原始索引", 0) or 0))
                )
            except Exception:
                视图索引 = 0
            self.当前页 = max(
                0, int(视图索引 // max(1, int(getattr(self, "每页数量", 1) or 1)))
            )
            self._踏板选中视图索引 = int(视图索引)
        else:
            self.当前页 = 0
            self._踏板选中视图索引 = None

        self.当前页卡片 = self.生成指定页卡片(self.当前页)
        self.安排预加载(基准页=self.当前页)
        self._同步踏板卡片高亮()

    def _切换收藏夹模式(self):
        当前歌曲键 = ""
        原始 = self.当前原始歌曲列表()
        try:
            当前索引 = int(getattr(self, "当前选择原始索引", 0) or 0)
        except Exception:
            当前索引 = 0

        if 0 <= 当前索引 < len(原始):
            当前歌曲键 = self._取歌曲收藏键(原始[当前索引])

        self.是否收藏夹模式 = not bool(getattr(self, "是否收藏夹模式", False))
        self.当前筛选星级 = None
        self._失效歌曲视图缓存()
        self._失效详情浮层缓存()
        self._刷新当前歌曲视图(保留歌曲键=当前歌曲键, 强制返回列表=True)
        try:
            if isinstance(getattr(self, "按钮_收藏夹", None), 底部图文按钮):
                self.按钮_收藏夹.底部文字 = (
                    "退出收藏夹" if bool(self.是否收藏夹模式) else "收藏夹"
                )
        except Exception:
            pass

    def _重置列表筛选(self):
        当前歌曲键 = ""
        原始 = self.当前原始歌曲列表()
        try:
            当前索引 = int(getattr(self, "当前选择原始索引", 0) or 0)
        except Exception:
            当前索引 = 0

        if 0 <= 当前索引 < len(原始):
            当前歌曲键 = self._取歌曲收藏键(原始[当前索引])

        self.当前筛选星级 = None
        if bool(getattr(self, "是否收藏夹模式", False)):
            self.是否收藏夹模式 = False
            self._失效歌曲视图缓存()
            self._失效详情浮层缓存()
            self._刷新当前歌曲视图(保留歌曲键=当前歌曲键, 强制返回列表=True)
            return

        self.设置星级筛选(None)

    def _切换当前歌曲收藏(self):
        原始 = self.当前原始歌曲列表()
        if not 原始:
            return

        try:
            当前索引 = int(getattr(self, "当前选择原始索引", 0) or 0)
        except Exception:
            当前索引 = 0
        当前索引 = max(0, min(当前索引, len(原始) - 1))
        歌 = 原始[当前索引]

        歌曲键 = self._取歌曲收藏键(歌)
        if not 歌曲键:
            self.显示消息提示("收藏夹保存失败", 持续秒=1.6)
            return

        原已收藏 = bool(歌曲键 in self._收藏歌曲键集合)
        if 原已收藏:
            self._收藏歌曲键集合.discard(歌曲键)
        else:
            self._收藏歌曲键集合.add(歌曲键)

        if not self._写入收藏夹数据():
            if 原已收藏:
                self._收藏歌曲键集合.add(歌曲键)
            else:
                self._收藏歌曲键集合.discard(歌曲键)
            self._同步歌曲收藏状态()
            self.显示消息提示("收藏夹保存失败", 持续秒=1.8)
            return

        self._同步歌曲收藏状态()
        self._失效收藏夹缓存()

        强制返回列表 = bool(self.是否收藏夹模式 and 原已收藏)
        self._刷新当前歌曲视图(
            保留歌曲键="" if 强制返回列表 else 歌曲键,
            强制返回列表=强制返回列表,
        )

        if 原已收藏:
            self.显示消息提示("移除收藏成功", 持续秒=1.5)
        else:
            self.显示消息提示("存入收藏夹成功", 持续秒=1.5)

    def _取详情封面图(
        self,
        歌: 歌曲信息,
        封面矩形: pygame.Rect,
    ) -> Optional[pygame.Surface]:
        if not isinstance(封面矩形, pygame.Rect):
            return None
        封面路径 = str(getattr(歌, "封面路径", "") or "")
        if (not 封面路径) or (not os.path.isfile(封面路径)):
            return None

        封面图 = self.图缓存.获取(
            封面路径,
            封面矩形.w,
            封面矩形.h,
            0,
            "stretch",
        )
        if isinstance(封面图, pygame.Surface):
            return 封面图

        封面图 = 载入并缩放封面(
            封面路径,
            封面矩形.w,
            封面矩形.h,
            0,
            "stretch",
        )
        if isinstance(封面图, pygame.Surface):
            self.图缓存.写入(
                封面路径,
                封面矩形.w,
                封面矩形.h,
                0,
                "stretch",
                封面图,
            )
        return 封面图

    def _绘制详情浮层面板内容(
        self,
        局部画布: pygame.Surface,
        歌: 歌曲信息,
        框路径: str,
        内容基础矩形: pygame.Rect,
        局部封面框: pygame.Rect,
        局部信息条: pygame.Rect,
        局部星星区域: pygame.Rect,
        局部游玩区域: pygame.Rect,
        局部bpm区域: pygame.Rect,
        装饰贴图宽: int,
        装饰贴图高: int,
        贴图绘制x: int,
        贴图绘制y: int,
        内容偏移x: int,
        内容偏移y: int,
        总宽: int,
        总高: int,
    ) -> None:
        封面图 = self._取详情封面图(歌, 局部封面框)
        _渲染详情浮层面板内容模块(
            panel_surface=局部画布,
            song=歌,
            frame_path=框路径,
            content_base_rect=内容基础矩形,
            local_cover_rect=局部封面框,
            local_info_rect=局部信息条,
            local_star_rect=局部星星区域,
            local_play_rect=局部游玩区域,
            local_bpm_rect=局部bpm区域,
            ornament_width=int(装饰贴图宽),
            ornament_height=int(装饰贴图高),
            ornament_draw_x=int(贴图绘制x),
            ornament_draw_y=int(贴图绘制y),
            content_offset_x=int(内容偏移x),
            content_offset_y=int(内容偏移y),
            cover_surface=封面图,
            big_star_path=_资源路径("UI-img", "选歌界面资源", "小星星", "大星星.png"),
            get_font=获取字体,
            get_play_count_color=_取游玩次数颜色,
            get_ui_container_image=获取UI容器图,
            draw_star_row=绘制星星行_图片,
            draw_sequence_label=绘制序号标签_图片,
            draw_mv_badge=绘制MV角标_文本,
            text_style=dict(_大图文字样式参数),
        )

    def _绘制详情浮层星星光泽(
        self,
        *,
        当前大框: pygame.Rect,
        局部星星区域: pygame.Rect,
        内容偏移x: int,
        内容偏移y: int,
        总宽: int,
        总高: int,
        星数: int,
        光效透明度: int,
    ):
        _绘制详情浮层星光模块(
            screen=self.屏幕,
            current_frame_rect=当前大框,
            local_star_rect=局部星星区域,
            content_offset_x=int(内容偏移x),
            content_offset_y=int(内容偏移y),
            total_width=int(总宽),
            total_height=int(总高),
            star_count=int(星数),
            effect_alpha=int(光效透明度),
            big_star_path=_资源路径("UI-img", "选歌界面资源", "小星星", "大星星.png"),
            star_effect_path=_资源路径("UI-img", "选歌界面资源", "小星星", "星星动态.png"),
            draw_star_row=绘制星星行_图片,
        )

    def _取当前歌曲列表缓存键(
        self, 原始列表: Optional[List[歌曲信息]] = None
    ) -> Tuple[str, str, Optional[int], bool, int, int, int]:
        if 原始列表 is None:
            原始列表 = self.当前原始歌曲列表()
        return (
            str(self.当前类型名() or ""),
            str(self.当前模式名() or ""),
            self.当前筛选星级,
            bool(getattr(self, "是否收藏夹模式", False)),
            int(getattr(self, "_收藏夹修改序号", 0) or 0),
            int(id(原始列表)),
            int(len(原始列表)),
        )

    def 当前原始歌曲列表(self) -> List[歌曲信息]:
        if bool(getattr(self, "是否收藏夹模式", False)):
            return self._获取收藏歌曲列表()

        if not self.类型列表 or not self.模式列表:
            return []
        try:
            列表 = self.数据树[self.当前类型名()][self.当前模式名()]
        except Exception:
            return []

        # ✅ 确保 NEW 标记已计算
        try:
            self._确保NEW标记(列表)
        except Exception:
            pass

        return 列表

    def _同步歌曲游玩记录(self):
        根目录 = self._取歌曲数据根目录()
        try:
            索引 = 读取歌曲记录索引(根目录)
        except Exception:
            索引 = {}

        self._歌曲记录索引 = dict(索引) if isinstance(索引, dict) else {}

        for 类型映射 in self.数据树.values():
            if not isinstance(类型映射, dict):
                continue
            for 列表 in 类型映射.values():
                if not isinstance(列表, list):
                    continue
                for 歌 in 列表:
                    try:
                        键 = 取歌曲记录键(_取歌曲记录路径源(歌), 根目录)
                    except Exception:
                        键 = ""
                    项 = self._歌曲记录索引.get(键, {})
                    try:
                        游玩次数 = int(max(0, int((项 or {}).get("游玩次数", 0) or 0)))
                    except Exception:
                        游玩次数 = 0
                    try:
                        setattr(歌, "游玩次数", 游玩次数)
                        setattr(歌, "是否HOT", _需要HOT标记(游玩次数))
                    except Exception:
                        pass

    def _确保NEW标记(self, 原始列表: Optional[List[歌曲信息]] = None):
        if bool(getattr(self, "_禁用NEW标记计算", False)):
            self._NEW标记_缓存键 = ("__DISABLED__",)
            return
        if 原始列表 is None:
            try:
                原始列表 = self.数据树[self.当前类型名()][self.当前模式名()]
            except Exception:
                原始列表 = []

        try:
            缓存键 = (self.当前类型名(), self.当前模式名(), id(原始列表), len(原始列表))
        except Exception:
            缓存键 = None

        if getattr(self, "_NEW标记_缓存键", None) == 缓存键:
            return

        self._NEW标记_缓存键 = 缓存键
        self._更新当前模式NEW标记(原始列表)

    def _更新当前模式NEW标记(self, 原始列表: List[歌曲信息]):
        if bool(getattr(self, "_禁用NEW标记计算", False)):
            return
        """
        规则：
        - 同“歌名”(解析后的 歌.歌名) 出现多个版本时
        - 最高星级的版本标记为 是否NEW=True（其余 False）
        """
        名称来源数: Dict[str, Set[str]] = {}
        名称最大星: Dict[str, int] = {}

        for 歌 in 原始列表:
            名键 = re.sub(r"\s+", "", str(getattr(歌, "歌名", "") or "")).lower()
            if not 名键:
                名键 = re.sub(
                    r"\s+", "", str(getattr(歌, "歌曲文件夹", "") or "")
                ).lower()
            来源键 = str(getattr(歌, "sm路径", "") or "").strip()
            if not 来源键:
                来源键 = str(getattr(歌, "歌曲路径", "") or "").strip()

            星 = 0
            try:
                星 = int(getattr(歌, "星级", 0) or 0)
            except Exception:
                星 = 0

            if 名键 not in 名称来源数:
                名称来源数[名键] = set()
            if 来源键:
                名称来源数[名键].add(来源键)
            名称最大星[名键] = max(名称最大星.get(名键, 0), 星)

        for 歌 in 原始列表:
            名键 = re.sub(r"\s+", "", str(getattr(歌, "歌名", "") or "")).lower()
            if not 名键:
                名键 = re.sub(
                    r"\s+", "", str(getattr(歌, "歌曲文件夹", "") or "")
                ).lower()

            星 = 0
            try:
                星 = int(getattr(歌, "星级", 0) or 0)
            except Exception:
                星 = 0

            是否多版本 = len(名称来源数.get(名键, set())) >= 2
            是否最高星 = 星 == 名称最大星.get(名键, 星)

            try:
                setattr(歌, "是否NEW", bool(是否多版本 and 是否最高星))
            except Exception:
                pass

    def 绘制详情角标_大图(self):
        """
        ✅ 叠加绘制（z轴在最上层）：
        - NEW：允许超出详情大框边界
        - VIP：允许超出详情大框边界
        - HOT：游玩次数大于等于 2 时显示在右下角
        """
        if not bool(getattr(self, "是否详情页", False)):
            return

        原始 = self.当前原始歌曲列表()
        if not 原始:
            return

        idx = int(getattr(self, "当前选择原始索引", 0) or 0)
        if idx < 0 or idx >= len(原始):
            return
        歌 = 原始[idx]

        大框 = getattr(self, "详情大框矩形", None)
        if not isinstance(大框, pygame.Rect) or 大框.w <= 10 or 大框.h <= 10:
            return

        alpha = int(getattr(self, "_详情浮层_alpha", 255) or 255)
        alpha = max(0, min(255, alpha))
        try:
            游玩次数 = int(max(0, int(getattr(歌, "游玩次数", 0) or 0)))
        except Exception:
            游玩次数 = 0
        _渲染详情角标模块(
            screen=self.屏幕,
            song=歌,
            panel_rect=大框,
            alpha=int(alpha),
            play_count=int(游玩次数),
            vip_path=_资源路径("UI-img", "选歌界面资源", "vip.png"),
            hot_path=_资源路径("UI-img", "选歌界面资源", "热门.png"),
            new_path=_资源路径("UI-img", "选歌界面资源", "NEW绿色.png"),
            get_ui_image=获取UI原图,
            scale_to_height=_按高等比缩放,
            get_layout_value=self._取布局值,
            get_layout_pixel=self._取布局像素,
            needs_hot=_需要HOT标记,
        )
        try:
            锚点矩形 = getattr(self, "详情封面矩形", None)
            if not isinstance(锚点矩形, pygame.Rect) or 锚点矩形.w <= 8:
                锚点矩形 = 大框
            _绘制歌曲模式标记(
                self.屏幕,
                锚点矩形,
                歌,
                是否大图=True,
                透明度=int(alpha),
            )
        except Exception:
            pass

    def 当前歌曲列表与映射(self) -> Tuple[List[歌曲信息], List[int]]:
        """
        返回：(显示用歌曲列表, 显示索引 -> 原始索引 映射)
        """
        原始 = self.当前原始歌曲列表()
        if not 原始:
            self._当前歌曲列表缓存键 = None
            self._当前歌曲列表缓存值 = ([], [])
            return [], []
        缓存键 = self._取当前歌曲列表缓存键(原始)
        if self._当前歌曲列表缓存键 == 缓存键:
            return self._当前歌曲列表缓存值
        if self.当前筛选星级 is None:
            映射 = list(range(len(原始)))
            self._当前歌曲列表缓存键 = 缓存键
            self._当前歌曲列表缓存值 = (原始, 映射)
            return self._当前歌曲列表缓存值

        过滤列表: List[歌曲信息] = []
        映射: List[int] = []
        for i, 歌 in enumerate(原始):
            if int(歌.星级) == int(self.当前筛选星级):
                过滤列表.append(歌)
                映射.append(i)
        self._当前歌曲列表缓存键 = 缓存键
        self._当前歌曲列表缓存值 = (过滤列表, 映射)
        return self._当前歌曲列表缓存值

    def 总页数(self) -> int:
        列表, _映射 = self.当前歌曲列表与映射()
        return max(1, math.ceil(len(列表) / self.每页数量))

    def _播放开始游戏音效(self):
        """
        ✅ 尽量不打断 pygame.mixer.music（它在播预览MP3/背景BGM）
        这里用你项目里的 公用按钮音效（通常走 Sound 通道）。
        """
        try:
            if getattr(self, "_开始游戏音效_对象", None) is not None:
                self._开始游戏音效_对象.播放()
        except Exception:
            # 兜底：静默失败，避免影响主循环
            pass

    def _生成加载页载荷(self) -> dict:
        # ✅ 先确保设置页默认参数存在
        try:
            if hasattr(self, "_确保设置页资源"):
                self._确保设置页资源()
        except Exception:
            pass

        原始列表 = []
        try:
            原始列表 = self.当前原始歌曲列表()
        except Exception:
            原始列表 = []

        歌 = None
        try:
            当前索引 = int(getattr(self, "当前选择原始索引", 0) or 0)
            if 0 <= 当前索引 < len(原始列表):
                歌 = 原始列表[当前索引]
        except Exception:
            歌 = None

        # ✅ 设置参数：优先用持久化 json，其次才用内存参数
        try:
            if hasattr(self, "_设置页_保存持久化设置"):
                self._设置页_保存持久化设置()
        except Exception:
            pass

        设置参数 = {}
        背景文件名 = ""
        箭头文件名 = ""
        设置参数文本 = ""

        try:
            if hasattr(self, "_设置页_读取持久化设置"):
                持久化数据 = self._设置页_读取持久化设置()
            else:
                持久化数据 = {}
        except Exception:
            持久化数据 = {}

        if isinstance(持久化数据, dict):
            try:
                v = 持久化数据.get("设置参数", {})
                if isinstance(v, dict):
                    设置参数 = dict(v)
            except Exception:
                pass
            try:
                背景文件名 = str(持久化数据.get("背景文件名", "") or "")
            except Exception:
                背景文件名 = ""
            try:
                箭头文件名 = str(持久化数据.get("箭头文件名", "") or "")
            except Exception:
                箭头文件名 = ""
            try:
                设置参数文本 = str(持久化数据.get("设置参数文本", "") or "")
            except Exception:
                设置参数文本 = ""

        if not 设置参数:
            try:
                临时参数 = getattr(self, "设置_参数", None)
                if isinstance(临时参数, dict):
                    设置参数 = dict(临时参数)
            except Exception:
                设置参数 = {}

        if not 背景文件名:
            try:
                背景文件名 = str(getattr(self, "设置_背景大图文件名", "") or "")
            except Exception:
                背景文件名 = ""
        if not 箭头文件名:
            try:
                箭头文件名 = str(getattr(self, "设置_箭头文件名", "") or "")
            except Exception:
                箭头文件名 = ""

        if not 设置参数文本:
            try:
                设置参数文本 = self._设置页_构建参数文本(
                    设置参数=设置参数,
                    背景文件名=背景文件名,
                    箭头文件名=箭头文件名,
                )
            except Exception:
                设置参数文本 = "设置参数：默认"

        # ✅ 歌曲信息（兜底）
        sm路径 = "未知"
        封面路径 = ""
        歌名 = "Loading..."
        星级 = 0
        bpm = None
        游玩次数 = 0
        类型 = ""
        模式 = ""
        歌曲文件夹 = ""
        原始歌曲文件夹 = ""
        谱面charttype = ""
        谱面模式标记 = ""
        记录键sm路径 = ""

        if 歌 is not None:
            try:
                _按需补全歌曲模式标记字段(歌)
            except Exception:
                pass
            try:
                sm路径 = str(getattr(歌, "sm路径", "") or "未知")
            except Exception:
                sm路径 = "未知"
            try:
                封面路径 = str(getattr(歌, "封面路径", "") or "")
            except Exception:
                封面路径 = ""
            try:
                歌名 = str(getattr(歌, "歌名", "") or "Loading...")
            except Exception:
                歌名 = "Loading..."
            try:
                星级 = int(getattr(歌, "星级", 0) or 0)
            except Exception:
                星级 = 0
            try:
                bpm = getattr(歌, "bpm", None)
                bpm = int(bpm) if bpm is not None else None
            except Exception:
                bpm = None
            try:
                游玩次数 = int(max(0, int(getattr(歌, "游玩次数", 0) or 0)))
            except Exception:
                游玩次数 = 0

            # ✅ 这三个用于 StepMania runtime pack 命名/建目录
            try:
                类型 = str(getattr(歌, "类型", "") or "")
            except Exception:
                类型 = ""
            try:
                模式 = str(getattr(歌, "模式", "") or "")
            except Exception:
                模式 = ""
            try:
                歌曲文件夹 = str(getattr(歌, "歌曲文件夹", "") or "")
            except Exception:
                歌曲文件夹 = ""
            try:
                谱面charttype = str(getattr(歌, "谱面charttype", "") or "").strip().lower()
            except Exception:
                谱面charttype = ""
            try:
                谱面模式标记 = str(getattr(歌, "谱面模式标记", "") or "").strip()
            except Exception:
                谱面模式标记 = ""
            try:
                记录键sm路径 = str(getattr(歌, "记录键sm路径", "") or "").strip()
            except Exception:
                记录键sm路径 = ""

            # ✅ 原始歌曲文件夹：直接取 sm 所在目录（里面有 .sm）
            try:
                if sm路径 and os.path.isfile(sm路径):
                    原始歌曲文件夹 = os.path.dirname(sm路径)
            except Exception:
                原始歌曲文件夹 = ""

        人气 = 0
        try:
            人气 = int(bpm or 0)
        except Exception:
            人气 = 0

        状态 = self.上下文.get("状态", {}) if isinstance(self.上下文, dict) else {}
        当前关卡 = 取当前关卡(状态, 1)
        累计S数 = 取累计S数(状态)
        已赠送第四把 = 是否赠送第四把(状态)
        背景模式 = str(
            设置参数.get("背景模式", 设置参数.get("变速", "图片")) or "图片"
        ).strip()
        背景文件名 = _按关卡解析图片背景文件名(
            self,
            背景文件名=背景文件名,
            背景模式=背景模式,
            持久化数据=持久化数据 if isinstance(持久化数据, dict) else None,
            自动补全=True,
            可用背景文件名列表=list(
                getattr(self, "设置_背景大图文件名列表", []) or []
            ),
        )
        if 背景文件名:
            try:
                self.设置_背景大图文件名 = str(背景文件名)
            except Exception:
                pass
        try:
            设置参数文本 = self._设置页_构建参数文本(
                设置参数=设置参数,
                背景文件名=背景文件名,
                箭头文件名=箭头文件名,
            )
        except Exception:
            pass
        当前页码 = 0
        try:
            当前页码 = max(0, int(getattr(self, "当前页", 0) or 0))
        except Exception:
            当前页码 = 0
        收藏夹模式 = bool(getattr(self, "是否收藏夹模式", False))

        return {
            "sm路径": sm路径,
            "封面路径": 封面路径,
            "歌名": 歌名,
            "星级": int(星级),
            "bpm": bpm,
            "人气": int(人气),
            "游玩次数": int(游玩次数),
            "设置参数": dict(设置参数),
            "设置参数文本": str(设置参数文本),
            "背景文件名": str(背景文件名),
            "背景文件名_按关卡": dict(
                _规范化关卡背景映射(getattr(self, "设置_背景文件名按关卡", {}))
            ),
            "箭头文件名": str(箭头文件名),
            "关闭视频背景": bool(
                str(
                    设置参数.get("背景模式", 设置参数.get("变速", "图片"))
                    or "图片"
                ).strip()
                != "视频"
            ),
            # ✅ 给 StepMania 用
            "类型": 类型,
            "模式": 模式,
            "谱面charttype": str(谱面charttype),
            "谱面模式标记": str(谱面模式标记),
            "记录键sm路径": str(记录键sm路径 or sm路径),
            "歌曲文件夹": 歌曲文件夹,
            "原始歌曲文件夹": 原始歌曲文件夹,
            "选歌原始索引": int(当前索引 if 歌 is not None else -1),
            "选歌收藏夹模式": bool(收藏夹模式),
            "选歌收藏夹页码": int(当前页码),
            "当前关卡": int(当前关卡),
            "局数": int(当前关卡),
            "累计S数": int(累计S数),
            "是否赠送第四把": bool(已赠送第四把),
        }

    def _写入加载页json(self, 载荷: dict):
        try:
            _覆盖存储作用域(_加载页存储作用域, dict(载荷 or {}))
        except Exception:
            return

    def _记录并处理大图确认点击(self):
        现在时间 = time.time()
        上次触发 = float(getattr(self, "_大图确认_上次触发时间", 0.0) or 0.0)

        if 上次触发 > 0.0 and (现在时间 - 上次触发) < 0.25:
            return

        self._大图确认_上次触发时间 = 现在时间

        # 1) 播放开始音效（你原逻辑）
        self._播放开始游戏音效()

        # 2) 生成加载页载荷（给新场景展示）
        try:
            self._加载页_载荷 = self._生成加载页载荷()
        except Exception:
            self._加载页_载荷 = {}

        # ✅ 2.1 关键：落盘，加载页/谱面播放器都能兜底读取
        try:
            self._写入加载页json(self._加载页_载荷)
        except Exception:
            pass

        # 3) 退出选歌，交给上层切场景
        self._返回状态 = "GO_LOADING"
        self._需要退出 = True

    def 显示消息提示(self, 文本: str, 持续秒: float = 2.0):
        self._消息提示_文本 = str(文本 or "")
        self._消息提示_截止时间 = time.time() + float(max(0.1, 持续秒))

    def _绘制消息提示(self):
        文本 = str(getattr(self, "_消息提示_文本", "") or "")
        截止 = float(getattr(self, "_消息提示_截止时间", 0.0) or 0.0)
        if (not 文本) or time.time() >= 截止:
            return

        屏幕 = self.屏幕
        w, h = 屏幕.get_size()

        try:
            字体 = getattr(self, "正文字体粗", None) or getattr(self, "正文字体", None)
            if 字体 is None:
                字体 = 获取字体(26, 是否粗体=True)
        except Exception:
            字体 = 获取字体(26, 是否粗体=True)

        最大宽 = int(w * 0.72)
        内边距x = 26
        内边距y = 18
        圆角 = 18

        # 简单自动换行（按像素宽）
        行列表 = []
        当前行 = ""
        for 字 in 文本:
            if 字 == "\n":
                行列表.append(当前行)
                当前行 = ""
                continue
            测试 = 当前行 + 字
            try:
                if 字体.size(测试)[0] <= 最大宽:
                    当前行 = 测试
                else:
                    if 当前行:
                        行列表.append(当前行)
                    当前行 = 字
            except Exception:
                当前行 = 测试

        if 当前行:
            行列表.append(当前行)

        # 渲染每行
        行面列表 = []
        文本宽 = 0
        文本高 = 0
        for 行 in 行列表:
            try:
                白 = 字体.render(行, True, (255, 255, 255))
                黑 = 字体.render(行, True, (0, 0, 0))
                行面列表.append((白, 黑))
                文本宽 = max(文本宽, 白.get_width())
                文本高 += 白.get_height()
            except Exception:
                continue

        if not 行面列表:
            return

        背景宽 = min(w - 60, 文本宽 + 内边距x * 2)
        背景高 = min(h - 60, 文本高 + 内边距y * 2)

        # 位置：偏下中间（别挡住top栏）
        背景x = (w - 背景宽) // 2
        背景y = int(h * 0.58) - 背景高 // 2
        背景y = max(int(getattr(self, "顶部高", 80) + 18), 背景y)

        背景矩形 = pygame.Rect(背景x, 背景y, 背景宽, 背景高)

        # 半透明背景 + 边框
        背景面 = pygame.Surface((背景矩形.w, 背景矩形.h), pygame.SRCALPHA)
        背景面.fill((0, 0, 0, 180))
        屏幕.blit(背景面, 背景矩形.topleft)
        try:
            pygame.draw.rect(
                屏幕, (255, 220, 120), 背景矩形, width=2, border_radius=圆角
            )
        except Exception:
            pass

        # 绘制文字（带轻微黑影）
        当前y = 背景矩形.y + 内边距y
        for 白, 黑 in 行面列表:
            x = 背景矩形.centerx - 白.get_width() // 2
            屏幕.blit(黑, (x + 2, 当前y + 2))
            屏幕.blit(白, (x, 当前y))
            当前y += 白.get_height()

    def _背景音乐被全局关闭(self) -> bool:
        try:
            状态 = self.上下文.get("状态", {}) if isinstance(self.上下文, dict) else {}
        except Exception:
            状态 = {}
        if not isinstance(状态, dict):
            状态 = {}
        try:
            return bool(状态.get("非游戏菜单背景音乐关闭", False))
        except Exception:
            return False

    def 确保播放背景音乐(self):
        if not self.音频可用:
            return
        if self._背景音乐被全局关闭():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            return
        if not self.背景音乐路径 or not self._背景音乐路径存在():
            return
        try:
            if pygame.mixer.music.get_busy():
                return
            pygame.mixer.music.load(self.背景音乐路径)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    def _背景音乐路径存在(self) -> bool:
        路径 = str(getattr(self, "背景音乐路径", "") or "")
        if 路径 == str(getattr(self, "_背景音乐路径存在缓存键", "") or ""):
            return bool(getattr(self, "_背景音乐路径存在缓存值", False))
        结果 = bool(路径 and os.path.isfile(路径))
        self._背景音乐路径存在缓存键 = 路径
        self._背景音乐路径存在缓存值 = bool(结果)
        return bool(结果)

    def 播放歌曲mp3(self, mp3路径: Optional[str]):
        if not self.音频可用:
            return
        if self._背景音乐被全局关闭():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        if not mp3路径 or not os.path.isfile(mp3路径):
            return
        try:
            pygame.mixer.music.load(mp3路径)
            pygame.mixer.music.play()
        except Exception:
            pass


    def 重算布局(self):
        self._确保公共交互()

        self.宽, self.高 = self.屏幕.get_size()
        self._top缓存尺寸 = (0, 0)

        self._确保top栏缓存()

        if self.背景图_原图 is None:
            self._加载背景图()

        # ========= 底部槽位（修复：默认值按窗口同比缩放，不再焊死） =========
        槽边长 = self._取底部布局像素("底部.槽边长", 164, 最小=64, 最大=420)

        标签占比 = self._取布局值("底部.标签区高占比", 0.26)
        try:
            标签占比 = float(标签占比)
        except Exception:
            标签占比 = 0.26
        标签占比 = max(0.05, min(0.60, 标签占比))

        标签区高 = max(24, int(槽边长 * 标签占比))
        槽总高 = 槽边长 + 标签区高

        底部最小高 = self._取底部布局像素("底部.底部最小高", 220, 最小=100, 最大=9999)
        底部额外高 = self._取底部布局像素("底部.底部额外高", 40, 最小=0, 最大=9999)
        self.底部高 = max(底部最小高, 槽总高 + 底部额外高)

        self.中间区域 = pygame.Rect(
            0, self.顶部高, self.宽, self.高 - self.顶部高 - self.底部高
        )

        槽y = self.高 - self.底部高 + (self.底部高 - 槽总高) // 2

        左起 = self._取底部布局像素("底部.左起", 28, 最小=0, 最大=9999)
        左组间距 = self._取底部布局像素("底部.左组间距", 12, 最小=0, 最大=9999)
        右组间距 = self._取底部布局像素("底部.右组间距", 26, 最小=0, 最大=9999)
        右外边距 = self._取底部布局像素("底部.右外边距", 40, 最小=0, 最大=9999)

        槽_歌曲分类 = pygame.Rect(左起, 槽y, 槽边长, 槽总高)
        槽_收藏夹 = pygame.Rect(槽_歌曲分类.right + 左组间距, 槽y, 槽边长, 槽总高)
        槽_ALL = pygame.Rect(槽_收藏夹.right + 左组间距, 槽y, 槽边长, 槽总高)
        槽_重开 = pygame.Rect(槽_ALL.right + 左组间距, 槽y, 槽边长, 槽总高)

        右起 = self.宽 - 右外边距 - 槽边长
        槽_设置 = pygame.Rect(右起, 槽y, 槽边长, 槽总高)
        槽_P加入 = pygame.Rect(右起 - 右组间距 - 槽边长, 槽y, 槽边长, 槽总高)

        # ===== 资源路径 =====
        歌曲分类图路径 = _资源路径("UI-img", "选歌界面资源", "歌曲分类.png")
        收藏夹图路径 = _资源路径("UI-img", "选歌界面资源", "收藏夹.png")
        收藏夹底文 = "退出收藏夹" if bool(getattr(self, "是否收藏夹模式", False)) else "收藏夹"
        ALL图路径 = _资源路径("UI-img", "选歌界面资源", "all按钮.png")
        设置图路径 = _资源路径("UI-img", "选歌界面资源", "设置.png")

        # ✅ 1P/2P 联动：缺谁就显示谁加入
        当前玩家数 = 2 if int(getattr(self, "玩家数", 1)) == 2 else 1
        需要显示加入 = 2 if 当前玩家数 == 1 else 1
        P加入底文 = f"{需要显示加入}P加入"

        P加入候选 = [
            _资源路径("UI-img", "选歌界面资源", f"{需要显示加入}p加入.png"),
            _资源路径("UI-img", "选歌界面资源", f"{需要显示加入}P加入.png"),
            _资源路径("UI-img", "选歌界面资源", "1p加入.png"),
        ]
        P加入图路径 = P加入候选[-1]
        for p in P加入候选:
            if os.path.isfile(p):
                P加入图路径 = p
                break

        # ===== 确保底部按钮类型 =====
        if (not hasattr(self, "按钮_歌曲分类")) or (
            not isinstance(self.按钮_歌曲分类, 底部图文按钮)
        ):
            self.按钮_歌曲分类 = 底部图文按钮(
                图片路径=歌曲分类图路径,
                矩形=pygame.Rect(0, 0, 0, 0),
                底部文字="歌曲分类",
                是否处理透明像素=False,
            )

        if (not hasattr(self, "按钮_收藏夹")) or (
            not isinstance(self.按钮_收藏夹, 底部图文按钮)
        ):
            self.按钮_收藏夹 = 底部图文按钮(
                图片路径=收藏夹图路径,
                矩形=pygame.Rect(0, 0, 0, 0),
                底部文字=收藏夹底文,
                是否处理透明像素=False,
            )
        else:
            try:
                self.按钮_收藏夹.图片路径 = str(收藏夹图路径)
                self.按钮_收藏夹.底部文字 = 收藏夹底文
                self.按钮_收藏夹._加载原图()
            except Exception:
                pass

        if (not hasattr(self, "按钮_ALL")) or (not isinstance(self.按钮_ALL, 图片按钮)):
            self.按钮_ALL = 图片按钮(
                图片路径=ALL图路径,
                矩形=pygame.Rect(0, 0, 0, 0),
                是否水平翻转=False,
                是否垂直翻转=False,
            )

        if (not hasattr(self, "按钮_2P加入")) or (
            not isinstance(self.按钮_2P加入, 底部图文按钮)
        ):
            self.按钮_2P加入 = 底部图文按钮(
                图片路径=P加入图路径,
                矩形=pygame.Rect(0, 0, 0, 0),
                底部文字=P加入底文,
                是否处理透明像素=False,
            )
        else:
            try:
                self.按钮_2P加入.图片路径 = str(P加入图路径)
                self.按钮_2P加入.底部文字 = str(P加入底文)
                self.按钮_2P加入._加载原图()
            except Exception:
                pass

        if (not hasattr(self, "按钮_设置")) or (
            not isinstance(self.按钮_设置, 底部图文按钮)
        ):
            self.按钮_设置 = 底部图文按钮(
                图片路径=设置图路径,
                矩形=pygame.Rect(0, 0, 0, 0),
                底部文字="设置",
                是否处理透明像素=False,
            )

        if not hasattr(self, "按钮_重选模式"):
            self.按钮_重选模式 = 按钮("", pygame.Rect(0, 0, 0, 0))
        else:
            try:
                self.按钮_重选模式.名称 = ""
            except Exception:
                pass

        # ===== 设置最终矩形 =====
        self.按钮_歌曲分类.矩形 = 槽_歌曲分类
        self.按钮_收藏夹.矩形 = 槽_收藏夹
        self.按钮_2P加入.矩形 = 槽_P加入
        self.按钮_设置.矩形 = 槽_设置

        统一文字偏移 = self._取底部布局像素("底部.统一文字偏移", -6, 最小=-9999, 最大=9999)
        try:
            self.按钮_歌曲分类.文字y偏移 = 统一文字偏移
            self.按钮_收藏夹.文字y偏移 = 统一文字偏移
            self.按钮_2P加入.文字y偏移 = 统一文字偏移
            self.按钮_设置.文字y偏移 = 统一文字偏移
        except Exception:
            pass

        # ALL / 重开：只占上半部图标区
        槽_ALL_图标区 = pygame.Rect(槽_ALL.x, 槽_ALL.y, 槽边长, 槽边长)
        槽_重开_图标区 = pygame.Rect(槽_重开.x, 槽_重开.y, 槽边长, 槽边长)

        ALL缩放 = self._取布局值("底部.ALL缩放", 0.5)
        重开缩放 = self._取布局值("底部.重开缩放", 0.5)
        try:
            ALL缩放 = float(ALL缩放)
        except Exception:
            ALL缩放 = 0.5
        try:
            重开缩放 = float(重开缩放)
        except Exception:
            重开缩放 = 0.5
        ALL缩放 = max(0.1, min(2.0, ALL缩放))
        重开缩放 = max(0.1, min(2.0, 重开缩放))

        ALL边长 = max(24, int(槽边长 * ALL缩放))
        重开边长 = max(24, int(槽边长 * 重开缩放))

        ALL矩形 = pygame.Rect(0, 0, ALL边长, ALL边长)
        ALL矩形.center = 槽_ALL_图标区.center
        self.按钮_ALL.矩形 = ALL矩形

        重开矩形 = pygame.Rect(0, 0, 重开边长, 重开边长)
        重开矩形.center = 槽_重开_图标区.center
        self.按钮_重选模式.矩形 = 重开矩形

        # # ========= 模式选择面板（保留原逻辑） =========
        # 最大宽 = self._取布局像素("模式选择面板.最大宽", 920, 最小=300, 最大=9999)
        # 最大高 = self._取布局像素("模式选择面板.最大高", 460, 最小=200, 最大=9999)

        # 宽占比 = self._取布局值("模式选择面板.宽占比", 0.75)
        # 高占比 = self._取布局值("模式选择面板.高占比", 0.55)
        # try:
        #     宽占比 = float(宽占比)
        # except Exception:
        #     宽占比 = 0.75
        # try:
        #     高占比 = float(高占比)
        # except Exception:
        #     高占比 = 0.55
        # 宽占比 = max(0.20, min(0.98, 宽占比))
        # 高占比 = max(0.20, min(0.98, 高占比))

        # ========= 卡片网格（保留原逻辑） =========
        try:
            列数 = int(self._取布局值("卡片网格.列数", 4))
        except Exception:
            列数 = 4
        try:
            行数 = int(self._取布局值("卡片网格.行数", 2))
        except Exception:
            行数 = 2
        列数 = max(1, min(12, 列数))
        行数 = max(1, min(12, 行数))
        self.每页数量 = int(列数 * 行数)

        self._清空页卡片缓存()
        self.当前页卡片 = self.生成指定页卡片(self.当前页)
        self._重算星级筛选页布局()

        # 详情页左右按钮（保留）
        下一首图路径 = _资源路径("UI-img", "选歌界面资源", "下一首.png")
        if (not hasattr(self, "按钮_详情上一首")) or (
            not isinstance(self.按钮_详情上一首, 图片按钮)
        ):
            self.按钮_详情上一首 = 图片按钮(
                图片路径=下一首图路径,
                矩形=pygame.Rect(0, 0, 0, 0),
                是否水平翻转=True,
                是否垂直翻转=False,
            )
        if (not hasattr(self, "按钮_详情下一首")) or (
            not isinstance(self.按钮_详情下一首, 图片按钮)
        ):
            self.按钮_详情下一首 = 图片按钮(
                图片路径=下一首图路径,
                矩形=pygame.Rect(0, 0, 0, 0),
                是否水平翻转=False,
                是否垂直翻转=False,
            )

        列表翻页图路径 = _资源路径("UI-img", "选歌界面资源", "下一首-选歌.png")
        if (not hasattr(self, "按钮_列表上一页")) or (
            not isinstance(self.按钮_列表上一页, 图片按钮)
        ):
            self.按钮_列表上一页 = 图片按钮(
                图片路径=列表翻页图路径,
                矩形=pygame.Rect(0, 0, 0, 0),
                是否水平翻转=True,
                是否垂直翻转=False,
                透明度=176,
            )
        else:
            if str(getattr(self.按钮_列表上一页, "图片路径", "") or "") != 列表翻页图路径:
                self.按钮_列表上一页.图片路径 = str(列表翻页图路径)
                self.按钮_列表上一页._加载原图()
            self.按钮_列表上一页.是否水平翻转 = True
            self.按钮_列表上一页.是否垂直翻转 = False
            self.按钮_列表上一页.透明度 = 176

        if (not hasattr(self, "按钮_列表下一页")) or (
            not isinstance(self.按钮_列表下一页, 图片按钮)
        ):
            self.按钮_列表下一页 = 图片按钮(
                图片路径=列表翻页图路径,
                矩形=pygame.Rect(0, 0, 0, 0),
                是否水平翻转=False,
                是否垂直翻转=False,
                透明度=176,
            )
        else:
            if str(getattr(self.按钮_列表下一页, "图片路径", "") or "") != 列表翻页图路径:
                self.按钮_列表下一页.图片路径 = str(列表翻页图路径)
                self.按钮_列表下一页._加载原图()
            self.按钮_列表下一页.是否水平翻转 = False
            self.按钮_列表下一页.是否垂直翻转 = False
            self.按钮_列表下一页.透明度 = 176

        翻页按钮原图 = getattr(self.按钮_列表下一页, "_原图", None)
        if not isinstance(翻页按钮原图, pygame.Surface):
            翻页按钮原图 = getattr(self.按钮_列表上一页, "_原图", None)
        if isinstance(翻页按钮原图, pygame.Surface):
            原宽 = max(1, int(翻页按钮原图.get_width()))
            原高 = max(1, int(翻页按钮原图.get_height()))
        else:
            原宽, 原高 = 157, 238

        列表翻页按钮高 = max(96, min(int(self.中间区域.h * 0.28), 176))
        列表翻页按钮宽 = max(
            48, int(round(float(列表翻页按钮高) * float(原宽) / float(max(1, 原高))))
        )
        列表翻页按钮边距 = max(12, int(self.宽 * 0.016))
        列表翻页按钮y = self.中间区域.centery - 列表翻页按钮高 // 2
        列表翻页按钮y = max(
            self.中间区域.top + 12,
            min(self.中间区域.bottom - 列表翻页按钮高 - 12, 列表翻页按钮y),
        )

        self.按钮_列表上一页.矩形 = pygame.Rect(
            列表翻页按钮边距,
            列表翻页按钮y,
            列表翻页按钮宽,
            列表翻页按钮高,
        )
        self.按钮_列表下一页.矩形 = pygame.Rect(
            self.宽 - 列表翻页按钮边距 - 列表翻页按钮宽,
            列表翻页按钮y,
            列表翻页按钮宽,
            列表翻页按钮高,
        )
        self._失效GPU界面层缓存()

    def _加载背景图(self):
        try:
            默认路径 = _公共取冷资源路径("backimages", "选歌界面.png")
            路径 = 默认路径
            可用背景文件名列表 = list(
                getattr(self, "设置_背景大图文件名列表", []) or []
            )
            if not 可用背景文件名列表:
                背景目录 = _资源路径("冷资源", "backimages", "背景图")
                if os.path.isdir(背景目录):
                    支持后缀 = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
                    try:
                        for 文件名 in sorted(os.listdir(背景目录)):
                            if str(文件名 or "").lower().endswith(支持后缀):
                                可用背景文件名列表.append(str(文件名))
                    except Exception:
                        可用背景文件名列表 = []

            设置参数 = {}
            背景文件名 = ""
            try:
                if isinstance(getattr(self, "设置_参数", None), dict):
                    设置参数 = dict(getattr(self, "设置_参数", {}) or {})
                背景文件名 = str(getattr(self, "设置_背景大图文件名", "") or "").strip()
            except Exception:
                设置参数 = {}
                背景文件名 = ""

            持久化数据 = {}
            try:
                持久化数据 = self._设置页_读取持久化设置()
            except Exception:
                持久化数据 = {}
            if isinstance(持久化数据, dict):
                if not 设置参数:
                    try:
                        值 = 持久化数据.get("设置参数", {})
                        if isinstance(值, dict):
                            设置参数 = dict(值)
                    except Exception:
                        设置参数 = {}
                if not 背景文件名:
                    try:
                        背景文件名 = str(持久化数据.get("背景文件名", "") or "").strip()
                    except Exception:
                        背景文件名 = ""

            背景模式 = str(
                设置参数.get("背景模式", 设置参数.get("变速", "图片")) or "图片"
            ).strip()
            背景文件名 = _按关卡解析图片背景文件名(
                self,
                背景文件名=背景文件名,
                背景模式=背景模式,
                持久化数据=持久化数据 if isinstance(持久化数据, dict) else None,
                自动补全=True,
                可用背景文件名列表=可用背景文件名列表
                if 可用背景文件名列表
                else None,
            )
            if 背景模式 == "图片" and 背景文件名:
                self.设置_背景大图文件名 = str(背景文件名)
                if 可用背景文件名列表:
                    try:
                        self.设置_背景索引 = int(
                            max(
                                0,
                                min(
                                    len(可用背景文件名列表) - 1,
                                    可用背景文件名列表.index(str(背景文件名)),
                                ),
                            )
                        )
                    except Exception:
                        pass
                路径 = _公共取首个存在路径(
                    _公共取冷资源路径("backimages", "背景图", 背景文件名),
                    _公共取冷资源路径("backimages", 背景文件名),
                    路径,
                )
            else:
                _读取关卡背景映射(
                    self,
                    持久化数据=持久化数据 if isinstance(持久化数据, dict) else None,
                    可用背景文件名列表=可用背景文件名列表 if 可用背景文件名列表 else None,
                )

            if os.path.isfile(路径):
                背景图 = pygame.image.load(路径)
                self.背景图_原图 = (
                    背景图.convert_alpha()
                    if 背景图.get_alpha() is not None
                    else 背景图.convert()
                )
            else:
                self.背景图_原图 = None
        except Exception:
            self.背景图_原图 = None
        self.背景图_缩放缓存 = None
        self.背景图_缩放尺寸 = (0, 0)
        try:
            self._动态背景上次刷新秒 = float(time.perf_counter())
            self._同步动态背景管理器(True)
        except Exception:
            pass

    def _刷新背景遮罩设置(self, 强制: bool = False):
        现在时刻 = float(time.perf_counter())
        if (not bool(强制)) and (
            现在时刻 - float(getattr(self, "_背景遮罩设置最近读取时间", -999.0) or -999.0)
        ) < 0.25:
            return

        self._背景遮罩设置最近读取时间 = 现在时刻
        新alpha = 60
        try:
            持久化数据 = _读取存储作用域(_游戏esc菜单设置存储作用域)
        except Exception:
            持久化数据 = {}

        if isinstance(持久化数据, dict):
            try:
                新alpha = int(持久化数据.get("背景遮罩alpha", 新alpha) or 新alpha)
            except Exception:
                新alpha = 60

        新alpha = max(0, min(255, int(新alpha)))
        if 新alpha != int(getattr(self, "_背景遮罩alpha", 60) or 60):
            self._背景遮罩alpha = int(新alpha)
            self._背景暗层缓存 = None
            self._背景暗层缓存键 = (0, 0, 0)

    def _取当前背景设置参数(self) -> dict:
        try:
            self._设置页_同步外部持久化设置(强制=False, 刷新界面=False)
        except Exception:
            pass
        参数 = {}
        try:
            if isinstance(getattr(self, "设置_参数", None), dict):
                参数 = dict(getattr(self, "设置_参数", {}) or {})
        except Exception:
            参数 = {}

        if 参数:
            return 参数

        try:
            持久化数据 = self._设置页_读取持久化设置()
        except Exception:
            持久化数据 = {}
        if isinstance(持久化数据, dict):
            try:
                值 = 持久化数据.get("设置参数", {})
                if isinstance(值, dict):
                    参数 = dict(值)
            except Exception:
                参数 = {}
        return 参数

    def _取动态背景模式(self) -> str:
        参数 = self._取当前背景设置参数()
        背景模式 = str(
            参数.get("背景模式", 参数.get("变速", "图片")) or "图片"
        ).strip()
        if 背景模式 != "动态背景":
            return "关闭"
        值 = DynamicBackgroundManager.normalize_mode(
            str(参数.get("动态背景", "关闭") or "关闭").strip()
        )
        return 值 if 值 != "关闭" else "唱片"

    def _取背景渲染模式(self) -> str:
        参数 = self._取当前背景设置参数()
        值 = str(参数.get("背景模式", 参数.get("变速", "图片")) or "图片").strip()
        if 值 == "视频":
            return "视频"
        if 值 == "动态背景":
            return "动态背景"
        return "图片"

    def _同步动态背景管理器(self, 重置: bool = False):
        管理器 = getattr(self, "_动态背景管理器", None)
        if 管理器 is None:
            return
        资源根目录 = ""
        try:
            资源 = self.上下文.get("资源", {}) if isinstance(self.上下文, dict) else {}
            if isinstance(资源, dict):
                资源根目录 = str(资源.get("根", "") or "").strip()
        except Exception:
            资源根目录 = ""
        if not 资源根目录:
            资源根目录 = _取项目根目录()
        try:
            管理器.configure_paths(
                resource_root=资源根目录,
                runtime_root=_取运行根目录(),
                project_root=_取项目根目录(),
            )
            if bool(重置):
                管理器.reset()
        except Exception:
            pass

    def _更新动态背景模块(self, 时间差: float, 当前秒: float):
        模式 = self._取动态背景模式()
        if 模式 == "关闭":
            return
        管理器 = getattr(self, "_动态背景管理器", None)
        if 管理器 is None:
            return
        self._同步动态背景管理器(False)
        try:
            管理器.update(
                模式,
                DynamicBackgroundContext(
                    renderer=None,
                    screen_size=(int(self.宽), int(self.高)),
                    combo=0,
                    now=float(当前秒),
                    delta_time=float(max(0.0, 时间差)),
                    resource_root=str(getattr(管理器, "resource_root", "") or ""),
                    runtime_root=str(getattr(管理器, "runtime_root", "") or ""),
                    project_root=str(getattr(管理器, "project_root", "") or ""),
                ),
            )
        except Exception:
            pass

    def _绘制软件动态背景(self) -> bool:
        模式 = self._取动态背景模式()
        if 模式 == "关闭":
            return False
        管理器 = getattr(self, "_动态背景管理器", None)
        if 管理器 is None:
            return False
        self._同步动态背景管理器(False)
        try:
            return bool(
                管理器.render_preview_surface(
                    模式,
                    self.屏幕,
                    now=float(time.perf_counter()),
                )
            )
        except Exception:
            return False

    def _应使用GPU背景(self) -> bool:
        if bool(getattr(self, "_选歌场景强制CPU绘制", False)):
            return False
        if _sdl2_video is None:
            return False
        try:
            显示后端 = self.上下文.get("显示后端", None) if isinstance(self.上下文, dict) else None
        except Exception:
            显示后端 = None
        return bool(getattr(显示后端, "是否GPU", False))

    def _同步GPU背景缓存(self, 渲染器):
        当前渲染器id = int(id(渲染器))
        if 当前渲染器id == int(getattr(self, "_GPU背景纹理渲染器id", 0) or 0):
            return
        self._GPU背景纹理渲染器id = 当前渲染器id
        self._GPU背景纹理 = None
        self._GPU背景纹理键 = ()
        self._GPU背景遮罩纹理缓存 = {}

    def _取GPU背景纹理(self, 渲染器, 图: Optional[pygame.Surface]):
        if _sdl2_video is None or 渲染器 is None or not isinstance(图, pygame.Surface):
            return None
        缓存键 = (
            int(id(渲染器)),
            int(id(图)),
            int(图.get_width()),
            int(图.get_height()),
        )
        if self._GPU背景纹理 is not None and tuple(self._GPU背景纹理键) == tuple(缓存键):
            return self._GPU背景纹理
        try:
            纹理 = _sdl2_video.Texture.from_surface(渲染器, 图)
        except Exception:
            return None
        self._GPU背景纹理 = 纹理
        self._GPU背景纹理键 = tuple(缓存键)
        return 纹理

    def _取GPU背景遮罩纹理(self, 渲染器, alpha: int):
        if _sdl2_video is None or 渲染器 is None:
            return None
        alpha = int(max(0, min(255, alpha)))
        已有 = self._GPU背景遮罩纹理缓存.get(alpha)
        if 已有 is not None:
            return 已有
        try:
            图 = pygame.Surface((1, 1), pygame.SRCALPHA, 32)
            图.fill((0, 0, 0, alpha))
            纹理 = _sdl2_video.Texture.from_surface(渲染器, 图)
        except Exception:
            return None
        self._GPU背景遮罩纹理缓存[alpha] = 纹理
        return 纹理

    def _绘制GPU静态背景(
        self,
        渲染器,
        图: Optional[pygame.Surface],
        屏宽: int,
        屏高: int,
    ):
        纹理 = self._取GPU背景纹理(渲染器, 图)
        if 纹理 is None or 图 is None:
            return
        原宽 = int(max(1, 图.get_width()))
        原高 = int(max(1, 图.get_height()))
        比例 = max(float(屏宽) / float(原宽), float(屏高) / float(原高))
        新宽 = int(max(1, round(float(原宽) * 比例)))
        新高 = int(max(1, round(float(原高) * 比例)))
        x = int((屏宽 - 新宽) // 2)
        y = int((屏高 - 新高) // 2)
        try:
            纹理.draw(dstrect=(int(x), int(y), int(新宽), int(新高)))
        except Exception:
            pass

    def _应使用GPU界面(self) -> bool:
        if bool(getattr(self, "_选歌场景强制CPU绘制", False)):
            return False
        return bool(self._应使用GPU背景())

    def _同步GPU界面纹理缓存(self, 渲染器):
        当前渲染器id = int(id(渲染器))
        if 当前渲染器id == int(getattr(self, "_GPU界面纹理渲染器id", 0) or 0):
            return
        self._GPU界面纹理渲染器id = 当前渲染器id
        self._GPU界面纹理缓存 = {}

    def _取GPU界面纹理(self, 渲染器, 图: Optional[pygame.Surface]):
        if _sdl2_video is None or 渲染器 is None or not isinstance(图, pygame.Surface):
            return None
        self._同步GPU界面纹理缓存(渲染器)
        缓存键 = (
            int(id(图)),
            int(图.get_width()),
            int(图.get_height()),
            int(id(渲染器)),
        )
        已有 = self._GPU界面纹理缓存.get(缓存键)
        if 已有 is not None:
            return 已有
        try:
            纹理 = _sdl2_video.Texture.from_surface(渲染器, 图)
        except Exception:
            return None
        self._GPU界面纹理缓存[缓存键] = 纹理
        return 纹理

    def _清理GPU界面纹理(self, 图: Optional[pygame.Surface]):
        if not isinstance(图, pygame.Surface):
            return
        try:
            图id = int(id(图))
        except Exception:
            return
        删除键列表 = [
            键 for 键 in list(self._GPU界面纹理缓存.keys()) if int(键[0]) == 图id
        ]
        for 键 in 删除键列表:
            self._GPU界面纹理缓存.pop(键, None)

    def _绘制GPU图层(
        self,
        渲染器,
        图层: Optional[pygame.Surface],
        目标矩形: Optional[Tuple[int, int, int, int]] = None,
    ):
        if 图层 is None:
            return
        纹理 = self._取GPU界面纹理(渲染器, 图层)
        if 纹理 is None:
            return
        if 目标矩形 is None:
            目标矩形 = (0, 0, int(self.宽), int(self.高))
        try:
            纹理.draw(
                dstrect=(
                    int(目标矩形[0]),
                    int(目标矩形[1]),
                    int(目标矩形[2]),
                    int(目标矩形[3]),
                )
            )
        except Exception:
            pass

    def _按钮状态签名(self, 按钮对象) -> Tuple[object, ...]:
        if 按钮对象 is None:
            return ("none",)
        try:
            矩形 = getattr(按钮对象, "矩形", pygame.Rect(0, 0, 0, 0))
        except Exception:
            矩形 = pygame.Rect(0, 0, 0, 0)
        return (
            str(type(按钮对象).__name__),
            str(getattr(按钮对象, "图片路径", "") or ""),
            str(getattr(按钮对象, "底部文字", "") or ""),
            int(getattr(矩形, "x", 0) or 0),
            int(getattr(矩形, "y", 0) or 0),
            int(getattr(矩形, "w", 0) or 0),
            int(getattr(矩形, "h", 0) or 0),
            bool(getattr(按钮对象, "悬停", False)),
            bool(getattr(按钮对象, "按下", False)),
            bool(getattr(按钮对象, "是否水平翻转", False)),
            bool(getattr(按钮对象, "是否垂直翻转", False)),
            int(getattr(按钮对象, "透明度", 255) or 255),
        )

    def _取卡片缩略图封面缓存键(
        self, 卡片对象
    ) -> Optional[Tuple[str, int, int, int, str]]:
        if 卡片对象 is None:
            return None
        歌曲 = getattr(卡片对象, "歌曲", None)
        try:
            路径 = str(getattr(歌曲, "封面路径", "") or "")
        except Exception:
            路径 = ""
        if not 路径:
            return None
        try:
            矩形 = getattr(卡片对象, "矩形", pygame.Rect(0, 0, 0, 0))
        except Exception:
            矩形 = pygame.Rect(0, 0, 0, 0)

        框路径 = _资源路径("UI-img", "选歌界面资源", "缩略图小.png")
        局部布局 = 计算缩略图卡片布局(矩形, 框路径)
        封面矩形 = 局部布局["封面矩形"]
        return (
            路径,
            max(1, int(封面矩形.w)),
            max(1, int(封面矩形.h)),
            0,
            "cover",
        )

    def _卡片封面已就绪(self, 卡片对象) -> bool:
        缓存键 = self._取卡片缩略图封面缓存键(卡片对象)
        if not 缓存键:
            return False
        try:
            return isinstance(self.图缓存.获取(*缓存键), pygame.Surface)
        except Exception:
            return False

    def _当前页缺失封面数(self) -> int:
        缺失数 = 0
        for 卡片 in list(getattr(self, "当前页卡片", []) or []):
            缓存键 = self._取卡片缩略图封面缓存键(卡片)
            if not 缓存键:
                continue
            try:
                if self.图缓存.获取(*缓存键) is None:
                    缺失数 += 1
            except Exception:
                缺失数 += 1
        return int(缺失数)

    def _卡片状态签名(self, 卡片对象) -> Tuple[object, ...]:
        if 卡片对象 is None:
            return ("none",)
        歌曲 = getattr(卡片对象, "歌曲", None)
        矩形 = getattr(卡片对象, "矩形", pygame.Rect(0, 0, 0, 0))
        try:
            序号 = int(getattr(歌曲, "序号", 0) or 0)
        except Exception:
            序号 = 0
        return (
            str(getattr(歌曲, "sm路径", "") or ""),
            int(getattr(矩形, "x", 0) or 0),
            int(getattr(矩形, "y", 0) or 0),
            int(getattr(矩形, "w", 0) or 0),
            int(getattr(矩形, "h", 0) or 0),
            bool(self._卡片封面已就绪(卡片对象)),
            bool(getattr(卡片对象, "悬停", False)),
            bool(getattr(卡片对象, "踏板高亮", False)),
            int(序号),
        )

    def _取GPU顶栏层缓存键(self) -> Tuple[object, ...]:
        return (
            int(self.宽),
            int(self.高),
            bool(getattr(self, "是否收藏夹模式", False)),
            str(self.当前类型名() or ""),
            str(self.当前模式名() or ""),
        )

    def _取GPU底栏层缓存键(self) -> Tuple[object, ...]:
        状态 = self.上下文.get("状态", {}) if isinstance(self.上下文, dict) else {}
        return (
            int(self.宽),
            int(self.高),
            int(self.玩家数),
            int(状态.get("投币数", 0) or 0) if isinstance(状态, dict) else 0,
            bool(getattr(self, "是否详情页", False)),
            bool(getattr(self, "是否收藏夹模式", False)),
            self._按钮状态签名(getattr(self, "按钮_歌曲分类", None)),
            self._按钮状态签名(getattr(self, "按钮_收藏夹", None)),
            self._按钮状态签名(getattr(self, "按钮_ALL", None)),
            self._按钮状态签名(getattr(self, "按钮_2P加入", None)),
            self._按钮状态签名(getattr(self, "按钮_设置", None)),
            self._按钮状态签名(getattr(self, "按钮_重选模式", None)),
        )

    def _取GPU列表按钮层缓存键(self) -> Tuple[object, ...]:
        return (
            int(self.宽),
            int(self.高),
            bool(self._列表翻页按钮应显示()),
            self._按钮状态签名(getattr(self, "按钮_列表上一页", None)),
            self._按钮状态签名(getattr(self, "按钮_列表下一页", None)),
        )

    def _取GPU内容层缓存键(self) -> Tuple[object, ...]:
        return (
            "list",
            int(self.宽),
            int(self.高),
            self._取当前歌曲列表缓存键(),
            int(getattr(self, "当前页", 0) or 0),
            tuple(self._卡片状态签名(卡片) for 卡片 in list(getattr(self, "当前页卡片", []) or [])),
        )

    def _写入GPU列表页缓存(
        self, 缓存键: Tuple[object, ...], 图层: pygame.Surface
    ):
        try:
            self._GPU列表页缓存顺序.remove(缓存键)
        except Exception:
            pass

        self._GPU列表页缓存[缓存键] = 图层
        self._GPU列表页缓存顺序.append(缓存键)

        try:
            上限 = int(getattr(self, "_GPU列表页缓存上限", 6) or 6)
        except Exception:
            上限 = 6
        上限 = max(2, min(12, 上限))

        while len(self._GPU列表页缓存顺序) > 上限:
            旧键 = self._GPU列表页缓存顺序.pop(0)
            旧图层 = self._GPU列表页缓存.pop(旧键, None)
            self._清理GPU界面纹理(旧图层)

    def _取GPU列表页缓存键(
        self, 页码: int, 卡片列表: List[歌曲卡片]
    ) -> Tuple[object, ...]:
        return (
            "list_page",
            int(self.宽),
            int(self.高),
            self._取当前歌曲列表缓存键(),
            int(页码),
            tuple(self._卡片状态签名(卡片) for 卡片 in list(卡片列表 or [])),
        )

    def _在临时列表页上下文中执行(
        self, 页码: int, 卡片列表: List[歌曲卡片], 回调: Callable[[], object]
    ):
        原当前页 = getattr(self, "当前页", 0)
        原当前页卡片 = getattr(self, "当前页卡片", [])
        原详情页 = bool(getattr(self, "是否详情页", False))
        原动画中 = bool(getattr(self, "动画中", False))
        self.当前页 = int(页码)
        self.当前页卡片 = list(卡片列表 or [])
        self.是否详情页 = False
        self.动画中 = False
        try:
            return 回调()
        finally:
            self.当前页 = 原当前页
            self.当前页卡片 = 原当前页卡片
            self.是否详情页 = 原详情页
            self.动画中 = 原动画中

    def _构建GPU列表页层(
        self, 页码: int, 卡片列表: List[歌曲卡片]
    ) -> pygame.Surface:
        return self._在临时列表页上下文中执行(
            int(页码),
            list(卡片列表 or []),
            lambda: self._构建GPU界面层(lambda: self.绘制列表页()),
        )

    def _取GPU列表页层(
        self, 页码: int, 卡片列表: List[歌曲卡片]
    ) -> Optional[pygame.Surface]:
        缓存键 = self._取GPU列表页缓存键(int(页码), list(卡片列表 or []))
        已有 = self._GPU列表页缓存.get(缓存键)
        if isinstance(已有, pygame.Surface):
            self._写入GPU列表页缓存(缓存键, 已有)
            return 已有
        图层 = self._构建GPU列表页层(int(页码), list(卡片列表 or []))
        self._写入GPU列表页缓存(缓存键, 图层)
        return 图层

    def _取列表翻页动画偏移(self) -> Tuple[int, int]:
        try:
            动画持续 = float(max(0.001, getattr(self, "动画持续", 0.35) or 0.35))
        except Exception:
            动画持续 = 0.35
        try:
            t = (time.time() - float(getattr(self, "动画开始时间", 0.0) or 0.0)) / 动画持续
        except Exception:
            t = 1.0
        t = max(0.0, min(1.0, t))
        t2 = t * t * (3 - 2 * t)
        dx = int(self.中间区域.w * t2) * int(getattr(self, "动画方向", 0) or 0)
        旧偏移 = -dx
        新偏移 = (
            self.中间区域.w - dx
            if int(getattr(self, "动画方向", 0) or 0) > 0
            else -self.中间区域.w - dx
        )
        return int(旧偏移), int(新偏移)

    def _构建GPU界面层(self, 绘制回调: Callable[[], None]) -> pygame.Surface:
        画布 = pygame.Surface((int(self.宽), int(self.高)), pygame.SRCALPHA)
        画布.fill((0, 0, 0, 0))
        原屏幕 = self.屏幕
        self.屏幕 = 画布
        try:
            绘制回调()
        finally:
            self.屏幕 = 原屏幕
        return 画布

    def _确保GPU界面层缓存(self):
        顶栏键 = self._取GPU顶栏层缓存键()
        if self._GPU顶栏层缓存图 is None or self._GPU顶栏层缓存键 != 顶栏键:
            self._GPU顶栏层缓存图 = self._构建GPU界面层(lambda: self.绘制顶部())
            self._GPU顶栏层缓存键 = 顶栏键

        底栏键 = self._取GPU底栏层缓存键()
        if self._GPU底栏层缓存图 is None or self._GPU底栏层缓存键 != 底栏键:
            self._GPU底栏层缓存图 = self._构建GPU界面层(lambda: self.绘制底部())
            self._GPU底栏层缓存键 = 底栏键

        列表按钮键 = self._取GPU列表按钮层缓存键()
        if (
            self._GPU列表按钮层缓存图 is None
            or self._GPU列表按钮层缓存键 != 列表按钮键
        ):
            if self._列表翻页按钮应显示():
                self._GPU列表按钮层缓存图 = self._构建GPU界面层(
                    lambda: self._绘制列表翻页按钮()
                )
            else:
                self._GPU列表按钮层缓存图 = None
            self._GPU列表按钮层缓存键 = 列表按钮键

        内容键 = self._取GPU内容层缓存键()
        if self._GPU内容层缓存图 is None or self._GPU内容层缓存键 != 内容键:
            self._GPU内容层缓存图 = self._取GPU列表页层(
                int(getattr(self, "当前页", 0) or 0),
                list(getattr(self, "当前页卡片", []) or []),
            )
            self._GPU内容层缓存键 = 内容键

        if bool(getattr(self, "动画中", False)):
            self._取GPU列表页层(
                int(getattr(self, "当前页", 0) or 0),
                list(getattr(self, "动画旧页卡片", []) or []),
            )
            self._取GPU列表页层(
                int(getattr(self, "动画目标页", 0) or 0),
                list(getattr(self, "动画新页卡片", []) or []),
            )

    def _合成GPU动画列表页到画布(self, 画布: pygame.Surface):
        if not isinstance(画布, pygame.Surface):
            return
        旧图层 = getattr(self, "_GPU翻页旧页层图", None)
        新图层 = getattr(self, "_GPU翻页新页层图", None)
        if not isinstance(旧图层, pygame.Surface):
            旧图层 = self._取GPU列表页层(
                int(getattr(self, "当前页", 0) or 0),
                list(getattr(self, "动画旧页卡片", []) or []),
            )
        if not isinstance(新图层, pygame.Surface):
            新图层 = self._取GPU列表页层(
                int(getattr(self, "动画目标页", 0) or 0),
                list(getattr(self, "动画新页卡片", []) or []),
            )
        旧偏移, 新偏移 = self._取列表翻页动画偏移()
        for 图层, 偏移 in ((旧图层, 旧偏移), (新图层, 新偏移)):
            if isinstance(图层, pygame.Surface):
                try:
                    画布.blit(图层, (int(偏移), 0))
                except Exception:
                    continue

    def _绘制GPU动画列表页(self, 渲染器):
        旧图层 = getattr(self, "_GPU翻页旧页层图", None)
        新图层 = getattr(self, "_GPU翻页新页层图", None)
        if not isinstance(旧图层, pygame.Surface):
            旧图层 = self._取GPU列表页层(
                int(getattr(self, "当前页", 0) or 0),
                list(getattr(self, "动画旧页卡片", []) or []),
            )
        if not isinstance(新图层, pygame.Surface):
            新图层 = self._取GPU列表页层(
                int(getattr(self, "动画目标页", 0) or 0),
                list(getattr(self, "动画新页卡片", []) or []),
            )
        旧偏移, 新偏移 = self._取列表翻页动画偏移()
        self._绘制GPU图层(
            渲染器,
            旧图层,
            目标矩形=(int(旧偏移), 0, int(self.宽), int(self.高)),
        )
        self._绘制GPU图层(
            渲染器,
            新图层,
            目标矩形=(int(新偏移), 0, int(self.宽), int(self.高)),
        )

    def _合成GPU界面到画布(self, 画布: pygame.Surface):
        if not isinstance(画布, pygame.Surface):
            return
        self._确保GPU界面层缓存()
        for 图层 in (getattr(self, "_GPU顶栏层缓存图", None),):
            if isinstance(图层, pygame.Surface):
                try:
                    画布.blit(图层, (0, 0))
                except Exception:
                    continue
        if bool(getattr(self, "动画中", False)) and (
            not bool(getattr(self, "是否详情页", False))
        ):
            self._合成GPU动画列表页到画布(画布)
            图层序列 = (
                getattr(self, "_GPU列表按钮层缓存图", None),
                getattr(self, "_GPU底栏层缓存图", None),
            )
        else:
            图层序列 = (getattr(self, "_GPU内容层缓存图", None),)
            if not bool(getattr(self, "是否详情页", False)):
                图层序列 += (getattr(self, "_GPU列表按钮层缓存图", None),)
            图层序列 += (getattr(self, "_GPU底栏层缓存图", None),)
        for 图层 in 图层序列:
            if isinstance(图层, pygame.Surface):
                try:
                    画布.blit(图层, (0, 0))
                except Exception:
                    continue

    def 绘制GPU背景(self, 显示后端):
        if not self._应使用GPU背景():
            return
        if _sdl2_video is None:
            return
        取渲染器 = getattr(显示后端, "取GPU渲染器", None)
        if not callable(取渲染器):
            return
        渲染器 = 取渲染器()
        if 渲染器 is None:
            return
        try:
            屏宽, 屏高 = tuple(int(v) for v in 显示后端.取绘制屏幕().get_size())
        except Exception:
            return

        self._同步GPU背景缓存(渲染器)
        背景模式 = self._取背景渲染模式()
        已绘制背景 = False
        if 背景模式 == "动态背景":
            管理器 = getattr(self, "_动态背景管理器", None)
            if 管理器 is not None:
                self._同步动态背景管理器(False)
                try:
                    管理器.render(
                        self._取动态背景模式(),
                        DynamicBackgroundContext(
                            renderer=渲染器,
                            screen_size=(int(屏宽), int(屏高)),
                            combo=0,
                            now=float(time.perf_counter()),
                            delta_time=0.0,
                            resource_root=str(getattr(管理器, "resource_root", "") or ""),
                            runtime_root=str(getattr(管理器, "runtime_root", "") or ""),
                            project_root=str(getattr(管理器, "project_root", "") or ""),
                        ),
                    )
                    已绘制背景 = True
                except Exception:
                    已绘制背景 = False
        if (not 已绘制背景) and isinstance(self.背景图_原图, pygame.Surface):
            self._绘制GPU静态背景(渲染器, self.背景图_原图, int(屏宽), int(屏高))

        遮罩纹理 = self._取GPU背景遮罩纹理(
            渲染器,
            int(getattr(self, "_背景遮罩alpha", 60) or 60),
        )
        if 遮罩纹理 is not None:
            try:
                遮罩纹理.draw(dstrect=(0, 0, int(屏宽), int(屏高)))
            except Exception:
                pass

    def 绘制GPU中层(self, 显示后端):
        if not self._应使用GPU界面():
            return
        if _sdl2_video is None:
            return
        取渲染器 = getattr(显示后端, "取GPU渲染器", None)
        if not callable(取渲染器):
            return
        渲染器 = 取渲染器()
        if 渲染器 is None:
            return
        try:
            self._确保GPU界面层缓存()
            self._绘制GPU图层(渲染器, getattr(self, "_GPU顶栏层缓存图", None))
            if bool(getattr(self, "动画中", False)) and (not bool(getattr(self, "是否详情页", False))):
                self._绘制GPU动画列表页(渲染器)
                self._绘制GPU图层(渲染器, getattr(self, "_GPU列表按钮层缓存图", None))
            else:
                self._绘制GPU图层(渲染器, getattr(self, "_GPU内容层缓存图", None))
                if not bool(getattr(self, "是否详情页", False)):
                    self._绘制GPU图层(渲染器, getattr(self, "_GPU列表按钮层缓存图", None))
            self._绘制GPU图层(渲染器, getattr(self, "_GPU底栏层缓存图", None))
        except Exception:
            pass

    def _确保top栏缓存(self):
        self._确保top栏资源()

        w, h = self.屏幕.get_size()
        当前模式 = bool(getattr(self, "是否收藏夹模式", False))
        if (
            getattr(self, "_top缓存尺寸", (0, 0)) == (w, h)
            and getattr(self, "_top缓存模式", None) == 当前模式
        ):
            return
        self._top缓存尺寸 = (w, h)
        self._top缓存模式 = 当前模式

        if 当前模式 and getattr(self, "_top中间标题图_收藏夹", None) is not None:
            标题原图 = self._top中间标题图_收藏夹
        else:
            标题原图 = getattr(self, "_top中间标题图_歌曲选择", None) or self._top中间标题原图

        # ✅ 用 ui/top栏.py 统一生成 top 栏（中间标题用 歌曲选择.png）
        self._top_rect, self._top图, self._top标题rect, self._top标题图 = 生成top栏(
            屏幕=self.屏幕,
            top背景原图=self._top栏背景原图,
            标题原图=标题原图,
            设计宽=self._设计宽,
            设计高=self._设计高,
            top设计高=150,
            top背景宽占比=1.0,
            top背景高占比=1.0,
            标题最大宽占比=0.5,
            标题最大高占比=0.5,
            标题整体缩放=1.0,
            标题上移比例=0.1,
        )

        # ✅ 让布局用 top 真高度（避免你中间区域算错）
        self.顶部高 = max(78, int(self._top_rect.h))

    def _确保top栏资源(self):
        if getattr(self, "_top资源已初始化", False):
            return

        self._top资源已初始化 = True

        # ===== 设计基准（给 ui/top栏.py 缩放用）=====
        if not hasattr(self, "_设计宽"):
            self._设计宽 = 2048
        if not hasattr(self, "_设计高"):
            self._设计高 = 1152

        # ===== top栏背景（统一皮肤）=====
        self._top栏背景原图 = None
        try:
            路径 = _资源路径("UI-img", "top栏", "top栏背景.png")
            if os.path.isfile(路径):
                self._top栏背景原图 = pygame.image.load(路径).convert_alpha()
        except Exception:
            self._top栏背景原图 = None

        # ===== 中间标题：歌曲选择.png =====
        self._top中间标题原图 = None
        self._top中间标题图_歌曲选择 = None
        self._top中间标题图_收藏夹 = None
        try:
            路径 = _资源路径("UI-img", "top栏", "歌曲选择.png")
            if os.path.isfile(路径):
                self._top中间标题原图 = pygame.image.load(路径).convert_alpha()
                self._top中间标题图_歌曲选择 = self._top中间标题原图
        except Exception:
            self._top中间标题原图 = None
            self._top中间标题图_歌曲选择 = None

        # ===== 中间标题：收藏夹.png =====
        try:
            路径 = _资源路径("UI-img", "top栏", "收藏夹.png")
            if os.path.isfile(路径):
                self._top中间标题图_收藏夹 = pygame.image.load(路径).convert_alpha()
        except Exception:
            self._top中间标题图_收藏夹 = None

        # ===== 左上角：类型/模式 图片绑定表 =====
        # 类型（大模式）
        self._top类型图片路径表 = {
            "花式": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "大模式-花式.png"),
            "竞速": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "大模式-竞速.png"),
            "派对": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "大模式-派对模式.png"),
            "diy": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "大模式-diy.png"),
            "wef": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "大模式-wef.png"),
        }

        # 模式（子模式）
        self._top模式图片路径表 = {
            "表演": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "表演模式.png"),
            "学习": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "学习模式.png"),
            "疯狂": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "疯狂模式.png"),
            "混音": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "混音模式.png"),
            "情侣": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "情侣模式.png"),
            "club": _资源路径("UI-img", "选歌界面资源", "top栏小标题", "双踏板模式.png"),
        }

        # ===== 缓存 =====
        self._top小标题原图缓存 = {}  # 路径 -> 原图
        self._top小标题缩放缓存 = {}  # (路径, 目标高, 额外缩放) -> 缩放后图

        # =========================================================
        # ✅ 手动可调参数（你要调位置/缩放就改这里）
        # =========================================================
        self._top左上_x屏宽占比 = 0.10  # ✅ 整体向右移动屏宽10%
        self._top左上_y像素 = 0  # ✅ 纵轴=0（贴top上边）
        self._top类型模式间距 = 13  # ✅ 类型图 与 模式图 之间的间距

        self._top小标题目标高占比 = (
            0.45  # 相对top栏高度的目标高度（先自动fit，再乘手动缩放）
        )
        self._top类型_缩放 = 1.10
        self._top模式_缩放 = 1.10
        self._top类型_偏移 = (0, 0)  # (dx, dy)
        self._top模式_偏移 = (0, 0)

        # 可选：按“具体类型/模式”覆盖缩放和偏移（你后面发现某张图偏大/偏小就填这里）
        self._top类型_缩放覆盖 = {}  # 例：{"派对": 0.92}
        self._top类型_偏移覆盖 = {}  # 例：{"派对": (0, 2)}
        self._top模式_缩放覆盖 = {}  # 例：{"club": 0.90}
        self._top模式_偏移覆盖 = {}  # 例：{"club": (0, 1)}

    def _归一化类型名(self, 类型名: str) -> str:
        s = str(类型名 or "").strip()
        低 = s.lower()

        if "花" in s or "fancy" in 低:
            return "花式"
        if "竞" in s or "speed" in 低:
            return "竞速"
        if "派对" in s or "party" in 低:
            return "派对"
        if "diy" in 低:
            return "diy"
        if "wef" in 低:
            return "wef"

        # 兜底：就返回原字符串（后面会走“缺图->文字”）
        return s

    def _归一化模式名(self, 模式名: str) -> str:
        s = str(模式名 or "").strip()
        低 = s.lower()

        if "表演" in s or "show" in 低:
            return "表演"
        if "学习" in s or "learn" in 低:
            return "学习"
        if "疯狂" in s or "crazy" in 低:
            return "疯狂"
        if "混音" in s or "mix" in 低:
            return "混音"
        if "情侣" in s or "lover" in 低:
            return "情侣"
        if "club" in 低 or "双踏板" in s:
            return "club"

        return s

    def _夹紧矩形到top内部(self, r: pygame.Rect) -> pygame.Rect:
        """
        保证左上角小标题永远“包裹在top背景内部”
        """
        top = getattr(self, "_top_rect", pygame.Rect(0, 0, self.宽, 100))
        rr = r.copy()

        if rr.w > top.w:
            rr.w = top.w
        if rr.h > top.h:
            rr.h = top.h

        rr.x = max(top.left, min(rr.x, top.right - rr.w))
        rr.y = max(top.top, min(rr.y, top.bottom - rr.h))
        return rr

    def _获取top小标题图(
        self,
        路径: str,
        目标高: int,
        额外缩放: float,
        最大宽: Optional[int] = None,
    ) -> Optional[pygame.Surface]:
        if not 路径 or (not os.path.isfile(路径)):
            return None

        # ✅ 全局：所有小标题图“宽度额外加宽 1.3 倍”
        全局宽度加宽 = 1.30

        最大宽值 = int(最大宽) if 最大宽 is not None else -1
        key = (路径, int(目标高), float(额外缩放), 最大宽值, float(全局宽度加宽))
        if key in self._top小标题缩放缓存:
            return self._top小标题缩放缓存.get(key)

        原图 = self._top小标题原图缓存.get(路径)
        if 原图 is None:
            try:
                原图 = pygame.image.load(路径).convert_alpha()
            except Exception:
                原图 = None
            self._top小标题原图缓存[路径] = 原图

        if 原图 is None:
            self._top小标题缩放缓存[key] = None
            return None

        ow, oh = 原图.get_size()
        if ow <= 0 or oh <= 0:
            self._top小标题缩放缓存[key] = None
            return None

        # ✅ 先按目标高 fit，再乘你的“额外缩放”
        比例 = (float(目标高) / float(oh)) * float(额外缩放)
        nw = max(1, int(ow * 比例))
        nh = max(1, int(oh * 比例))

        # ✅ 统一加宽：只改宽，不改高
        nw = max(1, int(nw * float(全局宽度加宽)))

        # ✅ 宽限制：超出可用宽就等比缩小（避免被裁切）
        if 最大宽值 and 最大宽值 > 0 and nw > 最大宽值:
            缩比 = float(最大宽值) / float(max(1, nw))
            nw = 最大宽值
            nh = max(1, int(nh * 缩比))  # 这里会影响高度（为避免裁切必须等比缩）

        try:
            缩放图 = pygame.transform.smoothscale(原图, (nw, nh)).convert_alpha()
        except Exception:
            缩放图 = None

        self._top小标题缩放缓存[key] = 缩放图
        return 缩放图

    def _重算星级筛选页布局(self):
        面板宽 = min(920, int(self.宽 * 0.78))
        面板高 = min(620, int(self.高 * 0.70))
        面板x = (self.宽 - 面板宽) // 2
        面板y = (self.高 - 面板高) // 2
        self.筛选页面板矩形 = pygame.Rect(面板x, 面板y, 面板宽, 面板高)

        self.星级按钮列表.clear()

        # ✅ 只取“当前模式目录真实存在”的星级
        原始 = self.当前原始歌曲列表()
        星集合: List[int] = []
        try:
            星集合 = sorted(
                {max(1, min(20, int(getattr(歌, "星级", 0) or 0))) for 歌 in 原始}
            )
        except Exception:
            星集合 = []

        if not 星集合:
            星集合 = [1, 2, 3, 4, 5]

        内边距 = 26
        区域 = self.筛选页面板矩形.inflate(-内边距 * 2, -内边距 * 2)

        标题区高 = 120
        可用 = pygame.Rect(
            区域.x, 区域.y + 标题区高, 区域.w, max(10, 区域.h - 标题区高)
        )

        # ✅ 统一按钮宽高（与星级数量无关，避免“只有4个星级时按钮巨大”）
        按钮宽 = max(120, min(190, int(可用.w * 0.18)))
        按钮高 = max(86, int(按钮宽 * 0.70))
        间距 = max(12, int(按钮宽 * 0.10))

        # ✅ 浮动布局：能放几列放几列，自动换行
        列数 = int((可用.w + 间距) // (按钮宽 + 间距))
        列数 = max(1, min(列数, len(星集合)))

        总数 = len(星集合)
        行数 = int(math.ceil(总数 / max(1, 列数)))

        总高 = 行数 * 按钮高 + max(0, 行数 - 1) * 间距
        起点y = 可用.y + max(0, (可用.h - 总高) // 2)

        索引 = 0
        for 行 in range(行数):
            本行剩余 = 总数 - 索引
            本行数量 = min(列数, max(0, 本行剩余))
            if 本行数量 <= 0:
                break

            本行总宽 = 本行数量 * 按钮宽 + max(0, 本行数量 - 1) * 间距
            起点x = 可用.centerx - 本行总宽 // 2

            y = 起点y + 行 * (按钮高 + 间距)
            for 列 in range(本行数量):
                星 = int(星集合[索引])
                x = 起点x + 列 * (按钮宽 + 间距)
                b = 星级筛选按钮(self, 星, pygame.Rect(x, y, 按钮宽, 按钮高))
                self.星级按钮列表.append((星, b))
                索引 += 1

    def _取页卡片缓存键(
        self, 页码: int, 每页数量: int
    ) -> Tuple[object, ...]:
        try:
            布局版本 = float(_选歌布局_修改时间)
        except Exception:
            布局版本 = -1.0

        return (
            self._取当前歌曲列表缓存键(),
            int(页码),
            int(每页数量),
            int(getattr(self.中间区域, "x", 0) or 0),
            int(getattr(self.中间区域, "y", 0) or 0),
            int(getattr(self.中间区域, "w", 0) or 0),
            int(getattr(self.中间区域, "h", 0) or 0),
            float(布局版本),
        )

    def _重置页卡片瞬时状态(self, 卡片列表: List[歌曲卡片]):
        for 卡片 in 卡片列表:
            try:
                卡片.悬停 = False
                卡片.踏板高亮 = False
            except Exception:
                pass

    def _写入页卡片缓存(
        self, 缓存键: Tuple[object, ...], 卡片列表: List[歌曲卡片]
    ):
        try:
            self._页卡片缓存顺序.remove(缓存键)
        except Exception:
            pass

        self._页卡片缓存[缓存键] = 卡片列表
        self._页卡片缓存顺序.append(缓存键)

        try:
            上限 = int(getattr(self, "_页卡片缓存上限", 10) or 10)
        except Exception:
            上限 = 10
        上限 = max(2, min(24, 上限))

        while len(self._页卡片缓存顺序) > 上限:
            旧键 = self._页卡片缓存顺序.pop(0)
            self._页卡片缓存.pop(旧键, None)

    def 生成指定页卡片(self, 页码: int) -> List[歌曲卡片]:
        列表, _映射 = self.当前歌曲列表与映射()
        if not 列表:
            return []

        try:
            列数 = int(self._取布局值("卡片网格.列数", 4))
        except Exception:
            列数 = 4
        try:
            行数 = int(self._取布局值("卡片网格.行数", 2))
        except Exception:
            行数 = 2
        列数 = max(1, min(12, 列数))
        行数 = max(1, min(12, 行数))

        self.每页数量 = int(列数 * 行数)
        缓存键 = self._取页卡片缓存键(int(页码), int(self.每页数量))
        缓存卡片 = self._页卡片缓存.get(缓存键)
        if isinstance(缓存卡片, list) and 缓存卡片:
            self._重置页卡片瞬时状态(缓存卡片)
            self._写入页卡片缓存(缓存键, 缓存卡片)
            return 缓存卡片

        外留白 = self._取布局像素("卡片网格.外留白", 70, 最小=0, 最大=9999)
        上下留白 = self._取布局像素("卡片网格.上下留白", 36, 最小=0, 最大=9999)

        原间距x = self._取布局像素("卡片网格.原卡片间距x", 44, 最小=0, 最大=9999)
        原间距y = self._取布局像素("卡片网格.原卡片间距y", 26, 最小=0, 最大=9999)

        倍率x = self._取布局值("卡片网格.间距x倍率", 2.0)
        倍率y = self._取布局值("卡片网格.间距y倍率", 3.0)
        try:
            倍率x = float(倍率x)
        except Exception:
            倍率x = 2.0
        try:
            倍率y = float(倍率y)
        except Exception:
            倍率y = 3.0
        倍率x = max(0.0, min(10.0, 倍率x))
        倍率y = max(0.0, min(10.0, 倍率y))

        卡片间距x = int(原间距x * 倍率x)
        卡片间距y = int(原间距y * 倍率y)

        区域最小宽 = self._取布局像素("卡片网格.区域最小宽", 500, 最小=200, 最大=9999)
        区域最小高 = self._取布局像素("卡片网格.区域最小高", 200, 最小=120, 最大=9999)
        兜底留白 = self._取布局像素("卡片网格.区域兜底留白", 40, 最小=0, 最大=9999)

        原卡片宽最小 = self._取布局像素(
            "卡片网格.原卡片宽最小", 140, 最小=60, 最大=9999
        )
        原卡片高最小 = self._取布局像素(
            "卡片网格.原卡片高最小", 120, 最小=60, 最大=9999
        )

        宽缩放 = self._取布局值("卡片网格.卡片宽缩放", 0.95)
        高缩放 = self._取布局值("卡片网格.卡片高缩放", 1.00)
        try:
            宽缩放 = float(宽缩放)
        except Exception:
            宽缩放 = 0.95
        try:
            高缩放 = float(高缩放)
        except Exception:
            高缩放 = 1.00
        宽缩放 = max(0.30, min(1.50, 宽缩放))
        高缩放 = max(0.30, min(1.50, 高缩放))

        卡片宽最小 = self._取布局像素("卡片网格.卡片宽最小", 120, 最小=40, 最大=9999)
        卡片高最小 = self._取布局像素("卡片网格.卡片高最小", 110, 最小=40, 最大=9999)

        上移占比 = self._取布局值("卡片网格.整体上移占比", 0.05)
        try:
            上移占比 = float(上移占比)
        except Exception:
            上移占比 = 0.05
        上移占比 = max(-0.50, min(0.50, 上移占比))
        网格配置 = _卡片网格配置模块(
            columns=int(列数),
            rows=int(行数),
            outer_padding=int(外留白),
            vertical_padding=int(上下留白),
            gap_x=int(卡片间距x),
            gap_y=int(卡片间距y),
            min_region_w=int(区域最小宽),
            min_region_h=int(区域最小高),
            fallback_padding=int(兜底留白),
            min_raw_card_w=int(原卡片宽最小),
            min_raw_card_h=int(原卡片高最小),
            card_scale_x=float(宽缩放),
            card_scale_y=float(高缩放),
            min_card_w=int(卡片宽最小),
            min_card_h=int(卡片高最小),
            vertical_shift_ratio=float(上移占比),
        )
        卡片矩形列表 = _构建卡片网格矩形模块(
            container_rect=self.中间区域,
            page_index=int(页码),
            page_size=int(self.每页数量),
            total_items=len(列表),
            config=网格配置,
        )
        起始索引 = int(页码) * int(self.每页数量)
        卡片列表 = [
            歌曲卡片(列表[起始索引 + idx], pygame.Rect(矩形))
            for idx, 矩形 in enumerate(卡片矩形列表)
            if (起始索引 + idx) < len(列表)
        ]

        self._写入页卡片缓存(缓存键, 卡片列表)
        return 卡片列表

    def _取预加载页顺序(self, 基准页: int) -> List[int]:
        try:
            总页数 = int(self.总页数())
        except Exception:
            总页数 = 1
        return _构建预加载页顺序模块(
            base_page=int(基准页),
            total_pages=int(总页数),
        )

    def _收集预加载封面键列表(
        self, 基准页: int
    ) -> List[Tuple[str, int, int, int, str]]:
        刷新选歌布局常量()

        列表, _映射 = self.当前歌曲列表与映射()
        if not 列表:
            return []

        框路径 = _资源路径("UI-img", "选歌界面资源", "缩略图小.png")
        try:
            总页数 = int(self.总页数())
        except Exception:
            总页数 = 1
        需要保留键列表 = _收集预加载封面键列表模块(
            base_page=int(基准页),
            total_pages=int(总页数),
            get_cards_for_page=self.生成指定页卡片,
            get_card_cover_path=lambda 卡片: str(
                getattr(getattr(卡片, "歌曲", None), "封面路径", "") or ""
            ),
            get_card_rect=lambda 卡片: getattr(卡片, "矩形", pygame.Rect(0, 0, 0, 0)),
            frame_path=框路径,
            get_ui_image=获取UI原图,
            frame_scale_x=_缩略图小框_宽缩放,
            frame_scale_y=_缩略图小框_高缩放,
            frame_x_offset=_缩略图小框_x偏移,
            frame_y_offset_ratio=_缩略图小框_y偏移,
            target_ratio=4.0 / 3.0,
            slot_params=dict(_缩略图槽位参数),
            small_visible_bottom_px=float(_缩略图可视底设计像素),
            small_frame_design_height=float(_缩略图框体设计高),
            small_info_anchor=str(_缩略图信息条锚点),
        )
        已收录键集合: Set[Tuple[str, int, int, int, str]] = set(需要保留键列表)

        if bool(getattr(self, "是否详情页", False)):
            原始列表 = self.当前原始歌曲列表()
            try:
                当前索引 = int(getattr(self, "当前选择原始索引", 0) or 0)
            except Exception:
                当前索引 = 0

            if 0 <= 当前索引 < len(原始列表):
                当前歌曲 = 原始列表[当前索引]
                try:
                    大图路径 = str(getattr(当前歌曲, "封面路径", "") or "")
                except Exception:
                    大图路径 = ""

                if 大图路径 and os.path.isfile(大图路径):
                    try:
                        当前大框 = getattr(self, "详情大框矩形", None)
                        if not isinstance(当前大框, pygame.Rect):
                            当前大框 = None
                    except Exception:
                        当前大框 = None

                    try:
                        最后缩放 = float(getattr(self, "_详情浮层_最后缩放", 1.0) or 1.0)
                    except Exception:
                        最后缩放 = 1.0
                    最后缩放 = max(0.001, 最后缩放)

                    if 当前大框 is not None and 当前大框.w > 10 and 当前大框.h > 10:
                        基础宽 = max(10, int(round(float(当前大框.w) / 最后缩放)))
                        基础高 = max(10, int(round(float(当前大框.h) / 最后缩放)))

                        框基础矩形 = pygame.Rect(0, 0, 基础宽, 基础高)
                        布局 = 计算框体槽位布局(框基础矩形, 是否大图=True)
                        封面矩形 = 布局["封面矩形"]

                        缓存键 = (
                            大图路径,
                            max(1, int(封面矩形.w)),
                            max(1, int(封面矩形.h)),
                            0,
                            "stretch",
                        )
                        if 缓存键 not in 已收录键集合:
                            已收录键集合.add(缓存键)
                            需要保留键列表.append(缓存键)

        return 需要保留键列表


    def 安排预加载(self, 基准页: int):
        列表, _映射 = self.当前歌曲列表与映射()
        if not 列表:
            self.预加载队列 = deque()
            self._预加载_已排队 = set()
            self._待清理保留key集合 = set()
            self.图缓存.清理远端(set())
            return

        需要key列表 = self._收集预加载封面键列表(int(基准页))
        需要key集合 = set(需要key列表)
        新队列 = deque()

        for 路径, w, h, 圆角, 模式 in 需要key列表:
            if self.图缓存.获取(路径, w, h, 圆角, 模式) is None:
                新队列.append((路径, w, h, 圆角, 模式))

        self.预加载队列 = 新队列
        self._预加载_已排队 = set(新队列)
        self._待清理保留key集合 = 需要key集合

        if not self.预加载队列 and self._待清理保留key集合 is not None:
            self.图缓存.清理远端(self._待清理保留key集合)
            self._待清理保留key集合 = None

    def 每帧执行预加载(self, 每帧数量: int = 3):
        if not hasattr(self, "_预加载_已排队"):
            self._预加载_已排队 = set()

        if bool(getattr(self, "动画中", False)):
            return

        try:
            每帧数量 = int(每帧数量)
        except Exception:
            每帧数量 = 3
        每帧数量 = max(1, min(30, 每帧数量))

        当前页缺失封面数 = self._当前页缺失封面数()
        if 当前页缺失封面数 > 0:
            每帧数量 = max(每帧数量, min(12, max(4, 当前页缺失封面数)))

        try:
            当前类型小写 = str(self.当前类型名() or "").strip().lower()
        except Exception:
            当前类型小写 = ""
        if (
            当前类型小写 == "diy"
            and (not bool(getattr(self, "动画中", False)))
            and bool(self.预加载队列)
        ):
            每帧数量 = max(每帧数量, 5)

        for _ in range(每帧数量):
            if not self.预加载队列:
                break

            路径, w, h, 圆角, 模式 = self.预加载队列.popleft()

            try:
                self._预加载_已排队.discard(
                    (路径, int(w), int(h), int(圆角), str(模式))
                )
            except Exception:
                pass

            if self.图缓存.获取(路径, w, h, 圆角, 模式) is not None:
                continue

            图 = 载入并缩放封面(路径, w, h, 圆角, 模式)
            if 图:
                self.图缓存.写入(路径, w, h, 圆角, 模式, 图)

        if (not self.预加载队列) and (self._待清理保留key集合 is not None):
            self.图缓存.清理远端(self._待清理保留key集合)
            self._待清理保留key集合 = None

    def 触发翻页动画(self, 目标页: int, 方向: int):
        if self.动画中 or self.是否星级筛选页:
            return

        总 = self.总页数()
        if 总 <= 1:
            return

        try:
            目标页 = int(目标页)
        except Exception:
            目标页 = self.当前页

        # ✅ 环绕：第一页往上滚/右滑 -> 末页；末页往下滚/左滑 -> 首页
        if 目标页 < 0:
            目标页 = 总 - 1
        elif 目标页 >= 总:
            目标页 = 0

        if 目标页 == self.当前页:
            return

        self._播放翻页音效()
        self.动画中 = True
        self.动画开始时间 = time.time()
        self.动画方向 = (
            int(方向) if int(方向) != 0 else (1 if 目标页 > self.当前页 else -1)
        )
        self.动画目标页 = 目标页

        self.动画旧页卡片 = list(getattr(self, "当前页卡片", []) or [])
        self.动画新页卡片 = self.生成指定页卡片(self.动画目标页)
        self._GPU翻页旧页层图 = None
        self._GPU翻页新页层图 = None
        if bool(getattr(self, "_应使用GPU界面", lambda: False)()):
            self._GPU翻页旧页层图 = self._取GPU列表页层(
                int(getattr(self, "当前页", 0) or 0),
                list(getattr(self, "动画旧页卡片", []) or []),
            )
            self._GPU翻页新页层图 = self._取GPU列表页层(
                int(getattr(self, "动画目标页", 0) or 0),
                list(getattr(self, "动画新页卡片", []) or []),
            )

    def 更新动画状态(self):
        if not self.动画中:
            return
        经过 = time.time() - self.动画开始时间
        if 经过 >= self.动画持续:
            self.动画中 = False
            self._GPU翻页旧页层图 = None
            self._GPU翻页新页层图 = None
            self.当前页 = self.动画目标页
            self.当前页卡片 = list(getattr(self, "动画新页卡片", []) or [])
            if not self.当前页卡片:
                self.当前页卡片 = self.生成指定页卡片(self.当前页)
            self.安排预加载(基准页=self.当前页)

    def _确保翻页交互状态(self):
        if getattr(self, "_翻页交互已初始化", False):
            return
        self._翻页交互已初始化 = True
        self._滑动_按下 = False
        self._滑动_起点 = (0, 0)
        self._滑动_已触发 = False
        self._滑动_已移动 = False
        self._连续翻页激活 = False
        self._连续翻页方向 = 0
        self._连续翻页来源 = ""
        self._连续翻页下次触发秒 = 0.0
        self._连续翻页首次延迟秒 = 0.26
        self._连续翻页间隔秒 = 0.03

    def _停止连续翻页(self):
        self._确保翻页交互状态()
        来源 = str(getattr(self, "_连续翻页来源", "") or "")
        if 来源 in ("list_page_button_left", "list_page_button_right"):
            for 按钮对象 in (
                getattr(self, "按钮_列表上一页", None),
                getattr(self, "按钮_列表下一页", None),
            ):
                if isinstance(按钮对象, 图片按钮):
                    按钮对象.按下 = False
        self._连续翻页激活 = False
        self._连续翻页方向 = 0
        self._连续翻页来源 = ""
        self._连续翻页下次触发秒 = 0.0

    def _触发列表翻页(self, 步数: int):
        try:
            步数 = int(步数)
        except Exception:
            步数 = 0
        if 步数 == 0:
            return

        总页数 = int(self.总页数())
        if 总页数 <= 1:
            return

        目标页 = (int(self.当前页) + int(步数)) % int(总页数)
        方向 = 1 if int(步数) > 0 else -1
        self.触发翻页动画(目标页=目标页, 方向=方向)

    def _开始连续翻页(self, 方向: int, 来源: str, 立即触发: bool = True):
        self._确保翻页交互状态()
        方向 = 1 if int(方向) > 0 else -1
        if (
            bool(getattr(self, "_连续翻页激活", False))
            and int(getattr(self, "_连续翻页方向", 0) or 0) == int(方向)
            and str(getattr(self, "_连续翻页来源", "") or "") == str(来源 or "")
        ):
            return
        self._连续翻页激活 = True
        self._连续翻页方向 = int(方向)
        self._连续翻页来源 = str(来源 or "")
        当前秒 = float(time.perf_counter())
        self._连续翻页下次触发秒 = 当前秒 + float(
            getattr(self, "_连续翻页首次延迟秒", 0.26)
        )
        if 立即触发:
            self._触发列表翻页(int(方向))

    def _更新连续翻页(self):
        self._确保翻页交互状态()
        if not bool(getattr(self, "_连续翻页激活", False)):
            return
        来源 = str(getattr(self, "_连续翻页来源", "") or "")
        if 来源 == "keyboard":
            try:
                按键状态 = pygame.key.get_pressed()
            except Exception:
                按键状态 = None
            方向 = int(getattr(self, "_连续翻页方向", 0) or 0)
            是否仍按住 = bool(
                按键状态
                and (
                    按键状态[pygame.K_LEFT]
                    if int(方向) < 0
                    else 按键状态[pygame.K_RIGHT]
                )
            )
            if not bool(是否仍按住):
                self._停止连续翻页()
                return
        elif 来源 in ("list_page_button_left", "list_page_button_right"):
            try:
                鼠标状态 = pygame.mouse.get_pressed(3)
            except Exception:
                鼠标状态 = None
            if not bool(鼠标状态 and 鼠标状态[0]):
                self._停止连续翻页()
                return
        if bool(getattr(self, "动画中", False)):
            return
        if bool(getattr(self, "是否详情页", False)):
            self._停止连续翻页()
            return
        if bool(getattr(self, "是否星级筛选页", False)) or bool(
            getattr(self, "是否设置页", False)
        ):
            self._停止连续翻页()
            return

        当前秒 = float(time.perf_counter())
        if 当前秒 < float(getattr(self, "_连续翻页下次触发秒", 0.0) or 0.0):
            return

        self._触发列表翻页(int(getattr(self, "_连续翻页方向", 0) or 0))
        self._连续翻页下次触发秒 = 当前秒 + float(
            getattr(self, "_连续翻页间隔秒", 0.03)
        )

    def _列表翻页按钮项(self):
        return (
            (-1, getattr(self, "按钮_列表上一页", None), "list_page_button_left"),
            (+1, getattr(self, "按钮_列表下一页", None), "list_page_button_right"),
        )

    def _列表翻页按钮应显示(self) -> bool:
        try:
            return (
                int(self.总页数()) > 1
                and (not bool(getattr(self, "是否详情页", False)))
                and (not bool(getattr(self, "是否星级筛选页", False)))
                and (not bool(getattr(self, "是否设置页", False)))
            )
        except Exception:
            return False

    def _绘制列表翻页按钮(self):
        if not self._列表翻页按钮应显示():
            return
        for _方向, 按钮对象, _来源 in self._列表翻页按钮项():
            if isinstance(按钮对象, 图片按钮):
                按钮对象.绘制(self.屏幕)

    def _处理列表翻页按钮事件(self, 事件) -> bool:
        按钮项 = tuple(self._列表翻页按钮项())
        if not 按钮项:
            return False

        for _方向, 按钮对象, _来源 in 按钮项:
            if isinstance(按钮对象, 图片按钮):
                try:
                    按钮对象.处理事件(事件)
                except Exception:
                    pass

        if not self._列表翻页按钮应显示():
            return False

        if 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            for 方向, 按钮对象, 来源 in 按钮项:
                if isinstance(按钮对象, 图片按钮) and 按钮对象.矩形.collidepoint(事件.pos):
                    self._滑动_按下 = False
                    self._滑动_已触发 = False
                    self._滑动_已移动 = False
                    self._开始连续翻页(int(方向), 来源=来源, 立即触发=True)
                    return True

        if 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            if str(getattr(self, "_连续翻页来源", "") or "") in (
                "list_page_button_left",
                "list_page_button_right",
            ):
                self._停止连续翻页()
                return True

        return False

    def _处理列表页点击进入详情(self, 点击位置) -> bool:
        if not self.中间区域.collidepoint(点击位置):
            return False

        _列表, 映射 = self.当前歌曲列表与映射()
        for idx, 卡片 in enumerate(self.当前页卡片):
            if not 卡片.矩形.collidepoint(点击位置):
                continue
            视图索引 = self.当前页 * self.每页数量 + idx
            原始索引 = 映射[视图索引] if 0 <= 视图索引 < len(映射) else 0
            try:
                self._播放按钮音效()
            except Exception:
                pass
            self.进入详情_原始索引(int(原始索引))
            return True
        return False

    def _处理列表页输入(self, 事件) -> bool:
        self._确保翻页交互状态()

        if self._处理列表翻页按钮事件(事件):
            return True

        if 事件.type == pygame.MOUSEMOTION:
            self._踏板选中视图索引 = None
            self._同步踏板卡片高亮()
            for 卡片 in self.当前页卡片:
                try:
                    卡片.处理事件(事件)
                except Exception:
                    pass

        if 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            if self.中间区域.collidepoint(事件.pos):
                self._滑动_按下 = True
                self._滑动_起点 = tuple(事件.pos)
                self._滑动_已触发 = False
                self._滑动_已移动 = False
                return True

        if 事件.type == pygame.MOUSEMOTION:
            if bool(getattr(self, "_滑动_按下", False)) and (
                not bool(getattr(self, "_滑动_已触发", False))
            ):
                try:
                    if hasattr(事件, "buttons") and 事件.buttons and (not 事件.buttons[0]):
                        pass
                    else:
                        sx, sy = getattr(self, "_滑动_起点", (0, 0))
                        dx = int(事件.pos[0] - sx)
                        dy = int(事件.pos[1] - sy)

                        if abs(dx) > 12 or abs(dy) > 12:
                            self._滑动_已移动 = True

                        阈值 = max(60, int(self.宽 * 0.05))
                        if (abs(dx) >= 阈值) and (abs(dx) > int(abs(dy) * 1.2)):
                            self._触发列表翻页(+1 if dx < 0 else -1)
                            self._滑动_已触发 = True
                except Exception:
                    pass
                return True

        if 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            if bool(getattr(self, "_滑动_按下", False)):
                self._滑动_按下 = False

                if (not bool(getattr(self, "_滑动_已触发", False))) and (
                    not bool(getattr(self, "_滑动_已移动", False))
                ):
                    self._处理列表页点击进入详情(事件.pos)

                self._滑动_已触发 = False
                self._滑动_已移动 = False
                return True

        if 事件.type == pygame.MOUSEBUTTONDOWN:
            if 事件.button == 4:
                self._停止连续翻页()
                self._触发列表翻页(-1)
                return True
            if 事件.button == 5:
                self._停止连续翻页()
                self._触发列表翻页(+1)
                return True

        if 事件.type == pygame.KEYDOWN:
            if 事件.key == pygame.K_LEFT:
                self._开始连续翻页(-1, 来源="keyboard", 立即触发=True)
                return True
            if 事件.key == pygame.K_RIGHT:
                self._开始连续翻页(+1, 来源="keyboard", 立即触发=True)
                return True
            if 事件.key == pygame.K_ESCAPE and getattr(self, "当前筛选星级", None) is not None:
                self._停止连续翻页()
                self._启动过渡(
                    self._特效_按钮,
                    pygame.Rect(self.宽 // 2 - 60, self.顶部高 // 2 - 20, 120, 40),
                    lambda: self.设置星级筛选(None),
                )
                return True

        if 事件.type == pygame.KEYUP and 事件.key in (pygame.K_LEFT, pygame.K_RIGHT):
            if str(getattr(self, "_连续翻页来源", "") or "") == "keyboard":
                self._停止连续翻页()
                return True

        return False

    def _取当前视图索引(self, 映射: List[int]) -> int:
        try:
            return int(映射.index(int(self.当前选择原始索引)))
        except Exception:
            return 0

    def _详情切到视图索引(self, 目标视图索引: int, 方向: int):
        列表, 映射 = self.当前歌曲列表与映射()
        if not 映射:
            return

        n = len(映射)
        try:
            目标视图索引 = int(目标视图索引) % n
        except Exception:
            目标视图索引 = 0

        新原始索引 = int(映射[目标视图索引])
        原始 = self.当前原始歌曲列表()
        if not 原始:
            return

        新原始索引 = max(0, min(新原始索引, len(原始) - 1))
        self.当前选择原始索引 = 新原始索引
        self._踏板选中视图索引 = int(目标视图索引)

        # ✅ 播放预览
        try:
            歌 = 原始[self.当前选择原始索引]
            self.播放歌曲mp3(getattr(歌, "mp3路径", None))
        except Exception:
            pass

        # ✅ 同步底下缩略图页码（必要时触发翻页）
        目标页 = int(目标视图索引 // int(self.每页数量))

        if bool(getattr(self, "动画中", False)):
            # 防御：如果正在动画，强制收敛状态，避免“动画锁死导致详情切歌不同步页码”
            try:
                self.动画中 = False
                self.当前页 = int(getattr(self, "动画目标页", self.当前页))
                self.当前页卡片 = self.生成指定页卡片(self.当前页)
            except Exception:
                pass

        if 目标页 != int(self.当前页):
            # 只要跨页，就翻（满足你“第8首下一首要翻页”）
            self.触发翻页动画(目标页=目标页, 方向=int(方向))
        else:
            # 同页也预加载一下，避免大图切歌时封面没进缓存
            self.安排预加载(基准页=self.当前页)

    def 打开星级筛选页(self):
        if self.是否详情页:
            return
        self.是否星级筛选页 = True

    def 关闭星级筛选页(self):
        self.是否星级筛选页 = False

    def 设置星级筛选(self, 星级: Optional[int]):
        self.当前筛选星级 = 星级
        self._失效歌曲视图缓存()
        self.当前页 = 0
        self.当前页卡片 = self.生成指定页卡片(self.当前页)
        self.安排预加载(基准页=self.当前页)

    def 进入详情_原始索引(self, 原始索引: int):
        原始 = self.当前原始歌曲列表()
        if not 原始:
            return

        self.当前选择原始索引 = max(0, min(原始索引, len(原始) - 1))
        self.是否详情页 = True
        try:
            _列表, 映射 = self.当前歌曲列表与映射()
            self._踏板选中视图索引 = int(映射.index(self.当前选择原始索引))
        except Exception:
            self._踏板选中视图索引 = None

        # ✅ 改：第一次点击就播，所以不需要“点击次数”
        # 只重置“上次播放时间”，防止刚切歌立刻点被节流
        self._大图确认_上次触发时间 = 0.0

        # ✅ 记录“浮动大图入场动画”开始时间（0.5秒）
        try:
            self._浮动大图入场开始毫秒 = int(pygame.time.get_ticks())
        except Exception:
            self._浮动大图入场开始毫秒 = 0
        self._浮动大图入场时长毫秒 = 500

        歌 = 原始[self.当前选择原始索引]
        self.播放歌曲mp3(歌.mp3路径)

        self.安排预加载(基准页=self.当前页)

    def 返回列表(self):
        self.是否详情页 = False
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.确保播放背景音乐()

        # 返回时定位到该歌所在页（基于“当前视图列表”）
        列表, 映射 = self.当前歌曲列表与映射()
        if 映射:
            try:
                视图索引 = 映射.index(self.当前选择原始索引)
            except Exception:
                视图索引 = 0
            self.当前页 = max(0, 视图索引 // self.每页数量)
            self._踏板选中视图索引 = int(视图索引)
        else:
            self.当前页 = 0
            self._踏板选中视图索引 = None

        self.当前页卡片 = self.生成指定页卡片(self.当前页)
        self.安排预加载(基准页=self.当前页)
        self._同步踏板卡片高亮()

    def 下一首(self):
        列表, 映射 = self.当前歌曲列表与映射()
        if not 映射:
            return

        当前视图索引 = self._取当前视图索引(映射)
        目标视图索引 = (当前视图索引 + 1) % len(映射)
        self._详情切到视图索引(目标视图索引, 方向=+1)

    def 上一首(self):
        列表, 映射 = self.当前歌曲列表与映射()
        if not 映射:
            return

        当前视图索引 = self._取当前视图索引(映射)
        目标视图索引 = (当前视图索引 - 1) % len(映射)
        self._详情切到视图索引(目标视图索引, 方向=-1)

    def _同步踏板卡片高亮(self):
        基准视图索引 = getattr(self, "_踏板选中视图索引", None)
        for idx, 卡片 in enumerate(getattr(self, "当前页卡片", []) or []):
            try:
                视图索引 = int(self.当前页) * int(self.每页数量) + int(idx)
                卡片.踏板高亮 = (
                    基准视图索引 is not None and int(基准视图索引) == 视图索引
                )
            except Exception:
                try:
                    卡片.踏板高亮 = False
                except Exception:
                    pass

    def _踏板选中缩略图(self, 方向步进: int):
        if bool(getattr(self, "动画中", False)) or bool(
            getattr(self, "是否设置页", False)
        ):
            return None
        if bool(getattr(self, "是否星级筛选页", False)):
            return None

        列表, 映射 = self.当前歌曲列表与映射()
        if not 映射:
            return None

        if bool(getattr(self, "是否详情页", False)):
            try:
                self._播放按钮音效()
            except Exception:
                pass
            if int(方向步进) < 0:
                self.上一首()
            else:
                self.下一首()
            return None

        当前视图索引 = getattr(self, "_踏板选中视图索引", None)
        if 当前视图索引 is None:
            当前视图索引 = int(self.当前页) * int(self.每页数量)
            当前视图索引 = max(0, min(int(当前视图索引), len(映射) - 1))
        else:
            当前视图索引 = (int(当前视图索引) + int(方向步进)) % len(映射)

        self._踏板选中视图索引 = int(当前视图索引)
        self.当前页 = int(
            max(0, min(len(映射) - 1, 当前视图索引)) // max(1, int(self.每页数量))
        )
        self.当前页卡片 = self.生成指定页卡片(self.当前页)
        self.安排预加载(基准页=self.当前页)
        self._同步踏板卡片高亮()

        try:
            self.当前选择原始索引 = int(映射[int(当前视图索引)])
        except Exception:
            pass

        try:
            self._播放按钮音效()
        except Exception:
            pass
        return None

    def _踏板确认当前歌曲(self):
        if bool(getattr(self, "动画中", False)) or bool(
            getattr(self, "是否设置页", False)
        ):
            return None
        if bool(getattr(self, "是否星级筛选页", False)):
            return None

        if bool(getattr(self, "是否详情页", False)):
            self._启动过渡(
                self._特效_大图确认,
                self.详情大框矩形,
                self._记录并处理大图确认点击,
            )
            return None

        列表, 映射 = self.当前歌曲列表与映射()
        if not 映射:
            return None

        当前视图索引 = getattr(self, "_踏板选中视图索引", None)
        if 当前视图索引 is None:
            当前视图索引 = int(self.当前页) * int(self.每页数量)
        当前视图索引 = max(0, min(int(当前视图索引), len(映射) - 1))

        页内索引 = int(当前视图索引) - int(self.当前页) * int(self.每页数量)
        if not (0 <= 页内索引 < len(self.当前页卡片)):
            self._踏板选中视图索引 = int(当前视图索引)
            self._同步踏板卡片高亮()
            return None

        try:
            原始索引 = int(映射[int(当前视图索引)])
        except Exception:
            原始索引 = 0
        卡片 = self.当前页卡片[int(页内索引)]
        self._踏板选中视图索引 = int(当前视图索引)
        self._同步踏板卡片高亮()
        self._启动过渡(
            self._特效_按钮,
            卡片.矩形,
            lambda: self.进入详情_原始索引(int(原始索引)),
        )
        return None

    def 处理全局踏板(self, 动作: str):
        try:
            self._确保公共交互()
        except Exception:
            pass
        try:
            if (
                getattr(self, "_过渡_特效", None) is not None
                and self._过渡_特效.是否动画中()
            ):
                return None
        except Exception:
            pass
        if 动作 == 踏板动作_左:
            return self._踏板选中缩略图(-1)
        if 动作 == 踏板动作_右:
            return self._踏板选中缩略图(+1)
        if 动作 == 踏板动作_确认:
            return self._踏板确认当前歌曲()
        return None


    def 绘制背景(self):
        self._刷新背景遮罩设置(False)
        if self._应使用GPU背景():
            try:
                self.屏幕.fill((0, 0, 0, 0))
            except Exception:
                self.屏幕.fill((0, 0, 0))
            return

        if self._取背景渲染模式() == "动态背景":
            if not self._绘制软件动态背景():
                self.屏幕.fill((10, 10, 18))
        elif self.背景图_原图 is not None:
            目标尺寸 = (self.宽, self.高)
            if self.背景图_缩放缓存 is None or self.背景图_缩放尺寸 != 目标尺寸:
                try:
                    self.背景图_缩放缓存 = pygame.transform.smoothscale(
                        self.背景图_原图, 目标尺寸
                    )
                    self.背景图_缩放尺寸 = 目标尺寸
                except Exception:
                    self.背景图_缩放缓存 = None
                    self.背景图_缩放尺寸 = (0, 0)

            if self.背景图_缩放缓存 is not None:
                self.屏幕.blit(self.背景图_缩放缓存, (0, 0))
            else:
                self.屏幕.fill((10, 10, 18))
        else:
            self.屏幕.fill((10, 10, 18))

        # 背景遮罩亮度来自 SQLite 持久化设置
        遮罩alpha = max(0, min(255, int(getattr(self, "_背景遮罩alpha", 60) or 60)))
        暗层键 = (int(self.宽), int(self.高), int(遮罩alpha))
        暗层 = self._背景暗层缓存 if self._背景暗层缓存键 == 暗层键 else None
        if 暗层 is None:
            暗层 = pygame.Surface((self.宽, self.高), pygame.SRCALPHA)
            暗层.fill((0, 0, 0, int(遮罩alpha)))
            self._背景暗层缓存 = 暗层
            self._背景暗层缓存键 = 暗层键
        self.屏幕.blit(暗层, (0, 0))

    def 绘制顶部(self):
        self._确保top栏缓存()

        # 1) top背景
        if self._top图:
            self.屏幕.blit(self._top图, self._top_rect.topleft)
        else:
            pygame.draw.rect(self.屏幕, (20, 40, 80), self._top_rect)

        # 2) 中间标题（歌曲选择.png）
        if getattr(self, "_top标题图", None) is not None:
            self.屏幕.blit(self._top标题图, self._top标题rect.topleft)

        # 3) 左上角：类型 + 模式（优先图片，缺图退文字；y=0；x=屏宽10%）
        self._绘制顶部左上类型模式()

    def 绘制底部(self):
        self._确保公共交互()

        # ✅ 底部图文按钮统一字号（重开除外）
        try:
            参考宽 = (
                int(self.按钮_歌曲分类.矩形.w)
                if hasattr(self, "按钮_歌曲分类")
                else 160
            )
            标签字号 = max(14, int(参考宽 * 0.16))
        except Exception:
            标签字号 = 22
        底部标签字体 = 获取字体(标签字号, 是否粗体=True)

        # 歌曲分类
        if isinstance(self.按钮_歌曲分类, 底部图文按钮):
            self.按钮_歌曲分类.绘制(self.屏幕, 底部标签字体)
        else:
            self.按钮_歌曲分类.绘制(self.屏幕, 底部标签字体)

        # 收藏夹
        if isinstance(self.按钮_收藏夹, 底部图文按钮):
            self.按钮_收藏夹.绘制(self.屏幕, 底部标签字体)
        else:
            self.按钮_收藏夹.绘制(self.屏幕, 底部标签字体)

        # ALL（只画图）
        if isinstance(self.按钮_ALL, 图片按钮):
            self.按钮_ALL.绘制(self.屏幕)
        else:
            self.按钮_ALL.绘制(self.屏幕, 底部标签字体)

        # 重开（例外：走你自己的按钮样式）
        重选字号 = max(12, int(self.按钮_重选模式.矩形.h * 0.26))
        self.按钮_重选模式.绘制(self.屏幕, 获取字体(重选字号, 是否粗体=True))

        # P加入（会在重算布局里根据玩家数切成 1P加入/2P加入）
        if isinstance(self.按钮_2P加入, 底部图文按钮):
            self.按钮_2P加入.绘制(self.屏幕, 底部标签字体)
        else:
            self.按钮_2P加入.绘制(self.屏幕, 底部标签字体)

        # 设置
        if isinstance(self.按钮_设置, 底部图文按钮):
            self.按钮_设置.绘制(self.屏幕, 底部标签字体)
        else:
            self.按钮_设置.绘制(self.屏幕, 底部标签字体)

        # ✅ 公共函数：联网状态图标（放底部中间，不挤左右按钮）
        try:
            from core.工具 import 绘制底部联网与信用

            联网原图 = self._获取联网原图_尽力()
            字体_credit = 获取字体(max(14, int(标签字号 * 1.3)), 是否粗体=False)

            # credit数值这里先给个占位（你后面接真实 credit 再改）
            绘制底部联网与信用(
                屏幕=self.屏幕,
                联网原图=联网原图,
                字体_credit=字体_credit,
                credit数值=str(int(self.上下文.get("状态", {}).get("投币数", 0) or 0)),
            )
        except Exception:
            pass

    def _绘制顶部左上类型模式(self):
        self._确保top栏资源()

        屏宽, _屏高 = self.屏幕.get_size()
        顶栏矩形 = self._top_rect

        起始x = 顶栏矩形.left + int(屏宽 * float(self._top左上_x屏宽占比))
        起始y = 顶栏矩形.top + int(self._top左上_y像素)

        目标高 = max(1, int(顶栏矩形.h * float(self._top小标题目标高占比)))

        类型名 = self._归一化类型名(self.当前类型名())
        模式名 = self._归一化模式名(self.当前模式名())

        # ===== 类型 =====
        类型路径 = self._top类型图片路径表.get(类型名, "")
        类型缩放 = float(self._top类型_缩放覆盖.get(类型名, self._top类型_缩放))
        类型偏移 = self._top类型_偏移覆盖.get(类型名, self._top类型_偏移)

        x = 起始x + int(类型偏移[0])
        y = 起始y + int(类型偏移[1])

        类型图 = None
        if 类型路径:
            可用宽 = max(1, 顶栏矩形.right - x)
            类型图 = self._获取top小标题图(类型路径, 目标高, 类型缩放, 最大宽=可用宽)

        if 类型图 is not None:
            类型矩形 = 类型图.get_rect(topleft=(x, y))
            类型矩形 = self._夹紧矩形到top内部(类型矩形)
            self.屏幕.blit(类型图, 类型矩形.topleft)
            x = 类型矩形.right + int(self._top类型模式间距)
        else:
            字体 = 获取字体(26, 是否粗体=False)
            文面 = 字体.render(str(类型名 or ""), True, (255, 255, 255))
            文矩形 = 文面.get_rect(topleft=(x, y))
            文矩形 = self._夹紧矩形到top内部(文矩形)
            self.屏幕.blit(文面, 文矩形.topleft)
            x = 文矩形.right + int(self._top类型模式间距)

        # ===== 模式 =====
        模式路径 = self._top模式图片路径表.get(模式名, "")
        模式缩放 = float(self._top模式_缩放覆盖.get(模式名, self._top模式_缩放))
        模式偏移 = self._top模式_偏移覆盖.get(模式名, self._top模式_偏移)

        x2 = x + int(模式偏移[0])
        y2 = 起始y + int(模式偏移[1])

        模式图 = None
        if 模式路径:
            可用宽2 = max(1, 顶栏矩形.right - x2)
            模式图 = self._获取top小标题图(模式路径, 目标高, 模式缩放, 最大宽=可用宽2)

        if 模式图 is not None:
            模式矩形 = 模式图.get_rect(topleft=(x2, y2))
            模式矩形 = self._夹紧矩形到top内部(模式矩形)
            self.屏幕.blit(模式图, 模式矩形.topleft)
        else:
            字体 = 获取字体(26, 是否粗体=False)
            文面 = 字体.render(str(模式名 or ""), True, (255, 255, 255))
            文矩形 = 文面.get_rect(topleft=(x2, y2))
            文矩形 = self._夹紧矩形到top内部(文矩形)
            self.屏幕.blit(文面, 文矩形.topleft)

    def 绘制列表页(self):
        列表, _映射 = self.当前歌曲列表与映射()
        if not 列表:
            try:
                字体 = 获取字体(28)
                if bool(getattr(self, "是否收藏夹模式", False)):
                    if self.当前筛选星级 is None:
                        提示文本 = "收藏夹为空，先在浮动大图右侧点收藏按钮"
                    else:
                        提示文本 = "收藏夹里没有符合当前筛选的歌曲，点 ALL 查看全部收藏"
                else:
                    提示文本 = "没有扫描到歌曲，请检查歌曲目录songs文件夹，点击重开按钮退出当前模式"
                文面 = 字体.render(
                    提示文本,
                    True,
                    (255, 255, 255),
                )
                文r = 文面.get_rect(center=(self.宽 // 2, self.顶部高 + 90))
                self.屏幕.blit(文面, 文r.topleft)
            except Exception:
                pass
            return

        self._同步踏板卡片高亮()

        # 列表页禁止同步读封面；冷资源先占位，等后台预加载补齐。
        for 卡片 in self.当前页卡片:
            卡片.绘制(
                self.屏幕,
                self.小字体,
                self.图缓存,
                允许同步封面加载=False,
            )

    def 绘制列表页_动画(self):
        旧偏移, 新偏移 = self._取列表翻页动画偏移()

        for 卡片 in self.动画旧页卡片:
            原矩形 = 卡片.矩形
            try:
                卡片.矩形 = 原矩形.move(旧偏移, 0)
                卡片.绘制(
                    self.屏幕,
                    self.小字体,
                    self.图缓存,
                    允许同步封面加载=False,
                )
            finally:
                卡片.矩形 = 原矩形

        for 卡片 in self.动画新页卡片:
            原矩形 = 卡片.矩形
            try:
                卡片.矩形 = 原矩形.move(新偏移, 0)
                卡片.绘制(
                    self.屏幕,
                    self.小字体,
                    self.图缓存,
                    允许同步封面加载=False,
                )
            finally:
                卡片.矩形 = 原矩形

    def 绘制详情浮层(self):
        原始 = self.当前原始歌曲列表()
        if not 原始:
            return

        歌 = 原始[self.当前选择原始索引]

        def _夹紧(值: float, 最小值: float, 最大值: float) -> float:
            return 最小值 if 值 < 最小值 else (最大值 if 值 > 最大值 else 值)

        def _缓出(进度: float) -> float:
            进度 = _夹紧(进度, 0.0, 1.0)
            return 1.0 - (1.0 - 进度) * (1.0 - 进度)

        详情浮层整体缩放 = self._取布局值("详情大图.整体缩放", 1.12)
        try:
            详情浮层整体缩放 = float(详情浮层整体缩放)
        except Exception:
            详情浮层整体缩放 = 1.12
        详情浮层整体缩放 = max(0.10, min(3.00, 详情浮层整体缩放))

        目标比例 = self._取布局值("详情大图.目标比例", 1.38)
        try:
            目标比例 = float(目标比例)
        except Exception:
            目标比例 = 1.38
        目标比例 = max(0.20, min(5.0, 目标比例))

        可用宽占比 = self._取布局值("详情大图.可用宽占比", 0.60)
        可用高占比 = self._取布局值("详情大图.可用高占比", 0.78)
        try:
            可用宽占比 = float(可用宽占比)
        except Exception:
            可用宽占比 = 0.60
        try:
            可用高占比 = float(可用高占比)
        except Exception:
            可用高占比 = 0.78

        可用宽占比 = max(0.20, min(0.98, 可用宽占比))
        可用高占比 = max(0.20, min(0.98, 可用高占比))

        可用宽 = int(self.中间区域.w * 可用宽占比)
        可用高 = int(self.中间区域.h * 可用高占比)

        基准宽 = min(可用宽, int(可用高 * 目标比例))
        基准高 = int(基准宽 / 目标比例)

        最终缩放 = min(
            详情浮层整体缩放,
            float(可用宽) / float(max(1, 基准宽)),
            float(可用高) / float(max(1, 基准高)),
        )
        最终缩放 = max(0.10, 最终缩放)

        内容宽 = max(320, int(基准宽 * 最终缩放))
        内容高 = max(220, int(基准高 * 最终缩放))

        if 内容宽 > 可用宽:
            内容宽 = 可用宽
            内容高 = int(内容宽 / 目标比例)
        if 内容高 > 可用高:
            内容高 = 可用高
            内容宽 = int(内容高 * 目标比例)

        框路径 = _资源路径("UI-img", "选歌界面资源", "缩略图大.png")

        try:
            框宽缩放 = float(_缩略图大框_宽缩放)
        except Exception:
            框宽缩放 = 1.0
        try:
            框高缩放 = float(_缩略图大框_高缩放)
        except Exception:
            框高缩放 = 1.0
        try:
            框x偏移 = int(_缩略图大框_x偏移)
        except Exception:
            框x偏移 = 0
        try:
            框y偏移 = int(_缩略图大框_y偏移)
        except Exception:
            框y偏移 = 0

        try:
            贴图宽缩放 = float(_详情大框贴图_宽缩放)
        except Exception:
            贴图宽缩放 = 1.0
        try:
            贴图高缩放 = float(_详情大框贴图_高缩放)
        except Exception:
            贴图高缩放 = 1.0
        try:
            贴图x偏移 = int(_详情大框贴图_x偏移)
        except Exception:
            贴图x偏移 = 0
        try:
            贴图y偏移 = int(_详情大框贴图_y偏移)
        except Exception:
            贴图y偏移 = 0

        框宽缩放 = max(0.05, min(5.0, 框宽缩放))
        框高缩放 = max(0.05, min(5.0, 框高缩放))
        贴图宽缩放 = max(0.05, min(5.0, 贴图宽缩放))
        贴图高缩放 = max(0.05, min(5.0, 贴图高缩放))

        内容基础矩形 = pygame.Rect(
            0,
            0,
            max(1, int(round(内容宽 * 框宽缩放))),
            max(1, int(round(内容高 * 框高缩放))),
        )
        内容基础矩形.center = self.中间区域.center
        内容基础矩形.x += int(框x偏移)
        内容基础矩形.y += int(框y偏移)

        局部内容矩形 = pygame.Rect(0, 0, 内容基础矩形.w, 内容基础矩形.h)
        局部布局 = 计算框体槽位布局(局部内容矩形, 是否大图=True)

        局部封面框 = 局部布局["封面矩形"]
        局部信息条 = 局部布局["信息条矩形"]
        局部星星区域 = 局部布局["星星区域"]
        局部游玩区域 = 局部布局["游玩区域"]
        局部bpm区域 = 局部布局["bpm区域"]

        装饰贴图宽 = max(1, int(round(内容基础矩形.w * 贴图宽缩放)))
        装饰贴图高 = max(1, int(round(内容基础矩形.h * 贴图高缩放)))

        局部内容左 = 0
        局部内容上 = 0
        局部内容右 = 内容基础矩形.w
        局部内容下 = 内容基础矩形.h

        局部贴图左 = (内容基础矩形.w - 装饰贴图宽) // 2 + int(贴图x偏移)
        局部贴图上 = (内容基础矩形.h - 装饰贴图高) // 2 + int(贴图y偏移)
        局部贴图右 = 局部贴图左 + 装饰贴图宽
        局部贴图下 = 局部贴图上 + 装饰贴图高

        总左 = min(局部内容左, 局部贴图左)
        总上 = min(局部内容上, 局部贴图上)
        总右 = max(局部内容右, 局部贴图右)
        总下 = max(局部内容下, 局部贴图下)

        总宽 = max(1, int(总右 - 总左))
        总高 = max(1, int(总下 - 总上))

        内容偏移x = int(-总左)
        内容偏移y = int(-总上)
        贴图绘制x = int(局部贴图左 - 总左)
        贴图绘制y = int(局部贴图上 - 总上)

        现在毫秒 = 0
        try:
            现在毫秒 = int(pygame.time.get_ticks())
        except Exception:
            现在毫秒 = 0

        开始毫秒 = int(getattr(self, "_浮动大图入场开始毫秒", 0) or 0)
        时长毫秒 = int(getattr(self, "_浮动大图入场时长毫秒", 500) or 500)

        进度 = 1.0
        if 开始毫秒 > 0 and 时长毫秒 > 0:
            进度 = (现在毫秒 - 开始毫秒) / max(1, 时长毫秒)
            进度 = _夹紧(进度, 0.0, 1.0)

        缓动进度 = _缓出(进度)
        入场透明度 = int(255 * 缓动进度)
        入场透明度 = max(0, min(255, 入场透明度))
        入场y偏移 = int(
            round((1.0 - 缓动进度) * max(18, min(48, int(self.高 * 0.035))))
        )
        遮罩透明度 = int(round(150 * 缓动进度))
        遮罩透明度 = max(0, min(220, 遮罩透明度))

        self._详情浮层_alpha = int(入场透明度)
        # 详情页改成设置页同类的叠加层：保留独立局部画布，避免把整块大图再做逐帧 smoothscale。
        self._详情浮层_最后缩放 = 1.0

        if 遮罩透明度 > 0:
            遮罩键 = (int(self.宽), int(self.高), int(遮罩透明度))
            遮罩 = (
                self._详情浮层遮罩缓存图
                if self._详情浮层遮罩缓存键 == 遮罩键
                else None
            )
            if 遮罩 is None:
                遮罩 = pygame.Surface((int(self.宽), int(self.高)), pygame.SRCALPHA)
                遮罩.fill((0, 0, 0, int(遮罩透明度)))
                self._详情浮层遮罩缓存图 = 遮罩
                self._详情浮层遮罩缓存键 = 遮罩键
            self.屏幕.blit(遮罩, (0, 0))

        画布尺寸 = (int(总宽), int(总高))
        局部画布 = (
            self._详情浮层面板缓存图
            if self._详情浮层面板缓存尺寸 == 画布尺寸
            else None
        )
        if 局部画布 is None:
            局部画布 = pygame.Surface(画布尺寸, pygame.SRCALPHA)
            self._详情浮层面板缓存图 = 局部画布
            self._详情浮层面板缓存尺寸 = 画布尺寸

        self._绘制详情浮层面板内容(
            局部画布,
            歌,
            框路径,
            内容基础矩形,
            局部封面框,
            局部信息条,
            局部星星区域,
            局部游玩区域,
            局部bpm区域,
            装饰贴图宽,
            装饰贴图高,
            贴图绘制x,
            贴图绘制y,
            内容偏移x,
            内容偏移y,
            总宽,
            总高,
        )
        try:
            局部画布.set_alpha(int(入场透明度))
        except Exception:
            pass

        当前大框 = 局部画布.get_rect(center=内容基础矩形.center)
        当前大框.y += int(入场y偏移)
        self.详情大框矩形 = 当前大框
        self.详情封面矩形 = pygame.Rect(
            int(当前大框.x + 内容偏移x + 局部封面框.x),
            int(当前大框.y + 内容偏移y + 局部封面框.y),
            int(局部封面框.w),
            int(局部封面框.h),
        )
        self.屏幕.blit(局部画布, 当前大框.topleft)
        try:
            self._绘制详情浮层星星光泽(
                当前大框=当前大框,
                局部星星区域=局部星星区域,
                内容偏移x=内容偏移x,
                内容偏移y=内容偏移y,
                总宽=总宽,
                总高=总高,
                星数=int(getattr(歌, "星级", 0) or 0),
                光效透明度=入场透明度,
            )
        except Exception:
            pass

        下一首图路径 = _资源路径("UI-img", "选歌界面资源", "下一首.png")
        下一首原图 = 获取UI原图(下一首图路径, 透明=True)
        if 下一首原图 is not None:
            原宽, 原高 = 下一首原图.get_size()
        else:
            原宽, 原高 = (150, 74)

        左右按钮高占比 = self._取布局值("详情大图.左右按钮.目标高占比", 0.22)
        try:
            左右按钮高占比 = float(左右按钮高占比)
        except Exception:
            左右按钮高占比 = 0.22
        左右按钮高占比 = max(0.05, min(0.80, 左右按钮高占比))

        按钮最小高 = self._取布局像素(
            "详情大图.左右按钮.最小高", 72, 最小=24, 最大=99999
        )
        按钮最大高 = self._取布局像素(
            "详情大图.左右按钮.最大高", 99999, 最小=按钮最小高, 最大=99999
        )
        按钮高 = max(按钮最小高, int(round(float(当前大框.h) * 左右按钮高占比)))
        按钮高 = min(按钮高, 按钮最大高)
        按钮宽 = max(36, int(按钮高 * float(原宽) / float(max(1, 原高))))
        按钮外间距 = self._取布局像素(
            "详情大图.左右按钮.外间距",
            max(24, int(self.宽 * 0.022)),
            最小=0,
            最大=99999,
        )
        按钮y偏移 = self._取布局像素(
            "详情大图.左右按钮.y偏移", 0, 最小=-99999, 最大=99999
        )
        按钮边距 = self._取布局像素(
            "详情大图.左右按钮.边距", 12, 最小=0, 最大=99999
        )
        上一首x偏移 = self._取布局像素(
            "详情大图.左右按钮.上一首x偏移", 0, 最小=-99999, 最大=99999
        )
        下一首x偏移 = self._取布局像素(
            "详情大图.左右按钮.下一首x偏移", 0, 最小=-99999, 最大=99999
        )

        左按钮矩形 = pygame.Rect(
            max(按钮边距, 当前大框.left - 按钮外间距 - 按钮宽 + 上一首x偏移),
            当前大框.centery - 按钮高 // 2 + 按钮y偏移,
            按钮宽,
            按钮高,
        )
        右按钮矩形 = pygame.Rect(
            min(
                self.宽 - 按钮边距 - 按钮宽,
                当前大框.right + 按钮外间距 + 下一首x偏移,
            ),
            当前大框.centery - 按钮高 // 2 + 按钮y偏移,
            按钮宽,
            按钮高,
        )

        self.按钮_详情上一首.矩形 = 左按钮矩形
        self.按钮_详情下一首.矩形 = 右按钮矩形

        self.按钮_详情上一首.绘制(self.屏幕)
        self.按钮_详情下一首.绘制(self.屏幕)

        收藏图路径 = _资源路径(
            "UI-img",
            "选歌界面资源",
            "移除收藏.png" if bool(getattr(歌, "是否收藏", False)) else "添加收藏.png",
        )
        if (not hasattr(self, "按钮_详情收藏")) or (
            not isinstance(self.按钮_详情收藏, 图片按钮)
        ):
            self.按钮_详情收藏 = 图片按钮(收藏图路径, pygame.Rect(0, 0, 1, 1))
        elif str(getattr(self.按钮_详情收藏, "图片路径", "") or "") != 收藏图路径:
            try:
                self.按钮_详情收藏.图片路径 = str(收藏图路径)
                self.按钮_详情收藏._加载原图()
            except Exception:
                pass

        收藏原图 = 获取UI原图(收藏图路径, 透明=True)
        if 收藏原图 is not None:
            收藏原宽, 收藏原高 = 收藏原图.get_size()
        else:
            收藏原宽, 收藏原高 = (220, 96)

        收藏按钮高 = max(48, int(当前大框.h * 0.13))
        收藏按钮宽 = max(
            90, int(收藏按钮高 * float(收藏原宽) / float(max(1, 收藏原高)))
        )
        收藏按钮间距x = max(16, int(self.宽 * 0.012))
        收藏按钮x = min(self.宽 - 收藏按钮宽 - 12, 当前大框.right + 收藏按钮间距x)
        收藏按钮y = max(12, 当前大框.top + int(当前大框.h * 0.17))
        收藏按钮y = min(self.高 - 收藏按钮高 - 12, 收藏按钮y)

        self.按钮_详情收藏.矩形 = pygame.Rect(
            收藏按钮x, 收藏按钮y, 收藏按钮宽, 收藏按钮高
        )
        self.按钮_详情收藏.绘制(self.屏幕)


    def 绘制星级筛选页(self):
        # 半透明遮罩
        暗层 = pygame.Surface((self.宽, self.高), pygame.SRCALPHA)
        暗层.fill((0, 0, 0, 170))
        self.屏幕.blit(暗层, (0, 0))

        面板 = self.筛选页面板矩形

        面板底 = pygame.Surface((面板.w, 面板.h), pygame.SRCALPHA)
        面板底.fill((10, 20, 40, 220))
        self.屏幕.blit(面板底, 面板.topleft)
        绘制圆角矩形(self.屏幕, 面板, (180, 220, 255), 圆角=18, 线宽=3)

        标题字体 = 获取字体(36)
        说明字体 = 获取字体(18)
        按钮字体 = 获取字体(18)

        绘制文本(
            self.屏幕,
            "按星级筛选",
            标题字体,
            (255, 255, 255),
            (面板.centerx, 面板.y + 36),
            对齐="center",
        )
        绘制文本(
            self.屏幕,
            "选择星级后仅展示对应星星的歌（ESC/点空白关闭）",
            说明字体,
            (210, 235, 255),
            (面板.centerx, 面板.y + 78),
            对齐="center",
        )

        # 画 1~20 星按钮（你已经在 _重算星级筛选页布局 里生成了）
        for 星, 按钮对象 in self.星级按钮列表:
            try:
                按钮对象.绘制(self.屏幕, 按钮字体)
            except TypeError:
                # 兼容你可能混进来的旧按钮类
                try:
                    按钮对象.绘制(self.屏幕, 按钮字体)
                except Exception:
                    pass

            # 当前筛选高亮（可选：更直观）
            try:
                if self.当前筛选星级 is not None and int(self.当前筛选星级) == int(星):
                    r = getattr(按钮对象, "矩形", None)
                    if isinstance(r, pygame.Rect):
                        pygame.draw.rect(
                            self.屏幕, (255, 220, 80), r, width=3, border_radius=16
                        )
            except Exception:
                pass

    def _确保公共交互(self):
        if getattr(self, "_公共交互已初始化", False):
            return
        self._公共交互已初始化 = True
        self._确保翻页交互状态()

        # 过渡（按钮截图缩放淡出）
        self._过渡_特效 = None
        self._过渡_图片 = None
        self._过渡_rect = pygame.Rect(0, 0, 0, 0)
        self._过渡_回调 = None
        self._过渡_曾在播放 = False

        # ✅ 星级筛选专用：0.5s 渐隐放大（像“浮动大图入场”）
        self._特效_星级筛选 = 渐隐放大点击特效(总时长=0.5)

        # ✅ 全局点击序列帧特效
        self._全局点击特效 = None

        # 公用按钮音效 + 公用点击特效
        self._按钮音效 = None
        self._翻页音效 = None
        self._翻页音效通道 = None
        self._特效_按钮 = None
        self._特效_大图确认 = None

        # ✅ 开始游戏音效（大图二次点击触发）
        self._开始游戏音效_对象 = None

        # ✅ “几P加入”嘲讽提示（2秒）
        self._消息提示_文本 = ""
        self._消息提示_截止时间 = 0.0

        # ✅ “浮动大图二次点击”计数器（不是双击判定，是第二次点击）
        self._大图确认_点击次数 = 0
        self._大图确认_上次点击时间 = 0.0

        # ===== 引入：ui/点击特效.py（序列帧）=====
        try:
            from ui.点击特效 import 序列帧特效资源, 全局点击特效管理器
        except Exception:
            序列帧特效资源 = None
            全局点击特效管理器 = None

        # ===== 引入：ui/按钮特效.py（截图缩放淡出 + 音效）=====
        try:
            from ui.按钮特效 import 公用按钮点击特效, 公用按钮音效
        except Exception:
            公用按钮点击特效 = None
            公用按钮音效 = None

        # -------------------------
        # 初始化：全局点击序列帧特效
        # -------------------------
        if 序列帧特效资源 and 全局点击特效管理器:
            点击特效目录 = ""
            try:
                from core.常量与路径 import 默认资源路径

                资源 = 默认资源路径()
                根目录 = str(资源.get("根", "") or "")
                if 根目录:
                    点击特效目录 = os.path.join(根目录, "UI-img", "点击特效")
            except Exception:
                点击特效目录 = ""

            if not 点击特效目录:
                try:
                    点击特效目录 = _资源路径("UI-img", "点击特效")
                except Exception:
                    点击特效目录 = ""

            try:
                特效资源 = 序列帧特效资源(目录=点击特效目录, 扩展名=".png")
                特效ok = bool(特效资源.加载())
                帧列表 = 特效资源.帧列表 if 特效ok else []
            except Exception:
                帧列表 = []

            try:
                self._全局点击特效 = 全局点击特效管理器(
                    帧列表=帧列表,
                    每秒帧数=30,
                    缩放比例=1.0,
                )
            except Exception:
                self._全局点击特效 = None

        # -------------------------
        # 初始化：按钮音效
        # -------------------------
        音效路径 = ""
        try:
            from core.常量与路径 import 默认资源路径

            资源 = 默认资源路径()
            音效路径 = str(资源.get("按钮音效", "") or "")
        except Exception:
            音效路径 = ""

        if 公用按钮音效 and 音效路径 and os.path.isfile(音效路径):
            try:
                self._按钮音效 = 公用按钮音效(音效路径)
            except Exception:
                self._按钮音效 = None

        # -------------------------
        # 初始化：翻页音效
        # -------------------------
        翻页音效路径 = _资源路径("冷资源", "Buttonsound", "翻页.mp3")
        try:
            if pygame.mixer.get_init() and os.path.isfile(翻页音效路径):
                self._翻页音效 = pygame.mixer.Sound(翻页音效路径)
        except Exception:
            self._翻页音效 = None

        # -------------------------
        # 初始化：按钮点击“截图缩放淡出”特效
        # -------------------------
        if 公用按钮点击特效:
            try:
                self._特效_按钮 = 公用按钮点击特效()
                self._特效_大图确认 = 公用按钮点击特效(
                    总时长=0.35,
                    缩小阶段=0.10,
                    缩小到=0.98,
                    放大到=6.00,
                    透明起始=255,
                    透明结束=0,
                )
            except Exception:
                self._特效_按钮 = None
                self._特效_大图确认 = None

        # -------------------------
        # ✅ 初始化：开始游戏音效 backsound/开始游戏.mp3
        # -------------------------
        开始游戏路径 = _资源路径("冷资源", "backsound", "开始游戏.mp3")
        if 公用按钮音效 and os.path.isfile(开始游戏路径):
            try:
                self._开始游戏音效_对象 = 公用按钮音效(开始游戏路径)
            except Exception:
                self._开始游戏音效_对象 = None
        else:
            self._开始游戏音效_对象 = None

        if not hasattr(self, "_浮动大图入场时长毫秒"):
            self._浮动大图入场时长毫秒 = 500

    def _播放按钮音效(self):
        self._确保公共交互()
        if self._按钮音效 is None:
            return
        try:
            self._按钮音效.播放()
        except Exception:
            pass

    def _播放翻页音效(self):
        self._确保公共交互()
        if self._翻页音效 is None:
            return
        try:
            if self._翻页音效通道 is not None:
                self._翻页音效通道.stop()
        except Exception:
            pass
        try:
            self._翻页音效通道 = self._翻页音效.play()
        except Exception:
            self._翻页音效通道 = None

    def _启动过渡(
        self,
        特效对象,
        目标矩形: pygame.Rect,
        回调: Callable[[], None],
        覆盖图片: Optional[pygame.Surface] = None,
    ):
        """
        ✅ 所有按钮/卡片/大图确认都走这个入口：
        - 默认播放统一按钮音效
        - 用“公用按钮点击特效”对截图做缩放
        - 特效结束后才执行回调（避免乱序）

        ✅ 例外：
        - 大图确认（开始游戏）不播放“全局按钮音效”，只由回调播放 backsound/开始游戏.mp3
        """
        self._确保公共交互()

        if 特效对象 is None:
            # 没特效就直接执行
            try:
                回调()
            except Exception:
                pass
            return

        # 正在过渡就忽略（避免连点乱序）
        if self._过渡_曾在播放 and self._过渡_特效 is not None:
            try:
                if self._过渡_特效.是否动画中():
                    return
            except Exception:
                pass

        # ✅ 是否播放全局按钮音效：大图确认要禁用
        是否播放全局按钮音效 = True
        try:
            if (
                getattr(self, "_特效_大图确认", None) is not None
                and 特效对象 is self._特效_大图确认
            ):
                是否播放全局按钮音效 = False
        except Exception:
            pass

        # 再加一道兜底：如果回调就是“大图确认处理”，也禁用全局按钮音效
        try:
            if getattr(回调, "__name__", "") == "_记录并处理大图确认点击":
                是否播放全局按钮音效 = False
        except Exception:
            pass

        # 播放统一音效（大图确认例外不播）
        if 是否播放全局按钮音效:
            self._播放按钮音效()

        if 覆盖图片 is not None:
            r = 目标矩形.copy()
            try:
                图片 = 覆盖图片.copy().convert_alpha()
            except Exception:
                图片 = 覆盖图片
        else:
            # 截图：一定要 clip 到屏幕范围，否则 subsurface 会崩
            try:
                屏幕矩形 = self.屏幕.get_rect()
                r = 目标矩形.clip(屏幕矩形)
                if r.w <= 0 or r.h <= 0:
                    r = pygame.Rect(max(0, 目标矩形.x), max(0, 目标矩形.y), 2, 2)
                    r = r.clip(屏幕矩形)
                if bool(getattr(self, "_应使用GPU界面", lambda: False)()):
                    合成画布 = pygame.Surface(self.屏幕.get_size(), pygame.SRCALPHA)
                    try:
                        self._合成GPU界面到画布(合成画布)
                    except Exception:
                        pass
                    try:
                        合成画布.blit(self.屏幕, (0, 0))
                    except Exception:
                        pass
                    图片 = 合成画布.subsurface(r).copy()
                else:
                    图片 = self.屏幕.subsurface(r).copy()
            except Exception:
                r = 目标矩形.copy()
                图片 = None

        try:
            特效对象.触发()
        except Exception:
            # 特效触发失败就直接执行回调
            try:
                回调()
            except Exception:
                pass
            return

        self._过渡_特效 = 特效对象
        self._过渡_图片 = 图片
        self._过渡_rect = r
        self._过渡_回调 = 回调
        self._过渡_曾在播放 = True

    def _更新过渡(self):
        if not getattr(self, "_过渡_曾在播放", False):
            return
        if self._过渡_特效 is None:
            self._过渡_曾在播放 = False
            return

        仍在动画中 = False
        try:
            仍在动画中 = bool(self._过渡_特效.是否动画中())
        except Exception:
            仍在动画中 = False

        if not 仍在动画中:
            self._过渡_曾在播放 = False
            回调 = self._过渡_回调
            self._过渡_回调 = None
            self._过渡_图片 = None
            try:
                if 回调:
                    回调()
            except Exception:
                pass

    def _绘制过渡(self):
        if self._过渡_特效 is None or self._过渡_图片 is None:
            return
        try:
            if self._过渡_特效.是否动画中():
                self._过渡_特效.绘制按钮(self.屏幕, self._过渡_图片, self._过渡_rect)
        except Exception:
            pass

    def _获取联网原图_尽力(self) -> Optional[pygame.Surface]:
        # 优先返回已缓存
        if getattr(self, "_联网原图_缓存", None) is not None:
            return self._联网原图_缓存

        图 = None

        # 1) 优先走 core/常量与路径.py（你给的最权威路径）
        try:
            from core.常量与路径 import 默认资源路径

            资源 = 默认资源路径()
            路径 = str(资源.get("投币_联网图标", "") or "")
            图 = 安全加载图片(路径, 透明=True)
            if 图 is not None:
                self._联网原图_缓存 = 图
                return 图
        except Exception:
            pass

        # 2) 兜底：硬猜路径（兼容你可能搬目录）
        候选 = [
            _资源路径("UI-img", "联网状态", "已联网.png"),
            _资源路径("UI-img", "联网状态", "联网.png"),
            _资源路径("UI-img", "选歌界面资源", "联网图标.png"),
            _资源路径("UI-img", "投币界面", "联网图标.png"),
        ]
        for p in 候选:
            try:
                if os.path.isfile(p):
                    图 = pygame.image.load(p).convert_alpha()
                    break
            except Exception:
                continue

        self._联网原图_缓存 = 图
        return 图

    def 安排点击动作(self, 高亮矩形: pygame.Rect, 动作: Callable[[], None]):
        """
        兼容老接口：以前你可能有 self.点击动效
        现在统一走：_启动过渡(按钮特效, 截图矩形, 动作)
        """
        self._确保公共交互()
        try:
            self._启动过渡(self._特效_按钮, 高亮矩形, 动作)
        except Exception:
            try:
                动作()
            except Exception:
                pass

    def 请求回主程序重新选歌(self):
        """
        ✅ 需求：点击“重选模式”不在选歌界面内部处理，而是退出选歌界面，
        返回一个状态给主程序.py，让主程序回到模式选择重新选。
        """
        self._返回状态 = "RESELECT_MAIN"
        self._需要退出 = True

def 绑定设置页方法到选歌游戏类():
    选歌游戏._设置页_持久化文件路径 = _设置页_持久化文件路径
    选歌游戏._设置页_从参数文本提取 = _设置页_从参数文本提取
    选歌游戏._设置页_构建参数文本 = _设置页_构建参数文本
    选歌游戏._设置页_读取持久化设置 = _设置页_读取持久化设置
    选歌游戏._设置页_写入持久化设置 = _设置页_写入持久化设置
    选歌游戏._设置页_加载持久化设置 = _设置页_加载持久化设置
    选歌游戏._设置页_保存持久化设置 = _设置页_保存持久化设置
    选歌游戏._确保设置页资源 = _确保设置页资源
    选歌游戏._设置页_同步参数 = _设置页_同步参数
    选歌游戏._设置页_取缩放图 = _设置页_取缩放图
    选歌游戏._重算设置页布局 = 重算设置页布局
    选歌游戏._设置页_缓入 = _设置页_缓入
    选歌游戏._设置页_缓出 = _设置页_缓出
    选歌游戏._设置页_点在有效面板区域 = _设置页_点在有效面板区域
    选歌游戏.打开设置页 = 打开设置页
    选歌游戏.关闭设置页 = 关闭设置页
    选歌游戏._设置页_切换选项 = _设置页_切换选项
    选歌游戏._设置页_切换背景 = _设置页_切换背景
    选歌游戏._设置页_处理事件 = _设置页_处理事件
    选歌游戏.绘制设置页 = 绘制设置页
绑定设置页方法到选歌游戏类()
_绑定选歌场景化方法模块(选歌游戏, 刷新选歌布局常量)
