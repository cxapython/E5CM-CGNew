
import os
import sys
import time
from typing import Dict, Optional, List

import pygame
from core.常量与路径 import (
    取项目根目录 as _公共取项目根目录,
    取运行根目录 as _公共取运行根目录,
)
from core.sqlite_store import (
    SCOPE_LOADING_PAYLOAD as _加载页存储作用域,
    replace_scope as _覆盖存储作用域,
    read_scope as _读取存储作用域,
)
from core.歌曲记录 import 取歌曲记录
from core.工具 import 绘制底部联网与信用
from scenes.场景基类 import 场景基类


_项目根目录_缓存: str | None = None


def _取项目根目录() -> str:
    return _公共取项目根目录()


def _取运行根目录() -> str:
    return _公共取运行根目录()


def _安全加载图片(路径: str, 透明: bool = True) -> Optional[pygame.Surface]:
    try:
        if (not 路径) or (not os.path.isfile(路径)):
            return None
        图 = pygame.image.load(路径)
        return 图.convert_alpha() if 透明 else 图.convert()
    except Exception:
        return None


def _contain缩放(图片: pygame.Surface, 目标宽: int, 目标高: int) -> pygame.Surface:
    ow, oh = 图片.get_size()
    ow = max(1, int(ow))
    oh = max(1, int(oh))
    目标宽 = max(1, int(目标宽))
    目标高 = max(1, int(目标高))

    比例 = min(目标宽 / ow, 目标高 / oh)
    nw = max(1, int(ow * 比例))
    nh = max(1, int(oh * 比例))
    缩放 = pygame.transform.smoothscale(图片, (nw, nh)).convert_alpha()

    画布 = pygame.Surface((目标宽, 目标高), pygame.SRCALPHA)
    画布.fill((0, 0, 0, 0))
    x = (目标宽 - nw) // 2
    y = (目标高 - nh) // 2
    画布.blit(缩放, (x, y))
    return 画布


def _获取字体(字号: int, 是否粗体: bool = False) -> pygame.font.Font:
    """
    优先用 core.工具 的 获取字体；没有就回退系统字体。
    """
    try:
        from core.工具 import 获取字体  # type: ignore

        return 获取字体(int(字号), 是否粗体=bool(是否粗体))
    except Exception:
        pygame.font.init()
        try:
            return pygame.font.SysFont(
                "Microsoft YaHei", int(字号), bold=bool(是否粗体)
            )
        except Exception:
            return pygame.font.Font(None, int(字号))


def _载荷值有效(值) -> bool:
    if 值 is None:
        return False
    if isinstance(值, str):
        文本 = 值.strip()
        return 文本.lower() not in ("", "未知", "loading...")
    if isinstance(值, (list, tuple, set, dict)):
        return len(值) > 0
    return True


def _合并载荷源(*载荷源) -> Dict:
    合并后: Dict = {}
    for 载荷 in 载荷源:
        if not isinstance(载荷, dict):
            continue
        for 键, 值 in 载荷.items():
            if _载荷值有效(值) or (键 not in 合并后):
                if isinstance(值, dict):
                    合并后[键] = dict(值)
                elif isinstance(值, list):
                    合并后[键] = list(值)
                else:
                    合并后[键] = 值
    return 合并后



