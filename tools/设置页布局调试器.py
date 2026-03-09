import os
import sys
import json
from typing import Dict, List, Tuple, Optional

import pygame



def 确保项目根目录在模块路径里() -> str:
    候选列表 = []

    try:
        当前文件 = os.path.abspath(__file__)
        当前目录 = os.path.dirname(当前文件)
        候选列表.append(当前目录)
        候选列表.append(os.path.abspath(os.path.join(当前目录, "..")))
        候选列表.append(os.path.abspath(os.path.join(当前目录, "..", "..")))
    except Exception:
        pass

    try:
        候选列表.append(os.getcwd())
    except Exception:
        pass

    已检查 = set()

    for 起点 in 候选列表:
        当前 = os.path.abspath(str(起点 or ""))
        if (not 当前) or (当前 in 已检查):
            continue
        已检查.add(当前)

        for _ in range(6):
            if (
                os.path.isdir(os.path.join(当前, "ui"))
                and os.path.isdir(os.path.join(当前, "UI-img"))
            ):
                if 当前 not in sys.path:
                    sys.path.insert(0, 当前)
                return 当前

            上级 = os.path.dirname(当前)
            if 上级 == 当前:
                break
            当前 = 上级

    回退目录 = os.path.abspath(os.getcwd())
    if 回退目录 not in sys.path:
        sys.path.insert(0, 回退目录)
    return 回退目录




项目根目录 = 确保项目根目录在模块路径里()


from ui import 选歌设置菜单控件 as 设置模块

def 取资源路径(*片段: str) -> str:
    return os.path.join(项目根目录, *片段)


def 安全加载图片(路径: str) -> Optional[pygame.Surface]:
    try:
        if 路径 and os.path.isfile(路径):
            return pygame.image.load(路径).convert_alpha()
    except Exception:
        pass
    return None


def 获取字体(字号: int, 是否粗体: bool = False) -> pygame.font.Font:
    字号 = max(10, int(字号))
    候选 = [
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ]
    for 名称 in 候选:
        try:
            return pygame.font.SysFont(名称, 字号, bold=是否粗体)
        except Exception:
            continue
    return pygame.font.SysFont(None, 字号, bold=是否粗体)


def 绘制文字(
    目标面: pygame.Surface,
    文本: str,
    位置: Tuple[int, int],
    字号: int = 18,
    颜色: Tuple[int, int, int] = (255, 255, 255),
    对齐: str = "topleft",
    是否粗体: bool = False,
):
    字体 = 获取字体(字号, 是否粗体=是否粗体)
    文字面 = 字体.render(str(文本), True, 颜色)
    文字矩形 = 文字面.get_rect()
    setattr(文字矩形, 对齐, 位置)
    目标面.blit(文字面, 文字矩形)
    return 文字矩形


def 限制浮点(值: float, 最小值: float, 最大值: float) -> float:
    return max(float(最小值), min(float(最大值), float(值)))


def 限制整数(值: int, 最小值: int, 最大值: int) -> int:
    return max(int(最小值), min(int(最大值), int(值)))


