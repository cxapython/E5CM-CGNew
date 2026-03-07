import os
import math
import time
import pygame

try:
    import cv2

    _可用视频 = True
except Exception:
    cv2 = None
    _可用视频 = False

from ui.按钮特效 import 公用按钮点击特效, 公用按钮音效
from ui.场景过渡 import 公用放大过渡器
from core.踏板控制 import 踏板动作_左, 踏板动作_右, 踏板动作_确认


class 视频循环播放器:
    def __init__(self, 视频路径: str):
        self.视频路径 = 视频路径
        self._cap = None
        self._fps = 30.0
        self._上一帧面 = None
        self._上次读帧时间 = 0.0
        self._背景视频 = self.上下文.get("背景视频")

    def 打开(self):
        if not _可用视频 or not self.视频路径:
            return
        self.关闭()
        self._cap = cv2.VideoCapture(self.视频路径)
        fps = 0.0
        try:
            fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        except Exception:
            fps = 0.0
        self._fps = fps if fps and fps > 1 else 30.0
        self._上次读帧时间 = 0.0

    def 关闭(self):
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
        self._cap = None

    def 读取帧(self):
        if not _可用视频:
            return self._上一帧面
        if self._cap is None:
            self.打开()
            if self._cap is None:
                return self._上一帧面

        现在 = time.time()
        间隔 = 1.0 / max(1.0, self._fps)
        if self._上次读帧时间 and (现在 - self._上次读帧时间) < 间隔:
            return self._上一帧面
        self._上次读帧时间 = 现在

        ok, frame = self._cap.read()
        if not ok or frame is None:
            try:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self._cap.read()
            except Exception:
                ok, frame = False, None

        if not ok or frame is None:
            return self._上一帧面

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        面 = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        self._上一帧面 = 面
        return 面