class 场景_加载页(场景基类):
    名称 = "加载页"

    _设计宽 = 2048
    _设计高 = 1152

    _封面区域 = (68, 380, 874, 939)
    _右侧信息区 = (967, 553, 1782, 862)
    _左下记录区 = (49, 953, 621, 1098)
    _右下记录区 = (1084, 878, 1790, 1050)

    def __init__(self, 上下文: dict):
        super().__init__(上下文)

        self._载荷: Dict = {}
        self._入场开始 = 0.0

        self._个人资料路径: str = ""
        self._个人资料_mtime: float = 0.0
        self._个人资料数据: dict = {}

        self._个人昵称: str = "未知"
        self._最高分: int = 0
        self._最大等级: int = 0

        self._联网原图: Optional[pygame.Surface] = None

        self._背景原图: Optional[pygame.Surface] = None
        self._背景缩放缓存: Optional[pygame.Surface] = None
        self._背景缩放尺寸 = (0, 0)

        self._星星原图: Optional[pygame.Surface] = None
        self._封面原图: Optional[pygame.Surface] = None
        self._封面缩放缓存: Optional[pygame.Surface] = None
        self._封面缩放尺寸 = (0, 0)

    def 进入(self, 载荷=None):
        self._入场开始 = time.time()
        落盘载荷 = self._读取加载页json()
        if (not 落盘载荷) and isinstance(载荷, dict) and 载荷:
            try:
                落盘载荷 = _覆盖存储作用域(_加载页存储作用域, dict(载荷))
            except Exception:
                落盘载荷 = dict(载荷)
        self._载荷 = dict(落盘载荷) if isinstance(落盘载荷, dict) else {}

        try:
            运行根目录 = _取运行根目录()
            self._个人资料路径 = os.path.join(运行根目录, "json", "个人资料.json")

            try:
                联网图路径 = str(
                    (self.上下文.get("资源", {}) or {}).get("投币_联网图标", "") or ""
                )
                if 联网图路径 and os.path.isfile(联网图路径):
                    self._联网原图 = pygame.image.load(联网图路径).convert_alpha()
                else:
                    self._联网原图 = None
            except Exception:
                self._联网原图 = None

        except Exception:
            self._个人资料路径 = ""
            self._联网原图 = None

        try:
            if isinstance(self.上下文, dict):
                状态 = self.上下文.get("状态", {}) or {}
                if isinstance(状态, dict):
                    状态.pop("加载页_载荷", None)
        except Exception:
            pass

        self._加载资源()
        self._加载封面()
        self._刷新个人资料缓存(强制=True)

    def _读取个人资料json(self, 文件路径: str) -> dict:
        try:
            import json
        except Exception:
            return {}

        try:
            if (not 文件路径) or (not os.path.isfile(文件路径)):
                return {}

            with open(文件路径, "r", encoding="utf-8") as 文件:
                数据 = json.load(文件)

            return dict(数据) if isinstance(数据, dict) else {}
        except Exception:
            return {}

    def _刷新个人资料缓存(self, 强制: bool = False):
        路径 = str(getattr(self, "_个人资料路径", "") or "")
        if not 路径 or (not os.path.isfile(路径)):
            self._个人昵称 = "未知"
            self._最高分 = 0
            self._最大等级 = 0
            self._个人资料数据 = {}
            return

        try:
            修改时间 = float(os.path.getmtime(路径))
            if (not 强制) and (
                修改时间 == float(getattr(self, "_个人资料_mtime", 0.0) or 0.0)
            ):
                return

            数据 = self._读取个人资料json(路径)
            self._个人资料数据 = 数据 if isinstance(数据, dict) else {}
            self._个人资料_mtime = 修改时间

            昵称 = str(self._个人资料数据.get("昵称", "") or "").strip() or "未知"

            try:
                根目录 = _取项目根目录()
                记录 = 取歌曲记录(
                    根目录,
                    str(self._载荷.get("sm路径", "") or ""),
                    str(self._载荷.get("歌名", "") or ""),
                )
                最高分 = int((记录 or {}).get("最高分", 0) or 0)
            except Exception:
                最高分 = 0

            try:
                最大等级 = int(
                    ((self._个人资料数据.get("进度", {}) or {}).get("最大等级", 0) or 0)
                )
            except Exception:
                最大等级 = 0

            self._个人昵称 = 昵称
            self._最高分 = max(0, int(最高分))
            self._最大等级 = max(0, int(最大等级))

        except Exception:
            self._个人昵称 = "未知"
            self._最高分 = 0
            self._最大等级 = 0
            self._个人资料数据 = {}

    def 退出(self):
        return

    def 更新(self):
        try:
            if (time.time() - float(getattr(self, "_入场开始", 0.0) or 0.0)) >= 3.0:
                return {"切换到": "谱面播放器", "禁用黑屏过渡": True}
        except Exception:
            pass
        return None

    def 处理事件(self, 事件):
        if 事件.type == pygame.KEYDOWN:
            if 事件.key == pygame.K_ESCAPE:
                return {"切换到": "子模式", "禁用黑屏过渡": True}

            if 事件.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return {"切换到": "谱面播放器", "禁用黑屏过渡": True}

        return None

    def 绘制(self):
        屏幕: pygame.Surface = self.上下文["屏幕"]
        self._刷新个人资料缓存(强制=False)

        self._绘制背景(屏幕)

        封面区域 = self._映射到屏幕_rect(self._封面区域)
        右侧信息区 = self._映射到屏幕_rect(self._右侧信息区)
        左下记录区 = self._映射到屏幕_rect(self._左下记录区)
        右下记录区 = self._映射到屏幕_rect(self._右下记录区)

        self._绘制缩略图(屏幕, 封面区域)
        self._绘制右侧信息(屏幕, 右侧信息区)
        self._绘制左下记录(屏幕, 左下记录区)
        self._绘制右下记录(屏幕, 右下记录区)
        self._绘制底部币值(屏幕)

    def _绘制底部币值(self, 屏幕: pygame.Surface):
        try:
            字体_credit = (self.上下文.get("字体", {}) or {}).get("投币_credit字")
        except Exception:
            字体_credit = None

        if not isinstance(字体_credit, pygame.font.Font):
            return

        try:
            状态 = self.上下文.get("状态", {}) if isinstance(self.上下文, dict) else {}
            投币数 = int((状态 or {}).get("投币数", 0) or 0)
            所需信用 = int((状态 or {}).get("每局所需信用", 3) or 3)
        except Exception:
            投币数 = 0
            所需信用 = 3

        try:
            绘制底部联网与信用(
                屏幕=屏幕,
                联网原图=getattr(self, "_联网原图", None),
                字体_credit=字体_credit,
                credit数值=f"{max(0, 投币数)}/{int(max(1, 所需信用))}",
                总信用需求=int(max(1, 所需信用)),
                文本=f"CREDIT：{max(0, 投币数)}/{int(max(1, 所需信用))}",
            )
        except Exception:
            pass

    def _读取加载页json(self) -> dict:
        数据 = _读取存储作用域(_加载页存储作用域)
        return dict(数据) if isinstance(数据, dict) else {}

    def _加载资源(self):
        try:
            资源 = self.上下文.get("资源", {}) or {}
        except Exception:
            资源 = {}
        根目录 = str((资源 or {}).get("根", "") or "").strip() or _取项目根目录()

        背景路径 = os.path.join(根目录, "冷资源", "backimages", "选歌界面.png")
        星星路径 = os.path.join(
            根目录, "UI-img", "选歌界面资源", "小星星", "大星星.png"
        )

        self._背景原图 = _安全加载图片(背景路径, 透明=False)
        self._星星原图 = _安全加载图片(星星路径, 透明=True)

    def _加载封面(self):
        封面路径 = str(self._载荷.get("封面路径", "") or "")
        self._封面原图 = _安全加载图片(封面路径, 透明=True)
        self._封面缩放缓存 = None
        self._封面缩放尺寸 = (0, 0)

    def _绘制背景(self, 屏幕: pygame.Surface):
        宽度, 高度 = 屏幕.get_size()
        if self._背景原图 is None:
            屏幕.fill((0, 0, 0))
            return

        目标尺寸 = (int(宽度), int(高度))
        if self._背景缩放缓存 is None or self._背景缩放尺寸 != 目标尺寸:
            try:
                self._背景缩放缓存 = pygame.transform.smoothscale(
                    self._背景原图, 目标尺寸
                ).convert()
                self._背景缩放尺寸 = 目标尺寸
            except Exception:
                self._背景缩放缓存 = None
                self._背景缩放尺寸 = (0, 0)

        if self._背景缩放缓存 is not None:
            屏幕.blit(self._背景缩放缓存, (0, 0))
        else:
            屏幕.fill((0, 0, 0))

    def _绘制缩略图(self, 屏幕: pygame.Surface, 区域: pygame.Rect):
        if self._封面原图 is None:
            字体 = _获取字体(max(16, int(区域.h * 0.12)), 是否粗体=False)
            文字面 = 字体.render("无封面", True, (255, 255, 255))
            文字框 = 文字面.get_rect(center=区域.center)
            屏幕.blit(文字面, 文字框.topleft)
            return

        目标尺寸 = (int(区域.w - 16), int(区域.h - 16))
        if self._封面缩放缓存 is None or self._封面缩放尺寸 != 目标尺寸:
            try:
                图 = self._封面原图.convert_alpha()
            except Exception:
                图 = self._封面原图
            self._封面缩放缓存 = _contain缩放(图, 目标尺寸[0], 目标尺寸[1])
            self._封面缩放尺寸 = 目标尺寸

        if self._封面缩放缓存 is not None:
            x坐标 = 区域.x + (区域.w - self._封面缩放缓存.get_width()) // 2
            y坐标 = 区域.y + (区域.h - self._封面缩放缓存.get_height()) // 2
            屏幕.blit(self._封面缩放缓存, (x坐标, y坐标))

    def _绘制右侧信息(self, 屏幕: pygame.Surface, 区域: pygame.Rect):
        歌名 = str(self._载荷.get("歌名", "") or "Loading...")
        try:
            星级 = int(self._载荷.get("星级", 0) or 0)
        except Exception:
            星级 = 0

        try:
            bpm显示 = str(int(self._载荷.get("bpm", 0) or 0))
        except Exception:
            bpm显示 = "?"

        try:
            人气显示 = str(int(self._载荷.get("人气", 0) or 0))
        except Exception:
            人气显示 = "0"

        星区 = pygame.Rect(区域.x, 区域.y, 区域.w, int(区域.h * 0.30))
        名区 = pygame.Rect(区域.x, 星区.bottom + 8, 区域.w, int(区域.h * 0.18))
        数值区 = pygame.Rect(区域.x, 名区.bottom + 10, 区域.w, int(区域.h * 0.18))

        self._绘制星星行(屏幕, 星区, 星级)

        歌名字体 = _获取字体(max(28, int(区域.h * 0.12)), 是否粗体=False)
        歌名面 = 歌名字体.render(歌名, True, (255, 255, 255))
        歌名框 = 歌名面.get_rect(center=名区.center)
        屏幕.blit(歌名面, 歌名框.topleft)

        数值字体 = _获取字体(max(22, int(区域.h * 0.10)), 是否粗体=False)
        左文 = 数值字体.render(f"人气: {人气显示}", True, (255, 255, 255))
        右文 = 数值字体.render(f"BPM: {bpm显示}", True, (255, 255, 255))

        左框 = 左文.get_rect(
            midleft=(数值区.x + int(数值区.w * 0.14), 数值区.centery)
        )
        右框 = 右文.get_rect(
            midright=(数值区.right - int(数值区.w * 0.12), 数值区.centery)
        )

        屏幕.blit(左文, 左框.topleft)
        屏幕.blit(右文, 右框.topleft)

    def _绘制星星行(self, 屏幕: pygame.Surface, 区域: pygame.Rect, 星数: int):
        星数 = max(0, int(星数))
        if 星数 <= 0:
            return

        if self._星星原图 is None:
            字体 = _获取字体(max(18, int(区域.h * 0.55)), 是否粗体=False)
            文字面 = 字体.render("★" * min(20, 星数), True, (255, 220, 80))
            文字框 = 文字面.get_rect(center=区域.center)
            屏幕.blit(文字面, 文字框.topleft)
            return

        目标高 = max(10, int(区域.h * 0.35))
        try:
            星图 = pygame.transform.smoothscale(
                self._星星原图,
                (
                    int(
                        self._星星原图.get_width()
                        * (目标高 / max(1, self._星星原图.get_height()))
                    ),
                    目标高,
                ),
            ).convert_alpha()
        except Exception:
            return

        星宽, 星高 = 星图.get_size()
        间距 = max(2, int(星宽 * 0.12))
        每行最大 = 12

        行列表 = []
        剩余星数 = 星数
        while 剩余星数 > 0:
            本行数量 = min(每行最大, 剩余星数)
            行列表.append(本行数量)
            剩余星数 -= 本行数量

        行距 = max(6, int(星高 * 0.25))
        总高 = len(行列表) * 星高 + max(0, len(行列表) - 1) * 行距
        起始y = 区域.y + (区域.h - 总高) // 2

        当前y = 起始y
        for 数量 in 行列表:
            总宽 = 数量 * 星宽 + max(0, 数量 - 1) * 间距
            起始x = 区域.centerx - 总宽 // 2
            for 索引 in range(数量):
                屏幕.blit(星图, (起始x + 索引 * (星宽 + 间距), 当前y))
            当前y += 星高 + 行距

    def _绘制左下记录(self, 屏幕: pygame.Surface, 区域: pygame.Rect):
        绿色 = (167, 226, 180)
        粉色 = (224, 167, 178)
        字体 = _获取字体(max(22, int(区域.h * 0.24)), 是否粗体=False)
        行高 = int(字体.get_height() * 1.35)

        记录保持者 = str(getattr(self, "_个人昵称", "未知") or "未知")
        最高分 = int(getattr(self, "_最高分", 0) or 0)

        文1 = 字体.render(f"记录保持者：         {记录保持者}", True, 绿色)
        文2 = 字体.render(f"最高分：         {最高分}", True, 粉色)

        屏幕.blit(文1, (区域.x + 10, 区域.y))
        屏幕.blit(文2, (区域.x + 10, 区域.y + 行高))

    def _绘制右下记录(self, 屏幕: pygame.Surface, 区域: pygame.Rect):
        蓝绿 = (109, 204, 191)
        白色 = (255, 255, 255)
        淡黄 = (247, 253, 235)

        字体 = _获取字体(max(22, int(区域.h * 0.20)), 是否粗体=False)
        行高 = int(字体.get_height() * 1.30)

        最大等级 = int(getattr(self, "_最大等级", 0) or 0)
        昵称 = str(getattr(self, "_个人昵称", "未知") or "未知")
        舞队 = "e舞成名重构版玩家大队"
        店名 = f"{昵称}的电脑"

        文1 = 字体.render(f"级别：{最大等级}", True, 蓝绿)
        文2 = 字体.render(f"所属舞队：{舞队}", True, 白色)
        文3 = 字体.render(f"店名：{店名}", True, 淡黄)

        屏幕.blit(文1, (区域.x + 10, 区域.y))
        屏幕.blit(文2, (区域.x + 10, 区域.y + 行高))
        屏幕.blit(文3, (区域.x + 10, 区域.y + 行高 * 2))

    def _映射到屏幕_rect(self, 边界框) -> pygame.Rect:
        屏幕 = self.上下文["屏幕"]
        屏幕宽, 屏幕高 = 屏幕.get_size()

        缩放比例 = min(屏幕宽 / self._设计宽, 屏幕高 / self._设计高)
        内容宽 = self._设计宽 * 缩放比例
        内容高 = self._设计高 * 缩放比例
        偏移x = (屏幕宽 - 内容宽) / 2.0
        偏移y = (屏幕高 - 内容高) / 2.0

        左, 上, 右, 下 = 边界框
        x坐标 = int(偏移x + 左 * 缩放比例)
        y坐标 = int(偏移y + 上 * 缩放比例)
        宽度 = int((右 - 左) * 缩放比例)
        高度 = int((下 - 上) * 缩放比例)
        return pygame.Rect(x坐标, y坐标, max(1, 宽度), max(1, 高度))
