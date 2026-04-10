import math
import os
import time
from dataclasses import dataclass

import pygame

from core.常量与路径 import 取项目根目录 as _公共取项目根目录
from core.工具 import cover缩放 as _cover缩放
from core.踏板控制 import 踏板动作_左, 踏板动作_右, 踏板动作_确认
from ui.按钮特效 import 公用按钮点击特效, 公用按钮音效
from ui.场景过渡 import 公用放大过渡器


@dataclass
class 图片资源组:
    联网图标: pygame.Surface | None = None
    top栏背景: pygame.Surface | None = None
    个人中心标题: pygame.Surface | None = None
    场景1游客: pygame.Surface | None = None
    场景1vip: pygame.Surface | None = None
    场景2游客: pygame.Surface | None = None
    刷卡背景: pygame.Surface | None = None
    刷卡内容: pygame.Surface | None = None
    刷卡内容白: pygame.Surface | None = None
    磁卡: pygame.Surface | None = None
    贵宾装饰: pygame.Surface | None = None


@dataclass
class 缓存资源组:
    遮罩图: pygame.Surface | None = None
    top栏图: pygame.Surface | None = None
    个人中心图: pygame.Surface | None = None
    场景1游客图: pygame.Surface | None = None
    场景1vip图: pygame.Surface | None = None
    场景2游客图: pygame.Surface | None = None
    刷卡背景图: pygame.Surface | None = None
    刷卡内容图: pygame.Surface | None = None
    刷卡内容白图: pygame.Surface | None = None
    磁卡图: pygame.Surface | None = None
    贵宾装饰图: pygame.Surface | None = None


@dataclass
class 布局框组:
    top栏框: pygame.Rect = pygame.Rect(0, 0, 1, 1)
    个人中心框: pygame.Rect = pygame.Rect(0, 0, 1, 1)
    场景1游客框: pygame.Rect = pygame.Rect(0, 0, 1, 1)
    场景1vip框: pygame.Rect = pygame.Rect(0, 0, 1, 1)
    场景2游客框: pygame.Rect = pygame.Rect(0, 0, 1, 1)
    刷卡背景框: pygame.Rect = pygame.Rect(0, 0, 1, 1)
    刷卡内容框: pygame.Rect = pygame.Rect(0, 0, 1, 1)
    贵宾装饰框: pygame.Rect = pygame.Rect(0, 0, 1, 1)
    磁卡目标框: pygame.Rect = pygame.Rect(0, 0, 1, 1)
    磁卡当前框: pygame.Rect = pygame.Rect(0, 0, 1, 1)


@dataclass
class 运行时状态:
    阶段: str = "选择"
    按钮消失中: bool = False
    按钮消失开始: float = 0.0
    刷卡放大开始: float = 0.0
    闪烁开始: float = 0.0
    磁卡滑入开始: float = 0.0
    拖拽中: bool = False
    拖拽偏移: tuple[int, int] = (0, 0)
    hover游客: bool = False
    hovervip: bool = False
    踏板选中项: str | None = None
    自动刷卡中: bool = False
    自动刷卡开始: float = 0.0
    自动刷卡起点: tuple[float, float] = (0.0, 0.0)
    自动刷卡终点: tuple[float, float] = (0.0, 0.0)
    游客悬停插值: float = 0.0
    vip悬停插值: float = 0.0
    悬停更新时间: float = 0.0
    正在放大切场景: bool = False
    延迟目标场景: str | None = None


