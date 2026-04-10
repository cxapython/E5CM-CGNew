from typing import Any, Dict, List, Optional, Tuple

import pygame


_情侣高阈值特效前缀: Tuple[str, ...] = (
    "image_313",
    "image_314",
    "image_315",
    "image_316",
    "image_324",
    "image_325",
    "image_326",
    "image_327",
)


def _图集含帧前缀(图集: Any, 前缀: str) -> bool:
    if 图集 is None or not hasattr(图集, "取"):
        return False
    前缀 = str(前缀 or "").strip()
    if not 前缀:
        return False
    try:
        return 图集.取(f"{前缀}_0000.png") is not None
    except Exception:
        return False


def _取情侣特效前缀集合(图集: Any, 玩家序号: int = 1) -> Dict[str, str]:
    try:
        玩家 = int(玩家序号)
    except Exception:
        玩家 = 1

    def _取首个可用(候选: List[str], 默认值: str) -> str:
        for 项 in 候选:
            if _图集含帧前缀(图集, str(项)):
                return str(项)
        return str(默认值)

    if 玩家 == 2:
        if any(_图集含帧前缀(图集, 前缀) for 前缀 in ("image_313", "image_314", "image_315", "image_316")):
            return {
                "hand": _取首个可用(["image_313", "image_324"], "image_313"),
                "lb": _取首个可用(["image_314", "image_325"], "image_314"),
                "lt": _取首个可用(["image_315", "image_326"], "image_315"),
                "cc": _取首个可用(["image_316", "image_327"], "image_316"),
            }
    if any(_图集含帧前缀(图集, 前缀) for 前缀 in ("image_324", "image_325", "image_326", "image_327")):
        return {
            "hand": _取首个可用(["image_324", "image_313"], "image_324"),
            "lb": _取首个可用(["image_325", "image_314"], "image_325"),
            "lt": _取首个可用(["image_326", "image_315"], "image_326"),
            "cc": _取首个可用(["image_327", "image_316"], "image_327"),
        }
    if any(_图集含帧前缀(图集, 前缀) for 前缀 in ("image_313", "image_314", "image_315", "image_316")):
        return {
            "hand": _取首个可用(["image_313", "image_324"], "image_313"),
            "lb": _取首个可用(["image_314", "image_325"], "image_314"),
            "lt": _取首个可用(["image_315", "image_326"], "image_315"),
            "cc": _取首个可用(["image_316", "image_327"], "image_316"),
        }
    return {}


def 轨道到击中序列(
    轨道: int, 图集: Any = None, 玩家序号: int = 1
) -> Tuple[str, bool, float]:
    轨道 = int(轨道)
    情侣前缀 = _取情侣特效前缀集合(图集, 玩家序号=玩家序号)
    if 情侣前缀:
        if 轨道 == 0:
            return (str(情侣前缀.get("lb", "image_084")), False, 0.0)
        if 轨道 == 1:
            return (str(情侣前缀.get("lt", "image_085")), False, 0.0)
        if 轨道 == 2:
            return (str(情侣前缀.get("cc", "image_086")), False, 0.0)
        if 轨道 == 3:
            return (str(情侣前缀.get("lt", "image_085")), True, 0.0)
        if 轨道 == 4:
            return (str(情侣前缀.get("lb", "image_084")), True, 0.0)
        if 轨道 == 5:
            return (str(情侣前缀.get("hand", "image_083")), False, 0.0)
        if 轨道 == 6:
            return (str(情侣前缀.get("hand", "image_083")), False, -90.0)
        if 轨道 == 7:
            return (str(情侣前缀.get("hand", "image_083")), False, 90.0)
        if 轨道 == 8:
            return (str(情侣前缀.get("hand", "image_083")), True, 0.0)
        return (str(情侣前缀.get("cc", "image_086")), False, 0.0)

    if 轨道 == 0:
        return ("image_084", False, 0.0)
    if 轨道 == 1:
        return ("image_085", False, 0.0)
    if 轨道 == 2:
        return ("image_086", False, 0.0)
    if 轨道 == 3:
        return ("image_085", True, 0.0)
    if 轨道 == 4:
        return ("image_084", True, 0.0)
    if 轨道 == 5:
        return ("image_083", False, 0.0)
    if 轨道 == 6:
        # 手键上（tt）
        return ("image_083", False, -90.0)
    if 轨道 == 7:
        # 手键下（bb）
        return ("image_083", False, 90.0)
    if 轨道 == 8:
        return ("image_083", True, 0.0)
    return ("image_086", False, 0.0)


def _取击中特效轨道总数(宿主: Any) -> int:
    取总数 = getattr(宿主, "_击中特效轨道总数", None)
    if callable(取总数):
        try:
            return int(max(5, int(取总数())))
        except Exception:
            return 5
    return 5


