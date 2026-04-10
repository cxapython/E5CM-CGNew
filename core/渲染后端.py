import os
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import pygame
from core.常量与路径 import 取运行根目录
from core.日志 import 取日志器 as _取日志器, 记录异常 as _记录异常日志, 记录信息 as _记录信息日志

try:
    from pygame._sdl2 import video as _sdl2_video
except Exception:
    _sdl2_video = None


_应用图标缓存: Optional[pygame.Surface] = None
_应用图标已扫描 = False
_日志器 = _取日志器("core.渲染后端")


额外绘制回调 = Callable[["显示后端基类"], None]
额外背景绘制回调 = Callable[["显示后端基类"], None]
额外中层绘制回调 = Callable[["显示后端基类"], None]


def _设置SDL渲染缩放质量(质量: str = "best"):
    质量文本 = str(质量 or "best").strip().lower() or "best"
    if 质量文本 not in ("0", "1", "2", "nearest", "linear", "best"):
        质量文本 = "best"
    try:
        os.environ["SDL_RENDER_SCALE_QUALITY"] = 质量文本
    except Exception:
        pass
    if os.name != "nt":
        return
    try:
        import ctypes

        if not hasattr(_设置SDL渲染缩放质量, "_sdl2_dll"):
            pygame目录 = Path(getattr(pygame, "__file__", "") or "").resolve().parent
            dll路径 = pygame目录 / "SDL2.dll"
            if dll路径.is_file():
                dll对象 = ctypes.CDLL(str(dll路径))
                dll对象.SDL_SetHint.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
                dll对象.SDL_SetHint.restype = ctypes.c_int
                _设置SDL渲染缩放质量._sdl2_dll = dll对象
            else:
                _设置SDL渲染缩放质量._sdl2_dll = False
        dll对象 = getattr(_设置SDL渲染缩放质量, "_sdl2_dll", None)
        if dll对象:
            dll对象.SDL_SetHint(
                b"SDL_RENDER_SCALE_QUALITY",
                质量文本.encode("utf-8", errors="ignore"),
            )
    except Exception:
        pass


def _规范尺寸(尺寸: Tuple[int, int]) -> Tuple[int, int]:
    try:
        宽 = int(max(1, int(尺寸[0])))
    except Exception:
        宽 = 1280
    try:
        高 = int(max(1, int(尺寸[1])))
    except Exception:
        高 = 720
    return 宽, 高


def _规范刷新率(值: object, 默认值: int = 60) -> int:
    try:
        刷新率 = int(值 or 默认值)
    except Exception:
        刷新率 = int(默认值)
    return max(30, min(240, int(刷新率)))


def _确保显示模块已初始化():
    try:
        if not pygame.display.get_init():
            pygame.display.init()
    except Exception:
        try:
            pygame.display.init()
        except Exception:
            pass


def _取应用图标路径列表() -> List[Path]:
    运行根目录 = Path(取运行根目录())
    return [(运行根目录 / "UI-img" / "app.ico").resolve()]


def _读取应用图标() -> Optional[pygame.Surface]:
    global _应用图标缓存, _应用图标已扫描
    if _应用图标已扫描:
        return _应用图标缓存
    _应用图标已扫描 = True

    for 图标路径 in _取应用图标路径列表():
        try:
            if not 图标路径.is_file():
                continue
            _应用图标缓存 = pygame.image.load(str(图标路径))
            return _应用图标缓存
        except Exception:
            continue
    return None


def _应用窗口图标(窗口=None):
    图标 = _读取应用图标()
    if 图标 is None:
        return
    try:
        pygame.display.set_icon(图标)
    except Exception:
        pass
    try:
        if 窗口 is not None:
            窗口.set_icon(图标)
    except Exception:
        pass


def _读取垂直同步偏好(默认值: bool = False) -> bool:
    文本 = str(os.environ.get("E5CM_VSYNC", "") or "").strip().lower()
    if 文本 in ("1", "true", "yes", "on"):
        return True
    if 文本 in ("0", "false", "no", "off"):
        return False
    return bool(默认值)


def _查找Windows顶层窗口句柄(标题: str = "") -> int:
    if os.name != "nt":
        return 0
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        当前进程id = int(kernel32.GetCurrentProcessId() or 0)
        目标标题 = str(标题 or "").strip()
        候选列表 = []

        def _取窗口标题(hwnd) -> str:
            长度 = int(user32.GetWindowTextLengthW(hwnd) or 0)
            缓冲区 = ctypes.create_unicode_buffer(max(1, 长度 + 1))
            user32.GetWindowTextW(hwnd, 缓冲区, len(缓冲区))
            return str(缓冲区.value or "").strip()

        def _枚举窗口(hwnd, _lparam):
            try:
                if not bool(user32.IsWindowVisible(hwnd)):
                    return True
                进程id = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(进程id))
                if int(进程id.value or 0) != int(当前进程id):
                    return True
                窗口标题 = _取窗口标题(hwnd)
                if 目标标题 and 目标标题 not in 窗口标题 and 窗口标题 not in 目标标题:
                    return True
                rect = wintypes.RECT()
                if not bool(user32.GetWindowRect(hwnd, ctypes.byref(rect))):
                    return True
                宽 = int(rect.right) - int(rect.left)
                高 = int(rect.bottom) - int(rect.top)
                面积 = max(0, 宽) * max(0, 高)
                if 面积 <= 4:
                    return True
                匹配分 = 2 if 目标标题 and 窗口标题 == 目标标题 else (1 if 目标标题 else 0)
                候选列表.append((int(匹配分), int(面积), int(hwnd)))
            except Exception:
                pass
            return True

        枚举回调 = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(枚举回调(_枚举窗口), 0)
        if 候选列表:
            候选列表.sort(reverse=True)
            return int(候选列表[0][2])
    except Exception:
        pass
    return 0