def 复制当前设置常量() -> Dict[str, object]:
    return {
        "设置页_面板宽占比": float(设置模块.设置页_面板宽占比),
        "设置页_面板高占比": float(设置模块.设置页_面板高占比),
        "设置页_面板整体缩放": float(设置模块.设置页_面板整体缩放),
        "设置页_面板_x偏移": int(设置模块.设置页_面板_x偏移),
        "设置页_面板_y偏移": int(设置模块.设置页_面板_y偏移),
        "设置页_左区_x占比": float(设置模块.设置页_左区_x占比),
        "设置页_左区_y占比": float(设置模块.设置页_左区_y占比),
        "设置页_左区_宽占比": float(设置模块.设置页_左区_宽占比),
        "设置页_左区_行高占比": float(设置模块.设置页_左区_行高占比),
        "设置页_左区_行间距像素": int(设置模块.设置页_左区_行间距像素),
        "设置页_左区_行偏移覆盖": dict(设置模块.设置页_左区_行偏移覆盖),
        "设置页_右区_x占比": float(设置模块.设置页_右区_x占比),
        "设置页_右区_y占比": float(设置模块.设置页_右区_y占比),
        "设置页_右区_宽占比": float(设置模块.设置页_右区_宽占比),
        "设置页_右区_高占比": float(设置模块.设置页_右区_高占比),
        "设置页_右区_额外偏移": tuple(设置模块.设置页_右区_额外偏移),
        "设置页_右区_预览内边距": int(设置模块.设置页_右区_预览内边距),
        "设置页_右区_预览框_偏移": tuple(设置模块.设置页_右区_预览框_偏移),
        "设置页_右区_预览框_宽缩放": float(设置模块.设置页_右区_预览框_宽缩放),
        "设置页_右区_预览框_高缩放": float(设置模块.设置页_右区_预览框_高缩放),
        "设置页_右区_左大箭头_偏移": tuple(设置模块.设置页_右区_左大箭头_偏移),
        "设置页_右区_右大箭头_偏移": tuple(设置模块.设置页_右区_右大箭头_偏移),
        "设置页_右区_左大箭头_缩放": float(设置模块.设置页_右区_左大箭头_缩放),
        "设置页_右区_右大箭头_缩放": float(设置模块.设置页_右区_右大箭头_缩放),
        "设置页_箭头预览_x占比": float(设置模块.设置页_箭头预览_x占比),
        "设置页_箭头预览_y占比": float(设置模块.设置页_箭头预览_y占比),
        "设置页_箭头预览_宽占比": float(设置模块.设置页_箭头预览_宽占比),
        "设置页_箭头预览_高占比": float(设置模块.设置页_箭头预览_高占比),
        "设置页_箭头预览_额外偏移": tuple(设置模块.设置页_箭头预览_额外偏移),
        "设置页_箭头预览_内边距": int(设置模块.设置页_箭头预览_内边距),
    }


def 应用设置常量(常量表: Dict[str, object]):
    for 键名, 值 in 常量表.items():
        setattr(设置模块, 键名, 值)