def _取key_effect图集(宿主: Any, 输入: Any) -> Optional[Any]:
    皮肤包 = getattr(宿主, "_皮肤包", None)
    if 皮肤包 is None:
        return None
    取分玩家图集 = getattr(皮肤包, "取key_effect图集", None)
    if callable(取分玩家图集):
        try:
            玩家序号 = int(getattr(输入, "玩家序号", 1) or 1)
        except Exception:
            玩家序号 = 1
        try:
            图集 = 取分玩家图集(int(玩家序号))
            if 图集 is not None:
                return 图集
        except Exception:
            pass
    return getattr(皮肤包, "key_effect", None)


def _取帧文件后缀(文件名: str) -> str:
    文本 = str(文件名 or "").strip()
    if not 文本:
        return ""
    分隔点 = 文本.rfind("_")
    if 分隔点 < 0 or 分隔点 >= len(文本) - 1:
        return ""
    return str(文本[分隔点 + 1 :])


def _取击中特效帧(图集: Any, 文件名: str, 统一前缀: str = "") -> Optional[pygame.Surface]:
    if 图集 is None or (not hasattr(图集, "取")):
        return None
    文件名 = str(文件名 or "").strip()
    if not 文件名:
        return None

    try:
        原图 = 图集.取(文件名)
    except Exception:
        原图 = None
    if 原图 is not None:
        return 原图

    后缀 = _取帧文件后缀(文件名)
    if 统一前缀 and 后缀:
        try:
            原图 = 图集.取(f"{统一前缀}_{后缀}")
        except Exception:
            原图 = None
        if 原图 is not None:
            return 原图

    if str(文件名).startswith("image_083_"):
        try:
            return 图集.取(str(文件名).replace("image_083_", "image_084_", 1))
        except Exception:
            return None
    return None


def _取击中特效去黑阈值(文件名: str) -> int:
    名 = str(文件名 or "").strip().lower()
    if not 名:
        return 12
    for 前缀 in _情侣高阈值特效前缀:
        if 名.startswith(f"{前缀}_"):
            return 28
    return 12


def _取游戏区参数(宿主: Any) -> Dict[str, float]:
    取参数 = getattr(宿主, "_取游戏区参数", None)
    if not callable(取参数):
        return {}
    try:
        return dict(取参数() or {})
    except Exception:
        return {}


def _取击中特效布局矩形表(
    宿主: Any,
    屏幕: pygame.Surface,
    输入: Any,
) -> Dict[int, pygame.Rect]:
    取矩形表 = getattr(宿主, "_取击中特效布局矩形表", None)
    if not callable(取矩形表):
        return {}
    try:
        值 = dict(取矩形表(屏幕, 输入) or {})
    except Exception:
        return {}
    结果: Dict[int, pygame.Rect] = {}
    for 键, 矩形 in 值.items():
        if not isinstance(矩形, pygame.Rect):
            continue
        try:
            结果[int(键)] = 矩形.copy()
        except Exception:
            continue
    return 结果


