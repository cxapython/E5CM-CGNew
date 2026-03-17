import bisect
import math
from typing import Any, Dict, List, Optional, Tuple

import pygame

from core.game_esc_menu_settings import is_binding_pressed

try:
    from pygame._sdl2 import video as _sdl2_video
except Exception:
    _sdl2_video = None


def _取浮点(值: Any, 默认值: float = 0.0) -> float:
    try:
        return float(值)
    except Exception:
        return float(默认值)


def _取整数(值: Any, 默认值: int = 0) -> int:
    try:
        return int(值)
    except Exception:
        return int(默认值)


class 谱面GPU管线渲染器:
    def __init__(self):
        self._左帧: Optional[Dict[str, Any]] = None
        self._右帧: Optional[Dict[str, Any]] = None
        self._事件缓存表: Dict[int, Dict[str, Any]] = {}
        self._纹理缓存表: Dict[Tuple[int, int, int, int], Any] = {}
        self._灰度图缓存表: Dict[Tuple[int, int, int], pygame.Surface] = {}
        self._最近绘制统计: str = ""
        self._最近渲染器id: int = 0
        self._彩色轨道颜色: List[Tuple[int, int, int]] = [
            (44, 214, 255),
            (45, 232, 118),
            (255, 152, 48),
            (255, 92, 181),
            (255, 227, 72),
        ]
        self._灰度轨道颜色: List[Tuple[int, int, int]] = [
            (170, 170, 170),
            (182, 182, 182),
            (196, 196, 196),
            (162, 162, 162),
            (205, 205, 205),
        ]

    def 清空(self):
        self._左帧 = None
        self._右帧 = None
        self._最近绘制统计 = ""

    def 提交帧(
        self,
        左输入,
        右输入=None,
        左渲染器=None,
        右渲染器=None,
        屏幕: Optional[pygame.Surface] = None,
    ):
        self._左帧 = self._构建帧输入(左输入, 左渲染器, 屏幕)
        self._右帧 = self._构建帧输入(右输入, 右渲染器, 屏幕)

    def 取最近绘制统计(self) -> str:
        return str(self._最近绘制统计 or "")

    def 绘制(self, 显示后端):
        if 显示后端 is None:
            return
        取渲染器 = getattr(显示后端, "取GPU渲染器", None)
        if not callable(取渲染器):
            return
        渲染器 = 取渲染器()
        if 渲染器 is None:
            return

        self._同步纹理缓存归属(渲染器)

        notes数 = 0
        判定区数 = 0
        特效数 = 0
        计数动画数 = 0
        for 帧输入 in (self._左帧, self._右帧):
            单侧notes, 单侧判定区, 单侧特效, 单侧计数动画 = self._绘制单侧(渲染器, 帧输入)
            notes数 += int(单侧notes)
            判定区数 += int(单侧判定区)
            特效数 += int(单侧特效)
            计数动画数 += int(单侧计数动画)

        self._最近绘制统计 = (
            f"GPU notes={int(notes数)} receptor={int(判定区数)} fx={int(特效数)} judge={int(计数动画数)}"
        )

    def _同步纹理缓存归属(self, 渲染器):
        当前渲染器id = int(id(渲染器))
        if 当前渲染器id == int(getattr(self, "_最近渲染器id", 0) or 0):
            return
        self._最近渲染器id = 当前渲染器id
        if not self._纹理缓存表:
            return
        删除键 = [键 for 键 in self._纹理缓存表 if int(键[0]) != 当前渲染器id]
        for 键 in 删除键:
            self._纹理缓存表.pop(键, None)

    def _构建帧输入(
        self,
        输入,
        软件渲染器=None,
        屏幕: Optional[pygame.Surface] = None,
    ) -> Optional[Dict[str, Any]]:
        if 输入 is None:
            return None
        try:
            轨道中心列表 = [
                int(v) for v in list(getattr(输入, "轨道中心列表", []) or [])[:5]
            ]
        except Exception:
            轨道中心列表 = []
        if len(轨道中心列表) < 5:
            return None

        原事件列表 = getattr(输入, "事件列表", []) or []
        事件列表 = 原事件列表 if isinstance(原事件列表, list) else list(原事件列表)

        判定区列表: List[Dict[str, Any]] = []
        击中特效列表: List[Dict[str, Any]] = []
        计数动画图层: Optional[pygame.Surface] = None
        计数动画矩形: Optional[pygame.Rect] = None
        Stage数据: Dict[str, Any] = {}
        HUD数据: Dict[str, Any] = {}
        游戏区参数: Dict[str, float] = {}
        布局锚点: Optional[Dict[str, Any]] = None
        if 屏幕 is not None and 软件渲染器 is not None:
            取判定区数据 = getattr(软件渲染器, "取GPU判定区数据", None)
            if callable(取判定区数据):
                try:
                    判定区列表 = list(取判定区数据(屏幕, 输入) or [])
                except Exception:
                    判定区列表 = []
            取击中特效数据 = getattr(软件渲染器, "取GPU击中特效数据", None)
            if callable(取击中特效数据):
                try:
                    击中特效列表 = list(取击中特效数据(屏幕, 输入) or [])
                except Exception:
                    击中特效列表 = []
            取游戏区参数 = getattr(软件渲染器, "_取游戏区参数", None)
            if callable(取游戏区参数):
                try:
                    游戏区参数 = dict(取游戏区参数() or {})
                except Exception:
                    游戏区参数 = {}
            取判定区实际锚点 = getattr(软件渲染器, "_取判定区实际锚点", None)
            if callable(取判定区实际锚点):
                try:
                    结果 = 取判定区实际锚点(屏幕, 输入)
                    if isinstance(结果, dict):
                        布局锚点 = dict(结果)
                except Exception:
                    布局锚点 = None
            if bool(getattr(输入, "GPU接管计数动画绘制", False)):
                取计数动画图层 = getattr(软件渲染器, "取GPU计数动画图层", None)
                if callable(取计数动画图层):
                    try:
                        图层结果 = 取计数动画图层(屏幕, 输入)
                        if (
                            isinstance(图层结果, tuple)
                            and len(图层结果) == 2
                        ):
                            候选图层, 候选矩形 = 图层结果
                            if isinstance(候选图层, pygame.Surface):
                                计数动画图层 = 候选图层
                            if isinstance(候选矩形, pygame.Rect):
                                计数动画矩形 = 候选矩形.copy()
                    except Exception:
                        计数动画图层 = None
                        计数动画矩形 = None
            取Stage数据 = getattr(软件渲染器, "取GPUStage数据", None)
            if callable(取Stage数据):
                try:
                    Stage数据 = dict(取Stage数据(屏幕, 输入) or {})
                except Exception:
                    Stage数据 = {}
            取HUD数据 = getattr(软件渲染器, "取GPU顶部HUD数据", None)
            if callable(取HUD数据):
                try:
                    HUD数据 = dict(取HUD数据(屏幕, 输入) or {})
                except Exception:
                    HUD数据 = {}

        游戏缩放 = float(游戏区参数.get("缩放", 1.0) or 1.0)
        y偏移 = float(游戏区参数.get("y偏移", 0.0) or 0.0)
        hold宽度系数 = float(游戏区参数.get("hold宽度系数", 0.96) or 0.96)
        判定线y列表: List[int] = []
        y判定 = int(float(getattr(输入, "判定线y", 0) or 0) + y偏移)
        if isinstance(布局锚点, dict):
            try:
                轨道中心列表 = [
                    int(v)
                    for v in list(布局锚点.get("轨道中心列表", 轨道中心列表) or 轨道中心列表)[:5]
                ]
            except Exception:
                pass
            try:
                判定线y列表 = [
                    int(v) for v in list(布局锚点.get("判定线y列表", []) or [])[:5]
                ]
            except Exception:
                判定线y列表 = []
            try:
                y判定 = int(布局锚点.get("判定线y", y判定) or y判定)
            except Exception:
                pass
        while len(判定线y列表) < 5:
            判定线y列表.append(int(y判定))

        y底 = int(float(getattr(输入, "底部y", 0) or 0) + y偏移)
        有效速度 = max(
            60.0, float(_取浮点(getattr(输入, "滚动速度px每秒", 0.0), 60.0)) * 游戏缩放
        )
        箭头宽_tap = int(
            max(18, int(float(_取整数(getattr(输入, "箭头目标宽", 32), 32)) * 游戏缩放))
        )
        箭头宽_hold = int(max(16, int(float(箭头宽_tap) * hold宽度系数)))
        上边界 = -int(max(40, 箭头宽_tap * 2))
        下边界 = int(y底 + max(40, 箭头宽_tap * 2))
        半隐y阈值 = (
            int(屏幕.get_height() * 0.5)
            if isinstance(屏幕, pygame.Surface)
            else int(max(0, y判定 - (y判定 * 0.45)))
        )
        可视秒 = float(max(1, (y底 - y判定))) / float(max(60.0, float(有效速度)))

        return {
            "当前谱面秒": _取浮点(getattr(输入, "当前谱面秒", 0.0), 0.0),
            "谱面视觉偏移秒": _取浮点(getattr(输入, "谱面视觉偏移秒", 0.0), 0.0),
            "BPM变速效果开启": bool(getattr(输入, "BPM变速效果开启", False)),
            "BPM变速合成脉冲开启": bool(
                getattr(输入, "BPM变速合成脉冲开启", False)
            ),
            "BPM变速秒转beat函数": getattr(输入, "BPM变速秒转beat函数", None),
            "BPM变速像素每拍": _取浮点(
                getattr(输入, "BPM变速像素每拍", 0.0), 0.0
            ),
            "轨道中心列表": 轨道中心列表,
            "判定线y": int(y判定),
            "判定线y列表": 判定线y列表[:5],
            "底部y": int(y底),
            "滚动速度px每秒": float(有效速度),
            "箭头目标宽": int(箭头宽_tap),
            "hold目标宽": int(箭头宽_hold),
            "上边界": int(上边界),
            "下边界": int(下边界),
            "半隐y阈值": int(半隐y阈值),
            "提前秒": float(可视秒 + 1.0),
            "事件列表": 事件列表,
            "隐藏模式": str(getattr(输入, "隐藏模式", "关闭") or "关闭"),
            "轨迹模式": str(getattr(输入, "轨迹模式", "正常") or "正常"),
            "Note层灰度": bool(getattr(输入, "Note层灰度", False)),
            "判定区列表": 判定区列表,
            "击中特效列表": 击中特效列表,
            "计数动画图层": 计数动画图层,
            "计数动画矩形": 计数动画矩形,
            "Stage数据": Stage数据,
            "HUD数据": HUD数据,
            "软件渲染器": 软件渲染器,
        }

    def _取事件缓存(self, 事件列表: List[Any]) -> Dict[str, Any]:
        if not isinstance(事件列表, list):
            事件列表 = list(事件列表 or [])
        首事件 = 事件列表[0] if 事件列表 else None
        末事件 = 事件列表[-1] if 事件列表 else None
        签名 = (
            id(事件列表),
            int(len(事件列表)),
            _取浮点(getattr(首事件, "开始秒", 0.0), 0.0),
            _取浮点(getattr(末事件, "开始秒", 0.0), 0.0),
            _取浮点(getattr(末事件, "结束秒", 0.0), 0.0),
        )
        缓存键 = int(id(事件列表))
        已有缓存 = self._事件缓存表.get(缓存键)
        if isinstance(已有缓存, dict) and 已有缓存.get("签名") == 签名:
            return 已有缓存

        开始秒列表: List[float] = []
        前缀最大结束秒: List[float] = []
        开始beat列表: List[float] = []
        前缀最大结束beat: List[float] = []
        当前最大结束秒 = -1e12
        当前最大结束beat = -1e12
        for 事件 in 事件列表:
            开始秒 = _取浮点(getattr(事件, "开始秒", 0.0), 0.0)
            结束秒 = _取浮点(getattr(事件, "结束秒", 开始秒), 开始秒)
            开始beat = _取浮点(getattr(事件, "开始beat", 0.0), 0.0)
            结束beat = _取浮点(getattr(事件, "结束beat", 开始beat), 开始beat)
            if 结束秒 < 开始秒:
                结束秒 = 开始秒
            if 结束beat < 开始beat:
                结束beat = 开始beat
            开始秒列表.append(开始秒)
            开始beat列表.append(开始beat)
            当前最大结束秒 = max(当前最大结束秒, 结束秒)
            当前最大结束beat = max(当前最大结束beat, 结束beat)
            前缀最大结束秒.append(当前最大结束秒)
            前缀最大结束beat.append(当前最大结束beat)

        新缓存 = {
            "签名": 签名,
            "事件列表": 事件列表,
            "开始秒列表": 开始秒列表,
            "开始beat列表": 开始beat列表,
            "前缀最大结束秒": 前缀最大结束秒,
            "前缀最大结束beat": 前缀最大结束beat,
        }
        self._事件缓存表[缓存键] = 新缓存
        if len(self._事件缓存表) > 8:
            for 旧键 in list(self._事件缓存表.keys())[:-8]:
                self._事件缓存表.pop(旧键, None)
        return 新缓存

    def _绘制单侧(self, 渲染器, 帧输入: Optional[Dict[str, Any]]) -> Tuple[int, int, int, int]:
        if not isinstance(帧输入, dict):
            return 0, 0, 0, 0
        轨道中心列表 = list(帧输入.get("轨道中心列表", []) or [])[:5]
        if len(轨道中心列表) < 5:
            return 0, 0, 0, 0
        self._绘制Stage组(渲染器, 帧输入)
        notes数 = self._绘制音符组(渲染器, 帧输入)
        判定区数 = self._绘制判定区组(渲染器, 帧输入)
        特效数 = self._绘制击中特效组(渲染器, 帧输入)
        self._绘制HUD组(渲染器, 帧输入)
        计数动画数 = self._绘制计数动画图层(渲染器, 帧输入)
        return int(notes数), int(判定区数), int(特效数), int(计数动画数)

    def _绘制计数动画图层(self, 渲染器, 帧输入: Dict[str, Any]) -> int:
        图层 = 帧输入.get("计数动画图层")
        矩形 = 帧输入.get("计数动画矩形")
        if not isinstance(图层, pygame.Surface) or not isinstance(矩形, pygame.Rect):
            return 0
        if 矩形.w <= 0 or 矩形.h <= 0:
            return 0
        纹理 = self._建临时纹理(渲染器, 图层)
        if 纹理 is None:
            return 0
        return int(
            bool(
                self._绘制纹理矩形(
                    纹理,
                    图层,
                    pygame.Rect(int(矩形.x), int(矩形.y), int(矩形.w), int(矩形.h)),
                    None,
                    alpha=255,
                    blend_mode=1,
                )
            )
        )

    def _绘制Stage组(self, 渲染器, 帧输入: Dict[str, Any]):
        Stage数据 = 帧输入.get("Stage数据")
        if not isinstance(Stage数据, dict) or not Stage数据:
            return
        背景 = Stage数据.get("背景")
        if isinstance(背景, dict):
            self._绘制GPU图片控件(渲染器, 背景)
        频谱 = Stage数据.get("频谱")
        if isinstance(频谱, dict):
            self._绘制GPU频谱数据(渲染器, 频谱.get("绘制数据"))
    def _绘制HUD组(self, 渲染器, 帧输入: Dict[str, Any]):
        HUD数据 = 帧输入.get("HUD数据")
        if not isinstance(HUD数据, dict) or not HUD数据:
            return
        图层列表 = list(HUD数据.get("图层列表", []) or [])
        图层列表.sort(key=lambda 项: int(项.get("z", 0)) if isinstance(项, dict) else 0)
        for 项 in 图层列表:
            if not isinstance(项, dict):
                continue
            类型 = str(项.get("类型") or "图层").strip()
            if 类型 == "图片":
                数据 = 项.get("数据")
                if isinstance(数据, dict):
                    self._绘制GPU图片控件(渲染器, 数据)
                continue
            if 类型 == "频谱":
                数据 = 项.get("数据")
                if isinstance(数据, dict):
                    self._绘制GPU频谱数据(渲染器, 数据.get("绘制数据"))
                continue
            图层 = 项.get("图层")
            矩形 = 项.get("rect")
            if not isinstance(图层, pygame.Surface) or not isinstance(矩形, pygame.Rect):
                continue
            if 矩形.w <= 0 or 矩形.h <= 0:
                continue
            if bool(项.get("缓存纹理", False)):
                纹理 = self._取纹理(渲染器, 图层)
            else:
                纹理 = self._建临时纹理(渲染器, 图层)
            if 纹理 is None:
                continue
            self._绘制纹理矩形(
                纹理,
                图层,
                pygame.Rect(int(矩形.x), int(矩形.y), int(矩形.w), int(矩形.h)),
                None,
                alpha=int(max(0, min(255, int(项.get("alpha", 255) or 255)))),
                blend_mode=int(max(1, min(2, int(项.get("blend_mode", 1) or 1)))),
            )

    def _绘制GPU图片控件(self, 渲染器, 数据: Dict[str, Any]) -> bool:
        图 = 数据.get("图")
        目标矩形 = 数据.get("rect")
        if not isinstance(图, pygame.Surface) or not isinstance(目标矩形, pygame.Rect):
            return False
        纹理 = self._取纹理(渲染器, 图)
        if 纹理 is None:
            return False
        alpha = int(max(0, min(255, int(数据.get("alpha", 255) or 255))))
        blend_mode = 1
        if str(数据.get("混合", "") or "").lower() == "add":
            blend_mode = 2
        等比 = str(数据.get("等比", "stretch") or "stretch").lower()
        角度 = float(数据.get("角度", 0.0) or 0.0)
        目标 = pygame.Rect(目标矩形)
        if 等比 == "contain":
            原宽 = max(1, int(图.get_width()))
            原高 = max(1, int(图.get_height()))
            比例 = min(float(目标.w) / float(原宽), float(目标.h) / float(原高))
            绘制宽 = int(max(2, round(float(原宽) * 比例)))
            绘制高 = int(max(2, round(float(原高) * 比例)))
            目标 = pygame.Rect(
                int(目标.centerx - 绘制宽 // 2),
                int(目标.centery - 绘制高 // 2),
                int(绘制宽),
                int(绘制高),
            )
        if abs(角度) > 0.001:
            self._设置纹理透明与颜色(纹理, alpha=alpha, blend_mode=blend_mode)
            try:
                纹理.draw(
                    dstrect=(int(目标.x), int(目标.y), int(目标.w), int(目标.h)),
                    angle=float(角度),
                    origin=(float(目标.w) * 0.5, float(目标.h) * 0.5),
                )
                return True
            except Exception:
                return False
        return self._绘制纹理矩形(
            纹理,
            图,
            目标,
            None,
            alpha=alpha,
            blend_mode=blend_mode,
        )

    @staticmethod
    def _设置渲染器画笔(渲染器, 颜色: Tuple[int, int, int], alpha: int = 255):
        if 渲染器 is None:
            return
        try:
            渲染器.draw_color = (
                int(max(0, min(255, 颜色[0]))),
                int(max(0, min(255, 颜色[1]))),
                int(max(0, min(255, 颜色[2]))),
                int(max(0, min(255, alpha))),
            )
        except Exception:
            pass
        try:
            渲染器.draw_blend_mode = 1
        except Exception:
            pass

    def _绘制GPU频谱数据(self, 渲染器, 数据: Any):
        if not isinstance(数据, dict):
            return
        for 线条 in list(数据.get("线条", []) or []):
            if isinstance(线条, tuple) and len(线条) >= 9:
                x1, y1, x2, y2, r, g, b, 宽度, _抗锯齿 = 线条[:9]
                颜色 = (int(r), int(g), int(b))
            elif isinstance(线条, dict):
                起点 = tuple(线条.get("起点", (0.0, 0.0)) or (0.0, 0.0))
                终点 = tuple(线条.get("终点", (0.0, 0.0)) or (0.0, 0.0))
                x1 = int(round(float(起点[0])))
                y1 = int(round(float(起点[1])))
                x2 = int(round(float(终点[0])))
                y2 = int(round(float(终点[1])))
                颜色 = tuple(int(v) for v in tuple(线条.get("颜色", (255, 255, 255)) or (255, 255, 255))[:3])
                宽度 = int(max(1, int(线条.get("宽度", 1) or 1)))
            else:
                continue
            self._设置渲染器画笔(渲染器, 颜色, 255)
            try:
                渲染器.draw_line((int(x1), int(y1)), (int(x2), int(y2)))
                for 偏移 in range(1, 宽度):
                    渲染器.draw_line(
                        (int(x1 + 偏移 * 0.4), int(y1 + 偏移 * 0.4)),
                        (int(x2 + 偏移 * 0.4), int(y2 + 偏移 * 0.4)),
                    )
            except Exception:
                pass

        for 轮廓 in list(数据.get("轮廓", []) or []):
            if not isinstance(轮廓, dict):
                continue
            点列 = list(轮廓.get("点列", []) or [])
            if len(点列) < 2:
                continue
            颜色 = tuple(int(v) for v in tuple(轮廓.get("颜色", (255, 255, 255)) or (255, 255, 255))[:3])
            闭合 = bool(轮廓.get("闭合", True))
            self._设置渲染器画笔(渲染器, 颜色, 255)
            try:
                for 索引 in range(len(点列) - 1):
                    起点 = 点列[索引]
                    终点 = 点列[索引 + 1]
                    渲染器.draw_line(
                        (int(round(float(起点[0]))), int(round(float(起点[1])))),
                        (int(round(float(终点[0]))), int(round(float(终点[1])))),
                    )
                if 闭合:
                    起点 = 点列[-1]
                    终点 = 点列[0]
                    渲染器.draw_line(
                        (int(round(float(起点[0]))), int(round(float(起点[1])))),
                        (int(round(float(终点[0]))), int(round(float(终点[1])))),
                    )
            except Exception:
                pass

        for 圆 in list(数据.get("圆", []) or []):
            if not isinstance(圆, dict):
                continue
            中心 = tuple(int(v) for v in tuple(圆.get("中心", (0, 0)) or (0, 0))[:2])
            半径 = int(max(1, int(圆.get("半径", 1) or 1)))
            宽度 = int(max(1, int(圆.get("宽度", 1) or 1)))
            颜色 = tuple(int(v) for v in tuple(圆.get("颜色", (255, 255, 255)) or (255, 255, 255))[:3])
            self._设置渲染器画笔(渲染器, 颜色, 255)
            段数 = int(max(24, min(144, 半径 * 2)))
            点列 = []
            for 索引 in range(段数):
                角 = (float(索引) / float(段数)) * math.tau
                点列.append(
                    (
                        float(中心[0]) + math.cos(角) * float(半径),
                        float(中心[1]) + math.sin(角) * float(半径),
                    )
                )
            for 厚度偏移 in range(宽度):
                try:
                    for 索引 in range(len(点列)):
                        起点 = 点列[索引]
                        终点 = 点列[(索引 + 1) % len(点列)]
                        渲染器.draw_line(
                            (
                                int(round(float(起点[0]) + 厚度偏移 * 0.35)),
                                int(round(float(起点[1]) + 厚度偏移 * 0.35)),
                            ),
                            (
                                int(round(float(终点[0]) + 厚度偏移 * 0.35)),
                                int(round(float(终点[1]) + 厚度偏移 * 0.35)),
                            ),
                        )
                except Exception:
                    pass

    def _取皮肤帧(self, 软件渲染器, 分包名: str, 名称: str) -> Optional[pygame.Surface]:
        if 软件渲染器 is None:
            return None
        皮肤包 = getattr(软件渲染器, "_皮肤包", None)
        图集 = getattr(皮肤包, str(分包名), None) if 皮肤包 is not None else None
        取图 = getattr(图集, "取", None)
        if not callable(取图):
            return None
        try:
            return 取图(str(名称))
        except Exception:
            return None

    def _取缩放图(
        self,
        软件渲染器,
        缓存键: str,
        原图: Optional[pygame.Surface],
        目标宽: int,
    ) -> Optional[pygame.Surface]:
        if 原图 is None:
            return None
        目标宽 = int(max(2, 目标宽))
        取图 = getattr(软件渲染器, "_取缩放图", None)
        if callable(取图):
            try:
                return 取图(str(缓存键), 原图, int(目标宽))
            except Exception:
                pass
        try:
            比例 = float(目标宽) / float(max(1, 原图.get_width()))
            目标高 = int(max(2, round(float(原图.get_height()) * 比例)))
            return pygame.transform.smoothscale(原图, (int(目标宽), int(目标高))).convert_alpha()
        except Exception:
            return 原图

    def _取按高缩放图(
        self,
        软件渲染器,
        缓存键: str,
        原图: Optional[pygame.Surface],
        目标高: int,
    ) -> Optional[pygame.Surface]:
        if 原图 is None:
            return None
        目标高 = int(max(2, 目标高))
        取图 = getattr(软件渲染器, "_取按高缩放图", None)
        if callable(取图):
            try:
                return 取图(str(缓存键), 原图, int(目标高))
            except Exception:
                pass
        try:
            比例 = float(目标高) / float(max(1, 原图.get_height()))
            目标宽 = int(max(2, round(float(原图.get_width()) * 比例)))
            return pygame.transform.smoothscale(原图, (int(目标宽), int(目标高))).convert_alpha()
        except Exception:
            return 原图

    def _取灰度图(self, 图: pygame.Surface) -> pygame.Surface:
        键 = (int(id(图)), int(图.get_width()), int(图.get_height()))
        旧图 = self._灰度图缓存表.get(键)
        if isinstance(旧图, pygame.Surface):
            return 旧图
        try:
            新图 = pygame.transform.grayscale(图).convert_alpha()
        except Exception:
            新图 = 图
        self._灰度图缓存表[键] = 新图
        if len(self._灰度图缓存表) > 512:
            for 旧键 in list(self._灰度图缓存表.keys())[:-256]:
                self._灰度图缓存表.pop(旧键, None)
        return 新图

    def _取纹理(self, 渲染器, 图: pygame.Surface):
        if _sdl2_video is None or 图 is None:
            return None
        键 = (int(id(渲染器)), int(id(图)), int(图.get_width()), int(图.get_height()))
        旧纹理 = self._纹理缓存表.get(键)
        if 旧纹理 is not None:
            return 旧纹理
        try:
            新纹理 = _sdl2_video.Texture.from_surface(渲染器, 图)
        except Exception:
            return None
        self._纹理缓存表[键] = 新纹理
        if len(self._纹理缓存表) > 1024:
            for 旧键 in list(self._纹理缓存表.keys())[:-512]:
                self._纹理缓存表.pop(旧键, None)
        return 新纹理

    def _建临时纹理(self, 渲染器, 图: pygame.Surface):
        if _sdl2_video is None or 图 is None:
            return None
        try:
            return _sdl2_video.Texture.from_surface(渲染器, 图)
        except Exception:
            return None

    def _取贴图条目(
        self,
        渲染器,
        软件渲染器,
        缓存键: str,
        原图: Optional[pygame.Surface],
        目标宽: int,
        使用灰度: bool,
    ) -> Tuple[Optional[Any], Optional[pygame.Surface]]:
        图 = self._取缩放图(软件渲染器, 缓存键, 原图, 目标宽)
        if 图 is None:
            return None, None
        if bool(使用灰度):
            图 = self._取灰度图(图)
        return self._取纹理(渲染器, 图), 图

    @staticmethod
    def _设置纹理透明与颜色(
        纹理,
        alpha: int = 255,
        blend_mode: Optional[int] = 1,
    ):
        if 纹理 is None:
            return
        try:
            纹理.alpha = int(max(0, min(255, alpha)))
        except Exception:
            pass
        if blend_mode is not None:
            try:
                纹理.blend_mode = int(blend_mode)
            except Exception:
                pass
        try:
            纹理.color = (255, 255, 255)
        except Exception:
            pass

    def _绘制纹理中心(
        self,
        纹理,
        图: pygame.Surface,
        x中心: float,
        y中心: float,
        flip_x: bool = False,
        angle: float = 0.0,
        alpha: int = 255,
        blend_mode: Optional[int] = 1,
    ) -> bool:
        if 纹理 is None or 图 is None:
            return False
        self._设置纹理透明与颜色(纹理, alpha=alpha, blend_mode=blend_mode)
        try:
            纹理.draw(
                dstrect=(
                    float(x中心) - float(图.get_width()) * 0.5,
                    float(y中心) - float(图.get_height()) * 0.5,
                    float(图.get_width()),
                    float(图.get_height()),
                ),
                angle=float(angle),
                origin=(float(图.get_width()) * 0.5, float(图.get_height()) * 0.5),
                flip_x=bool(flip_x),
            )
            return True
        except Exception:
            try:
                纹理.draw(
                    dstrect=(
                        int(round(float(x中心) - float(图.get_width()) * 0.5)),
                        int(round(float(y中心) - float(图.get_height()) * 0.5)),
                        int(图.get_width()),
                        int(图.get_height()),
                    ),
                    angle=float(angle),
                    origin=(float(图.get_width()) * 0.5, float(图.get_height()) * 0.5),
                    flip_x=bool(flip_x),
                )
                return True
            except Exception:
                return False

    def _绘制纹理矩形数据(
        self,
        纹理,
        图: pygame.Surface,
        x: float,
        y: float,
        w: float,
        h: float,
        源矩形: Optional[pygame.Rect] = None,
        flip_x: bool = False,
        alpha: int = 255,
        blend_mode: Optional[int] = 1,
    ) -> bool:
        if 纹理 is None or 图 is None:
            return False
        self._设置纹理透明与颜色(纹理, alpha=alpha, blend_mode=blend_mode)
        try:
            if isinstance(源矩形, pygame.Rect):
                纹理.draw(
                    srcrect=(
                        int(源矩形.x),
                        int(源矩形.y),
                        int(源矩形.w),
                        int(源矩形.h),
                    ),
                    dstrect=(float(x), float(y), float(w), float(h)),
                    flip_x=bool(flip_x),
                )
            else:
                纹理.draw(
                    dstrect=(float(x), float(y), float(w), float(h)),
                    flip_x=bool(flip_x),
                )
            return True
        except Exception:
            try:
                if isinstance(源矩形, pygame.Rect):
                    纹理.draw(
                        srcrect=(
                            int(源矩形.x),
                            int(源矩形.y),
                            int(源矩形.w),
                            int(源矩形.h),
                        ),
                        dstrect=(
                            int(round(float(x))),
                            int(round(float(y))),
                            int(round(float(w))),
                            int(round(float(h))),
                        ),
                        flip_x=bool(flip_x),
                    )
                else:
                    纹理.draw(
                        dstrect=(
                            int(round(float(x))),
                            int(round(float(y))),
                            int(round(float(w))),
                            int(round(float(h))),
                        ),
                        flip_x=bool(flip_x),
                    )
                return True
            except Exception:
                return False

    def _绘制纹理矩形(
        self,
        纹理,
        图: pygame.Surface,
        目标矩形: pygame.Rect,
        源矩形: Optional[pygame.Rect] = None,
        flip_x: bool = False,
        alpha: int = 255,
        blend_mode: Optional[int] = 1,
    ) -> bool:
        if 纹理 is None or 图 is None or not isinstance(目标矩形, pygame.Rect):
            return False
        return self._绘制纹理矩形数据(
            纹理,
            图,
            float(目标矩形.x),
            float(目标矩形.y),
            float(目标矩形.w),
            float(目标矩形.h),
            源矩形=源矩形,
            flip_x=flip_x,
            alpha=alpha,
            blend_mode=blend_mode,
        )

    def _绘制音符组(self, 渲染器, 帧输入: Dict[str, Any]) -> int:
        软件渲染器 = 帧输入.get("软件渲染器")
        事件缓存 = self._取事件缓存(帧输入.get("事件列表", []) or [])
        事件列表 = 事件缓存.get("事件列表", []) or []
        if not 事件列表:
            return 0

        当前秒 = _取浮点(帧输入.get("当前谱面秒", 0.0), 0.0)
        视觉偏移秒 = _取浮点(帧输入.get("谱面视觉偏移秒", 0.0), 0.0)
        视觉偏移绝对值 = abs(float(视觉偏移秒))
        秒转beat函数 = 帧输入.get("BPM变速秒转beat函数")
        BPM变速像素每拍 = max(
            0.0, _取浮点(帧输入.get("BPM变速像素每拍", 0.0), 0.0)
        )
        BPM变速开启 = bool(callable(秒转beat函数)) and float(BPM变速像素每拍) > 0.0
        BPM变速合成脉冲开启 = bool(
            帧输入.get("BPM变速合成脉冲开启", False)
        )

        def _变速显示beat(beat值: float) -> float:
            结果 = float(beat值)
            if not bool(BPM变速合成脉冲开启):
                return 结果
            整拍 = math.floor(float(结果))
            相位 = float(结果) - float(整拍)
            加速区间 = 0.12
            加速倍率 = 4.0
            减速倍率 = (1.0 - 加速区间 * 加速倍率) / max(
                0.001, 1.0 - 加速区间
            )
            if float(相位) < float(加速区间):
                return float(整拍) + float(相位) * float(加速倍率)
            return float(整拍) + float(加速区间) * float(加速倍率) + (
                float(相位) - float(加速区间)
            ) * float(减速倍率)
        判定线y = _取整数(帧输入.get("判定线y", 0), 0)
        轨道中心列表 = list(帧输入.get("轨道中心列表", []) or [])[:5]
        判定线y列表 = list(帧输入.get("判定线y列表", []) or [])[:5]
        while len(判定线y列表) < len(轨道中心列表):
            判定线y列表.append(int(判定线y))
        底部y = _取整数(帧输入.get("底部y", 0), 0)
        速度 = max(60.0, _取浮点(帧输入.get("滚动速度px每秒", 60.0), 60.0))
        箭头宽_tap = max(18, _取整数(帧输入.get("箭头目标宽", 32), 32))
        箭头宽_hold = max(16, _取整数(帧输入.get("hold目标宽", 箭头宽_tap), 箭头宽_tap))
        隐藏模式 = str(帧输入.get("隐藏模式", "关闭") or "关闭")
        轨迹模式 = str(帧输入.get("轨迹模式", "正常") or "正常")
        使用灰度 = bool(帧输入.get("Note层灰度", False))
        if "全隐" in 隐藏模式:
            return 0

        半隐模式 = bool("半隐" in 隐藏模式)
        半隐y阈值 = _取整数(帧输入.get("半隐y阈值", 0), 0)
        提前秒 = max(0.5, _取浮点(帧输入.get("提前秒", 1.0), 1.0))
        上边界 = _取整数(帧输入.get("上边界", -max(40, 箭头宽_tap * 2)), -max(40, 箭头宽_tap * 2))
        下边界 = _取整数(帧输入.get("下边界", 底部y + max(40, 箭头宽_tap * 2)), 底部y + max(40, 箭头宽_tap * 2))
        渲染秒 = self._取渲染秒(软件渲染器, float(当前秒))
        当前可视beat = 0.0
        渲染beat = 0.0
        可视前beat = 0.0
        可视后beat = 0.0
        if BPM变速开启 and callable(秒转beat函数) and BPM变速像素每拍 > 0.0:
            try:
                当前可视beat = float(
                    _变速显示beat(
                        float(秒转beat函数(float(当前秒) - float(视觉偏移秒)))
                    )
                )
                渲染beat = float(
                    _变速显示beat(
                        float(秒转beat函数(float(渲染秒) - float(视觉偏移秒)))
                    )
                )
                可视前beat = float(max(1, (底部y - 判定线y))) / float(BPM变速像素每拍)
                可视后beat = float(
                    max(1, max(0, 判定线y - 上边界))
                ) / float(BPM变速像素每拍)
            except Exception:
                BPM变速开启 = False
        self._同步命中可视状态(
            软件渲染器=软件渲染器,
            事件列表=事件列表,
            当前秒=float(当前秒),
            渲染秒=float(渲染秒),
            视觉偏移秒=float(视觉偏移秒),
            BPM变速开启=bool(BPM变速开启),
            BPM变速合成脉冲开启=bool(BPM变速合成脉冲开启),
            当前可视beat=float(当前可视beat),
            渲染beat=float(渲染beat),
            BPM变速像素每拍=float(BPM变速像素每拍),
            判定线y列表=判定线y列表,
            速度=float(速度),
            提前秒=float(提前秒),
            上边界=int(上边界),
            下边界=int(下边界),
            半隐模式=bool(半隐模式),
            半隐y阈值=int(半隐y阈值),
        )
        if BPM变速开启:
            开始beat列表 = list(事件缓存.get("开始beat列表", []) or [])
            前缀最大结束beat = list(事件缓存.get("前缀最大结束beat", []) or [])
            起始阈值beat = float(当前可视beat - 可视后beat - 1.0)
            起始索引 = bisect.bisect_left(前缀最大结束beat, 起始阈值beat)
            if 起始索引 < 0:
                起始索引 = 0
        else:
            消失后秒 = max(0.8, float(max(0, 判定线y) + 箭头宽_tap * 2) / float(max(1.0, 速度)) + 0.18)
            起始阈值秒 = 当前秒 - float(消失后秒) - float(视觉偏移绝对值)
            开始秒列表 = list(事件缓存.get("开始秒列表", []) or [])
            前缀最大结束秒 = list(事件缓存.get("前缀最大结束秒", []) or [])
            起始索引 = bisect.bisect_left(前缀最大结束秒, 起始阈值秒)
            if 起始索引 < 0:
                起始索引 = 0

        绘制数 = 0
        for 索引 in range(int(起始索引), len(事件列表)):
            事件 = 事件列表[索引]
            开始秒 = _取浮点(getattr(事件, "开始秒", 0.0), 0.0)
            结束秒 = _取浮点(getattr(事件, "结束秒", 开始秒), 开始秒)
            开始beat = _取浮点(getattr(事件, "开始beat", 0.0), 0.0)
            结束beat = _取浮点(getattr(事件, "结束beat", 开始beat), 开始beat)
            if 结束秒 < 开始秒:
                结束秒 = 开始秒
            if 结束beat < 开始beat:
                结束beat = 开始beat
            显示开始秒 = float(开始秒) + float(视觉偏移秒)
            if BPM变速开启:
                显示开始beat = float(_变速显示beat(float(开始beat)))
                显示结束beat = float(_变速显示beat(float(结束beat)))
                if float(显示开始beat) > float(当前可视beat + 可视前beat + 1.0):
                    break
            else:
                if 显示开始秒 > 当前秒 + 提前秒:
                    break
            轨道 = _取整数(getattr(事件, "轨道序号", -1), -1)
            if 轨道 < 0 or 轨道 >= len(轨道中心列表):
                continue
            显示结束秒 = float(结束秒) + float(视觉偏移秒)

            x中心 = float(_取整数(轨道中心列表[轨道], 0))
            当前轨判定y = float(_取整数(判定线y列表[轨道], 判定线y))
            if BPM变速开启:
                y开始 = float(当前轨判定y) + (
                    float(显示开始beat) - float(渲染beat)
                ) * float(BPM变速像素每拍)
                y结束 = float(当前轨判定y) + (
                    float(显示结束beat) - float(渲染beat)
                ) * float(BPM变速像素每拍)
            else:
                y开始 = float(当前轨判定y) + (显示开始秒 - 渲染秒) * 速度
                y结束 = float(当前轨判定y) + (显示结束秒 - 渲染秒) * 速度

            类型 = str(getattr(事件, "类型", "tap") or "tap")
            if str(类型) == "hold":
                是否命中hold = self._是否命中长按(
                    软件渲染器, int(轨道), float(开始秒), float(结束秒), float(当前秒)
                )
                if bool(是否命中hold) and float(当前秒) >= float(显示结束秒):
                    continue
                绘制数 += self._绘制长按(
                    渲染器,
                    软件渲染器,
                    int(轨道),
                    float(x中心),
                    float(y开始),
                    float(y结束),
                    int(箭头宽_hold),
                    float(当前轨判定y),
                    int(上边界),
                    int(下边界),
                    bool(半隐模式),
                    int(半隐y阈值),
                    使用灰度,
                    bool(是否命中hold),
                    float(当前秒),
                    float(显示结束秒),
                )
                continue

            if float(y开始) < float(上边界) or float(y开始) > float(下边界):
                continue
            if 半隐模式 and float(y开始) > float(半隐y阈值):
                continue
            if self._tap已命中(
                软件渲染器,
                int(轨道),
                float(开始秒),
                float(y开始),
                float(当前轨判定y),
                float(当前秒),
            ):
                continue

            x绘制 = float(x中心)
            旋转角度 = 0.0
            if "摇摆" in 轨迹模式:
                主振幅 = max(16.0, float(箭头宽_tap) * 0.52)
                主相位 = (
                    float(渲染秒) * (math.pi * 2.0) * 2.05
                    + float(显示开始秒) * 0.55
                    + float(轨道) * 0.72
                )
                次相位 = float(主相位) * 0.52 + float(轨道) * 0.35
                x绘制 = float(x中心) + math.sin(主相位) * 主振幅 + math.sin(次相位) * (主振幅 * 0.22)
            elif "旋转" in 轨迹模式:
                旋转角度 = float(
                    (
                        渲染秒 * 360.0 * 1.25
                        + float(显示开始秒) * 140.0
                        + float(轨道) * 35.0
                    )
                    % 360.0
                )

            if self._绘制点按(
                渲染器,
                软件渲染器,
                int(轨道),
                float(x绘制),
                float(y开始),
                int(箭头宽_tap),
                使用灰度,
                float(旋转角度),
            ):
                绘制数 += 1
        return 绘制数

    def _取渲染秒(self, 软件渲染器, 当前秒: float) -> float:
        if 软件渲染器 is None:
            return float(当前秒)
        取渲染平滑谱面秒 = getattr(软件渲染器, "_取渲染平滑谱面秒", None)
        if callable(取渲染平滑谱面秒):
            try:
                return float(取渲染平滑谱面秒(float(当前秒)))
            except Exception:
                return float(当前秒)
        return float(当前秒)

    def _同步命中可视状态(
        self,
        软件渲染器,
        事件列表: List[Any],
        当前秒: float,
        渲染秒: float,
        视觉偏移秒: float,
        BPM变速开启: bool,
        BPM变速合成脉冲开启: bool,
        当前可视beat: float,
        渲染beat: float,
        BPM变速像素每拍: float,
        判定线y列表: List[int],
        速度: float,
        提前秒: float,
        上边界: int,
        下边界: int,
        半隐模式: bool,
        半隐y阈值: int,
    ):
        if 软件渲染器 is None:
            return
        确保命中映射缓存 = getattr(软件渲染器, "_确保命中映射缓存", None)
        if callable(确保命中映射缓存):
            try:
                确保命中映射缓存()
            except Exception:
                return
        try:
            当前毫秒 = int(round(float(当前秒) * 1000.0))
        except Exception:
            当前毫秒 = 0

        try:
            按下数组 = pygame.key.get_pressed()
        except Exception:
            按下数组 = None
        轨道到按键列表 = (
            dict(getattr(软件渲染器, "_按键反馈轨道到按键列表", {}) or {})
            if isinstance(getattr(软件渲染器, "_按键反馈轨道到按键列表", None), dict)
            else {}
        )
        if not 轨道到按键列表:
            轨道到按键列表 = {
                0: [f"key:{int(pygame.K_1)}", f"key:{int(pygame.K_KP1)}"],
                1: [f"key:{int(pygame.K_7)}", f"key:{int(pygame.K_KP7)}"],
                2: [f"key:{int(pygame.K_5)}", f"key:{int(pygame.K_KP5)}"],
                3: [f"key:{int(pygame.K_9)}", f"key:{int(pygame.K_KP9)}"],
                4: [f"key:{int(pygame.K_3)}", f"key:{int(pygame.K_KP3)}"],
            }

        def _轨道是否按下(轨道: int) -> bool:
            for 键 in 轨道到按键列表.get(int(轨道), []):
                if is_binding_pressed(键, 按下数组):
                    return True
            return False

        def _变速显示beat(beat值: float) -> float:
            结果 = float(beat值)
            if not bool(BPM变速合成脉冲开启):
                return 结果
            整拍 = math.floor(float(结果))
            相位 = float(结果) - float(整拍)
            加速区间 = 0.12
            加速倍率 = 4.0
            减速倍率 = (1.0 - 加速区间 * 加速倍率) / max(
                0.001, 1.0 - 加速区间
            )
            if float(相位) < float(加速区间):
                return float(整拍) + float(相位) * float(加速倍率)
            return float(整拍) + float(加速区间) * float(加速倍率) + (
                float(相位) - float(加速区间)
            ) * float(减速倍率)

        命中窗毫秒 = int(round(float(getattr(软件渲染器, "_命中匹配窗秒", 0.12) or 0.12) * 1000.0))
        命中窗毫秒 = max(40, min(260, int(命中窗毫秒)))
        已命中tap过期表毫秒 = getattr(软件渲染器, "_已命中tap过期表毫秒", [])
        待命中队列毫秒 = getattr(软件渲染器, "_待命中队列毫秒", [])
        命中hold开始谱面秒 = getattr(软件渲染器, "_命中hold开始谱面秒", [])
        命中hold结束谱面秒 = getattr(软件渲染器, "_命中hold结束谱面秒", [])
        击中特效开始谱面秒 = getattr(软件渲染器, "_击中特效开始谱面秒", [])
        击中特效循环到谱面秒 = getattr(软件渲染器, "_击中特效循环到谱面秒", [])
        if not isinstance(已命中tap过期表毫秒, list) or not isinstance(待命中队列毫秒, list):
            return
        if (
            not isinstance(命中hold开始谱面秒, list)
            or not isinstance(命中hold结束谱面秒, list)
            or not isinstance(击中特效开始谱面秒, list)
            or not isinstance(击中特效循环到谱面秒, list)
        ):
            return

        for 轨 in range(min(5, len(已命中tap过期表毫秒))):
            表 = 已命中tap过期表毫秒[轨]
            if isinstance(表, dict) and 表:
                for 键 in list(表.keys()):
                    try:
                        if 当前毫秒 > int(表.get(键, -1)):
                            del 表[键]
                    except Exception:
                        try:
                            del 表[键]
                        except Exception:
                            pass
            if 轨 < len(待命中队列毫秒):
                队列 = 待命中队列毫秒[轨]
                if isinstance(队列, list) and 队列:
                    丢弃阈值 = int(当前毫秒 - 2000)
                    while 队列 and int(队列[0]) < 丢弃阈值:
                        队列.pop(0)

        取事件渲染缓存 = getattr(软件渲染器, "_取事件渲染缓存", None)
        if callable(取事件渲染缓存):
            try:
                缓存 = dict(取事件渲染缓存(事件列表) or {})
                缓存事件列表 = list(缓存.get("事件", []) or [])
            except Exception:
                缓存事件列表 = []
        else:
            缓存事件列表 = []
            for 事件 in list(事件列表 or []):
                try:
                    st = float(getattr(事件, "开始秒"))
                    ed = float(getattr(事件, "结束秒"))
                    st_beat = float(getattr(事件, "开始beat"))
                    ed_beat = float(getattr(事件, "结束beat"))
                    轨道 = int(getattr(事件, "轨道序号"))
                    类型 = str(getattr(事件, "类型"))
                except Exception:
                    continue
                缓存事件列表.append(
                    (
                        st,
                        ed,
                        st_beat,
                        ed_beat,
                        轨道,
                        类型,
                        int(round(st * 1000.0)),
                    )
                )
            缓存事件列表.sort(key=lambda 项: (float(项[0]), int(项[4]), float(项[1])))

        活跃hold轨道: set[int] = set()
        try:
            软件渲染器._hold当前按下中 = [False] * 5
        except Exception:
            pass

        可视后beat = 0.0
        可视前beat = 0.0
        if bool(BPM变速开启) and float(BPM变速像素每拍) > 0.0:
            try:
                基准判定y = int(
                    判定线y列表[2]
                    if len(判定线y列表) >= 3
                    else (
                        sum(int(v) for v in 判定线y列表)
                        / float(max(1, len(判定线y列表)))
                    )
                )
            except Exception:
                基准判定y = 0
            可视前beat = float(max(1, 下边界 - 基准判定y)) / float(
                BPM变速像素每拍
            )
            可视后beat = float(max(1, 基准判定y - 上边界)) / float(
                BPM变速像素每拍
            )

        for 条目 in 缓存事件列表:
            try:
                st, ed, st_beat, ed_beat, 轨道, 类型, st毫秒 = 条目
            except Exception:
                continue
            显示开始秒 = float(st) + float(视觉偏移秒)
            显示结束秒 = float(ed) + float(视觉偏移秒)
            if bool(BPM变速开启):
                显示开始beat = float(_变速显示beat(float(st_beat)))
                显示结束beat = float(_变速显示beat(float(ed_beat)))
                if float(显示开始beat) > float(当前可视beat + 可视前beat + 1.0):
                    break
                if float(显示结束beat) < float(当前可视beat - 可视后beat - 1.0):
                    continue
            else:
                if float(显示开始秒) > float(当前秒) + float(提前秒):
                    break
                if (
                    float(显示开始秒) < float(当前秒) - 2.5 - abs(float(视觉偏移秒))
                    and float(显示结束秒) < float(当前秒) - 2.5 - abs(float(视觉偏移秒))
                ):
                    continue
            轨道 = int(轨道)
            if 轨道 < 0 or 轨道 >= len(判定线y列表):
                continue
            当前轨判定y = int(判定线y列表[轨道])
            if bool(BPM变速开启):
                y开始 = float(当前轨判定y) + (
                    float(显示开始beat) - float(渲染beat)
                ) * float(BPM变速像素每拍)
            else:
                y开始 = float(当前轨判定y) + (
                    float(显示开始秒) - float(渲染秒)
                ) * float(速度)

            if abs(float(ed) - float(st)) < 1e-6 or str(类型) == "tap":
                if y开始 < float(上边界) or y开始 > float(下边界):
                    continue
                if 轨道 >= len(已命中tap过期表毫秒):
                    continue
                已命中表 = 已命中tap过期表毫秒[轨道]
                if not isinstance(已命中表, dict):
                    continue
                命中匹配 = False
                try:
                    过期 = int(已命中表.get(int(st毫秒), -1))
                    if 过期 > 0 and 当前毫秒 <= 过期:
                        命中匹配 = True
                except Exception:
                    命中匹配 = False
                if (not 命中匹配) and 轨道 < len(待命中队列毫秒):
                    队列 = 待命中队列毫秒[轨道]
                    if isinstance(队列, list):
                        左界 = int(int(st毫秒) - int(命中窗毫秒))
                        while 队列 and int(队列[0]) < 左界:
                            队列.pop(0)
                        if 队列:
                            hit_ms = int(队列[0])
                            if abs(int(hit_ms) - int(st毫秒)) <= int(命中窗毫秒):
                                队列.pop(0)
                                命中匹配 = True
                                已命中表[int(st毫秒)] = int(
                                    max(int(st毫秒) + 1000, int(当前毫秒) + 650)
                                )
                continue

            if bool(BPM变速开启):
                y结束 = float(当前轨判定y) + (
                    float(显示结束beat) - float(渲染beat)
                ) * float(BPM变速像素每拍)
            else:
                y结束 = float(当前轨判定y) + (
                    float(显示结束秒) - float(渲染秒)
                ) * float(速度)
            seg_top = float(min(y开始, y结束))
            seg_bot = float(max(y开始, y结束))
            if seg_bot < float(上边界) or seg_top > float(下边界):
                continue

            是否命中hold = False
            if 轨道 < len(命中hold开始谱面秒) and 轨道 < len(命中hold结束谱面秒):
                命中开始 = float(命中hold开始谱面秒[轨道])
                命中结束 = float(命中hold结束谱面秒[轨道])
                if 命中结束 > -1.0 and (float(当前秒) <= 命中结束 + 1.2):
                    if abs(float(st) - 命中开始) <= max(
                        0.08,
                        float(getattr(软件渲染器, "_命中匹配窗秒", 0.12) or 0.12) * 2.0,
                    ):
                        是否命中hold = True
            if (not 是否命中hold) and 轨道 < len(待命中队列毫秒):
                队列 = 待命中队列毫秒[轨道]
                if isinstance(队列, list):
                    左界 = int(int(st毫秒) - int(命中窗毫秒))
                    while 队列 and int(队列[0]) < 左界:
                        队列.pop(0)
                    if 队列:
                        hit_ms = int(队列[0])
                        if abs(int(hit_ms) - int(st毫秒)) <= int(命中窗毫秒):
                            队列.pop(0)
                            if 轨道 < len(命中hold开始谱面秒):
                                命中hold开始谱面秒[轨道] = float(st)
                            if 轨道 < len(命中hold结束谱面秒):
                                命中hold结束谱面秒[轨道] = float(ed)
                            if 轨道 < len(击中特效开始谱面秒):
                                击中特效开始谱面秒[轨道] = float(st)
                            if 轨道 < len(击中特效循环到谱面秒):
                                击中特效循环到谱面秒[轨道] = float(ed)
                            是否命中hold = True
            if bool(是否命中hold) and (
                float(显示开始秒) <= float(当前秒) <= float(显示结束秒)
            ):
                活跃hold轨道.add(int(轨道))
                try:
                    软件渲染器._hold当前按下中[int(轨道)] = bool(_轨道是否按下(int(轨道)))
                    软件渲染器._hold松手系统秒[int(轨道)] = None
                except Exception:
                    pass

        for i in range(5):
            if i not in 活跃hold轨道:
                try:
                    软件渲染器._hold松手系统秒[i] = None
                    软件渲染器._hold当前按下中[i] = False
                except Exception:
                    pass
            try:
                if (
                    i < len(命中hold结束谱面秒)
                    and float(命中hold结束谱面秒[i]) > -1.0
                    and float(当前秒) > float(命中hold结束谱面秒[i]) + 2.0
                ):
                    if i < len(命中hold开始谱面秒):
                        命中hold开始谱面秒[i] = -999.0
                    if i < len(命中hold结束谱面秒):
                        命中hold结束谱面秒[i] = -999.0
                    if i < len(击中特效循环到谱面秒) and float(击中特效循环到谱面秒[i]) > -1.0:
                        击中特效循环到谱面秒[i] = -999.0
            except Exception:
                continue

    def _绘制判定区组(self, 渲染器, 帧输入: Dict[str, Any]) -> int:
        判定区列表 = list(帧输入.get("判定区列表", []) or [])
        使用灰度 = bool(帧输入.get("Note层灰度", False))
        软件渲染器 = 帧输入.get("软件渲染器")
        if not 判定区列表:
            return 0
        绘制数 = 0
        项列表 = [项 for 项 in 判定区列表 if isinstance(项, dict)]
        项列表.sort(
            key=lambda 项: (
                _取整数(项.get("z", 0), 0),
                _取整数(项.get("_序号", 0), 0),
            )
        )
        for 项 in 项列表:
            if not isinstance(项, dict):
                continue
            轨道 = _取整数(项.get("轨道", -1), -1)
            if self._绘制判定区贴图项(渲染器, 软件渲染器, 项, int(轨道), 使用灰度):
                绘制数 += 1
            else:
                几何轨道 = int(轨道)
                if 几何轨道 < 0:
                    文件名 = str(项.get("文件名") or "")
                    if 文件名 == "key_ll.png":
                        几何轨道 = 0
                    elif 文件名 == "key_rr.png":
                        几何轨道 = 4
                    else:
                        几何轨道 = 2
                self._绘制几何判定区项(渲染器, 项, int(几何轨道), 使用灰度)
                绘制数 += 1
        return 绘制数

    def _绘制击中特效组(self, 渲染器, 帧输入: Dict[str, Any]) -> int:
        特效列表 = list(帧输入.get("击中特效列表", []) or [])
        使用灰度 = bool(帧输入.get("Note层灰度", False))
        软件渲染器 = 帧输入.get("软件渲染器")
        当前谱面秒 = _取浮点(帧输入.get("当前谱面秒", 0.0), 0.0)
        绘制数 = 0
        for 项 in 特效列表:
            if not isinstance(项, dict):
                continue
            矩形 = 项.get("rect")
            if not isinstance(矩形, pygame.Rect):
                continue
            轨道 = _取整数(项.get("轨道", -1), -1)
            if self._绘制击中特效贴图项(
                渲染器, 软件渲染器, 项, int(轨道), float(当前谱面秒), 使用灰度
            ):
                绘制数 += 1
            else:
                self._绘制几何特效项(渲染器, 项, int(轨道), 使用灰度)
                绘制数 += 1
        return 绘制数

    def _tap已命中(
        self,
        软件渲染器,
        轨道: int,
        开始秒: float,
        y开始: float,
        判定线y: float,
        当前秒: float,
    ) -> bool:
        if 软件渲染器 is None:
            return False
        try:
            表列表 = list(getattr(软件渲染器, "_已命中tap过期表毫秒", []) or [])
            if not (0 <= int(轨道) < len(表列表)):
                return False
            已命中表 = 表列表[int(轨道)]
            if not isinstance(已命中表, dict):
                return False
            开始毫秒 = int(round(float(开始秒) * 1000.0))
            当前毫秒 = int(round(float(当前秒) * 1000.0))
            过期毫秒 = int(已命中表.get(int(开始毫秒), -1))
            return bool(
                过期毫秒 > 0
                and 当前毫秒 <= 过期毫秒
                and float(y开始) < float(判定线y)
            )
        except Exception:
            return False

    def _是否命中长按(
        self,
        软件渲染器,
        轨道: int,
        开始秒: float,
        结束秒: float,
        当前秒: float,
    ) -> bool:
        if 软件渲染器 is None:
            return False
        try:
            命中开始列表 = list(getattr(软件渲染器, "_命中hold开始谱面秒", []) or [])
            命中结束列表 = list(getattr(软件渲染器, "_命中hold结束谱面秒", []) or [])
            轨 = int(轨道)
            if 轨 < 0 or 轨 >= len(命中开始列表) or 轨 >= len(命中结束列表):
                return False
            命中开始 = float(命中开始列表[轨])
            命中结束 = float(命中结束列表[轨])
            命中窗 = float(getattr(软件渲染器, "_命中匹配窗秒", 0.12) or 0.12)
            if 命中结束 <= -1.0 or float(当前秒) > 命中结束 + 1.2:
                return False
            return bool(abs(float(开始秒) - 命中开始) <= max(0.08, 命中窗 * 2.0))
        except Exception:
            return False

    def _绘制点按(
        self,
        渲染器,
        软件渲染器,
        轨道: int,
        x中心: float,
        y: float,
        箭头宽: int,
        使用灰度: bool,
        旋转角度: float = 0.0,
    ) -> bool:
        方位 = self._轨道到arrow方位码(int(轨道))
        文件名 = f"arrow_body_{方位}.png"
        原图 = self._取皮肤帧(软件渲染器, "arrow", 文件名)
        纹理, 图 = self._取贴图条目(
            渲染器,
            软件渲染器,
            f"arrow:{文件名}:{int(箭头宽)}",
            原图,
            int(箭头宽),
            bool(使用灰度),
        )
        if 纹理 is None or 图 is None:
            self._绘制几何点按(
                渲染器,
                int(轨道),
                int(round(float(x中心))),
                int(round(float(y))),
                int(箭头宽),
                bool(使用灰度),
                float(旋转角度),
            )
            return False
        return bool(
            self._绘制纹理中心(
                纹理,
                图,
                float(x中心),
                float(y),
                angle=float(旋转角度),
            )
        )

    def _绘制长按(
        self,
        渲染器,
        软件渲染器,
        轨道: int,
        x中心: float,
        y开始: float,
        y结束: float,
        箭头宽: int,
        判定线y: float,
        上边界: int,
        下边界: int,
        半隐模式: bool,
        半隐y阈值: int,
        使用灰度: bool,
        是否命中hold: bool,
        当前谱面秒: float,
        结束谱面秒: float,
    ) -> int:
        方位 = self._轨道到arrow方位码(int(轨道))
        皮肤包 = getattr(软件渲染器, "_皮肤包", None) if 软件渲染器 is not None else None
        箭头图集 = getattr(皮肤包, "arrow", None) if 皮肤包 is not None else None
        取hold图 = getattr(软件渲染器, "_取hold接缝优化图", None)
        取hold身体模式 = getattr(软件渲染器, "_取hold身体模式", None)

        def 取hold贴图(文件名: str) -> Tuple[Optional[Any], Optional[pygame.Surface]]:
            if callable(取hold图) and 箭头图集 is not None:
                try:
                    图 = 取hold图(箭头图集, 文件名, int(箭头宽))
                    if 图 is not None:
                        if bool(使用灰度):
                            图 = self._取灰度图(图)
                        return self._取纹理(渲染器, 图), 图
                except Exception:
                    pass
            return self._取贴图条目(
                渲染器,
                软件渲染器,
                f"arrow:{文件名}:{int(箭头宽)}",
                self._取皮肤帧(软件渲染器, "arrow", 文件名),
                int(箭头宽),
                bool(使用灰度),
            )

        头纹理, 头图 = 取hold贴图(f"arrow_body_{方位}.png")
        罩纹理, 罩图 = 取hold贴图(f"arrow_mask_{方位}.png")
        身纹理, 身图 = 取hold贴图(f"arrow_repeat_{方位}.png")
        尾纹理, 尾图 = 取hold贴图(f"arrow_tail_{方位}.png")
        if all(x is None for x in (头纹理, 罩纹理, 身纹理, 尾纹理)):
            return int(
                self._绘制几何长按(
                    渲染器,
                    int(轨道),
                    int(x中心),
                    int(y开始),
                    int(y结束),
                    int(箭头宽),
                    int(判定线y),
                    int(max(下边界, 判定线y + 箭头宽)),
                    bool(半隐模式),
                    int(半隐y阈值),
                    bool(使用灰度),
                    bool(是否命中hold),
                )
            )

        if bool(半隐模式) and min(float(y开始), float(y结束)) > float(半隐y阈值):
            return 0

        头中心y = float(y开始)
        尾巴中心y = float(y结束)
        目标判定y = float(判定线y)

        if bool(是否命中hold):
            if float(当前谱面秒) >= float(结束谱面秒):
                return 0
            if 头中心y < 目标判定y:
                头中心y = float(目标判定y)

        首块纹理, 首块图 = (罩纹理, 罩图)
        if 首块图 is None:
            首块纹理, 首块图 = 身纹理, 身图
        if 首块图 is None:
            首块纹理, 首块图 = 尾纹理, 尾图

        中块纹理, 中块图 = (身纹理, 身图)
        if 中块图 is None:
            中块纹理, 中块图 = 首块纹理, 首块图
        if 中块图 is None:
            中块纹理, 中块图 = 尾纹理, 尾图

        末块纹理, 末块图 = (尾纹理, 尾图)
        if 末块图 is None:
            末块纹理, 末块图 = 中块纹理, 中块图
        if 末块图 is None:
            末块纹理, 末块图 = 首块纹理, 首块图

        参考图 = 中块图 or 首块图 or 末块图
        身体模式 = (
            str(取hold身体模式() or "repeat").strip().lower()
            if callable(取hold身体模式)
            else "repeat"
        )
        已绘制 = False
        if 参考图 is None and 头图 is None:
            return int(
                self._绘制几何长按(
                    渲染器,
                    int(轨道),
                    int(x中心),
                    int(y开始),
                    int(y结束),
                    int(箭头宽),
                    int(判定线y),
                    int(max(下边界, 判定线y + 箭头宽)),
                    bool(半隐模式),
                    int(半隐y阈值),
                    bool(使用灰度),
                    bool(是否命中hold),
                )
            )

        if (
            参考图 is not None
            and float(尾巴中心y) > float(头中心y)
            and int(参考图.get_height()) > 0
        ):
            块步进 = float(max(1, int(参考图.get_height())))
            首块中心y = float(头中心y) + float(块步进) * 0.5
            首块顶y = (
                float(首块中心y) - float(首块图.get_height()) * 0.5
                if 首块图 is not None
                else float(头中心y)
            )
            if 罩图 is not None and 首块图 is 罩图 and 头图 is not None:
                首块顶y = float(头中心y) - float(首块图.get_height()) * 0.5
            if (
                身体模式 == "stretch"
                and 首块纹理 is not None
                and 首块图 is not None
                and 中块纹理 is not None
                and 中块图 is not None
                and 末块纹理 is not None
                and 末块图 is not None
                and float(尾巴中心y) > float(首块顶y + 首块图.get_height()) + 0.01
            ):
                if (
                    float(首块顶y + 首块图.get_height()) >= float(上边界)
                    and float(首块顶y) <= float(下边界)
                ):
                    已绘制 = bool(
                        self._绘制纹理矩形数据(
                            首块纹理,
                            首块图,
                            float(x中心) - float(首块图.get_width()) * 0.5,
                            float(首块顶y),
                            float(首块图.get_width()),
                            float(首块图.get_height()),
                        )
                        or 已绘制
                    )

                身体顶y = float(首块顶y + 首块图.get_height())
                身体底y = float(尾巴中心y)
                if float(身体底y) > float(身体顶y) + 0.01:
                    身体高 = int(max(1, round(float(身体底y - 身体顶y))))
                    if float(身体顶y) < float(下边界) and float(身体顶y + 身体高) > float(上边界):
                        已绘制 = bool(
                            self._绘制纹理矩形数据(
                                中块纹理,
                                中块图,
                                float(x中心) - float(中块图.get_width()) * 0.5,
                                float(身体顶y),
                                float(中块图.get_width()),
                                float(身体高),
                            )
                            or 已绘制
                        )

                末块顶y = float(尾巴中心y)
                if (
                    float(末块顶y + 末块图.get_height()) >= float(上边界)
                    and float(末块顶y) <= float(下边界)
                ):
                    已绘制 = bool(
                        self._绘制纹理矩形数据(
                            末块纹理,
                            末块图,
                            float(x中心) - float(末块图.get_width()) * 0.5,
                            float(末块顶y),
                            float(末块图.get_width()),
                            float(末块图.get_height()),
                        )
                        or 已绘制
                    )
            else:
                块列表: List[Tuple[Optional[Any], Optional[pygame.Surface], float, Optional[pygame.Rect]]] = []
                if 首块图 is not None:
                    块列表.append((首块纹理, 首块图, float(首块顶y), None))

                当前顶y = float(首块顶y + (首块图.get_height() if 首块图 is not None else 0))
                中块高 = int(max(1, 中块图.get_height())) if 中块图 is not None else 0
                while 中块图 is not None and float(当前顶y + 中块高) <= float(尾巴中心y):
                    块列表.append((中块纹理, 中块图, float(当前顶y), None))
                    当前顶y += float(中块高)

                if 中块图 is not None and float(当前顶y) < float(尾巴中心y):
                    剩余高 = int(max(1, round(float(尾巴中心y) - float(当前顶y))))
                    剩余高 = int(min(剩余高, int(中块图.get_height())))
                    if 剩余高 > 0:
                        块列表.append(
                            (
                                中块纹理,
                                中块图,
                                float(当前顶y),
                                pygame.Rect(0, 0, int(中块图.get_width()), int(剩余高)),
                            )
                        )

                if 末块图 is not None:
                    块列表.append((末块纹理, 末块图, float(尾巴中心y), None))

                for 块纹理, 块图, 块顶y, 源矩形 in 块列表:
                    if 块纹理 is None or 块图 is None:
                        continue
                    if (
                        float(块顶y + (源矩形.h if isinstance(源矩形, pygame.Rect) else 块图.get_height())) < float(上边界)
                        or float(块顶y) > float(下边界)
                    ):
                        continue
                    目标高 = (
                        int(源矩形.h)
                        if isinstance(源矩形, pygame.Rect)
                        else int(块图.get_height())
                    )
                    已绘制 = bool(
                        self._绘制纹理矩形数据(
                            块纹理,
                            块图,
                            float(x中心) - float(块图.get_width()) * 0.5,
                            float(块顶y),
                            float(块图.get_width()),
                            float(目标高),
                            源矩形=源矩形,
                        )
                        or 已绘制
                    )

        if (
            头纹理 is not None
            and 头图 is not None
            and float(上边界) <= float(头中心y) <= float(下边界)
        ):
            已绘制 = bool(
                self._绘制纹理中心(
                    头纹理, 头图, float(x中心), float(头中心y)
                )
                or 已绘制
            )
        return 1 if 已绘制 else 0

    def _绘制软件长按图层(
        self,
        渲染器,
        软件渲染器,
        轨道: int,
        x中心: int,
        y开始: int,
        y结束: int,
        箭头宽: int,
        判定线y: int,
        上边界: int,
        下边界: int,
        头图: Optional[pygame.Surface],
        罩图: Optional[pygame.Surface],
        身图: Optional[pygame.Surface],
        尾图: Optional[pygame.Surface],
        是否命中hold: bool,
        当前谱面秒: float,
        结束谱面秒: float,
    ) -> Optional[int]:
        if 软件渲染器 is None:
            return None
        画hold = getattr(软件渲染器, "_画hold", None)
        图集 = getattr(getattr(软件渲染器, "_皮肤包", None), "arrow", None)
        if not callable(画hold) or 图集 is None:
            return None

        候选图列表 = [图 for 图 in (头图, 罩图, 身图, 尾图) if isinstance(图, pygame.Surface)]
        if not 候选图列表:
            return None

        try:
            最大宽 = max(int(图.get_width()) for 图 in 候选图列表)
            最大高 = max(int(图.get_height()) for 图 in 候选图列表)
        except Exception:
            最大宽 = int(max(16, 箭头宽))
            最大高 = int(max(16, 箭头宽))

        半宽 = int(max(最大宽 // 2 + 8, 箭头宽))
        上余量 = int(max(最大高 + 8, 箭头宽 * 2))
        下余量 = int(max(最大高 + 8, 箭头宽 * 2))
        局部左 = int(x中心 - 半宽)
        局部上 = int(min(y开始, y结束, 判定线y) - 上余量)
        局部下 = int(max(y开始, y结束, 判定线y) + 下余量)
        局部上 = int(max(上边界 - 上余量, 局部上))
        局部下 = int(min(下边界 + 下余量, 局部下))
        if 局部下 <= 局部上:
            return 0

        局部宽 = int(max(2, 半宽 * 2))
        局部高 = int(max(2, 局部下 - 局部上))
        try:
            图层 = pygame.Surface((局部宽, 局部高), pygame.SRCALPHA)
            图层.fill((0, 0, 0, 0))
            画hold(
                图层,
                图集,
                int(轨道),
                int(x中心 - 局部左),
                float(y开始 - 局部上),
                float(y结束 - 局部上),
                当前谱面秒=float(当前谱面秒),
                结束谱面秒=float(结束谱面秒),
                箭头宽=int(箭头宽),
                判定线y=int(判定线y - 局部上),
                是否命中hold=bool(是否命中hold),
                上边界=int(上边界 - 局部上),
                下边界=int(下边界 - 局部上),
                是否绘制头=True,
            )
            if 图层.get_bounding_rect().w <= 0 or 图层.get_bounding_rect().h <= 0:
                return 0
            纹理 = self._建临时纹理(渲染器, 图层)
            if 纹理 is None:
                return 0
            已绘制 = self._绘制纹理矩形(
                纹理,
                图层,
                pygame.Rect(int(局部左), int(局部上), int(局部宽), int(局部高)),
                None,
                alpha=255,
                blend_mode=1,
            )
            return 1 if bool(已绘制) else 0
        except Exception:
            return None

    def _绘制判定区双手(
        self,
        渲染器,
        软件渲染器,
        判定区列表: List[Dict[str, Any]],
        使用灰度: bool,
    ):
        if len(判定区列表) < 5:
            return
        按轨道 = {
            _取整数(项.get("轨道", -1), -1): 项
            for 项 in 判定区列表
            if isinstance(项, dict)
        }
        if 0 not in 按轨道 or 4 not in 按轨道:
            return
        左项 = 按轨道[0]
        右项 = 按轨道[4]
        轨1 = 按轨道.get(1, 左项)
        左x = _取整数(左项.get("x", 0), 0)
        右x = _取整数(右项.get("x", 0), 0)
        参考x = _取整数(轨1.get("x", 左x), 左x)
        间距 = int(max(8, abs(int(参考x) - int(左x))))
        左手x = int(左x - 间距)
        右手x = int(右x + 间距)
        左手y = _取整数(左项.get("y", 0), 0)
        右手y = _取整数(右项.get("y", 左手y), 左手y)
        receptor宽 = int(
            max(
                16,
                _取整数(左项.get("基础宽", 左项.get("w", 0)), 0),
                _取整数(右项.get("基础宽", 右项.get("w", 0)), 0),
            )
        )
        for 文件名, x中心, y中心 in (
            ("key_ll.png", 左手x, 左手y),
            ("key_rr.png", 右手x, 右手y),
        ):
            原图 = self._取皮肤帧(软件渲染器, "key", 文件名)
            图 = self._取按高缩放图(
                软件渲染器,
                f"key:{文件名}:h:{int(receptor宽)}",
                原图,
                int(receptor宽),
            )
            if 图 is None:
                continue
            if bool(使用灰度):
                图 = self._取灰度图(图)
            纹理 = self._取纹理(渲染器, 图)
            if 纹理 is not None and 图 is not None:
                self._绘制纹理中心(纹理, 图, int(x中心), int(y中心))

    def _绘制判定区贴图项(
        self,
        渲染器,
        软件渲染器,
        项: Dict[str, Any],
        轨道: int,
        使用灰度: bool,
    ) -> bool:
        文件名 = str(项.get("文件名") or "").strip()
        if not 文件名 and int(轨道) >= 0:
            方位 = self._轨道到key方位码(int(轨道))
            文件名 = f"key_{方位}.png"
        if not 文件名:
            return False

        目标矩形 = 项.get("rect")
        if isinstance(目标矩形, pygame.Rect):
            x中心 = int(目标矩形.centerx)
            y中心 = int(目标矩形.centery)
            目标宽 = int(max(8, 目标矩形.w))
            目标高 = int(max(8, 目标矩形.h))
        else:
            x中心 = _取整数(项.get("x", 0), 0)
            y中心 = _取整数(项.get("y", 0), 0)
            目标宽 = int(
                max(
                    8,
                    _取整数(项.get("w", 0), 0),
                    _取整数(项.get("基础宽", 0), 0),
                )
            )
            目标高 = int(
                max(
                    8,
                    _取整数(项.get("h", 0), 0),
                    _取整数(项.get("基础高", 0), 0),
                )
            )

        if bool(项.get("按高缩放", False)) or 文件名 in ("key_ll.png", "key_rr.png"):
            原图 = self._取皮肤帧(软件渲染器, "key", 文件名)
            图 = self._取按高缩放图(
                软件渲染器,
                f"key:{文件名}:h:{int(目标高)}",
                原图,
                int(目标高),
            )
            if 图 is None:
                return False
            if bool(使用灰度):
                图 = self._取灰度图(图)
            纹理 = self._取纹理(渲染器, 图)
            if 纹理 is None:
                return False
        else:
            纹理, 图 = self._取贴图条目(
                渲染器,
                软件渲染器,
                f"key:{文件名}:{int(目标宽)}",
                self._取皮肤帧(软件渲染器, "key", 文件名),
                int(目标宽),
                bool(使用灰度),
            )
            if 纹理 is None or 图 is None:
                return False
        return bool(
            self._绘制纹理中心(
                纹理,
                图,
                int(x中心),
                int(y中心),
            )
        )

    def _绘制击中特效贴图项(
        self,
        渲染器,
        软件渲染器,
        项: Dict[str, Any],
        轨道: int,
        当前谱面秒: float,
        使用灰度: bool,
    ) -> bool:
        矩形 = 项.get("rect")
        if not isinstance(矩形, pygame.Rect):
            return False
        帧信息 = self._取击中特效帧信息(软件渲染器, int(轨道), float(当前谱面秒))
        if 帧信息 is None:
            return False
        文件名, 需要翻转, 循环播放 = 帧信息
        目标宽 = int(max(24, 矩形.w))
        纹理, 图 = self._取贴图条目(
            渲染器,
            软件渲染器,
            f"fx:{文件名}:{int(目标宽)}",
            self._取皮肤帧(软件渲染器, "key_effect", 文件名),
            int(目标宽),
            bool(使用灰度),
        )
        if 纹理 is None or 图 is None:
            return False
        alpha = int(max(48, min(255, round(float(_取浮点(项.get("强度", 1.0), 1.0)) * 255.0))))
        已绘制 = bool(
            self._绘制纹理中心(
                纹理,
                图,
                int(矩形.centerx),
                int(矩形.centery),
                flip_x=bool(需要翻转),
                alpha=alpha,
                blend_mode=2,
            )
        )
        if bool(循环播放):
            已绘制 = bool(
                self._绘制纹理中心(
                    纹理,
                    图,
                    int(矩形.centerx),
                    int(矩形.centery),
                    flip_x=bool(需要翻转),
                    alpha=alpha,
                    blend_mode=2,
                )
                or 已绘制
            )
        return 已绘制

    def _取击中特效帧信息(
        self,
        软件渲染器,
        轨道: int,
        当前谱面秒: float,
    ) -> Optional[Tuple[str, bool, bool]]:
        if 软件渲染器 is None or int(轨道) < 0 or int(轨道) >= 5:
            return None
        try:
            轨 = int(轨道)
            帧数 = 18
            fps = float(getattr(软件渲染器, "_击中特效帧率", 60.0) or 60.0)
            循环到列表 = list(getattr(软件渲染器, "_击中特效循环到谱面秒", []) or [])
            开始列表 = list(getattr(软件渲染器, "_击中特效开始谱面秒", []) or [])
            进行列表 = list(getattr(软件渲染器, "_击中特效进行秒", []) or [])
            循环到 = float(循环到列表[轨])
            进行秒 = float(进行列表[轨])
            if 循环到 <= 0.0 and 进行秒 < 0.0:
                return None
            循环播放 = False
            if 循环到 > 0.0:
                if float(当前谱面秒) > 循环到 + 0.02:
                    return None
                if 进行秒 < 0.0:
                    进行秒 = 0.0
                帧号 = int(max(0, min(帧数 - 1, int(进行秒 * fps))))
                循环播放 = True
            else:
                帧号 = int(max(0, min(帧数 - 1, int(进行秒 * fps))))
            前缀, 需要翻转 = self._轨道到击中序列(int(轨))
            return (f"{前缀}_{帧号:04d}.png", bool(需要翻转), bool(循环播放))
        except Exception:
            return None

    def _绘制几何点按(
        self,
        渲染器,
        轨道: int,
        x中心: int,
        y: int,
        箭头宽: int,
        使用灰度: bool,
        旋转角度: float = 0.0,
    ):
        del 旋转角度
        颜色 = self._取轨道颜色(int(轨道), bool(使用灰度))
        尺寸 = int(max(10, 箭头宽))
        矩形 = pygame.Rect(
            int(x中心 - 尺寸 // 2),
            int(y - 尺寸 // 2),
            int(尺寸),
            int(尺寸),
        )
        try:
            渲染器.draw_color = (int(颜色[0]), int(颜色[1]), int(颜色[2]), 230)
            渲染器.fill_rect(矩形)
        except Exception:
            pass

    def _绘制几何长按(
        self,
        渲染器,
        轨道: int,
        x中心: int,
        y开始: int,
        y结束: int,
        箭头宽: int,
        判定线y: int,
        底部y: int,
        半隐模式: bool,
        半隐y阈值: int,
        使用灰度: bool,
        是否命中hold: bool,
    ) -> int:
        颜色 = self._取轨道颜色(int(轨道), bool(使用灰度))
        if bool(是否命中hold) and int(y开始) < int(判定线y):
            y开始 = int(判定线y)
        y1 = int(min(int(y开始), int(y结束)))
        y2 = int(max(int(y开始), int(y结束)))
        if bool(半隐模式):
            y2 = int(min(int(y2), int(半隐y阈值)))
        if y2 < -箭头宽 or y1 > int(底部y + 箭头宽):
            return 0
        宽 = int(max(8, round(float(箭头宽) * 0.4)))
        身体 = pygame.Rect(
            int(x中心 - 宽 // 2),
            int(max(-箭头宽, y1)),
            int(宽),
            int(max(1, min(int(底部y + 箭头宽), y2) - max(-箭头宽, y1))),
        )
        try:
            渲染器.draw_color = (int(颜色[0]), int(颜色[1]), int(颜色[2]), 190)
            if 身体.h > 0:
                渲染器.fill_rect(身体)
            头 = pygame.Rect(
                int(x中心 - 箭头宽 // 2),
                int(y开始 - 箭头宽 // 2),
                int(箭头宽),
                int(箭头宽),
            )
            尾 = pygame.Rect(
                int(x中心 - max(8, 箭头宽 // 3)),
                int(y结束 - max(8, 箭头宽 // 3)),
                int(max(16, 箭头宽 // 1.5)),
                int(max(16, 箭头宽 // 1.5)),
            )
            渲染器.fill_rect(尾)
            渲染器.fill_rect(头)
            return 1
        except Exception:
            return 0

    def _绘制几何判定区项(
        self,
        渲染器,
        项: Dict[str, Any],
        轨道: int,
        使用灰度: bool,
    ):
        颜色 = self._取轨道颜色(int(轨道), bool(使用灰度))
        矩形 = pygame.Rect(
            int(_取整数(项.get("x", 0), 0) - _取整数(项.get("w", 0), 0) // 2),
            int(_取整数(项.get("y", 0), 0) - _取整数(项.get("h", 0), 0) // 2),
            int(max(4, _取整数(项.get("w", 0), 0))),
            int(max(4, _取整数(项.get("h", 0), 0))),
        )
        try:
            渲染器.draw_color = (int(颜色[0]), int(颜色[1]), int(颜色[2]), 210)
            渲染器.fill_rect(矩形)
        except Exception:
            pass

    def _绘制几何特效项(
        self,
        渲染器,
        项: Dict[str, Any],
        轨道: int,
        使用灰度: bool,
    ):
        矩形 = 项.get("rect")
        if not isinstance(矩形, pygame.Rect):
            return
        颜色 = self._取轨道颜色(int(轨道), bool(使用灰度))
        alpha = int(
            max(36, min(220, round(float(_取浮点(项.get("强度", 1.0), 1.0)) * 180.0)))
        )
        try:
            渲染器.draw_color = (int(颜色[0]), int(颜色[1]), int(颜色[2]), alpha)
            渲染器.fill_rect(矩形)
        except Exception:
            pass

    @staticmethod
    def _轨道到key方位码(轨道序号: int) -> str:
        return {0: "bl", 1: "tl", 2: "cc", 3: "tr", 4: "br"}.get(int(轨道序号), "cc")

    @staticmethod
    def _轨道到arrow方位码(轨道序号: int) -> str:
        return {0: "lb", 1: "lt", 2: "cc", 3: "rt", 4: "rb"}.get(int(轨道序号), "cc")

    @staticmethod
    def _轨道到击中序列(轨道: int) -> Tuple[str, bool]:
        if int(轨道) == 0:
            return ("image_084", False)
        if int(轨道) == 1:
            return ("image_085", False)
        if int(轨道) == 2:
            return ("image_086", False)
        if int(轨道) == 3:
            return ("image_085", True)
        if int(轨道) == 4:
            return ("image_084", True)
        return ("image_086", False)

    def _取轨道颜色(self, 轨道: int, 使用灰度: bool) -> Tuple[int, int, int]:
        轨 = int(max(0, min(4, int(轨道))))
        颜色表 = self._灰度轨道颜色 if bool(使用灰度) else self._彩色轨道颜色
        try:
            return tuple(int(v) for v in 颜色表[轨])
        except Exception:
            return (220, 220, 220)