def _尝试激活Windows窗口句柄(hwnd: int) -> bool:
    if os.name != "nt":
        return False
    try:
        hwnd = int(hwnd or 0)
    except Exception:
        hwnd = 0
    if hwnd <= 0:
        return False
    try:
        import ctypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        当前线程id = int(kernel32.GetCurrentThreadId() or 0)
        前台句柄 = int(user32.GetForegroundWindow() or 0)
        前台线程id = int(user32.GetWindowThreadProcessId(前台句柄, None) or 0)
        目标线程id = int(user32.GetWindowThreadProcessId(hwnd, None) or 0)
        已附着前台线程 = False
        已附着目标线程 = False
        成功 = False
        SW_RESTORE = 9
        SW_SHOW = 5
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2

        try:
            if 前台线程id and 前台线程id != 当前线程id:
                user32.AttachThreadInput(前台线程id, 当前线程id, True)
                已附着前台线程 = True
            if 目标线程id and 目标线程id not in (当前线程id, 前台线程id):
                user32.AttachThreadInput(目标线程id, 当前线程id, True)
                已附着目标线程 = True
        except Exception:
            pass

        try:
            try:
                user32.ShowWindow(hwnd, SW_SHOW)
            except Exception:
                pass
            try:
                user32.ShowWindow(hwnd, SW_RESTORE)
            except Exception:
                pass
            try:
                user32.BringWindowToTop(hwnd)
            except Exception:
                pass
            try:
                user32.SetWindowPos(
                    hwnd,
                    HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
                )
                user32.SetWindowPos(
                    hwnd,
                    HWND_NOTOPMOST,
                    0,
                    0,
                    0,
                    0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
                )
            except Exception:
                pass
            try:
                user32.AllowSetForegroundWindow(-1)
            except Exception:
                pass
            try:
                成功 = bool(user32.SetForegroundWindow(hwnd)) or bool(成功)
            except Exception:
                pass
            try:
                成功 = bool(user32.SetActiveWindow(hwnd)) or bool(成功)
            except Exception:
                pass
            try:
                成功 = bool(user32.SetFocus(hwnd)) or bool(成功)
            except Exception:
                pass
        finally:
            try:
                if 已附着目标线程:
                    user32.AttachThreadInput(目标线程id, 当前线程id, False)
            except Exception:
                pass
            try:
                if 已附着前台线程:
                    user32.AttachThreadInput(前台线程id, 当前线程id, False)
            except Exception:
                pass
        return bool(成功)
    except Exception:
        return False


def _尝试激活当前pygame窗口(标题: Optional[str] = None) -> bool:
    _确保显示模块已初始化()
    成功 = False

    if _sdl2_video is not None and hasattr(_sdl2_video.Window, "from_display_module"):
        try:
            窗口 = _sdl2_video.Window.from_display_module()
        except Exception:
            窗口 = None
        if 窗口 is not None:
            try:
                窗口.show()
            except Exception:
                pass
            try:
                窗口.restore()
            except Exception:
                pass
            try:
                窗口.focus()
                成功 = True
            except Exception:
                pass

    if os.name == "nt":
        try:
            hwnd = _查找Windows顶层窗口句柄(str(标题 or ""))
            if hwnd <= 0:
                信息 = pygame.display.get_wm_info()
                hwnd = int((信息 or {}).get("window", 0) or 0)
            if hwnd:
                成功 = bool(_尝试激活Windows窗口句柄(int(hwnd))) or bool(成功)
        except Exception:
            pass

    try:
        pygame.event.pump()
    except Exception:
        pass
    return 成功


def _创建软件显示窗口(
    尺寸: Tuple[int, int],
    flags: int,
) -> pygame.Surface:
    _确保显示模块已初始化()
    请求flags = int(flags | pygame.DOUBLEBUF)
    if _读取垂直同步偏好(False):
        try:
            return pygame.display.set_mode(尺寸, 请求flags, vsync=1)
        except TypeError:
            pass
        except Exception:
            pass
    try:
        return pygame.display.set_mode(尺寸, 请求flags)
    except Exception:
        return pygame.display.set_mode(尺寸, flags)


def _创建透明绘制面(尺寸: Tuple[int, int]) -> pygame.Surface:
    尺寸 = _规范尺寸(尺寸)
    try:
        return pygame.Surface(尺寸, pygame.SRCALPHA, 32).convert_alpha()
    except Exception:
        return pygame.Surface(尺寸, pygame.SRCALPHA, 32)


def _创建平滑缩放缓存面(尺寸: Tuple[int, int]) -> pygame.Surface:
    尺寸 = _规范尺寸(尺寸)
    try:
        return pygame.Surface(尺寸).convert()
    except Exception:
        return pygame.Surface(尺寸)


def _是桌面输出模式(flags: int) -> bool:
    try:
        flags = int(flags or 0)
    except Exception:
        flags = 0
    return bool(flags & pygame.FULLSCREEN) or bool(flags & pygame.NOFRAME)


def _应用SDL2无边框窗口属性(窗口, 桌面尺寸: Tuple[int, int]):
    if 窗口 is None:
        return
    try:
        窗口.set_windowed()
    except Exception:
        pass
    try:
        窗口.borderless = True
    except Exception:
        pass
    try:
        窗口.resizable = False
    except Exception:
        pass
    try:
        窗口.size = tuple(_规范尺寸(桌面尺寸))
    except Exception:
        pass
    try:
        窗口.position = (0, 0)
    except Exception:
        pass
    try:
        标题 = str(getattr(窗口, "title", "") or "")
    except Exception:
        标题 = ""
    try:
        _应用Windows窗口边框样式(标题, 无边框=True, 可调整=False)
    except Exception:
        pass


