import time
import pygame


class 公共黑屏过渡:
    """
    单段式黑屏过渡：
    - 当前场景丝滑渐黑
    - 黑到满值时触发切场景
    - 切场景后额外保持纯黑一小段时间
    - 然后自动结束黑屏

    这样既能掩盖切场景卡顿，又不会永远黑屏。
    """

    def __init__(
        self,
        渐入秒: float = 0.12,
        渐出秒: float | None = None,
        切换后保持黑屏秒: float = 0.06,
    ):
        """
        渐出秒 参数仅为兼容旧调用而保留，当前版本不会使用。
        """
        self.渐入秒 = max(0.001, float(渐入秒))
        self.渐出秒 = 0.0 if 渐出秒 is None else float(渐出秒)
        self.切换后保持黑屏秒 = max(0.0, float(切换后保持黑屏秒))

        self._是否进行中 = False
        self._阶段 = "无"  # 无 / 渐入 / 切换后保持黑屏
        self._开始时间 = 0.0

        self._待切换目标场景名 = None
        self._是否已触发切换回调 = False

        self._黑层缓存 = None
        self._黑层缓存尺寸 = (0, 0)

    def _取当前时间(self) -> float:
        return time.perf_counter()

    def _限制范围(self, 数值: float, 最小值: float, 最大值: float) -> float:
        if 数值 < 最小值:
            return 最小值
        if 数值 > 最大值:
            return 最大值
        return 数值

    def _缓入缓出(self, 进度: float) -> float:
        进度 = self._限制范围(进度, 0.0, 1.0)
        return 进度 * 进度 * 进度 * (进度 * (进度 * 6.0 - 15.0) + 10.0)

    def _确保黑层缓存(self, 屏幕: pygame.Surface):
        宽, 高 = 屏幕.get_size()
        if (
            self._黑层缓存 is None
            or self._黑层缓存尺寸[0] != 宽
            or self._黑层缓存尺寸[1] != 高
        ):
            self._黑层缓存 = pygame.Surface((宽, 高)).convert()
            self._黑层缓存.fill((0, 0, 0))
            self._黑层缓存尺寸 = (宽, 高)

    def 开始(self, 目标场景名: str):
        self._是否进行中 = True
        self._阶段 = "渐入"
        self._开始时间 = self._取当前时间()
        self._待切换目标场景名 = 目标场景名
        self._是否已触发切换回调 = False

    def 是否进行中(self) -> bool:
        return self._是否进行中

    def 获取目标场景名(self):
        return self._待切换目标场景名

    def 结束黑屏(self):
        self._是否进行中 = False
        self._阶段 = "无"
        self._开始时间 = 0.0
        self._待切换目标场景名 = None
        self._是否已触发切换回调 = False

    def 更新(self, 触发切换回调):
        if not self._是否进行中:
            return

        当前时间 = self._取当前时间()
        已过秒数 = 当前时间 - self._开始时间

        if self._阶段 == "渐入":
            if 已过秒数 >= self.渐入秒:
                if not self._是否已触发切换回调:
                    self._是否已触发切换回调 = True
                    try:
                        触发切换回调()
                    except Exception:
                        pass

                self._阶段 = "切换后保持黑屏"
                self._开始时间 = 当前时间
                return

        if self._阶段 == "切换后保持黑屏":
            if 已过秒数 >= self.切换后保持黑屏秒:
                self.结束黑屏()

    def _计算透明度(self) -> int:
        if not self._是否进行中:
            return 0

        当前时间 = self._取当前时间()

        if self._阶段 == "渐入":
            已过秒数 = 当前时间 - self._开始时间
            进度 = 已过秒数 / self.渐入秒
            进度 = self._缓入缓出(进度)
            return int(255 * 进度)

        if self._阶段 == "切换后保持黑屏":
            return 255

        return 0

    def 绘制(self, 屏幕: pygame.Surface):
        if not self._是否进行中:
            return

        透明度 = self._计算透明度()
        if 透明度 <= 0:
            return

        self._确保黑层缓存(屏幕)

        if 透明度 >= 255:
            屏幕.blit(self._黑层缓存, (0, 0))
            return

        self._黑层缓存.set_alpha(透明度)
        屏幕.blit(self._黑层缓存, (0, 0))
        self._黑层缓存.set_alpha(None)




