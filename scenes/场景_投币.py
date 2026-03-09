import json
import os
import time
import pygame

from core.对局状态 import 初始化对局流程, 消耗信用, 取每局所需信用
from core.踏板控制 import 踏板动作_左, 踏板动作_右, 踏板动作_确认
from ui.按钮特效 import 公用按钮点击特效, 公用按钮音效


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

    def __init__(self, 上下文: dict):
        self.上下文 = 上下文
        资源 = self.上下文["资源"]

        self._背景视频 = self.上下文.get("背景视频")
        self._开始时间 = time.time()
        self._缓存尺寸 = (0, 0)

        self._阶段 = self._阶段_投币
        self._是否显示logo = False
        self._hover_1p = False
        self._hover_2p = False
        self._踏板选中玩家数: int | None = None

        self._遮罩图 = None
        self._logo图 = None
        self._1p图 = None
        self._2p图 = None
        self._1p图_hover = None
        self._2p图_hover = None

        self._1p_rect = pygame.Rect(0, 0, 1, 1)
        self._2p_rect = pygame.Rect(0, 0, 1, 1)

        self._logo原图 = self._安全加载图片(资源.get("投币_logo", ""), 透明=True)
        self._联网原图 = self._安全加载图片(资源.get("投币_联网图标", ""), 透明=True)
        self._1p原图 = self._安全加载图片(资源.get("1P按钮", ""), 透明=True)
        self._2p原图 = self._安全加载图片(资源.get("2P按钮", ""), 透明=True)

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

        根目录 = str(资源.get("根", "") or os.getcwd())
        self._全局设置路径 = os.path.join(根目录, "json", "全局设置.json")
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
        self._选择动画进行中 = False
        self._选择动画结束时间 = 0.0
        self._待切换结果 = None
        self._确保缓存()
        self._按当前信用刷新阶段(允许播放满额音效=False)
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
        if int(玩家数) == 1:
            self._1p特效.触发()
        else:
            self._2p特效.触发()

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
            os.makedirs(os.path.dirname(self._全局设置路径), exist_ok=True)
            with open(self._全局设置路径, "w", encoding="utf-8") as 文件:
                json.dump(数据, 文件, ensure_ascii=False, indent=2)
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
        self._是否显示logo = True
        self._播放玩家选择背景音乐(播放满额音效=播放满额音效)

    def _按当前信用刷新阶段(self, 允许播放满额音效: bool):
        当前信用 = self._取当前信用()
        所需信用 = self._取所需信用()
        self._是否显示logo = bool(当前信用 > 0)

        if 当前信用 >= 所需信用:
            首次满额 = self._阶段 != self._阶段_玩家选择
            self._切换到玩家选择阶段(播放满额音效=bool(允许播放满额音效 and 首次满额))
            return

        if self._阶段 != self._阶段_投币:
            self._切换到投币阶段()

    def 退出(self):
        pass

    def _绘制玩家选择按钮(self, 屏幕: pygame.Surface):
        if self._1p图:
            if self._1p特效.是否动画中():
                self._1p特效.绘制按钮(屏幕, self._1p图, self._1p_rect)
            else:
                if self._踏板选中玩家数 == 1:
                    self._绘制_按中心缩放(屏幕, self._1p图, self._1p_rect, 1.12)
                elif self._hover_1p and self._1p图_hover:
                    临时框 = self._1p图_hover.get_rect(center=self._1p_rect.center)
                    屏幕.blit(self._1p图_hover, 临时框.topleft)
                else:
                    屏幕.blit(self._1p图, self._1p_rect.topleft)

        if self._2p图:
            if self._2p特效.是否动画中():
                self._2p特效.绘制按钮(屏幕, self._2p图, self._2p_rect)
            else:
                if self._踏板选中玩家数 == 2:
                    self._绘制_按中心缩放(屏幕, self._2p图, self._2p_rect, 1.12)
                elif self._hover_2p and self._2p图_hover:
                    临时框 = self._2p图_hover.get_rect(center=self._2p_rect.center)
                    屏幕.blit(self._2p图_hover, 临时框.topleft)
                else:
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
        新图 = pygame.transform.smoothscale(图片, (目标宽, 目标高)).convert_alpha()
        新框 = 新图.get_rect(center=基准框.center)
        屏幕.blit(新图, 新框.topleft)

    def _绘制文本(self, 屏幕, 文本, 字体, 颜色, 位置, 对齐="center"):
        文本面 = 字体.render(文本, True, 颜色)
        文本框 = 文本面.get_rect()
        setattr(文本框, 对齐, 位置)
        屏幕.blit(文本面, 文本框)
        return 文本框

    def _确保缓存(self):
        屏幕 = self.上下文["屏幕"]
        宽, 高 = 屏幕.get_size()
        if (宽, 高) == self._缓存尺寸:
            return
        self._缓存尺寸 = (宽, 高)

        暗层 = pygame.Surface((宽, 高), pygame.SRCALPHA)
        暗层.fill((0, 0, 0, 128))
        self._遮罩图 = 暗层

        logo框 = self._映射到屏幕_rect(self._bbox_logo)
        self._logo图 = (
            pygame.transform.smoothscale(
                self._logo原图, (logo框.w, logo框.h)
            ).convert_alpha()
            if self._logo原图
            else None
        )

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

    def 绘制(self):
        from core.工具 import 绘制底部联网与信用

        屏幕 = self.上下文["屏幕"]
        self._确保缓存()
        字体_credit = self.上下文["字体"]["投币_credit字"]
        字体_请投币 = self.上下文["字体"]["投币_请投币字"]

        宽, 高 = 屏幕.get_size()
        当前信用 = self._取当前信用()
        所需信用 = self._取所需信用()

        屏幕.fill((0, 0, 0))
        背景面 = self._背景视频.读取覆盖帧(宽, 高) if self._背景视频 else None
        if 背景面 is not None:
            屏幕.blit(背景面, (0, 0))

        if self._遮罩图:
            屏幕.blit(self._遮罩图, (0, 0))

        if self._是否显示logo and self._logo图:
            logo_rect = self._映射到屏幕_rect(self._bbox_logo)
            屏幕.blit(self._logo图, logo_rect.topleft)

        当前时间 = time.time()
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
        else:
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