def _恢复SDL2标准窗口属性(窗口, 尺寸: Tuple[int, int], *, 可调整: bool):
    if 窗口 is None:
        return
    try:
        窗口.set_windowed()
    except Exception:
        pass
    try:
        窗口.borderless = False
    except Exception:
        pass
    try:
        窗口.resizable = bool(可调整)
    except Exception:
        pass
    try:
        窗口.size = tuple(_规范尺寸(尺寸))
    except Exception:
        pass
    try:
        桌面宽, 桌面高 = 取桌面尺寸(tuple(_规范尺寸(尺寸)))
        目标宽, 目标高 = tuple(_规范尺寸(尺寸))
        窗口.position = (
            int(max(0, (int(桌面宽) - int(目标宽)) // 2)),
            int(max(0, (int(桌面高) - int(目标高)) // 2)),
        )
    except Exception:
        pass
    try:
        标题 = str(getattr(窗口, "title", "") or "")
    except Exception:
        标题 = ""
    try:
        _应用Windows窗口边框样式(标题, 无边框=False, 可调整=bool(可调整))
    except Exception:
        pass


def _取Windows窗口句柄(标题: str = "") -> int:
    if os.name != "nt":
        return 0
    try:
        hwnd = _查找Windows顶层窗口句柄(str(标题 or ""))
        if int(hwnd or 0) > 0:
            return int(hwnd)
    except Exception:
        pass
    try:
        信息 = pygame.display.get_wm_info()
        hwnd = int((信息 or {}).get("window", 0) or 0)
        if hwnd > 0:
            return int(hwnd)
    except Exception:
        pass
    return 0


def _应用Windows窗口边框样式(
    标题: str = "",
    *,
    无边框: bool,
    可调整: bool,
) -> bool:
    if os.name != "nt":
        return False
    hwnd = _取Windows窗口句柄(标题)
    if hwnd <= 0:
        return False
    try:
        import ctypes

        user32 = ctypes.windll.user32
        GWL_STYLE = -16
        WS_VISIBLE = 0x10000000
        WS_POPUP = 0x80000000
        WS_CAPTION = 0x00C00000
        WS_SYSMENU = 0x00080000
        WS_THICKFRAME = 0x00040000
        WS_MINIMIZEBOX = 0x00020000
        WS_MAXIMIZEBOX = 0x00010000
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        现有样式 = int(user32.GetWindowLongW(int(hwnd), GWL_STYLE) or 0)
        if bool(无边框):
            新样式 = int((现有样式 & ~int(WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)) | int(WS_POPUP | WS_VISIBLE))
        else:
            新样式 = int((现有样式 & ~int(WS_POPUP)) | int(WS_VISIBLE | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX))
            if bool(可调整):
                新样式 = int(新样式 | int(WS_THICKFRAME | WS_MAXIMIZEBOX))
            else:
                新样式 = int(新样式 & ~int(WS_THICKFRAME | WS_MAXIMIZEBOX))
        if int(新样式) != int(现有样式):
            user32.SetWindowLongW(int(hwnd), GWL_STYLE, int(新样式))
        user32.SetWindowPos(
            int(hwnd),
            0,
            0,
            0,
            0,
            0,
            int(SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED),
        )
        return True
    except Exception:
        return False


def _取Windows原生桌面尺寸() -> Optional[Tuple[int, int]]:
    if os.name != "nt":
        return None

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

        user32 = ctypes.windll.user32
        模式 = DEVMODEW()
        模式.dmSize = ctypes.sizeof(DEVMODEW)
        if bool(user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(模式))):
            宽 = int(模式.dmPelsWidth or 0)
            高 = int(模式.dmPelsHeight or 0)
            if 宽 > 0 and 高 > 0:
                return _规范尺寸((宽, 高))
    except Exception:
        pass

    try:
        import ctypes

        user32 = ctypes.windll.user32
        SM_CXSCREEN = 0
        SM_CYSCREEN = 1
        宽 = int(user32.GetSystemMetrics(SM_CXSCREEN) or 0)
        高 = int(user32.GetSystemMetrics(SM_CYSCREEN) or 0)
        if 宽 > 0 and 高 > 0:
            return _规范尺寸((宽, 高))
    except Exception:
        pass

    return None


def 取桌面尺寸(默认尺寸: Tuple[int, int] = (1280, 720)) -> Tuple[int, int]:
    默认尺寸 = _规范尺寸(默认尺寸)

    已缓存 = getattr(取桌面尺寸, "_cache", None)
    if isinstance(已缓存, tuple) and len(已缓存) >= 2:
        return _规范尺寸(已缓存)

    原生尺寸 = _取Windows原生桌面尺寸()
    if isinstance(原生尺寸, tuple) and len(原生尺寸) >= 2:
        原生尺寸 = _规范尺寸(原生尺寸)
        setattr(取桌面尺寸, "_cache", tuple(原生尺寸))
        return 原生尺寸

    try:
        尺寸列表 = pygame.display.get_desktop_sizes()
        if 尺寸列表:
            结果 = _规范尺寸(tuple(尺寸列表[0]))
            setattr(取桌面尺寸, "_cache", tuple(结果))
            return 结果
    except Exception:
        pass

    try:
        信息 = pygame.display.Info()
        宽 = int(信息.current_w or 默认尺寸[0])
        高 = int(信息.current_h or 默认尺寸[1])
        结果 = _规范尺寸((宽, 高))
        setattr(取桌面尺寸, "_cache", tuple(结果))
        return 结果
    except Exception:
        return 默认尺寸


def 取桌面刷新率(默认值: int = 60) -> int:
    默认值 = _规范刷新率(默认值, 60)

    try:
        if hasattr(pygame.display, "get_current_refresh_rate"):
            return _规范刷新率(pygame.display.get_current_refresh_rate(), 默认值)
    except Exception:
        pass

    启用Windows原生刷新率 = str(
        os.environ.get("E5CM_ENABLE_WIN_REFRESH_API", "")
    ).strip().lower() in ("1", "true", "yes", "on")
    if os.name == "nt" and bool(启用Windows原生刷新率):
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
            模式 = DEVMODEW()
            模式.dmSize = ctypes.sizeof(DEVMODEW)
            if bool(用户32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(模式))):
                return _规范刷新率(int(模式.dmDisplayFrequency or 默认值), 默认值)
        except Exception:
            pass

    return 默认值


class 显示后端基类:
    名称 = "software"
    是否GPU = False

    def __init__(
        self,
        尺寸: Tuple[int, int],
        flags: int,
        标题: str,
    ):
        self._标题 = str(标题 or "")
        self._flags = int(flags)
        self._屏幕尺寸 = _规范尺寸(尺寸)
        self._输出尺寸 = _规范尺寸(尺寸)
        self._桌面刷新率 = 取桌面刷新率(60)
        self._屏幕: Optional[pygame.Surface] = None
        self._最近呈现统计 = {
            "upload_ms": 0.0,
            "overlay_ms": 0.0,
            "present_ms": 0.0,
            "total_ms": 0.0,
        }

    def 取绘制屏幕(self) -> pygame.Surface:
        if self._屏幕 is None:
            raise RuntimeError("显示后端尚未初始化绘制屏幕")
        return self._屏幕

    def 取窗口尺寸(self) -> Tuple[int, int]:
        return _规范尺寸(self._屏幕尺寸)

    def 取输出尺寸(self) -> Tuple[int, int]:
        return _规范尺寸(self._输出尺寸)

    def 取桌面尺寸(self) -> Tuple[int, int]:
        return 取桌面尺寸(self._屏幕尺寸)

    def 取桌面刷新率(self) -> int:
        try:
            self._桌面刷新率 = _规范刷新率(
                取桌面刷新率(int(getattr(self, "_桌面刷新率", 60) or 60)),
                int(getattr(self, "_桌面刷新率", 60) or 60),
            )
        except Exception:
            self._桌面刷新率 = _规范刷新率(
                int(getattr(self, "_桌面刷新率", 60) or 60), 60
            )
        return int(self._桌面刷新率)

    def 设置标题(self, 标题: str):
        self._标题 = str(标题 or "")

    def 调整窗口模式(
        self,
        尺寸: Tuple[int, int],
        flags: int,
    ) -> pygame.Surface:
        raise NotImplementedError

    def 处理事件(self, 事件) -> List[pygame.event.Event]:
        if 事件 is None:
            return []
        return [self._缩放输入事件坐标(事件)]

    def _缩放输入事件坐标(self, 事件):
        事件类型 = int(getattr(事件, "type", -1))
        if 事件类型 not in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
        ):
            return 事件
        if not hasattr(事件, "pos"):
            return 事件
        try:
            if bool(getattr(self, "使用逻辑坐标映射", lambda: False)()):
                return 事件
        except Exception:
            pass
        try:
            输出宽, 输出高 = tuple(self.取输出尺寸())
            绘制宽, 绘制高 = tuple(self.取窗口尺寸())
        except Exception:
            return 事件
        if (
            int(输出宽) <= 0
            or int(输出高) <= 0
            or tuple((int(输出宽), int(输出高))) == tuple((int(绘制宽), int(绘制高)))
        ):
            return 事件
        try:
            原始属性 = dict(getattr(事件, "dict", {}) or {})
        except Exception:
            原始属性 = {}
        try:
            比例x = float(绘制宽) / float(max(1, int(输出宽)))
            比例y = float(绘制高) / float(max(1, int(输出高)))
            pos = getattr(事件, "pos", (0, 0))
            原始属性["pos"] = (
                int(round(float(pos[0]) * 比例x)),
                int(round(float(pos[1]) * 比例y)),
            )
            if 事件类型 == pygame.MOUSEMOTION and hasattr(事件, "rel"):
                rel = getattr(事件, "rel", (0, 0))
                原始属性["rel"] = (
                    int(round(float(rel[0]) * 比例x)),
                    int(round(float(rel[1]) * 比例y)),
                )
            return pygame.event.Event(事件类型, 原始属性)
        except Exception:
            return 事件

    def 呈现(
        self,
        额外背景绘制: Optional[额外背景绘制回调] = None,
        额外中层绘制: Optional[额外中层绘制回调] = None,
        额外绘制: Optional[额外绘制回调] = None,
        上传脏矩形列表=None,
        强制全量上传: bool = False,
    ):
        raise NotImplementedError

    def 取最近呈现统计(self) -> dict:
        return dict(self._最近呈现统计 or {})

    def 取GPU渲染器(self):
        return None

    def 使用逻辑坐标映射(self) -> bool:
        return False

    def 取渲染驱动名(self) -> str:
        return ""

    def 取渲染驱动标签(self) -> str:
        return "CPU-Software"

    def 最大化窗口(self) -> bool:
        return False

    def 激活窗口(self) -> bool:
        return _尝试激活当前pygame窗口(self._标题)

    def 关闭(self):
        self._屏幕 = None


class 软件显示后端(显示后端基类):
    名称 = "software"
    是否GPU = False

    def __init__(
        self,
        尺寸: Tuple[int, int],
        flags: int,
        标题: str,
    ):
        super().__init__(尺寸, flags, 标题)
        self._显示面: Optional[pygame.Surface] = None
        self._平滑缩放缓存: Optional[pygame.Surface] = None
        self.设置标题(标题)
        self.调整窗口模式(尺寸, flags)

    def 设置标题(self, 标题: str):
        super().设置标题(标题)
        try:
            pygame.display.set_caption(self._标题)
        except Exception:
            pass

    def 调整窗口模式(
        self,
        尺寸: Tuple[int, int],
        flags: int,
    ) -> pygame.Surface:
        目标尺寸 = _规范尺寸(尺寸)
        原先桌面输出 = _是桌面输出模式(self._flags)
        self._flags = int(flags)
        当前桌面输出 = _是桌面输出模式(self._flags)
        self._平滑缩放缓存 = None

        if bool(当前桌面输出):
            桌面尺寸 = _规范尺寸(self.取桌面尺寸())
            当前显示面 = pygame.display.get_surface()
            if (
                (not bool(原先桌面输出))
                or (not isinstance(self._显示面, pygame.Surface))
                or (not isinstance(当前显示面, pygame.Surface))
                or 当前显示面 is not self._显示面
                or tuple(self._输出尺寸) != tuple(桌面尺寸)
            ):
                self._显示面 = _创建软件显示窗口(tuple(桌面尺寸), pygame.NOFRAME)
                if _sdl2_video is not None and hasattr(_sdl2_video.Window, "from_display_module"):
                    try:
                        _应用SDL2无边框窗口属性(
                            _sdl2_video.Window.from_display_module(),
                            tuple(桌面尺寸),
                        )
                    except Exception:
                        pass
            self._输出尺寸 = tuple(桌面尺寸)
            self._屏幕 = _创建透明绘制面(tuple(目标尺寸))
            self._屏幕尺寸 = tuple(目标尺寸)
        else:
            self._显示面 = _创建软件显示窗口(tuple(目标尺寸), self._flags)
            if _sdl2_video is not None and hasattr(_sdl2_video.Window, "from_display_module"):
                try:
                    _恢复SDL2标准窗口属性(
                        _sdl2_video.Window.from_display_module(),
                        tuple(目标尺寸),
                        可调整=bool(self._flags & pygame.RESIZABLE),
                    )
                except Exception:
                    pass
            self._屏幕 = self._显示面
            self._屏幕尺寸 = _规范尺寸(self._屏幕.get_size())
            self._输出尺寸 = tuple(self._屏幕尺寸)
        _应用窗口图标()
        self.设置标题(self._标题)
        return self._屏幕

    def 处理事件(self, 事件) -> List[pygame.event.Event]:
        if 事件 is None:
            return []

        # pygame 2 在 Windows 上常只发 WINDOWSIZECHANGED/WINDOWRESIZED，
        # 主循环主要消费 VIDEORESIZE，这里统一桥接，避免窗口放大后逻辑尺寸失步。
        窗口变化事件 = {
            getattr(pygame, "WINDOWRESIZED", -1),
            getattr(pygame, "WINDOWSIZECHANGED", -1),
        }
        if int(getattr(事件, "type", -1)) in 窗口变化事件:
            try:
                宽 = int(getattr(事件, "x", 0) or 0)
            except Exception:
                宽 = 0
            try:
                高 = int(getattr(事件, "y", 0) or 0)
            except Exception:
                高 = 0

            if 宽 <= 0 or 高 <= 0:
                try:
                    当前显示面 = pygame.display.get_surface()
                    if isinstance(当前显示面, pygame.Surface):
                        宽, 高 = tuple(int(v) for v in 当前显示面.get_size())
                except Exception:
                    宽, 高 = 0, 0

            新尺寸 = _规范尺寸((宽 if 宽 > 0 else self._屏幕尺寸[0], 高 if 高 > 0 else self._屏幕尺寸[1]))

            # 无边框桌面输出模式：逻辑屏幕尺寸不变，输出尺寸跟随桌面窗口。
            if bool(_是桌面输出模式(self._flags)):
                self._输出尺寸 = tuple(新尺寸)
                return []

            try:
                当前显示面 = pygame.display.get_surface()
                if isinstance(当前显示面, pygame.Surface):
                    self._显示面 = 当前显示面
                    self._屏幕 = 当前显示面
            except Exception:
                pass

            if isinstance(self._屏幕, pygame.Surface):
                self._屏幕尺寸 = _规范尺寸(tuple(self._屏幕.get_size()))
            else:
                self._屏幕尺寸 = tuple(新尺寸)
            self._输出尺寸 = tuple(self._屏幕尺寸)
            self._平滑缩放缓存 = None

            return [
                pygame.event.Event(
                    pygame.VIDEORESIZE,
                    {
                        "w": int(self._屏幕尺寸[0]),
                        "h": int(self._屏幕尺寸[1]),
                        "size": tuple(self._屏幕尺寸),
                    },
                )
            ]

        # 软件窗口在极少数平台上不触发 WINDOW* 事件，仅 surface 尺寸变化；
        # 在鼠标事件入口轻量同步一次，避免输入坐标与绘制坐标漂移。
        if int(getattr(事件, "type", -1)) in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
        ):
            try:
                当前显示面 = pygame.display.get_surface()
                if (
                    isinstance(当前显示面, pygame.Surface)
                    and tuple(int(v) for v in 当前显示面.get_size()) != tuple(self._屏幕尺寸)
                    and not bool(_是桌面输出模式(self._flags))
                ):
                    self._显示面 = 当前显示面
                    self._屏幕 = 当前显示面
                    self._屏幕尺寸 = _规范尺寸(tuple(self._屏幕.get_size()))
                    self._输出尺寸 = tuple(self._屏幕尺寸)
                    self._平滑缩放缓存 = None
            except Exception:
                pass

        return super().处理事件(事件)

    def 关闭(self):
        self._显示面 = None
        self._平滑缩放缓存 = None
        try:
            if pygame.display.get_init():
                pygame.display.quit()
        except Exception:
            pass
        super().关闭()

    def 呈现(
        self,
        额外背景绘制: Optional[额外背景绘制回调] = None,
        额外中层绘制: Optional[额外中层绘制回调] = None,
        额外绘制: Optional[额外绘制回调] = None,
        上传脏矩形列表=None,
        强制全量上传: bool = False,
    ):
        del 上传脏矩形列表, 强制全量上传
        开始秒 = time.perf_counter()
        overlay开始秒 = time.perf_counter()
        if callable(额外背景绘制):
            额外背景绘制(self)
        if callable(额外中层绘制):
            额外中层绘制(self)
        if callable(额外绘制):
            额外绘制(self)
        overlay_ms = (time.perf_counter() - overlay开始秒) * 1000.0
        present开始秒 = time.perf_counter()
        if (
            isinstance(self._显示面, pygame.Surface)
            and isinstance(self._屏幕, pygame.Surface)
            and self._显示面 is not self._屏幕
        ):
            输出尺寸 = tuple(int(v) for v in self._输出尺寸)
            try:
                if (
                    not isinstance(self._平滑缩放缓存, pygame.Surface)
                    or self._平滑缩放缓存.get_size() != tuple(输出尺寸)
                ):
                    self._平滑缩放缓存 = _创建平滑缩放缓存面(tuple(输出尺寸))
                缩放面 = pygame.transform.smoothscale(
                    self._屏幕,
                    tuple(输出尺寸),
                    self._平滑缩放缓存,
                )
            except Exception:
                缩放面 = None
            if isinstance(缩放面, pygame.Surface):
                try:
                    self._显示面.blit(缩放面, (0, 0))
                except Exception:
                    pass
            else:
                try:
                    pygame.transform.scale(
                        self._屏幕,
                        tuple(输出尺寸),
                        self._显示面,
                    )
                except Exception:
                    pass
        pygame.display.flip()
        present_ms = (time.perf_counter() - present开始秒) * 1000.0
        total_ms = (time.perf_counter() - 开始秒) * 1000.0
        self._最近呈现统计 = {
            "upload_ms": 0.0,
            "overlay_ms": float(overlay_ms),
            "present_ms": float(present_ms),
            "total_ms": float(total_ms),
        }
        return self.取最近呈现统计()

    def 取渲染驱动名(self) -> str:
        return "software"

    def 取渲染驱动标签(self) -> str:
        return "CPU-Software"


