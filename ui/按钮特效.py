import time
import os
import pygame
from core.工具 import 绘制文本, contain缩放, 画圆角面, 安全加载图片


class 公用按钮点击特效:
    """
    通用按钮点击动画：
    - 总时长 0.3s
    - 前 0.1s：缩小到 shrink_to
    - 后 0.2s：放大到 expand_to，并透明度从 255 线性降到 0
    """

    def __init__(
        self,
        总时长: float = 0.3,
        缩小阶段: float = 0.1,
        缩小到: float = 0.90,
        放大到: float = 4.00,
        透明起始: int = 255,
        透明结束: int = 0,
    ):
        self.总时长 = float(总时长)
        self.缩小阶段 = float(缩小阶段)
        self.缩小到 = float(缩小到)
        self.放大到 = float(放大到)
        self.透明起始 = int(透明起始)
        self.透明结束 = int(透明结束)

        self._动画开始 = 0.0
        self._动画中 = False

    def 触发(self):
        self._动画开始 = time.time()
        self._动画中 = True

    def 是否动画中(self) -> bool:
        if not getattr(self, "_动画中", False):
            return False
        import time as _time

        if (_time.time() - getattr(self, "_动画开始", 0.0)) >= float(
            getattr(self, "总时长", 0.3)
        ):
            self._动画中 = False
            return False
        return True

    def 计算参数(self, 当前时间: float):
        if not self._动画中:
            return 1.0, 255, False

        t = (当前时间 - self._动画开始) / max(0.001, self.总时长)
        if t >= 1.0:
            self._动画中 = False
            return 1.0, 255, True

        缩小占比 = self.缩小阶段 / max(0.001, self.总时长)

        if t < 缩小占比:
            k = t / max(0.001, 缩小占比)
            scale = 1.0 + (self.缩小到 - 1.0) * k
            alpha = self.透明起始
            return scale, alpha, False

        # 放大 + 淡出
        k = (t - 缩小占比) / max(0.001, (1.0 - 缩小占比))
        scale = self.缩小到 + (self.放大到 - self.缩小到) * k
        alpha = int(self.透明起始 + (self.透明结束 - self.透明起始) * k)
        alpha = max(0, min(255, alpha))
        return scale, alpha, False

    def 绘制按钮(
        self, 屏幕: pygame.Surface, 原图: pygame.Surface, 基准矩形: pygame.Rect
    ):
        """
        - 原图：按钮的“标准尺寸贴图”（通常等于基准矩形大小的图）
        - 基准矩形：按钮原本应该显示的位置/大小（用于居中放大）
        """
        现在 = time.time()
        scale, alpha, _结束 = self.计算参数(现在)

        if scale == 1.0 and alpha == 255:
            屏幕.blit(原图, 基准矩形.topleft)
            return

        ww = max(1, int(基准矩形.w * scale))
        hh = max(1, int(基准矩形.h * scale))
        x = 基准矩形.centerx - ww // 2
        y = 基准矩形.centery - hh // 2

        图 = pygame.transform.smoothscale(原图, (ww, hh)).convert_alpha()
        图.set_alpha(alpha)
        屏幕.blit(图, (x, y))


class 公用按钮音效:
    """
    全局按钮点击音效：加载一次，多处复用
    """

    def __init__(self, 音效路径: str):
        self._音效 = None
        路径 = str(音效路径 or "").strip()
        if 路径:
            后缀 = str(os.path.splitext(路径)[1] or "").strip().lower()
            if 后缀 == ".mp3":
                根路径, _ = os.path.splitext(路径)
                替代路径 = ""
                for 候选后缀 in (".wav", ".ogg"):
                    候选路径 = f"{根路径}{候选后缀}"
                    if os.path.isfile(候选路径):
                        替代路径 = 候选路径
                        break
                # 兼容性保护：不直接使用 mp3 作为短音效，避免部分环境硬崩。
                路径 = str(替代路径)
        if (not 路径) or (not os.path.isfile(路径)):
            return
        try:
            self._音效 = pygame.mixer.Sound(路径)
        except Exception:
            self._音效 = None

    def 播放(self):
        if not self._音效:
            return
        try:
            self._音效.play()
        except Exception:
            pass


class 图片按钮:
    def __init__(self, 名称: str, 图片路径: str):
        self.名称 = 名称
        self.图片路径 = 图片路径
        self.矩形 = pygame.Rect(0, 0, 160, 160)
        self.悬停 = False
        self.按下 = False
        self.图片 = None

    def 重新加载图片(self):
        self.图片 = 安全加载图片(self.图片路径, 透明=True)

    def 设置矩形(self, r: pygame.Rect):
        self.矩形 = r

    def 处理事件(self, 事件) -> bool:
        if 事件.type == pygame.MOUSEMOTION:
            self.悬停 = self.矩形.collidepoint(事件.pos)
        elif 事件.type == pygame.MOUSEBUTTONDOWN and 事件.button == 1:
            if self.矩形.collidepoint(事件.pos):
                self.按下 = True
        elif 事件.type == pygame.MOUSEBUTTONUP and 事件.button == 1:
            命中 = self.矩形.collidepoint(事件.pos)
            触发 = self.按下 and 命中
            self.按下 = False
            return 触发
        return False

    def 绘制(self, 屏幕: pygame.Surface, 字体: pygame.font.Font):
        r = self.矩形

        缩放系数 = 1.0
        if self.悬停:
            缩放系数 = 1.03
        if self.按下:
            缩放系数 = 0.98

        阴影 = pygame.Rect(r.x + 6, r.y + 10, r.w, r.h)
        pygame.draw.rect(屏幕, (0, 0, 0), 阴影, border_radius=18)

        if self.图片:
            if 缩放系数 != 1.0:
                nw = int(r.w * 缩放系数)
                nh = int(r.h * 缩放系数)
                画布 = contain缩放(self.图片, nw, nh)
                x = r.centerx - nw // 2
                y = r.centery - nh // 2
                屏幕.blit(画布, (x, y))
            else:
                画布 = contain缩放(self.图片, r.w, r.h)
                屏幕.blit(画布, r.topleft)
        else:
            底 = (40, 120, 220) if not self.悬停 else (55, 140, 245)
            if self.按下:
                底 = (28, 95, 180)
            面 = 画圆角面(r.w, r.h, 底, 圆角=18, alpha=245)
            屏幕.blit(面, r.topleft)
            pygame.draw.rect(屏幕, (255, 255, 255), r, width=4, border_radius=18)
            绘制文本(屏幕, self.名称, 字体, (255, 255, 255), r.center, "center")