class 公共丝滑入场:
    """
    单段式丝滑入场：
    - 开始时默认全黑
    - 然后按缓动曲线从黑到透明
    - 不负责场景切换，只负责新场景揭幕

    阶段：
    无 -> 保持黑屏 -> 渐出黑层 -> 无
    """

    def __init__(
        self,
        保持黑屏秒: float = 0.03,
        渐出秒: float = 0.12,
    ):
        self.保持黑屏秒 = max(0.0, float(保持黑屏秒))
        self.渐出秒 = max(0.001, float(渐出秒))

        self._是否进行中 = False
        self._阶段 = "无"  # 无 / 保持黑屏 / 渐出黑层
        self._开始时间 = 0.0

        self._黑层缓存 = None
        self._黑层缓存尺寸 = (0, 0)

    def _取当前时间(self) -> float:
        return time.perf_counter()

    def _限制范围(self, 数值: float, 最小值: float, 最大值: float) -> float:
        if 数值 < 最小值:
            return 最小值
        if 数值 > 最大值:
            return 最大值
        return 数值

    def _缓入缓出(self, 进度: float) -> float:
        进度 = self._限制范围(进度, 0.0, 1.0)
        return 进度 * 进度 * 进度 * (进度 * (进度 * 6.0 - 15.0) + 10.0)

    def _确保黑层缓存(self, 屏幕: pygame.Surface):
        宽, 高 = 屏幕.get_size()
        if (
            self._黑层缓存 is None
            or self._黑层缓存尺寸[0] != 宽
            or self._黑层缓存尺寸[1] != 高
        ):
            self._黑层缓存 = pygame.Surface((宽, 高)).convert()
            self._黑层缓存.fill((0, 0, 0))
            self._黑层缓存尺寸 = (宽, 高)

    def 开始(self):
        self._是否进行中 = True
        self._阶段 = "保持黑屏"
        self._开始时间 = self._取当前时间()

    def 是否进行中(self) -> bool:
        return self._是否进行中

    def 结束(self):
        self._是否进行中 = False
        self._阶段 = "无"
        self._开始时间 = 0.0

    def 更新(self):
        if not self._是否进行中:
            return

        当前时间 = self._取当前时间()
        已过秒数 = 当前时间 - self._开始时间

        if self._阶段 == "保持黑屏":
            if 已过秒数 >= self.保持黑屏秒:
                self._阶段 = "渐出黑层"
                self._开始时间 = 当前时间
                return

        if self._阶段 == "渐出黑层":
            if 已过秒数 >= self.渐出秒:
                self.结束()

    def _计算透明度(self) -> int:
        if not self._是否进行中:
            return 0

        当前时间 = self._取当前时间()

        if self._阶段 == "保持黑屏":
            return 255

        if self._阶段 == "渐出黑层":
            已过秒数 = 当前时间 - self._开始时间
            进度 = 已过秒数 / self.渐出秒
            进度 = self._缓入缓出(进度)
            return int(255 * (1.0 - 进度))

        return 0

    def 绘制(self, 屏幕: pygame.Surface):
        if not self._是否进行中:
            return

        透明度 = self._计算透明度()
        if 透明度 <= 0:
            return

        self._确保黑层缓存(屏幕)

        if 透明度 >= 255:
            屏幕.blit(self._黑层缓存, (0, 0))
            return

        self._黑层缓存.set_alpha(透明度)
        屏幕.blit(self._黑层缓存, (0, 0))
        self._黑层缓存.set_alpha(None)



class 公用放大过渡器:
    def __init__(
        self,
        总时长毫秒: int = 520,
        缩小阶段占比: float = 0.25,
        缩小到: float = 0.92,
        透明起始: int = 255,
        透明结束: int = 0,
        # ✅ 放大到全屏时加一点余量，避免边缘露黑（cover更稳）
        覆盖余量: float = 1.04,
    ):
        self.总时长毫秒 = int(总时长毫秒)
        self.缩小阶段占比 = float(缩小阶段占比)
        self.缩小到 = float(缩小到)
        self.透明起始 = int(透明起始)
        self.透明结束 = int(透明结束)
        self.覆盖余量 = float(覆盖余量)

        self._开始毫秒 = 0
        self._进行中 = False
        self._起始图: pygame.Surface | None = None
        self._起始rect = pygame.Rect(0, 0, 1, 1)

        # 动态计算出来的“放大到倍数”
        self._放大到 = 4.0

    def 开始(self, 起始图: pygame.Surface, 起始rect: pygame.Rect):
        self._起始图 = 起始图
        self._起始rect = 起始rect.copy()
        self._开始毫秒 = pygame.time.get_ticks()
        self._进行中 = True
        self._放大到 = 4.0  # 先给默认，首次绘制时会按屏幕尺寸重算

    def 是否进行中(self) -> bool:
        return bool(self._进行中)

    def 是否完成(self) -> bool:
        if not self._进行中:
            return False
        return (pygame.time.get_ticks() - self._开始毫秒) >= max(1, self.总时长毫秒)

    def _计算覆盖全屏倍数(self, 屏幕: pygame.Surface) -> float:
        sw, sh = 屏幕.get_size()
        w0 = max(1, int(self._起始rect.w))
        h0 = max(1, int(self._起始rect.h))

        # ✅ cover：至少有一边铺满，另一边允许超出
        倍数 = max(sw / w0, sh / h0) * max(1.0, float(self.覆盖余量))
        # 保底：别太小
        return max(1.0, float(倍数))

    def 更新并绘制(self, 屏幕: pygame.Surface):
        if (not self._进行中) or (self._起始图 is None):
            return

        # ✅ 动态算“放大到全屏”的倍数（屏幕改尺寸也能跟着变）
        self._放大到 = self._计算覆盖全屏倍数(屏幕)

        现在 = pygame.time.get_ticks()
        t = (现在 - self._开始毫秒) / max(1, self.总时长毫秒)
        t = max(0.0, min(1.0, float(t)))

        # 参考按钮点击特效：两段
        缩小占比 = max(0.05, min(0.95, float(self.缩小阶段占比)))

        if t < 缩小占比:
            k = t / max(0.0001, 缩小占比)
            scale = 1.0 + (self.缩小到 - 1.0) * k
            alpha = self.透明起始
        else:
            k = (t - 缩小占比) / max(0.0001, (1.0 - 缩小占比))
            scale = self.缩小到 + (self._放大到 - self.缩小到) * k
            alpha = int(self.透明起始 + (self.透明结束 - self.透明起始) * k)
            alpha = max(0, min(255, alpha))

        # ✅ 围绕起始rect中心缩放（按钮点击特效同款手感）
        ww = max(1, int(self._起始rect.w * scale))
        hh = max(1, int(self._起始rect.h * scale))
        x = int(self._起始rect.centerx - ww // 2)
        y = int(self._起始rect.centery - hh // 2)

        图2 = pygame.transform.smoothscale(self._起始图, (ww, hh)).convert_alpha()
        图2.set_alpha(alpha)

        屏幕.blit(图2, (x, y))

        if t >= 1.0:
            self._进行中 = False