class 场景_登陆磁卡:
    名称 = "登陆磁卡"

    _设计宽 = 2048
    _设计高 = 1152

    _bbox_场景1_游客 = (255, 274, 967, 886)
    _bbox_场景1_vip = (1081, 353, 1526, 799)
    _bbox_场景2_游客 = (277, 247, 784, 754)

    _bbox_刷卡内容 = (694, 542, 1348, 809)
    _bbox_刷卡背景 = (500, 312, 1542, 1039)

    _刷卡背景缩放系数 = 1.3
    _刷卡内容宽占比 = 0.7

    _贵宾装饰宽占比 = 0.5
    _贵宾装饰外溢x占比 = 0.0
    _贵宾装饰外溢y占比 = -0.01

    _bbox_磁卡目标 = (1197, 764, 1859, 1152)
    _磁卡缩放系数 = 0.5

    _场景1游客放大系数 = 1.4
    _事件_延迟切场景 = pygame.USEREVENT + 24  # 避免和大模式(+23)冲突

    def __init__(self, 上下文: dict):
        self.上下文 = 上下文
        资源 = 上下文["资源"]

        # ✅ 全局背景视频（main.py 注入，跨场景不断）
        self._背景视频 = 上下文.get("背景视频")

        # 通用资源
        self._联网原图 = self._安全加载图片(资源["投币_联网图标"], 透明=True)

        # 顶栏
        self._top栏原图 = self._安全加载图片(
            os.path.join(资源["根"], "UI-img", "top栏", "top栏背景.png"), 透明=True
        )
        self._个人中心原图 = self._安全加载图片(
            os.path.join(资源["根"], "UI-img", "top栏", "个人中心.png"), 透明=True
        )

        # 场景1
        self._场景1游客原图 = self._安全加载图片(
            os.path.join(资源["根"], "UI-img", "个人中心-登陆", "场景1-游客.png"),
            透明=True,
        )
        self._场景1vip原图 = self._安全加载图片(
            os.path.join(
                资源["根"], "UI-img", "个人中心-登陆", "场景1-vip磁卡-半透明.png"
            ),
            透明=True,
        )

        # 场景2
        self._场景2游客原图 = self._安全加载图片(
            os.path.join(资源["根"], "UI-img", "个人中心-登陆", "场景2-游客.png"),
            透明=True,
        )
        self._刷卡背景原图 = self._安全加载图片(
            os.path.join(资源["根"], "UI-img", "个人中心-登陆", "请刷卡背景.png"),
            透明=True,
        )
        self._刷卡内容原图 = self._安全加载图片(
            os.path.join(资源["根"], "UI-img", "个人中心-登陆", "请刷卡内容.png"),
            透明=True,
        )
        self._刷卡内容白原图 = self._安全加载图片(
            os.path.join(资源["根"], "UI-img", "个人中心-登陆", "请刷卡内容白色.png"),
            透明=True,
        )
        self._磁卡原图 = self._安全加载图片(
            os.path.join(资源["根"], "UI-img", "个人中心-登陆", "磁卡.png"),
            透明=True,
        )
        self._贵宾装饰原图 = self._安全加载图片(
            os.path.join(资源["根"], "UI-img", "个人中心-登陆", "贵宾装饰.png"),
            透明=True,
        )

        # 音效 + 点击特效
        # 音效 + 点击特效
        self.按钮音效 = 公用按钮音效(资源.get("按钮音效", ""))

        # ✅ 刷卡成功登录音效（来自 常量与路径.py: "刷卡音效": 拼路径("Buttonsound", "刷卡.mp3")）
        刷卡音效路径 = 资源.get("刷卡音效", "") or 资源.get("按钮音效", "")
        self.刷卡音效 = 公用按钮音效(刷卡音效路径)

        self._游客点击特效 = 公用按钮点击特效(
            总时长=0.3, 缩小阶段=0.1, 缩小到=0.90, 放大到=4.00, 透明起始=255, 透明结束=0
        )

        # 缓存
        self._缓存尺寸 = (0, 0)
        self._遮罩图 = None
        self._top栏图 = None
        self._个人中心图 = None

        self._场景1游客图 = None
        self._场景1vip图 = None
        self._场景2游客图 = None
        self._刷卡背景图 = None
        self._刷卡内容图 = None
        self._刷卡内容白图 = None
        self._磁卡图 = None
        self._贵宾装饰图 = None

        self._rect_top栏 = pygame.Rect(0, 0, 1, 1)
        self._rect_个人中心 = pygame.Rect(0, 0, 1, 1)

        self._rect_场景1游客 = pygame.Rect(0, 0, 1, 1)
        self._rect_场景1vip = pygame.Rect(0, 0, 1, 1)

        self._rect_场景2游客 = pygame.Rect(0, 0, 1, 1)
        self._rect_刷卡背景 = pygame.Rect(0, 0, 1, 1)
        self._rect_刷卡内容 = pygame.Rect(0, 0, 1, 1)
        self._rect_贵宾装饰 = pygame.Rect(0, 0, 1, 1)

        self._磁卡当前rect = pygame.Rect(0, 0, 1, 1)
        self._磁卡目标rect = pygame.Rect(0, 0, 1, 1)

        # 状态
        self._子场景 = 1

        self._按钮消失中 = False
        self._按钮消失开始 = 0.0

        self._刷卡放大开始 = 0.0
        self._闪烁开始 = time.time()

        self._磁卡滑入开始 = 0.0
        self._拖拽中 = False
        self._拖拽偏移 = (0, 0)
        self._hover_场景1游客 = False
        self._hover_场景1vip = False
        self._踏板选中项: str | None = None
        self._自动刷卡中 = False
        self._自动刷卡开始 = 0.0
        self._自动刷卡起点 = (0.0, 0.0)
        self._自动刷卡终点 = (0.0, 0.0)
        # ✅ 全屏放大过渡（320ms）
        self._全屏放大过渡 = 公用放大过渡器(总时长毫秒=320)
        self._正在放大切场景 = False
        self._延迟目标场景: str | None = None

    def _开始放大切场景(
        self, 起始图: pygame.Surface | None, 起始rect: pygame.Rect, 目标场景名: str
    ):
        """
        启动公用放大过渡，并在过渡结束后通过 USEREVENT 切场景。
        """
        if self._正在放大切场景:
            return

        if 起始图 is None:
            # 兜底：没图就直接切（但仍禁用黑屏，避免突兀）
            self._延迟目标场景 = 目标场景名
            self._正在放大切场景 = False
            pygame.time.set_timer(self._事件_延迟切场景, 1)
            return

        self._正在放大切场景 = True
        self._延迟目标场景 = 目标场景名

        try:
            self._全屏放大过渡.开始(起始图, 起始rect)
        except Exception:
            # 兜底：开始失败就直接切
            pygame.time.set_timer(self._事件_延迟切场景, 1)
            return

        pygame.time.set_timer(self._事件_延迟切场景, 320, loops=1)

    # ---------------- 工具 ----------------
    def _安全加载图片(self, 路径: str, 透明: bool):
        try:
            if not 路径 or (not os.path.isfile(路径)):
                return None
            图 = pygame.image.load(路径)
            return 图.convert_alpha() if 透明 else 图.convert()
        except Exception:
            return None

    def _cover缩放(
        self, 图片: pygame.Surface, 目标宽: int, 目标高: int
    ) -> pygame.Surface:
        ow, oh = 图片.get_size()
        比例 = max(目标宽 / max(1, ow), 目标高 / max(1, oh))
        nw, nh = max(1, int(ow * 比例)), max(1, int(oh * 比例))
        缩放 = pygame.transform.smoothscale(图片, (nw, nh))
        x = (nw - 目标宽) // 2
        y = (nh - 目标高) // 2
        out = pygame.Surface((目标宽, 目标高), pygame.SRCALPHA)
        out.blit(缩放, (0, 0), area=pygame.Rect(x, y, 目标宽, 目标高))
        return out

    def _映射到屏幕_rect(self, bbox):
        屏幕 = self.上下文["屏幕"]
        w, h = 屏幕.get_size()

        scale = min(w / self._设计宽, h / self._设计高)
        content_w = self._设计宽 * scale
        content_h = self._设计高 * scale
        ox = (w - content_w) / 2.0
        oy = (h - content_h) / 2.0

        l, t, r, b = bbox
        x = int(ox + l * scale)
        y = int(oy + t * scale)
        ww = int((r - l) * scale)
        hh = int((b - t) * scale)
        return pygame.Rect(x, y, max(1, ww), max(1, hh))

    def _确保缓存(self):
        from ui.top栏 import 生成top栏

        屏幕 = self.上下文["屏幕"]
        w, h = 屏幕.get_size()
        if (w, h) == self._缓存尺寸:
            return
        self._缓存尺寸 = (w, h)

        暗层 = pygame.Surface((w, h), pygame.SRCALPHA)
        暗层.fill((0, 0, 0, 128))
        self._遮罩图 = 暗层

        # top栏
        self._rect_top栏, self._top栏图, self._rect_个人中心, self._个人中心图 = (
            生成top栏(
                屏幕=屏幕,
                top背景原图=self._top栏原图,
                标题原图=self._个人中心原图,
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
        )

        # 场景1按钮
        self._rect_场景1游客 = self._映射到屏幕_rect(self._bbox_场景1_游客)
        self._rect_场景1vip = self._映射到屏幕_rect(self._bbox_场景1_vip)

        self._场景1游客图 = (
            pygame.transform.smoothscale(
                self._场景1游客原图, (self._rect_场景1游客.w, self._rect_场景1游客.h)
            ).convert_alpha()
            if self._场景1游客原图
            else None
        )
        self._场景1vip图 = (
            pygame.transform.smoothscale(
                self._场景1vip原图, (self._rect_场景1vip.w, self._rect_场景1vip.h)
            ).convert_alpha()
            if self._场景1vip原图
            else None
        )

        # 场景2游客
        self._rect_场景2游客 = self._映射到屏幕_rect(self._bbox_场景2_游客)
        self._场景2游客图 = (
            pygame.transform.smoothscale(
                self._场景2游客原图, (self._rect_场景2游客.w, self._rect_场景2游客.h)
            ).convert_alpha()
            if self._场景2游客原图
            else None
        )

        # 请刷卡背景（屏幕居中+缩放）
        scale = min(w / max(1, self._设计宽), h / max(1, self._设计高))
        bg_scale = scale * float(self._刷卡背景缩放系数)

        if self._刷卡背景原图:
            bg_w = max(1, int(self._刷卡背景原图.get_width() * bg_scale))
            bg_h = max(1, int(self._刷卡背景原图.get_height() * bg_scale))
            self._刷卡背景图 = pygame.transform.smoothscale(
                self._刷卡背景原图, (bg_w, bg_h)
            ).convert_alpha()
            self._rect_刷卡背景 = self._刷卡背景图.get_rect()
            self._rect_刷卡背景.center = (w // 2, h // 2)
        else:
            self._刷卡背景图 = None
            self._rect_刷卡背景 = pygame.Rect(w // 2, h // 2, 1, 1)

        # 请刷卡内容（居中，按背景宽）
        if self._刷卡内容原图 and self._刷卡背景图:
            内容目标宽 = max(
                1, int(self._rect_刷卡背景.w * float(self._刷卡内容宽占比))
            )
            比例 = 内容目标宽 / max(1, self._刷卡内容原图.get_width())
            内容目标高 = max(1, int(self._刷卡内容原图.get_height() * 比例))

            self._刷卡内容图 = pygame.transform.smoothscale(
                self._刷卡内容原图, (内容目标宽, 内容目标高)
            ).convert_alpha()
            self._刷卡内容白图 = (
                pygame.transform.smoothscale(
                    self._刷卡内容白原图, (内容目标宽, 内容目标高)
                ).convert_alpha()
                if self._刷卡内容白原图
                else None
            )
            self._rect_刷卡内容 = self._刷卡内容图.get_rect()
            self._rect_刷卡内容.center = self._rect_刷卡背景.center
        else:
            self._刷卡内容图 = None
            self._刷卡内容白图 = None
            self._rect_刷卡内容 = self._rect_刷卡背景.copy()

        # 贵宾装饰：中心贴背景右上角（允许外溢）
        if self._贵宾装饰原图 and self._刷卡背景图:
            装饰目标宽 = int(self._rect_刷卡背景.w * float(self._贵宾装饰宽占比))
            比例 = 装饰目标宽 / max(1, self._贵宾装饰原图.get_width())
            装饰目标高 = max(1, int(self._贵宾装饰原图.get_height() * 比例))

            self._贵宾装饰图 = pygame.transform.smoothscale(
                self._贵宾装饰原图, (装饰目标宽, 装饰目标高)
            ).convert_alpha()
            self._rect_贵宾装饰 = self._贵宾装饰图.get_rect()

            dx = int(self._rect_刷卡背景.w * float(self._贵宾装饰外溢x占比))
            dy = int(self._rect_刷卡背景.h * float(self._贵宾装饰外溢y占比))
            self._rect_贵宾装饰.center = (
                self._rect_刷卡背景.right + dx,
                self._rect_刷卡背景.top + dy,
            )
        else:
            self._贵宾装饰图 = None
            self._rect_贵宾装饰 = pygame.Rect(0, 0, 1, 1)

        # 磁卡（缩小）
        原目标 = self._映射到屏幕_rect(self._bbox_磁卡目标)
        self._磁卡目标rect = 原目标.copy()

        缩放 = float(self._磁卡缩放系数)
        nw = max(1, int(原目标.w * 缩放))
        nh = max(1, int(原目标.h * 缩放))
        self._磁卡目标rect.size = (nw, nh)
        self._磁卡目标rect.center = 原目标.center

        self._磁卡图 = (
            pygame.transform.smoothscale(self._磁卡原图, (nw, nh)).convert_alpha()
            if self._磁卡原图
            else None
        )

    # ---------------- 生命周期 ----------------

    def 进入(self):
        """
        ✅ 这里改成 排行榜.mp3，并且“继续刚刚的播放”：
        - 如果前一个场景已经在播排行榜BGM：这里不再调用 播放循环()，避免从头重播
        - 如果没播过：这里才切到排行榜.mp3
        """
        资源 = self.上下文.get("资源", {})
        状态 = self.上下文.get("状态", {})

        # ✅ 排行榜BGM路径（固定 backsound/排行榜.mp3）
        根目录 = str(资源.get("根", "") or os.getcwd())
        排行榜BGM路径 = os.path.join(根目录, "冷资源", "backsound", "排行榜.mp3")

        # ✅ 是否已在播排行榜（用你前面我们建立的状态位去重，保证“继续播放不重启”）
        已经在播排行榜 = False
        try:
            已经在播排行榜 = bool(状态.get("bgm_排行榜_已播放", False))
        except Exception:
            已经在播排行榜 = False

        if not 已经在播排行榜:
            if os.path.isfile(排行榜BGM路径):
                try:
                    self.上下文["音乐"].播放循环(排行榜BGM路径)
                    状态["bgm_排行榜_已播放"] = True
                except Exception:
                    # 兜底：播放失败就别强行停当前音乐，避免静默
                    pass
            else:
                # 兜底：文件不存在就别乱切，避免黑屏/没声
                # （你也可以改成 fallback 到资源["投币_BGM"]，但“继续播放”更符合你现在的目标）
                pass

        # ===== 原逻辑：进入场景状态复位 =====
        self._子场景 = 1
        self._按钮消失中 = False
        self._hover_场景1游客 = False
        self._hover_场景1vip = False
        self._踏板选中项 = None
        self._自动刷卡中 = False
        self._自动刷卡开始 = 0.0

        # ✅ 过渡状态复位
        self._正在放大切场景 = False
        self._延迟目标场景 = None
        pygame.time.set_timer(self._事件_延迟切场景, 0)

        # 缓存刷新
        self._确保缓存()

    def 退出(self):
        pygame.time.set_timer(self._事件_延迟切场景, 0)

    def 更新(self):
        if (self._子场景 != 2) or (not self._自动刷卡中):
            return None

        经过 = (time.time() - float(self._自动刷卡开始 or 0.0)) / 0.48
        t = max(0.0, min(1.0, float(经过)))
        k = 1.0 - (1.0 - t) ** 3

        起点x, 起点y = self._自动刷卡起点
        终点x, 终点y = self._自动刷卡终点
        抛物线抬升 = math.sin(k * math.pi) * max(
            18.0, float(self._磁卡目标rect.h) * 0.14
        )
        cx = 起点x + (终点x - 起点x) * k
        cy = 起点y + (终点y - 起点y) * k - 抛物线抬升
        self._磁卡当前rect.center = (int(cx), int(cy))

        if t >= 1.0:
            self._自动刷卡中 = False
            return self._触发刷卡成功()
        return None

    # ---------------- 绘制 ----------------
    def 绘制(self):
        屏幕 = self.上下文["屏幕"]
        self._确保缓存()

        w, h = 屏幕.get_size()

        # ✅ 背景视频（全局连续）
        屏幕.fill((0, 0, 0))
        帧 = self._背景视频.读取帧() if self._背景视频 else None
        if 帧 is not None:
            背景面 = self._cover缩放(帧, w, h)
            屏幕.blit(背景面, (0, 0))

        # 遮罩
        if self._遮罩图:
            屏幕.blit(self._遮罩图, (0, 0))

        # top栏
        if self._top栏图:
            屏幕.blit(self._top栏图, self._rect_top栏.topleft)
        if self._个人中心图:
            屏幕.blit(self._个人中心图, self._rect_个人中心.topleft)

        from core.工具 import 绘制底部联网与信用

        # ✅ 底部联网图标 + CREDIT（统一用 1P/2P 标准）
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

        # 子场景
        if self._子场景 == 1:
            self._绘制_场景1(屏幕)
        else:
            self._绘制_场景2(屏幕)

            # ✅ 最上层绘制：全屏放大过渡盖住一切
        if self._全屏放大过渡.是否进行中():
            self._全屏放大过渡.更新并绘制(屏幕)

    def _缓动逼近(
        self, 当前值: float, 目标值: float, 帧间隔: float, 速度: float
    ) -> float:
        try:
            当前值 = float(当前值)
        except Exception:
            当前值 = 0.0

        try:
            目标值 = float(目标值)
        except Exception:
            目标值 = 0.0

        try:
            帧间隔 = float(帧间隔)
        except Exception:
            帧间隔 = 0.016

        try:
            速度 = float(速度)
        except Exception:
            速度 = 10.0

        帧间隔 = max(0.0, min(0.05, 帧间隔))
        速度 = max(0.0, 速度)

        if abs(目标值 - 当前值) < 0.0001:
            return 目标值

        插值 = min(1.0, 帧间隔 * 速度)
        return 当前值 + (目标值 - 当前值) * 插值

    def _绘制_场景1(self, 屏幕: pygame.Surface):
        现在 = time.time()

        if not hasattr(self, "_场景1悬停插值_游客"):
            self._场景1悬停插值_游客 = 0.0
        if not hasattr(self, "_场景1悬停插值_vip"):
            self._场景1悬停插值_vip = 0.0
        if not hasattr(self, "_场景1悬停更新时间"):
            self._场景1悬停更新时间 = 0.0

        上次更新时间 = float(getattr(self, "_场景1悬停更新时间", 0.0) or 0.0)
        if 上次更新时间 <= 0.0:
            帧间隔 = 0.016
        else:
            帧间隔 = max(0.0, min(0.05, 现在 - 上次更新时间))
        self._场景1悬停更新时间 = 现在

        游客激活 = bool(self._hover_场景1游客 or self._踏板选中项 == "游客")
        vip激活 = bool(self._hover_场景1vip or self._踏板选中项 == "VIP")

        self._场景1悬停插值_游客 = self._缓动逼近(
            float(getattr(self, "_场景1悬停插值_游客", 0.0) or 0.0),
            1.0 if 游客激活 else 0.0,
            帧间隔,
            12.0 if 游客激活 else 14.0,
        )
        self._场景1悬停插值_vip = self._缓动逼近(
            float(getattr(self, "_场景1悬停插值_vip", 0.0) or 0.0),
            1.0 if vip激活 else 0.0,
            帧间隔,
            12.0 if vip激活 else 14.0,
        )

        if self._按钮消失中:
            t = (现在 - self._按钮消失开始) / 0.2
            t = max(0.0, min(1.0, t))
            scale = max(0.0, 1.0 - t)
        else:
            scale = 1.0

        游客呼吸 = 1.0 + math.sin(现在 * 5.8) * 0.008 * float(self._场景1悬停插值_游客)
        vip呼吸 = 1.0 + math.sin(现在 * 5.2 + 0.35) * 0.007 * float(
            self._场景1悬停插值_vip
        )

        游客scale = (
            scale
            * float(self._场景1游客放大系数)
            * (1.0 + 0.045 * float(self._场景1悬停插值_游客))
            * 游客呼吸
        )
        vipscale = scale * (1.0 + 0.040 * float(self._场景1悬停插值_vip)) * vip呼吸

        游客基准rect = self._rect_场景1游客.copy()
        vip基准rect = self._rect_场景1vip.copy()

        游客上浮 = -int(
            self._rect_场景1游客.h * 0.018 * float(self._场景1悬停插值_游客)
        )
        vip上浮 = -int(self._rect_场景1vip.h * 0.015 * float(self._场景1悬停插值_vip))

        游客基准rect.y += 游客上浮
        vip基准rect.y += vip上浮

        if float(self._场景1悬停插值_游客) > 0.01:
            self._绘制_场景1高亮底光(
                屏幕,
                游客基准rect,
                强度=float(self._场景1悬停插值_游客),
                主色=(150, 215, 255),
            )

        if float(self._场景1悬停插值_vip) > 0.01:
            self._绘制_场景1高亮底光(
                屏幕,
                vip基准rect,
                强度=float(self._场景1悬停插值_vip),
                主色=(255, 215, 135),
            )

        if self._场景1游客图:
            self._绘制_按中心缩放(
                屏幕,
                self._场景1游客图,
                游客基准rect,
                游客scale,
            )

        if self._场景1vip图:
            self._绘制_按中心缩放(
                屏幕,
                self._场景1vip图,
                vip基准rect,
                vipscale,
            )

        if self._按钮消失中 and scale <= 0.001:
            self._按钮消失中 = False
            self._进入场景2()

    def _绘制_场景1高亮底光(
        self,
        屏幕: pygame.Surface,
        基准rect: pygame.Rect,
        *,
        强度: float,
        主色: tuple[int, int, int],
    ):
        try:
            强度 = float(强度)
        except Exception:
            强度 = 0.0

        if 强度 <= 0.001:
            return

        强度 = max(0.0, min(1.0, 强度))

        glow_w = max(1, int(基准rect.w * (1.06 + 0.08 * 强度)))
        glow_h = max(1, int(基准rect.h * (1.04 + 0.06 * 强度)))

        光晕 = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)

        外层rect = 光晕.get_rect().inflate(-int(glow_w * 0.04), -int(glow_h * 0.08))
        中层rect = 光晕.get_rect().inflate(-int(glow_w * 0.16), -int(glow_h * 0.20))
        内层rect = 光晕.get_rect().inflate(-int(glow_w * 0.30), -int(glow_h * 0.34))

        外层颜色 = (主色[0], 主色[1], 主色[2], int(12 + 16 * 强度))
        中层颜色 = (主色[0], 主色[1], 主色[2], int(18 + 22 * 强度))
        内层颜色 = (255, 255, 255, int(6 + 10 * 强度))

        pygame.draw.ellipse(光晕, 外层颜色, 外层rect)
        pygame.draw.ellipse(光晕, 中层颜色, 中层rect)
        pygame.draw.ellipse(光晕, 内层颜色, 内层rect)

        光晕rect = 光晕.get_rect(
            center=(基准rect.centerx, int(基准rect.centery + 基准rect.h * 0.02))
        )
        屏幕.blit(光晕, 光晕rect.topleft)

    def _进入场景2(self):
        self._子场景 = 2
        self._刷卡放大开始 = time.time()
        self._闪烁开始 = time.time()
        self._磁卡滑入开始 = time.time()
        self._拖拽中 = False
        self._自动刷卡中 = False
        self._自动刷卡开始 = 0.0

        self._磁卡当前rect = self._磁卡目标rect.copy()
        self._磁卡当前rect.y = self._磁卡目标rect.y + int(self._磁卡目标rect.h * 0.35)

    def _绘制_场景2(self, 屏幕: pygame.Surface):
        现在 = time.time()

        if self._场景2游客图:
            屏幕.blit(self._场景2游客图, self._rect_场景2游客.topleft)

        背景scale = 1.0
        t = (现在 - self._刷卡放大开始) / 0.2
        if t < 1.0:
            t = max(0.0, min(1.0, t))
            背景scale = 1.25 - 0.25 * t

        if self._刷卡背景图:
            self._绘制_按中心缩放(
                屏幕, self._刷卡背景图, self._rect_刷卡背景, 背景scale
            )

        if self._贵宾装饰图:
            屏幕.blit(self._贵宾装饰图, self._rect_贵宾装饰.topleft)

        闪 = int((现在 - self._闪烁开始) // 1) % 2
        内容图 = self._刷卡内容白图 if 闪 == 1 else self._刷卡内容图
        if 内容图:
            屏幕.blit(内容图, self._rect_刷卡内容.topleft)

        if self._磁卡图:
            if (not self._拖拽中) and (not self._自动刷卡中):
                t2 = (现在 - self._磁卡滑入开始) / 0.3
                t2 = max(0.0, min(1.0, t2))
                y0 = self._磁卡目标rect.y + int(self._磁卡目标rect.h * 0.35)
                y1 = self._磁卡目标rect.y
                self._磁卡当前rect.x = self._磁卡目标rect.x
                self._磁卡当前rect.y = int(y0 + (y1 - y0) * t2)

            屏幕.blit(self._磁卡图, self._磁卡当前rect.topleft)

    def _绘制_按中心缩放(
        self,
        屏幕: pygame.Surface,
        图: pygame.Surface,
        基准rect: pygame.Rect,
        scale: float,
    ):
        if scale >= 0.999:
            屏幕.blit(图, 基准rect.topleft)
            return
        if scale <= 0.001:
            return
        ww = max(1, int(基准rect.w * scale))
        hh = max(1, int(基准rect.h * scale))
        x = 基准rect.centerx - ww // 2
        y = 基准rect.centery - hh // 2
        缩 = pygame.transform.smoothscale(图, (ww, hh)).convert_alpha()
        屏幕.blit(缩, (x, y))

    def _执行场景1选择(self, 选项: str):
        if self._按钮消失中:
            return None

        选项 = str(选项 or "").strip().upper()
        if 选项 == "游客".upper():
            self.按钮音效.播放()
            self._游客点击特效.触发()

            起始rect = self._rect_场景1游客.copy()
            k = float(self._场景1游客放大系数)
            起始rect.size = (
                max(1, int(起始rect.w * k)),
                max(1, int(起始rect.h * k)),
            )
            起始rect.center = self._rect_场景1游客.center

            起始图 = None
            if self._场景1游客原图:
                起始图 = pygame.transform.smoothscale(
                    self._场景1游客原图, (起始rect.w, 起始rect.h)
                ).convert_alpha()

            self._开始放大切场景(起始图, 起始rect, "大模式")
            return None

        if 选项 == "VIP":
            self.按钮音效.播放()
            self._按钮消失中 = True
            self._按钮消失开始 = time.time()
        return None

    def _开始自动刷卡(self):
        if self._自动刷卡中 or self._全屏放大过渡.是否进行中():
            return None
        self._拖拽中 = False
        self._自动刷卡中 = True
        self._自动刷卡开始 = time.time()
        self._自动刷卡起点 = (
            float(self._磁卡当前rect.centerx),
            float(self._磁卡当前rect.centery),
        )
        self._自动刷卡终点 = (
            float(self._rect_刷卡背景.centerx),
            float(self._rect_刷卡背景.centery),
        )
        return None

    def _触发刷卡成功(self):
        try:
            self.刷卡音效.播放()
        except Exception:
            try:
                self.按钮音效.播放()
            except Exception:
                pass

        起始图 = self._磁卡图
        起始rect = self._磁卡当前rect.copy()
        self._开始放大切场景(起始图, 起始rect, "个人资料")
        return None

    # ---------------- 事件 ----------------
    def 处理全局踏板(self, 动作: str):
        if self._全屏放大过渡.是否进行中():
            return None

        if self._子场景 == 1:
            if 动作 == 踏板动作_左:
                if self._踏板选中项 != "游客":
                    self.按钮音效.播放()
                self._踏板选中项 = "游客"
                return None
            if 动作 == 踏板动作_右:
                if self._踏板选中项 != "VIP":
                    self.按钮音效.播放()
                self._踏板选中项 = "VIP"
                return None
            if 动作 == 踏板动作_确认 and self._踏板选中项:
                return self._执行场景1选择(str(self._踏板选中项))
            return None

        if self._子场景 == 2 and 动作 == 踏板动作_确认:
            return self._开始自动刷卡()
        return None

    def 处理事件(self, 事件):
        if 事件.type == pygame.VIDEORESIZE:
            return None
            # ✅ 过渡结束 -> 切场景（禁用黑屏）
        if 事件.type == self._事件_延迟切场景:
            pygame.time.set_timer(self._事件_延迟切场景, 0)
            self._正在放大切场景 = False
            if self._延迟目标场景:
                目标 = self._延迟目标场景
                self._延迟目标场景 = None
                return {"切换到": 目标, "禁用黑屏过渡": True}
            return None

        # ✅ 放大过渡进行中：屏蔽交互
        if self._全屏放大过渡.是否进行中():
            return None

        if self._子场景 == 1 and 事件.type == pygame.MOUSEMOTION:
            self._hover_场景1游客 = self._rect_场景1游客.collidepoint(事件.pos)
            self._hover_场景1vip = self._rect_场景1vip.collidepoint(事件.pos)
            return None

        if self._子场景 == 2:
            return self._处理事件_场景2(事件)

        if 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            if self._按钮消失中:
                return None

            # ✅ 场景1：游客 -> 放大过渡切到大模式
            if self._rect_场景1游客.collidepoint(事件.pos):
                self._踏板选中项 = "游客"
                return self._执行场景1选择("游客")

            # VIP：保持你原来的“消失->进入场景2”
            if self._rect_场景1vip.collidepoint(事件.pos):
                self._踏板选中项 = "VIP"
                return self._执行场景1选择("VIP")

        return None

    def _处理事件_场景2(self, 事件):
        if self._自动刷卡中:
            return None

        if 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            if self._rect_场景2游客.collidepoint(事件.pos):
                self.按钮音效.播放()
                self._子场景 = 1
                self._按钮消失中 = False
                self._拖拽中 = False
                self._踏板选中项 = "游客"
                return None

            if self._拖拽中:
                self._拖拽中 = False
                if self._磁卡当前rect.colliderect(self._rect_刷卡背景):
                    return self._触发刷卡成功()

        if 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            if self._磁卡当前rect.collidepoint(事件.pos):
                self._拖拽中 = True
                mx, my = 事件.pos
                self._拖拽偏移 = (mx - self._磁卡当前rect.x, my - self._磁卡当前rect.y)
                return None

        if 事件.type == pygame.MOUSEMOTION:
            if self._拖拽中:
                mx, my = 事件.pos
                ox, oy = self._拖拽偏移
                self._磁卡当前rect.x = mx - ox
                self._磁卡当前rect.y = my - oy
                return None

        return None
