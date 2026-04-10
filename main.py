import atexit
import os
import sys
import time
import inspect
import gc
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
from typing import Optional

from core.常量与路径 import 默认资源路径, 取运行根目录
from core.日志 import (
    初始化日志系统 as _初始化日志系统,
    取日志器 as _取日志器,
    记录异常 as _记录异常日志,
    记录信息 as _记录信息日志,
    取日志文件路径 as _取日志文件路径,
)
from core.对局状态 import 取每局所需信用
from core.渲染后端 import 创建显示后端, 取桌面尺寸, 取桌面刷新率
from core.踏板控制 import 解析踏板动作
from core.工具 import 获取字体
from core.音频 import 音乐管理
from core.视频 import 全局视频循环播放器, 选择第一个视频
from core.软件版本 import 读取当前版本号
from core.sqlite_store import (
    SCOPE_GLOBAL_SETTINGS as _全局设置存储作用域,
    read_scope as _读取存储作用域,
    replace_scope as _替换存储作用域,
    write_scope_patch as _写入存储作用域补丁,
)
from scenes.场景_投币 import 场景_投币
from scenes.场景_登陆磁卡 import 场景_登陆磁卡
from scenes.场景_个人资料 import 场景_个人资料
from scenes.场景_大模式 import 场景_大模式
from scenes.场景_子模式 import 场景_子模式
from scenes.场景_选歌 import 场景_选歌
from scenes.场景_加载页 import 场景_加载页
from scenes.场景_结算 import 场景_结算
from scenes.场景_谱面播放器 import 场景_谱面播放器
from ui.点击特效 import 序列帧特效资源, 全局点击特效管理器
from ui.场景过渡 import 公共黑屏过渡,公共丝滑入场
from ui.select_scene_esc_menu_host import SelectSceneEscMenuHost


def _启用稳定GC模式() -> bool:
    环境值 = str(os.environ.get("E5CM_SAFE_GC", "") or "").strip().lower()
    if 环境值 in ("1", "true", "yes", "on"):
        return True
    if 环境值 in ("0", "false", "no", "off"):
        return False
    return bool(getattr(sys, "frozen", False))


def _启用Windows高DPI感知():
    if os.name != "nt":
        return
    try:
        # 强制按物理像素坐标运行，避免 Win11 150% / 125% 把 SDL 坐标系虚拟成逻辑点。
        os.environ["SDL_WINDOWS_DPI_AWARENESS"] = "permonitorv2"
        os.environ["SDL_WINDOWS_DPI_SCALING"] = "0"
    except Exception:
        pass
    try:
        import ctypes

        user32 = ctypes.windll.user32
        try:
            shcore = ctypes.windll.shcore
        except Exception:
            shcore = None

        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            try:
                if bool(user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))):
                    return
            except Exception:
                pass
        if shcore is not None and hasattr(shcore, "SetProcessDpiAwareness"):
            try:
                shcore.SetProcessDpiAwareness(2)
                return
            except Exception:
                pass
        if hasattr(user32, "SetProcessDPIAware"):
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass
    except Exception:
        pass


def _读取布尔环境变量(键名: str, 默认值: bool = False) -> bool:
    文本 = str(os.environ.get(str(键名), "") or "").strip().lower()
    if 文本 in ("1", "true", "yes", "on"):
        return True
    if 文本 in ("0", "false", "no", "off"):
        return False
    return bool(默认值)


def _读取Windows系统缩放系数() -> float:
    if os.name != "nt":
        return 1.0
    try:
        import ctypes

        user32 = ctypes.windll.user32
        dpi值 = 0

        hwnd = 0
        try:
            hwnd = int(user32.GetForegroundWindow() or 0)
        except Exception:
            hwnd = 0
        if hwnd <= 0 and hasattr(user32, "GetDesktopWindow"):
            try:
                hwnd = int(user32.GetDesktopWindow() or 0)
            except Exception:
                hwnd = 0

        if hwnd > 0 and hasattr(user32, "GetDpiForWindow"):
            try:
                dpi值 = int(user32.GetDpiForWindow(hwnd) or 0)
            except Exception:
                dpi值 = 0
        if dpi值 <= 0 and hasattr(user32, "GetDpiForSystem"):
            try:
                dpi值 = int(user32.GetDpiForSystem() or 0)
            except Exception:
                dpi值 = 0
        if dpi值 <= 0:
            try:
                hdc = user32.GetDC(0)
                if hdc:
                    try:
                        gdi32 = ctypes.windll.gdi32
                        LOGPIXELSX = 88
                        dpi值 = int(gdi32.GetDeviceCaps(hdc, LOGPIXELSX) or 0)
                    finally:
                        try:
                            user32.ReleaseDC(0, hdc)
                        except Exception:
                            pass
            except Exception:
                dpi值 = 0

        if dpi值 <= 0:
            return 1.0
        return float(max(0.5, min(4.0, float(dpi值) / 96.0)))
    except Exception:
        return 1.0


def _应用Windows高DPI启动保底策略(启动调试设置: dict, 日志器) -> dict:
    信息 = {
        "已启用": False,
        "缩放系数": 1.0,
        "缩放百分比": 100,
        "调整项": [],
    }
    if os.name != "nt" or (not isinstance(启动调试设置, dict)):
        return 信息

    策略文本 = str(os.environ.get("E5CM_HIGHDPI_SAFE_LAUNCH", "auto") or "auto").strip().lower()
    if 策略文本 in ("0", "false", "no", "off", "disable", "disabled"):
        return 信息

    缩放系数 = float(_读取Windows系统缩放系数())
    信息["缩放系数"] = float(缩放系数)
    信息["缩放百分比"] = int(round(float(缩放系数) * 100.0))

    强制启用 = 策略文本 in ("1", "true", "yes", "on", "force", "enabled")
    自动启用 = 策略文本 in ("", "auto")
    if (not bool(强制启用)) and (
        (not bool(自动启用)) or float(缩放系数) < 1.35
    ):
        return 信息

    调整项: list[str] = []
    # auto 模式下只做轻量保底，避免在 2K/4K + 高缩放环境把正常全屏误降级为窗口模式。
    # 如需旧版“强制窗口化/CPU”的重度保底，可设 E5CM_HIGHDPI_SAFE_LAUNCH=force。
    启用重度保底 = bool(强制启用)

    当前后端 = str(启动调试设置.get("默认渲染后端", "") or "").strip().lower()
    if bool(启用重度保底) and 当前后端.startswith("gpu-"):
        启动调试设置["默认渲染后端"] = "software"
        调整项.append("默认渲染后端=software")

    if bool(启用重度保底) and str(启动调试设置.get("默认显示模式", "") or "").strip().lower() == "borderless":
        启动调试设置["默认显示模式"] = "windowed"
        调整项.append("默认显示模式=windowed")

    if bool(启动调试设置.get("显示启动幻灯片", True)):
        启动调试设置["显示启动幻灯片"] = False
        调整项.append("显示启动幻灯片=False")

    try:
        原窗口w = int(启动调试设置.get("默认窗口宽", 1600) or 1600)
        原窗口h = int(启动调试设置.get("默认窗口高", 900) or 900)
    except Exception:
        原窗口w, 原窗口h = 1600, 900
    安全窗口w = max(960, min(1920, int(原窗口w)))
    安全窗口h = max(540, min(1080, int(原窗口h)))
    if (安全窗口w, 安全窗口h) != (原窗口w, 原窗口h):
        启动调试设置["默认窗口宽"] = int(安全窗口w)
        启动调试设置["默认窗口高"] = int(安全窗口h)
        调整项.append(f"默认窗口尺寸={安全窗口w}x{安全窗口h}")

    os.environ.setdefault("E5CM_VIDEO_DISABLE_GRAB", "1")
    调整项.append("E5CM_VIDEO_DISABLE_GRAB=1")

    信息["已启用"] = True
    信息["调整项"] = list(调整项)
    try:
        _记录信息日志(
            日志器,
            "启用Windows高DPI启动保底策略 "
            f"缩放={信息['缩放百分比']}% "
            f"调整={', '.join(list(调整项) or ['无'])}",
        )
    except Exception:
        pass
    return 信息


def _取Windows显示设置上下文():
    if os.name != "nt":
        return None

    已缓存 = getattr(_取Windows显示设置上下文, "_cache", None)
    if 已缓存 is False:
        return None
    if isinstance(已缓存, dict):
        return 已缓存

    try:
        import ctypes
        from ctypes import wintypes

        CCHDEVICENAME = 32
        CCHFORMNAME = 32
        ENUM_CURRENT_SETTINGS = -1

        class POINTL(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class _打印字段(ctypes.Structure):
            _fields_ = [
                ("dmOrientation", ctypes.c_short),
                ("dmPaperSize", ctypes.c_short),
                ("dmPaperLength", ctypes.c_short),
                ("dmPaperWidth", ctypes.c_short),
                ("dmScale", ctypes.c_short),
                ("dmCopies", ctypes.c_short),
                ("dmDefaultSource", ctypes.c_short),
                ("dmPrintQuality", ctypes.c_short),
            ]

        class _显示字段(ctypes.Structure):
            _fields_ = [
                ("dmPosition", POINTL),
                ("dmDisplayOrientation", wintypes.DWORD),
                ("dmDisplayFixedOutput", wintypes.DWORD),
            ]

        class _DUMMYUNIONNAME(ctypes.Union):
            _fields_ = [
                ("printer", _打印字段),
                ("display", _显示字段),
            ]

        class _DUMMYUNIONNAME2(ctypes.Union):
            _fields_ = [
                ("dmDisplayFlags", wintypes.DWORD),
                ("dmNup", wintypes.DWORD),
            ]

        class DEVMODEW(ctypes.Structure):
            _anonymous_ = ("u1", "u2")
            _fields_ = [
                ("dmDeviceName", wintypes.WCHAR * CCHDEVICENAME),
                ("dmSpecVersion", wintypes.WORD),
                ("dmDriverVersion", wintypes.WORD),
                ("dmSize", wintypes.WORD),
                ("dmDriverExtra", wintypes.WORD),
                ("dmFields", wintypes.DWORD),
                ("u1", _DUMMYUNIONNAME),
                ("dmColor", ctypes.c_short),
                ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short),
                ("dmFormName", wintypes.WCHAR * CCHFORMNAME),
                ("dmLogPixels", wintypes.WORD),
                ("dmBitsPerPel", wintypes.DWORD),
                ("dmPelsWidth", wintypes.DWORD),
                ("dmPelsHeight", wintypes.DWORD),
                ("u2", _DUMMYUNIONNAME2),
                ("dmDisplayFrequency", wintypes.DWORD),
                ("dmICMMethod", wintypes.DWORD),
                ("dmICMIntent", wintypes.DWORD),
                ("dmMediaType", wintypes.DWORD),
                ("dmDitherType", wintypes.DWORD),
                ("dmReserved1", wintypes.DWORD),
                ("dmReserved2", wintypes.DWORD),
                ("dmPanningWidth", wintypes.DWORD),
                ("dmPanningHeight", wintypes.DWORD),
            ]

        用户32 = ctypes.windll.user32
        LPDEVMODEW = ctypes.POINTER(DEVMODEW)
        用户32.EnumDisplaySettingsW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            LPDEVMODEW,
        ]
        用户32.EnumDisplaySettingsW.restype = wintypes.BOOL
        用户32.ChangeDisplaySettingsW.argtypes = [LPDEVMODEW, wintypes.DWORD]
        用户32.ChangeDisplaySettingsW.restype = wintypes.LONG

        上下文 = {
            "ctypes": ctypes,
            "用户32": 用户32,
            "DEVMODEW": DEVMODEW,
            "ENUM_CURRENT_SETTINGS": ENUM_CURRENT_SETTINGS,
            "DM_BITSPERPEL": 0x00040000,
            "DM_PELSWIDTH": 0x00080000,
            "DM_PELSHEIGHT": 0x00100000,
            "DM_DISPLAYFREQUENCY": 0x00400000,
            "CDS_TEST": 0x00000002,
            "CDS_FULLSCREEN": 0x00000004,
            "DISP_CHANGE_SUCCESSFUL": 0,
        }
        setattr(_取Windows显示设置上下文, "_cache", 上下文)
        return 上下文
    except Exception:
        setattr(_取Windows显示设置上下文, "_cache", False)
        return None


def _取Windows当前显示模式() -> Optional[dict]:
    上下文 = _取Windows显示设置上下文()
    if not isinstance(上下文, dict):
        return None

    try:
        ctypes = 上下文["ctypes"]
        用户32 = 上下文["用户32"]
        DEVMODEW = 上下文["DEVMODEW"]
        ENUM_CURRENT_SETTINGS = int(上下文["ENUM_CURRENT_SETTINGS"])

        模式 = DEVMODEW()
        模式.dmSize = ctypes.sizeof(DEVMODEW)
        if not bool(用户32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(模式))):
            return None
        return {
            "宽": int(模式.dmPelsWidth or 0),
            "高": int(模式.dmPelsHeight or 0),
            "色深": int(模式.dmBitsPerPel or 32),
            "刷新率": int(模式.dmDisplayFrequency or 0),
        }
    except Exception:
        return None


def _尝试临时切换Windows桌面到1080p(
    目标宽: int = 1920,
    目标高: int = 1080,
) -> dict:
    上下文 = _取Windows显示设置上下文()
    if not isinstance(上下文, dict):
        return {"成功": False, "已切换": False, "原因": "Windows 显示 API 不可用"}

    当前模式 = _取Windows当前显示模式()
    if not isinstance(当前模式, dict):
        return {"成功": False, "已切换": False, "原因": "读取当前桌面模式失败"}

    当前宽 = int(当前模式.get("宽", 0) or 0)
    当前高 = int(当前模式.get("高", 0) or 0)
    if 当前宽 <= int(目标宽) and 当前高 <= int(目标高):
        return {
            "成功": True,
            "已切换": False,
            "原因": "当前桌面分辨率无需降级",
            "当前模式": dict(当前模式),
        }

    ctypes = 上下文["ctypes"]
    用户32 = 上下文["用户32"]
    DEVMODEW = 上下文["DEVMODEW"]
    ENUM_CURRENT_SETTINGS = int(上下文["ENUM_CURRENT_SETTINGS"])
    DM_BITSPERPEL = int(上下文["DM_BITSPERPEL"])
    DM_PELSWIDTH = int(上下文["DM_PELSWIDTH"])
    DM_PELSHEIGHT = int(上下文["DM_PELSHEIGHT"])
    DM_DISPLAYFREQUENCY = int(上下文["DM_DISPLAYFREQUENCY"])
    CDS_TEST = int(上下文["CDS_TEST"])
    CDS_FULLSCREEN = int(上下文["CDS_FULLSCREEN"])
    DISP_CHANGE_SUCCESSFUL = int(上下文["DISP_CHANGE_SUCCESSFUL"])

    当前刷新率 = int(当前模式.get("刷新率", 0) or 0)
    字段候选列表 = []
    if 当前刷新率 > 0:
        字段候选列表.append(
            (DM_PELSWIDTH | DM_PELSHEIGHT | DM_BITSPERPEL | DM_DISPLAYFREQUENCY, 当前刷新率)
        )
    字段候选列表.append((DM_PELSWIDTH | DM_PELSHEIGHT | DM_BITSPERPEL, 0))

    最后返回码 = None
    for 字段, 刷新率 in 字段候选列表:
        模式 = DEVMODEW()
        模式.dmSize = ctypes.sizeof(DEVMODEW)
        if not bool(用户32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(模式))):
            continue
        模式.dmPelsWidth = int(目标宽)
        模式.dmPelsHeight = int(目标高)
        模式.dmBitsPerPel = int(当前模式.get("色深", 32) or 32)
        模式.dmFields = int(字段)
        if int(字段) & int(DM_DISPLAYFREQUENCY) and int(刷新率) > 0:
            模式.dmDisplayFrequency = int(刷新率)

        测试返回码 = int(用户32.ChangeDisplaySettingsW(ctypes.byref(模式), CDS_TEST))
        最后返回码 = int(测试返回码)
        if int(测试返回码) != int(DISP_CHANGE_SUCCESSFUL):
            continue

        应用返回码 = int(用户32.ChangeDisplaySettingsW(ctypes.byref(模式), CDS_FULLSCREEN))
        最后返回码 = int(应用返回码)
        if int(应用返回码) == int(DISP_CHANGE_SUCCESSFUL):
            新模式 = _取Windows当前显示模式()
            return {
                "成功": True,
                "已切换": True,
                "切换前模式": dict(当前模式),
                "切换后模式": dict(新模式 or {}),
            }

    return {
        "成功": False,
        "已切换": False,
        "原因": f"ChangeDisplaySettingsW 返回 {最后返回码}",
        "当前模式": dict(当前模式),
    }


def _恢复Windows桌面显示设置() -> bool:
    上下文 = _取Windows显示设置上下文()
    if not isinstance(上下文, dict):
        return False

    try:
        用户32 = 上下文["用户32"]
        DISP_CHANGE_SUCCESSFUL = int(上下文["DISP_CHANGE_SUCCESSFUL"])
        返回码 = int(用户32.ChangeDisplaySettingsW(None, 0))
        return int(返回码) == int(DISP_CHANGE_SUCCESSFUL)
    except Exception:
        return False


