import os
import math
import pygame


from core.工具 import 绘制文本, cover缩放, 安全加载图片
from core.踏板控制 import (
    踏板动作_左,
    踏板动作_右,
    踏板动作_确认,
    循环切换索引,
)
from scenes.场景基类 import 场景基类, 场景切换请求
from ui.按钮特效 import 图片按钮
from ui.按钮特效 import 公用按钮音效
from ui.top栏 import 生成top栏
from core.工具 import 绘制渐隐放大图
from ui.场景过渡 import 公用放大过渡器

class 场景_大模式(场景基类):
    名称 = "大模式"

    _设计宽 = 2048
    _设计高 = 1152
    _事件_延迟切场景 = pygame.USEREVENT + 23

    def __init__(self, 上下文: dict):
        super().__init__(上下文)
        资源 = self.上下文["资源"]
        根 = 资源.get("根", os.getcwd())

        self._背景视频 = self.上下文.get("背景视频")
        self._联网原图 = 安全加载图片(资源.get("投币_联网图标", ""), 透明=True)
        self._按钮音效 = 公用按钮音效(资源.get("按钮音效", ""))

        self._top栏原图 = 安全加载图片(
            os.path.join(根, "UI-img", "top栏", "top栏背景.png"), 透明=True
        )
        self._top标题原图 = 安全加载图片(
            os.path.join(根, "UI-img", "top栏", "模式选择.png"), 透明=True
        )
        self._rect_top栏 = pygame.Rect(0, 0, 1, 1)
        self._top栏图 = None
        self._rect_top标题 = pygame.Rect(0, 0, 1, 1)
        self._top标题图 = None

        self._按钮当前偏移x: dict[str, float] = {}
        self._选中开始毫秒: int = 0
        self._推开时长毫秒 = 320
        self._推开屏幕边距 = 24
        self._推开间距缩放 = 1.0

        self._模式列表 = [
            {
                "键": "花式",
                "按钮图": os.path.join(
                    根, "UI-img", "大模式选择界面", "按钮", "花式模式按钮.png"
                ),
                "banner图": os.path.join(
                    根, "UI-img", "大模式选择界面", "花式模式.png"
                ),
                "文案": "花式模式：是一种花里胡哨的模式",
                "songs子目录": "花式",
            },
            {
                "键": "竞速",
                "按钮图": os.path.join(
                    根, "UI-img", "大模式选择界面", "按钮", "竞速模式按钮.png"
                ),
                "banner图": os.path.join(
                    根, "UI-img", "大模式选择界面", "竞速模式.png"
                ),
                "文案": "竞速模式：是一种速度很快的模式",
                "songs子目录": "竞速",
            },
            {
                "键": "派对",
                "按钮图": os.path.join(
                    根, "UI-img", "大模式选择界面", "按钮", "派对模式按钮.png"
                ),
                "banner图": os.path.join(
                    根, "UI-img", "大模式选择界面", "派对模式.png"
                ),
                "文案": "派对模式：不清楚这里原本是啥",
                "songs子目录": "派对",
            },
            {
                "键": "DIY",
                "按钮图": os.path.join(
                    根, "UI-img", "大模式选择界面", "按钮", "DIY乐谱模式按钮.png"
                ),
                "banner图": os.path.join(根, "UI-img", "大模式选择界面", "diy模式.png"),
                "文案": "diy乐谱模式：你能搞到.sm文件吗？",
                "songs子目录": "diy",
            },
            {
                "键": "WEF",
                "按钮图": os.path.join(
                    根, "UI-img", "大模式选择界面", "按钮", "wef模式按钮.png"
                ),
                "banner图": os.path.join(根, "UI-img", "大模式选择界面", "wef模式.png"),
                "文案": "wef联赛模式：不知道我还没玩过 所以这里没有内容",
                "songs子目录": "wef",
            },
        ]

        self._按钮列表: list[图片按钮] = []
        self._按钮键列表: list[str] = []
        for 配置 in self._模式列表:
            按钮 = 图片按钮(配置["键"], 配置["按钮图"])
            按钮.重新加载图片()
            self._按钮列表.append(按钮)
            self._按钮键列表.append(配置["键"])

        self._banner原图字典: dict[str, pygame.Surface | None] = {}
        for 配置 in self._模式列表:
            self._banner原图字典[配置["键"]] = 安全加载图片(配置["banner图"], 透明=True)

        self._当前选择键: str | None = None
        self._当前文案 = ""
        self._当前banner原图: pygame.Surface | None = None

        self._rect_banner槽位 = pygame.Rect(0, 0, 1, 1)
        self._rect_banner命中 = pygame.Rect(0, 0, 1, 1)

        self._缓存尺寸 = (0, 0)
        self._按钮基准rect: list[pygame.Rect] = [
            pygame.Rect(0, 0, 1, 1) for _ in self._按钮列表
        ]

        self._入场开始毫秒 = 0
        self._入场时长毫秒 = 700
        self._入场下移像素 = 120
        self._跳动周期毫秒 = 2000
        self._单个跳动时长毫秒 = 300
        self._跳动幅度 = 8

        self._可进入子模式集合 = {"花式", "竞速"}

        self._提示文本 = ""
        self._提示截止毫秒 = 0
        self._提示强调开始毫秒 = 0
        self._banner摇头开始毫秒 = 0
        self._banner摇头时长毫秒 = 340
        self._banner特效开始时间 = 0.0

        self._延迟目标场景: str | None = None

        self._banner当前图: pygame.Surface | None = None
        self._banner当前rect: pygame.Rect | None = None
        self._全屏放大过渡 = None
        self._正在放大切场景 = False

        self._背景压暗_alpha = 120
        self._文案遮罩alpha = 150
        self._文案整体上移像素 = 10

        self._纯色遮罩缓存: dict[
            tuple[int, int, tuple[int, int, int, int]], pygame.Surface
        ] = {}
        self._按钮缩放缓存: dict[tuple[str, int, int, int], pygame.Surface] = {}

    def 进入(self, 载荷=None):
        bgm = (
            self.上下文["资源"].get("back_music_ui")
            or self.上下文["资源"].get("音乐_UI")
            or self.上下文["资源"].get("投币_BGM")
        )
        if bgm:
            self.上下文["音乐"].播放循环(bgm)

        当前毫秒 = pygame.time.get_ticks()
        self._入场开始毫秒 = 当前毫秒
        self._当前选择键 = None
        self._当前文案 = ""
        self._当前banner原图 = None
        self._提示文本 = ""
        self._提示截止毫秒 = 0
        self._提示强调开始毫秒 = 0
        self._banner摇头开始毫秒 = 0
        self._banner特效开始时间 = 当前毫秒 / 1000.0
        self._延迟目标场景 = None
        self._按钮当前偏移x = {配置["键"]: 0.0 for 配置 in self._模式列表}
        self._选中开始毫秒 = 0
        self._banner当前图 = None
        self._banner当前rect = None
        self._全屏放大过渡 = 公用放大过渡器(总时长毫秒=400)
        self._正在放大切场景 = False

        pygame.time.set_timer(self._事件_延迟切场景, 0)

        self._缓存尺寸 = (0, 0)
        self._纯色遮罩缓存.clear()
        self._按钮缩放缓存.clear()
        self.重算布局()

    def 退出(self):
        pygame.time.set_timer(self._事件_延迟切场景, 0)

    def _取当前毫秒(self) -> int:
        return int(pygame.time.get_ticks())

    def _取纯色遮罩面(
        self,
        宽: int,
        高: int,
        颜色: tuple[int, int, int, int],
    ) -> pygame.Surface:
        缓存键 = (int(宽), int(高), tuple(颜色))
        已缓存 = self._纯色遮罩缓存.get(缓存键)
        if 已缓存 is not None:
            return 已缓存

        遮罩面 = pygame.Surface((max(1, 宽), max(1, 高)), pygame.SRCALPHA)
        遮罩面.fill(颜色)
        self._纯色遮罩缓存[缓存键] = 遮罩面
        return 遮罩面

    def _取按钮缓存图(
        self,
        按钮键: str,
        原图: pygame.Surface,
        宽: int,
        高: int,
        alpha: int,
    ) -> pygame.Surface:
        缓存键 = (按钮键, int(宽), int(高), int(alpha))
        已缓存 = self._按钮缩放缓存.get(缓存键)
        if 已缓存 is not None:
            return 已缓存

        缩放图 = pygame.transform.smoothscale(
            原图, (max(1, int(宽)), max(1, int(高)))
        ).convert_alpha()
        if int(alpha) < 255:
            缩放图.set_alpha(int(alpha))
        self._按钮缩放缓存[缓存键] = 缩放图
        return 缩放图

    def _更新推开动画(self):
        if not self._当前选择键:
            return

        from core.工具 import 计算推开偏移字典

        当前毫秒 = self._取当前毫秒()
        进度 = (当前毫秒 - int(self._选中开始毫秒)) / max(1, int(self._推开时长毫秒))
        进度 = max(0.0, min(1.0, float(进度)))
        缓动值 = 1.0 - (1.0 - 进度) ** 3

        目标rect列表 = [self._按钮基准rect[i] for i in range(len(self._按钮列表))]
        键列表 = self._按钮键列表[:]
        选中索引 = (
            max(0, 键列表.index(self._当前选择键)) if self._当前选择键 in 键列表 else 0
        )

        屏幕宽, _ = self.上下文["屏幕"].get_size()

        偏移列表 = 计算推开偏移字典(
            按钮目标矩形列表=目标rect列表,
            选中索引=选中索引,
            推开进度k=缓动值,
            屏幕宽=屏幕宽,
            屏幕边距=int(self._推开屏幕边距),
            间距缩放=float(self._推开间距缩放),
        )

        for 索引, 键 in enumerate(键列表):
            if 键 == self._当前选择键:
                self._按钮当前偏移x[键] = 0.0
            else:
                self._按钮当前偏移x[键] = float(偏移列表[索引])

    def _确保缓存(self):
        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()
        if (宽, 高) == self._缓存尺寸:
            return

        self._缓存尺寸 = (宽, 高)
        self._rect_top栏, self._top栏图, self._rect_top标题, self._top标题图 = (
            生成top栏(
                屏幕=屏幕,
                top背景原图=self._top栏原图,
                标题原图=self._top标题原图,
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
        )
        self._纯色遮罩缓存.clear()
        self._按钮缩放缓存.clear()

    def 重算布局(self):
        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()

        数量 = len(self._按钮列表)
        if 数量 <= 0:
            return

        按边 = int(min(宽, 高) * 0.22)
        按边 = max(170, min(240, 按边))
        按宽 = int(按边 * 1.05)
        按高 = int(按边 * 1.00)

        间距 = int(宽 * 0.015)
        间距 = max(14, min(28, 间距))
        总宽 = 数量 * 按宽 + (数量 - 1) * 间距
        起始x = (宽 - 总宽) // 2

        起始y = int(高 * 0.62)
        起始y = min(起始y, 高 - 按高 - int(高 * 0.14))

        for 索引, 按钮 in enumerate(self._按钮列表):
            矩形 = pygame.Rect(起始x + 索引 * (按宽 + 间距), 起始y, 按宽, 按高)
            self._按钮基准rect[索引] = 矩形
            按钮.设置矩形(矩形)

        banner宽 = int(宽 * 0.95)
        banner宽 = max(860, min(banner宽, int(宽 * 1.5)))
        banner高 = int(高 * 0.44)
        banner高 = max(320, min(banner高, int(高 * 0.62)))

        banner_x = (宽 - banner宽) // 2
        banner_y = self._按钮基准rect[0].top - banner高 - int(高 * 0.04)
        banner_y = max(int(高 * 0.12), banner_y)

        self._rect_banner槽位 = pygame.Rect(banner_x, banner_y, banner宽, banner高)
        self._rect_banner命中 = self._rect_banner槽位.copy()

    def _设置选择(self, 键: str):
        self._当前选择键 = 键
        self._当前banner原图 = self._banner原图字典.get(键)
        self._banner特效开始时间 = self._取当前毫秒() / 1000.0
        self._提示文本 = ""
        self._提示截止毫秒 = 0

        状态 = self.上下文.setdefault("状态", {})
        if not isinstance(状态, dict):
            状态 = {}
            self.上下文["状态"] = 状态

        for 配置 in self._模式列表:
            if 配置["键"] == 键:
                self._当前文案 = 配置["文案"]

                类型名 = str(配置.get("键", "") or "").strip()
                songs子目录 = str(配置.get("songs子目录", "") or 类型名).strip()

                状态["大模式"] = 类型名
                状态["songs子文件夹"] = songs子目录
                状态["选歌_类型"] = songs子目录 or 类型名
                状态["子模式"] = ""
                状态["选歌_模式"] = ""
                状态.pop("选歌_BGM", None)
                break

    def _取当前选择索引(self) -> int | None:
        if self._当前选择键 not in self._按钮键列表:
            return None
        return int(self._按钮键列表.index(self._当前选择键))

    def _踏板切换选择(self, 步进: int):
        if not self._按钮键列表:
            return None

        新索引 = 循环切换索引(
            self._取当前选择索引(),
            len(self._按钮键列表),
            int(步进),
            初始索引=0,
        )
        键 = self._按钮键列表[int(新索引)]
        if self._当前选择键 == 键:
            return None

        self._按钮音效.播放()
        self._选中开始毫秒 = self._取当前毫秒()
        if 键 not in self._按钮当前偏移x:
            self._按钮当前偏移x[键] = 0.0
        self._设置选择(键)
        return None

    def _触发不可用提示(self):
        当前毫秒 = self._取当前毫秒()
        self._提示文本 = "我还没写，所以点不动"
        self._提示截止毫秒 = 当前毫秒 + 1600
        self._提示强调开始毫秒 = 当前毫秒
        self._banner摇头开始毫秒 = 当前毫秒

    def _取banner摇头偏移(self) -> int:
        if self._banner摇头开始毫秒 <= 0:
            return 0

        当前毫秒 = self._取当前毫秒()
        进度 = (当前毫秒 - int(self._banner摇头开始毫秒)) / max(
            1, int(self._banner摇头时长毫秒)
        )
        if 进度 <= 0.0 or 进度 >= 1.0:
            return 0

        幅度 = 22.0 * (1.0 - float(进度) * 0.15)
        return int(math.sin(float(进度) * math.pi * 4.0) * 幅度)

    def _触发当前选择确认(self):
        if not self._当前选择键:
            return None

        self._按钮音效.播放()
        if self._当前选择键 in self._可进入子模式集合:
            if self._正在放大切场景:
                return None

            self._正在放大切场景 = True
            起始图 = self._banner当前图
            起始rect = self._banner当前rect

            if 起始rect is None:
                起始rect = self._rect_banner命中.copy()

            if 起始图 is None and self._当前banner原图 is not None:
                起始图 = pygame.transform.smoothscale(
                    self._当前banner原图,
                    (max(1, 起始rect.w), max(1, 起始rect.h)),
                ).convert_alpha()

            if 起始图 is not None and self._全屏放大过渡 is not None:
                self._全屏放大过渡.开始(起始图, 起始rect)
                self._延迟目标场景 = "子模式"
                pygame.time.set_timer(
                    self._事件_延迟切场景,
                    int(getattr(self._全屏放大过渡, "总时长毫秒", 520)),
                    loops=1,
                )
                return None

            self._延迟目标场景 = "子模式"
            pygame.time.set_timer(self._事件_延迟切场景, 300, loops=1)
            return None

        self._触发不可用提示()
        return None

    def _绘制未开放提示(self):
        当前毫秒 = self._取当前毫秒()
        if (not self._提示文本) or 当前毫秒 >= int(self._提示截止毫秒 or 0):
            return

        屏幕 = self.上下文["屏幕"]
        小字 = self.上下文["字体"]["小字"]
        宽, 高 = 屏幕.get_size()

        已过秒数 = max(0.0, (当前毫秒 - int(self._提示强调开始毫秒 or 0)) / 1000.0)
        脉冲 = 0.5 + 0.5 * math.sin(已过秒数 * 9.0)

        提示框宽 = min(int(宽 * 0.58), 860)
        提示框高 = max(82, int(高 * 0.09))
        提示框 = pygame.Rect(0, 0, 提示框宽, 提示框高)
        提示框.center = (宽 // 2, int(高 * 0.145))

        pygame.draw.rect(屏幕, (0, 0, 0), 提示框.move(0, 8), border_radius=28)

        面 = pygame.Surface((提示框.w, 提示框.h), pygame.SRCALPHA)
        pygame.draw.rect(面, (42, 18, 18, 228), 面.get_rect(), border_radius=28)
        高亮宽 = max(16, int(提示框.w * (0.16 + 0.04 * 脉冲)))
        pygame.draw.rect(
            面,
            (255, 115, 92, 120),
            pygame.Rect(18, 12, 高亮宽, 提示框.h - 24),
            border_radius=12,
        )
        pygame.draw.rect(
            面,
            (255, 193, 107),
            面.get_rect(),
            width=3,
            border_radius=28,
        )
        屏幕.blit(面, 提示框.topleft)

        标签色 = (255, 223, 180) if 脉冲 >= 0.5 else (255, 201, 147)
        提示色 = (255, 241, 220)

        绘制文本(
            屏幕,
            "UNAVAILABLE",
            小字,
            标签色,
            (提示框.centerx, 提示框.y + 24),
            "center",
        )
        绘制文本(
            屏幕,
            self._提示文本,
            小字,
            提示色,
            (提示框.centerx, 提示框.centery + 16),
            "center",
        )

    def _画背景(self):
        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()

        屏幕.fill((0, 0, 0))

        帧 = self._背景视频.读取帧() if self._背景视频 else None
        if 帧 is not None:
            屏幕.blit(cover缩放(帧, 宽, 高), (0, 0))
        else:
            背景图 = self.上下文.get("缓存", {}).get("背景图_模式")
            if 背景图:
                屏幕.blit(cover缩放(背景图, 宽, 高), (0, 0))

        alpha = max(0, min(255, int(getattr(self, "_背景压暗_alpha", 120))))
        if alpha > 0:
            背景遮罩面 = self._取纯色遮罩面(宽, 高, (0, 0, 0, alpha))
            屏幕.blit(背景遮罩面, (0, 0))

        self._确保缓存()

    def _画底部credit(self):
        from core.工具 import 绘制底部联网与信用

        屏幕 = self.上下文["屏幕"]
        字体_credit = self.上下文["字体"]["投币_credit字"]
        当前信用 = int(self.上下文.get("状态", {}).get("投币数", 0) or 0)
        所需信用 = int(self.上下文.get("状态", {}).get("每局所需信用", 3) or 3)

        绘制底部联网与信用(
            屏幕=屏幕,
            联网原图=self._联网原图,
            字体_credit=字体_credit,
            credit数值=f"{当前信用}/{所需信用}",
            总信用需求=所需信用,
        )

    def _获取入场偏移(self) -> int:
        当前毫秒 = self._取当前毫秒()
        已过毫秒 = 当前毫秒 - int(self._入场开始毫秒)
        if 已过毫秒 <= 0:
            return int(self._入场下移像素)
        if 已过毫秒 >= int(self._入场时长毫秒):
            return 0

        进度 = 已过毫秒 / max(1, int(self._入场时长毫秒))
        余量 = 1.0 - 进度
        return int(self._入场下移像素 * 余量)

    def _获取跳动偏移(self, 索引: int) -> int:
        当前毫秒 = self._取当前毫秒()
        if (当前毫秒 - int(self._入场开始毫秒)) < int(self._入场时长毫秒):
            return 0

        数量 = len(self._按钮列表)
        if 数量 <= 0:
            return 0

        周期毫秒 = int(self._跳动周期毫秒)
        单个时长毫秒 = int(self._单个跳动时长毫秒)

        总窗毫秒 = 数量 * 单个时长毫秒
        if 总窗毫秒 >= 周期毫秒:
            周期毫秒 = 总窗毫秒 + 200

        当前周期内毫秒 = 当前毫秒 % 周期毫秒
        开始毫秒 = 索引 * 单个时长毫秒
        结束毫秒 = 开始毫秒 + 单个时长毫秒
        if not (开始毫秒 <= 当前周期内毫秒 < 结束毫秒):
            return 0

        进度 = (当前周期内毫秒 - 开始毫秒) / max(1, 单个时长毫秒)
        振幅比 = (进度 / 0.5) if 进度 < 0.5 else ((1.0 - 进度) / 0.5)
        return -int(self._跳动幅度 * 振幅比)

    def _画按钮(self):
        屏幕 = self.上下文["屏幕"]

        当前毫秒 = self._取当前毫秒()
        入场进度 = (当前毫秒 - int(self._入场开始毫秒)) / max(
            1, int(self._入场时长毫秒)
        )
        入场进度 = max(0.0, min(1.0, 入场进度))

        缓动值 = 1.0 - (1.0 - 入场进度) ** 3
        缩放比 = 0.92 + (1.00 - 0.92) * 缓动值
        alpha = max(0, min(255, int(255 * 缓动值)))
        # 入场偏移 = self._获取入场偏移()
        # 此处特地这样写，避免在“入场动画结束但跳动动画未开始”时，按钮位置突然跳一下（因为入场偏移突然变为0了）
        入场偏移 = 0

        for 索引, 按钮 in enumerate(self._按钮列表):
            按钮键 = self._按钮键列表[索引]
            if self._当前选择键 == 按钮键:
                continue

            基准矩形 = self._按钮基准rect[索引]
            跳动偏移 = self._获取跳动偏移(索引)
            推开偏移 = float(self._按钮当前偏移x.get(按钮键, 0.0))
            当前矩形 = pygame.Rect(
                int(基准矩形.x + 推开偏移),
                int(基准矩形.y + 入场偏移 + 跳动偏移),
                基准矩形.w,
                基准矩形.h,
            )
            按钮.设置矩形(当前矩形)

            if getattr(按钮, "图片", None) is not None:
                目标宽 = max(1, int(当前矩形.w * 缩放比))
                目标高 = max(1, int(当前矩形.h * 缩放比))
                绘制图 = self._取按钮缓存图(
                    按钮键=按钮键,
                    原图=按钮.图片,
                    宽=目标宽,
                    高=目标高,
                    alpha=alpha,
                )
                绘制矩形 = 绘制图.get_rect()
                绘制矩形.center = 当前矩形.center
                屏幕.blit(绘制图, 绘制矩形.topleft)
            else:
                pygame.draw.rect(屏幕, (255, 255, 255), 当前矩形, width=2)

        for 索引, 按钮 in enumerate(self._按钮列表):
            按钮.设置矩形(self._按钮基准rect[索引])

    def _画banner与文案(self):
        屏幕 = self.上下文["屏幕"]
        屏宽, 屏高 = 屏幕.get_size()
        字体_文案 = self.上下文["字体"]["小字"]

        槽位矩形 = self._rect_banner槽位
        if not isinstance(槽位矩形, pygame.Rect):
            槽位矩形 = pygame.Rect(0, int(屏高 * 0.18), 屏宽, int(屏高 * 0.35))

        按钮顶边 = (
            int(self._按钮基准rect[0].top)
            if self._按钮基准rect and isinstance(self._按钮基准rect[0], pygame.Rect)
            else int(屏高 * 0.62)
        )

        文案y = 槽位矩形.bottom + int((按钮顶边 - 槽位矩形.bottom) * 0.40)
        文案y = max(槽位矩形.bottom + 6, min(文案y, 按钮顶边 - 12))
        文案y = int(文案y - int(getattr(self, "_文案整体上移像素", 10)))
        文案y = max(槽位矩形.bottom + 6, min(文案y, 按钮顶边 - 12))

        文案遮罩透明度 = max(0, min(255, int(getattr(self, "_文案遮罩alpha", 150))))
        文案字高 = int(字体_文案.get_height()) if 字体_文案 else 24
        文案上下内边距 = max(10, int(文案字高 * 0.60))
        文案遮罩条高 = max(32, 文案字高 + 文案上下内边距 * 2)
        文案遮罩条y = int(文案y - 文案遮罩条高 // 2)

        if 文案遮罩透明度 > 0:
            文案遮罩条面 = self._取纯色遮罩面(
                屏宽,
                文案遮罩条高,
                (0, 0, 0, 文案遮罩透明度),
            )
        else:
            文案遮罩条面 = None

        if not self._当前选择键:
            self._banner当前图 = None
            self._banner当前rect = None

            if 文案遮罩条面 is not None:
                屏幕.blit(文案遮罩条面, (0, 文案遮罩条y))

            绘制文本(
                屏幕,
                "请点击选择您喜欢的游戏模式",
                字体_文案,
                (255, 255, 255),
                (屏宽 // 2, 文案y),
                "center",
            )
            return

        实际矩形 = 槽位矩形.copy()
        可画图 = None

        if self._当前banner原图:
            槽宽, 槽高 = 槽位矩形.size
            原宽, 原高 = self._当前banner原图.get_size()
            缩放比例 = min(槽宽 / max(1, 原宽), 槽高 / max(1, 原高))
            新宽 = max(1, int(原宽 * 缩放比例))
            新高 = max(1, int(原高 * 缩放比例))
            可画图 = pygame.transform.smoothscale(
                self._当前banner原图, (新宽, 新高)
            ).convert_alpha()
            实际矩形 = 可画图.get_rect()
            实际矩形.center = 槽位矩形.center
            实际矩形.x += self._取banner摇头偏移()
            self._rect_banner命中 = 实际矩形
        else:
            self._rect_banner命中 = 槽位矩形.copy()

        self._banner当前图 = 可画图
        self._banner当前rect = 实际矩形.copy()

        if 可画图 is not None:
            动效进度 = (
                self._取当前毫秒() / 1000.0 - float(self._banner特效开始时间)
            ) / 0.26
            动效进度 = max(0.0, min(1.0, 动效进度))

            动效后矩形 = 绘制渐隐放大图(
                屏幕=屏幕,
                原图=可画图,
                基准rect=实际矩形,
                进度t=动效进度,
                基准宽=int(实际矩形.w),
                上移像素=0,
            )
            self._rect_banner命中 = 动效后矩形
            self._banner当前rect = 动效后矩形.copy()

        if self._当前文案:
            if 文案遮罩条面 is not None:
                屏幕.blit(文案遮罩条面, (0, 文案遮罩条y))

            绘制文本(
                屏幕,
                self._当前文案,
                字体_文案,
                (251, 200, 106),
                (屏宽 // 2, 文案y),
                "center",
            )

    def 绘制(self):
        屏幕 = self.上下文["屏幕"]

        self._画背景()

        if self._top栏图:
            屏幕.blit(self._top栏图, self._rect_top栏.topleft)
        if self._top标题图:
            屏幕.blit(self._top标题图, self._rect_top标题.topleft)

        self._画banner与文案()
        self._更新推开动画()
        self._画按钮()
        self._画底部credit()
        self._绘制未开放提示()

        if self._全屏放大过渡 is not None and self._全屏放大过渡.是否进行中():
            self._全屏放大过渡.更新并绘制(屏幕)

    def 处理全局踏板(self, 动作: str):
        if 动作 == 踏板动作_左:
            return self._踏板切换选择(-1)
        if 动作 == 踏板动作_右:
            return self._踏板切换选择(+1)
        if 动作 == 踏板动作_确认:
            return self._触发当前选择确认()
        return None

    def 处理事件(self, 事件):
        if 事件.type == pygame.VIDEORESIZE:
            self.重算布局()
            return None

        if 事件.type == pygame.KEYDOWN and 事件.key == pygame.K_ESCAPE:
            return 场景切换请求("玩家选择", 动作="REPLACE")

        if 事件.type == self._事件_延迟切场景:
            pygame.time.set_timer(self._事件_延迟切场景, 0)
            self._正在放大切场景 = False
            if self._延迟目标场景:
                目标场景 = self._延迟目标场景
                self._延迟目标场景 = None
                return {"切换到": 目标场景, "禁用黑屏过渡": True}
            return None

        if self._全屏放大过渡 is not None and self._全屏放大过渡.是否进行中():
            return None

        if self._当前选择键 and 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            if self._rect_banner命中.collidepoint(事件.pos):
                return self._触发当前选择确认()

        for 索引, 按钮 in enumerate(self._按钮列表):
            按钮键 = self._按钮键列表[索引]
            if self._当前选择键 == 按钮键:
                continue

            if 按钮.处理事件(事件):
                self._按钮音效.播放()
                self._选中开始毫秒 = self._取当前毫秒()
                if 按钮键 not in self._按钮当前偏移x:
                    self._按钮当前偏移x[按钮键] = 0.0
                self._设置选择(按钮键)
                return None

        return None