def 绘制击中特效序列帧(
    宿主: Any,
    屏幕: pygame.Surface,
    输入: Any,
    使用加色混合: bool = True,
) -> None:
    if not isinstance(屏幕, pygame.Surface) or 输入 is None:
        return
    图集 = _取key_effect图集(宿主, 输入)
    if 图集 is None:
        return
    try:
        玩家序号 = int(getattr(输入, "玩家序号", 1) or 1)
    except Exception:
        玩家序号 = 1

    开始列表 = getattr(宿主, "_击中特效开始谱面秒", [])
    循环列表 = getattr(宿主, "_击中特效循环到谱面秒", [])
    进行列表 = getattr(宿主, "_击中特效进行秒", [])
    if (
        not isinstance(开始列表, list)
        or not isinstance(循环列表, list)
        or not isinstance(进行列表, list)
    ):
        return

    轨道总数 = int(
        max(
            0,
            min(
                _取击中特效轨道总数(宿主),
                len(开始列表),
                len(循环列表),
                len(进行列表),
            ),
        )
    )
    if 轨道总数 <= 0:
        return

    GPU接管击中特效绘制 = bool(getattr(输入, "GPU接管击中特效绘制", False))
    if (not bool(GPU接管击中特效绘制)) and bool(
        getattr(输入, "调试_循环击中特效", False)
    ):
        当前 = float(getattr(输入, "当前谱面秒", 0.0) or 0.0)
        for i in range(int(轨道总数)):
            开始列表[i] = 当前
            循环列表[i] = 当前 + 99999.0
            if float(进行列表[i]) < 0.0:
                进行列表[i] = 0.0

    参数 = _取游戏区参数(宿主)
    游戏缩放 = float(参数.get("缩放", 1.1) or 1.1)
    y偏移 = float(参数.get("y偏移", 0.0) or 0.0)
    偏移x = float(参数.get("击中特效偏移x", 0.0) or 0.0)
    偏移y = float(参数.get("击中特效偏移y", 0.0) or 0.0)
    宽度系数 = float(参数.get("击中特效宽度系数", 2.6) or 2.6)

    当前谱面秒 = float(getattr(输入, "当前谱面秒", 0.0) or 0.0)
    y判定 = int(float(getattr(输入, "判定线y", 0) or 0) + y偏移 + 偏移y)
    目标宽 = int(
        max(
            90,
            int(
                float(getattr(输入, "箭头目标宽", 0) or 0)
                * 宽度系数
                * 游戏缩放
                * 1.25
            ),
        )
    )
    帧数 = 18
    帧率 = float(getattr(宿主, "_击中特效帧率", 60.0) or 60.0)

    特效帧名列表: List[str] = [""] * int(轨道总数)
    特效翻转列表: List[bool] = [False] * int(轨道总数)
    特效旋转角度列表: List[float] = [0.0] * int(轨道总数)

    for i in range(int(轨道总数)):
        开始谱面秒 = float(开始列表[i])
        循环到 = float(循环列表[i])

        if 开始谱面秒 > -900.0 and 当前谱面秒 + 0.08 < 开始谱面秒:
            进行列表[i] = -1.0
            开始列表[i] = -999.0
            循环列表[i] = -999.0
            continue

        if 循环到 > 0.0:
            if 当前谱面秒 > 循环到 + 0.02:
                循环列表[i] = -999.0
                进行列表[i] = -1.0
                开始列表[i] = -999.0
                continue
            进行秒 = float(进行列表[i])
            if 进行秒 < 0.0:
                进行秒 = 0.0
            帧号 = int(max(0, min(帧数 - 1, int(进行秒 * 帧率))))
        else:
            进行秒 = float(进行列表[i])
            if 进行秒 < 0.0:
                continue
            帧号 = int(max(0, min(帧数 - 1, int(进行秒 * 帧率))))

        序列前缀, 需要水平翻转, 旋转角度 = 轨道到击中序列(
            i, 图集=图集, 玩家序号=int(玩家序号)
        )
        特效帧名列表[i] = f"{序列前缀}_{帧号:04d}.png"
        特效翻转列表[i] = bool(需要水平翻转)
        特效旋转角度列表[i] = float(旋转角度)

    特效布局矩形表 = _取击中特效布局矩形表(宿主, 屏幕, 输入)
    取预处理图 = getattr(宿主, "_取预处理图", None)
    取缩放图 = getattr(宿主, "_取缩放图", None)
    if not callable(取预处理图) or not callable(取缩放图):
        return

    try:
        轨道中心 = list(getattr(输入, "轨道中心列表", []) or [])
    except Exception:
        轨道中心 = []

    for i in range(int(轨道总数)):
        文件名 = str(特效帧名列表[i] or "")
        if not 文件名:
            continue

        原图 = _取击中特效帧(图集, 文件名, 统一前缀="")
        if 原图 is None:
            continue

        当前目标宽 = int(max(48, 目标宽))
        布局矩形 = 特效布局矩形表.get(int(i))
        if isinstance(布局矩形, pygame.Rect):
            当前目标宽 = int(max(48, 布局矩形.w))

        需要翻转 = bool(特效翻转列表[i])
        旋转角度 = float(
            特效旋转角度列表[i] if i < len(特效旋转角度列表) else 0.0
        )
        变换标记 = f"fx{1 if 需要翻转 else 0}:r{int(round(旋转角度 * 10.0))}"
        缓存键 = f"eff:{文件名}:{变换标记}:{当前目标宽}"
        原图2 = 取预处理图(
            f"effect_raw:{文件名}",
            原图,
            水平翻转=bool(需要翻转),
            旋转角度=float(旋转角度),
            黑底透明=True,
            黑阈值=int(_取击中特效去黑阈值(文件名)),
        )
        if 原图2 is None:
            continue
        图2 = 取缩放图(缓存键, 原图2, 当前目标宽)
        if 图2 is None:
            continue

        if isinstance(布局矩形, pygame.Rect):
            x = int(布局矩形.centerx - 图2.get_width() // 2)
            y = int(布局矩形.centery - 图2.get_height() // 2)
        else:
            中心x默认 = int(
                轨道中心[i]
                if 0 <= int(i) < len(轨道中心)
                else (轨道中心[2] if len(轨道中心) >= 3 else 0)
            )
            x = int(float(中心x默认) - 图2.get_width() // 2 + 偏移x)
            y = int(y判定 - 图2.get_height() // 2)

        if bool(使用加色混合):
            屏幕.blit(图2, (x, y), special_flags=pygame.BLEND_RGBA_ADD)
        else:
            屏幕.blit(图2, (x, y))
