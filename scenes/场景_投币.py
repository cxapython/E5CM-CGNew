import math
import os
import time
import pygame
try:
    from pygame._sdl2 import video as _sdl2_video
except Exception:
    _sdl2_video = None

from core.常量与路径 import 取项目根目录 as _公共取项目根目录
from core.工具 import cover缩放 as _cover缩放
from core.对局状态 import 初始化对局流程, 消耗信用, 取每局所需信用
from core.sqlite_store import (
    SCOPE_GLOBAL_SETTINGS as _全局设置存储作用域,
    write_scope_patch as _更新存储作用域,
)
from core.踏板控制 import 踏板动作_左, 踏板动作_右, 踏板动作_确认
from ui.按钮特效 import 公用按钮点击特效, 公用按钮音效
from ui.准备动画 import 全屏透明叠加层


def _限幅(值: float, 最小值: float = 0.0, 最大值: float = 1.0) -> float:
    try:
        值 = float(值)
    except Exception:
        值 = float(最小值)
    return max(float(最小值), min(float(最大值), 值))


def _缓出三次(值: float) -> float:
    值 = _限幅(值)
    return 1.0 - pow(1.0 - 值, 3)


def _缓入出(值: float) -> float:
    值 = _限幅(值)
    return 值 * 值 * (3.0 - 2.0 * 值)


def _脉冲(值: float) -> float:
    return math.sin(_限幅(值) * math.pi)


def _区间进度(当前: float, 开始: float, 结束: float) -> float:
    if float(结束) <= float(开始):
        return 1.0 if float(当前) >= float(结束) else 0.0
    return _限幅((float(当前) - float(开始)) / (float(结束) - float(开始)))


def _区间脉冲(当前: float, 开始: float, 峰值: float, 结束: float) -> float:
    if float(当前) <= float(开始) or float(当前) >= float(结束):
        return 0.0
    if float(当前) <= float(峰值):
        return _区间进度(float(当前), float(开始), float(峰值))
    return 1.0 - _区间进度(float(当前), float(峰值), float(结束))


def _颜色插值(
    起始颜色: tuple[int, int, int],
    结束颜色: tuple[int, int, int],
    进度: float,
) -> tuple[int, int, int]:
    进度 = _限幅(进度)
    return (
        int(int(起始颜色[0]) + (int(结束颜色[0]) - int(起始颜色[0])) * 进度),
        int(int(起始颜色[1]) + (int(结束颜色[1]) - int(起始颜色[1])) * 进度),
        int(int(起始颜色[2]) + (int(结束颜色[2]) - int(起始颜色[2])) * 进度),
    )


def _线性插值(起点: float, 终点: float, 进度: float) -> float:
    进度 = _限幅(进度)
    return float(起点) + (float(终点) - float(起点)) * 进度


def _周期脉冲(
    当前: float,
    起点: float,
    周期: float,
    开始: float,
    峰值: float,
    结束: float,
) -> float:
    if float(当前) < float(起点):
        return 0.0
    周期 = max(0.001, float(周期))
    局部时间 = (float(当前) - float(起点)) % 周期
    return _区间脉冲(局部时间, float(开始), float(峰值), float(结束))