class 场景_登陆磁卡:
    名称 = "登陆磁卡"

    _设计宽 = 2048
    _设计高 = 1152

    _阶段_选择 = "选择"
    _阶段_刷卡 = "刷卡"

    _bbox_场景1_游客 = (255, 274, 967, 886)
    _bbox_场景1_vip = (1081, 353, 1526, 799)
    _bbox_场景2_游客 = (277, 247, 784, 754)
    _bbox_磁卡目标 = (1197, 764, 1859, 1152)

    _刷卡背景缩放系数 = 1.3
    _刷卡内容宽占比 = 0.7
    _贵宾装饰宽占比 = 0.5
    _贵宾装饰外溢x占比 = 0.0
    _贵宾装饰外溢y占比 = -0.01
    _磁卡缩放系数 = 0.5
    _场景1游客放大系数 = 1.4

    _事件_延迟切场景 = pygame.USEREVENT + 24

    def __init__(self, 上下文: dict):
        self.上下文 = 上下文
        资源 = 上下文["资源"]
        根目录 = _公共取项目根目录(资源)

        self._背景视频 = 上下文.get("背景视频")
        self._缓存尺寸 = (0, 0)
        self._共享背景回退原图 = self._安全加载图片(
            str(上下文.get("共享背景回退图路径", "") or ""),
            False,
        )
        self._共享背景回退缓存图: pygame.Surface | None = None
        self._共享背景回退缓存尺寸 = (0, 0)

        self._图片资源 = 图片资源组(
            联网图标=self._安全加载图片(资源.get("投币_联网图标", ""), True),
            top栏背景=self._安全加载图片(
                os.path.join(根目录, "UI-img", "top栏", "top栏背景.png"), True
            ),
            个人中心标题=self._安全加载图片(
                os.path.join(根目录, "UI-img", "top栏", "个人中心.png"), True
            ),
            场景1游客=self._安全加载图片(
                os.path.join(根目录, "UI-img", "个人中心-登陆", "场景1-游客.png"), True
            ),
            场景1vip=self._安全加载图片(
                os.path.join(
                    根目录, "UI-img", "个人中心-登陆", "场景1-vip磁卡-半透明.png"
                ),
                True,
            ),
            场景2游客=self._安全加载图片(
                os.path.join(根目录, "UI-img", "个人中心-登陆", "场景2-游客.png"), True
            ),
            刷卡背景=self._安全加载图片(
                os.path.join(根目录, "UI-img", "个人中心-登陆", "请刷卡背景.png"), True
            ),
            刷卡内容=self._安全加载图片(
                os.path.join(根目录, "UI-img", "个人中心-登陆", "请刷卡内容.png"), True
            ),
            刷卡内容白=self._安全加载图片(
                os.path.join(根目录, "UI-img", "个人中心-登陆", "请刷卡内容白色.png"),
                True,
            ),
            磁卡=self._安全加载图片(
                os.path.join(根目录, "UI-img", "个人中心-登陆", "磁卡.png"), True
            ),
            贵宾装饰=self._安全加载图片(
                os.path.join(根目录, "UI-img", "个人中心-登陆", "贵宾装饰.png"), True
            ),
        )

        self._缓存资源 = 缓存资源组()
        self._布局框 = 布局框组()
        self._运行 = 运行时状态()

        self.按钮音效 = 公用按钮音效(资源.get("按钮音效", ""))
        刷卡音效路径 = 资源.get("刷卡音效", "") or 资源.get("按钮音效", "")
        self.刷卡音效 = 公用按钮音效(刷卡音效路径)
        self._游客点击特效 = 公用按钮点击特效(
            总时长=0.3,
            缩小阶段=0.1,
            缩小到=0.90,
            放大到=4.00,
            透明起始=255,
            透明结束=0,
        )
        self._全屏放大过渡 = 公用放大过渡器(总时长毫秒=320)

    def _取状态(self) -> dict:
        状态 = self.上下文.get("状态", {})
        if not isinstance(状态, dict):
            状态 = {}
            self.上下文["状态"] = 状态
        return 状态

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

    def _按尺寸缩放图(self, 图片: pygame.Surface | None, 尺寸: tuple[int, int]):
        if 图片 is None:
            return None
        return pygame.transform.smoothscale(图片, 尺寸).convert_alpha()

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

    def _取共享背景回退面(self, 宽: int, 高: int) -> pygame.Surface | None:
        原图 = getattr(self, "_共享背景回退原图", None)
        if not isinstance(原图, pygame.Surface):
            return None
        目标尺寸 = (max(1, int(宽)), max(1, int(高)))
        if (
            tuple(getattr(self, "_共享背景回退缓存尺寸", (0, 0))) == tuple(目标尺寸)
            and isinstance(getattr(self, "_共享背景回退缓存图", None), pygame.Surface)
        ):
            return self._共享背景回退缓存图
        try:
            图 = _cover缩放(原图, int(目标尺寸[0]), int(目标尺寸[1])).convert()
        except Exception:
            return None
        self._共享背景回退缓存图 = 图
        self._共享背景回退缓存尺寸 = tuple(目标尺寸)
        return 图

    def _绘制_按中心缩放(
        self,
        屏幕: pygame.Surface,
        图片: pygame.Surface | None,
        基准框: pygame.Rect,
        缩放倍率: float,
    ):
        if 图片 is None:
            return
        if 缩放倍率 >= 0.999:
            屏幕.blit(图片, 基准框.topleft)
            return
        if 缩放倍率 <= 0.001:
            return
        新宽 = max(1, int(基准框.w * 缩放倍率))
        新高 = max(1, int(基准框.h * 缩放倍率))
        新图 = pygame.transform.smoothscale(图片, (新宽, 新高)).convert_alpha()
        新框 = 新图.get_rect(center=基准框.center)
        屏幕.blit(新图, 新框.topleft)

    def _开始放大切场景(
        self,
        起始图: pygame.Surface | None,
        起始框: pygame.Rect,
        目标场景名: str,
    ):
        if self._运行.正在放大切场景:
            return
        if 起始图 is None:
            self._运行.延迟目标场景 = 目标场景名
            pygame.time.set_timer(self._事件_延迟切场景, 1)
            return

        self._运行.正在放大切场景 = True
        self._运行.延迟目标场景 = 目标场景名
        try:
            self._全屏放大过渡.开始(起始图, 起始框)
        except Exception:
            pygame.time.set_timer(self._事件_延迟切场景, 1)
            return
        pygame.time.set_timer(self._事件_延迟切场景, 320, loops=1)

    def _重置运行时状态(self):
        self._运行 = 运行时状态(
            阶段=self._阶段_选择,
            闪烁开始=time.time(),
        )

    def _进入刷卡阶段(self):
        self._运行.阶段 = self._阶段_刷卡
        self._运行.刷卡放大开始 = time.time()
        self._运行.闪烁开始 = time.time()
        self._运行.磁卡滑入开始 = time.time()
        self._运行.拖拽中 = False
        self._运行.自动刷卡中 = False
        self._运行.自动刷卡开始 = 0.0
        self._布局框.磁卡当前框 = self._布局框.磁卡目标框.copy()
        self._布局框.磁卡当前框.y = self._布局框.磁卡目标框.y + int(
            self._布局框.磁卡目标框.h * 0.35
        )

    def _缓动逼近(
        self,
        当前值: float,
        目标值: float,
        帧间隔: float,
        速度: float,
    ) -> float:
        当前值 = float(当前值)
        目标值 = float(目标值)
        帧间隔 = max(0.0, min(0.05, float(帧间隔)))
        速度 = max(0.0, float(速度))
        if abs(目标值 - 当前值) < 0.0001:
            return 目标值
        插值 = min(1.0, 帧间隔 * 速度)
        return 当前值 + (目标值 - 当前值) * 插值

    def _确保缓存(self):
        from ui.top栏 import 生成top栏

        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()
        if (宽, 高) == self._缓存尺寸:
            return
        self._缓存尺寸 = (宽, 高)

        遮罩 = pygame.Surface((宽, 高), pygame.SRCALPHA)
        遮罩.fill((0, 0, 0, 128))
        self._缓存资源.遮罩图 = 遮罩

        (
            self._布局框.top栏框,
            self._缓存资源.top栏图,
            self._布局框.个人中心框,
            self._缓存资源.个人中心图,
        ) = 生成top栏(
            屏幕=屏幕,
            top背景原图=self._图片资源.top栏背景,
            标题原图=self._图片资源.个人中心标题,
            设计宽=self._设计宽,
            设计高=self._设计高,
            top设计高=150,
            top背景宽占比=1,
            top背景高占比=1,
            标题最大宽占比=0.5,
            标题最大高占比=0.5,
            标题整体缩放=1,
            标题上移比例=0.1,
        )

        self._布局框.场景1游客框 = self._映射到屏幕_rect(self._bbox_场景1_游客)
        self._布局框.场景1vip框 = self._映射到屏幕_rect(self._bbox_场景1_vip)
        self._布局框.场景2游客框 = self._映射到屏幕_rect(self._bbox_场景2_游客)

        self._缓存资源.场景1游客图 = self._按尺寸缩放图(
            self._图片资源.场景1游客,
            (self._布局框.场景1游客框.w, self._布局框.场景1游客框.h),
        )
        self._缓存资源.场景1vip图 = self._按尺寸缩放图(
            self._图片资源.场景1vip,
            (self._布局框.场景1vip框.w, self._布局框.场景1vip框.h),
        )
        self._缓存资源.场景2游客图 = self._按尺寸缩放图(
            self._图片资源.场景2游客,
            (self._布局框.场景2游客框.w, self._布局框.场景2游客框.h),
        )

        缩放 = min(宽 / max(1, self._设计宽), 高 / max(1, self._设计高))
        背景缩放 = 缩放 * float(self._刷卡背景缩放系数)

        if self._图片资源.刷卡背景:
            背景宽 = max(1, int(self._图片资源.刷卡背景.get_width() * 背景缩放))
            背景高 = max(1, int(self._图片资源.刷卡背景.get_height() * 背景缩放))
            self._缓存资源.刷卡背景图 = self._按尺寸缩放图(
                self._图片资源.刷卡背景,
                (背景宽, 背景高),
            )
            self._布局框.刷卡背景框 = self._缓存资源.刷卡背景图.get_rect(
                center=(宽 // 2, 高 // 2)
            )
        else:
            self._缓存资源.刷卡背景图 = None
            self._布局框.刷卡背景框 = pygame.Rect(宽 // 2, 高 // 2, 1, 1)

        if self._图片资源.刷卡内容 and self._缓存资源.刷卡背景图:
            内容目标宽 = max(
                1, int(self._布局框.刷卡背景框.w * float(self._刷卡内容宽占比))
            )
            比例 = 内容目标宽 / max(1, self._图片资源.刷卡内容.get_width())
            内容目标高 = max(1, int(self._图片资源.刷卡内容.get_height() * 比例))
            self._缓存资源.刷卡内容图 = self._按尺寸缩放图(
                self._图片资源.刷卡内容,
                (内容目标宽, 内容目标高),
            )
            self._缓存资源.刷卡内容白图 = self._按尺寸缩放图(
                self._图片资源.刷卡内容白,
                (内容目标宽, 内容目标高),
            )
            self._布局框.刷卡内容框 = self._缓存资源.刷卡内容图.get_rect(
                center=self._布局框.刷卡背景框.center
            )
        else:
            self._缓存资源.刷卡内容图 = None
            self._缓存资源.刷卡内容白图 = None
            self._布局框.刷卡内容框 = self._布局框.刷卡背景框.copy()

        if self._图片资源.贵宾装饰 and self._缓存资源.刷卡背景图:
            装饰目标宽 = int(self._布局框.刷卡背景框.w * float(self._贵宾装饰宽占比))
            比例 = 装饰目标宽 / max(1, self._图片资源.贵宾装饰.get_width())
            装饰目标高 = max(1, int(self._图片资源.贵宾装饰.get_height() * 比例))
            self._缓存资源.贵宾装饰图 = self._按尺寸缩放图(
                self._图片资源.贵宾装饰,
                (装饰目标宽, 装饰目标高),
            )
            self._布局框.贵宾装饰框 = self._缓存资源.贵宾装饰图.get_rect()
            dx = int(self._布局框.刷卡背景框.w * float(self._贵宾装饰外溢x占比))
            dy = int(self._布局框.刷卡背景框.h * float(self._贵宾装饰外溢y占比))
            self._布局框.贵宾装饰框.center = (
                self._布局框.刷卡背景框.right + dx,
                self._布局框.刷卡背景框.top + dy,
            )
        else:
            self._缓存资源.贵宾装饰图 = None
            self._布局框.贵宾装饰框 = pygame.Rect(0, 0, 1, 1)

        原目标 = self._映射到屏幕_rect(self._bbox_磁卡目标)
        self._布局框.磁卡目标框 = 原目标.copy()
        缩放倍率 = float(self._磁卡缩放系数)
        新宽 = max(1, int(原目标.w * 缩放倍率))
        新高 = max(1, int(原目标.h * 缩放倍率))
        self._布局框.磁卡目标框.size = (新宽, 新高)
        self._布局框.磁卡目标框.center = 原目标.center
        self._缓存资源.磁卡图 = self._按尺寸缩放图(
            self._图片资源.磁卡,
            (新宽, 新高),
        )
        self._布局框.磁卡当前框 = self._布局框.磁卡目标框.copy()

    def 进入(self):
        资源 = self.上下文.get("资源", {})
        状态 = self._取状态()
        根目录 = _公共取项目根目录(资源)
        排行榜路径 = os.path.join(根目录, "冷资源", "backsound", "排行榜.mp3")

        if (not bool(状态.get("bgm_排行榜_已播放", False))) and os.path.isfile(
            排行榜路径
        ):
            try:
                self.上下文["音乐"].播放循环(排行榜路径)
                状态["bgm_排行榜_已播放"] = True
            except Exception:
                pass

        self._重置运行时状态()
        pygame.time.set_timer(self._事件_延迟切场景, 0)
        self._确保缓存()

    def 退出(self):
        pygame.time.set_timer(self._事件_延迟切场景, 0)

    def 更新(self):
        if (self._运行.阶段 != self._阶段_刷卡) or (not self._运行.自动刷卡中):
            return None

        经过 = (time.time() - float(self._运行.自动刷卡开始 or 0.0)) / 0.48
        t = max(0.0, min(1.0, float(经过)))
        缓动 = 1.0 - (1.0 - t) ** 3

        起点x, 起点y = self._运行.自动刷卡起点
        终点x, 终点y = self._运行.自动刷卡终点
        抬升 = math.sin(缓动 * math.pi) * max(
            18.0, float(self._布局框.磁卡目标框.h) * 0.14
        )
        cx = 起点x + (终点x - 起点x) * 缓动
        cy = 起点y + (终点y - 起点y) * 缓动 - 抬升
        self._布局框.磁卡当前框.center = (int(cx), int(cy))

        if t >= 1.0:
            self._运行.自动刷卡中 = False
            return self._触发刷卡成功()
        return None

    def 绘制(self):
        from core.工具 import cover缩放, 绘制底部联网与信用

        屏幕 = self.上下文["屏幕"]
        self._确保缓存()
        宽, 高 = 屏幕.get_size()

        屏幕.fill((0, 0, 0))
        try:
            帧 = self._背景视频.读取帧() if self._背景视频 else None
        except Exception:
            self._停用背景视频()
            帧 = None
        if 帧 is not None:
            屏幕.blit(cover缩放(帧, 宽, 高), (0, 0))
        else:
            回退背景 = self._取共享背景回退面(宽, 高)
            if isinstance(回退背景, pygame.Surface):
                屏幕.blit(回退背景, (0, 0))

        if self._缓存资源.遮罩图:
            屏幕.blit(self._缓存资源.遮罩图, (0, 0))
        if self._缓存资源.top栏图:
            屏幕.blit(self._缓存资源.top栏图, self._布局框.top栏框.topleft)
        if self._缓存资源.个人中心图:
            屏幕.blit(self._缓存资源.个人中心图, self._布局框.个人中心框.topleft)

        状态 = self._取状态()
        当前信用 = int(状态.get("投币数", 0) or 0)
        所需信用 = int(状态.get("每局所需信用", 3) or 3)
        绘制底部联网与信用(
            屏幕=屏幕,
            联网原图=self._图片资源.联网图标,
            字体_credit=self.上下文["字体"]["投币_credit字"],
            credit数值=f"{当前信用}/{所需信用}",
            总信用需求=所需信用,
        )

        if self._运行.阶段 == self._阶段_选择:
            self._绘制选择界面(屏幕)
        else:
            self._绘制刷卡界面(屏幕)

        if self._全屏放大过渡.是否进行中():
            self._全屏放大过渡.更新并绘制(屏幕)

    def _绘制高亮底光(
        self,
        屏幕: pygame.Surface,
        基准框: pygame.Rect,
        强度: float,
        主色: tuple[int, int, int],
    ):
        强度 = max(0.0, min(1.0, float(强度)))
        if 强度 <= 0.001:
            return

        光宽 = max(1, int(基准框.w * (1.06 + 0.08 * 强度)))
        光高 = max(1, int(基准框.h * (1.04 + 0.06 * 强度)))
        光晕 = pygame.Surface((光宽, 光高), pygame.SRCALPHA)

        外层框 = 光晕.get_rect().inflate(-int(光宽 * 0.04), -int(光高 * 0.08))
        中层框 = 光晕.get_rect().inflate(-int(光宽 * 0.16), -int(光高 * 0.20))
        内层框 = 光晕.get_rect().inflate(-int(光宽 * 0.30), -int(光高 * 0.34))

        pygame.draw.ellipse(
            光晕, (主色[0], 主色[1], 主色[2], int(12 + 16 * 强度)), 外层框
        )
        pygame.draw.ellipse(
            光晕, (主色[0], 主色[1], 主色[2], int(18 + 22 * 强度)), 中层框
        )
        pygame.draw.ellipse(光晕, (255, 255, 255, int(6 + 10 * 强度)), 内层框)

        光框 = 光晕.get_rect(
            center=(基准框.centerx, int(基准框.centery + 基准框.h * 0.02))
        )
        屏幕.blit(光晕, 光框.topleft)

    def _绘制选择界面(self, 屏幕: pygame.Surface):
        现在 = time.time()
        上次更新时间 = float(self._运行.悬停更新时间 or 0.0)
        帧间隔 = (
            0.016 if 上次更新时间 <= 0 else max(0.0, min(0.05, 现在 - 上次更新时间))
        )
        self._运行.悬停更新时间 = 现在

        游客激活 = bool(self._运行.hover游客 or self._运行.踏板选中项 == "游客")
        vip激活 = bool(self._运行.hovervip or self._运行.踏板选中项 == "VIP")

        self._运行.游客悬停插值 = self._缓动逼近(
            self._运行.游客悬停插值,
            1.0 if 游客激活 else 0.0,
            帧间隔,
            12.0 if 游客激活 else 14.0,
        )
        self._运行.vip悬停插值 = self._缓动逼近(
            self._运行.vip悬停插值,
            1.0 if vip激活 else 0.0,
            帧间隔,
            12.0 if vip激活 else 14.0,
        )

        基础缩放 = 1.0
        if self._运行.按钮消失中:
            t = max(0.0, min(1.0, (现在 - self._运行.按钮消失开始) / 0.2))
            基础缩放 = max(0.0, 1.0 - t)

        游客呼吸 = 1.0 + math.sin(现在 * 5.8) * 0.008 * self._运行.游客悬停插值
        vip呼吸 = 1.0 + math.sin(现在 * 5.2 + 0.35) * 0.007 * self._运行.vip悬停插值

        游客缩放 = (
            基础缩放
            * float(self._场景1游客放大系数)
            * (1.0 + 0.045 * self._运行.游客悬停插值)
            * 游客呼吸
        )
        vip缩放 = 基础缩放 * (1.0 + 0.040 * self._运行.vip悬停插值) * vip呼吸

        游客框 = self._布局框.场景1游客框.copy()
        vip框 = self._布局框.场景1vip框.copy()
        游客框.y -= int(self._布局框.场景1游客框.h * 0.018 * self._运行.游客悬停插值)
        vip框.y -= int(self._布局框.场景1vip框.h * 0.015 * self._运行.vip悬停插值)

        if self._运行.游客悬停插值 > 0.01:
            self._绘制高亮底光(屏幕, 游客框, self._运行.游客悬停插值, (150, 215, 255))
        if self._运行.vip悬停插值 > 0.01:
            self._绘制高亮底光(屏幕, vip框, self._运行.vip悬停插值, (255, 215, 135))

        self._绘制_按中心缩放(屏幕, self._缓存资源.场景1游客图, 游客框, 游客缩放)
        self._绘制_按中心缩放(屏幕, self._缓存资源.场景1vip图, vip框, vip缩放)

        if self._运行.按钮消失中 and 基础缩放 <= 0.001:
            self._运行.按钮消失中 = False
            self._进入刷卡阶段()

    def _绘制刷卡界面(self, 屏幕: pygame.Surface):
        现在 = time.time()
        if self._缓存资源.场景2游客图:
            屏幕.blit(self._缓存资源.场景2游客图, self._布局框.场景2游客框.topleft)

        背景缩放 = 1.0
        t = (现在 - self._运行.刷卡放大开始) / 0.2
        if t < 1.0:
            背景缩放 = 1.25 - 0.25 * max(0.0, min(1.0, t))

        self._绘制_按中心缩放(
            屏幕, self._缓存资源.刷卡背景图, self._布局框.刷卡背景框, 背景缩放
        )

        if self._缓存资源.贵宾装饰图:
            屏幕.blit(self._缓存资源.贵宾装饰图, self._布局框.贵宾装饰框.topleft)

        闪烁值 = int((现在 - self._运行.闪烁开始) // 1) % 2
        内容图 = (
            self._缓存资源.刷卡内容白图 if 闪烁值 == 1 else self._缓存资源.刷卡内容图
        )
        if 内容图:
            屏幕.blit(内容图, self._布局框.刷卡内容框.topleft)

        if self._缓存资源.磁卡图:
            if (not self._运行.拖拽中) and (not self._运行.自动刷卡中):
                t2 = max(0.0, min(1.0, (现在 - self._运行.磁卡滑入开始) / 0.3))
                起点y = self._布局框.磁卡目标框.y + int(
                    self._布局框.磁卡目标框.h * 0.35
                )
                终点y = self._布局框.磁卡目标框.y
                self._布局框.磁卡当前框.x = self._布局框.磁卡目标框.x
                self._布局框.磁卡当前框.y = int(起点y + (终点y - 起点y) * t2)

            屏幕.blit(self._缓存资源.磁卡图, self._布局框.磁卡当前框.topleft)

    def _执行选择(self, 选项: str):
        if self._运行.按钮消失中:
            return None

        选项 = str(选项 or "").strip().upper()
        if 选项 == "游客".upper():
            self.按钮音效.播放()
            self._游客点击特效.触发()

            起始框 = self._布局框.场景1游客框.copy()
            缩放倍率 = float(self._场景1游客放大系数)
            起始框.size = (
                max(1, int(起始框.w * 缩放倍率)),
                max(1, int(起始框.h * 缩放倍率)),
            )
            起始框.center = self._布局框.场景1游客框.center

            起始图 = None
            if self._图片资源.场景1游客:
                起始图 = pygame.transform.smoothscale(
                    self._图片资源.场景1游客,
                    (起始框.w, 起始框.h),
                ).convert_alpha()

            self._开始放大切场景(起始图, 起始框, "大模式")
            return None

        if 选项 == "VIP":
            self.按钮音效.播放()
            self._运行.按钮消失中 = True
            self._运行.按钮消失开始 = time.time()
        return None

    def _开始自动刷卡(self):
        if self._运行.自动刷卡中 or self._全屏放大过渡.是否进行中():
            return None
        self._运行.拖拽中 = False
        self._运行.自动刷卡中 = True
        self._运行.自动刷卡开始 = time.time()
        self._运行.自动刷卡起点 = (
            float(self._布局框.磁卡当前框.centerx),
            float(self._布局框.磁卡当前框.centery),
        )
        self._运行.自动刷卡终点 = (
            float(self._布局框.刷卡背景框.centerx),
            float(self._布局框.刷卡背景框.centery),
        )
        return None

    def _触发刷卡成功(self):
        状态 = self._取状态()
        状态["bgm_排行榜_已播放"] = bool(状态.get("bgm_排行榜_已播放", True))
        try:
            self.刷卡音效.播放()
        except Exception:
            try:
                self.按钮音效.播放()
            except Exception:
                pass
        self._开始放大切场景(
            self._缓存资源.磁卡图,
            self._布局框.磁卡当前框.copy(),
            "个人资料",
        )
        return None

    def 处理全局踏板(self, 动作: str):
        if self._全屏放大过渡.是否进行中():
            return None

        if self._运行.阶段 == self._阶段_选择:
            if 动作 == 踏板动作_左:
                if self._运行.踏板选中项 != "游客":
                    self.按钮音效.播放()
                self._运行.踏板选中项 = "游客"
                return None
            if 动作 == 踏板动作_右:
                if self._运行.踏板选中项 != "VIP":
                    self.按钮音效.播放()
                self._运行.踏板选中项 = "VIP"
                return None
            if 动作 == 踏板动作_确认 and self._运行.踏板选中项:
                return self._执行选择(self._运行.踏板选中项)
            return None

        if self._运行.阶段 == self._阶段_刷卡 and 动作 == 踏板动作_确认:
            return self._开始自动刷卡()
        return None

    def 处理事件(self, 事件):
        if 事件.type == pygame.VIDEORESIZE:
            return None

        if 事件.type == self._事件_延迟切场景:
            pygame.time.set_timer(self._事件_延迟切场景, 0)
            self._运行.正在放大切场景 = False
            if self._运行.延迟目标场景:
                目标 = self._运行.延迟目标场景
                self._运行.延迟目标场景 = None
                return {"切换到": 目标, "禁用黑屏过渡": True}
            return None

        if self._全屏放大过渡.是否进行中():
            return None

        if self._运行.阶段 == self._阶段_选择:
            return self._处理选择事件(事件)
        return self._处理刷卡事件(事件)

    def _处理选择事件(self, 事件):
        if 事件.type == pygame.MOUSEMOTION:
            self._运行.hover游客 = self._布局框.场景1游客框.collidepoint(事件.pos)
            self._运行.hovervip = self._布局框.场景1vip框.collidepoint(事件.pos)
            return None

        if 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            if self._运行.按钮消失中:
                return None
            if self._布局框.场景1游客框.collidepoint(事件.pos):
                self._运行.踏板选中项 = "游客"
                return self._执行选择("游客")
            if self._布局框.场景1vip框.collidepoint(事件.pos):
                self._运行.踏板选中项 = "VIP"
                return self._执行选择("VIP")
        return None

    def _处理刷卡事件(self, 事件):
        if self._运行.自动刷卡中:
            return None

        if 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            if self._布局框.场景2游客框.collidepoint(事件.pos):
                self.按钮音效.播放()
                self._运行.阶段 = self._阶段_选择
                self._运行.按钮消失中 = False
                self._运行.拖拽中 = False
                self._运行.踏板选中项 = "游客"
                return None

            if self._运行.拖拽中:
                self._运行.拖拽中 = False
                if self._布局框.磁卡当前框.colliderect(self._布局框.刷卡背景框):
                    return self._触发刷卡成功()

        if 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            if self._布局框.磁卡当前框.collidepoint(事件.pos):
                self._运行.拖拽中 = True
                鼠标x, 鼠标y = 事件.pos
                self._运行.拖拽偏移 = (
                    鼠标x - self._布局框.磁卡当前框.x,
                    鼠标y - self._布局框.磁卡当前框.y,
                )
                return None

        if 事件.type == pygame.MOUSEMOTION and self._运行.拖拽中:
            鼠标x, 鼠标y = 事件.pos
            偏移x, 偏移y = self._运行.拖拽偏移
            self._布局框.磁卡当前框.x = 鼠标x - 偏移x
            self._布局框.磁卡当前框.y = 鼠标y - 偏移y
            return None

        return None
