import math
import os
import sys
import threading

import pygame

from core.常量与路径 import 拼资源路径, 取songs根目录
from core.日志 import (
    取日志器 as _取日志器,
    记录异常 as _记录异常日志,
    记录信息 as _记录信息日志,
)
from core.工具 import cover缩放, 安全加载图片, 获取字体, 绘制文本
from core.踏板控制 import (
    踏板动作_左,
    踏板动作_右,
    踏板动作_确认,
    循环切换索引,
)
from scenes.场景基类 import 场景基类, 场景切换请求
from ui.按钮特效 import 图片按钮
from ui.top栏 import 生成top栏
from ui.场景过渡 import 公用放大过渡器
from ui.按钮特效 import 公用按钮音效


_日志器 = _取日志器("scene.子模式")


class 场景_子模式(场景基类):
    名称 = "子模式"
    _设计宽 = 2048
    _设计高 = 1152

    def __init__(self, 上下文: dict):
        super().__init__(上下文)

        资源 = self.上下文.get("资源", {})
        self._资源 = 资源 if isinstance(资源, dict) else {}
        self._按钮音效 = 公用按钮音效(self._资源.get("按钮音效", ""))

        self._背景视频 = self.上下文.get("背景视频")
        self.子模式按钮列表: list[tuple[图片按钮, str, str, str]] = []

        self._进入开始毫秒: int = 0
        self._按钮目标矩形: dict[str, pygame.Rect] = {}
        self._按钮当前偏移y: dict[str, float] = {}
        self._按钮当前偏移x: dict[str, float] = {}
        self._按钮标签中心点: dict[str, tuple[int, int]] = {}

        self._当前选中模式名: str | None = None
        self._选中开始毫秒: int = 0
        self._隐藏按钮模式名: str | None = None

        self._大图标表面: pygame.Surface | None = None
        self._大图标矩形: pygame.Rect | None = None
        self._大图标路径缓存: str | None = None
        self._大图缓存: dict[str, pygame.Surface | None] = {}

        self._top栏背景原图: pygame.Surface | None = None
        self._top标题原图: pygame.Surface | None = None
        self._top_rect = pygame.Rect(0, 0, 1, 1)
        self._top图: pygame.Surface | None = None
        self._top标题rect = pygame.Rect(0, 0, 1, 1)
        self._top标题图: pygame.Surface | None = None
        self._top缓存尺寸 = (0, 0)

        self._联网原图: pygame.Surface | None = None
        self._子模式背景图表面: pygame.Surface | None = None

        self._按钮缩放缓存: dict[tuple[str, int, int], pygame.Surface] = {}
        self._纯色遮罩缓存: dict[tuple[int, int, int, int, int], pygame.Surface] = {}

        self._入场时长毫秒 = 1200
        self._入场每个延迟毫秒 = 90

        self._推开时长毫秒 = 320
        self._推开屏幕边距 = 24
        self._推开间距缩放 = 1.0

        self._大图动画时长毫秒 = 260
        self._背景遮罩alpha = 140

        self._全屏放大过渡 = 公用放大过渡器(总时长毫秒=320)
        self._待进入选歌模式名: str | None = None

        self._每行最大数量 = 6
        self._每页最大行数 = 3
        self._当前页码 = 0
        self._总页数 = 1
        self._当前按钮边长 = 0
        self._空状态提示 = ""
        self._DIY滚动偏移x = 0.0
        self._DIY最大滚动偏移x = 0.0
        self._DIY起始x = 0
        self._DIY可视基准宽 = 0
        self._DIY内容总宽 = 0
        self._选歌预热线程: threading.Thread | None = None
        self._选歌预热停止事件 = threading.Event()
        self._选歌预热任务签名: tuple[str, str, tuple[str, ...]] | None = None
        self._已提示打包禁用预热 = False

    def _夹紧(self, 值: float, 最小值: float, 最大值: float) -> float:
        return max(最小值, min(最大值, 值))

    def _缓出(self, 进度: float) -> float:
        进度 = self._夹紧(进度, 0.0, 1.0)
        return 1 - (1 - 进度) ** 3

    def _弹跳回弹(self, 进度: float) -> float:
        进度 = self._夹紧(进度, 0.0, 1.0)
        系数 = 1.70158
        进度 -= 1
        return 进度 * 进度 * ((系数 + 1) * 进度 + 系数) + 1

    def _插值(self, 起点: float, 终点: float, 进度: float) -> float:
        return 起点 + (终点 - 起点) * 进度

    def _取纯色遮罩面(
        self,
        宽: int,
        高: int,
        红: int,
        绿: int,
        蓝: int,
        透明度: int,
    ) -> pygame.Surface:
        缓存键 = (宽, 高, 红, 绿, 蓝, 透明度)
        已缓存 = self._纯色遮罩缓存.get(缓存键)
        if 已缓存 is not None:
            return 已缓存

        遮罩面 = pygame.Surface((max(1, 宽), max(1, 高)), pygame.SRCALPHA)
        遮罩面.fill((红, 绿, 蓝, 透明度))
        self._纯色遮罩缓存[缓存键] = 遮罩面
        return 遮罩面

    def _取资源路径(self, *片段: str) -> str:
        return 拼资源路径(*片段, 资源=self._资源)

    def _当前是否DIY模式(self) -> bool:
        状态 = self.上下文.get("状态", {})
        if not isinstance(状态, dict):
            return False
        return str(状态.get("大模式", "") or "").strip().lower() == "diy"

    def _DIY可滚动(self) -> bool:
        return self._当前是否DIY模式() and float(self._DIY最大滚动偏移x) > 0.0

    def _取DIY滚轮步长(self) -> float:
        return float(max(96, int(self._当前按钮边长 * 0.90)))

    def _设置DIY滚动偏移(self, 偏移x: float):
        self._DIY滚动偏移x = float(
            self._夹紧(float(偏移x), 0.0, float(self._DIY最大滚动偏移x))
        )

    def _滚动DIY列表(self, 偏移量: float, *, 播放音效: bool = False) -> bool:
        if not self._DIY可滚动():
            return False

        旧值 = float(self._DIY滚动偏移x)
        self._设置DIY滚动偏移(旧值 + float(偏移量))
        if abs(float(self._DIY滚动偏移x) - 旧值) < 0.5:
            return False

        if 播放音效:
            self._按钮音效.播放()
        return True

    def _确保DIY模式可见(self, 模式名: str | None):
        if (not self._当前是否DIY模式()) or (not 模式名):
            return

        目标矩形 = self._按钮目标矩形.get(str(模式名))
        if not isinstance(目标矩形, pygame.Rect):
            return

        视口左 = int(self._DIY起始x)
        视口右 = int(self._DIY起始x + self._DIY可视基准宽)
        if 视口右 <= 视口左:
            return

        当前左 = float(目标矩形.left) - float(self._DIY滚动偏移x)
        当前右 = float(目标矩形.right) - float(self._DIY滚动偏移x)
        边距 = max(16, int(目标矩形.w * 0.18))

        新偏移 = float(self._DIY滚动偏移x)
        if 当前左 < float(视口左 + 边距):
            新偏移 -= float(视口左 + 边距) - 当前左
        elif 当前右 > float(视口右 - 边距):
            新偏移 += 当前右 - float(视口右 - 边距)

        self._设置DIY滚动偏移(新偏移)

    def _每页容量(self) -> int:
        return int(self._每行最大数量 * self._每页最大行数)

    def _取当前页范围(self) -> tuple[int, int]:
        if self._当前是否DIY模式():
            return 0, len(self.子模式按钮列表)
        每页容量 = max(1, self._每页容量())
        起始 = max(0, int(self._当前页码) * 每页容量)
        结束 = min(len(self.子模式按钮列表), 起始 + 每页容量)
        return 起始, 结束

    def _取当前页按钮项(self) -> list[tuple[图片按钮, str, str, str]]:
        起始, 结束 = self._取当前页范围()
        return self.子模式按钮列表[起始:结束]

    def _取模式所在页(self, 模式名: str | None) -> int | None:
        if not 模式名:
            return None
        if self._当前是否DIY模式():
            for _索引, (_按钮, 当前模式名, _小图, _大图) in enumerate(self.子模式按钮列表):
                if 当前模式名 == 模式名:
                    return 0
            return None
        每页容量 = max(1, self._每页容量())
        for 索引, (_按钮, 当前模式名, _小图, _大图) in enumerate(self.子模式按钮列表):
            if 当前模式名 == 模式名:
                return 索引 // 每页容量
        return None

    def _取当前页起始索引(self) -> int:
        if not self.子模式按钮列表:
            return 0
        if self._当前是否DIY模式():
            return 0
        起始, _ = self._取当前页范围()
        return max(0, min(len(self.子模式按钮列表) - 1, 起始))

    def _清空当前选中(self):
        self._当前选中模式名 = None
        self._选中开始毫秒 = 0
        self._隐藏按钮模式名 = None
        self._待进入选歌模式名 = None
        self._大图标表面 = None
        self._大图标矩形 = None
        self._大图标路径缓存 = None

    def _截断DIY标签(self, 文本: str, 最大字符数: int = 7) -> str:
        文本 = str(文本 or "").strip()
        if len(文本) <= int(最大字符数):
            return 文本
        可见字符数 = max(1, int(最大字符数) - 1)
        return f"{文本[:可见字符数]}…"

    def _取DIY标签字体(self) -> pygame.font.Font:
        字号 = max(18, min(30, int(self._当前按钮边长 * 0.13)))
        return 获取字体(字号)

    def _取DIY曲包目录列表(self) -> list[str]:
        状态 = self.上下文.get("状态", {})
        if not isinstance(状态, dict):
            状态 = {}

        songs根目录 = 取songs根目录(资源=self._资源, 状态=状态)
        diy目录 = os.path.join(songs根目录, "diy")
        if not os.path.isdir(diy目录):
            self._空状态提示 = "请将曲包文件夹放到 songs/diy 目录"
            return []

        目录列表: list[str] = []
        try:
            for 名称 in os.listdir(diy目录):
                if not str(名称 or "").strip():
                    continue
                完整路径 = os.path.join(diy目录, str(名称))
                if os.path.isdir(完整路径):
                    目录列表.append(str(名称))
        except Exception:
            self._空状态提示 = "读取 songs/diy 目录失败"
            return []

        目录列表.sort(key=lambda 名称: str(名称).casefold())
        if not 目录列表:
            self._空状态提示 = "请将曲包文件夹放到 songs/diy 目录"
        return 目录列表

    def _取模式配置列表(self) -> list[tuple[str, str, str]]:
        状态 = self.上下文.get("状态", {})
        大模式 = str(状态.get("大模式", "") or "").strip()
        大模式小写 = 大模式.lower()
        self._空状态提示 = ""

        if 大模式 == "花式":
            return [
                (
                    "学习",
                    self._取资源路径("UI-img/玩法选择界面/按钮/学习模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/学习模式.png"),
                ),
                (
                    "表演",
                    self._取资源路径("UI-img/玩法选择界面/按钮/表演模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/表演模式.png"),
                ),
                (
                    "疯狂",
                    self._取资源路径("UI-img/玩法选择界面/按钮/疯狂模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/疯狂模式.png"),
                ),
                (
                    "club",
                    self._取资源路径("UI-img/玩法选择界面/按钮/club模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/双踏板模式.png"),
                ),
                (
                    "情侣",
                    self._取资源路径("UI-img/玩法选择界面/按钮/情侣模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/情侣模式.png"),
                ),
                (
                    "混音",
                    self._取资源路径("UI-img/玩法选择界面/按钮/混音模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/混音模式.png"),
                ),
            ]

        if 大模式 == "竞速":
            return [
                (
                    "疯狂",
                    self._取资源路径("UI-img/玩法选择界面/按钮/疯狂模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/疯狂模式.png"),
                ),
                (
                    "club",
                    self._取资源路径("UI-img/玩法选择界面/按钮/club模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/双踏板模式.png"),
                ),
                (
                    "情侣",
                    self._取资源路径("UI-img/玩法选择界面/按钮/情侣模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/情侣模式.png"),
                ),
                (
                    "混音",
                    self._取资源路径("UI-img/玩法选择界面/按钮/混音模式按钮.png"),
                    self._取资源路径("UI-img/玩法选择界面/混音模式.png"),
                ),
            ]

        if 大模式小写 == "diy":
            曲包目录列表 = self._取DIY曲包目录列表()
            if not 曲包目录列表:
                return []

            按钮图路径 = self._取资源路径(
                "UI-img/玩法选择界面/按钮/diy模式按钮.png"
            )
            大图路径 = self._取资源路径("UI-img/玩法选择界面/diy模式.png")
            return [(曲包名, 按钮图路径, 大图路径) for 曲包名 in 曲包目录列表]

        return []

    def 子模式对应选歌BGM(self, 子模式名: str) -> str:
        if self._当前是否DIY模式():
            return str(self._资源.get("音乐_show", "") or "")
        if "表演" in 子模式名:
            return str(self._资源.get("音乐_show", "") or "")
        if "疯狂" in 子模式名:
            return str(self._资源.get("音乐_devil", "") or "")
        if "混音" in 子模式名:
            return str(self._资源.get("音乐_remix", "") or "")
        if "club" in 子模式名.lower():
            return str(self._资源.get("音乐_club", "") or "")
        return str(self._资源.get("音乐_UI", "") or "")

    def 进入(self, 载荷=None):
        背景音乐 = (
            self._资源.get("音乐_UI")
            or self._资源.get("back_music_ui")
            or self._资源.get("投币_BGM")
        )
        if 背景音乐:
            self.上下文["音乐"].播放循环(背景音乐)

        self._进入开始毫秒 = pygame.time.get_ticks()
        self._清空当前选中()
        self._按钮缩放缓存.clear()
        self._纯色遮罩缓存.clear()
        self._全屏放大过渡 = 公用放大过渡器(总时长毫秒=320)
        self._当前页码 = 0
        self._总页数 = 1
        self._当前按钮边长 = 0
        self._空状态提示 = ""
        self._DIY滚动偏移x = 0.0
        self._DIY最大滚动偏移x = 0.0
        self._DIY起始x = 0
        self._DIY可视基准宽 = 0
        self._DIY内容总宽 = 0

        self._预加载固定UI()
        self.重算布局()
        self._安排选歌预热()

    def 退出(self):
        self._停止选歌预热()

    def _预加载固定UI(self):
        self._top栏背景原图 = 安全加载图片(
            self._取资源路径("UI-img", "top栏", "top栏背景.png"),
            透明=True,
        )
        self._top标题原图 = 安全加载图片(
            self._取资源路径("UI-img", "top栏", "玩法选择.png"),
            透明=True,
        )
        self._联网原图 = 安全加载图片(
            self._资源.get("投币_联网图标", ""),
            透明=True,
        )

        背景路径 = str(self._资源.get("背景_子模式", "") or "")
        self._子模式背景图表面 = (
            安全加载图片(背景路径, 透明=False) if 背景路径 else None
        )

        self._top缓存尺寸 = (0, 0)
        self._确保top栏缓存()

    def _确保top栏缓存(self):
        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()
        if self._top缓存尺寸 == (宽, 高):
            return

        self._top缓存尺寸 = (宽, 高)
        self._top_rect, self._top图, self._top标题rect, self._top标题图 = 生成top栏(
            屏幕=屏幕,
            top背景原图=self._top栏背景原图,
            标题原图=self._top标题原图,
            设计宽=self._设计宽,
            设计高=self._设计高,
            top设计高=150,
            top背景宽占比=1.0,
            top背景高占比=1.0,
            标题最大宽占比=0.5,
            标题最大高占比=0.6,
            标题整体缩放=1.0,
            标题上移比例=0.1,
        )

    def _更新当前页布局(
        self,
        *,
        重置入场: bool = False,
        重置水平偏移: bool = False,
    ):
        self._确保top栏缓存()

        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()
        基准缩放 = min(宽 / max(1, self._设计宽), 高 / max(1, self._设计高))

        self._按钮标签中心点.clear()
        不可见矩形 = pygame.Rect(-20000, -20000, 1, 1)
        for 按钮, 模式名, _小图, _大图 in self.子模式按钮列表:
            self._按钮目标矩形[模式名] = 不可见矩形.copy()
            按钮.设置矩形(不可见矩形.copy())
            if 重置水平偏移:
                self._按钮当前偏移x[模式名] = 0.0
            if 重置入场:
                self._按钮当前偏移y[模式名] = 0.0

        可见按钮项 = self._取当前页按钮项()
        if not 可见按钮项:
            self._当前按钮边长 = 0
            self._DIY最大滚动偏移x = 0.0
            self._DIY可视基准宽 = 0
            self._DIY内容总宽 = 0
            return

        if self._当前是否DIY模式():
            可见数量 = len(可见按钮项)
            标签高度 = max(24, int(34 * 基准缩放))
            标签间距 = max(8, int(14 * 基准缩放))

            if 可见数量 == 1:
                按钮边长 = int(min(宽, 高) * 0.28)
                按钮边长 = max(150, min(360, 按钮边长))
            else:
                按钮边长 = int(min(宽, 高) * 0.22)
                按钮边长 = max(120, min(280, 按钮边长))

            间距x = int(宽 * 0.025)
            间距x = max(8, min(36, 间距x))

            基准显示数量 = max(1, min(self._每行最大数量, 可见数量))
            基准宽 = 基准显示数量 * 按钮边长 + max(0, 基准显示数量 - 1) * 间距x
            起始x = (宽 - 基准宽) // 2
            起始y = (高 // 2) - (按钮边长 // 2) + int(self._top_rect.h * 0.20)
            起始y = max(
                self._top_rect.bottom + max(18, int(20 * 基准缩放)),
                min(
                    起始y,
                    高 - 按钮边长 - 标签间距 - 标签高度 - max(24, int(20 * 基准缩放)),
                ),
            )

            总宽 = 可见数量 * 按钮边长 + max(0, 可见数量 - 1) * 间距x
            self._当前按钮边长 = int(按钮边长)
            self._DIY起始x = int(起始x)
            self._DIY可视基准宽 = int(基准宽)
            self._DIY内容总宽 = int(总宽)
            self._DIY最大滚动偏移x = float(max(0, int(总宽 - 基准宽)))
            self._设置DIY滚动偏移(self._DIY滚动偏移x)

            for 列索引, (按钮, 模式名, _小图, _大图) in enumerate(可见按钮项):
                目标矩形 = pygame.Rect(
                    起始x + 列索引 * (按钮边长 + 间距x),
                    起始y,
                    按钮边长,
                    按钮边长,
                )
                按钮.设置矩形(目标矩形)

                self._按钮目标矩形[模式名] = 目标矩形
                self._按钮标签中心点[模式名] = (
                    目标矩形.centerx,
                    目标矩形.bottom + 标签间距 + 标签高度 // 2,
                )

                if 重置入场:
                    self._按钮当前偏移y[模式名] = float(
                        高 - 起始y + 按钮边长 + 80
                    )
                else:
                    self._按钮当前偏移y[模式名] = float(
                        self._按钮当前偏移y.get(模式名, 0.0)
                    )

                if 重置水平偏移:
                    self._按钮当前偏移x[模式名] = 0.0
                else:
                    self._按钮当前偏移x[模式名] = float(
                        self._按钮当前偏移x.get(模式名, 0.0)
                    )
            return

        可见数量 = len(可见按钮项)
        行数 = max(1, math.ceil(可见数量 / max(1, self._每行最大数量)))
        标签高度 = max(24, int(34 * 基准缩放))
        标签间距 = max(8, int(14 * 基准缩放))
        行间距 = max(18, int(30 * 基准缩放))

        if 行数 == 1:
            if 可见数量 == 1:
                按钮边长 = int(min(宽, 高) * 0.28)
                按钮边长 = max(150, min(360, 按钮边长))
            else:
                按钮边长 = int(min(宽, 高) * 0.22)
                按钮边长 = max(120, min(280, 按钮边长))
        else:
            容器顶 = self._top_rect.bottom + max(24, int(36 * 基准缩放))
            容器底 = 高 - max(120, int(140 * 基准缩放))
            可用高 = max(1, 容器底 - 容器顶)
            高度限制 = int(
                (
                    可用高
                    - 行数 * (标签高度 + 标签间距)
                    - max(0, 行数 - 1) * 行间距
                )
                / max(1, 行数)
            )
            默认多行边长 = int(min(宽, 高) * (0.20 if 行数 == 2 else 0.18))
            按钮边长 = max(110, min(240, 默认多行边长, max(110, 高度限制)))

        间距x = int(宽 * (0.025 if 行数 == 1 else 0.018))
        间距x = max(8, min(36 if 行数 == 1 else 28, 间距x))

        if 行数 == 1:
            起始y = (高 // 2) - (按钮边长 // 2) + int(self._top_rect.h * 0.20)
            起始y = max(
                self._top_rect.bottom + max(18, int(20 * 基准缩放)),
                min(
                    起始y,
                    高 - 按钮边长 - 标签间距 - 标签高度 - max(24, int(20 * 基准缩放)),
                ),
            )
        else:
            容器顶 = self._top_rect.bottom + max(24, int(30 * 基准缩放))
            容器底 = 高 - max(120, int(140 * 基准缩放))
            总高 = (
                行数 * 按钮边长
                + 行数 * (标签间距 + 标签高度)
                + max(0, 行数 - 1) * 行间距
            )
            起始y = 容器顶 + max(0, (容器底 - 容器顶 - 总高) // 2)

        self._当前按钮边长 = int(按钮边长)

        for 行索引 in range(行数):
            行起始 = 行索引 * self._每行最大数量
            行按钮项 = 可见按钮项[行起始 : 行起始 + self._每行最大数量]
            行内数量 = len(行按钮项)
            if 行内数量 <= 0:
                continue

            总宽 = 行内数量 * 按钮边长 + (行内数量 - 1) * 间距x
            起始x = (宽 - 总宽) // 2
            按钮y = 起始y + 行索引 * (
                按钮边长 + 标签间距 + 标签高度 + 行间距
            )

            for 列索引, (按钮, 模式名, _小图, _大图) in enumerate(行按钮项):
                目标矩形 = pygame.Rect(
                    起始x + 列索引 * (按钮边长 + 间距x),
                    按钮y,
                    按钮边长,
                    按钮边长,
                )
                按钮.设置矩形(目标矩形)

                self._按钮目标矩形[模式名] = 目标矩形
                self._按钮标签中心点[模式名] = (
                    目标矩形.centerx,
                    目标矩形.bottom + 标签间距 + 标签高度 // 2,
                )

                if 重置入场:
                    self._按钮当前偏移y[模式名] = float(
                        高 - 按钮y + 按钮边长 + 80
                    )
                else:
                    self._按钮当前偏移y[模式名] = float(
                        self._按钮当前偏移y.get(模式名, 0.0)
                    )

                if 重置水平偏移:
                    self._按钮当前偏移x[模式名] = 0.0
                else:
                    self._按钮当前偏移x[模式名] = float(
                        self._按钮当前偏移x.get(模式名, 0.0)
                    )

    def 重算布局(self):
        self._确保top栏缓存()

        self.子模式按钮列表.clear()
        self._按钮目标矩形.clear()
        self._按钮当前偏移y.clear()
        self._按钮当前偏移x.clear()
        self._按钮标签中心点.clear()
        self._按钮缩放缓存.clear()

        模式列表 = self._取模式配置列表()
        if self._当前是否DIY模式():
            self._总页数 = 1
        else:
            self._总页数 = (
                max(1, math.ceil(len(模式列表) / max(1, self._每页容量())))
                if 模式列表
                else 1
            )

        for 模式名, 小按钮图路径, 大图路径 in 模式列表:
            按钮 = 图片按钮(模式名, 小按钮图路径)
            按钮.重新加载图片()

            self.子模式按钮列表.append((按钮, 模式名, 小按钮图路径, 大图路径))
            self._按钮目标矩形[模式名] = pygame.Rect(-20000, -20000, 1, 1)
            self._按钮当前偏移y[模式名] = 0.0
            self._按钮当前偏移x[模式名] = 0.0

        if self._当前选中模式名:
            选中页码 = self._取模式所在页(self._当前选中模式名)
            if 选中页码 is not None:
                self._当前页码 = int(选中页码)

        self._当前页码 = max(0, min(self._当前页码, self._总页数 - 1))

        if not self.子模式按钮列表:
            self._当前按钮边长 = 0
            return

        self._更新当前页布局(重置入场=True, 重置水平偏移=True)
        self._安排选歌预热()

    def _切换到页(
        self,
        目标页码: int,
        *,
        保留当前选中: bool = False,
        播放音效: bool = False,
    ) -> bool:
        if self._当前是否DIY模式():
            return False
        if self._总页数 <= 1:
            return False

        新页码 = max(0, min(int(目标页码), self._总页数 - 1))
        if 新页码 == self._当前页码:
            return False

        self._当前页码 = int(新页码)
        if (not 保留当前选中) and (
            self._取模式所在页(self._当前选中模式名) != self._当前页码
        ):
            self._清空当前选中()

        self._更新当前页布局(重置入场=False, 重置水平偏移=True)

        if 播放音效:
            self._按钮音效.播放()
        self._安排选歌预热()
        return True

    def _应用模式选中(self, 模式名: str):
        if self._当前是否DIY模式():
            self._确保DIY模式可见(模式名)
        self._当前选中模式名 = 模式名
        self._选中开始毫秒 = pygame.time.get_ticks()
        self._隐藏按钮模式名 = 模式名
        self._大图标表面 = None
        self._大图标路径缓存 = None
        self._安排选歌预热()
        return None

    def _取选歌预热任务(self) -> tuple[str, str, list[str]]:
        状态 = self.上下文.get("状态", {})
        if not isinstance(状态, dict):
            状态 = {}

        songs根目录 = 取songs根目录(资源=self._资源, 状态=状态)
        类型名 = str(
            状态.get("songs子文件夹", "")
            or 状态.get("选歌_类型", "")
            or 状态.get("大模式", "")
            or ""
        ).strip()
        if (not songs根目录) or (not 类型名):
            return "", "", []

        任务模式列表: list[str] = []

        def _加入模式(模式名: object):
            文本 = str(模式名 or "").strip()
            if (not 文本) or (文本 in 任务模式列表):
                return
            任务模式列表.append(文本)

        当前页按钮项 = self._取当前页按钮项()
        if self._当前是否DIY模式():
            _加入模式(self._当前选中模式名)
            if not 任务模式列表:
                for _按钮, 模式名, _小图, _大图 in 当前页按钮项[:2]:
                    _加入模式(模式名)
        else:
            for _按钮, 模式名, _小图, _大图 in 当前页按钮项:
                _加入模式(模式名)

        return str(songs根目录), str(类型名), 任务模式列表

    def _停止选歌预热(self, 等待秒: float = 0.08) -> bool:
        try:
            self._选歌预热停止事件.set()
        except Exception:
            pass

        线程 = getattr(self, "_选歌预热线程", None)
        仍存活 = False
        if (
            isinstance(线程, threading.Thread)
            and 线程.is_alive()
            and 线程 is not threading.current_thread()
        ):
            try:
                线程.join(timeout=max(0.0, float(等待秒)))
            except Exception:
                pass
            仍存活 = bool(线程.is_alive())

        if bool(仍存活):
            return False
        self._选歌预热线程 = None
        self._选歌预热任务签名 = None
        return True

    def _选歌预热线程主函数(
        self,
        songs根目录: str,
        类型名: str,
        模式列表: list[str],
        停止事件: threading.Event,
    ):
        try:
            from scenes.场景_选歌 import 扫描songs_指定路径
        except Exception as 异常:
            _记录异常日志(_日志器, "子模式预热导入选歌扫描函数失败", 异常)
            return

        for 模式名 in list(模式列表 or []):
            if bool(停止事件.is_set()):
                return
            try:
                扫描songs_指定路径(str(songs根目录), str(类型名), str(模式名))
            except Exception as 异常:
                _记录异常日志(
                    _日志器,
                    f"子模式预热扫描失败 类型={类型名} 模式={模式名}",
                    异常,
                )
                continue

    def _安排选歌预热(self):
        if bool(getattr(sys, "frozen", False)):
            self._停止选歌预热(等待秒=0.02)
            if not bool(getattr(self, "_已提示打包禁用预热", False)):
                _记录信息日志(_日志器, "打包环境已禁用子模式选歌预热线程")
                self._已提示打包禁用预热 = True
            return

        songs根目录, 类型名, 模式列表 = self._取选歌预热任务()
        if (not songs根目录) or (not 类型名) or (not 模式列表):
            self._停止选歌预热(等待秒=0.02)
            return

        任务签名 = (
            str(songs根目录),
            str(类型名),
            tuple(str(模式名) for 模式名 in 模式列表),
        )
        if 任务签名 == getattr(self, "_选歌预热任务签名", None):
            线程 = getattr(self, "_选歌预热线程", None)
            if isinstance(线程, threading.Thread) and 线程.is_alive():
                return

        if not bool(self._停止选歌预热(等待秒=0.02)):
            return
        self._选歌预热任务签名 = 任务签名
        self._选歌预热停止事件 = threading.Event()
        self._选歌预热线程 = threading.Thread(
            target=self._选歌预热线程主函数,
            args=(
                str(songs根目录),
                str(类型名),
                list(模式列表),
                self._选歌预热停止事件,
            ),
            name="submode-select-prewarm",
            daemon=True,
        )
        try:
            self._选歌预热线程.start()
        except Exception as 异常:
            _记录异常日志(_日志器, "启动子模式选歌预热线程失败", 异常)
            self._选歌预热线程 = None
            self._选歌预热任务签名 = None

    def _取当前选中索引(self) -> int | None:
        if not self.子模式按钮列表 or (not self._当前选中模式名):
            return None

        for 索引, (_按钮, 模式名, _小图, _大图) in enumerate(self.子模式按钮列表):
            if 模式名 == self._当前选中模式名:
                return 索引
        return None

    def _踏板切换模式(self, 步进: int):
        if not self.子模式按钮列表:
            return None

        新索引 = 循环切换索引(
            self._取当前选中索引(),
            len(self.子模式按钮列表),
            int(步进),
            初始索引=self._取当前页起始索引(),
        )
        _按钮, 模式名, _小图, _大图 = self.子模式按钮列表[int(新索引)]

        目标页码 = self._取模式所在页(模式名)
        if (not self._当前是否DIY模式()) and 目标页码 is not None and 目标页码 != self._当前页码:
            self._切换到页(目标页码, 保留当前选中=False, 播放音效=False)

        if self._当前选中模式名 == 模式名:
            return None

        self._按钮音效.播放()
        return self._应用模式选中(str(模式名))

    def _触发当前模式确认(self):
        if (not self._当前选中模式名) or self._全屏放大过渡.是否进行中():
            return None

        self._待进入选歌模式名 = self._当前选中模式名
        if self._大图标表面 and self._大图标矩形:
            过渡起始图 = pygame.transform.smoothscale(
                self._大图标表面,
                (self._大图标矩形.w, self._大图标矩形.h),
            ).convert_alpha()
            self._全屏放大过渡.开始(过渡起始图, self._大图标矩形)
        return None

    def _画背景(self):
        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()

        屏幕.fill((0, 0, 0))

        帧 = self._背景视频.读取帧() if self._背景视频 else None
        if 帧 is not None:
            屏幕.blit(cover缩放(帧, 宽, 高), (0, 0))
        elif self._子模式背景图表面:
            屏幕.blit(cover缩放(self._子模式背景图表面, 宽, 高), (0, 0))
        else:
            屏幕.fill((10, 12, 18))

        背景遮罩透明度 = max(0, min(255, int(self._背景遮罩alpha)))
        if 背景遮罩透明度 > 0:
            背景遮罩面 = self._取纯色遮罩面(
                宽,
                高,
                0,
                0,
                0,
                背景遮罩透明度,
            )
            屏幕.blit(背景遮罩面, (0, 0))

    def _画顶栏(self):
        self._确保top栏缓存()
        屏幕 = self.上下文["屏幕"]

        if self._top图:
            屏幕.blit(self._top图, self._top_rect.topleft)
        else:
            pygame.draw.rect(屏幕, (8, 20, 40), self._top_rect)

        if self._top标题图:
            屏幕.blit(self._top标题图, self._top标题rect.topleft)

    def _画底部联网与credit(self):
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

    def _更新动画(self):
        当前毫秒 = pygame.time.get_ticks()
        入场时长 = int(self._入场时长毫秒)
        每个延迟 = int(self._入场每个延迟毫秒)
        当前页按钮项 = self._取当前页按钮项()

        for 索引, (_按钮, 模式名, _小图, _大图) in enumerate(当前页按钮项):
            起始毫秒 = self._进入开始毫秒 + 索引 * 每个延迟
            进度 = (当前毫秒 - 起始毫秒) / max(1, 入场时长)

            if 进度 <= 0:
                continue
            if 进度 >= 1:
                self._按钮当前偏移y[模式名] = 0.0
            else:
                起始偏移 = float(self._按钮目标矩形[模式名].height + 220)
                偏移y = self._插值(起始偏移, 0.0, self._弹跳回弹(进度))
                self._按钮当前偏移y[模式名] = 偏移y

        if 当前毫秒 - self._进入开始毫秒 > 入场时长 and (self._当前选中模式名 is None):
            波浪幅度 = 6.0
            波浪周期 = 1100.0
            for 索引, (_按钮, 模式名, _小图, _大图) in enumerate(当前页按钮项):
                相位 = 索引 * 0.55
                偏移y = math.sin((当前毫秒 / 波浪周期) * 2 * math.pi + 相位) * 波浪幅度
                self._按钮当前偏移y[模式名] = 偏移y

        if self._当前选中模式名:
            if self._当前是否DIY模式():
                for _按钮, 模式名, _小图, _大图 in 当前页按钮项:
                    self._按钮当前偏移x[模式名] = 0.0
                return

            from core.工具 import 计算推开偏移字典

            推开时长 = int(self._推开时长毫秒)
            进度 = (当前毫秒 - self._选中开始毫秒) / max(1, 推开时长)
            进度 = self._夹紧(进度, 0.0, 1.0)
            缓动值 = self._缓出(进度)

            选中索引 = 0
            for 索引, (_按钮, 模式名, _小图, _大图) in enumerate(当前页按钮项):
                if 模式名 == self._当前选中模式名:
                    选中索引 = 索引
                    break

            目标矩形列表: list[pygame.Rect] = []
            模式名列表: list[str] = []
            for _按钮, 模式名, _小图, _大图 in 当前页按钮项:
                目标矩形列表.append(self._按钮目标矩形[模式名])
                模式名列表.append(模式名)

            屏幕宽, _ = self.上下文["屏幕"].get_size()
            偏移x列表 = 计算推开偏移字典(
                按钮目标矩形列表=目标矩形列表,
                选中索引=选中索引,
                推开进度k=缓动值,
                屏幕宽=屏幕宽,
                屏幕边距=int(self._推开屏幕边距),
                间距缩放=float(self._推开间距缩放),
            )

            for 索引, 模式名 in enumerate(模式名列表):
                if 模式名 == self._当前选中模式名:
                    self._按钮当前偏移x[模式名] = 0.0
                else:
                    self._按钮当前偏移x[模式名] = float(偏移x列表[索引])

    def _画子模式按钮(self):
        屏幕 = self.上下文["屏幕"]
        DIY滚动偏移x = -float(self._DIY滚动偏移x) if self._当前是否DIY模式() else 0.0

        for 按钮, 模式名, _小图, _大图 in self._取当前页按钮项():
            if self._隐藏按钮模式名 and 模式名 == self._隐藏按钮模式名:
                continue

            目标矩形 = self._按钮目标矩形[模式名]
            偏移x = self._按钮当前偏移x.get(模式名, 0.0) + DIY滚动偏移x
            偏移y = self._按钮当前偏移y.get(模式名, 0.0)

            当前矩形 = pygame.Rect(
                int(目标矩形.x + 偏移x),
                int(目标矩形.y + 偏移y),
                目标矩形.width,
                目标矩形.height,
            )
            按钮.设置矩形(当前矩形)

            原图 = getattr(按钮, "图片", None)
            if 原图 is None:
                pygame.draw.rect(屏幕, (255, 255, 255), 当前矩形, width=2)
                continue

            缓存键 = (模式名, 当前矩形.w, 当前矩形.h)
            缓存图 = self._按钮缩放缓存.get(缓存键)
            if 缓存图 is None:
                缓存图 = pygame.transform.smoothscale(
                    原图,
                    (当前矩形.w, 当前矩形.h),
                ).convert_alpha()
                self._按钮缩放缓存[缓存键] = 缓存图

            屏幕.blit(缓存图, 当前矩形.topleft)

    def _画DIY标签(self):
        if not self._当前是否DIY模式():
            return

        屏幕 = self.上下文["屏幕"]
        字体 = self._取DIY标签字体()
        DIY滚动偏移x = -float(self._DIY滚动偏移x)

        for _按钮, 模式名, _小图, _大图 in self._取当前页按钮项():
            标签中心点 = self._按钮标签中心点.get(模式名)
            if 标签中心点 is None:
                continue

            偏移x = self._按钮当前偏移x.get(模式名, 0.0) + DIY滚动偏移x
            偏移y = self._按钮当前偏移y.get(模式名, 0.0)
            文本位置 = (
                int(标签中心点[0] + 偏移x),
                int(标签中心点[1] + 偏移y),
            )
            标签文本 = self._截断DIY标签(模式名, 最大字符数=7)
            文字颜色 = (
                (251, 200, 106)
                if 模式名 == self._当前选中模式名
                else (255, 255, 255)
            )

            绘制文本(
                屏幕,
                标签文本,
                字体,
                (0, 0, 0),
                (文本位置[0] + 2, 文本位置[1] + 3),
                "center",
            )
            绘制文本(屏幕, 标签文本, 字体, 文字颜色, 文本位置, "center")

    def _取选中模式大图路径(self) -> tuple[str | None, int | None, pygame.Rect | None]:
        if not self._当前选中模式名:
            return None, None, None

        目标矩形 = self._按钮目标矩形.get(self._当前选中模式名)
        if not isinstance(目标矩形, pygame.Rect):
            return None, None, None

        偏移x = self._按钮当前偏移x.get(self._当前选中模式名, 0.0)
        if self._当前是否DIY模式():
            偏移x += -float(self._DIY滚动偏移x)
        偏移y = self._按钮当前偏移y.get(self._当前选中模式名, 0.0)
        当前矩形 = pygame.Rect(
            int(目标矩形.x + 偏移x),
            int(目标矩形.y + 偏移y),
            目标矩形.w,
            目标矩形.h,
        )

        for _按钮, 模式名, _小图, 大图路径 in self._取当前页按钮项():
            if 模式名 == self._当前选中模式名:
                return 大图路径, self._按钮目标矩形[模式名].w, 当前矩形

        return None, None, None

    def _取大图表面(self, 路径: str) -> pygame.Surface | None:
        if 路径 == self._大图标路径缓存 and self._大图标表面 is not None:
            return self._大图标表面

        if 路径 not in self._大图缓存:
            self._大图缓存[路径] = 安全加载图片(路径, 透明=True)

        self._大图标路径缓存 = 路径
        self._大图标表面 = self._大图缓存.get(路径)
        return self._大图标表面

    def _绘制大图标(self):
        if not self._当前选中模式名:
            return

        屏幕 = self.上下文["屏幕"]
        当前毫秒 = pygame.time.get_ticks()

        大图路径, 选中按钮边长, 当前按钮矩形 = self._取选中模式大图路径()
        if (not 大图路径) or (not 选中按钮边长) or (当前按钮矩形 is None):
            return

        原图 = self._取大图表面(大图路径)
        if 原图 is None:
            return

        动画时长 = int(self._大图动画时长毫秒)
        进度 = (当前毫秒 - self._选中开始毫秒) / max(1, 动画时长)
        进度 = self._夹紧(进度, 0.0, 1.0)

        if 进度 < 0.6:
            第一段进度 = 进度 / 0.6
            缩放倍率 = 0.92 + (1.06 - 0.92) * self._缓出(第一段进度)
        else:
            第二段进度 = (进度 - 0.6) / 0.4
            缩放倍率 = 1.06 + (1.00 - 1.06) * self._缓出(第二段进度)

        alpha = int(255 * self._缓出(进度))
        alpha = max(0, min(255, alpha))

        基准宽 = int(选中按钮边长 * 1.2)
        宽度缩放比 = 基准宽 / max(1, 原图.get_width())
        目标宽 = max(1, int(原图.get_width() * 宽度缩放比 * 缩放倍率))
        目标高 = max(1, int(原图.get_height() * 宽度缩放比 * 缩放倍率))

        绘制图 = pygame.transform.smoothscale(原图, (目标宽, 目标高)).convert_alpha()
        绘制图.set_alpha(alpha)

        基准中心x = 当前按钮矩形.centerx
        基准中心y = 当前按钮矩形.centery
        上移距离 = int(当前按钮矩形.h * 0.5)

        绘制x = 基准中心x - 目标宽 // 2
        绘制y = (基准中心y - 目标高 // 2) - 上移距离

        self._大图标矩形 = pygame.Rect(绘制x, 绘制y, 目标宽, 目标高)
        屏幕.blit(绘制图, (绘制x, 绘制y))

    def _画DIY翻页提示(self):
        if not self._当前是否DIY模式():
            return

        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()
        字体 = 获取字体(max(16, min(24, int(self._当前按钮边长 * 0.10))))
        if self._DIY可滚动():
            提示文本 = "滚轮左右平移曲包列表"
        else:
            提示文本 = "点击曲包进入选歌"
        提示位置 = (宽 // 2, 高 - max(72, int(86 * min(宽 / self._设计宽, 高 / self._设计高))))

        绘制文本(
            屏幕,
            提示文本,
            字体,
            (0, 0, 0),
            (提示位置[0] + 2, 提示位置[1] + 3),
            "center",
        )
        绘制文本(屏幕, 提示文本, 字体, (255, 255, 255), 提示位置, "center")

    def _画空状态提示(self):
        if self.子模式按钮列表 or (not self._空状态提示):
            return

        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()
        字体 = self.上下文["字体"]["小字"]
        标题 = "DIY 曲包列表为空" if self._当前是否DIY模式() else "暂无可选模式"
        标题位置 = (宽 // 2, int(高 * 0.46))
        说明位置 = (宽 // 2, int(高 * 0.52))

        绘制文本(
            屏幕,
            标题,
            字体,
            (255, 255, 255),
            标题位置,
            "center",
        )
        绘制文本(
            屏幕,
            self._空状态提示,
            字体,
            (251, 200, 106),
            说明位置,
            "center",
        )

    def 绘制(self):
        self._更新动画()
        self._画背景()
        self._画子模式按钮()

        if self._当前选中模式名:
            self._绘制大图标()

        self._画DIY标签()
        self._画DIY翻页提示()
        self._画空状态提示()
        self._画底部联网与credit()
        self._画顶栏()

        if self._全屏放大过渡.是否进行中():
            self._全屏放大过渡.更新并绘制(self.上下文["屏幕"])

    def 处理全局踏板(self, 动作: str):
        if 动作 == 踏板动作_左:
            return self._踏板切换模式(-1)
        if 动作 == 踏板动作_右:
            return self._踏板切换模式(+1)
        if 动作 == 踏板动作_确认:
            return self._触发当前模式确认()
        return None

    def 处理事件(self, 事件):
        if 事件.type == pygame.VIDEORESIZE:
            self.重算布局()
            return None

        if 事件.type == pygame.KEYDOWN and 事件.key == pygame.K_ESCAPE:
            return 场景切换请求("大模式", 动作="REPLACE")

        if self._DIY可滚动():
            if 事件.type == pygame.MOUSEWHEEL:
                横向步数 = int(getattr(事件, "x", 0) or 0)
                if 横向步数 != 0:
                    if self._滚动DIY列表(
                        -float(横向步数) * self._取DIY滚轮步长(),
                        播放音效=True,
                    ):
                        return None
                纵向步数 = int(getattr(事件, "y", 0) or 0)
                if 纵向步数 != 0:
                    if self._滚动DIY列表(
                        -float(纵向步数) * self._取DIY滚轮步长(),
                        播放音效=True,
                    ):
                        return None
            if 事件.type == pygame.MOUSEBUTTONDOWN:
                if int(getattr(事件, "button", 0) or 0) == 4:
                    if self._滚动DIY列表(
                        -self._取DIY滚轮步长(),
                        播放音效=True,
                    ):
                        return None
                if int(getattr(事件, "button", 0) or 0) == 5:
                    if self._滚动DIY列表(
                        self._取DIY滚轮步长(),
                        播放音效=True,
                    ):
                        return None

        elif self._当前是否DIY模式() and self._总页数 > 1:
            if 事件.type == pygame.MOUSEWHEEL:
                if int(getattr(事件, "y", 0) or 0) > 0:
                    self._切换到页(self._当前页码 - 1, 保留当前选中=False, 播放音效=True)
                    return None
                if int(getattr(事件, "y", 0) or 0) < 0:
                    self._切换到页(self._当前页码 + 1, 保留当前选中=False, 播放音效=True)
                    return None

            if 事件.type == pygame.MOUSEBUTTONDOWN:
                if int(getattr(事件, "button", 0) or 0) == 4:
                    self._切换到页(self._当前页码 - 1, 保留当前选中=False, 播放音效=True)
                    return None
                if int(getattr(事件, "button", 0) or 0) == 5:
                    self._切换到页(self._当前页码 + 1, 保留当前选中=False, 播放音效=True)
                    return None

        if (
            self._当前选中模式名
            and 事件.type == pygame.MOUSEBUTTONUP
            and 事件.button == 1
        ):
            if self._大图标矩形 and self._大图标矩形.collidepoint(事件.pos):
                self._按钮音效.播放()
                return self._触发当前模式确认()

        for 按钮, 模式名, _小图, _大图 in self._取当前页按钮项():
            if 按钮.处理事件(事件):
                if 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
                    self._按钮音效.播放()

                if self._当前选中模式名 != 模式名:
                    return self._应用模式选中(str(模式名))

                return self._触发当前模式确认()

        return None

    def 更新(self):
        if self._待进入选歌模式名 and (not self._全屏放大过渡.是否进行中()):
            模式名 = self._待进入选歌模式名
            self._按钮音效.播放()
            self._待进入选歌模式名 = None
            return self._进入选歌(模式名)
        return None

    def _进入选歌(self, 模式名: str):
        状态 = self.上下文.setdefault("状态", {})
        if not isinstance(状态, dict):
            状态 = {}
            self.上下文["状态"] = 状态

        类型名 = str(状态.get("songs子文件夹", "") or 状态.get("大模式", "") or "")
        状态["子模式"] = 模式名
        状态["选歌_类型"] = 类型名
        状态["选歌_模式"] = str(模式名 or "")
        状态["选歌_BGM"] = str(self.子模式对应选歌BGM(模式名) or "")

        音乐管理 = self.上下文.get("音乐")
        if 音乐管理 is not None:
            停止方法 = getattr(音乐管理, "停止", None)
            if callable(停止方法):
                try:
                    停止方法()
                except Exception as 异常:
                    _记录异常日志(_日志器, "子模式切换选歌前停止背景音乐失败", 异常)

        return {"切换到": "选歌", "禁用黑屏过渡": False}