class 设置页布局调试器:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.窗口宽 = 1600
        self.窗口高 = 980
        self.屏幕 = pygame.display.set_mode((self.窗口宽, self.窗口高), pygame.RESIZABLE)
        pygame.display.set_caption("设置页布局调试器（只调 ui/选歌设置菜单控件.py）")

        self.时钟 = pygame.time.Clock()
        self.运行中 = True
        self.背景图 = 安全加载图片(
            取资源路径("UI-img", "选歌界面资源", "设置", "设置背景图.png")
        )

        self.初始常量 = 复制当前设置常量()
        self.布局缩放 = 1.0
        self.面板矩形 = pygame.Rect(0, 0, 10, 10)

        self.局部目标矩形表: Dict[str, pygame.Rect] = {}
        self.目标矩形表: Dict[str, pygame.Rect] = {}

        self.目标顺序: List[str] = []
        self.当前目标索引 = 0

        self.拖拽中 = False
        self.上次鼠标位置 = (0, 0)

        self.预设窗口列表 = [
            (1280, 720),
            (1366, 768),
            (1400, 860),
            (1600, 900),
            (1920, 1080),
            (2560, 1440),
        ]
        self.当前预设索引 = 2

        self.提示文本 = "Tab切目标，左键拖动，滚轮缩放，Shift/Alt改宽高，F5恢复，F6/F7切分辨率，Ctrl+S保存"
        self.输出目录 = os.path.join(项目根目录, "json")
        self.输出_json = os.path.join(self.输出目录, "设置页布局调试输出.json")
        self.输出_py = os.path.join(self.输出目录, "设置页布局调试输出_常量.py")

        self.重算()

    def 当前目标名(self) -> str:
        if not self.目标顺序:
            return ""
        self.当前目标索引 = self.当前目标索引 % len(self.目标顺序)
        return self.目标顺序[self.当前目标索引]

    def _局部矩形转屏幕矩形(self, 局部矩形: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(
            int(self.面板矩形.x + 局部矩形.x),
            int(self.面板矩形.y + 局部矩形.y),
            int(局部矩形.w),
            int(局部矩形.h),
        )

    def _登记目标(self, 名称: str, 矩形: pygame.Rect, 是否局部坐标: bool):
        if not isinstance(矩形, pygame.Rect):
            return

        if 是否局部坐标:
            局部矩形 = 矩形.copy()
            屏幕矩形 = self._局部矩形转屏幕矩形(局部矩形)
        else:
            屏幕矩形 = 矩形.copy()
            局部矩形 = pygame.Rect(
                int(屏幕矩形.x - self.面板矩形.x),
                int(屏幕矩形.y - self.面板矩形.y),
                int(屏幕矩形.w),
                int(屏幕矩形.h),
            )

        self.局部目标矩形表[名称] = 局部矩形
        self.目标矩形表[名称] = 屏幕矩形

    def 重算(self):
        布局 = 设置模块.计算设置页布局(self.窗口宽, self.窗口高)
        self.布局缩放 = float(布局.get("布局缩放", 1.0) or 1.0)
        self.面板矩形 = 布局["面板基础矩形"].copy()

        self.局部目标矩形表 = {}
        self.目标矩形表 = {}

        self._登记目标("面板", self.面板矩形.copy(), 是否局部坐标=False)

        for 行键, 行矩形 in 布局["行矩形表"].items():
            self._登记目标(f"行:{行键}", 行矩形.copy(), 是否局部坐标=True)

        self._登记目标("箭头预览框", 布局["箭头预览矩形"].copy(), 是否局部坐标=True)
        self._登记目标("右区预览", 布局["背景控件矩形"]["预览"].copy(), 是否局部坐标=True)
        self._登记目标("右区左大箭", 布局["背景控件矩形"]["左"].copy(), 是否局部坐标=True)
        self._登记目标("右区右大箭", 布局["背景控件矩形"]["右"].copy(), 是否局部坐标=True)

        self.目标顺序 = list(self.目标矩形表.keys())
        self.当前目标索引 = min(self.当前目标索引, max(0, len(self.目标顺序) - 1))

    def 命中测试(self, 点位: Tuple[int, int]) -> Optional[str]:
        当前目标 = self.当前目标名()
        if 当前目标 and 当前目标 in self.目标矩形表:
            if self.目标矩形表[当前目标].collidepoint(点位):
                return 当前目标

        for 名称 in self.目标顺序[::-1]:
            矩形 = self.目标矩形表.get(名称)
            if isinstance(矩形, pygame.Rect) and 矩形.collidepoint(点位):
                return 名称
        return None

    def 转源像素(self, 屏幕像素: int) -> int:
        return int(round(float(屏幕像素) / max(0.001, float(self.布局缩放))))

    def 平移当前目标(self, 目标名: str, 屏幕dx: int, 屏幕dy: int):
        源dx = self.转源像素(屏幕dx)
        源dy = self.转源像素(屏幕dy)

        if 目标名 == "面板":
            设置模块.设置页_面板_x偏移 += 源dx
            设置模块.设置页_面板_y偏移 += 源dy

        elif 目标名.startswith("行:"):
            行键 = 目标名.split(":", 1)[1]
            当前dx, 当前dy = 设置模块.设置页_左区_行偏移覆盖.get(行键, (0, 0))
            设置模块.设置页_左区_行偏移覆盖[行键] = (
                int(当前dx) + 源dx,
                int(当前dy) + 源dy,
            )

        elif 目标名 == "箭头预览框":
            x, y = 设置模块.设置页_箭头预览_额外偏移
            设置模块.设置页_箭头预览_额外偏移 = (int(x) + 源dx, int(y) + 源dy)

        elif 目标名 == "右区预览":
            x, y = 设置模块.设置页_右区_预览框_偏移
            设置模块.设置页_右区_预览框_偏移 = (int(x) + 源dx, int(y) + 源dy)

        elif 目标名 == "右区左大箭":
            x, y = 设置模块.设置页_右区_左大箭头_偏移
            设置模块.设置页_右区_左大箭头_偏移 = (int(x) + 源dx, int(y) + 源dy)

        elif 目标名 == "右区右大箭":
            x, y = 设置模块.设置页_右区_右大箭头_偏移
            设置模块.设置页_右区_右大箭头_偏移 = (int(x) + 源dx, int(y) + 源dy)

        self.重算()

    def 缩放当前目标(self, 目标名: str, 方向: int, 修饰键: int):
        if 目标名 == "面板":
            if 修饰键 & pygame.KMOD_SHIFT:
                设置模块.设置页_面板宽占比 = 限制浮点(
                    设置模块.设置页_面板宽占比 + 方向 * 0.01,
                    0.20,
                    1.20,
                )
            elif 修饰键 & pygame.KMOD_ALT:
                设置模块.设置页_面板高占比 = 限制浮点(
                    设置模块.设置页_面板高占比 + 方向 * 0.01,
                    0.20,
                    1.20,
                )
            else:
                设置模块.设置页_面板整体缩放 = 限制浮点(
                    设置模块.设置页_面板整体缩放 + 方向 * 0.02,
                    0.30,
                    2.50,
                )

        elif 目标名.startswith("行:"):
            if 修饰键 & pygame.KMOD_SHIFT:
                设置模块.设置页_左区_宽占比 = 限制浮点(
                    设置模块.设置页_左区_宽占比 + 方向 * 0.005,
                    0.02,
                    0.80,
                )
            elif 修饰键 & pygame.KMOD_ALT:
                设置模块.设置页_左区_行间距像素 = 限制整数(
                    int(设置模块.设置页_左区_行间距像素) + 方向 * 2,
                    0,
                    200,
                )
            else:
                设置模块.设置页_左区_行高占比 = 限制浮点(
                    设置模块.设置页_左区_行高占比 + 方向 * 0.005,
                    0.01,
                    0.30,
                )

        elif 目标名 == "箭头预览框":
            if 修饰键 & pygame.KMOD_SHIFT:
                设置模块.设置页_箭头预览_宽占比 = 限制浮点(
                    设置模块.设置页_箭头预览_宽占比 + 方向 * 0.005,
                    0.01,
                    0.60,
                )
            elif 修饰键 & pygame.KMOD_ALT:
                设置模块.设置页_箭头预览_高占比 = 限制浮点(
                    设置模块.设置页_箭头预览_高占比 + 方向 * 0.005,
                    0.01,
                    0.60,
                )
            else:
                设置模块.设置页_箭头预览_宽占比 = 限制浮点(
                    设置模块.设置页_箭头预览_宽占比 + 方向 * 0.005,
                    0.01,
                    0.60,
                )
                设置模块.设置页_箭头预览_高占比 = 限制浮点(
                    设置模块.设置页_箭头预览_高占比 + 方向 * 0.005,
                    0.01,
                    0.60,
                )

        elif 目标名 == "右区预览":
            if 修饰键 & pygame.KMOD_SHIFT:
                设置模块.设置页_右区_预览框_宽缩放 = 限制浮点(
                    设置模块.设置页_右区_预览框_宽缩放 + 方向 * 0.02,
                    0.10,
                    3.00,
                )
            elif 修饰键 & pygame.KMOD_ALT:
                设置模块.设置页_右区_预览框_高缩放 = 限制浮点(
                    设置模块.设置页_右区_预览框_高缩放 + 方向 * 0.02,
                    0.10,
                    3.00,
                )
            else:
                设置模块.设置页_右区_预览框_宽缩放 = 限制浮点(
                    设置模块.设置页_右区_预览框_宽缩放 + 方向 * 0.02,
                    0.10,
                    3.00,
                )
                设置模块.设置页_右区_预览框_高缩放 = 限制浮点(
                    设置模块.设置页_右区_预览框_高缩放 + 方向 * 0.02,
                    0.10,
                    3.00,
                )

        elif 目标名 == "右区左大箭":
            设置模块.设置页_右区_左大箭头_缩放 = 限制浮点(
                设置模块.设置页_右区_左大箭头_缩放 + 方向 * 0.02,
                0.20,
                3.00,
            )

        elif 目标名 == "右区右大箭":
            设置模块.设置页_右区_右大箭头_缩放 = 限制浮点(
                设置模块.设置页_右区_右大箭头_缩放 + 方向 * 0.02,
                0.20,
                3.00,
            )

        self.重算()

    def 保存输出(self):
        os.makedirs(self.输出目录, exist_ok=True)
        常量表 = 复制当前设置常量()

        with open(self.输出_json, "w", encoding="utf-8") as 文件:
            json.dump(
                {
                    "来源": "ui/选歌设置菜单控件.py",
                    "常量": 常量表,
                },
                文件,
                ensure_ascii=False,
                indent=2,
            )

        行列表 = []
        for 键名, 值 in 常量表.items():
            行列表.append(f"{键名} = {repr(值)}")

        with open(self.输出_py, "w", encoding="utf-8") as 文件:
            文件.write("\n".join(行列表))

        self.提示文本 = f"已保存：{self.输出_json}"

    def 处理事件(self):
        for 事件 in pygame.event.get():
            if 事件.type == pygame.QUIT:
                self.运行中 = False
                return

            if 事件.type == pygame.VIDEORESIZE:
                self.窗口宽 = max(960, int(事件.w))
                self.窗口高 = max(600, int(事件.h))
                self.屏幕 = pygame.display.set_mode(
                    (self.窗口宽, self.窗口高),
                    pygame.RESIZABLE,
                )
                self.重算()

            elif 事件.type == pygame.KEYDOWN:
                修饰键 = pygame.key.get_mods()

                if 事件.key == pygame.K_ESCAPE:
                    self.运行中 = False
                    return

                elif 事件.key == pygame.K_TAB:
                    if self.目标顺序:
                        步进 = -1 if (修饰键 & pygame.KMOD_SHIFT) else 1
                        self.当前目标索引 = (self.当前目标索引 + 步进) % len(self.目标顺序)

                elif 事件.key == pygame.K_F5:
                    应用设置常量(self.初始常量)
                    self.提示文本 = "已恢复初始常量"
                    self.重算()

                elif 事件.key == pygame.K_F6:
                    self.当前预设索引 = (self.当前预设索引 - 1) % len(self.预设窗口列表)
                    self.窗口宽, self.窗口高 = self.预设窗口列表[self.当前预设索引]
                    self.屏幕 = pygame.display.set_mode(
                        (self.窗口宽, self.窗口高),
                        pygame.RESIZABLE,
                    )
                    self.提示文本 = f"已切到预设分辨率：{self.窗口宽}x{self.窗口高}"
                    self.重算()

                elif 事件.key == pygame.K_F7:
                    self.当前预设索引 = (self.当前预设索引 + 1) % len(self.预设窗口列表)
                    self.窗口宽, self.窗口高 = self.预设窗口列表[self.当前预设索引]
                    self.屏幕 = pygame.display.set_mode(
                        (self.窗口宽, self.窗口高),
                        pygame.RESIZABLE,
                    )
                    self.提示文本 = f"已切到预设分辨率：{self.窗口宽}x{self.窗口高}"
                    self.重算()

                elif (修饰键 & pygame.KMOD_CTRL) and 事件.key == pygame.K_s:
                    self.保存输出()

            elif 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
                命中 = self.命中测试(事件.pos)
                if 命中:
                    self.当前目标索引 = self.目标顺序.index(命中)
                    self.拖拽中 = True
                    self.上次鼠标位置 = 事件.pos
                    self.提示文本 = f"已选中：{命中}"

            elif 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
                self.拖拽中 = False

            elif 事件.type == pygame.MOUSEMOTION and self.拖拽中:
                当前目标 = self.当前目标名()
                dx = int(事件.pos[0] - self.上次鼠标位置[0])
                dy = int(事件.pos[1] - self.上次鼠标位置[1])
                self.上次鼠标位置 = 事件.pos

                if 当前目标 and (dx != 0 or dy != 0):
                    self.平移当前目标(当前目标, dx, dy)

            elif 事件.type == pygame.MOUSEWHEEL:
                当前目标 = self.当前目标名()
                if 当前目标:
                    self.缩放当前目标(
                        当前目标,
                        1 if 事件.y > 0 else -1,
                        pygame.key.get_mods(),
                    )

    def 绘制(self):
        self.屏幕.fill((16, 18, 24))

        if self.背景图 is not None:
            try:
                背景缩放图 = pygame.transform.smoothscale(
                    self.背景图,
                    (self.面板矩形.w, self.面板矩形.h),
                ).convert_alpha()
                self.屏幕.blit(背景缩放图, self.面板矩形.topleft)
            except Exception:
                pygame.draw.rect(self.屏幕, (40, 70, 130), self.面板矩形, border_radius=12)
        else:
            pygame.draw.rect(self.屏幕, (40, 70, 130), self.面板矩形, border_radius=12)

        try:
            pygame.draw.line(
                self.屏幕,
                (255, 255, 255),
                (self.面板矩形.x - 10, self.面板矩形.y),
                (self.面板矩形.x + 10, self.面板矩形.y),
                2,
            )
            pygame.draw.line(
                self.屏幕,
                (255, 255, 255),
                (self.面板矩形.x, self.面板矩形.y - 10),
                (self.面板矩形.x, self.面板矩形.y + 10),
                2,
            )
        except Exception:
            pass

        颜色表 = {
            "面板": (255, 255, 255),
            "箭头预览框": (200, 120, 255),
            "右区预览": (255, 240, 80),
            "右区左大箭": (255, 120, 120),
            "右区右大箭": (255, 120, 120),
        }

        当前目标 = self.当前目标名()

        for 名称 in self.目标顺序:
            屏幕矩形 = self.目标矩形表[名称]
            局部矩形 = self.局部目标矩形表.get(名称, pygame.Rect(0, 0, 0, 0))

            颜色 = 颜色表.get(名称, (0, 235, 180))
            线宽 = 3 if 名称 == 当前目标 else 2

            pygame.draw.rect(self.屏幕, 颜色, 屏幕矩形, 线宽, border_radius=8)

            标签文本 = f"{名称}"
            if 名称 != "面板":
                标签文本 += f"  L({局部矩形.x},{局部矩形.y},{局部矩形.w},{局部矩形.h})"

            绘制文字(
                self.屏幕,
                标签文本,
                (屏幕矩形.x + 4, 屏幕矩形.y - 4),
                14,
                颜色,
                "bottomleft",
            )

        当前屏幕矩形 = self.目标矩形表.get(当前目标, pygame.Rect(0, 0, 0, 0))
        当前局部矩形 = self.局部目标矩形表.get(当前目标, pygame.Rect(0, 0, 0, 0))

        信息y = 10
        绘制文字(
            self.屏幕,
            f"窗口 {self.窗口宽}x{self.窗口高}  布局缩放 {self.布局缩放:.3f}",
            (12, 信息y),
            20,
            (255, 255, 255),
        )
        信息y += 28

        绘制文字(
            self.屏幕,
            f"当前目标 {当前目标}",
            (12, 信息y),
            20,
            (120, 255, 180),
        )
        信息y += 28

        绘制文字(
            self.屏幕,
            f"屏幕坐标 x={当前屏幕矩形.x} y={当前屏幕矩形.y} w={当前屏幕矩形.w} h={当前屏幕矩形.h}",
            (12, 信息y),
            18,
            (220, 230, 240),
        )
        信息y += 24

        绘制文字(
            self.屏幕,
            f"局部坐标 x={当前局部矩形.x} y={当前局部矩形.y} w={当前局部矩形.w} h={当前局部矩形.h}",
            (12, 信息y),
            18,
            (220, 230, 240),
        )
        信息y += 24

        绘制文字(
            self.屏幕,
            f"面板原点 screen=({self.面板矩形.x},{self.面板矩形.y})",
            (12, 信息y),
            18,
            (255, 210, 120),
        )

        绘制文字(
            self.屏幕,
            self.提示文本,
            (12, self.窗口高 - 12),
            18,
            (210, 210, 210),
            "bottomleft",
        )

        pygame.display.flip()

    def 运行(self):
        while self.运行中:
            self.处理事件()
            self.绘制()
            self.时钟.tick(144)
        pygame.quit()

def 主函数():
    调试器 = 设置页布局调试器()
    调试器.运行()


if __name__ == "__main__":
    主函数()