class SDL2GPU显示后端(显示后端基类):
    名称 = "gpu-sdl2"
    是否GPU = True

    def __init__(
        self,
        尺寸: Tuple[int, int],
        flags: int,
        标题: str,
        vsync: bool = False,
        驱动偏好: str = "gpu-auto",
    ):
        if _sdl2_video is None:
            raise RuntimeError("当前 pygame 未提供 pygame._sdl2.video")

        super().__init__(尺寸, flags, 标题)
        self._window = None
        self._renderer = None
        self._渲染驱动名 = ""
        self._驱动偏好 = str(驱动偏好 or "gpu-auto")
        self._主纹理 = None
        self._兼容显示面 = None
        self._逻辑坐标映射 = False
        self._vsync = bool(vsync)
        self._确保兼容显示窗口()
        self.设置标题(标题)
        self.调整窗口模式(尺寸, flags)

    def _确保兼容显示窗口(self):
        _确保显示模块已初始化()
        try:
            现有显示面 = pygame.display.get_surface()
            if isinstance(现有显示面, pygame.Surface):
                self._兼容显示面 = 现有显示面
                return
        except Exception:
            pass

        try:
            self._兼容显示面 = pygame.display.set_mode((1, 1), pygame.HIDDEN)
        except TypeError:
            self._兼容显示面 = pygame.display.set_mode((1, 1))
        except Exception:
            self._兼容显示面 = None

    def _取渲染驱动候选索引(self) -> List[int]:
        if _sdl2_video is None or not hasattr(_sdl2_video, "get_drivers"):
            return [-1]
        try:
            驱动信息列表 = list(_sdl2_video.get_drivers())
        except Exception:
            return [-1]
        名称到索引 = {}
        for 索引, 信息 in enumerate(驱动信息列表):
            名称 = str(getattr(信息, "name", "") or "").strip().lower()
            if 名称 and 名称 not in 名称到索引:
                名称到索引[名称] = int(索引)
        偏好文本 = str(getattr(self, "_驱动偏好", "gpu-auto") or "gpu-auto").strip().lower()
        if 偏好文本 == "gpu-d3d11":
            优先名称列表 = ["direct3d11", "direct3d", "direct3d12", "opengl", "opengles2", "software"]
        elif 偏好文本 == "gpu-opengl":
            优先名称列表 = ["opengl", "opengles2", "direct3d11", "direct3d", "direct3d12", "software"]
        elif os.name == "nt":
            优先名称列表 = [
                "direct3d11",
                "direct3d",
                "direct3d12",
                "opengl",
                "opengles2",
                "software",
            ]
        else:
            优先名称列表 = ["opengl", "opengles2", "software"]
        候选索引: List[int] = []
        for 名称 in 优先名称列表:
            if 名称 in 名称到索引:
                候选索引.append(int(名称到索引[名称]))
        for 索引, 信息 in enumerate(驱动信息列表):
            if int(索引) in 候选索引:
                continue
            名称 = str(getattr(信息, "name", "") or "").strip().lower()
            if 名称:
                候选索引.append(int(索引))
        候选索引.append(-1)
        return 候选索引

    def _尝试创建渲染器(self, target_texture: bool = False):
        if _sdl2_video is None or self._window is None:
            return None
        最后异常 = None
        失败信息列表: List[str] = []
        驱动信息列表 = []
        try:
            驱动信息列表 = list(_sdl2_video.get_drivers())
        except Exception:
            驱动信息列表 = []
        for 索引 in self._取渲染驱动候选索引():
            try:
                渲染器 = _sdl2_video.Renderer(
                    self._window,
                    index=int(索引),
                    accelerated=1,
                    vsync=1 if self._vsync else 0,
                    target_texture=bool(target_texture),
                )
                if int(索引) >= 0 and int(索引) < len(驱动信息列表):
                    self._渲染驱动名 = str(
                        getattr(驱动信息列表[int(索引)], "name", "") or ""
                    )
                else:
                    self._渲染驱动名 = ""
                return 渲染器
            except TypeError as 异常:
                最后异常 = 异常
                驱动名 = (
                    str(getattr(驱动信息列表[int(索引)], "name", "") or "")
                    if int(索引) >= 0 and int(索引) < len(驱动信息列表)
                    else "auto"
                )
                失败信息列表.append(f"{驱动名}:TypeError:{异常}")
                try:
                    渲染器 = _sdl2_video.Renderer(
                        self._window,
                        index=int(索引),
                        accelerated=1,
                        vsync=1 if self._vsync else 0,
                    )
                    if int(索引) >= 0 and int(索引) < len(驱动信息列表):
                        self._渲染驱动名 = str(
                            getattr(驱动信息列表[int(索引)], "name", "") or ""
                        )
                    else:
                        self._渲染驱动名 = ""
                    return 渲染器
                except Exception as 二次异常:
                    最后异常 = 二次异常
                    失败信息列表.append(f"{驱动名}:RetryFail:{二次异常}")
                    continue
            except Exception as 异常:
                最后异常 = 异常
                驱动名 = (
                    str(getattr(驱动信息列表[int(索引)], "name", "") or "")
                    if int(索引) >= 0 and int(索引) < len(驱动信息列表)
                    else "auto"
                )
                失败信息列表.append(f"{驱动名}:{type(异常).__name__}:{异常}")
                continue
        if 最后异常 is not None:
            try:
                摘要 = " | ".join(失败信息列表[:8])
                _记录信息日志(
                    _日志器,
                    f"SDL2渲染器创建失败 偏好={self._驱动偏好} vsync={self._vsync} target_texture={target_texture} 失败详情={摘要}",
                )
            except Exception:
                pass
            raise 最后异常
        return None

    def _确保窗口与渲染器(
        self,
        尺寸: Tuple[int, int],
        flags: int,
    ):
        _设置SDL渲染缩放质量("best")
        尺寸 = _规范尺寸(尺寸)
        桌面输出模式 = _是桌面输出模式(flags)
        可调整 = bool(flags & pygame.RESIZABLE) and (not bool(桌面输出模式))

        if self._window is None:
            self._window = _sdl2_video.Window(
                title=self._标题,
                size=尺寸,
                resizable=可调整,
            )
        else:
            try:
                self._window.title = self._标题
            except Exception:
                pass
            try:
                self._window.resizable = 可调整
            except Exception:
                pass

        if self._renderer is None:
            try:
                self._renderer = self._尝试创建渲染器(target_texture=False)
            except Exception:
                self._renderer = self._尝试创建渲染器(target_texture=True)
        _应用窗口图标(self._window)

    def _重建绘制目标(self, 尺寸: Tuple[int, int]):
        尺寸 = _规范尺寸(尺寸)
        if self._屏幕 is not None and self._屏幕.get_size() == 尺寸:
            return

        self._确保兼容显示窗口()
        self._屏幕 = _创建透明绘制面(尺寸)
        self._主纹理 = None
        self._屏幕尺寸 = 尺寸

    def _同步逻辑坐标映射(self) -> bool:
        if self._renderer is None:
            self._逻辑坐标映射 = False
            return False
        try:
            逻辑尺寸 = _规范尺寸(
                tuple(self._屏幕.get_size())
                if isinstance(self._屏幕, pygame.Surface)
                else tuple(self._屏幕尺寸)
            )
        except Exception:
            逻辑尺寸 = _规范尺寸(self._屏幕尺寸)
        try:
            输出尺寸 = _规范尺寸(tuple(self._输出尺寸))
        except Exception:
            输出尺寸 = tuple(逻辑尺寸)

        self._逻辑坐标映射 = False
        try:
            self._renderer.logical_size = tuple(逻辑尺寸)
            self._逻辑坐标映射 = True
        except Exception:
            try:
                比例x = float(max(1, int(输出尺寸[0]))) / float(max(1, int(逻辑尺寸[0])))
                比例y = float(max(1, int(输出尺寸[1]))) / float(max(1, int(逻辑尺寸[1])))
                self._renderer.scale = (float(比例x), float(比例y))
                self._逻辑坐标映射 = True
            except Exception:
                self._逻辑坐标映射 = False
        return bool(self._逻辑坐标映射)

    def _规范脏矩形列表(self, 脏矩形列表) -> List[pygame.Rect]:
        if self._屏幕 is None:
            return []
        屏幕矩形 = self._屏幕.get_rect()
        if 屏幕矩形.w <= 0 or 屏幕矩形.h <= 0:
            return []

        结果: List[pygame.Rect] = []
        for 项 in list(脏矩形列表 or []):
            try:
                if isinstance(项, pygame.Rect):
                    矩形 = 项.copy()
                else:
                    矩形 = pygame.Rect(项)
            except Exception:
                continue
            if 矩形.w <= 0 or 矩形.h <= 0:
                continue
            矩形 = 矩形.inflate(12, 12)
            矩形 = 矩形.clip(屏幕矩形)
            if 矩形.w <= 0 or 矩形.h <= 0:
                continue

            已合并 = False
            for 索引, 已有 in enumerate(结果):
                try:
                    if 已有.inflate(24, 24).colliderect(矩形):
                        结果[索引] = 已有.union(矩形)
                        已合并 = True
                        break
                except Exception:
                    continue
            if not 已合并:
                结果.append(矩形)

        if len(结果) > 12:
            return []

        try:
            脏面积 = sum(int(r.w) * int(r.h) for r in 结果)
            总面积 = int(屏幕矩形.w) * int(屏幕矩形.h)
            if 总面积 > 0 and float(脏面积) / float(总面积) >= 0.72:
                return []
        except Exception:
            return []
        return 结果

    def _同步主纹理(self, 脏矩形列表=None, 强制全量上传: bool = False):
        if self._renderer is None or self._屏幕 is None:
            return

        if self._主纹理 is None:
            self._主纹理 = _sdl2_video.Texture.from_surface(self._renderer, self._屏幕)
            return

        try:
            if bool(强制全量上传):
                self._主纹理.update(self._屏幕)
                return

            if 脏矩形列表 is None:
                self._主纹理.update(self._屏幕)
                return

            显式脏矩形列表 = list(脏矩形列表 or [])
            if not 显式脏矩形列表:
                return

            规范矩形列表 = self._规范脏矩形列表(脏矩形列表)
            if not 规范矩形列表:
                self._主纹理.update(self._屏幕)
                return

            for 矩形 in 规范矩形列表:
                self._主纹理.update(
                    self._屏幕,
                    area=(int(矩形.x), int(矩形.y), int(矩形.w), int(矩形.h)),
                )
        except Exception:
            self._主纹理 = _sdl2_video.Texture.from_surface(self._renderer, self._屏幕)

    def 设置标题(self, 标题: str):
        super().设置标题(标题)
        try:
            pygame.display.set_caption(self._标题)
        except Exception:
            pass
        try:
            if self._window is not None:
                self._window.title = self._标题
        except Exception:
            pass

    def 调整窗口模式(
        self,
        尺寸: Tuple[int, int],
        flags: int,
    ) -> pygame.Surface:
        原先桌面输出 = _是桌面输出模式(self._flags)
        self._flags = int(flags)
        目标尺寸 = _规范尺寸(尺寸)
        self._确保窗口与渲染器(目标尺寸, flags)

        if self._window is None:
            raise RuntimeError("SDL2 Window 初始化失败")

        if bool(_是桌面输出模式(self._flags)):
            桌面尺寸 = _规范尺寸(self.取桌面尺寸())
            if (not bool(原先桌面输出)) or tuple(self._输出尺寸) != tuple(桌面尺寸):
                _应用SDL2无边框窗口属性(self._window, tuple(桌面尺寸))
            else:
                try:
                    self._window.borderless = True
                except Exception:
                    pass
            self._输出尺寸 = tuple(桌面尺寸)
            self._重建绘制目标(目标尺寸)
        else:
            _恢复SDL2标准窗口属性(
                self._window,
                tuple(目标尺寸),
                可调整=bool(self._flags & pygame.RESIZABLE),
            )
            try:
                实际尺寸 = _规范尺寸(tuple(self._window.size))
            except Exception:
                实际尺寸 = tuple(目标尺寸)
            self._输出尺寸 = tuple(实际尺寸)
            self._重建绘制目标(实际尺寸)
        self._同步逻辑坐标映射()

        return self.取绘制屏幕()

    def 处理事件(self, 事件) -> List[pygame.event.Event]:
        if 事件 is None:
            return []

        窗口变化事件 = {
            getattr(pygame, "WINDOWRESIZED", -1),
            getattr(pygame, "WINDOWSIZECHANGED", -1),
        }
        if int(getattr(事件, "type", -1)) in 窗口变化事件:
            try:
                宽 = int(getattr(事件, "x", 0) or 0)
            except Exception:
                宽 = 0
            try:
                高 = int(getattr(事件, "y", 0) or 0)
            except Exception:
                高 = 0
            if 宽 <= 0 or 高 <= 0:
                try:
                    宽, 高 = tuple(self._window.size)
                except Exception:
                    宽, 高 = self._输出尺寸

            新尺寸 = _规范尺寸((宽, 高))
            if bool(_是桌面输出模式(self._flags)):
                self._输出尺寸 = tuple(新尺寸)
                self._同步逻辑坐标映射()
                return []

            尺寸已变化 = tuple(新尺寸) != tuple(self._屏幕尺寸)
            self._输出尺寸 = tuple(新尺寸)
            self._重建绘制目标(新尺寸)
            self._同步逻辑坐标映射()

            if 尺寸已变化 and (not bool(_是桌面输出模式(self._flags))):
                return [
                    pygame.event.Event(
                        pygame.VIDEORESIZE,
                        {
                            "w": int(新尺寸[0]),
                            "h": int(新尺寸[1]),
                            "size": tuple(新尺寸),
                        },
                    )
                ]
            return []

        return super().处理事件(事件)

    def 呈现(
        self,
        额外背景绘制: Optional[额外背景绘制回调] = None,
        额外中层绘制: Optional[额外中层绘制回调] = None,
        额外绘制: Optional[额外绘制回调] = None,
        上传脏矩形列表=None,
        强制全量上传: bool = False,
    ):
        if self._renderer is None:
            return self.取最近呈现统计()
        self._同步逻辑坐标映射()

        开始秒 = time.perf_counter()
        upload开始秒 = time.perf_counter()
        self._同步主纹理(
            脏矩形列表=上传脏矩形列表,
            强制全量上传=bool(强制全量上传),
        )
        self._renderer.draw_color = (0, 0, 0, 255)
        self._renderer.clear()
        if callable(额外背景绘制):
            额外背景绘制(self)
        if callable(额外中层绘制):
            额外中层绘制(self)
        if self._主纹理 is not None:
            if bool(getattr(self, "_逻辑坐标映射", False)):
                self._renderer.blit(self._主纹理)
            else:
                try:
                    输出尺寸 = tuple(int(v) for v in self._输出尺寸)
                except Exception:
                    输出尺寸 = tuple(int(v) for v in self._屏幕尺寸)
                if (
                    len(输出尺寸) >= 2
                    and tuple(输出尺寸[:2]) != tuple(self._屏幕.get_size())
                ):
                    目标矩形 = pygame.Rect(
                        0,
                        0,
                        int(输出尺寸[0]),
                        int(输出尺寸[1]),
                    )
                    self._renderer.blit(
                        self._主纹理,
                        目标矩形,
                    )
                else:
                    self._renderer.blit(self._主纹理)
        upload_ms = (time.perf_counter() - upload开始秒) * 1000.0

        overlay开始秒 = time.perf_counter()
        if callable(额外绘制):
            额外绘制(self)
        overlay_ms = (time.perf_counter() - overlay开始秒) * 1000.0

        present开始秒 = time.perf_counter()
        self._renderer.present()
        present_ms = (time.perf_counter() - present开始秒) * 1000.0
        total_ms = (time.perf_counter() - 开始秒) * 1000.0
        self._最近呈现统计 = {
            "upload_ms": float(upload_ms),
            "overlay_ms": float(overlay_ms),
            "present_ms": float(present_ms),
            "total_ms": float(total_ms),
            "upload_rects": float(
                len(self._规范脏矩形列表(上传脏矩形列表))
                if not bool(强制全量上传)
                else 0
            ),
        }
        return self.取最近呈现统计()

    def 取GPU渲染器(self):
        return self._renderer

    def 使用逻辑坐标映射(self) -> bool:
        return bool(getattr(self, "_逻辑坐标映射", False))

    def 取渲染驱动名(self) -> str:
        return str(getattr(self, "_渲染驱动名", "") or "")

    def 取渲染驱动标签(self) -> str:
        名称 = str(self.取渲染驱动名() or "").strip().lower()
        映射 = {
            "direct3d11": "GPU-D3D11",
            "direct3d12": "GPU-D3D12",
            "direct3d": "GPU-D3D",
            "opengl": "GPU-OpenGL",
            "opengles2": "GPU-OpenGLES2",
            "software": "GPU-Software",
        }
        return str(映射.get(名称, "GPU"))

    def 最大化窗口(self) -> bool:
        try:
            if self._window is not None and (not bool(_是桌面输出模式(self._flags))):
                self._window.maximize()
                return True
        except Exception:
            pass
        return False

    def 激活窗口(self) -> bool:
        成功 = False
        try:
            if self._window is not None:
                try:
                    self._window.show()
                except Exception:
                    pass
                try:
                    self._window.restore()
                except Exception:
                    pass
                self._window.focus()
                try:
                    self._window.grab = False
                except Exception:
                    pass
                try:
                    pygame.event.pump()
                except Exception:
                    pass
                成功 = True
        except Exception:
            pass
        return bool(super().激活窗口() or 成功)

    def 关闭(self):
        self._主纹理 = None
        self._renderer = None
        try:
            if self._window is not None:
                self._window.destroy()
        except Exception:
            pass
        self._window = None
        self._兼容显示面 = None
        try:
            if pygame.display.get_init():
                pygame.display.quit()
        except Exception:
            pass
        super().关闭()