class 场景_投币:
    名称 = "投币"

    _设计宽 = 1920
    _设计高 = 1080

    _阶段_投币 = "投币"
    _阶段_玩家选择 = "玩家选择"

    _bbox_logo = (478, 247, 1443, 689)
    _bbox_请投币 = (860, 893, 1060, 950)
    _bbox_联网 = (703, 991, 767, 1046)
    _bbox_credit = (788, 1001, 1132, 1046)
    _bbox_1p = (125, 718, 368, 874)
    _bbox_2p = (1551, 718, 1795, 874)
    _logo登场总时长 = 2.35
    _logo实时特效总时长 = 6.68

    def __init__(self, 上下文: dict):
        self.上下文 = 上下文
        资源 = self.上下文["资源"]
        self._禁用投币特效 = True

        self._背景视频 = self.上下文.get("背景视频")
        self._开始时间 = time.time()
        self._缓存尺寸 = (0, 0)
        self._软件背景缓存面: pygame.Surface | None = None
        self._软件背景缓存尺寸 = (0, 0)
        self._软件背景下次取帧秒 = 0.0
        self._软件背景取帧间隔秒 = 1.0 / 30.0
        self._共享背景回退图 = self._安全加载图片(
            str(self.上下文.get("共享背景回退图路径", "") or ""),
            透明=False,
        )
        self._共享背景回退缓存面: pygame.Surface | None = None
        self._共享背景回退缓存尺寸 = (0, 0)

        self._阶段 = self._阶段_投币
        self._是否显示logo = False
        self._hover_1p = False
        self._hover_2p = False
        self._踏板选中玩家数: int | None = None

        self._遮罩图 = None
        self._logo图 = None
        self._logo遮罩图 = None
        self._logo柔光图 = None
        self._logo柔光偏移 = (0, 0)
        self._logo外描边图 = None
        self._logo外描边偏移 = (0, 0)
        self._logo红偏图 = None
        self._logo青偏图 = None
        self._logo柔光红图 = None
        self._logo柔光青图 = None
        self._logo描边青图 = None
        self._logo描边红图 = None
        self._logo轮廓点: list[tuple[int, int, float, float, float, float]] = []
        self._logo内部采样点: list[tuple[int, int, float, float]] = []
        self._logo电弧条目: list[dict] = []
        self._logo长弧条目: list[dict] = []
        self._logo闪点条目: list[dict] = []
        self._logo切片条目: list[dict] = []
        self._后处理暗角图 = None
        self._logo局部特效区域 = pygame.Rect(0, 0, 1, 1)
        self._logo_rect = pygame.Rect(0, 0, 1, 1)
        self._1p图 = None
        self._2p图 = None
        self._1p图_hover = None
        self._2p图_hover = None
        self._logo实时叠加层 = 全屏透明叠加层()
        self._中心缩放缓存: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self._logo登场缓存面: pygame.Surface | None = None
        self._logo登场缓存尺寸 = (0, 0)
        self._logo登场缓存帧 = -1
        self._logo登场缓存帧率 = 24.0
        self._logo实时特效缓存尺寸 = (0, 0)
        self._logo实时特效缓存帧 = -1
        self._logo实时特效缓存帧率 = 24.0
        self._logo实时特效缓存模式 = ""
        self._logo实时特效软件帧率 = 12.0
        self._GPU背景视频纹理 = None
        self._GPU背景视频纹理渲染器id: int = 0
        self._GPU背景视频纹理尺寸 = (0, 0)
        self._GPU背景视频纹理源键 = ()
        self._GPU界面纹理缓存: dict[tuple[int, int, int, int], object] = {}
        self._GPU界面纹理渲染器id: int = 0

        self._1p_rect = pygame.Rect(0, 0, 1, 1)
        self._2p_rect = pygame.Rect(0, 0, 1, 1)

        self._logo原图 = self._安全加载图片(资源.get("投币_logo", ""), 透明=True)
        self._联网原图 = self._安全加载图片(资源.get("投币_联网图标", ""), 透明=True)
        self._1p原图 = self._安全加载图片(资源.get("1P按钮", ""), 透明=True)
        self._2p原图 = self._安全加载图片(资源.get("2P按钮", ""), 透明=True)
        self._logo登场开始时间 = 0.0
        self._logo粒子种子 = self._生成logo粒子种子()

        self.按钮音效 = 公用按钮音效(资源.get("按钮音效") or 资源.get("投币音效", ""))
        self._满额音效 = None
        self._1p特效 = 公用按钮点击特效(
            总时长=0.3,
            缩小阶段=0.1,
            缩小到=0.90,
            放大到=4.00,
            透明起始=255,
            透明结束=0,
        )
        self._2p特效 = 公用按钮点击特效(
            总时长=0.3,
            缩小阶段=0.1,
            缩小到=0.90,
            放大到=4.00,
            透明起始=255,
            透明结束=0,
        )

        self._选择动画进行中 = False
        self._选择动画结束时间 = 0.0
        self._待切换结果 = None

        根目录 = _公共取项目根目录(资源)
        self._排行榜BGM路径 = os.path.join(根目录, "冷资源", "backsound", "排行榜.mp3")
        满额音效路径 = os.path.join(根目录, "冷资源", "backsound", "elogo.wav")
        if os.path.isfile(满额音效路径):
            try:
                self._满额音效 = 公用按钮音效(满额音效路径)
            except Exception:
                self._满额音效 = None

    def 进入(self):
        self._开始时间 = time.time()
        self._缓存尺寸 = (0, 0)
        self._软件背景缓存面 = None
        self._软件背景缓存尺寸 = (0, 0)
        self._软件背景下次取帧秒 = 0.0
        self._选择动画进行中 = False
        self._选择动画结束时间 = 0.0
        self._待切换结果 = None
        self._logo登场开始时间 = 0.0
        self._失效logo登场缓存()
        self._失效logo实时特效缓存()
        self._logo实时叠加层.重置()
        self._确保缓存()
        self._按当前信用刷新阶段(允许播放满额音效=False)
        if self._是否显示logo and (not bool(self._禁用投币特效)):
            self._触发logo登场动画()
        if self._阶段 == self._阶段_投币:
            self._播放投币背景音乐()

    def 更新(self):
        if bool(self._选择动画进行中):
            if time.time() >= float(self._选择动画结束时间):
                self._选择动画进行中 = False
                结果 = self._待切换结果
                self._待切换结果 = None
                return 结果
            return None

        self._按当前信用刷新阶段(允许播放满额音效=True)
        return None

    def _执行选择(self, 玩家数: int):
        if bool(self._选择动画进行中):
            return None

        状态 = self._取状态()
        所需信用 = self._取所需信用()
        当前信用 = self._取当前信用()
        if 当前信用 < 所需信用:
            self._按当前信用刷新阶段(允许播放满额音效=False)
            return None

        self.按钮音效.播放()

        原状态快照 = {
            "投币数": int(状态.get("投币数", 0) or 0),
            "credit": str(状态.get("credit", "0") or "0"),
            "每局所需信用": int(状态.get("每局所需信用", 所需信用) or 所需信用),
            "投币快捷键": int(状态.get("投币快捷键", pygame.K_F1) or pygame.K_F1),
            "投币快捷键显示": str(状态.get("投币快捷键显示", "F1") or "F1"),
            "bgm_排行榜_已播放": bool(状态.get("bgm_排行榜_已播放", False)),
        }

        消耗信用(状态, int(所需信用))
        try:
            扣费后投币数 = max(0, int(状态.get("投币数", 0) or 0))
        except Exception:
            扣费后投币数 = max(0, 原状态快照["投币数"] - int(所需信用))

        初始化对局流程(状态)

        状态["玩家数"] = int(玩家数)
        状态["投币数"] = int(扣费后投币数)
        状态["credit"] = str(int(扣费后投币数))
        状态["每局所需信用"] = int(原状态快照["每局所需信用"])
        状态["投币快捷键"] = int(原状态快照["投币快捷键"])
        状态["投币快捷键显示"] = str(原状态快照["投币快捷键显示"])
        状态["bgm_排行榜_已播放"] = bool(原状态快照["bgm_排行榜_已播放"])

        self._同步信用显示并持久化()

        self._选择动画进行中 = True
        self._选择动画结束时间 = time.time() + 0.32
        self._待切换结果 = {"切换到": "登陆磁卡", "禁用黑屏过渡": False}
        return None

    def 处理全局踏板(self, 动作: str):
        if bool(self._选择动画进行中):
            return None

        if self._阶段 != self._阶段_玩家选择:
            return None

        if 动作 == 踏板动作_左:
            if self._踏板选中玩家数 != 1:
                self.按钮音效.播放()
            self._踏板选中玩家数 = 1
            return None

        if 动作 == 踏板动作_右:
            if self._踏板选中玩家数 != 2:
                self.按钮音效.播放()
            self._踏板选中玩家数 = 2
            return None

        if 动作 == 踏板动作_确认 and self._踏板选中玩家数 in (1, 2):
            return self._执行选择(int(self._踏板选中玩家数))
        return None

    def 处理事件(self, 事件):
        if 事件.type == pygame.VIDEORESIZE:
            return None

        if bool(self._选择动画进行中):
            return None

        if self._阶段 != self._阶段_玩家选择:
            return None

        if 事件.type == pygame.MOUSEMOTION:
            self._hover_1p = self._1p_rect.collidepoint(事件.pos)
            self._hover_2p = self._2p_rect.collidepoint(事件.pos)
            return None

        if 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            if self._1p_rect.collidepoint(事件.pos):
                self._踏板选中玩家数 = 1
                return self._执行选择(1)
            if self._2p_rect.collidepoint(事件.pos):
                self._踏板选中玩家数 = 2
                return self._执行选择(2)
        return None

    def _取状态(self) -> dict:
        状态 = self.上下文.get("状态", {})
        if not isinstance(状态, dict):
            状态 = {}
            self.上下文["状态"] = 状态
        return 状态

    def _取当前信用(self) -> int:
        try:
            return max(0, int(self._取状态().get("投币数", 0) or 0))
        except Exception:
            return 0

    def _取所需信用(self) -> int:
        try:
            return max(1, int(取每局所需信用(self._取状态())))
        except Exception:
            return 3

    def _同步信用显示并持久化(self):
        状态 = self._取状态()
        当前信用 = self._取当前信用()
        状态["投币数"] = int(当前信用)
        状态["credit"] = str(int(当前信用))
        数据 = {
            "投币快捷键": int(状态.get("投币快捷键", pygame.K_F1) or pygame.K_F1),
            "投币快捷键显示": str(状态.get("投币快捷键显示", "F1") or "F1"),
            "投币数": int(当前信用),
        }
        try:
            _更新存储作用域(_全局设置存储作用域, 数据)
        except Exception:
            pass

    def _播放投币背景音乐(self):
        try:
            self.上下文["音乐"].播放循环(self.上下文["资源"]["投币_BGM"])
        except Exception:
            pass
        try:
            self._取状态()["bgm_排行榜_已播放"] = False
        except Exception:
            pass

    def _播放玩家选择背景音乐(self, 播放满额音效: bool):
        状态 = self._取状态()
        已播 = bool(状态.get("bgm_排行榜_已播放", False))
        if bool(播放满额音效) and self._满额音效 is not None:
            try:
                self._满额音效.播放()
            except Exception:
                pass
        if (not 已播) and os.path.isfile(self._排行榜BGM路径):
            try:
                self.上下文["音乐"].播放循环(self._排行榜BGM路径)
                状态["bgm_排行榜_已播放"] = True
            except Exception:
                pass
        elif (not 已播) and (not os.path.isfile(self._排行榜BGM路径)):
            try:
                self.上下文["音乐"].播放循环(self.上下文["资源"]["投币_BGM"])
                状态["bgm_排行榜_已播放"] = True
            except Exception:
                pass

    def _设置logo显示(self, 是否显示: bool, 强制重播: bool = False):
        旧值 = bool(self._是否显示logo)
        self._是否显示logo = bool(是否显示)
        if self._是否显示logo:
            if bool(self._禁用投币特效):
                self._logo登场开始时间 = 0.0
                self._失效logo登场缓存()
                self._清空logo实时叠加层(重置=True)
            elif 强制重播 or (not 旧值):
                self._触发logo登场动画()
        else:
            self._logo登场开始时间 = 0.0
            self._失效logo登场缓存()
            self._清空logo实时叠加层(重置=True)

    def _切换到投币阶段(self):
        self._阶段 = self._阶段_投币
        self._踏板选中玩家数 = None
        self._hover_1p = False
        self._hover_2p = False
        self._播放投币背景音乐()

    def _切换到玩家选择阶段(self, 播放满额音效: bool):
        self._阶段 = self._阶段_玩家选择
        if self._踏板选中玩家数 not in (1, 2):
            self._踏板选中玩家数 = 1
        self._设置logo显示(True)
        self._播放玩家选择背景音乐(播放满额音效=播放满额音效)

    def _按当前信用刷新阶段(self, 允许播放满额音效: bool):
        当前信用 = self._取当前信用()
        所需信用 = self._取所需信用()
        self._设置logo显示(当前信用 > 0)

        if 当前信用 >= 所需信用:
            首次满额 = self._阶段 != self._阶段_玩家选择
            self._切换到玩家选择阶段(播放满额音效=bool(允许播放满额音效 and 首次满额))
            return

        if self._阶段 != self._阶段_投币:
            self._切换到投币阶段()

    def _读取软件背景覆盖帧(
        self,
        目标宽: int,
        目标高: int,
        当前时间: float,
    ) -> pygame.Surface | None:
        if self._背景视频 is None:
            self._软件背景缓存面 = None
            self._软件背景缓存尺寸 = (0, 0)
            self._软件背景下次取帧秒 = 0.0
            return self._取共享背景回退面(目标宽, 目标高)

        有效宽 = max(1, int(目标宽))
        有效高 = max(1, int(目标高))
        目标尺寸 = (有效宽, 有效高)
        if tuple(self._软件背景缓存尺寸) != tuple(目标尺寸):
            self._软件背景缓存尺寸 = tuple(目标尺寸)
            self._软件背景下次取帧秒 = 0.0

        if (
            float(当前时间) < float(self._软件背景下次取帧秒)
            and isinstance(self._软件背景缓存面, pygame.Surface)
        ):
            return self._软件背景缓存面

        try:
            新帧 = self._背景视频.读取覆盖帧(有效宽, 有效高)
        except Exception:
            self._停用背景视频()
            新帧 = None

        if isinstance(新帧, pygame.Surface):
            if tuple(新帧.get_size()) != tuple(目标尺寸):
                try:
                    新帧 = pygame.transform.smoothscale(新帧, 目标尺寸).convert()
                except Exception:
                    pass
            self._软件背景缓存面 = 新帧
        self._软件背景下次取帧秒 = float(当前时间) + max(
            1.0 / 60.0,
            float(self._软件背景取帧间隔秒 or (1.0 / 30.0)),
        )
        if isinstance(self._软件背景缓存面, pygame.Surface):
            return self._软件背景缓存面
        if isinstance(新帧, pygame.Surface):
            return 新帧
        return self._取共享背景回退面(有效宽, 有效高)

    def _停用背景视频(self):
        背景视频 = getattr(self, "_背景视频", None)
        if 背景视频 is not None:
            try:
                if hasattr(背景视频, "关闭"):
                    背景视频.关闭()
            except Exception:
                pass
        self._背景视频 = None
        try:
            self.上下文["背景视频"] = None
        except Exception:
            pass

    def _取共享背景回退面(self, 目标宽: int, 目标高: int) -> pygame.Surface | None:
        原图 = getattr(self, "_共享背景回退图", None)
        if not isinstance(原图, pygame.Surface):
            return None
        目标尺寸 = (max(1, int(目标宽)), max(1, int(目标高)))
        if (
            tuple(getattr(self, "_共享背景回退缓存尺寸", (0, 0))) == tuple(目标尺寸)
            and isinstance(getattr(self, "_共享背景回退缓存面", None), pygame.Surface)
        ):
            return self._共享背景回退缓存面
        try:
            回退面 = _cover缩放(原图, int(目标尺寸[0]), int(目标尺寸[1])).convert()
        except Exception:
            return None
        self._共享背景回退缓存面 = 回退面
        self._共享背景回退缓存尺寸 = tuple(目标尺寸)
        return 回退面

    def 退出(self):
        self._软件背景缓存面 = None
        self._软件背景缓存尺寸 = (0, 0)
        self._软件背景下次取帧秒 = 0.0
        self._GPU背景视频纹理 = None
        self._GPU背景视频纹理渲染器id = 0
        self._GPU背景视频纹理尺寸 = (0, 0)
        self._GPU背景视频纹理源键 = ()
        self._GPU界面纹理缓存 = {}
        self._GPU界面纹理渲染器id = 0

    def _绘制玩家选择按钮(self, 屏幕: pygame.Surface):
        if self._1p图:
            屏幕.blit(self._1p图, self._1p_rect.topleft)

        if self._2p图:
            屏幕.blit(self._2p图, self._2p_rect.topleft)

    def _安全加载图片(self, 路径: str, 透明: bool):
        try:
            if not 路径 or (not os.path.isfile(路径)):
                return None
            图片 = pygame.image.load(路径)
            return 图片.convert_alpha() if 透明 else 图片.convert()
        except Exception:
            return None

    def _映射到屏幕_rect(self, 边界框):
        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()
        缩放 = min(宽 / self._设计宽, 高 / self._设计高)
        内容宽 = self._设计宽 * 缩放
        内容高 = self._设计高 * 缩放
        偏移x = (宽 - 内容宽) / 2.0
        偏移y = (高 - 内容高) / 2.0
        左, 上, 右, 下 = 边界框
        x = int(偏移x + 左 * 缩放)
        y = int(偏移y + 上 * 缩放)
        rect宽 = int((右 - 左) * 缩放)
        rect高 = int((下 - 上) * 缩放)
        return pygame.Rect(x, y, max(1, rect宽), max(1, rect高))

    def _绘制_按中心缩放(
        self,
        屏幕: pygame.Surface,
        图片: pygame.Surface | None,
        基准框: pygame.Rect,
        缩放倍率: float,
    ):
        if 图片 is None:
            return
        缩放倍率 = float(max(0.1, 缩放倍率))
        if abs(缩放倍率 - 1.0) <= 0.001:
            屏幕.blit(图片, 基准框.topleft)
            return
        目标宽 = max(1, int(基准框.w * 缩放倍率))
        目标高 = max(1, int(基准框.h * 缩放倍率))
        缓存键 = (
            int(id(图片)),
            int(目标宽),
            int(目标高),
            int(round(缩放倍率 * 1000.0)),
        )
        新图 = self._中心缩放缓存.get(缓存键)
        if 新图 is None:
            新图 = pygame.transform.smoothscale(图片, (目标宽, 目标高)).convert_alpha()
            self._中心缩放缓存[缓存键] = 新图
        新框 = 新图.get_rect(center=基准框.center)
        屏幕.blit(新图, 新框.topleft)

    def _绘制文本(self, 屏幕, 文本, 字体, 颜色, 位置, 对齐="center"):
        文本面 = 字体.render(文本, True, 颜色)
        文本框 = 文本面.get_rect()
        setattr(文本框, 对齐, 位置)
        屏幕.blit(文本面, 文本框)
        return 文本框

    def _近似模糊(self, 图层: pygame.Surface, 缩放系数: float = 0.22) -> pygame.Surface:
        宽, 高 = 图层.get_size()
        if 宽 <= 1 or 高 <= 1:
            return 图层.copy()
        目标宽 = max(1, int(宽 * max(0.05, float(缩放系数))))
        目标高 = max(1, int(高 * max(0.05, float(缩放系数))))
        try:
            小图 = pygame.transform.smoothscale(图层, (目标宽, 目标高)).convert_alpha()
            return pygame.transform.smoothscale(小图, (宽, 高)).convert_alpha()
        except Exception:
            return 图层.copy()

    def _应使用GPU背景(self) -> bool:
        if _sdl2_video is None:
            return False
        显示后端 = self.上下文.get("显示后端", None)
        return bool(getattr(显示后端, "是否GPU", False))

    def _同步GPU背景缓存(self, 渲染器):
        当前渲染器id = int(id(渲染器))
        if 当前渲染器id == int(getattr(self, "_GPU背景视频纹理渲染器id", 0) or 0):
            return
        self._GPU背景视频纹理 = None
        self._GPU背景视频纹理渲染器id = 当前渲染器id
        self._GPU背景视频纹理尺寸 = (0, 0)
        self._GPU背景视频纹理源键 = ()

    def _取GPU输出与绘制尺寸(self, 显示后端) -> tuple[int, int, int, int]:
        绘制宽, 绘制高 = 1, 1
        输出宽, 输出高 = 1, 1
        try:
            屏幕 = self.上下文.get("屏幕", None)
            if isinstance(屏幕, pygame.Surface):
                绘制宽, 绘制高 = tuple(int(v) for v in 屏幕.get_size())
                输出宽, 输出高 = int(绘制宽), int(绘制高)
        except Exception:
            绘制宽, 绘制高 = 1, 1
            输出宽, 输出高 = 1, 1

        try:
            绘制屏幕 = 显示后端.取绘制屏幕()
            if isinstance(绘制屏幕, pygame.Surface):
                绘制宽, 绘制高 = tuple(int(v) for v in 绘制屏幕.get_size())
        except Exception:
            pass

        try:
            if bool(getattr(显示后端, "使用逻辑坐标映射", lambda: False)()):
                输出宽, 输出高 = int(绘制宽), int(绘制高)
            else:
                输出宽, 输出高 = tuple(int(v) for v in 显示后端.取输出尺寸())
        except Exception:
            输出宽, 输出高 = int(绘制宽), int(绘制高)

        绘制宽 = max(1, int(绘制宽))
        绘制高 = max(1, int(绘制高))
        输出宽 = max(1, int(输出宽))
        输出高 = max(1, int(输出高))
        return 绘制宽, 绘制高, 输出宽, 输出高

    def _取GPU背景视频纹理(self, 渲染器, 图: pygame.Surface | None):
        if _sdl2_video is None or 渲染器 is None or not isinstance(图, pygame.Surface):
            return None

        当前渲染器id = int(id(渲染器))
        if 当前渲染器id != int(getattr(self, "_GPU背景视频纹理渲染器id", 0) or 0):
            self._GPU背景视频纹理 = None
            self._GPU背景视频纹理渲染器id = 当前渲染器id
            self._GPU背景视频纹理尺寸 = (0, 0)
            self._GPU背景视频纹理源键 = ()

        尺寸 = (int(max(1, 图.get_width())), int(max(1, 图.get_height())))
        源键 = (int(id(图)), int(尺寸[0]), int(尺寸[1]))

        if self._GPU背景视频纹理 is None or tuple(
            getattr(self, "_GPU背景视频纹理尺寸", (0, 0))
        ) != tuple(尺寸):
            try:
                self._GPU背景视频纹理 = _sdl2_video.Texture.from_surface(渲染器, 图)
                self._GPU背景视频纹理尺寸 = tuple(尺寸)
                self._GPU背景视频纹理源键 = tuple(源键)
            except Exception:
                self._GPU背景视频纹理 = None
                self._GPU背景视频纹理尺寸 = (0, 0)
                self._GPU背景视频纹理源键 = ()
                return None
        elif tuple(getattr(self, "_GPU背景视频纹理源键", ())) != tuple(源键):
            try:
                self._GPU背景视频纹理.update(图)
                self._GPU背景视频纹理源键 = tuple(源键)
            except Exception:
                try:
                    self._GPU背景视频纹理 = _sdl2_video.Texture.from_surface(
                        渲染器, 图
                    )
                    self._GPU背景视频纹理尺寸 = tuple(尺寸)
                    self._GPU背景视频纹理源键 = tuple(源键)
                except Exception:
                    self._GPU背景视频纹理 = None
                    self._GPU背景视频纹理尺寸 = (0, 0)
                    self._GPU背景视频纹理源键 = ()
                    return None

        return self._GPU背景视频纹理

    def _绘制GPU视频背景(
        self,
        渲染器,
        图: pygame.Surface | None,
        屏宽: int,
        屏高: int,
    ):
        if _sdl2_video is None or 渲染器 is None or not isinstance(图, pygame.Surface):
            return
        纹理 = self._取GPU背景视频纹理(渲染器, 图)
        if 纹理 is None:
            return

        原宽 = int(max(1, 图.get_width()))
        原高 = int(max(1, 图.get_height()))
        if (原宽, 原高) == (int(屏宽), int(屏高)):
            目标矩形 = (0, 0, int(屏宽), int(屏高))
        else:
            比例 = max(float(屏宽) / float(原宽), float(屏高) / float(原高))
            新宽 = int(max(1, round(float(原宽) * 比例)))
            新高 = int(max(1, round(float(原高) * 比例)))
            目标矩形 = (
                int((屏宽 - 新宽) // 2),
                int((屏高 - 新高) // 2),
                int(新宽),
                int(新高),
            )
        try:
            纹理.draw(dstrect=目标矩形)
        except Exception:
            pass

    def _应使用GPU中层(self) -> bool:
        return bool(self._应使用GPU背景())

    def _同步GPU界面纹理缓存(self, 渲染器):
        当前渲染器id = int(id(渲染器))
        if 当前渲染器id == int(getattr(self, "_GPU界面纹理渲染器id", 0) or 0):
            return
        self._GPU界面纹理渲染器id = 当前渲染器id
        self._GPU界面纹理缓存 = {}

    def _取GPU界面纹理(self, 渲染器, 图: pygame.Surface | None):
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

    def _清理GPU界面纹理(self, 图: pygame.Surface | None):
        if not isinstance(图, pygame.Surface):
            return
        图id = int(id(图))
        删除键列表 = [
            键 for 键 in list(self._GPU界面纹理缓存.keys()) if int(键[0]) == 图id
        ]
        for 键 in 删除键列表:
            self._GPU界面纹理缓存.pop(键, None)

    def _绘制GPU图层(
        self,
        渲染器,
        图层: pygame.Surface | None,
        目标矩形: tuple[int, int, int, int] | None = None,
        alpha: int = 255,
        比例x: float = 1.0,
        比例y: float = 1.0,
    ):
        if 图层 is None:
            return
        纹理 = self._取GPU界面纹理(渲染器, 图层)
        if 纹理 is None:
            return
        try:
            比例x = max(0.001, float(比例x))
        except Exception:
            比例x = 1.0
        try:
            比例y = max(0.001, float(比例y))
        except Exception:
            比例y = 1.0
        try:
            纹理.alpha = int(max(0, min(255, alpha)))
        except Exception:
            pass
        try:
            纹理.color = (255, 255, 255)
        except Exception:
            pass
        try:
            纹理.blend_mode = 1
        except Exception:
            pass
        if 目标矩形 is None:
            目标矩形 = (
                0,
                0,
                int(max(1, 图层.get_width())),
                int(max(1, 图层.get_height())),
            )
        try:
            渲染目标矩形 = (
                int(round(float(目标矩形[0]) * 比例x)),
                int(round(float(目标矩形[1]) * 比例y)),
                max(1, int(round(float(目标矩形[2]) * 比例x))),
                max(1, int(round(float(目标矩形[3]) * 比例y))),
            )
        except Exception:
            渲染目标矩形 = (
                int(目标矩形[0]),
                int(目标矩形[1]),
                max(1, int(目标矩形[2])),
                max(1, int(目标矩形[3])),
            )
        try:
            纹理.draw(dstrect=渲染目标矩形)
        except Exception:
            pass

    @staticmethod
    def _按中心缩放矩形(基准框: pygame.Rect, 缩放倍率: float) -> pygame.Rect:
        缩放倍率 = float(max(0.01, 缩放倍率))
        if abs(缩放倍率 - 1.0) <= 0.001:
            return pygame.Rect(基准框)
        目标宽 = max(1, int(round(float(基准框.w) * 缩放倍率)))
        目标高 = max(1, int(round(float(基准框.h) * 缩放倍率)))
        return pygame.Rect(
            int(round(float(基准框.centerx) - float(目标宽) * 0.5)),
            int(round(float(基准框.centery) - float(目标高) * 0.5)),
            int(目标宽),
            int(目标高),
        )

    def _绘制GPU按钮(
        self,
        渲染器,
        图片: pygame.Surface | None,
        基准框: pygame.Rect,
        点击特效: 公用按钮点击特效 | None,
        是否悬停: bool,
        是否选中: bool,
        比例x: float = 1.0,
        比例y: float = 1.0,
    ):
        if 图片 is None:
            return
        del 点击特效, 是否悬停, 是否选中
        目标框 = pygame.Rect(基准框)
        self._绘制GPU图层(
            渲染器,
            图片,
            (目标框.x, 目标框.y, 目标框.w, 目标框.h),
            alpha=255,
            比例x=float(比例x),
            比例y=float(比例y),
        )

    def _着色副本(
        self,
        图层: pygame.Surface | None,
        颜色: tuple[int, int, int],
        总透明度: int | None = None,
    ) -> pygame.Surface | None:
        if 图层 is None:
            return None
        结果 = 图层.copy()
        try:
            结果.fill(
                (int(颜色[0]), int(颜色[1]), int(颜色[2]), 255),
                special_flags=pygame.BLEND_RGBA_MULT,
            )
        except Exception:
            pass
        if 总透明度 is not None:
            try:
                结果.set_alpha(max(0, min(255, int(总透明度))))
            except Exception:
                pass
        return 结果

    def _重建logo实时特效条目(self):
        self._logo电弧条目 = []
        self._logo长弧条目 = []
        self._logo闪点条目 = []
        self._logo切片条目 = []

        轮廓数 = len(self._logo轮廓点)
        if 轮廓数 >= 8:
            细碎条数 = max(12, min(24, max(轮廓数 // 10, 12)))
            for i in range(细碎条数):
                self._logo电弧条目.append(
                    {
                        "索引": int((i * 37) % 轮廓数),
                        "phase": float(i) * 0.63,
                        "speed": 2.0 + float(i % 5) * 0.24,
                    }
                )

            长弧条数 = max(4, min(8, max(轮廓数 // 64, 4)))
            for i in range(长弧条数):
                self._logo长弧条目.append(
                    {
                        "起点索引": int((i * 53 + 7) % 轮廓数),
                        "终点偏移": int(
                            max(轮廓数 * 0.26, min(轮廓数 * 0.52, 轮廓数 * (0.28 + (i % 3) * 0.08)))
                        ),
                        "phase": float(i) * 0.91,
                        "speed": 1.12 + float(i % 4) * 0.18,
                    }
                )

        采样数 = len(self._logo内部采样点)
        if 采样数 <= 0:
            return
        闪点条数 = max(12, min(26, max(采样数 // 4, 12)))
        for i in range(闪点条数):
            self._logo闪点条目.append(
                {
                    "索引": int((i * 19 + 3) % 采样数),
                    "phase": float(i) * 0.42,
                    "speed": 0.92 + float(i % 5) * 0.11,
                }
            )

        for i, (顶部, 高度, 基础) in enumerate(
            (
                (0.13, 0.08, -12.0),
                (0.27, 0.06, 8.0),
                (0.44, 0.07, -6.0),
                (0.61, 0.06, 10.0),
                (0.79, 0.08, -9.0),
            )
        ):
            self._logo切片条目.append(
                {
                    "top": float(顶部),
                    "height": float(高度),
                    "base": float(基础),
                    "phase": float(i) * 0.57,
                }
            )

    def _取logo活跃秒(self, 当前时间: float) -> float:
        if float(self._logo登场开始时间) > 0.0:
            return max(0.0, float(当前时间) - float(self._logo登场开始时间))
        return max(0.0, float(当前时间) - float(self._开始时间))

    def _失效logo登场缓存(self):
        self._清理GPU界面纹理(getattr(self, "_logo登场缓存面", None))
        self._logo登场缓存面 = None
        self._logo登场缓存尺寸 = (0, 0)
        self._logo登场缓存帧 = -1

    def _失效logo实时特效缓存(self):
        self._logo实时特效缓存尺寸 = (0, 0)
        self._logo实时特效缓存帧 = -1
        self._logo实时特效缓存模式 = ""

    def _清空logo实时叠加层(self, 重置: bool = False):
        叠加层 = getattr(self, "_logo实时叠加层", None)
        if 叠加层 is None:
            return
        self._失效logo实时特效缓存()
        if bool(重置):
            try:
                叠加层.重置()
            except Exception:
                return
        try:
            叠加层.清空(清除画布=True)
        except Exception:
            pass

    def _取logo局部框(self, 局部区域: pygame.Rect) -> pygame.Rect:
        return self._logo_rect.move(-局部区域.x, -局部区域.y)

    def _应用logo局部蒙版(self, 图层: pygame.Surface, 局部区域: pygame.Rect):
        if 图层 is None or self._logo遮罩图 is None:
            return
        try:
            蒙版图层 = pygame.Surface(图层.get_size(), pygame.SRCALPHA)
            蒙版图层.blit(self._logo遮罩图, self._取logo局部框(局部区域).topleft)
            图层.blit(蒙版图层, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        except Exception:
            pass

    def _创建后处理暗角图(self, 尺寸: tuple[int, int]) -> pygame.Surface:
        宽, 高 = max(1, int(尺寸[0])), max(1, int(尺寸[1]))
        图层 = pygame.Surface((宽, 高), pygame.SRCALPHA)
        最短边 = max(1, min(宽, 高))
        边框宽 = max(20, int(最短边 * 0.02))
        for i in range(6):
            inset = int(i * 最短边 * 0.03)
            rect = pygame.Rect(
                inset,
                inset,
                max(1, 宽 - inset * 2),
                max(1, 高 - inset * 2),
            )
            alpha = int(14 + i * 10)
            try:
                pygame.draw.rect(
                    图层,
                    (0, 8, 20, alpha),
                    rect,
                    width=max(2, 边框宽),
                    border_radius=max(18, int(最短边 * 0.045)),
                )
            except Exception:
                pass
        return 图层

    def _生成logo粒子种子(self) -> list[dict]:
        结果: list[dict] = []
        总数 = 22
        for i in range(总数):
            角度 = (float(i) / float(总数)) * math.tau + math.sin(float(i) * 1.73) * 0.28
            结果.append(
                {
                    "角度": 角度,
                    "延迟": float(i % 6) * 0.035 + (0.018 if (i % 2) else 0.0),
                    "寿命": 0.46 + float(i % 5) * 0.075,
                    "速度": 0.32 + float((i * 17) % 9) * 0.085,
                    "尺寸": 1 + (i % 3),
                    "拖尾": 18 + (i % 4) * 9,
                    "横向": 0.92 + float((i * 11) % 5) * 0.07,
                    "纵向": 0.70 + float((i * 7) % 4) * 0.06,
                    "闪烁": 0.85 + float((i * 13) % 7) * 0.12,
                    "色相": i % 3,
                }
            )
        return 结果

    def _创建扫描带图(
        self,
        尺寸: tuple[int, int],
        中心x: float,
        基础宽: float,
    ) -> pygame.Surface:
        宽, 高 = max(1, int(尺寸[0])), max(1, int(尺寸[1]))
        图层 = pygame.Surface((宽, 高), pygame.SRCALPHA)
        偏移 = max(18, int(高 * 0.52))

        def _画带(宽倍率: float, alpha: int, 颜色: tuple[int, int, int]):
            半宽 = max(4, int(float(基础宽) * float(宽倍率) * 0.5))
            点列 = [
                (int(中心x) - 半宽 - 偏移, 0),
                (int(中心x) + 半宽 - 偏移, 0),
                (int(中心x) + 半宽 + 偏移, 高),
                (int(中心x) - 半宽 + 偏移, 高),
            ]
            try:
                pygame.draw.polygon(图层, (*颜色, int(alpha)), 点列)
            except Exception:
                pass

        _画带(0.78, 18, (26, 116, 255))
        _画带(0.28, 52, (82, 224, 255))
        _画带(0.11, 96, (255, 255, 255))
        return 图层

    def _绘制发光点(
        self,
        图层: pygame.Surface,
        位置: tuple[int, int],
        半径: int,
        颜色: tuple[int, int, int],
        alpha: int,
    ):
        alpha = max(0, min(255, int(alpha)))
        半径 = max(1, int(半径))
        if alpha <= 1:
            return
        try:
            pygame.draw.circle(图层, (*颜色, int(alpha * 0.16)), 位置, max(2, int(半径 * 2.8)))
            pygame.draw.circle(图层, (*颜色, int(alpha * 0.34)), 位置, max(2, int(半径 * 1.8)))
            pygame.draw.circle(图层, (*颜色, alpha), 位置, 半径)
        except Exception:
            pass

    def _绘制渐变发光线(
        self,
        图层: pygame.Surface,
        起点: tuple[int, int],
        终点: tuple[int, int],
        起始颜色: tuple[int, int, int],
        结束颜色: tuple[int, int, int],
        alpha: int,
        线宽: int,
    ):
        alpha = max(0, min(255, int(alpha)))
        线宽 = max(1, int(线宽))
        if alpha <= 1:
            return

        x1, y1 = float(起点[0]), float(起点[1])
        x2, y2 = float(终点[0]), float(终点[1])
        距离 = math.hypot(x2 - x1, y2 - y1)
        分段 = max(2, min(8, int(距离 / 42.0)))
        for i in range(分段):
            t0 = float(i) / float(分段)
            t1 = float(i + 1) / float(分段)
            p0 = (
                int(x1 + (x2 - x1) * t0),
                int(y1 + (y2 - y1) * t0),
            )
            p1 = (
                int(x1 + (x2 - x1) * t1),
                int(y1 + (y2 - y1) * t1),
            )
            颜色 = _颜色插值(起始颜色, 结束颜色, (t0 + t1) * 0.5)
            亮色 = _颜色插值(颜色, (255, 255, 255), 0.42)
            try:
                pygame.draw.line(图层, (*颜色, int(alpha * 0.18)), p0, p1, max(2, int(线宽 * 2.6)))
                pygame.draw.line(图层, (*颜色, int(alpha * 0.38)), p0, p1, max(2, int(线宽 * 1.7)))
                pygame.draw.line(图层, (*亮色, alpha), p0, p1, 线宽)
            except Exception:
                pass

    def _绘制logo最终状态(
        self,
        图层: pygame.Surface,
        位置: tuple[int, int],
        外描边alpha: int = 88,
        贴图alpha: int = 255,
    ):
        if self._logo图 is None:
            return

        if int(贴图alpha) >= 254:
            图层.blit(self._logo图, 位置)
            return

        最终 = self._logo图.copy()
        try:
            最终.set_alpha(max(0, min(255, int(贴图alpha))))
        except Exception:
            pass
        图层.blit(最终, 位置)

    def _裁剪到logo蒙版(self, 图层: pygame.Surface) -> pygame.Surface:
        if self._logo遮罩图 is None:
            return 图层
        try:
            图层.blit(self._logo遮罩图, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        except Exception:
            pass
        return 图层

    def _构建logo显现遮罩(self, 动画秒: float) -> pygame.Surface | None:
        if self._logo图 is None:
            return None
        logo尺寸 = (self._logo_rect.w, self._logo_rect.h)
        遮罩 = pygame.Surface(logo尺寸, pygame.SRCALPHA)
        主体进度 = _区间进度(float(动画秒), 1.02, 1.42)
        if 主体进度 <= 0.0:
            return 遮罩
        try:
            遮罩.fill((255, 255, 255, int(255 * _缓入出(主体进度))))
        except Exception:
            pass
        return 遮罩

    def _触发logo登场动画(self):
        if not self._logo图:
            return
        self._logo登场开始时间 = time.time()
        self._失效logo登场缓存()
        self._清空logo实时叠加层()

    def _取logo动画参数(self, 当前时间: float) -> dict:
        if (not self._是否显示logo) or (self._logo图 is None):
            return {"进行中": False, "动画秒": 999.0, "进度": 1.0}
        if float(self._logo登场开始时间) <= 0.0:
            return {"进行中": False, "动画秒": 999.0, "进度": 1.0}
        动画秒 = max(0.0, float(当前时间) - float(self._logo登场开始时间))
        进度 = _限幅(动画秒 / float(self._logo登场总时长))
        return {
            "进行中": bool(动画秒 < float(self._logo登场总时长)),
            "动画秒": 动画秒,
            "进度": 进度,
        }

    def _重建logo特效缓存(self, 屏幕尺寸: tuple[int, int]):
        self._logo遮罩图 = None
        self._logo柔光图 = None
        self._logo柔光偏移 = (0, 0)
        self._logo外描边图 = None
        self._logo外描边偏移 = (0, 0)
        self._logo红偏图 = None
        self._logo青偏图 = None
        self._logo柔光红图 = None
        self._logo柔光青图 = None
        self._logo描边青图 = None
        self._logo描边红图 = None
        self._logo轮廓点 = []
        self._logo内部采样点 = []
        self._logo电弧条目 = []
        self._logo长弧条目 = []
        self._logo闪点条目 = []
        self._logo切片条目 = []

        屏宽, 屏高 = max(1, int(屏幕尺寸[0])), max(1, int(屏幕尺寸[1]))
        屏幕矩形 = pygame.Rect(0, 0, 屏宽, 屏高)
        self._logo局部特效区域 = self._logo_rect.inflate(
            max(360, int(self._logo_rect.w * 0.90)),
            max(320, int(self._logo_rect.h * 1.15)),
        ).clip(屏幕矩形)
        self._后处理暗角图 = self._创建后处理暗角图((屏宽, 屏高))

        if self._logo图 is None:
            return

        try:
            蒙版 = pygame.mask.from_surface(self._logo图, threshold=8)
            self._logo遮罩图 = 蒙版.to_surface(
                setcolor=(255, 255, 255, 255),
                unsetcolor=(0, 0, 0, 0),
            ).convert_alpha()

            发光边距 = max(24, int(max(self._logo_rect.w, self._logo_rect.h) * 0.08))
            发光画布 = pygame.Surface(
                (self._logo_rect.w + 发光边距 * 2, self._logo_rect.h + 发光边距 * 2),
                pygame.SRCALPHA,
            )
            发光画布.blit(self._logo遮罩图, (发光边距, 发光边距))
            柔光 = self._近似模糊(发光画布, 0.18)
            self._logo柔光图 = self._近似模糊(柔光, 0.52)
            self._logo柔光偏移 = (-发光边距, -发光边距)
            self._logo柔光红图 = self._着色副本(self._logo柔光图, (255, 112, 192))
            self._logo柔光青图 = self._着色副本(self._logo柔光图, (90, 236, 255))

            轮廓 = list(蒙版.outline() or [])
            if 轮廓:
                步长 = max(1, len(轮廓) // 260)
                半宽 = max(1.0, float(self._logo_rect.w) * 0.5)
                半高 = max(1.0, float(self._logo_rect.h) * 0.5)
                对角总长 = max(1.0, float(self._logo_rect.w) + float(self._logo_rect.h) * 0.82)
                for x, y in 轮廓[::步长]:
                    dx = float(x) - 半宽
                    dy = float(y) - 半高
                    法线长 = math.hypot(dx, dy) or 1.0
                    self._logo轮廓点.append(
                        (
                            int(x),
                            int(y),
                            _限幅((float(x) + float(y) * 0.82) / 对角总长),
                            _限幅(math.hypot(dx / 半宽, dy / 半高), 0.0, 1.8),
                            dx / 法线长,
                            dy / 法线长,
                        )
                    )

                采样间距 = max(14, int(min(self._logo_rect.w, self._logo_rect.h) * 0.045))
                for y in range(max(采样间距 // 2, 1), self._logo_rect.h, 采样间距):
                    行偏移 = (y // max(1, 采样间距)) % 2
                    起始x = max(采样间距 // 2, 1) + 行偏移 * (采样间距 // 2)
                    for x in range(起始x, self._logo_rect.w, 采样间距):
                        if not 蒙版.get_at((int(x), int(y))):
                            continue
                        dx = (float(x) - 半宽) / 半宽
                        dy = (float(y) - 半高) / 半高
                        self._logo内部采样点.append(
                            (
                                int(x),
                                int(y),
                                _限幅((float(x) + float(y) * 0.82) / 对角总长),
                                _限幅(math.hypot(dx, dy), 0.0, 1.8),
                            )
                        )
            self._logo红偏图 = self._着色副本(self._logo图, (255, 118, 206))
            self._logo青偏图 = self._着色副本(self._logo图, (116, 238, 255))
            self._重建logo实时特效条目()
        except Exception:
            self._logo遮罩图 = None
            self._logo柔光图 = None
            self._logo外描边偏移 = (0, 0)
            self._logo外描边图 = None
            self._logo红偏图 = None
            self._logo青偏图 = None
            self._logo柔光红图 = None
            self._logo柔光青图 = None
            self._logo描边青图 = None
            self._logo描边红图 = None
            self._logo轮廓点 = []
            self._logo内部采样点 = []
            self._logo电弧条目 = []
            self._logo长弧条目 = []
            self._logo闪点条目 = []
            self._logo切片条目 = []

    def _确保缓存(self):
        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()
        if (宽, 高) == self._缓存尺寸:
            return
        self._缓存尺寸 = (宽, 高)
        self._中心缩放缓存 = {}
        self._失效logo登场缓存()
        self._清空logo实时叠加层(重置=True)

        暗层 = pygame.Surface((宽, 高), pygame.SRCALPHA)
        暗层.fill((0, 0, 0, 128))
        self._遮罩图 = 暗层

        self._logo_rect = self._映射到屏幕_rect(self._bbox_logo)
        self._logo图 = (
            pygame.transform.smoothscale(
                self._logo原图,
                (self._logo_rect.w, self._logo_rect.h),
            ).convert_alpha()
            if self._logo原图
            else None
        )
        self._重建logo特效缓存((宽, 高))

        self._1p_rect = self._映射到屏幕_rect(self._bbox_1p)
        self._2p_rect = self._映射到屏幕_rect(self._bbox_2p)

        self._1p图 = (
            pygame.transform.smoothscale(
                self._1p原图, (self._1p_rect.w, self._1p_rect.h)
            ).convert_alpha()
            if self._1p原图
            else None
        )
        self._2p图 = (
            pygame.transform.smoothscale(
                self._2p原图, (self._2p_rect.w, self._2p_rect.h)
            ).convert_alpha()
            if self._2p原图
            else None
        )

        hover倍率 = 1.04
        if self._1p图:
            hover宽 = max(1, int(self._1p_rect.w * hover倍率))
            hover高 = max(1, int(self._1p_rect.h * hover倍率))
            self._1p图_hover = pygame.transform.smoothscale(
                self._1p图, (hover宽, hover高)
            ).convert_alpha()
        else:
            self._1p图_hover = None

        if self._2p图:
            hover宽 = max(1, int(self._2p_rect.w * hover倍率))
            hover高 = max(1, int(self._2p_rect.h * hover倍率))
            self._2p图_hover = pygame.transform.smoothscale(
                self._2p图, (hover宽, hover高)
            ).convert_alpha()
        else:
            self._2p图_hover = None

    def _绘制logo背景层(self, 屏幕: pygame.Surface, 当前时间: float, 动画参数: dict):
        if (not bool(动画参数.get("进行中", False))) or self._logo_rect.w <= 1:
            return

        宽, 高 = 屏幕.get_size()
        中心x, 中心y = self._logo_rect.center
        动画秒 = float(动画参数.get("动画秒", 999.0) or 999.0)
        蓄能 = _区间进度(动画秒, 0.00, 0.92)
        冲击 = _区间脉冲(动画秒, 0.92, 1.07, 1.22)
        退场 = 1.0 - _区间进度(动画秒, 1.02, 1.28)
        强度 = max(0.0, (0.18 + 0.82 * max(蓄能, 冲击)) * 退场)
        if 强度 <= 0.01:
            return

        图层 = pygame.Surface((宽, 高), pygame.SRCALPHA)
        图层.fill((3, 8, 20, int(12 + 24 * 强度)))

        for 比例, alpha, 颜色 in (
            (0.11, 86, (92, 228, 255)),
            (0.19, 54, (38, 122, 255)),
            (0.31, 24, (10, 28, 84)),
        ):
            半径 = int(
                min(宽, 高)
                * 比例
                * (0.64 + 0.38 * 蓄能 + 0.28 * 冲击)
            )
            try:
                pygame.draw.circle(
                    图层,
                    (*颜色, int(alpha * (0.24 + 强度 * 0.76))),
                    (中心x, 中心y),
                    max(8, 半径),
                )
            except Exception:
                pass

        最大半径 = math.hypot(float(宽), float(高)) * 0.86
        线数 = 30
        for i in range(线数):
            角度 = (float(i) / float(线数)) * math.tau + math.sin(float(i) * 1.37) * 0.10
            相位 = (当前时间 * (1.10 + float(i % 4) * 0.13) + float(i) * 0.083) % 1.0
            起始半径 = (0.02 + 相位 * 0.08) * 最大半径
            结束半径 = (0.28 + 相位 * 0.72) * 最大半径
            alpha = int(pow(1.0 - 相位, 1.55) * (34 + 强度 * 116 + 冲击 * 36))
            线宽 = max(1, int(1 + (1.0 - 相位) * 1.9 + 冲击 * 1.0))
            起始颜色 = _颜色插值((14, 78, 206), (72, 204, 255), 0.28 + (1.0 - 相位) * 0.46)
            结束颜色 = _颜色插值((90, 228, 255), (255, 255, 255), 0.18 + 冲击 * 0.52)
            x1 = int(中心x + math.cos(角度) * 起始半径)
            y1 = int(中心y + math.sin(角度) * 起始半径 * 0.64)
            x2 = int(中心x + math.cos(角度) * 结束半径)
            y2 = int(中心y + math.sin(角度) * 结束半径 * 0.64)
            self._绘制渐变发光线(
                图层,
                (x1, y1),
                (x2, y2),
                起始颜色,
                结束颜色,
                alpha,
                线宽,
            )
            点t = 0.22 + 相位 * 0.62
            点x = int(x1 + (x2 - x1) * 点t)
            点y = int(y1 + (y2 - y1) * 点t)
            self._绘制发光点(
                图层,
                (点x, 点y),
                max(2, int(1 + 线宽 * 0.6)),
                结束颜色,
                int(alpha * (0.46 + 蓄能 * 0.22)),
            )

        柔光 = self._近似模糊(图层, 0.24)
        try:
            柔光.set_alpha(int(18 + 34 * 强度 + 10 * 冲击))
        except Exception:
            pass
        屏幕.blit(柔光, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        屏幕.blit(图层, (0, 0))

    def _绘制logo爆闪层(
        self,
        图层: pygame.Surface,
        局部区域: pygame.Rect,
        动画参数: dict,
    ):
        if not bool(动画参数.get("进行中", False)):
            return

        动画秒 = float(动画参数.get("动画秒", 999.0) or 999.0)
        爆闪强度 = _区间脉冲(动画秒, 0.94, 1.08, 1.22)
        if 爆闪强度 <= 0.0:
            return

        中心x = int(self._logo_rect.centerx - 局部区域.x)
        中心y = int(self._logo_rect.centery - 局部区域.y)
        最短边 = min(max(1, 局部区域.w), max(1, 局部区域.h))
        外扩 = 0.08 + 爆闪强度 * 0.24

        for 半径, 颜色, alpha in (
            (int(最短边 * (0.05 + 外扩 * 0.35)), (255, 255, 255), int(220 * 爆闪强度)),
            (int(最短边 * (0.10 + 外扩 * 0.56)), (182, 238, 255), int(132 * 爆闪强度)),
            (int(最短边 * (0.16 + 外扩 * 0.70)), (64, 154, 255), int(64 * 爆闪强度)),
        ):
            try:
                pygame.draw.circle(图层, (*颜色, alpha), (中心x, 中心y), max(8, 半径))
            except Exception:
                pass

        横光 = pygame.Rect(
            0,
            0,
            int(局部区域.w * (0.14 + 爆闪强度 * 0.48)),
            max(8, int(12 + 28 * 爆闪强度)),
        )
        横光.center = (中心x, 中心y)
        竖光 = pygame.Rect(
            0,
            0,
            max(6, int(8 + 14 * 爆闪强度)),
            int(局部区域.h * (0.12 + 爆闪强度 * 0.18)),
        )
        竖光.center = (中心x, 中心y)
        try:
            pygame.draw.ellipse(图层, (255, 255, 255, int(180 * 爆闪强度)), 横光)
            pygame.draw.ellipse(图层, (132, 224, 255, int(92 * 爆闪强度)), 竖光)
            pygame.draw.line(
                图层,
                (235, 248, 255, int(168 * 爆闪强度)),
                (横光.left, 中心y),
                (横光.right, 中心y),
                max(1, int(2 + 3 * 爆闪强度)),
            )
        except Exception:
            pass

    def _绘制logo显现层(
        self,
        图层: pygame.Surface,
        局部区域: pygame.Rect,
        当前时间: float,
        动画参数: dict,
    ):
        if self._logo图 is None:
            return

        logo局部框 = self._logo_rect.move(-局部区域.x, -局部区域.y)
        logo尺寸 = (self._logo_rect.w, self._logo_rect.h)
        动画中 = bool(动画参数.get("进行中", False))
        动画秒 = float(动画参数.get("动画秒", 999.0) or 999.0)
        爆闪强度 = _区间脉冲(动画秒, 0.94, 1.06, 1.18)
        弹跳进度 = _区间进度(动画秒, 1.00, 1.56)

        if not 动画中:
            self._绘制logo最终状态(图层, logo局部框.topleft, 贴图alpha=255)
            return

        if 弹跳进度 <= 0.0:
            return

        if 弹跳进度 < 0.42:
            局部进度 = _缓出三次(弹跳进度 / 0.42)
            缩放倍率 = 0.82 + (1.13 - 0.82) * 局部进度
        else:
            局部进度 = _缓入出((弹跳进度 - 0.42) / 0.58)
            缩放倍率 = 1.13 + (1.00 - 1.13) * 局部进度

        透明度 = max(0, min(255, int(255 * _缓入出(min(1.0, 弹跳进度 * 1.8)))))
        if 爆闪强度 > 0.0:
            透明度 = max(透明度, int(140 + 100 * 爆闪强度))

        目标宽 = max(1, int(float(logo尺寸[0]) * 缩放倍率))
        目标高 = max(1, int(float(logo尺寸[1]) * 缩放倍率))
        贴图 = pygame.transform.smoothscale(self._logo图, (目标宽, 目标高)).convert_alpha()
        try:
            贴图.set_alpha(透明度)
        except Exception:
            pass
        贴图框 = 贴图.get_rect(center=logo局部框.center)
        图层.blit(贴图, 贴图框.topleft)

    def _绘制logo粒子层(
        self,
        图层: pygame.Surface,
        局部区域: pygame.Rect,
        当前时间: float,
        动画参数: dict,
    ):
        if not bool(动画参数.get("进行中", False)):
            return

        动画秒 = float(动画参数.get("动画秒", 999.0) or 999.0)
        if 动画秒 < 0.34 or 动画秒 > 1.10:
            return

        中心x = float(self._logo_rect.centerx - 局部区域.x)
        中心y = float(self._logo_rect.centery - 局部区域.y)
        尺寸基准 = float(max(64, min(self._logo_rect.w, self._logo_rect.h)))
        蓄能 = _区间进度(动画秒, 0.34, 1.00)
        白闪强度 = _区间脉冲(动画秒, 0.96, 1.08, 1.20)
        展示衰减 = 1.0 - _区间进度(动画秒, 0.96, 1.10)

        for i, 粒子 in enumerate(self._logo粒子种子):
            起始 = 0.42 + float(粒子["延迟"]) * 0.90
            寿命 = 0.54 + float(粒子["寿命"]) * 0.55
            局部时间 = (动画秒 - 起始) / max(0.001, 寿命)
            if 局部时间 <= 0.0 or 局部时间 >= 1.0:
                continue

            进度 = _限幅(局部时间)
            位移进度 = _缓出三次(进度)
            角度 = float(粒子["角度"]) + math.sin(
                当前时间 * (2.0 + float(粒子["闪烁"])) + float(i) * 0.41
            ) * 0.12
            if 动画秒 < 1.08:
                外圈 = 0.74 + float(粒子["速度"]) * 0.32
                内圈 = 0.12 + 白闪强度 * 0.06
                距离 = 尺寸基准 * (外圈 - 位移进度 * (外圈 - 内圈))
            else:
                距离 = 尺寸基准 * (
                    0.12 + 位移进度 * (0.22 + float(粒子["速度"]) * 0.40)
                )
            x = 中心x + math.cos(角度) * 距离 * float(粒子["横向"])
            y = 中心y + math.sin(角度) * 距离 * float(粒子["纵向"])
            拖尾长 = float(粒子["拖尾"]) * (
                (1.16 - 进度 * 0.42) if 动画秒 < 1.08 else (0.76 - 进度 * 0.24)
            )
            if 动画秒 < 1.08:
                尾x = x + math.cos(角度) * 拖尾长
                尾y = y + math.sin(角度) * 拖尾长 * 0.84
            else:
                尾x = x - math.cos(角度) * 拖尾长
                尾y = y - math.sin(角度) * 拖尾长 * 0.84
            alpha = int(
                pow(1.0 - 进度, 1.55)
                * (48 + 82 * 蓄能 + 122 * 白闪强度 + 66 * 展示衰减)
            )
            alpha = max(0, min(255, alpha))
            if alpha <= 2:
                continue

            if int(粒子["色相"]) == 0:
                颜色 = (110, 228, 255)
            elif int(粒子["色相"]) == 1:
                颜色 = (255, 255, 255)
            else:
                颜色 = (92, 166, 255)

            try:
                pygame.draw.line(
                    图层,
                    (*颜色, int(alpha * 0.42)),
                    (int(尾x), int(尾y)),
                    (int(x), int(y)),
                    max(1, int(1 + float(粒子["尺寸"]) * 0.35)),
                )
                pygame.draw.circle(
                    图层,
                    (*颜色, alpha),
                    (int(x), int(y)),
                    max(1, int(粒子["尺寸"])),
                )
            except Exception:
                pass

    def _应用logo后处理(
        self,
        屏幕: pygame.Surface,
        局部层: pygame.Surface,
        局部区域: pygame.Rect,
        当前时间: float,
        动画参数: dict,
    ):
        动画中 = bool(动画参数.get("进行中", False))
        动画秒 = float(动画参数.get("动画秒", 999.0) or 999.0)
        白闪强度 = _区间脉冲(动画秒, 0.96, 1.08, 1.20)
        if (not 动画中) or 动画秒 > 1.18:
            屏幕.blit(局部层, (局部区域.x, 局部区域.y))
            return

        强度 = max(0.0, 1.0 - _区间进度(动画秒, 1.02, 1.18))

        震动 = 0.0
        if 动画中:
            震动 = 1.2 * 白闪强度 + 1.8 * pow(max(0.0, 1.0 - _区间进度(动画秒, 1.00, 1.14)), 2.0)
        偏移x = int(round(math.sin(当前时间 * 41.0) * 震动))
        偏移y = int(round(math.cos(当前时间 * 33.0) * 震动 * 0.64))
        绘制位置 = (局部区域.x + 偏移x, 局部区域.y + 偏移y)

        泛光 = self._近似模糊(局部层, 0.18)
        try:
            泛光.set_alpha(int(24 + 46 * 强度 + 64 * 白闪强度))
        except Exception:
            pass
        屏幕.blit(泛光, 绘制位置, special_flags=pygame.BLEND_RGBA_ADD)

        屏幕.blit(局部层, 绘制位置)

    def _取logo登场缓存(
        self,
        当前时间: float,
        屏幕尺寸: tuple[int, int],
    ) -> pygame.Surface | None:
        if (not self._是否显示logo) or (self._logo图 is None):
            self._失效logo登场缓存()
            return None

        动画参数 = self._取logo动画参数(当前时间)
        if not bool(动画参数.get("进行中", False)):
            self._失效logo登场缓存()
            return None

        帧率 = max(
            1.0,
            float(getattr(self, "_logo登场缓存帧率", 24.0) or 24.0),
        )
        动画秒 = max(0.0, float(动画参数.get("动画秒", 0.0) or 0.0))
        帧序号 = int(动画秒 * 帧率)
        缓存面 = getattr(self, "_logo登场缓存面", None)
        if (
            isinstance(缓存面, pygame.Surface)
            and tuple(getattr(self, "_logo登场缓存尺寸", (0, 0))) == tuple(屏幕尺寸)
            and int(getattr(self, "_logo登场缓存帧", -1)) == int(帧序号)
        ):
            return 缓存面

        try:
            self._清理GPU界面纹理(缓存面)
            缓存面 = pygame.Surface(屏幕尺寸, pygame.SRCALPHA, 32).convert_alpha()
        except Exception:
            缓存面 = pygame.Surface(屏幕尺寸, pygame.SRCALPHA)

        采样动画秒 = min(float(self._logo登场总时长), float(帧序号) / 帧率)
        采样时间 = float(self._logo登场开始时间 or 当前时间) + 采样动画秒
        采样参数 = self._取logo动画参数(采样时间)

        self._绘制logo背景层(缓存面, 采样时间, 采样参数)

        局部区域 = self._logo局部特效区域.clip(pygame.Rect(0, 0, *屏幕尺寸))
        if 局部区域.w <= 0 or 局部区域.h <= 0:
            self._绘制logo最终状态(缓存面, self._logo_rect.topleft, 贴图alpha=255)
            self._logo登场缓存面 = 缓存面
            self._logo登场缓存尺寸 = tuple(屏幕尺寸)
            self._logo登场缓存帧 = int(帧序号)
            return 缓存面

        局部层 = pygame.Surface((局部区域.w, 局部区域.h), pygame.SRCALPHA)
        self._绘制logo爆闪层(局部层, 局部区域, 采样参数)
        self._绘制logo显现层(局部层, 局部区域, 采样时间, 采样参数)
        self._绘制logo粒子层(局部层, 局部区域, 采样时间, 采样参数)
        self._应用logo后处理(缓存面, 局部层, 局部区域, 采样时间, 采样参数)
        self._logo登场缓存面 = 缓存面
        self._logo登场缓存尺寸 = tuple(屏幕尺寸)
        self._logo登场缓存帧 = int(帧序号)
        return 缓存面

    def _绘制logo登场效果(self, 屏幕: pygame.Surface, 当前时间: float):
        if (not self._是否显示logo) or (self._logo图 is None):
            self._失效logo登场缓存()
            return

        缓存面 = self._取logo登场缓存(当前时间, 屏幕.get_size())
        if isinstance(缓存面, pygame.Surface):
            屏幕.blit(缓存面, (0, 0))
            return

        self._绘制logo最终状态(屏幕, self._logo_rect.topleft, 贴图alpha=255)

    def _绘制logo发光折线(
        self,
        图层: pygame.Surface,
        点列: list[tuple[int, int]],
        颜色: tuple[int, int, int],
        alpha: int,
        线宽: float,
    ):
        if 图层 is None or len(点列) < 2:
            return
        alpha = max(0, min(255, int(alpha)))
        if alpha <= 2:
            return
        颜色 = tuple(int(max(0, min(255, v))) for v in 颜色[:3])
        亮色 = _颜色插值(颜色, (255, 255, 255), 0.48)
        核心宽 = max(1, int(round(float(线宽))))
        内层宽 = max(2, int(round(float(线宽) * 1.7)))
        外层宽 = max(2, int(round(float(线宽) * 2.6)))
        for 索引 in range(len(点列) - 1):
            起点 = 点列[索引]
            终点 = 点列[索引 + 1]
            try:
                pygame.draw.line(图层, (*颜色, int(alpha * 0.18)), 起点, 终点, 外层宽)
                pygame.draw.line(图层, (*颜色, int(alpha * 0.36)), 起点, 终点, 内层宽)
                pygame.draw.line(图层, (*亮色, alpha), 起点, 终点, 核心宽)
            except Exception:
                pass

    def _绘制logo实时色偏层(self, 画布: pygame.Surface, 活跃秒: float):
        return

    def _绘制logo实时切片层(self, 画布: pygame.Surface, 活跃秒: float):
        return

    def _绘制logo实时扫光层(
        self,
        画布: pygame.Surface,
        局部区域: pygame.Rect,
        活跃秒: float,
    ):
        总时长 = float(self._logo实时特效总时长)
        常驻尾段 = (
            1.0
            if 活跃秒 > 总时长
            else _区间进度(活跃秒, 总时长 - 0.45, 总时长 + 0.40)
        )
        主扫循环 = _周期脉冲(活跃秒, 3.26, 2.55, 0.08, 0.24, 0.46)
        次扫循环 = _周期脉冲(活跃秒, 3.86, 2.55, 0.04, 0.15, 0.28)
        主强度 = max(
            _区间进度(活跃秒, 3.32, 4.00)
            + 主扫循环 * max(_区间进度(活跃秒, 4.00, 6.40), 常驻尾段),
            常驻尾段 * (0.26 + 主扫循环 * 0.92),
        )
        次强度 = max(
            _区间脉冲(活跃秒, 3.54, 3.82, 4.18) * 0.86,
            次扫循环 * max(_区间进度(活跃秒, 4.12, 6.30), 常驻尾段) * 0.82,
            常驻尾段 * (0.16 + 次扫循环 * 0.82),
        )
        if max(主强度, 次强度) <= 0.01:
            return

        logo局部框 = self._取logo局部框(局部区域)
        for 强度, 宽倍率, 速度, 偏移相位, 模糊强度 in (
            (主强度, 0.22, 0.30, 0.00, 0.18),
            (次强度, 0.16, 0.34, -0.24, 0.16),
        ):
            if 强度 <= 0.01:
                continue
            带图层 = self._创建扫描带图(
                (局部区域.w, 局部区域.h),
                float(logo局部框.x)
                + (-0.36 + ((活跃秒 + 偏移相位) * 速度) % 1.60) * float(logo局部框.w),
                float(logo局部框.w) * 宽倍率,
            )
            self._应用logo局部蒙版(带图层, 局部区域)
            模糊层 = self._近似模糊(带图层, 模糊强度)
            try:
                模糊层.set_alpha(int(18 + 156 * 强度))
            except Exception:
                pass
            try:
                带图层.set_alpha(int(12 + 120 * 强度))
            except Exception:
                pass
            画布.blit(模糊层, 局部区域.topleft, special_flags=pygame.BLEND_RGBA_ADD)
            画布.blit(带图层, 局部区域.topleft, special_flags=pygame.BLEND_RGBA_ADD)

    def _绘制logo实时电弧层(
        self,
        画布: pygame.Surface,
        局部区域: pygame.Rect,
        活跃秒: float,
    ):
        if not self._logo轮廓点:
            return
        总时长 = float(self._logo实时特效总时长)
        常驻 = 1.0 if 活跃秒 > 总时长 else _区间进度(活跃秒, 3.20, 总时长)
        细碎强度 = max(
            _区间脉冲(活跃秒, 2.16, 2.36, 2.74),
            _区间脉冲(活跃秒, 3.08, 3.18, 3.48) * 0.76,
            常驻 * (0.38 + (math.sin(活跃秒 * 4.60) * 0.5 + 0.5) * 0.34),
        )
        长跳强度 = max(
            _区间脉冲(活跃秒, 2.24, 2.42, 2.86) * 0.90,
            _区间脉冲(活跃秒, 3.12, 3.28, 3.62) * 0.76,
            常驻 * (0.16 + (math.sin(活跃秒 * 2.20 + 0.60) * 0.5 + 0.5) * 0.24),
        )
        if max(细碎强度, 长跳强度) <= 0.02:
            return

        局部图层 = pygame.Surface((局部区域.w, 局部区域.h), pygame.SRCALPHA)
        logo局部框 = self._取logo局部框(局部区域)
        轮廓数 = len(self._logo轮廓点)

        细碎条数 = min(len(self._logo电弧条目), 10 + int(细碎强度 * 14))
        for i in range(细碎条数):
            条目 = self._logo电弧条目[i % len(self._logo电弧条目)]
            pulse = pow(max(0.0, math.sin(活跃秒 * 条目["speed"] + 条目["phase"])), 6)
            alpha = pulse * (0.14 + 细碎强度 * 0.88) + 细碎强度 * 0.08
            if alpha < 0.06:
                continue
            索引 = int((条目["索引"] + 活跃秒 * (4.5 + i * 0.12)) % max(1, 轮廓数))
            点x, 点y, _, _, 法线x, 法线y = self._logo轮廓点[索引]
            切线x = -法线y
            切线y = 法线x
            长度 = 28.0 + pulse * 24.0 + 细碎强度 * 20.0
            振幅 = 5.0 + pulse * 12.0 + 细碎强度 * 9.0
            点列: list[tuple[int, int]] = []
            基准x = float(logo局部框.x + 点x)
            基准y = float(logo局部框.y + 点y)
            for 节点 in range(7):
                p = float(节点) / 6.0 - 0.5
                横向 = p * 长度
                法向波 = (
                    math.sin((p + 0.5) * 13.0 + 活跃秒 * 24.0 + 条目["phase"])
                    + math.cos((p + 0.5) * 19.0 - 活跃秒 * 17.0 + 条目["phase"] * 0.6)
                ) * 振幅 * (1.0 - abs(p) * 0.42)
                点列.append(
                    (
                        int(round(基准x + 切线x * 横向 + 法线x * 法向波)),
                        int(round(基准y + 切线y * 横向 + 法线y * 法向波)),
                    )
                )
            self._绘制logo发光折线(
                局部图层,
                点列,
                (150, 242, 255),
                int((0.16 + alpha * 0.84) * 255),
                0.8 + alpha * 2.0,
            )

        长弧条数 = min(len(self._logo长弧条目), 2 + int(长跳强度 * 6))
        for i in range(长弧条数):
            条目 = self._logo长弧条目[i % len(self._logo长弧条目)]
            pulse = pow(max(0.0, math.sin(活跃秒 * 条目["speed"] + 条目["phase"])), 12)
            alpha = pulse * (0.18 + 长跳强度 * 0.96)
            if alpha < 0.08:
                continue
            起点索引 = int((条目["起点索引"] + 活跃秒 * (3.2 + i * 0.18)) % max(1, 轮廓数))
            终点索引 = int((起点索引 + int(条目["终点偏移"])) % max(1, 轮廓数))
            起点数据 = self._logo轮廓点[起点索引]
            终点数据 = self._logo轮廓点[终点索引]
            起点x = float(logo局部框.x + 起点数据[0])
            起点y = float(logo局部框.y + 起点数据[1])
            终点x = float(logo局部框.x + 终点数据[0])
            终点y = float(logo局部框.y + 终点数据[1])
            dx = 终点x - 起点x
            dy = 终点y - 起点y
            总长度 = math.hypot(dx, dy) or 1.0
            法线x = -dy / 总长度
            法线y = dx / 总长度
            点列 = []
            扩散 = 7.0 + alpha * 18.0
            for 节点 in range(10):
                p = float(节点) / 9.0
                x = _线性插值(起点x, 终点x, p)
                y = _线性插值(起点y, 终点y, p)
                扰动 = (
                    math.sin(p * 17.0 + 活跃秒 * 19.0 + 条目["phase"])
                    + math.cos(p * 23.0 - 活跃秒 * 11.0)
                ) * 扩散 * (1.0 - abs(0.5 - p) * 1.2)
                点列.append(
                    (
                        int(round(x + 法线x * 扰动)),
                        int(round(y + 法线y * 扰动)),
                    )
                )
            self._绘制logo发光折线(
                局部图层,
                点列,
                (175, 245, 255),
                int((0.18 + alpha) * 255),
                1.1 + alpha * 2.0,
            )

        模糊层 = self._近似模糊(局部图层, 0.24)
        try:
            模糊层.set_alpha(int(20 + 54 * max(细碎强度, 长跳强度)))
        except Exception:
            pass
        画布.blit(模糊层, 局部区域.topleft, special_flags=pygame.BLEND_RGBA_ADD)
        画布.blit(局部图层, 局部区域.topleft, special_flags=pygame.BLEND_RGBA_ADD)

    def _绘制logo实时闪点层(
        self,
        画布: pygame.Surface,
        局部区域: pygame.Rect,
        活跃秒: float,
    ):
        if not self._logo闪点条目 or not self._logo内部采样点:
            return
        总时长 = float(self._logo实时特效总时长)
        常驻 = 1.0 if 活跃秒 > 总时长 else _区间进度(活跃秒, 3.20, 总时长)
        基础 = max(
            _区间进度(活跃秒, 3.10, 6.20),
            常驻 * (0.32 + (math.sin(活跃秒 * 3.60) * 0.5 + 0.5) * 0.28),
        )
        if 基础 <= 0.0:
            return

        局部图层 = pygame.Surface((局部区域.w, 局部区域.h), pygame.SRCALPHA)
        logo局部框 = self._取logo局部框(局部区域)
        样本数 = len(self._logo内部采样点)
        for i, 条目 in enumerate(self._logo闪点条目):
            pulse = max(0.0, math.sin(活跃秒 * 条目["speed"] * 3.6 + 条目["phase"]))
            alpha = pow(pulse, 9) * (0.10 + 基础 * 0.48)
            if alpha < 0.028:
                continue
            索引 = int((条目["索引"] + 活跃秒 * (2.2 + i * 0.03)) % max(1, 样本数))
            点x, 点y, _, _ = self._logo内部采样点[索引]
            半径 = 2 + int(2 + pulse * 6)
            self._绘制发光点(
                局部图层,
                (logo局部框.x + int(点x), logo局部框.y + int(点y)),
                半径,
                (120, 225, 255),
                int(alpha * 255),
            )

        模糊层 = self._近似模糊(局部图层, 0.26)
        try:
            模糊层.set_alpha(int(16 + 72 * 基础))
        except Exception:
            pass
        画布.blit(模糊层, 局部区域.topleft, special_flags=pygame.BLEND_RGBA_ADD)
        画布.blit(局部图层, 局部区域.topleft, special_flags=pygame.BLEND_RGBA_ADD)

    def _绘制logo实时闪点层_轻量(
        self,
        画布: pygame.Surface,
        局部区域: pygame.Rect,
        活跃秒: float,
    ):
        if not self._logo闪点条目 or not self._logo内部采样点:
            return
        总时长 = float(self._logo实时特效总时长)
        常驻 = 1.0 if 活跃秒 > 总时长 else _区间进度(活跃秒, 3.20, 总时长)
        基础 = max(
            _区间进度(活跃秒, 3.10, 6.20),
            常驻 * (0.28 + (math.sin(活跃秒 * 3.20) * 0.5 + 0.5) * 0.24),
        )
        if 基础 <= 0.0:
            return

        logo局部框 = self._取logo局部框(局部区域)
        样本数 = len(self._logo内部采样点)
        条目总数 = len(self._logo闪点条目)
        if 条目总数 <= 0:
            return

        跳步 = max(1, 条目总数 // 6)
        for i in range(0, 条目总数, 跳步):
            条目 = self._logo闪点条目[i]
            pulse = max(0.0, math.sin(活跃秒 * 条目["speed"] * 3.2 + 条目["phase"]))
            alpha = pow(pulse, 7) * (0.08 + 基础 * 0.32)
            if alpha < 0.03:
                continue
            索引 = int((条目["索引"] + 活跃秒 * (1.8 + i * 0.02)) % max(1, 样本数))
            点x, 点y, _, _ = self._logo内部采样点[索引]
            半径 = 2 + int(pulse * 3)
            try:
                pygame.draw.circle(
                    画布,
                    (120, 225, 255, int(alpha * 255)),
                    (logo局部框.x + int(点x), logo局部框.y + int(点y)),
                    max(1, 半径),
                )
            except Exception:
                pass

    def _绘制logo实时叠加效果(self, 显示后端):
        if (not self._是否显示logo) or (self._logo图 is None):
            self._清空logo实时叠加层()
            return

        屏幕 = self.上下文.get("屏幕")
        if not isinstance(屏幕, pygame.Surface):
            self._清空logo实时叠加层()
            return

        self._确保缓存()
        叠加层 = getattr(self, "_logo实时叠加层", None)
        if 叠加层 is None:
            return

        局部区域 = self._logo局部特效区域.clip(屏幕.get_rect())
        if 局部区域.w <= 0 or 局部区域.h <= 0:
            self._清空logo实时叠加层()
            return

        使用GPU = bool(getattr(显示后端, "是否GPU", False))
        缓存模式 = "gpu" if 使用GPU else "software-lite"
        屏幕尺寸 = 屏幕.get_size()
        活跃秒 = self._取logo活跃秒(time.time())
        默认帧率 = (
            float(getattr(self, "_logo实时特效缓存帧率", 24.0) or 24.0)
            if 使用GPU
            else float(getattr(self, "_logo实时特效软件帧率", 12.0) or 12.0)
        )
        帧率 = max(
            1.0,
            默认帧率,
        )
        帧序号 = int(max(0.0, float(活跃秒)) * 帧率)
        if (
            tuple(getattr(self, "_logo实时特效缓存尺寸", (0, 0))) == tuple(屏幕尺寸)
            and int(getattr(self, "_logo实时特效缓存帧", -1)) == int(帧序号)
            and str(getattr(self, "_logo实时特效缓存模式", "")) == str(缓存模式)
            and bool(getattr(叠加层, "有内容", lambda: False)())
        ):
            叠加层.绘制到显示后端(显示后端)
            return

        画布 = 叠加层.开始绘制(屏幕尺寸)
        if not isinstance(画布, pygame.Surface):
            return

        采样活跃秒 = float(帧序号) / 帧率
        self._绘制logo实时色偏层(画布, 采样活跃秒)
        self._绘制logo实时切片层(画布, 采样活跃秒)
        self._绘制logo实时扫光层(画布, 局部区域, 采样活跃秒)
        if 使用GPU:
            self._绘制logo实时电弧层(画布, 局部区域, 采样活跃秒)
            self._绘制logo实时闪点层(画布, 局部区域, 采样活跃秒)
        else:
            self._绘制logo实时闪点层_轻量(画布, 局部区域, 采样活跃秒)
        self._logo实时特效缓存尺寸 = tuple(屏幕尺寸)
        self._logo实时特效缓存帧 = int(帧序号)
        self._logo实时特效缓存模式 = str(缓存模式)
        叠加层.绘制到显示后端(显示后端)

    def 绘制GPU叠加(self, 显示后端):
        if bool(self._禁用投币特效):
            self._清空logo实时叠加层()
            return
        try:
            self._绘制logo实时叠加效果(显示后端)
        except Exception:
            self._清空logo实时叠加层()

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
        _绘制宽, _绘制高, 输出宽, 输出高 = self._取GPU输出与绘制尺寸(显示后端)

        self._同步GPU背景缓存(渲染器)
        背景视频 = getattr(self, "_背景视频", None)
        背景帧 = None
        if 背景视频 is not None:
            try:
                背景帧 = 背景视频.读取帧() if hasattr(背景视频, "读取帧") else None
            except Exception:
                self._停用背景视频()
                背景帧 = None
        try:
            if not isinstance(背景帧, pygame.Surface):
                背景帧 = self._取共享背景回退面(int(输出宽), int(输出高))
        except Exception:
            背景帧 = None
        if isinstance(背景帧, pygame.Surface):
            self._绘制GPU视频背景(渲染器, 背景帧, int(输出宽), int(输出高))

    def 绘制GPU中层(self, 显示后端):
        if not self._应使用GPU中层():
            return
        if _sdl2_video is None:
            return
        取渲染器 = getattr(显示后端, "取GPU渲染器", None)
        if not callable(取渲染器):
            return
        渲染器 = 取渲染器()
        if 渲染器 is None:
            return
        self._确保缓存()
        self._同步GPU界面纹理缓存(渲染器)
        绘制宽, 绘制高, 输出宽, 输出高 = self._取GPU输出与绘制尺寸(显示后端)
        比例x = float(max(1, int(输出宽))) / float(max(1, int(绘制宽)))
        比例y = float(max(1, int(输出高))) / float(max(1, int(绘制高)))

        if self._遮罩图 is not None:
            self._绘制GPU图层(
                渲染器,
                self._遮罩图,
                比例x=比例x,
                比例y=比例y,
            )

        if self._是否显示logo and self._logo图 is not None:
            if bool(self._禁用投币特效):
                self._绘制GPU图层(
                    渲染器,
                    self._logo图,
                    (
                        int(self._logo_rect.x),
                        int(self._logo_rect.y),
                        int(self._logo_rect.w),
                        int(self._logo_rect.h),
                    ),
                    比例x=比例x,
                    比例y=比例y,
                )
            else:
                当前时间 = time.time()
                缓存面 = self._取logo登场缓存(当前时间, self.上下文["屏幕"].get_size())
                if isinstance(缓存面, pygame.Surface):
                    self._绘制GPU图层(
                        渲染器,
                        缓存面,
                        比例x=比例x,
                        比例y=比例y,
                    )
                else:
                    self._绘制GPU图层(
                        渲染器,
                        self._logo图,
                        (
                            int(self._logo_rect.x),
                            int(self._logo_rect.y),
                            int(self._logo_rect.w),
                            int(self._logo_rect.h),
                        ),
                        比例x=比例x,
                        比例y=比例y,
                    )

        if self._阶段 == self._阶段_玩家选择:
            self._绘制GPU按钮(
                渲染器,
                self._1p图,
                self._1p_rect,
                self._1p特效,
                self._hover_1p,
                self._踏板选中玩家数 == 1,
                比例x=比例x,
                比例y=比例y,
            )
            self._绘制GPU按钮(
                渲染器,
                self._2p图,
                self._2p_rect,
                self._2p特效,
                self._hover_2p,
                self._踏板选中玩家数 == 2,
                比例x=比例x,
                比例y=比例y,
            )

    def 绘制(self):
        from core.工具 import 绘制底部联网与信用

        屏幕 = self.上下文["屏幕"]
        self._确保缓存()
        字体_credit = self.上下文["字体"]["投币_credit字"]
        字体_请投币 = self.上下文["字体"]["投币_请投币字"]

        宽, 高 = 屏幕.get_size()
        当前信用 = self._取当前信用()
        所需信用 = self._取所需信用()
        当前时间 = time.time()
        GPU中层启用 = self._应使用GPU中层()

        if self._应使用GPU背景():
            try:
                屏幕.fill((0, 0, 0, 0))
            except Exception:
                屏幕.fill((0, 0, 0))
        else:
            屏幕.fill((0, 0, 0))
            背景面 = self._读取软件背景覆盖帧(宽, 高, 当前时间)
            if 背景面 is not None:
                屏幕.blit(背景面, (0, 0))

        if (not GPU中层启用) and self._遮罩图:
            屏幕.blit(self._遮罩图, (0, 0))

        if (not GPU中层启用) and self._是否显示logo and self._logo图:
            if bool(self._禁用投币特效):
                屏幕.blit(self._logo图, self._logo_rect.topleft)
            else:
                self._绘制logo登场效果(屏幕, 当前时间)

        if self._阶段 == self._阶段_投币:
            if int(当前时间 - self._开始时间) % 2 == 0:
                文本框 = self._映射到屏幕_rect(self._bbox_请投币)
                self._绘制文本(
                    屏幕,
                    "请投币！",
                    字体_请投币,
                    (255, 255, 255),
                    文本框.center,
                    "center",
                )
        elif not GPU中层启用:
            self._绘制玩家选择按钮(屏幕)

        绘制底部联网与信用(
            屏幕=屏幕,
            联网原图=self._联网原图,
            字体_credit=字体_credit,
            credit数值=f"{当前信用}/{所需信用}",
            总信用需求=所需信用,
            文本=f"CREDIT：{当前信用}/{所需信用}",
            标准设计宽=self._设计宽,
            标准设计高=self._设计高,
            标准bbox_联网=self._bbox_联网,
            标准bbox_credit=self._bbox_credit,
        )

        try:
            状态 = self._取状态()
            投币键显示 = str(状态.get("投币快捷键显示", "F1") or "F1").upper()
            提示 = f"{投币键显示}投币"
            提示面 = 字体_credit.render(提示, True, (255, 255, 255))
            提示框 = 提示面.get_rect()
            提示框.topright = (宽 - 20, 18)
            屏幕.blit(提示面, 提示框.topleft)

            提示字体 = self.上下文.get("字体", {}).get("小字", 字体_credit)
            if (
                self._阶段 == self._阶段_投币
                and int(当前时间 - self._开始时间) % 2 == 0
            ):
                提示2 = "请窗口最大化以后再点击F11全屏"
                提示面2 = 提示字体.render(提示2, True, (220, 220, 220))
                提示框2 = 提示面2.get_rect()
                提示框2.midtop = (宽 // 2, 18)
                屏幕.blit(提示面2, 提示框2.topleft)
        except Exception:
            pass