def _桌面需要全局1080p渲染策略(
    桌面尺寸: Optional[tuple[int, int]] = None,
) -> bool:
    try:
        if isinstance(桌面尺寸, tuple) and len(桌面尺寸) >= 2:
            桌面w = int(桌面尺寸[0] or 0)
            桌面h = int(桌面尺寸[1] or 0)
        else:
            桌面w, 桌面h = tuple(取桌面尺寸((1280, 720)))
            桌面w = int(桌面w or 0)
            桌面h = int(桌面h or 0)
    except Exception:
        return False
    return int(桌面w) > 1920 or int(桌面h) > 1080


def _取应用目标桌面尺寸(
    默认尺寸: tuple[int, int] = (1280, 720),
) -> tuple[int, int]:
    try:
        桌面w, 桌面h = tuple(取桌面尺寸(默认尺寸))
        桌面w = int(桌面w or 默认尺寸[0])
        桌面h = int(桌面h or 默认尺寸[1])
    except Exception:
        桌面w, 桌面h = int(默认尺寸[0]), int(默认尺寸[1])
    if bool(_桌面需要全局1080p渲染策略((桌面w, 桌面h))):
        return 1920, 1080
    return int(桌面w), int(桌面h)


def 主函数():
    显示后端 = None
    _保存全局设置 = None
    日志器 = _取日志器("main")
    try:
        日志器 = _初始化日志系统(取运行根目录(), 控制台输出=False)
    except Exception as 异常:
        _记录异常日志(日志器, "日志系统初始化失败", 异常)
    _记录信息日志(日志器, "主函数启动")
    _启用Windows高DPI感知()

    if bool(_启用稳定GC模式()):
        try:
            if bool(gc.isenabled()):
                gc.disable()
            _记录信息日志(
                日志器,
                "已启用稳定GC模式：默认关闭循环GC（可用 E5CM_SAFE_GC=0 关闭）",
            )
        except Exception as 异常:
            _记录异常日志(日志器, "启用稳定GC模式失败", 异常)

    def _激活谱面播放器输入焦点(场景对象):
        try:
            场景名 = str(getattr(场景对象, "名称", "") or "")
        except Exception:
            场景名 = ""
        if 场景名 != "谱面播放器":
            return
        try:
            if 显示后端 is not None:
                getattr(显示后端, "激活窗口", lambda: False)()
        except Exception:
            pass

    def _安全进入场景(场景对象, 载荷):
        try:
            进入方法 = getattr(场景对象, "进入", None)
            if 进入方法 is None:
                return

            签名 = inspect.signature(进入方法)
            参数列表 = list(签名.parameters.values())

            有可变参数 = any(
                p.kind
                in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                for p in 参数列表
            )

            if 有可变参数:
                进入方法(载荷)
                _激活谱面播放器输入焦点(场景对象)
                return

            if len(参数列表) == 0:
                进入方法()
                _激活谱面播放器输入焦点(场景对象)
                return

            if len(参数列表) == 1 and 参数列表[0].name == "self":
                进入方法()
                _激活谱面播放器输入焦点(场景对象)
                return

            进入方法(载荷)
            _激活谱面播放器输入焦点(场景对象)
            return

        except TypeError as 异常:
            文本 = str(异常)
            if (
                ("positional argument" in 文本)
                or ("unexpected" in 文本)
                or ("takes" in 文本)
            ):
                getattr(场景对象, "进入")()
                _激活谱面播放器输入焦点(场景对象)
                return
            raise

    def _取运行根目录() -> str:
        return 取运行根目录()

    def _同步屏幕引用():
        nonlocal 屏幕
        if 显示后端 is None:
            return
        try:
            屏幕 = 显示后端.取绘制屏幕()
        except Exception:
            return
        try:
            上下文["屏幕"] = 屏幕
        except Exception:
            pass
        try:
            刷新率 = int(
                getattr(显示后端, "取桌面刷新率", lambda: 取桌面刷新率(60))() or 60
            )
        except Exception:
            刷新率 = int(取桌面刷新率(60) or 60)
        刷新率 = int(max(30, min(240, 刷新率)))
        try:
            状态["显示器刷新率"] = int(刷新率)
        except Exception:
            pass
        try:
            上下文["显示器刷新率"] = int(刷新率)
        except Exception:
            pass

    def _取当前显示模式标识() -> str:
        return "borderless" if bool(是否全屏) else "windowed"

    def _取当前显示模式文本() -> str:
        return "无边框窗口" if bool(是否全屏) else "窗口"

    def _切换全屏():
        nonlocal 是否全屏, 屏幕

        if not bool(是否全屏):
            当前w, 当前h = _取当前全屏尺寸()
            _应用全屏分辨率(
                当前w,
                当前h,
                发送事件=False,
                保存设置=False,
            )
            return

        当前w, 当前h = _取当前窗口化尺寸()
        _应用窗口化分辨率(
            当前w,
            当前h,
            发送事件=False,
            保存设置=False,
        )

    def _发送窗口尺寸变化事件(宽: object, 高: object):
        尺寸变化事件 = None
        try:
            尺寸变化事件 = pygame.event.Event(
                pygame.VIDEORESIZE,
                {
                    "w": int(max(1, int(宽 or 1))),
                    "h": int(max(1, int(高 or 1))),
                },
            )
            pygame.event.post(尺寸变化事件)
        except Exception:
            尺寸变化事件 = None
        if 尺寸变化事件 is None:
            return
        try:
            场景对象 = 当前场景
        except Exception:
            场景对象 = None
        if 场景对象 is None:
            return
        处理事件 = getattr(场景对象, "处理事件", None)
        if not callable(处理事件):
            return
        try:
            处理事件(
                pygame.event.Event(
                    pygame.VIDEORESIZE,
                    {
                        "w": int(getattr(尺寸变化事件, "w", 1) or 1),
                        "h": int(getattr(尺寸变化事件, "h", 1) or 1),
                    },
                )
            )
        except Exception:
            pass

    def _播放开场幻灯片(图片目录: str):
        if (not 图片目录) or (not os.path.isdir(图片目录)):
            return

        图片路径列表 = []
        try:
            for 文件名 in sorted(os.listdir(图片目录)):
                小写名 = str(文件名).lower()
                if 小写名.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
                    图片路径列表.append(os.path.join(图片目录, 文件名))
        except Exception:
            图片路径列表 = []

        if not 图片路径列表:
            return

        def _加载并缩放图片(图片路径: str, 目标尺寸: tuple[int, int]) -> pygame.Surface | None:
            try:
                原图 = pygame.image.load(图片路径)
            except Exception:
                return None

            try:
                if 原图.get_alpha() is not None:
                    原图 = 原图.convert_alpha()
                else:
                    原图 = 原图.convert()
            except Exception:
                pass

            try:
                原宽, 原高 = 原图.get_size()
                目标宽, 目标高 = 目标尺寸
                if 原宽 <= 0 or 原高 <= 0 or 目标宽 <= 0 or 目标高 <= 0:
                    return 原图

                缩放比例 = min(目标宽 / 原宽, 目标高 / 原高)
                新宽 = max(1, int(round(原宽 * 缩放比例)))
                新高 = max(1, int(round(原高 * 缩放比例)))

                if 新宽 == 原宽 and 新高 == 原高:
                    return 原图

                return pygame.transform.smoothscale(原图, (新宽, 新高))
            except Exception:
                return 原图

        def _绘制居中图片(屏幕面: pygame.Surface, 图片面: pygame.Surface, 透明度: int):
            if 图片面 is None:
                return
            try:
                图片副本 = 图片面.copy()
                图片副本.set_alpha(max(0, min(255, int(透明度))))
            except Exception:
                图片副本 = 图片面

            屏幕宽, 屏幕高 = 屏幕面.get_size()
            图片宽, 图片高 = 图片副本.get_size()
            位置x = (屏幕宽 - 图片宽) // 2
            位置y = (屏幕高 - 图片高) // 2
            屏幕面.blit(图片副本, (位置x, 位置y))

        def _提交开场帧():
            if 显示后端 is not None:
                显示后端.呈现()
                return
            pygame.display.flip()

        def _处理开场事件():
            for 原始事件 in pygame.event.get():
                事件列表 = (
                    显示后端.处理事件(原始事件)
                    if 显示后端 is not None
                    else [原始事件]
                )
                for 事件 in 事件列表:
                    if 事件.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit(0)

                    if 事件.type == pygame.KEYDOWN:
                        if 事件.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit(0)

                    if 事件.type == pygame.VIDEORESIZE and (not 是否全屏):
                        新w = int(max(960, int(getattr(事件, "w", 0) or 0)))
                        新h = int(max(540, int(getattr(事件, "h", 0) or 0)))
                        _应用窗口化分辨率(新w, 新h, 发送事件=False)

        渐显秒 = 2.0
        停留秒 = 1.0
        切换秒 = 0.9
        收尾渐隐秒 = 1.5
        
        播放时钟 = pygame.time.Clock()
        已缓存图片 = {}
        当前屏幕尺寸 = 上下文["屏幕"].get_size()

        def _取缓存图片(图片路径: str) -> pygame.Surface | None:
            nonlocal 当前屏幕尺寸
            最新尺寸 = 上下文["屏幕"].get_size()
            if 最新尺寸 != 当前屏幕尺寸:
                当前屏幕尺寸 = 最新尺寸
                已缓存图片.clear()

            缓存键 = f"{图片路径}|{当前屏幕尺寸[0]}x{当前屏幕尺寸[1]}"
            if 缓存键 in 已缓存图片:
                return 已缓存图片[缓存键]

            图片面 = _加载并缩放图片(图片路径, 当前屏幕尺寸)
            if 图片面 is not None:
                已缓存图片[缓存键] = 图片面
            return 图片面

        if len(图片路径列表) == 1:
            当前图片路径 = 图片路径列表[0]
            开始时间 = time.perf_counter()
            while True:
                _处理开场事件()
                已过秒 = time.perf_counter() - 开始时间
                总秒 = 渐显秒 + 停留秒 + 收尾渐隐秒

                if 已过秒 >= 总秒:
                    break

                if 已过秒 < 渐显秒:
                    透明度 = int(255 * (已过秒 / max(0.001, 渐显秒)))
                elif 已过秒 < 渐显秒 + 停留秒:
                    透明度 = 255
                else:
                    收尾进度 = (已过秒 - 渐显秒 - 停留秒) / max(0.001, 收尾渐隐秒)
                    透明度 = int(255 * (1.0 - 收尾进度))

                当前图片面 = _取缓存图片(当前图片路径)

                上下文["屏幕"].fill((0, 0, 0))
                if 当前图片面 is not None:
                    _绘制居中图片(上下文["屏幕"], 当前图片面, 透明度)
                _提交开场帧()
                播放时钟.tick(60)
            return

        第一个图片路径 = 图片路径列表[0]
        开始时间 = time.perf_counter()

        while True:
            _处理开场事件()
            已过秒 = time.perf_counter() - 开始时间
            if 已过秒 >= 渐显秒 + 停留秒:
                break

            if 已过秒 < 渐显秒:
                当前透明度 = int(255 * (已过秒 / max(0.001, 渐显秒)))
            else:
                当前透明度 = 255

            当前图片面 = _取缓存图片(第一个图片路径)

            上下文["屏幕"].fill((0, 0, 0))
            if 当前图片面 is not None:
                _绘制居中图片(上下文["屏幕"], 当前图片面, 当前透明度)
            _提交开场帧()
            播放时钟.tick(60)

        for 索引 in range(len(图片路径列表) - 1):
            当前图片路径 = 图片路径列表[索引]
            下一张图片路径 = 图片路径列表[索引 + 1]

            当前图片面 = _取缓存图片(当前图片路径)
            下一张图片面 = _取缓存图片(下一张图片路径)

            切换开始时间 = time.perf_counter()
            while True:
                _处理开场事件()
                已过秒 = time.perf_counter() - 切换开始时间
                if 已过秒 >= 切换秒:
                    break

                进度 = max(0.0, min(1.0, 已过秒 / max(0.001, 切换秒)))
                当前透明度 = int(255 * (1.0 - 进度))
                下一张透明度 = int(255 * 进度)

                上下文["屏幕"].fill((0, 0, 0))
                if 当前图片面 is not None:
                    _绘制居中图片(上下文["屏幕"], 当前图片面, 当前透明度)
                if 下一张图片面 is not None:
                    _绘制居中图片(上下文["屏幕"], 下一张图片面, 下一张透明度)
                _提交开场帧()
                播放时钟.tick(60)

            if 索引 + 1 < len(图片路径列表) - 1:
                停留开始时间 = time.perf_counter()
                while True:
                    _处理开场事件()
                    已过秒 = time.perf_counter() - 停留开始时间
                    if 已过秒 >= 停留秒:
                        break

                    下一张图片面 = _取缓存图片(下一张图片路径)
                    上下文["屏幕"].fill((0, 0, 0))
                    if 下一张图片面 is not None:
                        _绘制居中图片(上下文["屏幕"], 下一张图片面, 255)
                    _提交开场帧()
                    播放时钟.tick(60)

        最后一张图片路径 = 图片路径列表[-1]
        结尾停留开始时间 = time.perf_counter()
        while True:
            _处理开场事件()
            已过秒 = time.perf_counter() - 结尾停留开始时间
            if 已过秒 >= 停留秒:
                break

            最后一张图片面 = _取缓存图片(最后一张图片路径)
            上下文["屏幕"].fill((0, 0, 0))
            if 最后一张图片面 is not None:
                _绘制居中图片(上下文["屏幕"], 最后一张图片面, 255)
            _提交开场帧()
            播放时钟.tick(60)

        收尾开始时间 = time.perf_counter()
        while True:
            _处理开场事件()
            已过秒 = time.perf_counter() - 收尾开始时间
            if 已过秒 >= 收尾渐隐秒:
                break

            收尾进度 = max(0.0, min(1.0, 已过秒 / max(0.001, 收尾渐隐秒)))
            最后一张透明度 = int(255 * (1.0 - 收尾进度))

            最后一张图片面 = _取缓存图片(最后一张图片路径)
            上下文["屏幕"].fill((0, 0, 0))
            if 最后一张图片面 is not None:
                _绘制居中图片(上下文["屏幕"], 最后一张图片面, 最后一张透明度)
            _提交开场帧()
            播放时钟.tick(60)

        上下文["屏幕"].fill((0, 0, 0))
        _提交开场帧()

    def _退出程序():
        音乐.停止()
        try:
            if callable(_保存全局设置):
                _保存全局设置()
        except Exception:
            pass
        try:
            背景视频.关闭()
        except Exception:
            pass
        try:
            if 显示后端 is not None:
                显示后端.关闭()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass
        try:
            _恢复1080p全屏兼容(原因="正常退出程序")
        except Exception:
            pass
        _标记会话状态("clean")
        sys.exit(0)

    def _默认渲染引擎偏好() -> str:
        return "gpu-d3d11" if os.name == "nt" else "gpu-auto"

    启动时已启用1080p全屏兼容 = False
    当前会话已切到1080p全屏兼容 = False

    def _当前桌面需要1080p全屏兼容(模式信息: Optional[dict] = None) -> bool:
        模式 = 模式信息 if isinstance(模式信息, dict) else _取Windows当前显示模式()
        if not isinstance(模式, dict):
            return False
        try:
            当前宽 = int(模式.get("宽", 0) or 0)
            当前高 = int(模式.get("高", 0) or 0)
        except Exception:
            return False
        return int(当前宽) > 1920 or int(当前高) > 1080

    def _启用1080p全屏兼容(*, 原因: str) -> bool:
        nonlocal 启动时已启用1080p全屏兼容, 当前会话已切到1080p全屏兼容

        if os.name != "nt":
            return False
        if bool(当前会话已切到1080p全屏兼容):
            return True

        当前模式 = _取Windows当前显示模式()
        if not bool(_当前桌面需要1080p全屏兼容(当前模式)):
            return False

        结果 = _尝试临时切换Windows桌面到1080p(1920, 1080)
        if not bool(结果.get("成功", False)) or not bool(结果.get("已切换", False)):
            try:
                _记录信息日志(
                    日志器,
                    f"1080p全屏兼容模式启用失败 原因={原因} 详情={结果}",
                )
            except Exception:
                pass
            return False

        当前会话已切到1080p全屏兼容 = True
        if not bool(启动时已启用1080p全屏兼容):
            启动时已启用1080p全屏兼容 = ("启动" in str(原因 or ""))
        try:
            _记录信息日志(
                日志器,
                f"已启用1080p全屏兼容模式 原因={原因} 模式={结果}",
            )
        except Exception:
            pass
        try:
            time.sleep(0.15)
        except Exception:
            pass
        return True

    def _恢复1080p全屏兼容(*, 原因: str) -> bool:
        nonlocal 当前会话已切到1080p全屏兼容

        if not bool(当前会话已切到1080p全屏兼容):
            return False

        已恢复 = bool(_恢复Windows桌面显示设置())
        当前模式 = _取Windows当前显示模式()
        if isinstance(当前模式, dict) and bool(_当前桌面需要1080p全屏兼容(当前模式)):
            当前会话已切到1080p全屏兼容 = False
        elif bool(已恢复):
            当前会话已切到1080p全屏兼容 = False

        try:
            _记录信息日志(
                日志器,
                f"1080p全屏兼容模式恢复结果 原因={原因} 成功={已恢复} 当前模式={当前模式}",
            )
        except Exception:
            pass
        return bool(已恢复)

    atexit.register(lambda: _恢复1080p全屏兼容(原因="进程退出"))

    def _规范渲染后端偏好(值: object, 默认值: Optional[str] = None) -> str:
        默认文本 = str(默认值 or _默认渲染引擎偏好() or "gpu-auto")
        文本 = str(值 or 默认文本).strip().lower().replace("_", "-")
        if 文本 in ("gpu", "gpu-sdl2", "sdl2", "auto", "gpu-auto"):
            return "gpu-auto"
        if 文本 in ("gpu-d3d11", "d3d11", "direct3d11"):
            return "gpu-d3d11"
        if 文本 in ("gpu-opengl", "opengl", "ogl"):
            return "gpu-opengl"
        if 文本 in ("software", "cpu", "cpu-software"):
            return "software"
        return str(默认文本)

    def _读取正整数设置(值: object, 默认值: int) -> int:
        try:
            整数值 = int(值)
        except Exception:
            整数值 = int(默认值)
        return max(1, int(整数值))

    def _标记会话状态(状态值: object):
        try:
            文本 = str(状态值 or "").strip().lower() or "clean"
            _写入存储作用域补丁(
                _全局设置存储作用域,
                {"最近会话状态": str(文本)},
            )
        except Exception:
            pass

    def _读取启动调试设置() -> dict:
        try:
            默认全屏宽, 默认全屏高 = tuple(_取应用目标桌面尺寸((1600, 900)))
        except Exception:
            默认全屏宽, 默认全屏高 = (1600, 900)
        默认设置 = {
            "默认渲染后端": _默认渲染引擎偏好(),
            "默认GPU谱面管线": True,
            "打包版选歌强制CPU兼容": False,
            "默认显示模式": "borderless",
            "显示性能调试信息": False,
            "显示状态HUD": True,
            "显示启动幻灯片": True,
            "显示谱面开场动画": True,
            "全局静音": False,
            "开发默认选歌载荷启用": True,
            "开发默认选歌类型": "竞速",
            "开发默认选歌模式": "混音",
            "默认窗口宽": 1600,
            "默认窗口高": 900,
            "默认全屏宽": int(默认全屏宽),
            "默认全屏高": int(默认全屏高),
        }
        数据 = _读取存储作用域(_全局设置存储作用域)
        if not isinstance(数据, dict):
            数据 = {}

        结果 = dict(默认设置)
        结果["默认渲染后端"] = _规范渲染后端偏好(
            数据.get("默认渲染后端", 默认设置["默认渲染后端"]),
            默认值=str(默认设置["默认渲染后端"]),
        )
        结果["默认GPU谱面管线"] = bool(
            数据.get("默认GPU谱面管线", 默认设置["默认GPU谱面管线"])
        )
        结果["打包版选歌强制CPU兼容"] = bool(
            数据.get(
                "打包版选歌强制CPU兼容",
                默认设置["打包版选歌强制CPU兼容"],
            )
        )
        默认显示模式文本 = str(
            数据.get("默认显示模式", 默认设置["默认显示模式"]) or "windowed"
        ).strip().lower()
        if 默认显示模式文本 in (
            "borderless",
            "borderless_window",
            "fullscreen",
            "全屏",
            "无边框",
            "无边框窗口",
        ):
            结果["默认显示模式"] = "borderless"
        else:
            结果["默认显示模式"] = "windowed"
        结果["显示性能调试信息"] = bool(
            数据.get("显示性能调试信息", 默认设置["显示性能调试信息"])
        )
        结果["显示状态HUD"] = bool(
            数据.get("显示状态HUD", 默认设置["显示状态HUD"])
        )
        结果["显示启动幻灯片"] = bool(
            数据.get("显示启动幻灯片", 默认设置["显示启动幻灯片"])
        )
        结果["显示谱面开场动画"] = bool(
            数据.get("显示谱面开场动画", 默认设置["显示谱面开场动画"])
        )
        结果["全局静音"] = bool(
            数据.get("全局静音", 默认设置["全局静音"])
        )
        结果["开发默认选歌载荷启用"] = bool(
            数据.get(
                "开发默认选歌载荷启用",
                默认设置["开发默认选歌载荷启用"],
            )
        )
        结果["开发默认选歌类型"] = str(
            数据.get("开发默认选歌类型", 默认设置["开发默认选歌类型"]) or "竞速"
        ).strip() or "竞速"
        结果["开发默认选歌模式"] = str(
            数据.get("开发默认选歌模式", 默认设置["开发默认选歌模式"]) or "混音"
        ).strip() or "混音"
        结果["默认窗口宽"] = _读取正整数设置(
            数据.get("默认窗口宽", 默认设置["默认窗口宽"]),
            默认设置["默认窗口宽"],
        )
        结果["默认窗口高"] = _读取正整数设置(
            数据.get("默认窗口高", 默认设置["默认窗口高"]),
            默认设置["默认窗口高"],
        )
        结果["默认全屏宽"] = _读取正整数设置(
            数据.get("默认全屏宽", 默认设置["默认全屏宽"]),
            默认设置["默认全屏宽"],
        )
        结果["默认全屏高"] = _读取正整数设置(
            数据.get("默认全屏高", 默认设置["默认全屏高"]),
            默认设置["默认全屏高"],
        )
        结果["默认全屏尺寸是否已保存"] = bool(
            ("默认全屏宽" in 数据) and ("默认全屏高" in 数据)
        )
        结果["最近会话未正常退出"] = (
            str(数据.get("最近会话状态", "clean") or "clean").strip().lower()
            == "running"
        )
        环境渲染后端 = str(os.environ.get("E5CM_RENDER_BACKEND", "") or "").strip()
        if 环境渲染后端:
            结果["默认渲染后端"] = _规范渲染后端偏好(
                环境渲染后端,
                默认值=str(结果.get("默认渲染后端", _默认渲染引擎偏好()) or _默认渲染引擎偏好()),
            )
        if str(os.environ.get("E5CM_GPU_PIPELINE", "") or "").strip():
            结果["默认GPU谱面管线"] = _读取布尔环境变量(
                "E5CM_GPU_PIPELINE",
                bool(结果.get("默认GPU谱面管线", True)),
            )
        return 结果

    # _切换英文输入法()

    启动调试设置 = _读取启动调试设置()
    原生桌面尺寸 = tuple(取桌面尺寸((1600, 900)))
    应用目标桌面尺寸 = tuple(_取应用目标桌面尺寸((1600, 900)))
    高分屏统一1080p策略启用 = bool(_桌面需要全局1080p渲染策略(原生桌面尺寸))
    环境强制软件启动 = (
        _规范渲染后端偏好(
            os.environ.get("E5CM_RENDER_BACKEND", ""),
            默认值="",
        )
        == "software"
    )
    if bool(高分屏统一1080p策略启用) and (not bool(环境强制软件启动)):
        当前默认后端 = _规范渲染后端偏好(
            启动调试设置.get("默认渲染后端", _默认渲染引擎偏好()),
            默认值=_默认渲染引擎偏好(),
        )
        if str(当前默认后端) in ("software", "gpu-auto"):
            启动调试设置["默认渲染后端"] = _默认渲染引擎偏好()
        启动调试设置["默认GPU谱面管线"] = True
        启动调试设置["打包版选歌强制CPU兼容"] = False
        启动调试设置["默认显示模式"] = "borderless"
        启动调试设置["默认窗口宽"] = int(应用目标桌面尺寸[0])
        启动调试设置["默认窗口高"] = int(应用目标桌面尺寸[1])
        启动调试设置["默认全屏宽"] = int(应用目标桌面尺寸[0])
        启动调试设置["默认全屏高"] = int(应用目标桌面尺寸[1])
    高DPI启动保底信息 = _应用Windows高DPI启动保底策略(启动调试设置, 日志器)
    # 背景视频输出尺寸不再在高 DPI 下强制钳到 1920x1080，
    # 否则在 2K/4K 画布上会出现左上角贴图+右侧黑边。
    启动背景视频最大输出尺寸 = None
    启动恢复模式已启用 = bool(启动调试设置.get("最近会话未正常退出", False))
    _标记会话状态("running")
    当前版本号 = 读取当前版本号(_取运行根目录())
    os.environ.setdefault(
        "E5CM_GPU_PIPELINE",
        "1" if bool(启动调试设置.get("默认GPU谱面管线", True)) else "0",
    )

    if (
        (not bool(高分屏统一1080p策略启用))
        and str(启动调试设置.get("默认显示模式", "windowed") or "windowed").strip().lower() == "borderless"
    ):
        _启用1080p全屏兼容(原因="启动进入无边框全屏")
    pygame.init()
    窗口标题 = "e舞成名重构版"
    默认窗口尺寸 = (1600, 900)
    最小窗口尺寸 = (960, 540)

    def _规范窗口尺寸设置(宽值: object, 高值: object) -> tuple[int, int]:
        桌面w, 桌面h = tuple(应用目标桌面尺寸)
        桌面w = _读取正整数设置(桌面w, 默认窗口尺寸[0])
        桌面h = _读取正整数设置(桌面h, 默认窗口尺寸[1])
        宽 = _读取正整数设置(宽值, 默认窗口尺寸[0])
        高 = _读取正整数设置(高值, 默认窗口尺寸[1])
        最小w = min(int(最小窗口尺寸[0]), int(桌面w))
        最小h = min(int(最小窗口尺寸[1]), int(桌面h))
        宽 = max(int(最小w), min(int(宽), int(桌面w)))
        高 = max(int(最小h), min(int(高), int(桌面h)))
        return int(宽), int(高)

    def _规范显示模式设置(值: object) -> str:
        文本 = str(值 or "").strip().lower()
        if 文本 in ("borderless", "borderless_window", "fullscreen", "全屏", "无边框", "无边框窗口"):
            return "borderless"
        return "windowed"

    def _规范初始全屏尺寸设置(宽值: object, 高值: object) -> tuple[int, int]:
        桌面w, 桌面h = _规范窗口尺寸设置(*取桌面尺寸(默认窗口尺寸))
        宽 = _读取正整数设置(宽值, 桌面w)
        高 = _读取正整数设置(高值, 桌面h)
        最小w = int(min(最小窗口尺寸[0], 桌面w))
        最小h = int(min(最小窗口尺寸[1], 桌面h))
        宽 = max(int(最小w), min(int(宽), int(桌面w)))
        高 = max(int(最小h), min(int(高), int(桌面h)))
        return int(宽), int(高)

    def _取渲染模式文本(后端对象) -> str:
        return "GPU" if bool(getattr(后端对象, "是否GPU", False)) else "CPU"

    def _取渲染后端偏好值(后端对象) -> str:
        return "gpu" if bool(getattr(后端对象, "是否GPU", False)) else "software"

    def _渲染引擎偏好是否GPU(偏好: object) -> bool:
        return str(_规范渲染后端偏好(偏好, _默认渲染引擎偏好())).startswith("gpu-")

    def _场景是否强制CPU渲染(场景名: object) -> bool:
        场景文本 = str(场景名 or "").strip()
        if not 场景文本:
            return False
        try:
            配置列表 = 状态.get(
                "强制CPU场景名单",
                启动调试设置.get("强制CPU场景名单", []),
            )
        except Exception:
            配置列表 = []
        if not isinstance(配置列表, (list, tuple, set)):
            return False
        for 项 in 配置列表:
            try:
                if str(项 or "").strip() == 场景文本:
                    return True
            except Exception:
                continue
        return False

    def _场景允许手动切换渲染后端(场景名: object) -> bool:
        return not bool(_场景是否强制CPU渲染(场景名))

    def _打包版选歌CPU兼容策略启用() -> bool:
        try:
            if isinstance(状态, dict):
                return bool(
                    状态.get(
                        "打包版选歌强制CPU兼容",
                        启动调试设置.get("打包版选歌强制CPU兼容", True),
                    )
                )
        except Exception:
            pass
        return bool(启动调试设置.get("打包版选歌强制CPU兼容", True))

    def _取场景策略渲染后端(场景名: object, 默认偏好: object) -> str:
        场景文本 = str(场景名 or "").strip()
        if bool(getattr(sys, "frozen", False)) and 场景文本 == "选歌":
            if bool(_打包版选歌CPU兼容策略启用()):
                if not bool(getattr(_取场景策略渲染后端, "_打包选歌CPU策略已记录", False)):
                    _记录信息日志(日志器, "打包版选歌场景启用CPU兼容策略")
                    setattr(_取场景策略渲染后端, "_打包选歌CPU策略已记录", True)
                return "software"
        if bool(_场景是否强制CPU渲染(场景名)):
            return "software"
        return _规范渲染后端偏好(默认偏好, _默认渲染引擎偏好())

    def _取渲染引擎偏好标签(偏好: object) -> str:
        规范值 = _规范渲染后端偏好(偏好, _默认渲染引擎偏好())
        映射 = {
            "gpu-auto": "GPU-Auto",
            "gpu-d3d11": "GPU-D3D11",
            "gpu-opengl": "GPU-OpenGL",
            "software": "CPU-Software",
        }
        return str(映射.get(规范值, "GPU-Auto"))

    def _取渲染引擎说明文本(偏好: object) -> str:
        规范值 = _规范渲染后端偏好(偏好, _默认渲染引擎偏好())
        映射 = {
            "gpu-auto": "优点：自动选当前机器最合适的 GPU 引擎，最省心。\n缺点：不同机器命中的实际引擎不固定，排查问题时可预期性较弱。",
            "gpu-d3d11": "优点：Windows 10/11 下一般最稳，延迟和清晰度表现最好，NVIDIA / Xbox Game Bar 识别更友好。\n缺点：极老驱动或老显卡上可能创建失败。",
            "gpu-opengl": "优点：兼容性广，老机器和跨平台环境通常更容易跑起来。\n缺点：Windows 下叠加层识别和帧延迟表现通常不如 D3D11。",
            "software": "优点：兼容性最高，GPU 环境出问题时最容易保底跑起来。\n缺点：最吃 CPU，放大输出更容易糊，外部 FPS / 延迟叠加常常拿不到数据。",
        }
        return str(映射.get(规范值, ""))

    def _取渲染引擎菜单选项() -> list[dict]:
        return [
            {
                "id": "gpu-d3d11",
                "label": "GPU-D3D11 | Win11 推荐，低延迟",
            },
            {
                "id": "gpu-opengl",
                "label": "GPU-OpenGL | 兼容旧机，通用",
            },
            {
                "id": "gpu-auto",
                "label": "GPU-Auto | 自动择优，省心",
            },
            {
                "id": "software",
                "label": "CPU-Software | 最稳，但最吃 CPU",
            },
        ]

    def _取实际渲染引擎标签(后端对象) -> str:
        if 后端对象 is None:
            return _取渲染引擎偏好标签(状态.get("默认渲染后端", _默认渲染引擎偏好()))
        获取标签 = getattr(后端对象, "取渲染驱动标签", None)
        if callable(获取标签):
            try:
                标签 = str(获取标签() or "").strip()
                if 标签:
                    return 标签
            except Exception:
                pass
        return _取渲染引擎偏好标签(
            "software" if not bool(getattr(后端对象, "是否GPU", False)) else 状态.get("默认渲染后端", _默认渲染引擎偏好())
        )

    def _刷新窗口标题(后端对象):
        try:
            后端对象.设置标题(f"{窗口标题} ---{_取实际渲染引擎标签(后端对象)}")
        except Exception:
            pass

    def _取当前实际渲染后端偏好() -> str:
        if 显示后端 is None:
            return str(状态.get("默认渲染后端", _默认渲染引擎偏好()) or _默认渲染引擎偏好())
        return _取渲染后端偏好值(显示后端)

    初始场景名 = "投币"
    初始显示模式 = _规范显示模式设置(启动调试设置.get("默认显示模式", "windowed"))
    初始窗口w, 初始窗口h = _规范窗口尺寸设置(
        启动调试设置.get("默认窗口宽", 默认窗口尺寸[0]),
        启动调试设置.get("默认窗口高", 默认窗口尺寸[1]),
    )
    默认桌面w, 默认桌面h = _规范窗口尺寸设置(*取桌面尺寸(默认窗口尺寸))
    if bool(启动调试设置.get("默认全屏尺寸是否已保存", False)):
        初始全屏源w = 启动调试设置.get("默认全屏宽", 默认桌面w)
        初始全屏源h = 启动调试设置.get("默认全屏高", 默认桌面h)
    else:
        初始全屏源w = 默认桌面w
        初始全屏源h = 默认桌面h
    初始全屏w, 初始全屏h = _规范初始全屏尺寸设置(
        初始全屏源w,
        初始全屏源h,
    )
    共享背景视频桌面尺寸上限 = (1920, 1080)
    初始w, 初始h = (
        (int(初始全屏w), int(初始全屏h))
        if str(初始显示模式) == "borderless"
        else (int(初始窗口w), int(初始窗口h))
    )
    初始flags = pygame.NOFRAME if str(初始显示模式) == "borderless" else pygame.RESIZABLE
    初始后端偏好 = _取场景策略渲染后端(
        初始场景名,
        启动调试设置.get("默认渲染后端", _默认渲染引擎偏好()),
    )
    显示后端 = 创建显示后端(
        (初始w, 初始h),
        int(初始flags),
        窗口标题,
        偏好=str(初始后端偏好),
    )
    _刷新窗口标题(显示后端)
    屏幕 = 显示后端.取绘制屏幕()
    try:
        当前显示器刷新率 = int(
            getattr(显示后端, "取桌面刷新率", lambda: 取桌面刷新率(60))() or 60
        )
    except Exception:
        当前显示器刷新率 = int(取桌面刷新率(60) or 60)

    # time.sleep(0.15)
    # _切换英文输入法()
    pygame.event.clear()

    try:
        if 显示后端 is not None:
            getattr(显示后端, "激活窗口", lambda: False)()
    except Exception:
        pass

    时钟 = pygame.time.Clock()
    资源 = 默认资源路径()
    共享背景回退图路径 = os.path.join(
        资源.get("根", os.getcwd()),
        "冷资源",
        "backimages",
        "背景图",
        "02.jpg",
    )
    共享背景视频超分辨率禁用 = bool(
        int(默认桌面w) > int(共享背景视频桌面尺寸上限[0])
        or int(默认桌面h) > int(共享背景视频桌面尺寸上限[1])
    )

    音乐 = 音乐管理()
    字体 = {
        "大字": 获取字体(72),
        "中字": 获取字体(36),
        "小字": 获取字体(22),
        "HUD字": 获取字体(18),
        "投币_credit字": 获取字体(28, 是否粗体=False),
        "投币_请投币字": 获取字体(48, 是否粗体=False),
    }

    状态 = {
        "玩家数": 1,
        "大模式": "",
        "子模式": "",
        "credit": "0",
        "投币数": 0,
        "每局所需信用": 3,
        "对局_当前把数": 1,
        "对局_S次数": 0,
        "对局_赠送第四把": False,
        "投币快捷键": int(pygame.K_f),
        "投币快捷键显示": "F",
        "显示器刷新率": int(max(30, min(240, int(当前显示器刷新率 or 60)))),
        "默认渲染后端": str(启动调试设置.get("默认渲染后端", _默认渲染引擎偏好()) or _默认渲染引擎偏好()),
        "默认GPU谱面管线": bool(启动调试设置.get("默认GPU谱面管线", True)),
        "打包版选歌强制CPU兼容": bool(启动调试设置.get("打包版选歌强制CPU兼容", True)),
        "默认显示模式": str(初始显示模式),
        "显示性能调试信息": bool(启动调试设置.get("显示性能调试信息", False)),
        "显示状态HUD": bool(启动调试设置.get("显示状态HUD", True)),
        "显示启动幻灯片": bool(启动调试设置.get("显示启动幻灯片", False)),
        "显示谱面开场动画": bool(启动调试设置.get("显示谱面开场动画", True)),
        "全局静音": bool(启动调试设置.get("全局静音", False)),
        "开发默认选歌载荷启用": bool(
            启动调试设置.get("开发默认选歌载荷启用", True)
        ),
        "开发默认选歌类型": str(
            启动调试设置.get("开发默认选歌类型", "竞速") or "竞速"
        ),
        "开发默认选歌模式": str(
            启动调试设置.get("开发默认选歌模式", "混音") or "混音"
        ),
        "默认窗口宽": int(初始窗口w),
        "默认窗口高": int(初始窗口h),
        "默认全屏宽": int(初始全屏w),
        "默认全屏高": int(初始全屏h),
        "软件版本": str(当前版本号),
        "日志文件路径": str(_取日志文件路径() or ""),
    }

    def _同步渲染后端状态(后端对象, 当前载荷=None):
        实际后端 = _取渲染后端偏好值(后端对象)
        实际启用GPU谱面管线 = bool(getattr(后端对象, "是否GPU", False))
        实际引擎标签 = _取实际渲染引擎标签(后端对象)
        获取驱动名 = getattr(后端对象, "取渲染驱动名", None)
        try:
            实际驱动名 = str(获取驱动名() if callable(获取驱动名) else "" or "")
        except Exception:
            实际驱动名 = ""
        状态["当前渲染后端"] = str("gpu" if bool(实际启用GPU谱面管线) else "software")
        状态["当前GPU谱面管线"] = bool(实际启用GPU谱面管线)
        状态["当前渲染引擎标签"] = str(实际引擎标签)
        状态["当前渲染驱动"] = str(实际驱动名)
        os.environ["E5CM_RENDER_BACKEND"] = str(实际后端)
        管线偏好开启 = bool(状态.get("默认GPU谱面管线", True))
        os.environ["E5CM_GPU_PIPELINE"] = (
            "1" if (bool(实际启用GPU谱面管线) and bool(管线偏好开启)) else "0"
        )
        if isinstance(当前载荷, dict):
            当前载荷["启用GPU谱面管线"] = bool(
                bool(实际启用GPU谱面管线) and bool(管线偏好开启)
            )
        _刷新窗口标题(后端对象)
        return 实际后端

    _同步渲染后端状态(显示后端)

    点击特效目录 = os.path.join(资源["根"], "UI-img", "点击特效")
    特效资源 = 序列帧特效资源(目录=点击特效目录, 扩展名=".png")
    特效ok = 特效资源.加载()
    全局点击特效 = 全局点击特效管理器(
        帧列表=特效资源.帧列表 if 特效ok else [],
        每秒帧数=60,
        缩放比例=1.0,
    )

    是否全屏 = bool(str(初始显示模式) == "borderless")
    上次窗口尺寸 = (int(初始窗口w), int(初始窗口h))
    上次全屏尺寸 = (int(初始全屏w), int(初始全屏h))

    def _取当前显示分辨率() -> tuple[int, int]:
        try:
            if 显示后端 is not None:
                当前尺寸 = tuple(显示后端.取窗口尺寸())
            else:
                当前尺寸 = tuple(屏幕.get_size())
        except Exception:
            try:
                当前尺寸 = tuple(上次全屏尺寸 if bool(是否全屏) else 上次窗口尺寸)
            except Exception:
                当前尺寸 = 默认窗口尺寸
        return _规范窗口尺寸设置(
            当前尺寸[0] if len(当前尺寸) > 0 else 默认窗口尺寸[0],
            当前尺寸[1] if len(当前尺寸) > 1 else 默认窗口尺寸[1],
        )

    def _记录窗口化显示分辨率(宽值: object, 高值: object) -> tuple[int, int]:
        nonlocal 上次窗口尺寸
        窗口w, 窗口h = _规范窗口尺寸设置(宽值, 高值)
        上次窗口尺寸 = (int(窗口w), int(窗口h))
        try:
            状态["默认窗口宽"] = int(窗口w)
            状态["默认窗口高"] = int(窗口h)
        except Exception:
            pass
        return int(窗口w), int(窗口h)

    def _记录全屏显示分辨率(宽值: object, 高值: object) -> tuple[int, int]:
        nonlocal 上次全屏尺寸
        全屏w, 全屏h = _规范全屏尺寸设置(宽值, 高值)
        上次全屏尺寸 = (int(全屏w), int(全屏h))
        try:
            状态["默认全屏宽"] = int(全屏w)
            状态["默认全屏高"] = int(全屏h)
        except Exception:
            pass
        return int(全屏w), int(全屏h)

    def _取当前窗口化尺寸() -> tuple[int, int]:
        try:
            if not bool(是否全屏):
                return _取当前显示分辨率()
            当前尺寸 = tuple(上次窗口尺寸)
        except Exception:
            当前尺寸 = 默认窗口尺寸
        return _规范窗口尺寸设置(
            当前尺寸[0] if len(当前尺寸) > 0 else 默认窗口尺寸[0],
            当前尺寸[1] if len(当前尺寸) > 1 else 默认窗口尺寸[1],
        )

    def _取可用窗口尺寸列表() -> list[tuple[int, int]]:
        桌面w, 桌面h = 取桌面尺寸(默认窗口尺寸)
        桌面w, 桌面h = _规范窗口尺寸设置(桌面w, 桌面h)
        候选列表 = [
            (960, 540),
            (1024, 576),
            (1280, 720),
            (1366, 768),
            (1600, 900),
            (1920, 1080),
            (2560, 1440),
        ]
        结果: list[tuple[int, int]] = []
        已存在: set[tuple[int, int]] = set()

        def _加入候选(宽值: object, 高值: object):
            尺寸 = _规范窗口尺寸设置(宽值, 高值)
            if tuple(尺寸) in 已存在:
                return
            已存在.add(tuple(尺寸))
            结果.append(tuple(尺寸))

        for 候选w, 候选h in 候选列表:
            if int(候选w) > int(桌面w) or int(候选h) > int(桌面h):
                continue
            _加入候选(候选w, 候选h)

        _加入候选(*默认窗口尺寸)
        _加入候选(*_取当前窗口化尺寸())
        _加入候选(桌面w, 桌面h)
        结果.sort(key=lambda 项: (int(项[0]) * int(项[1]), int(项[0]), int(项[1])))
        return list(结果)

    def _取可用全屏尺寸列表() -> list[tuple[int, int]]:
        桌面w, 桌面h = _规范窗口尺寸设置(*取桌面尺寸(默认窗口尺寸))
        最小w = int(min(最小窗口尺寸[0], 桌面w))
        最小h = int(min(最小窗口尺寸[1], 桌面h))
        结果: list[tuple[int, int]] = []
        已存在: set[tuple[int, int]] = set()
        额外候选列表 = [
            (960, 540),
            (1024, 576),
            (1280, 720),
            (1366, 768),
            (1600, 900),
            (1920, 1080),
            (2560, 1440),
        ]

        def _加入候选(宽值: object, 高值: object):
            try:
                宽 = int(宽值)
                高 = int(高值)
            except Exception:
                return
            if 宽 < 最小w or 高 < 最小h:
                return
            if 宽 > int(桌面w) or 高 > int(桌面h):
                return
            尺寸 = (int(宽), int(高))
            if 尺寸 in 已存在:
                return
            已存在.add(尺寸)
            结果.append(尺寸)

        for 候选w, 候选h in 额外候选列表:
            _加入候选(候选w, 候选h)

        _加入候选(*默认窗口尺寸)
        _加入候选(*_取当前窗口化尺寸())
        _加入候选(
            上次全屏尺寸[0] if len(上次全屏尺寸) > 0 else 默认窗口尺寸[0],
            上次全屏尺寸[1] if len(上次全屏尺寸) > 1 else 默认窗口尺寸[1],
        )
        _加入候选(桌面w, 桌面h)
        结果.sort(key=lambda 项: (int(项[0]) * int(项[1]), int(项[0]), int(项[1])))
        return list(结果)

    def _取窗口尺寸候选索引(
        尺寸: tuple[int, int],
        候选列表: list[tuple[int, int]],
        规范化函数=None,
    ) -> int:
        if not 候选列表:
            return 0
        if callable(规范化函数):
            目标w, 目标h = 规范化函数(
                尺寸[0] if len(尺寸) > 0 else 默认窗口尺寸[0],
                尺寸[1] if len(尺寸) > 1 else 默认窗口尺寸[1],
            )
        else:
            目标w, 目标h = _规范窗口尺寸设置(
                尺寸[0] if len(尺寸) > 0 else 默认窗口尺寸[0],
                尺寸[1] if len(尺寸) > 1 else 默认窗口尺寸[1],
            )
        try:
            return 候选列表.index((int(目标w), int(目标h)))
        except Exception:
            pass
        return int(
            min(
                range(len(候选列表)),
                key=lambda 索引: (
                    abs(int(候选列表[索引][0]) - int(目标w))
                    + abs(int(候选列表[索引][1]) - int(目标h)),
                    abs(
                        int(候选列表[索引][0]) * int(候选列表[索引][1])
                        - int(目标w) * int(目标h)
                    ),
                ),
            )
        )

    def _规范全屏尺寸设置(宽值: object, 高值: object) -> tuple[int, int]:
        桌面w, 桌面h = _规范窗口尺寸设置(*取桌面尺寸(默认窗口尺寸))
        宽 = _读取正整数设置(宽值, 默认窗口尺寸[0])
        高 = _读取正整数设置(高值, 默认窗口尺寸[1])
        最小w = int(min(最小窗口尺寸[0], 桌面w))
        最小h = int(min(最小窗口尺寸[1], 桌面h))
        宽 = max(int(最小w), min(int(宽), int(桌面w)))
        高 = max(int(最小h), min(int(高), int(桌面h)))
        候选列表 = _取可用全屏尺寸列表()
        if not 候选列表:
            return int(宽), int(高)
        try:
            return 候选列表[_取窗口尺寸候选索引((宽, 高), 候选列表, lambda 值w, 值h: (int(值w), int(值h)))]
        except Exception:
            return int(宽), int(高)

    def _取当前全屏尺寸() -> tuple[int, int]:
        try:
            if bool(是否全屏):
                当前尺寸 = tuple(_取当前显示分辨率())
            else:
                当前尺寸 = tuple(上次全屏尺寸)
        except Exception:
            当前尺寸 = 默认窗口尺寸
        return _规范全屏尺寸设置(
            当前尺寸[0] if len(当前尺寸) > 0 else 默认窗口尺寸[0],
            当前尺寸[1] if len(当前尺寸) > 1 else 默认窗口尺寸[1],
        )

    def _应用窗口化分辨率(
        宽值: object,
        高值: object,
        *,
        发送事件: bool = True,
        保存设置: bool = True,
    ) -> tuple[int, int]:
        nonlocal 是否全屏
        if bool(是否全屏) and (not bool(高分屏统一1080p策略启用)):
            try:
                _恢复1080p全屏兼容(原因="切回窗口模式")
            except Exception:
                pass
        目标w, 目标h = _规范窗口尺寸设置(宽值, 高值)
        当前窗口模式尺寸 = _取当前窗口化尺寸()
        if (
            (not bool(是否全屏))
            and tuple(int(v) for v in 当前窗口模式尺寸) == (int(目标w), int(目标h))
        ):
            _记录窗口化显示分辨率(int(目标w), int(目标h))
            try:
                状态["默认显示模式"] = "windowed"
            except Exception:
                pass
            if bool(保存设置):
                try:
                    if callable(_保存全局设置):
                        _保存全局设置()
                except Exception:
                    pass
            return int(目标w), int(目标h)
        if 显示后端 is not None:
            显示后端.调整窗口模式((目标w, 目标h), pygame.RESIZABLE)
        是否全屏 = False
        _记录窗口化显示分辨率(int(目标w), int(目标h))
        _同步屏幕引用()
        try:
            状态["默认显示模式"] = "windowed"
        except Exception:
            pass
        if bool(保存设置):
            try:
                if callable(_保存全局设置):
                    _保存全局设置()
            except Exception:
                pass
        if bool(发送事件):
            _发送窗口尺寸变化事件(int(目标w), int(目标h))
        return int(目标w), int(目标h)

    def _应用全屏分辨率(
        宽值: object,
        高值: object,
        *,
        发送事件: bool = True,
        保存设置: bool = True,
    ) -> tuple[int, int]:
        nonlocal 是否全屏
        if not bool(高分屏统一1080p策略启用):
            try:
                _启用1080p全屏兼容(原因="切换无边框全屏")
            except Exception:
                pass
        目标w, 目标h = _规范全屏尺寸设置(宽值, 高值)
        当前全屏尺寸 = _取当前全屏尺寸()
        if (
            bool(是否全屏)
            and tuple(int(v) for v in 当前全屏尺寸) == (int(目标w), int(目标h))
        ):
            _记录全屏显示分辨率(int(目标w), int(目标h))
            try:
                状态["默认显示模式"] = "borderless"
            except Exception:
                pass
            if bool(保存设置):
                try:
                    if callable(_保存全局设置):
                        _保存全局设置()
                except Exception:
                    pass
            return int(目标w), int(目标h)
        if 显示后端 is not None:
            显示后端.调整窗口模式((目标w, 目标h), pygame.NOFRAME)
        是否全屏 = True
        _记录全屏显示分辨率(int(目标w), int(目标h))
        _同步屏幕引用()
        try:
            状态["默认显示模式"] = "borderless"
        except Exception:
            pass
        if bool(保存设置):
            try:
                if callable(_保存全局设置):
                    _保存全局设置()
            except Exception:
                pass
        if bool(发送事件):
            _发送窗口尺寸变化事件(int(目标w), int(目标h))
        return int(目标w), int(目标h)

    def _应用显示分辨率(
        宽值: object,
        高值: object,
        *,
        发送事件: bool = True,
        保存设置: bool = True,
    ) -> tuple[int, int]:
        if bool(是否全屏):
            return _应用全屏分辨率(
                宽值,
                高值,
                发送事件=bool(发送事件),
                保存设置=bool(保存设置),
            )
        return _应用窗口化分辨率(
            宽值,
            高值,
            发送事件=bool(发送事件),
            保存设置=bool(保存设置),
        )

    def _切换全屏到(目标值: Optional[bool] = None) -> bool:
        当前 = bool(是否全屏)
        目标 = (not 当前) if 目标值 is None else bool(目标值)
        if 当前 == 目标:
            return bool(是否全屏)
        _切换全屏()
        try:
            if callable(_保存全局设置):
                _保存全局设置()
        except Exception:
            pass
        try:
            当前w, 当前h = tuple(上下文["屏幕"].get_size())
        except Exception:
            if bool(是否全屏):
                当前w, 当前h = _取当前全屏尺寸()
            else:
                当前w, 当前h = _取当前窗口化尺寸()
        _发送窗口尺寸变化事件(int(当前w), int(当前h))
        return bool(是否全屏)

    def _循环窗口分辨率(step: int = 1) -> tuple[int, int]:
        if bool(是否全屏):
            候选列表 = _取可用全屏尺寸列表()
            if not 候选列表:
                return _取当前全屏尺寸()
            当前尺寸 = _取当前全屏尺寸()
            当前索引 = _取窗口尺寸候选索引(
                当前尺寸,
                候选列表,
                _规范全屏尺寸设置,
            )
            新尺寸 = 候选列表[(int(当前索引) + int(step)) % len(候选列表)]
            return _应用全屏分辨率(新尺寸[0], 新尺寸[1], 发送事件=True)

        候选列表 = _取可用窗口尺寸列表()
        if not 候选列表:
            return _取当前窗口化尺寸()
        当前尺寸 = _取当前窗口化尺寸()
        当前索引 = _取窗口尺寸候选索引(当前尺寸, 候选列表)
        新尺寸 = 候选列表[(int(当前索引) + int(step)) % len(候选列表)]
        return _应用窗口化分辨率(新尺寸[0], 新尺寸[1], 发送事件=True)

    def _取显示设置快照() -> dict:
        当前窗口w, 当前窗口h = _取当前窗口化尺寸()
        当前全屏w, 当前全屏h = _取当前全屏尺寸()
        当前有效尺寸 = (
            (int(当前全屏w), int(当前全屏h))
            if bool(是否全屏)
            else (int(当前窗口w), int(当前窗口h))
        )
        候选列表 = _取可用全屏尺寸列表() if bool(是否全屏) else _取可用窗口尺寸列表()
        当前渲染偏好 = _规范渲染后端偏好(
            状态.get("默认渲染后端", _默认渲染引擎偏好()),
            _默认渲染引擎偏好(),
        )
        渲染引擎选项 = []
        for 选项 in _取渲染引擎菜单选项():
            选项标识 = str(选项.get("id", "") or "")
            if not 选项标识:
                continue
            渲染引擎选项.append(
                {
                    "id": str(选项标识),
                    "label": str(选项.get("label", 选项标识) or 选项标识),
                    "selected": bool(str(选项标识) == str(当前渲染偏好)),
                }
            )
        return {
            "display_mode": str(_取当前显示模式标识()),
            "display_mode_text": str(_取当前显示模式文本()),
            "fullscreen": bool(是否全屏),
            "window_size": (int(当前窗口w), int(当前窗口h)),
            "fullscreen_size": (int(当前全屏w), int(当前全屏h)),
            "active_size": tuple(int(v) for v in 当前有效尺寸),
            "resolution_options": [tuple(int(v) for v in 项) for 项 in 候选列表],
            "desktop_size": tuple(int(v) for v in 应用目标桌面尺寸),
            "render_backend": str(当前渲染偏好),
            "render_backend_text": str(_取渲染引擎偏好标签(当前渲染偏好)),
            "render_backend_actual_text": str(_取实际渲染引擎标签(显示后端)),
            "render_backend_description": str(_取渲染引擎说明文本(当前渲染偏好)),
            "render_backend_options": list(渲染引擎选项),
        }

    上下文 = {
        "屏幕": 屏幕,
        "时钟": 时钟,
        "资源": 资源,
        "字体": 字体,
        "音乐": 音乐,
        "状态": 状态,
        "全局点击特效": 全局点击特效,
        "背景视频": None,
        "显示后端": 显示后端,
        "渲染后端名称": str(_取实际渲染引擎标签(显示后端)),
        "主循环最近统计": {},
        "显示后端最近统计": {},
        "显示性能调试信息": bool(启动调试设置.get("显示性能调试信息", False)),
        "显示状态HUD": bool(启动调试设置.get("显示状态HUD", True)),
        "显示器刷新率": int(max(30, min(240, int(当前显示器刷新率 or 60)))),
        "共享背景回退图路径": str(共享背景回退图路径 or ""),
        "共享背景视频超分辨率禁用": bool(共享背景视频超分辨率禁用),
        "开发调试菜单开启": False,
        "取显示设置": _取显示设置快照,
        "切换全屏": _切换全屏到,
        "循环显示分辨率": _循环窗口分辨率,
        "循环窗口分辨率": _循环窗口分辨率,
        "应用显示分辨率": _应用显示分辨率,
        "应用全屏分辨率": _应用全屏分辨率,
        "应用窗口分辨率": _应用窗口化分辨率,
    }

    backmovies目录 = 资源.get(
        "backmovies目录", os.path.join(资源.get("根", os.getcwd()), "backmovies")
    )
    开场动画目录 = os.path.join(backmovies目录, "开场动画")
    if bool(启动调试设置.get("显示启动幻灯片", True)):
        _播放开场幻灯片(开场动画目录)

    视频路径 = ""
    if bool(共享背景视频超分辨率禁用):
        _记录信息日志(
            日志器,
            "桌面尺寸超过 1920x1080，启动共享背景视频已禁用 "
            f"桌面={默认桌面w}x{默认桌面h} "
            f"回退图={共享背景回退图路径}",
        )
    else:
        强制视频 = os.path.join(backmovies目录, "003.mp4")
        if os.path.isfile(强制视频):
            视频路径 = 强制视频
        else:
            视频路径 = 选择第一个视频(backmovies目录)

    背景视频 = None
    if str(视频路径 or "").strip():
        背景视频 = 全局视频循环播放器(
            视频路径,
            最大输出尺寸=启动背景视频最大输出尺寸,
        )
    上下文["背景视频"] = 背景视频

    场景表 = {
        "投币": 场景_投币,
        "登陆磁卡": 场景_登陆磁卡,
        "个人资料": 场景_个人资料,
        "大模式": 场景_大模式,
        "子模式": 场景_子模式,
        "选歌": 场景_选歌,
        "加载页": 场景_加载页,
        "结算": 场景_结算,
        "谱面播放器": 场景_谱面播放器,
    }


    当前场景名 = str(初始场景名)
    当前场景 = 场景表[当前场景名](上下文)
    _安全进入场景(当前场景, None)

    过渡 = 公共黑屏过渡(渐入秒=0.2,渐出秒=0)
    入场 = 公共丝滑入场(保持黑屏秒=0.03, 渐出秒=0.3)
    
    待切换目标场景名 = None
    待切换载荷 = None

    调试提示文本 = ""
    调试提示截止 = 0.0
    右上状态条上次矩形 = pygame.Rect(0, 0, 0, 0)
    非游戏菜单开启 = False
    非游戏菜单索引 = 0
    投币快捷键录入中 = False
    非游戏菜单项矩形: list[pygame.Rect] = []
    非游戏菜单背景音乐关闭 = False
    非游戏菜单背景音乐路径 = ""
    选歌ESC菜单宿主 = SelectSceneEscMenuHost(上下文)
    投币音效对象 = None
    def _解析安全短音效路径(原路径: object) -> str:
        路径 = str(原路径 or "").strip()
        if (not 路径) or (not os.path.isfile(路径)):
            return ""
        后缀 = str(os.path.splitext(路径)[1] or "").strip().lower()
        if 后缀 != ".mp3":
            return 路径
        根路径, _ = os.path.splitext(路径)
        for 候选后缀 in (".wav", ".ogg"):
            候选路径 = f"{根路径}{候选后缀}"
            if os.path.isfile(候选路径):
                return 候选路径
        # 兼容性保护：避免在部分机器上触发 mp3 短音效硬崩。
        return ""
    try:
        投币音效路径 = _解析安全短音效路径(资源.get("投币音效", ""))
        if 投币音效路径 and pygame.mixer.get_init():
            投币音效对象 = pygame.mixer.Sound(str(投币音效路径))
    except Exception:
        投币音效对象 = None

    投币快捷键 = int(pygame.K_f)
    投币快捷键显示 = "F"
    def _格式化按键名(键值: int) -> str:
        try:
            名 = str(pygame.key.name(int(键值)) or "").strip()
        except Exception:
            名 = ""
        if not 名:
            return f"KEY_{int(键值)}"
        return 名.upper()

    def _保存全局设置():
        try:
            当前投币数 = max(0, int(状态.get("投币数", 0) or 0))
        except Exception:
            当前投币数 = 0
        当前窗口w, 当前窗口h = _取当前窗口化尺寸()
        当前全屏w, 当前全屏h = _取当前全屏尺寸()

        旧数据 = _读取存储作用域(_全局设置存储作用域)
        if not isinstance(旧数据, dict):
            旧数据 = {}

        新数据 = dict(旧数据)
        新数据.update(
            {
                "投币快捷键": int(投币快捷键),
                "投币快捷键显示": str(投币快捷键显示),
                "投币数": int(当前投币数),
                "默认渲染后端": str(状态.get("默认渲染后端", _默认渲染引擎偏好()) or _默认渲染引擎偏好()),
                "默认GPU谱面管线": bool(
                    状态.get("默认GPU谱面管线", True)
                ),
                "打包版选歌强制CPU兼容": bool(
                    状态.get("打包版选歌强制CPU兼容", True)
                ),
                "默认显示模式": str(_取当前显示模式标识()),
                "显示性能调试信息": bool(
                    状态.get("显示性能调试信息", False)
                ),
                "显示状态HUD": bool(
                    状态.get("显示状态HUD", True)
                ),
                "显示启动幻灯片": bool(
                    状态.get("显示启动幻灯片", True)
                ),
                "显示谱面开场动画": bool(
                    状态.get("显示谱面开场动画", True)
                ),
                "全局静音": bool(
                    状态.get("全局静音", False)
                ),
                "开发默认选歌载荷启用": bool(
                    状态.get("开发默认选歌载荷启用", True)
                ),
                "开发默认选歌类型": str(
                    状态.get("开发默认选歌类型", "竞速") or "竞速"
                ),
                "开发默认选歌模式": str(
                    状态.get("开发默认选歌模式", "混音") or "混音"
                ),
                "默认窗口宽": int(当前窗口w),
                "默认窗口高": int(当前窗口h),
                "默认全屏宽": int(当前全屏w),
                "默认全屏高": int(当前全屏h),
            }
        )

        新数据.pop("残余币值", None)
        新数据.pop("credit", None)

        try:
            _替换存储作用域(_全局设置存储作用域, 新数据)
        except Exception:
            pass


    def _加载全局设置():
        nonlocal 投币快捷键, 投币快捷键显示

        数据 = _读取存储作用域(_全局设置存储作用域)
        if not isinstance(数据, dict):
            数据 = {}

        try:
            键值 = int(数据.get("投币快捷键", pygame.K_f))
            投币快捷键 = int(max(0, min(4096, 键值)))
        except Exception:
            投币快捷键 = int(pygame.K_f)

        投币快捷键显示 = _格式化按键名(int(投币快捷键))
        状态["投币快捷键"] = int(投币快捷键)
        状态["投币快捷键显示"] = str(投币快捷键显示)

        try:
            当前投币数 = max(0, int(数据.get("投币数", 0) or 0))
        except Exception:
            当前投币数 = 0

        状态["投币数"] = int(当前投币数)
        状态["credit"] = str(int(当前投币数))
        状态["默认渲染后端"] = _规范渲染后端偏好(
            数据.get("默认渲染后端", 状态.get("默认渲染后端", _默认渲染引擎偏好())),
            默认值=str(状态.get("默认渲染后端", _默认渲染引擎偏好()) or _默认渲染引擎偏好()),
        )
        状态["默认GPU谱面管线"] = bool(
            数据.get("默认GPU谱面管线", 状态.get("默认GPU谱面管线", True))
        )
        状态["打包版选歌强制CPU兼容"] = bool(
            数据.get(
                "打包版选歌强制CPU兼容",
                状态.get("打包版选歌强制CPU兼容", True),
            )
        )
        状态["默认显示模式"] = _规范显示模式设置(
            数据.get("默认显示模式", 状态.get("默认显示模式", "windowed"))
        )
        if bool(高分屏统一1080p策略启用) and (not bool(环境强制软件启动)):
            状态["默认渲染后端"] = _默认渲染引擎偏好()
            状态["默认GPU谱面管线"] = True
            状态["打包版选歌强制CPU兼容"] = False
            状态["默认显示模式"] = "borderless"
            状态["默认窗口宽"] = int(应用目标桌面尺寸[0])
            状态["默认窗口高"] = int(应用目标桌面尺寸[1])
            状态["默认全屏宽"] = int(应用目标桌面尺寸[0])
            状态["默认全屏高"] = int(应用目标桌面尺寸[1])
        状态["显示性能调试信息"] = bool(
            数据.get("显示性能调试信息", 状态.get("显示性能调试信息", False))
        )
        状态["显示状态HUD"] = bool(
            数据.get("显示状态HUD", 状态.get("显示状态HUD", True))
        )
        状态["显示启动幻灯片"] = bool(
            数据.get("显示启动幻灯片", 状态.get("显示启动幻灯片", True))
        )
        状态["显示谱面开场动画"] = bool(
            数据.get("显示谱面开场动画", 状态.get("显示谱面开场动画", True))
        )
        状态["全局静音"] = bool(
            数据.get("全局静音", 状态.get("全局静音", False))
        )
        状态["开发默认选歌载荷启用"] = bool(
            数据.get(
                "开发默认选歌载荷启用",
                状态.get("开发默认选歌载荷启用", True),
            )
        )
        状态["开发默认选歌类型"] = str(
            数据.get(
                "开发默认选歌类型",
                状态.get("开发默认选歌类型", "竞速"),
            )
            or "竞速"
        ).strip() or "竞速"
        状态["开发默认选歌模式"] = str(
            数据.get(
                "开发默认选歌模式",
                状态.get("开发默认选歌模式", "混音"),
            )
            or "混音"
        ).strip() or "混音"
        状态["日志文件路径"] = str(_取日志文件路径() or "")
        上下文["显示性能调试信息"] = bool(
            状态.get("显示性能调试信息", False)
        )
        上下文["显示状态HUD"] = bool(
            状态.get("显示状态HUD", True)
        )
        os.environ["E5CM_GPU_PIPELINE"] = (
            "1" if bool(状态.get("默认GPU谱面管线", True)) else "0"
        )

    def _应用全局静音状态():
        静音 = bool(状态.get("全局静音", False))
        try:
            if pygame.mixer.get_init():
                音量 = 0.0 if 静音 else 1.0
                try:
                    pygame.mixer.music.set_volume(float(音量))
                except Exception:
                    pass
                try:
                    for i in range(int(pygame.mixer.get_num_channels())):
                        pygame.mixer.Channel(int(i)).set_volume(float(音量))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if 投币音效对象 is not None:
                投币音效对象.set_volume(0.0 if 静音 else 1.0)
        except Exception:
            pass
        

    def _显示调试提示(文本: str, 秒: float = 1.2):
        nonlocal 调试提示文本, 调试提示截止
        调试提示文本 = 文本
        调试提示截止 = time.time() + float(秒)

    上下文["显示调试提示"] = _显示调试提示

    def _追加GPU上传脏矩形(矩形: pygame.Rect):
        if not isinstance(矩形, pygame.Rect) or 矩形.w <= 0 or 矩形.h <= 0:
            return
        try:
            if bool(上下文.get("GPU强制全量上传", False)):
                return
        except Exception:
            return
        try:
            现有列表 = 上下文.get("GPU上传脏矩形列表", None)
            if not isinstance(现有列表, list):
                return
            现有列表.append(矩形.copy())
            上下文["GPU上传脏矩形列表"] = 现有列表
        except Exception:
            pass

    def _构建右上状态条图层(
        参考宽: int,
        参考高: int,
    ) -> tuple[pygame.Surface | None, pygame.Rect]:
        if not bool(状态.get("显示状态HUD", True)):
            return None, pygame.Rect(0, 0, 0, 0)
        try:
            小字 = 上下文["字体"].get("HUD字") or 上下文["字体"].get("小字")
        except Exception:
            小字 = None
        if not isinstance(小字, pygame.font.Font):
            try:
                小字 = 获取字体(18)
            except Exception:
                return None, pygame.Rect(0, 0, 0, 0)

        fps值 = 0.0
        try:
            fps值 = float(时钟.get_fps() or 0.0)
        except Exception:
            fps值 = 0.0
        if fps值 <= 0.1:
            try:
                主循环统计 = dict(上下文.get("主循环最近统计", {}) or {})
                帧毫秒 = float(主循环统计.get("frame_ms", 0.0) or 0.0)
                if 帧毫秒 > 0.001:
                    fps值 = 1000.0 / float(帧毫秒)
            except Exception:
                fps值 = 0.0

        if fps值 > 0.1:
            fps文本 = f"{fps值:.1f}"
        else:
            fps文本 = "--"
        渲染文本 = str(_取实际渲染引擎标签(显示后端) or "CPU-Software")
        try:
            分辨率w, 分辨率h = _取当前显示分辨率()
            分辨率文本 = f"{int(分辨率w)}*{int(分辨率h)}"
        except Exception:
            分辨率文本 = ""
        状态文本 = f"{fps文本} FPS | {渲染文本}"
        if 分辨率文本:
            状态文本 = f"{状态文本} | {分辨率文本}"

        文图 = 小字.render(状态文本, True, (188, 194, 201))
        内边距x = 12
        内边距y = 6
        面板矩形 = pygame.Rect(
            0,
            0,
            int(文图.get_width() + 内边距x * 2),
            int(文图.get_height() + 内边距y * 2),
        )
        面板矩形.bottomright = (
            int(max(1, int(参考宽)) - 14),
            int(max(1, int(参考高)) - 12),
        )
        面板 = pygame.Surface((int(面板矩形.w), int(面板矩形.h)), pygame.SRCALPHA)
        pygame.draw.rect(
            面板,
            (6, 8, 12, 126),
            pygame.Rect(0, 0, 面板矩形.w, 面板矩形.h),
            border_radius=10,
        )
        pygame.draw.rect(
            面板,
            (255, 255, 255, 36),
            pygame.Rect(0, 0, 面板矩形.w, 面板矩形.h),
            width=1,
            border_radius=10,
        )
        面板.blit(
            文图,
            (
                int(内边距x),
                int(内边距y),
            ),
        )
        return 面板, 面板矩形.copy()

    def _绘制右上状态条() -> pygame.Rect:
        nonlocal 右上状态条上次矩形
        try:
            屏幕对象 = 上下文.get("屏幕", None)
        except Exception:
            屏幕对象 = None
        if not isinstance(屏幕对象, pygame.Surface):
            return pygame.Rect(0, 0, 0, 0)
        面板, 面板矩形 = _构建右上状态条图层(
            int(屏幕对象.get_width()),
            int(屏幕对象.get_height()),
        )
        if not isinstance(面板, pygame.Surface):
            右上状态条上次矩形 = pygame.Rect(0, 0, 0, 0)
            return pygame.Rect(0, 0, 0, 0)
        屏幕对象.blit(面板, 面板矩形.topleft)
        脏矩形 = 面板矩形.copy()
        if isinstance(右上状态条上次矩形, pygame.Rect) and 右上状态条上次矩形.w > 0 and 右上状态条上次矩形.h > 0:
            脏矩形 = 脏矩形.union(右上状态条上次矩形)
        右上状态条上次矩形 = 面板矩形.copy()
        return 脏矩形

    def _绘制右上状态条_到显示后端(显示后端对象) -> pygame.Rect:
        if not bool(getattr(显示后端对象, "是否GPU", False)):
            return pygame.Rect(0, 0, 0, 0)
        try:
            from pygame._sdl2 import video as _sdl2_video
        except Exception:
            return pygame.Rect(0, 0, 0, 0)
        if _sdl2_video is None:
            return pygame.Rect(0, 0, 0, 0)
        取渲染器 = getattr(显示后端对象, "取GPU渲染器", None)
        if not callable(取渲染器):
            return pygame.Rect(0, 0, 0, 0)
        渲染器 = 取渲染器()
        if 渲染器 is None:
            return pygame.Rect(0, 0, 0, 0)
        try:
            渲染宽, 渲染高 = tuple(int(v) for v in 显示后端对象.取窗口尺寸())
        except Exception:
            try:
                渲染宽, 渲染高 = tuple(int(v) for v in 上下文["屏幕"].get_size())
            except Exception:
                return pygame.Rect(0, 0, 0, 0)
        面板, 渲染矩形 = _构建右上状态条图层(int(渲染宽), int(渲染高))
        if not isinstance(面板, pygame.Surface):
            return pygame.Rect(0, 0, 0, 0)
        目标矩形 = 渲染矩形.copy()
        try:
            使用逻辑坐标映射 = bool(
                getattr(显示后端对象, "使用逻辑坐标映射", lambda: False)()
            )
        except Exception:
            使用逻辑坐标映射 = False
        if not bool(使用逻辑坐标映射):
            try:
                输出宽, 输出高 = tuple(int(v) for v in 显示后端对象.取输出尺寸())
            except Exception:
                输出宽, 输出高 = int(渲染宽), int(渲染高)
            比例x = float(max(1, int(输出宽))) / float(max(1, int(渲染宽)))
            比例y = float(max(1, int(输出高))) / float(max(1, int(渲染高)))
            目标矩形 = pygame.Rect(
                int(round(float(渲染矩形.x) * 比例x)),
                int(round(float(渲染矩形.y) * 比例y)),
                max(1, int(round(float(渲染矩形.w) * 比例x))),
                max(1, int(round(float(渲染矩形.h) * 比例y))),
            )
        try:
            纹理 = _sdl2_video.Texture.from_surface(渲染器, 面板)
            try:
                纹理.blend_mode = 1
            except Exception:
                pass
            纹理.draw(
                dstrect=(
                    int(目标矩形.x),
                    int(目标矩形.y),
                    int(目标矩形.w),
                    int(目标矩形.h),
                )
            )
            return 目标矩形
        except Exception:
            return pygame.Rect(0, 0, 0, 0)

    def _同步投币显示():
        try:
            投币数 = int(状态.get("投币数", 0) or 0)
        except Exception:
            投币数 = 0

        投币数 = max(0, 投币数)
        状态["投币数"] = int(投币数)
        状态["credit"] = str(int(投币数))
        try:
            if callable(_保存全局设置):
                _保存全局设置()
        except Exception:
            pass
        
    _加载全局设置()
    _同步渲染后端状态(显示后端)
    _应用全局静音状态()
    _同步投币显示()
    if bool(启动恢复模式已启用):
        _显示调试提示("检测到上次异常退出，已用窗口/CPU兼容模式启动", 3.6)
    elif bool(高分屏统一1080p策略启用):
        _显示调试提示("检测到高分屏，已统一切到全局1080p渲染（GPU优先）", 3.2)
    elif bool(启动时已启用1080p全屏兼容):
        _显示调试提示("检测到 2K 桌面，已自动切到 1080p 全屏兼容模式", 3.2)

    状态["非游戏菜单背景音乐关闭"] = bool(非游戏菜单背景音乐关闭)
    开发调试菜单开启 = False
    开发调试菜单索引 = 0
    开发调试菜单项矩形: list[pygame.Rect] = []
    开发调试目标场景列表 = [
        "选歌",
        "投币",
        "登陆磁卡",
        "个人资料",
        "加载页",
        "谱面播放器",
    ]
    开发调试目标场景索引 = int(
        max(0, min(len(开发调试目标场景列表) - 1, 开发调试目标场景列表.index("选歌")))
    )

    def _取当前场景载荷() -> dict:
        try:
            值 = getattr(当前场景, "_载荷", None)
            if isinstance(值, dict):
                return dict(值)
        except Exception:
            pass
        return {}

    def _取当前开发目标场景() -> str:
        try:
            return str(开发调试目标场景列表[int(开发调试目标场景索引)] or "投币")
        except Exception:
            return "投币"

    def _解析开发载荷预设() -> dict:
        try:
            值 = 状态.get("加载页_载荷", {})
            if isinstance(值, dict):
                return dict(值)
        except Exception:
            pass
        return {}

    def _取开发默认选歌载荷() -> dict:
        if not bool(状态.get("开发默认选歌载荷启用", True)):
            return {}
        类型 = str(状态.get("开发默认选歌类型", "竞速") or "竞速").strip() or "竞速"
        模式 = str(状态.get("开发默认选歌模式", "混音") or "混音").strip() or "混音"
        return {
            "选歌类型": str(类型),
            "选歌模式": str(模式),
            "类型": str(类型),
            "模式": str(模式),
            "大模式": str(类型),
            "子模式": str(模式),
            "songs子文件夹": str(类型),
        }

    def _合并开发默认选歌载荷(载荷: Optional[dict]) -> dict:
        结果 = dict(载荷 or {}) if isinstance(载荷, dict) else {}
        for 键, 值 in _取开发默认选歌载荷().items():
            结果.setdefault(str(键), 值)
        return 结果

    def _构建开发跳转载荷(目标场景名: str):
        目标场景名 = str(目标场景名 or "").strip()
        预设载荷 = _解析开发载荷预设()
        if 目标场景名 in ("加载页", "谱面播放器"):
            载荷 = dict(预设载荷 or {})
            载荷["显示准备动画"] = bool(状态.get("显示谱面开场动画", True))
            载荷["启用GPU谱面管线"] = bool(状态.get("默认GPU谱面管线", True))
            return 载荷
        if 目标场景名 == "选歌":
            选歌载荷 = _合并开发默认选歌载荷(预设载荷)
            return {"加载页_载荷": dict(选歌载荷)} if bool(选歌载荷) else None
        return None

    def _当前显示后端满足目标偏好(目标后端: object) -> bool:
        规范目标 = _规范渲染后端偏好(目标后端, _默认渲染引擎偏好())
        当前是GPU = bool(getattr(显示后端, "是否GPU", False)) if 显示后端 is not None else False
        if str(规范目标) == "software":
            return not bool(当前是GPU)
        if not bool(当前是GPU):
            return False
        if str(规范目标) == "gpu-auto":
            return True
        try:
            取驱动名 = getattr(显示后端, "取渲染驱动名", None)
            当前驱动名 = (
                str(取驱动名() or "").strip().lower()
                if callable(取驱动名)
                else ""
            )
        except Exception:
            当前驱动名 = ""
        当前标签 = str(_取实际渲染引擎标签(显示后端) or "").strip()

        if str(规范目标) == "gpu-opengl":
            if 当前驱动名 in ("opengl", "opengles2"):
                return True
            return 当前标签 in ("GPU-OpenGL", "GPU-OpenGLES2")

        if str(规范目标) == "gpu-d3d11":
            if 当前驱动名 in ("direct3d11", "direct3d", "direct3d12"):
                return True
            return 当前标签 in ("GPU-D3D11", "GPU-D3D", "GPU-D3D12")

        return str(当前标签) == str(_取渲染引擎偏好标签(规范目标))

    def _切换显示后端(
        目标后端: str,
        *,
        当前载荷: Optional[dict] = None,
        持久化为默认: bool = True,
    ):
        nonlocal 显示后端
        目标后端 = _规范渲染后端偏好(目标后端, 默认值=_默认渲染引擎偏好())
        if bool(持久化为默认):
            状态["默认渲染后端"] = str(目标后端)
        目标flags = pygame.NOFRAME if bool(是否全屏) else pygame.RESIZABLE
        try:
            目标尺寸 = tuple(int(v) for v in 上下文["屏幕"].get_size())
        except Exception:
            目标尺寸 = (1280, 720)
        try:
            if 显示后端 is not None:
                显示后端.关闭()
        except Exception:
            pass
        try:
            显示后端 = 创建显示后端(
                目标尺寸,
                int(目标flags),
                窗口标题,
                偏好=str(目标后端),
            )
        except Exception as 异常:
            _记录异常日志(
                日志器,
                f"创建显示后端失败，目标后端={目标后端}",
                异常,
            )
            显示后端 = 创建显示后端(
                目标尺寸,
                int(目标flags),
                窗口标题,
                偏好="software",
            )
            状态["默认GPU谱面管线"] = False
            if bool(持久化为默认):
                状态["默认渲染后端"] = "software"
            _显示调试提示("渲染后端创建失败，已降级为CPU兼容模式", 2.2)
        _同步渲染后端状态(
            显示后端,
            当前载荷 if isinstance(当前载荷, dict) else None,
        )
        _同步屏幕引用()
        上下文["显示后端"] = 显示后端
        上下文["渲染后端名称"] = str(_取实际渲染引擎标签(显示后端))
        上下文["显示性能调试信息"] = bool(状态.get("显示性能调试信息", False))
        上下文["显示状态HUD"] = bool(状态.get("显示状态HUD", True))

    def _按场景策略同步显示后端(目标场景名: object, 当前载荷: Optional[dict] = None):
        目标后端 = _取场景策略渲染后端(
            目标场景名,
            状态.get("默认渲染后端", _默认渲染引擎偏好()),
        )
        try:
            if bool(_当前显示后端满足目标偏好(目标后端)):
                return
            _切换显示后端(
                str(目标后端),
                当前载荷=当前载荷 if isinstance(当前载荷, dict) else None,
                持久化为默认=False,
            )
        except Exception as 异常:
            _记录异常日志(
                日志器,
                f"按场景策略切换显示后端失败，场景={目标场景名} 目标后端={目标后端}",
                异常,
            )
            _切换显示后端(
                "software",
                当前载荷=当前载荷 if isinstance(当前载荷, dict) else None,
                持久化为默认=False,
            )

    def _重建当前场景并切换后端(
        目标后端: str,
        *,
        持久化为默认: bool = True,
        显示提示: bool = True,
    ):
        nonlocal 当前场景
        目标后端 = _规范渲染后端偏好(目标后端, 默认值=_默认渲染引擎偏好())
        当前载荷 = _取当前场景载荷()

        try:
            当前场景.退出()
        except Exception:
            pass

        _切换显示后端(
            str(目标后端),
            当前载荷=当前载荷,
            持久化为默认=bool(持久化为默认),
        )
        try:
            当前场景 = 场景表[当前场景名](上下文)
            _安全进入场景(当前场景, 当前载荷 if bool(当前载荷) else None)
        except Exception as 异常:
            _记录异常日志(
                日志器,
                f"重建场景失败，场景={当前场景名}，已回退投币",
                异常,
            )
            当前场景 = 场景表["投币"](上下文)
            _安全进入场景(当前场景, None)
        if bool(持久化为默认):
            _保存全局设置()
        if bool(显示提示):
            _显示调试提示(
                (
                    f"渲染引擎已切换为：{_取实际渲染引擎标签(显示后端)}"
                    if bool(持久化为默认)
                    else f"本次会话已切换为：{_取实际渲染引擎标签(显示后端)}"
                ),
                1.2,
            )

    def _应用渲染引擎偏好(目标偏好: object):
        if not bool(_场景允许手动切换渲染后端(当前场景名)):
            _显示调试提示("当前场景已锁定CPU渲染（可在强制CPU场景名单中调整）", 1.8)
            return
        规范目标 = _规范渲染后端偏好(目标偏好, _默认渲染引擎偏好())
        if bool(getattr(sys, "frozen", False)) and bool(
            _渲染引擎偏好是否GPU(规范目标)
        ):
            if bool(状态.get("打包版选歌强制CPU兼容", True)):
                状态["打包版选歌强制CPU兼容"] = False
                try:
                    启动调试设置["打包版选歌强制CPU兼容"] = False
                except Exception:
                    pass
                _显示调试提示("已关闭打包版选歌CPU锁定：后续场景保持GPU渲染", 1.6)
        当前偏好 = _规范渲染后端偏好(
            状态.get("默认渲染后端", _默认渲染引擎偏好()),
            _默认渲染引擎偏好(),
        )
        当前实际可用 = bool(getattr(显示后端, "是否GPU", False)) if 显示后端 is not None else False
        当前实际标签 = _取实际渲染引擎标签(显示后端)
        目标偏好标签 = _取渲染引擎偏好标签(规范目标)
        实际满足目标 = False
        if str(规范目标) == "software":
            实际满足目标 = (not bool(当前实际可用))
        elif str(规范目标) == "gpu-auto":
            实际满足目标 = bool(当前实际可用)
        else:
            实际满足目标 = bool(当前实际可用) and str(当前实际标签) == str(目标偏好标签)
        if (
            str(规范目标) == str(当前偏好)
            and bool(实际满足目标)
        ):
            _显示调试提示(f"渲染引擎：{_取渲染引擎偏好标签(规范目标)}", 1.0)
            return
        _重建当前场景并切换后端(str(规范目标), 持久化为默认=True)

    def _切换性能调试信息显示():
        状态["显示性能调试信息"] = not bool(状态.get("显示性能调试信息", False))
        上下文["显示性能调试信息"] = bool(状态["显示性能调试信息"])
        _保存全局设置()
        _显示调试提示(
            f"性能调试信息已{'显示' if bool(状态['显示性能调试信息']) else '隐藏'}",
            1.0,
        )

    def _切换状态HUD显示():
        状态["显示状态HUD"] = not bool(状态.get("显示状态HUD", True))
        上下文["显示状态HUD"] = bool(状态["显示状态HUD"])
        _保存全局设置()
        _显示调试提示(
            f"状态HUD已{'显示' if bool(状态['显示状态HUD']) else '隐藏'}",
            1.0,
        )

    上下文["切换状态HUD"] = _切换状态HUD显示
    上下文["应用渲染引擎偏好"] = _应用渲染引擎偏好

    def _切换全局静音():
        状态["全局静音"] = not bool(状态.get("全局静音", False))
        _应用全局静音状态()
        _保存全局设置()
        _显示调试提示(
            f"全局静音已{'开启' if bool(状态['全局静音']) else '关闭'}",
            1.0,
        )

    def _切换开发默认选歌载荷():
        当前启用 = bool(状态.get("开发默认选歌载荷启用", True))
        状态["开发默认选歌载荷启用"] = not 当前启用
        if bool(状态["开发默认选歌载荷启用"]):
            状态["开发默认选歌类型"] = str(
                状态.get("开发默认选歌类型", "竞速") or "竞速"
            ).strip() or "竞速"
            状态["开发默认选歌模式"] = str(
                状态.get("开发默认选歌模式", "混音") or "混音"
            ).strip() or "混音"
        _保存全局设置()
        if bool(状态["开发默认选歌载荷启用"]):
            _显示调试提示(
                f"选歌默认载荷：{状态['开发默认选歌类型']} / {状态['开发默认选歌模式']}",
                1.0,
            )
        else:
            _显示调试提示("选歌默认载荷已关闭", 1.0)

    def _执行开发场景跳转():
        nonlocal 当前场景名, 当前场景, 开发调试菜单开启
        目标场景名 = _取当前开发目标场景()
        载荷 = _构建开发跳转载荷(目标场景名)
        try:
            当前场景.退出()
        except Exception:
            pass
        当前场景名 = str(目标场景名)
        _按场景策略同步显示后端(当前场景名, 载荷 if isinstance(载荷, dict) else None)
        # 优化思路：
        # 1. 场景实例化应该只做轻量级的变量初始化
        当前场景 = 场景表[当前场景名](上下文)
        
        # 2. 将重量级加载放入一个独立的方法，并让场景自己决定是否异步
        # if hasattr(当前场景, '开始异步加载'):
        #     当前场景.开始异步加载(载荷)
        
        _安全进入场景(当前场景, 载荷)
        开发调试菜单开启 = False
        _显示调试提示(f"已切换到场景：{当前场景名}", 1.0)

    def _取开发调试菜单项() -> list[str]:
        渲染文本 = _取渲染模式文本(显示后端)
        默认选歌文本 = (
            f"{str(状态.get('开发默认选歌类型', '竞速') or '竞速')} / "
            f"{str(状态.get('开发默认选歌模式', '混音') or '混音')}"
            if bool(状态.get("开发默认选歌载荷启用", True))
            else "关闭"
        )
        return [
            f"渲染模式：{渲染文本}",
            f"性能调试信息：{'显示' if bool(状态.get('显示性能调试信息', False)) else '隐藏'}",
            f"全局静音：{'开启' if bool(状态.get('全局静音', False)) else '关闭'}",
            f"选歌默认载荷：{默认选歌文本}",
            f"跳转场景：{_取当前开发目标场景()}",
            "立即切换场景",
        ]

    def _执行开发调试菜单选项(索引: int, 方向: int = 0):
        nonlocal 开发调试目标场景索引
        索引 = int(max(0, min(len(_取开发调试菜单项()) - 1, int(索引))))
        if 索引 == 0:
            当前模式 = _取当前实际渲染后端偏好()
            目标模式 = "software" if _渲染引擎偏好是否GPU(当前模式) else _默认渲染引擎偏好()
            _应用渲染引擎偏好(目标模式)
            return
        if 索引 == 1:
            _切换性能调试信息显示()
            return
        if 索引 == 2:
            _切换全局静音()
            return
        if 索引 == 3:
            _切换开发默认选歌载荷()
            return
        if 索引 == 4:
            步进 = int(方向) if int(方向) != 0 else 1
            开发调试目标场景索引 = (
                int(开发调试目标场景索引) + 步进
            ) % len(开发调试目标场景列表)
            return
        if 索引 == 5:
            _执行开发场景跳转()
            return

    def _全局投币一次():
        try:
            状态["投币数"] = int(状态.get("投币数", 0) or 0) + 1
        except Exception:
            状态["投币数"] = 1
        _同步投币显示()
        try:
            if 投币音效对象 is not None:
                投币音效对象.play()
        except Exception:
            pass
        try:
            当前币 = int(状态.get("投币数", 0) or 0)
        except Exception:
            当前币 = 0
        所需信用 = 取每局所需信用(状态)
        _显示调试提示(
            f"{str(状态.get('投币快捷键显示', 投币快捷键显示))}投币 +1  当前:{max(0, 当前币)}/{int(所需信用)}",
            0.8,
        )

    def _取非游戏菜单项() -> list[str]:
        菜单项 = [
            f"设置投币快捷键（当前：{str(状态.get('投币快捷键显示', 投币快捷键显示))}）",
            "开启背景音乐" if bool(非游戏菜单背景音乐关闭) else "关闭背景音乐",
        ]
        菜单项.append("退出到桌面")
        return 菜单项

    def _切换非游戏背景音乐():
        nonlocal 非游戏菜单背景音乐关闭, 非游戏菜单背景音乐路径, 当前场景名
        if not bool(非游戏菜单背景音乐关闭):
            try:
                当前路径 = str(getattr(音乐, "当前路径", "") or "")
            except Exception:
                当前路径 = ""
            if 当前路径 and os.path.isfile(当前路径):
                非游戏菜单背景音乐路径 = 当前路径
            try:
                音乐.停止()
            except Exception:
                pass
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
            except Exception:
                pass
            非游戏菜单背景音乐关闭 = True
            状态["非游戏菜单背景音乐关闭"] = True
            _显示调试提示("背景音乐已关闭", 1.0)
            return

        恢复路径 = str(非游戏菜单背景音乐路径 or "").strip()
        if (not 恢复路径) or (not os.path.isfile(恢复路径)):
            恢复路径 = str(资源.get("音乐_UI", "") or "").strip()
        if 恢复路径 and os.path.isfile(恢复路径) and (str(当前场景名 or "") != "选歌"):
            try:
                音乐.播放循环(恢复路径)
            except Exception:
                pass
        非游戏菜单背景音乐关闭 = False
        状态["非游戏菜单背景音乐关闭"] = False
        _显示调试提示("背景音乐已开启", 1.0)

    def _执行非游戏菜单选项(索引: int):
        nonlocal 投币快捷键录入中
        菜单项 = _取非游戏菜单项()
        if not 菜单项:
            return
        索引 = int(max(0, min(len(菜单项) - 1, int(索引))))
        选项 = 菜单项[索引]
        if "设置投币快捷键" in 选项:
            投币快捷键录入中 = True
            _显示调试提示("请按任意键设置为投币快捷键（ESC取消）", 2.0)
            return
        if "背景音乐" in 选项:
            _切换非游戏背景音乐()
            return
        if 选项 == "退出到桌面":
            _退出程序()
            return

    def _绘制非游戏菜单():
        nonlocal 非游戏菜单项矩形
        非游戏菜单项矩形 = []
        if not 非游戏菜单开启:
            return
        try:
            屏幕面 = 上下文["屏幕"]
            w, h = 屏幕面.get_size()
            遮罩 = pygame.Surface((w, h), pygame.SRCALPHA)
            遮罩.fill((0, 0, 0, 178))
            屏幕面.blit(遮罩, (0, 0))

            菜单项 = _取非游戏菜单项()
            面板w = max(660, min(int(w * 0.46), 860))
            面板h = max(320, min(int(h * 0.66), 200 + len(菜单项) * 72))
            面板 = pygame.Rect((w - 面板w) // 2, (h - 面板h) // 2, 面板w, 面板h)

            标题字 = 上下文["字体"]["中字"]
            小字 = 上下文["字体"]["小字"]
            标题面 = 标题字.render("系统菜单", True, (245, 248, 255))
            屏幕面.blit(标题面, (面板.x + 24, 面板.y + 2))
            副标题面 = 小字.render("ESC / SYSTEM", True, (140, 172, 225))
            try:
                副标题面.set_alpha(170)
            except Exception:
                pass
            屏幕面.blit(副标题面, (面板.x + 26, 面板.y + 46))

            按钮高 = 58
            按钮间距 = 14
            选项起y = int(面板.y + 86)
            for idx, 名称 in enumerate(菜单项):
                选中 = idx == int(非游戏菜单索引)
                行rect = pygame.Rect(
                    int(面板.x + 22),
                    int(选项起y + idx * (按钮高 + 按钮间距)),
                    int(面板.w - 44),
                    int(按钮高),
                )
                底色 = (26, 34, 54) if 选中 else (18, 24, 40)
                边色 = (120, 238, 255) if 选中 else (76, 96, 136)
                pygame.draw.rect(屏幕面, 底色, 行rect, border_radius=14)
                pygame.draw.rect(
                    屏幕面,
                    边色,
                    行rect,
                    width=2 if 选中 else 1,
                    border_radius=14,
                )
                if 选中:
                    高亮 = pygame.Surface((行rect.w, 行rect.h), pygame.SRCALPHA)
                    pygame.draw.rect(
                        高亮,
                        (0, 239, 251, 34),
                        pygame.Rect(0, 0, 行rect.w, 行rect.h),
                        border_radius=14,
                    )
                    pygame.draw.rect(
                        高亮,
                        (255, 88, 170, 150),
                        pygame.Rect(0, 10, 5, 行rect.h - 20),
                        border_radius=3,
                    )
                    屏幕面.blit(高亮, 行rect.topleft)
                序号面 = 小字.render(f"{idx + 1:02d}", True, (116, 146, 196))
                屏幕面.blit(
                    序号面,
                    (
                        int(行rect.x + 16),
                        int(行rect.y + (行rect.h - 序号面.get_height()) // 2),
                    ),
                )
                项面 = 小字.render(
                    str(名称),
                    True,
                    (255, 245, 164) if 选中 else (226, 233, 246),
                )
                屏幕面.blit(
                    项面,
                    (
                        int(行rect.x + 62),
                        int(行rect.y + (行rect.h - 项面.get_height()) // 2),
                    ),
                )
                非游戏菜单项矩形.append(行rect)

            提示行 = [
                f"{str(状态.get('投币快捷键显示', 投币快捷键显示))}投币   ESC关闭",
                "鼠标点击 / 1或7上一项 / 3或9下一项 / 5确认",
            ]
            提示y = int(选项起y + len(菜单项) * (按钮高 + 按钮间距) + 12)
            for 文本 in 提示行:
                行面 = 小字.render(文本, True, (132, 148, 178))
                try:
                    行面.set_alpha(150)
                except Exception:
                    pass
                屏幕面.blit(行面, (面板.x + 24, 提示y))
                提示y += int(行面.get_height()) + 2

            if bool(投币快捷键录入中):
                提示 = "等待按键输入：按任意键设为投币键（ESC取消）"
                提示面 = 小字.render(提示, True, (255, 240, 140))
                屏幕面.blit(提示面, (面板.x + 24, int(面板.y + 58)))
        except Exception:
            pass

    def _绘制开发调试菜单():
        nonlocal 开发调试菜单项矩形
        开发调试菜单项矩形 = []
        if not 开发调试菜单开启:
            return
        try:
            屏幕面 = 上下文["屏幕"]
            w, h = 屏幕面.get_size()
            遮罩 = pygame.Surface((w, h), pygame.SRCALPHA)
            遮罩.fill((0, 8, 18, 190))
            屏幕面.blit(遮罩, (0, 0))

            菜单项 = _取开发调试菜单项()
            面板w = max(760, min(int(w * 0.58), 980))
            面板h = max(420, min(int(h * 0.76), 220 + len(菜单项) * 72))
            面板 = pygame.Rect((w - 面板w) // 2, (h - 面板h) // 2, 面板w, 面板h)

            标题字 = 上下文["字体"]["中字"]
            小字 = 上下文["字体"]["小字"]
            标题面 = 标题字.render("开发调试菜单", True, (245, 248, 255))
            屏幕面.blit(标题面, (面板.x + 24, 面板.y + 2))
            副标题面 = 小字.render("CTRL+F10 / DEV MENU", True, (120, 220, 255))
            try:
                副标题面.set_alpha(170)
            except Exception:
                pass
            屏幕面.blit(副标题面, (面板.x + 26, 面板.y + 46))

            按钮高 = 58
            按钮间距 = 14
            选项起y = int(面板.y + 86)
            for idx, 名称 in enumerate(菜单项):
                选中 = idx == int(开发调试菜单索引)
                行rect = pygame.Rect(
                    int(面板.x + 22),
                    int(选项起y + idx * (按钮高 + 按钮间距)),
                    int(面板.w - 44),
                    int(按钮高),
                )
                底色 = (22, 30, 48) if 选中 else (16, 22, 36)
                边色 = (120, 238, 255) if 选中 else (66, 90, 128)
                pygame.draw.rect(屏幕面, 底色, 行rect, border_radius=14)
                pygame.draw.rect(
                    屏幕面,
                    边色,
                    行rect,
                    width=2 if 选中 else 1,
                    border_radius=14,
                )
                if 选中:
                    高亮 = pygame.Surface((行rect.w, 行rect.h), pygame.SRCALPHA)
                    pygame.draw.rect(
                        高亮,
                        (0, 239, 251, 28),
                        pygame.Rect(0, 0, 行rect.w, 行rect.h),
                        border_radius=14,
                    )
                    pygame.draw.rect(
                        高亮,
                        (255, 88, 170, 150),
                        pygame.Rect(0, 10, 5, 行rect.h - 20),
                        border_radius=3,
                    )
                    屏幕面.blit(高亮, 行rect.topleft)
                序号面 = 小字.render(f"{idx + 1:02d}", True, (116, 146, 196))
                屏幕面.blit(
                    序号面,
                    (
                        int(行rect.x + 16),
                        int(行rect.y + (行rect.h - 序号面.get_height()) // 2),
                    ),
                )
                项面 = 小字.render(
                    str(名称),
                    True,
                    (255, 245, 164) if 选中 else (226, 233, 246),
                )
                屏幕面.blit(
                    项面,
                    (
                        int(行rect.x + 62),
                        int(行rect.y + (行rect.h - 项面.get_height()) // 2),
                    ),
                )
                开发调试菜单项矩形.append(行rect)

            提示行 = [
                "左右切换选项值 / 回车执行 / ESC或Ctrl+F10关闭",
                "选歌跳转会给空载荷补默认模式；加载页和谱面播放器沿用当前状态载荷",
            ]
            提示y = int(选项起y + len(菜单项) * (按钮高 + 按钮间距) + 12)
            for 文本 in 提示行:
                行面 = 小字.render(文本, True, (132, 148, 178))
                try:
                    行面.set_alpha(150)
                except Exception:
                    pass
                屏幕面.blit(行面, (面板.x + 24, 提示y))
                提示y += int(行面.get_height()) + 2
        except Exception:
            pass

    def _处理非游戏菜单按键(事件) -> bool:
        nonlocal 非游戏菜单开启, 非游戏菜单索引
        nonlocal 投币快捷键录入中, 投币快捷键, 投币快捷键显示

        if not 非游戏菜单开启:
            return False

        菜单项 = _取非游戏菜单项()

        if bool(投币快捷键录入中):
            if 事件.type == pygame.KEYDOWN:
                if 事件.key == pygame.K_ESCAPE:
                    投币快捷键录入中 = False
                    _显示调试提示("已取消修改投币快捷键", 1.0)
                    return True
                投币快捷键 = int(max(0, min(4096, int(事件.key))))
                投币快捷键显示 = _格式化按键名(int(投币快捷键))
                状态["投币快捷键"] = int(投币快捷键)
                状态["投币快捷键显示"] = str(投币快捷键显示)
                _保存全局设置()
                投币快捷键录入中 = False
                _显示调试提示(f"投币快捷键已改为：{投币快捷键显示}", 1.2)
                return True
            return True

        if 事件.type == pygame.KEYDOWN:
            if 事件.key == pygame.K_ESCAPE:
                非游戏菜单开启 = False
                return True
            if 事件.key in (
                pygame.K_LEFT,
                pygame.K_1,
                pygame.K_KP1,
                pygame.K_UP,
                pygame.K_7,
                pygame.K_KP7,
            ):
                非游戏菜单索引 = (int(非游戏菜单索引) - 1) % len(菜单项)
                return True
            if 事件.key in (
                pygame.K_RIGHT,
                pygame.K_3,
                pygame.K_KP3,
                pygame.K_DOWN,
                pygame.K_9,
                pygame.K_KP9,
            ):
                非游戏菜单索引 = (int(非游戏菜单索引) + 1) % len(菜单项)
                return True
            if 事件.key in (
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
                pygame.K_5,
                pygame.K_KP5,
            ):
                _执行非游戏菜单选项(int(非游戏菜单索引))
                return True
            return True

        if 事件.type == pygame.MOUSEMOTION:
            for idx, rect in enumerate(非游戏菜单项矩形):
                if rect.collidepoint(事件.pos):
                    非游戏菜单索引 = int(idx)
                    break
            return True

        if 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            for idx, rect in enumerate(非游戏菜单项矩形):
                if rect.collidepoint(事件.pos):
                    非游戏菜单索引 = int(idx)
                    _执行非游戏菜单选项(int(idx))
                    return True
            非游戏菜单开启 = False
            投币快捷键录入中 = False
            return True

        return True

    def _处理开发调试菜单按键(事件) -> bool:
        nonlocal 开发调试菜单开启, 开发调试菜单索引
        if not 开发调试菜单开启:
            return False

        菜单项 = _取开发调试菜单项()
        if 事件.type == pygame.KEYDOWN:
            mod = int(getattr(事件, "mod", 0) or 0)
            ctrl_f10 = bool(
                事件.key == pygame.K_F10 and (mod & pygame.KMOD_CTRL)
            )
            if 事件.key == pygame.K_ESCAPE or ctrl_f10:
                开发调试菜单开启 = False
                return True
            if 事件.key in (
                pygame.K_UP,
                pygame.K_7,
                pygame.K_KP7,
                pygame.K_LEFT,
                pygame.K_1,
                pygame.K_KP1,
            ):
                if 事件.key in (pygame.K_LEFT, pygame.K_1, pygame.K_KP1):
                    _执行开发调试菜单选项(int(开发调试菜单索引), -1)
                else:
                    开发调试菜单索引 = (int(开发调试菜单索引) - 1) % len(菜单项)
                return True
            if 事件.key in (
                pygame.K_DOWN,
                pygame.K_9,
                pygame.K_KP9,
                pygame.K_RIGHT,
                pygame.K_3,
                pygame.K_KP3,
            ):
                if 事件.key in (pygame.K_RIGHT, pygame.K_3, pygame.K_KP3):
                    _执行开发调试菜单选项(int(开发调试菜单索引), 1)
                else:
                    开发调试菜单索引 = (int(开发调试菜单索引) + 1) % len(菜单项)
                return True
            if 事件.key in (
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
                pygame.K_5,
                pygame.K_KP5,
            ):
                _执行开发调试菜单选项(int(开发调试菜单索引), 0)
                return True
            return True

        if 事件.type == pygame.MOUSEMOTION:
            for idx, rect in enumerate(开发调试菜单项矩形):
                if rect.collidepoint(事件.pos):
                    开发调试菜单索引 = int(idx)
                    break
            return True

        if 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            for idx, rect in enumerate(开发调试菜单项矩形):
                if rect.collidepoint(事件.pos):
                    开发调试菜单索引 = int(idx)
                    _执行开发调试菜单选项(int(idx), 0)
                    return True
            开发调试菜单开启 = False
            return True

        return True

    def _执行场景切换():
        nonlocal 当前场景名, 当前场景, 待切换目标场景名, 待切换载荷
        nonlocal 非游戏菜单开启, 非游戏菜单索引, 投币快捷键录入中

        原场景名 = str(当前场景名 or "")
        目标 = 待切换目标场景名
        载荷 = 待切换载荷
        if 目标 == "玩家选择":
            目标 = "投币"
        if not 目标 or (目标 not in 场景表):
            return

        try:
            当前场景.退出()
        except Exception:
            pass

        # 在加载重型场景前，强制刷新一次屏幕，防止上一帧残留在缓冲区
        if 显示后端:
            try:
                显示后端.呈现(lambda b: None, lambda b: None, lambda b: None)
            except Exception:
                pass

        try:
            _按场景策略同步显示后端(
                str(目标),
                载荷 if isinstance(载荷, dict) else None,
            )
            当前场景名 = 目标
            当前场景 = 场景表[当前场景名](上下文)
            _安全进入场景(当前场景, 载荷)
        except Exception as 异常:
            _记录异常日志(
                日志器,
                f"场景切换失败：{原场景名} -> {目标}",
                异常,
            )
            try:
                _切换显示后端(
                    "software",
                    当前载荷=载荷 if isinstance(载荷, dict) else None,
                    持久化为默认=False,
                )
                当前场景名 = 目标
                当前场景 = 场景表[当前场景名](上下文)
                _安全进入场景(当前场景, 载荷)
                _显示调试提示("场景切换异常，已降级CPU后重试", 2.0)
            except Exception as 二次异常:
                _记录异常日志(
                    日志器,
                    f"场景切换二次失败，已回退投币：{原场景名} -> {目标}",
                    二次异常,
                )
                当前场景名 = "投币"
                当前场景 = 场景表["投币"](上下文)
                _安全进入场景(当前场景, None)
                _显示调试提示("场景切换失败，已回退投币场景", 2.4)
        if str(当前场景名 or "") != "选歌" and bool(选歌ESC菜单宿主.is_open()):
            选歌ESC菜单宿主.close()

        if 原场景名 == "投币" and 当前场景名 == "登陆磁卡":
            入场.开始()

        待切换目标场景名 = None
        待切换载荷 = None
        非游戏菜单开启 = False
        非游戏菜单索引 = 0
        投币快捷键录入中 = False


    def _当前场景允许非游戏菜单() -> bool:
        return bool(当前场景名 not in ("谱面播放器", "结算"))

    def _获取当前目标帧率() -> int:
        try:
            值 = int(getattr(当前场景, "目标帧率", 60) or 60)
        except Exception:
            值 = 60
        return max(30, min(240, 值))

    def _当前场景使用高精度帧率节流() -> bool:
        try:
            return bool(getattr(当前场景, "高精度帧率节流", False))
        except Exception:
            return False

    def _处理场景返回结果(结果) -> bool:
        nonlocal 待切换目标场景名, 待切换载荷

        目标 = None
        载荷 = None
        禁用黑屏 = False

        if isinstance(结果, dict):
            if bool(结果.get("退出程序", False)):
                _退出程序()
            目标 = 结果.get("切换到")
            载荷 = 结果.get("载荷")
            禁用黑屏 = bool(结果.get("禁用黑屏过渡", False))
        else:
            try:
                目标 = getattr(结果, "目标场景名", None)
                载荷 = getattr(结果, "载荷", None)
            except Exception:
                目标 = None

        if 目标 == "玩家选择":
            目标 = "投币"

        if not 目标 or (目标 not in 场景表):
            return False

        待切换目标场景名 = 目标
        待切换载荷 = 载荷
        if 禁用黑屏:
            _执行场景切换()
        else:
            过渡.开始(目标)
        return True

    while True:
        循环开始秒 = time.perf_counter()
        if _当前场景使用高精度帧率节流() and hasattr(时钟, "tick_busy_loop"):
            时钟.tick_busy_loop(_获取当前目标帧率())
        else:
            时钟.tick(_获取当前目标帧率())

        for 原始事件 in pygame.event.get():
            事件列表 = (
                显示后端.处理事件(原始事件)
                if 显示后端 is not None
                else [原始事件]
            )
            for 事件 in 事件列表:
                if 事件.type == pygame.QUIT:
                    _退出程序()

                if 事件.type == pygame.KEYDOWN:
                    mod = int(getattr(事件, "mod", 0) or 0)
                    if 事件.key == pygame.K_F10 and (mod & pygame.KMOD_CTRL):
                        开发调试菜单开启 = not bool(开发调试菜单开启)
                        if bool(开发调试菜单开启):
                            非游戏菜单开启 = False
                            非游戏菜单索引 = 0
                            投币快捷键录入中 = False
                        continue

                if _处理开发调试菜单按键(事件):
                    continue

                if (
                    事件.type == pygame.KEYDOWN
                    and int(事件.key) == int(投币快捷键)
                    and (not bool(投币快捷键录入中))
                ):
                    try:
                        _全局投币一次()
                    except Exception as 异常:
                        try:
                            _显示调试提示(
                                f"投币处理异常：{type(异常).__name__}",
                                1.6,
                            )
                        except Exception:
                            pass
                    if (not 过渡.是否进行中()) and 当前场景名 == "投币":
                        try:
                            当前币 = int(状态.get("投币数", 0) or 0)
                        except Exception:
                            当前币 = 0
                        所需信用 = 取每局所需信用(状态)
                        if 当前币 >= int(所需信用):
                            _显示调试提示(
                                f"已满足开局条件：请选择 1P / 2P（{int(当前币)}/{int(所需信用)}）",
                                0.9,
                            )
                        else:
                            _显示调试提示(
                                f"还需 {max(0, int(所需信用) - 当前币)} 币（{int(所需信用)}币开局）",
                                0.9,
                            )
                    continue

                窗口变化事件类型 = {
                    pygame.VIDEORESIZE,
                    getattr(pygame, "WINDOWRESIZED", -1),
                    getattr(pygame, "WINDOWSIZECHANGED", -1),
                }
                if int(getattr(事件, "type", -1)) in 窗口变化事件类型 and (not 是否全屏):
                    新w = int(max(960, int(getattr(事件, "w", 0) or 0)))
                    新h = int(max(540, int(getattr(事件, "h", 0) or 0)))
                    if int(新w) <= 0 or int(新h) <= 0:
                        新w = int(max(960, int(getattr(事件, "x", 0) or 0)))
                        新h = int(max(540, int(getattr(事件, "y", 0) or 0)))
                    _应用窗口化分辨率(新w, 新h, 发送事件=False)

                # if 事件.type == pygame.KEYDOWN and 事件.key == pygame.K_F5:
                #     if not 过渡.是否进行中():
                #         _热更新当前场景()
                #     continue

                if 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
                    x, y = 事件.pos
                    全局点击特效.触发(x, y)

                if 过渡.是否进行中():
                    continue

                if str(当前场景名 or "") == "选歌":
                    if 事件.type == pygame.KEYDOWN and 事件.key == pygame.K_ESCAPE:
                        非游戏菜单开启 = False
                        投币快捷键录入中 = False
                        if bool(选歌ESC菜单宿主.is_open()):
                            选歌ESC菜单宿主.close()
                        else:
                            选歌ESC菜单宿主.open()
                        continue

                    if bool(选歌ESC菜单宿主.is_open()):
                        结果 = 选歌ESC菜单宿主.handle_event(事件)
                        if isinstance(结果, dict) and bool(结果.get("close_menu", False)):
                            选歌ESC菜单宿主.close()
                            continue
                        if _处理场景返回结果(结果):
                            continue
                        continue

                elif _当前场景允许非游戏菜单():
                    if 事件.type == pygame.KEYDOWN and 事件.key == pygame.K_ESCAPE:
                        if bool(非游戏菜单开启) and bool(投币快捷键录入中):
                            投币快捷键录入中 = False
                            _显示调试提示("已取消修改投币快捷键", 1.0)
                        else:
                            非游戏菜单开启 = not bool(非游戏菜单开启)
                            if not 非游戏菜单开启:
                                投币快捷键录入中 = False
                            非游戏菜单索引 = 0
                            状态["非游戏菜单背景音乐关闭"] = bool(非游戏菜单背景音乐关闭)
                        continue

                    if _处理非游戏菜单按键(事件):
                        continue
                else:
                    if 非游戏菜单开启:
                        非游戏菜单开启 = False
                        非游戏菜单索引 = 0
                        投币快捷键录入中 = False
                    if bool(选歌ESC菜单宿主.is_open()):
                        选歌ESC菜单宿主.close()

                踏板动作 = 解析踏板动作(事件)
                if 踏板动作 is not None:
                    处理踏板 = getattr(当前场景, "处理全局踏板", None)
                    if callable(处理踏板):
                        try:
                            踏板结果 = 处理踏板(踏板动作)
                        except Exception:
                            踏板结果 = None
                        _处理场景返回结果(踏板结果)
                        continue

                try:
                    结果 = 当前场景.处理事件(事件)
                except Exception as 异常:
                    结果 = None
                    try:
                        _显示调试提示(
                            f"场景事件异常：{type(异常).__name__}",
                            1.5,
                        )
                    except Exception:
                        pass
                    _记录异常日志(日志器, "主循环处理场景事件异常", 异常)
                _处理场景返回结果(结果)

        if (not 过渡.是否进行中()) and hasattr(当前场景, "更新"):
            try:
                更新结果 = 当前场景.更新()
            except Exception:
                更新结果 = None
            _处理场景返回结果(更新结果)

        过渡.更新(_执行场景切换)
        入场.更新()

        CPU绘制开始秒 = time.perf_counter()
        上下文["GPU上传脏矩形列表"] = None
        上下文["GPU强制全量上传"] = False
        上下文["开发调试菜单开启"] = bool(开发调试菜单开启)
        try:
            当前场景.绘制()
        except Exception as 异常:
            _记录异常日志(日志器, "主循环场景绘制异常", 异常)
            try:
                if (
                    str(当前场景名 or "") == "谱面播放器"
                    and bool(getattr(当前场景, "_暂停菜单开启", False))
                ):
                    关闭暂停菜单 = getattr(当前场景, "_关闭暂停菜单", None)
                    if callable(关闭暂停菜单):
                        关闭暂停菜单(恢复播放=False)
                    _显示调试提示(
                        f"ESC菜单绘制异常，已自动关闭：{type(异常).__name__}",
                        2.6,
                    )
                else:
                    _显示调试提示(
                        f"场景绘制异常：{type(异常).__name__}",
                        2.4,
                    )
            except Exception:
                pass
            try:
                if isinstance(上下文.get("屏幕"), pygame.Surface):
                    上下文["屏幕"].fill((0, 0, 0))
            except Exception:
                pass
        场景后CPU叠加已绘制 = False
        if bool(选歌ESC菜单宿主.is_open()) and str(当前场景名 or "") == "选歌":
            场景后CPU叠加已绘制 = True
            选歌ESC菜单宿主.draw(上下文["屏幕"])
        else:
            if bool(非游戏菜单开启):
                场景后CPU叠加已绘制 = True
            _绘制非游戏菜单()
        if bool(开发调试菜单开启):
            场景后CPU叠加已绘制 = True
        _绘制开发调试菜单()
        全局点击特效.更新并绘制(上下文["屏幕"])
        if bool(getattr(全局点击特效, "_实例列表", [])):
            场景后CPU叠加已绘制 = True

        if bool(getattr(显示后端, "是否GPU", False)):
            try:
                _右上图层, 右上状态条矩形 = _构建右上状态条图层(
                    int(上下文["屏幕"].get_width()),
                    int(上下文["屏幕"].get_height()),
                )
                del _右上图层
            except Exception:
                右上状态条矩形 = pygame.Rect(0, 0, 0, 0)
        else:
            右上状态条矩形 = _绘制右上状态条()
            _追加GPU上传脏矩形(右上状态条矩形)

        if 调试提示文本 and time.time() < 调试提示截止:
            场景后CPU叠加已绘制 = True
            try:
                小字 = 上下文["字体"]["小字"]
                文面 = 小字.render(调试提示文本, True, (255, 220, 120))
                文r = 文面.get_rect()
                w, _h = 上下文["屏幕"].get_size()
                文r.topright = (w - 12, 44)
                上下文["屏幕"].blit(文面, 文r.topleft)
            except Exception:
                pass

        过渡.绘制(上下文["屏幕"])
        入场.绘制(上下文["屏幕"])

        if bool(场景后CPU叠加已绘制):
            上下文["GPU上传脏矩形列表"] = None
            上下文["GPU强制全量上传"] = True
        CPU绘制毫秒 = (time.perf_counter() - CPU绘制开始秒) * 1000.0

        呈现统计 = {}
        if 显示后端 is not None:
            def _绘制GPU背景(后端):
                绘制方法 = getattr(当前场景, "绘制GPU背景", None)
                if callable(绘制方法):
                    绘制方法(后端)

            def _绘制GPU中层(后端):
                绘制方法 = getattr(当前场景, "绘制GPU中层", None)
                if callable(绘制方法):
                    绘制方法(后端)

            def _绘制GPU叠加(后端):
                绘制方法 = getattr(当前场景, "绘制GPU叠加", None)
                if callable(绘制方法):
                    绘制方法(后端)
                _绘制右上状态条_到显示后端(后端)

            GPU上传脏矩形列表 = 上下文.get("GPU上传脏矩形列表", None)
            GPU强制全量上传 = bool(上下文.get("GPU强制全量上传", False))
            try:
                if callable(getattr(过渡, "是否进行中", None)) and bool(过渡.是否进行中()):
                    GPU强制全量上传 = True
                if callable(getattr(入场, "是否进行中", None)) and bool(入场.是否进行中()):
                    GPU强制全量上传 = True
            except Exception:
                GPU强制全量上传 = True
            try:
                呈现统计 = (
                    显示后端.呈现(
                        _绘制GPU背景,
                        _绘制GPU中层,
                        _绘制GPU叠加,
                        上传脏矩形列表=GPU上传脏矩形列表,
                        强制全量上传=bool(GPU强制全量上传),
                    )
                    or {}
                )
            except Exception as 异常:
                _记录异常日志(日志器, "显示后端呈现异常", 异常)
                if bool(getattr(显示后端, "是否GPU", False)):
                    _重建当前场景并切换后端(
                        "software",
                        持久化为默认=False,
                    )
                    try:
                        if bool(是否全屏):
                            安全窗口w, 安全窗口h = _取当前窗口化尺寸()
                            _应用窗口化分辨率(
                                安全窗口w,
                                安全窗口h,
                                发送事件=False,
                                保存设置=False,
                            )
                    except Exception:
                        pass
                    _显示调试提示(
                        f"GPU显示异常，本次会话已切换CPU兼容模式：{type(异常).__name__}",
                        2.4,
                    )
                    continue
                raise
        else:
            pygame.display.flip()
        帧总毫秒 = (time.perf_counter() - 循环开始秒) * 1000.0
        上下文["主循环最近统计"] = {
            "cpu_draw_ms": float(CPU绘制毫秒),
            "frame_ms": float(帧总毫秒),
        }
        上下文["显示后端最近统计"] = (
            dict(呈现统计) if isinstance(呈现统计, dict) else {}
        )


if __name__ == "__main__":
    主函数()