def 读取后端偏好(偏好: Optional[str] = None, 默认值: str = "software") -> str:
    if 偏好 is None or not str(偏好).strip():
        文本 = str(os.environ.get("E5CM_RENDER_BACKEND", 默认值) or 默认值)
    else:
        文本 = str(偏好 or 默认值)
    文本 = 文本.strip().lower().replace("_", "-")
    if 文本 in ("gpu", "gpu-sdl2", "sdl2", "gpu-auto", "auto"):
        return "gpu-auto"
    if 文本 in ("gpu-d3d11", "d3d11", "direct3d11"):
        return "gpu-d3d11"
    if 文本 in ("gpu-opengl", "opengl", "ogl"):
        return "gpu-opengl"
    return "software"


def 创建显示后端(
    尺寸: Tuple[int, int],
    flags: int,
    标题: str,
    偏好: str = "software",
) -> 显示后端基类:
    模式 = 读取后端偏好(偏好=偏好, 默认值="software")
    启用垂直同步 = _读取垂直同步偏好(False)
    GPU驱动偏好 = str(模式 if str(模式).startswith("gpu-") else "gpu-auto")
    _记录信息日志(
        _日志器,
        f"创建显示后端 请求偏好={偏好} 解析模式={模式} 尺寸={tuple(尺寸)} flags={int(flags)} vsync={bool(启用垂直同步)}",
    )

    def _尝试创建GPU后端() -> 显示后端基类:
        try:
            return SDL2GPU显示后端(
                尺寸,
                flags,
                标题,
                vsync=启用垂直同步,
                驱动偏好=GPU驱动偏好,
            )
        except Exception as 异常:
            _记录异常日志(
                _日志器,
                f"GPU后端创建失败，准备重试（关闭vsync） 驱动偏好={GPU驱动偏好}",
                异常,
            )
            if 启用垂直同步:
                return SDL2GPU显示后端(
                    尺寸,
                    flags,
                    标题,
                    vsync=False,
                    驱动偏好=GPU驱动偏好,
                )
            raise

    if str(模式).startswith("gpu-"):
        try:
            return _尝试创建GPU后端()
        except Exception as 异常:
            _记录异常日志(
                _日志器,
                f"GPU后端不可用，已降级软件后端 解析模式={模式}",
                异常,
            )
            return 软件显示后端(尺寸, flags, 标题)

    return 软件显示后端(尺寸, flags, 标题)
