import os
import threading
import time
import weakref

import pygame

try:
    import av  # type: ignore

    _可用视频 = True
except Exception:
    av = None
    _可用视频 = False

try:
    from PIL import Image

    _可用图像库 = True
except Exception:
    Image = None
    _可用图像库 = False

try:
    import numpy as np  # type: ignore
except Exception:
    np = None


_视频解码线程数 = 1
_视频缓冲帧数 = 1


def _读取布尔环境变量(键名: str, 默认值: bool = False) -> bool:
    文本 = str(os.environ.get(str(键名), "") or "").strip().lower()
    if 文本 in ("1", "true", "yes", "on"):
        return True
    if 文本 in ("0", "false", "no", "off"):
        return False
    return bool(默认值)


def _读取整数环境变量(键名: str, 默认值: int, 最小值: int = 1, 最大值: int = 64) -> int:
    try:
        数值 = int(os.environ.get(str(键名), 默认值))
    except Exception:
        数值 = int(默认值)
    return int(max(int(最小值), min(int(最大值), int(数值))))


def _取PIL插值双线性():
    if Image is None:
        return None
    try:
        return Image.Resampling.BILINEAR  # Pillow >= 9
    except Exception:
        return getattr(Image, "BILINEAR", None)


def _解析帧率数值(候选值) -> float:
    if 候选值 is None:
        return 0.0
    try:
        值 = float(候选值)
        if 值 > 0:
            return float(值)
    except Exception:
        pass
    try:
        分子 = float(getattr(候选值, "numerator", 0) or 0)
        分母 = float(getattr(候选值, "denominator", 0) or 0)
        if 分子 > 0 and 分母 > 0:
            return float(分子 / 分母)
    except Exception:
        pass
    return 0.0


class _PyAV视频捕获:
    def __init__(self, 路径: str):
        self._路径 = os.path.abspath(str(路径 or "").strip())
        self._容器 = None
        self._视频流 = None
        self._帧迭代器 = None
        self._fps = 30.0
        self._打开()

    def _打开(self):
        if av is None:
            raise RuntimeError("pyav_unavailable")
        if not self._路径:
            raise RuntimeError("empty_path")

        容器 = av.open(self._路径, mode="r")
        视频流 = None
        for 流 in list(getattr(容器, "streams", []) or []):
            if str(getattr(流, "type", "") or "").strip().lower() == "video":
                视频流 = 流
                break
        if 视频流 is None:
            容器.close()
            raise RuntimeError("video_stream_not_found")

        try:
            视频流.thread_type = "AUTO"
        except Exception:
            pass
        try:
            线程数 = _读取整数环境变量(
                "E5CM_VIDEO_DECODE_THREADS",
                int(max(1, int(_视频解码线程数))),
                最小值=1,
                最大值=16,
            )
            if hasattr(视频流, "codec_context") and 视频流.codec_context is not None:
                视频流.codec_context.thread_count = int(线程数)
        except Exception:
            pass

        fps候选 = [
            getattr(视频流, "average_rate", None),
            getattr(视频流, "guessed_rate", None),
            getattr(视频流, "base_rate", None),
        ]
        fps = 0.0
        for 候选 in fps候选:
            fps = _解析帧率数值(候选)
            if fps > 1.0:
                break
        if fps <= 1.0:
            fps = 30.0
        fps = float(max(1.0, min(240.0, float(fps))))

        self._容器 = 容器
        self._视频流 = 视频流
        self._帧迭代器 = 容器.decode(video=视频流.index)
        self._fps = float(fps)

    def isOpened(self) -> bool:
        return self._容器 is not None and self._视频流 is not None and self._帧迭代器 is not None

    def get_fps(self) -> float:
        return float(self._fps if self._fps > 1.0 else 30.0)

    def read(self):
        if not self.isOpened():
            return False, None
        while True:
            try:
                帧 = next(self._帧迭代器)
            except StopIteration:
                return False, None
            except Exception:
                return False, None
            if 帧 is None:
                continue
            return True, 帧

    def grab(self) -> bool:
        ok, _ = self.read()
        return bool(ok)

    def reset(self) -> bool:
        try:
            self.release()
            self._打开()
            return True
        except Exception:
            return False

    def release(self):
        try:
            if self._容器 is not None:
                self._容器.close()
        except Exception:
            pass
        self._容器 = None
        self._视频流 = None
        self._帧迭代器 = None
        self._fps = 30.0


def 选择第一个视频(目录: str) -> str:
    try:
        if not 目录 or (not os.path.isdir(目录)):
            return ""
        目标路径 = os.path.join(目录, "003.mp4")
        if os.path.isfile(目标路径):
            return 目标路径
        return ""
    except Exception:
        return ""


def _打开视频捕获(路径: str):
    if (
        (not _可用视频)
        or av is None
        or (not _可用图像库)
        or (not 路径)
        or _读取布尔环境变量("E5CM_VIDEO_DISABLE_PYAV", False)
        or _读取布尔环境变量("E5CM_VIDEO_DISABLE_DECODER", False)
    ):
        return None, 30.0

    cap = None
    try:
        cap = _PyAV视频捕获(str(路径))
        if not bool(cap.isOpened()):
            raise RuntimeError("capture_not_opened")
        return cap, float(cap.get_fps())
    except Exception:
        try:
            if cap is not None:
                cap.release()
        except Exception:
            pass
        return None, 30.0


def _计算输出帧率(源fps: float, 最大输出帧率: float | None) -> float:
    输出fps = float(源fps if 源fps and 源fps > 1 else 30.0)
    if 最大输出帧率 is not None:
        try:
            输出fps = min(float(输出fps), float(最大输出帧率))
        except Exception:
            pass
    return max(1.0, float(输出fps))


def _规范输出尺寸(尺寸) -> tuple[int, int] | None:
    try:
        if 尺寸 is None:
            return None
        宽 = int(max(1, int(tuple(尺寸)[0])))
        高 = int(max(1, int(tuple(尺寸)[1])))
        return 宽, 高
    except Exception:
        return None


def _限制帧尺寸(frame, 最大输出尺寸):
    if (not _可用视频) or (not _可用图像库) or frame is None:
        return frame

    限制尺寸 = _规范输出尺寸(最大输出尺寸)
    if 限制尺寸 is None:
        return frame

    try:
        原宽, 原高 = tuple(getattr(frame, "size", (0, 0)) or (0, 0))
    except Exception:
        return frame

    最大宽, 最大高 = tuple(限制尺寸)
    if 原宽 <= 最大宽 and 原高 <= 最大高:
        return frame

    比例 = min(float(最大宽) / max(1.0, float(原宽)), float(最大高) / max(1.0, float(原高)))
    新宽 = max(1, int(round(float(原宽) * 比例)))
    新高 = max(1, int(round(float(原高) * 比例)))
    if (新宽, 新高) == (int(原宽), int(原高)):
        return frame
    try:
        插值 = _取PIL插值双线性()
        if 插值 is None:
            return frame
        return frame.resize((int(新宽), int(新高)), resample=插值)
    except Exception:
        return frame


def _限制目标尺寸(目标宽: int, 目标高: int, 最大输出尺寸):
    限制尺寸 = _规范输出尺寸(最大输出尺寸)
    if 限制尺寸 is None:
        return int(目标宽), int(目标高)
    最大宽, 最大高 = tuple(限制尺寸)
    目标宽 = int(max(1, int(目标宽)))
    目标高 = int(max(1, int(目标高)))
    if 目标宽 <= 最大宽 and 目标高 <= 最大高:
        return 目标宽, 目标高
    比例 = min(float(最大宽) / float(目标宽), float(最大高) / float(目标高))
    return (
        max(1, int(round(float(目标宽) * 比例))),
        max(1, int(round(float(目标高) * 比例))),
    )


def _原始帧转rgb数据(frame, 最大输出尺寸=None):
    if (not _可用视频) or (not _可用图像库) or frame is None:
        return None
    try:
        if (
            最大输出尺寸 is None
            and np is not None
            and hasattr(frame, "to_ndarray")
        ):
            try:
                数组 = frame.to_ndarray(format="rgb24")
            except Exception:
                数组 = None
            if 数组 is not None:
                try:
                    高, 宽 = tuple(int(v) for v in getattr(数组, "shape", (0, 0, 0))[:2])
                except Exception:
                    高, 宽 = 0, 0
                if 宽 > 0 and 高 > 0:
                    return {
                        "尺寸": (int(宽), int(高)),
                        "字节": 数组.tobytes(order="C"),
                    }
        if hasattr(frame, "to_image"):
            图像 = frame.to_image()
        elif isinstance(frame, Image.Image):
            图像 = frame
        else:
            return None
        if 图像 is None:
            return None
        if str(getattr(图像, "mode", "") or "").upper() != "RGB":
            图像 = 图像.convert("RGB")
        图像 = _限制帧尺寸(图像, 最大输出尺寸)
        宽, 高 = tuple(getattr(图像, "size", (0, 0)) or (0, 0))
        if 宽 <= 0 or 高 <= 0:
            return None
        return {
            "尺寸": (int(max(1, 宽)), int(max(1, 高))),
            "字节": 图像.tobytes(),
        }
    except Exception:
        return None


def _原始帧cover到窗口数据(frame, 目标宽: int, 目标高: int, 最大输出尺寸=None):
    if (not _可用视频) or (not _可用图像库) or frame is None:
        return None

    try:
        目标宽 = int(max(1, int(目标宽)))
        目标高 = int(max(1, int(目标高)))
        目标宽, 目标高 = _限制目标尺寸(目标宽, 目标高, 最大输出尺寸)
        if hasattr(frame, "to_image"):
            图像 = frame.to_image()
        elif isinstance(frame, Image.Image):
            图像 = frame
        else:
            return None
        if 图像 is None:
            return None
        if str(getattr(图像, "mode", "") or "").upper() != "RGB":
            图像 = 图像.convert("RGB")
        帧宽, 帧高 = tuple(getattr(图像, "size", (0, 0)) or (0, 0))
    except Exception:
        return None

    if 帧宽 <= 0 or 帧高 <= 0:
        return None

    比例 = max(目标宽 / max(1, 帧宽), 目标高 / max(1, 帧高))
    新宽 = max(1, int(round(float(帧宽) * 比例)))
    新高 = max(1, int(round(float(帧高) * 比例)))
    插值 = _取PIL插值双线性()
    if 插值 is None:
        return None

    try:
        if (新宽, 新高) == (帧宽, 帧高):
            缩放帧 = 图像
        else:
            缩放帧 = 图像.resize((int(新宽), int(新高)), resample=插值)

        起始x = max(0, (新宽 - 目标宽) // 2)
        起始y = max(0, (新高 - 目标高) // 2)
        裁切帧 = 缩放帧.crop(
            (
                int(起始x),
                int(起始y),
                int(起始x + int(目标宽)),
                int(起始y + int(目标高)),
            )
        )
        if tuple(getattr(裁切帧, "size", (0, 0)) or (0, 0)) != (int(目标宽), int(目标高)):
            裁切帧 = 裁切帧.resize((int(目标宽), int(目标高)), resample=插值)
        return {
            "尺寸": (int(目标宽), int(目标高)),
            "字节": 裁切帧.tobytes(),
        }
    except Exception:
        return None


def _从rgb字节创建独立Surface(字节数据, 尺寸) -> pygame.Surface | None:
    try:
        宽 = int(max(1, int(tuple(尺寸)[0])))
        高 = int(max(1, int(tuple(尺寸)[1])))
    except Exception:
        return None

    try:
        共享面 = pygame.image.frombuffer(字节数据, (宽, 高), "RGB")
    except Exception:
        return None

    try:
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            return 共享面.convert()
    except Exception:
        pass

    try:
        return 共享面.copy()
    except Exception:
        return 共享面


def _视频后台线程循环(owner_ref):
    cap = None
    已打开路径 = ""
    源fps = 30.0
    上次读帧时间 = 0.0
    空闲阈值秒 = 0.35
    禁用grab丢帧 = _读取布尔环境变量(
        "E5CM_VIDEO_DISABLE_GRAB",
        默认值=bool(os.name == "nt"),
    )

    def _重置捕获到起点() -> bool:
        nonlocal cap
        if cap is None:
            return False
        try:
            if hasattr(cap, "reset"):
                return bool(cap.reset())
        except Exception:
            return False
        return False

    def _释放capture():
        nonlocal cap, 已打开路径, 源fps, 上次读帧时间
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        cap = None
        已打开路径 = ""
        源fps = 30.0
        上次读帧时间 = 0.0

    while True:
        owner = owner_ref()
        if owner is None:
            _释放capture()
            return

        停止事件 = getattr(owner, "_后台停止事件", None)
        if 停止事件 is not None and 停止事件.is_set():
            _释放capture()
            return

        try:
            with owner._后台锁:
                视频路径 = (
                    os.path.abspath(str(owner.视频路径))
                    if str(owner.视频路径 or "").strip()
                    else ""
                )
                最大输出帧率 = owner._最大输出帧率
                最大输出尺寸 = getattr(owner, "_最大输出尺寸", None)
                请求模式 = str(getattr(owner, "_后台请求模式", "raw") or "raw")
                请求覆盖尺寸 = tuple(
                    getattr(owner, "_后台请求覆盖尺寸", (0, 0)) or (0, 0)
                )
                请求重置 = bool(getattr(owner, "_后台请求重置", False))
                最后请求秒 = float(getattr(owner, "_后台最后请求秒", 0.0) or 0.0)
        except Exception:
            if 停止事件 is not None and 停止事件.wait(0.03):
                break
            continue

        try:
            当前单调秒 = float(time.perf_counter())
        except Exception:
            当前单调秒 = 0.0
        if 最后请求秒 <= 0.0 or (
            当前单调秒 > 0.0 and (当前单调秒 - 最后请求秒) > float(空闲阈值秒)
        ):
            try:
                with owner._后台锁:
                    owner._后台准备中 = False
            except Exception:
                pass
            if 停止事件 is not None and 停止事件.wait(0.05):
                break
            continue

        if 视频路径 != 已打开路径 or cap is None or (
            hasattr(cap, "isOpened") and (not cap.isOpened())
        ):
            _释放capture()
            if not 视频路径:
                try:
                    with owner._后台锁:
                        owner._后台准备中 = False
                        owner._后台到达结尾 = False
                        owner._后台打开路径 = ""
                        owner._后台请求重置 = False
                except Exception:
                    pass
                if 停止事件 is not None and 停止事件.wait(0.03):
                    break
                continue

            try:
                with owner._后台锁:
                    owner._后台准备中 = True
                    owner._后台到达结尾 = False
                    owner._后台打开路径 = ""
                    owner._后台请求重置 = False
            except Exception:
                pass

            cap, 源fps = _打开视频捕获(视频路径)
            上次读帧时间 = 0.0
            if cap is None:
                try:
                    with owner._后台锁:
                        owner._后台准备中 = False
                        owner._后台打开路径 = ""
                except Exception:
                    pass
                if 停止事件 is not None and 停止事件.wait(0.12):
                    break
                continue
            已打开路径 = 视频路径
            try:
                with owner._后台锁:
                    owner._后台准备中 = False
                    owner._后台打开路径 = str(已打开路径)
            except Exception:
                pass

        if cap is None:
            if 停止事件 is not None and 停止事件.wait(0.03):
                break
            continue

        if 请求重置:
            if not bool(_重置捕获到起点()):
                _释放capture()
                if 停止事件 is not None and 停止事件.wait(0.03):
                    break
                continue
            上次读帧时间 = 0.0
            try:
                with owner._后台锁:
                    owner._后台请求重置 = False
                    owner._后台到达结尾 = False
            except Exception:
                pass

        输出fps = _计算输出帧率(float(源fps), 最大输出帧率)
        间隔 = 1.0 / float(max(1.0, 输出fps))
        现在 = time.time()
        if 上次读帧时间 and (现在 - 上次读帧时间) < 间隔:
            等待秒 = max(0.001, float(间隔 - (现在 - 上次读帧时间)))
            if 停止事件 is not None and 停止事件.wait(min(0.02, 等待秒)):
                break
            continue

        已过秒 = max(间隔, float(现在 - 上次读帧时间)) if 上次读帧时间 else 间隔
        目标推进帧数 = max(1, int(round(float(已过秒) * float(源fps))))
        上次读帧时间 = 现在

        while 目标推进帧数 > 1:
            丢帧成功 = False
            if not bool(禁用grab丢帧):
                try:
                    丢帧成功 = bool(cap.grab())
                except Exception:
                    丢帧成功 = False
            if not bool(丢帧成功):
                try:
                    丢帧成功, _ = cap.read()
                    丢帧成功 = bool(丢帧成功)
                except Exception:
                    丢帧成功 = False
            if not bool(丢帧成功):
                break
            目标推进帧数 -= 1

        ok, frame = (False, None)
        try:
            ok, frame = cap.read()
        except Exception:
            ok, frame = False, None

        已到结尾 = False
        if (not ok) or frame is None:
            if bool(getattr(owner, "循环播放", True)):
                if bool(_重置捕获到起点()):
                    try:
                        ok, frame = cap.read()
                    except Exception:
                        ok, frame = False, None
                else:
                    ok, frame = False, None
            else:
                已到结尾 = True

        if (not ok) or frame is None:
            try:
                with owner._后台锁:
                    owner._后台准备中 = False
                    owner._后台到达结尾 = bool(已到结尾)
            except Exception:
                pass
            if 停止事件 is not None and 停止事件.wait(0.03 if 已到结尾 else 0.01):
                break
            continue

        原始数据 = _原始帧转rgb数据(frame, 最大输出尺寸=最大输出尺寸)
        if 原始数据 is None:
            if 停止事件 is not None and 停止事件.wait(0.01):
                break
            continue

        覆盖数据 = None
        if 请求模式 == "cover" and len(请求覆盖尺寸) >= 2:
            try:
                目标宽 = int(max(1, int(请求覆盖尺寸[0])))
                目标高 = int(max(1, int(请求覆盖尺寸[1])))
            except Exception:
                目标宽, 目标高 = 0, 0
            if 目标宽 > 0 and 目标高 > 0:
                覆盖数据 = _原始帧cover到窗口数据(
                    frame,
                    目标宽,
                    目标高,
                    最大输出尺寸=最大输出尺寸,
                )

        owner = owner_ref()
        if owner is None:
            _释放capture()
            return

        try:
            当前路径 = (
                os.path.abspath(str(owner.视频路径))
                if str(owner.视频路径 or "").strip()
                else ""
            )
        except Exception:
            当前路径 = ""
        if 当前路径 != 已打开路径:
            continue

        try:
            with owner._后台锁:
                owner._帧版本 = int(getattr(owner, "_帧版本", 0) or 0) + 1
                帧版本 = int(owner._帧版本)
                owner._上一帧数组 = None
                owner._后台原始帧字节 = 原始数据.get("字节")
                owner._后台原始帧尺寸 = tuple(原始数据.get("尺寸", (0, 0)) or (0, 0))
                owner._后台原始帧版本 = 帧版本
                owner._后台准备中 = False
                owner._后台到达结尾 = False
                if 请求模式 == "cover" and isinstance(覆盖数据, dict):
                    owner._后台覆盖帧字节 = 覆盖数据.get("字节")
                    owner._后台覆盖帧尺寸 = tuple(
                        覆盖数据.get("尺寸", (0, 0)) or (0, 0)
                    )
                    owner._后台覆盖帧版本 = 帧版本
                elif 请求模式 != "cover":
                    owner._后台覆盖帧字节 = None
                    owner._后台覆盖帧尺寸 = (0, 0)
                    owner._后台覆盖帧版本 = -1
        except Exception:
            pass


class 全局视频循环播放器:
    def __init__(
        self,
        视频路径: str,
        循环播放: bool = True,
        最大输出帧率: float | None = None,
        最大输出尺寸: tuple[int, int] | None = None,
    ):
        self.视频路径 = 视频路径
        self.循环播放 = bool(循环播放)
        self._cap = None
        self._fps = 30.0
        self._最大输出帧率 = (
            float(最大输出帧率) if 最大输出帧率 and 最大输出帧率 > 0 else None
        )
        self._最大输出尺寸 = _规范输出尺寸(最大输出尺寸)
        self._上一帧数组 = None
        self._上一帧面: pygame.Surface | None = None
        self._上一帧面版本 = -1
        self._上一帧面字节引用 = None
        self._上次读帧时间 = 0.0
        self._帧版本 = 0
        self._覆盖缓存尺寸 = (0, 0)
        self._覆盖缓存版本 = -1
        self._覆盖缓存面: pygame.Surface | None = None
        self._覆盖缓存字节引用 = None

        self._后台锁 = threading.Lock()
        self._后台停止事件 = threading.Event()
        self._后台线程: threading.Thread | None = None
        self._后台请求模式 = "raw"
        self._后台请求覆盖尺寸 = (0, 0)
        self._后台请求重置 = False
        self._后台最后请求秒 = 0.0
        self._后台准备中 = False
        self._后台打开路径 = ""
        self._后台到达结尾 = False
        self._后台原始帧字节 = None
        self._后台原始帧尺寸 = (0, 0)
        self._后台原始帧版本 = -1
        self._后台覆盖帧字节 = None
        self._后台覆盖帧尺寸 = (0, 0)
        self._后台覆盖帧版本 = -1

    def _重置覆盖缓存(self):
        self._覆盖缓存尺寸 = (0, 0)
        self._覆盖缓存版本 = -1
        self._覆盖缓存面 = None
        self._覆盖缓存字节引用 = None

    def _重置显示缓存(self):
        self._上一帧数组 = None
        self._上一帧面 = None
        self._上一帧面版本 = -1
        self._上一帧面字节引用 = None
        self._重置覆盖缓存()

    def _清空后台缓存(self):
        try:
            with self._后台锁:
                self._后台原始帧字节 = None
                self._后台原始帧尺寸 = (0, 0)
                self._后台原始帧版本 = -1
                self._后台覆盖帧字节 = None
                self._后台覆盖帧尺寸 = (0, 0)
                self._后台覆盖帧版本 = -1
                self._后台打开路径 = ""
                self._后台到达结尾 = False
                self._后台准备中 = False
                self._后台请求模式 = "raw"
                self._后台请求覆盖尺寸 = (0, 0)
                self._后台请求重置 = False
                self._后台最后请求秒 = 0.0
        except Exception:
            pass

    @staticmethod
    def _cover缩放到窗口(
        图片: pygame.Surface, 目标宽: int, 目标高: int
    ) -> pygame.Surface:
        ow, oh = 图片.get_size()
        if ow <= 0 or oh <= 0:
            return pygame.Surface((目标宽, 目标高)).convert()

        比例 = max(目标宽 / max(1, ow), 目标高 / max(1, oh))
        nw = max(1, int(round(ow * 比例)))
        nh = max(1, int(round(oh * 比例)))

        if (nw, nh) == (ow, oh):
            缩放 = 图片
        else:
            缩放 = pygame.transform.scale(图片, (nw, nh)).convert()

        if (nw, nh) == (目标宽, 目标高):
            return 缩放

        x = max(0, (nw - 目标宽) // 2)
        y = max(0, (nh - 目标高) // 2)
        out = pygame.Surface((目标宽, 目标高)).convert()
        out.blit(缩放, (0, 0), area=pygame.Rect(x, y, 目标宽, 目标高))
        return out

    def _确保后台线程(self):
        if not _可用视频:
            return
        线程 = getattr(self, "_后台线程", None)
        if isinstance(线程, threading.Thread) and 线程.is_alive():
            return
        try:
            self._后台停止事件.clear()
        except Exception:
            self._后台停止事件 = threading.Event()
        self._后台线程 = threading.Thread(
            target=_视频后台线程循环,
            args=(weakref.ref(self),),
            name="e5cm_video_decode",
            daemon=True,
        )
        self._后台线程.start()

    def _更新后台请求(
        self,
        模式: str = "raw",
        覆盖尺寸: tuple[int, int] = (0, 0),
    ):
        try:
            with self._后台锁:
                self._后台请求模式 = str(模式 or "raw")
                if len(tuple(覆盖尺寸 or (0, 0))) >= 2:
                    宽 = int(max(0, int(tuple(覆盖尺寸 or (0, 0))[0])))
                    高 = int(max(0, int(tuple(覆盖尺寸 or (0, 0))[1])))
                    self._后台请求覆盖尺寸 = (宽, 高)
                else:
                    self._后台请求覆盖尺寸 = (0, 0)
        except Exception:
            pass

    def 设置视频(self, 新路径: str, 是否重置进度: bool = True):
        新路径 = (新路径 or "").strip()
        if not 新路径:
            return
        新路径 = os.path.abspath(新路径)
        旧路径 = os.path.abspath(self.视频路径) if self.视频路径 else ""
        if 新路径 != 旧路径:
            self.视频路径 = 新路径
            self._重置显示缓存()
            self._清空后台缓存()
        self.打开(是否重置进度=bool(是否重置进度 or 新路径 != 旧路径))

    def 打开(self, 是否重置进度: bool = True):
        if not _可用视频 or not self.视频路径:
            return

        try:
            with self._后台锁:
                self._后台请求重置 = bool(是否重置进度)
                self._后台准备中 = False
                self._后台到达结尾 = False
        except Exception:
            pass

    def 关闭(self):
        try:
            self._后台停止事件.set()
        except Exception:
            pass

        线程 = getattr(self, "_后台线程", None)
        if isinstance(线程, threading.Thread) and 线程.is_alive():
            try:
                线程.join(timeout=0.12)
            except Exception:
                pass
        self._后台线程 = None
        self._后台停止事件 = threading.Event()

        self._cap = None
        self._fps = 30.0
        self._上次读帧时间 = 0.0
        self._帧版本 = 0
        self._重置显示缓存()
        self._清空后台缓存()

    def 正在准备(self) -> bool:
        try:
            with self._后台锁:
                return bool(getattr(self, "_后台准备中", False))
        except Exception:
            return False

    def 已到结尾(self) -> bool:
        if bool(self.循环播放):
            return False
        try:
            with self._后台锁:
                return bool(getattr(self, "_后台到达结尾", False))
        except Exception:
            return False

    def _取后台原始帧数据(self):
        try:
            with self._后台锁:
                版本 = int(getattr(self, "_后台原始帧版本", -1) or -1)
                尺寸 = tuple(getattr(self, "_后台原始帧尺寸", (0, 0)) or (0, 0))
                字节 = getattr(self, "_后台原始帧字节", None)
        except Exception:
            return None
        if 版本 < 0 or len(尺寸) < 2 or 尺寸[0] <= 0 or 尺寸[1] <= 0 or 字节 is None:
            return None
        return 版本, 尺寸, 字节

    def _取后台覆盖帧数据(self, 目标宽: int, 目标高: int):
        有效尺寸 = _限制目标尺寸(目标宽, 目标高, self._最大输出尺寸)
        try:
            with self._后台锁:
                版本 = int(getattr(self, "_后台覆盖帧版本", -1) or -1)
                尺寸 = tuple(getattr(self, "_后台覆盖帧尺寸", (0, 0)) or (0, 0))
                字节 = getattr(self, "_后台覆盖帧字节", None)
        except Exception:
            return None
        if (
            版本 < 0
            or len(尺寸) < 2
            or 字节 is None
            or tuple(尺寸) != tuple(有效尺寸)
        ):
            return None
        return 版本, 尺寸, 字节

    def 读取帧(self) -> pygame.Surface | None:
        try:
            with self._后台锁:
                self._后台最后请求秒 = float(time.perf_counter())
                self._后台准备中 = True
        except Exception:
            pass
        self._确保后台线程()
        self._更新后台请求("raw", (0, 0))

        数据 = self._取后台原始帧数据()
        if 数据 is None:
            return None if self.已到结尾() else self._上一帧面

        版本, 尺寸, 字节 = 数据
        if (
            self._上一帧面 is not None
            and int(self._上一帧面版本) == int(版本)
            and self._上一帧面.get_size() == tuple(尺寸)
        ):
            return self._上一帧面

        try:
            面 = _从rgb字节创建独立Surface(字节, tuple(尺寸))
            if 面 is None:
                raise RuntimeError("surface_create_failed")
            self._上一帧面 = 面
            self._上一帧面版本 = int(版本)
            self._上一帧面字节引用 = 字节
            return 面
        except Exception:
            return self._上一帧面

    def 读取覆盖帧(self, 目标宽: int, 目标高: int) -> pygame.Surface | None:
        目标宽 = max(1, int(目标宽))
        目标高 = max(1, int(目标高))
        有效宽, 有效高 = _限制目标尺寸(目标宽, 目标高, self._最大输出尺寸)

        try:
            with self._后台锁:
                self._后台最后请求秒 = float(time.perf_counter())
                self._后台准备中 = True
        except Exception:
            pass
        self._确保后台线程()
        self._更新后台请求("cover", (目标宽, 目标高))

        数据 = self._取后台覆盖帧数据(目标宽, 目标高)
        if 数据 is None:
            if self._覆盖缓存尺寸 == (int(有效宽), int(有效高)):
                return None if self.已到结尾() else self._覆盖缓存面
            return None

        版本, 尺寸, 字节 = 数据
        if (
            self._覆盖缓存面 is not None
            and self._覆盖缓存尺寸 == tuple(尺寸)
            and self._覆盖缓存版本 == int(版本)
        ):
            return self._覆盖缓存面

        try:
            覆盖面 = _从rgb字节创建独立Surface(字节, tuple(尺寸))
            if 覆盖面 is None:
                raise RuntimeError("surface_create_failed")
            self._覆盖缓存尺寸 = tuple(尺寸)
            self._覆盖缓存版本 = int(版本)
            self._覆盖缓存面 = 覆盖面
            self._覆盖缓存字节引用 = 字节
            return 覆盖面
        except Exception:
            return self._覆盖缓存面

    def __del__(self):
        # 避免在 GC 析构阶段执行重清理逻辑（join/release/surface 释放等），
        # 仅发送停止信号，把实际清理留给显式调用 关闭()。
        try:
            停止事件 = getattr(self, "_后台停止事件", None)
            if 停止事件 is not None:
                停止事件.set()
        except Exception:
            pass


class 全局视频顺序循环播放器:
    """
    目录播放：
    - 按文件名排序顺序播放
    - 播放到最后一个后回到第一个
    """

    def __init__(
        self,
        视频目录: str,
        最大输出帧率: float | None = None,
        最大输出尺寸: tuple[int, int] | None = None,
    ):
        self.视频目录 = str(视频目录 or "")
        self._最大输出帧率 = (
            float(最大输出帧率) if 最大输出帧率 and 最大输出帧率 > 0 else None
        )
        self._最大输出尺寸 = _规范输出尺寸(最大输出尺寸)
        self._文件列表: list[str] = []
        self._当前索引: int = 0
        self._当前播放器: 全局视频循环播放器 | None = None
        self._上一帧面: pygame.Surface | None = None

    @staticmethod
    def _收集视频文件(目录: str) -> list[str]:
        try:
            if not 目录 or (not os.path.isdir(目录)):
                return []
            候选后缀 = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ogv")
            文件列表: list[str] = []
            for 名称 in os.listdir(目录):
                路径 = os.path.join(目录, 名称)
                if (not os.path.isfile(路径)) or (
                    not str(名称).lower().endswith(候选后缀)
                ):
                    continue
                文件列表.append(路径)
            文件列表.sort(key=lambda p: os.path.basename(p).lower())
            return 文件列表
        except Exception:
            return []

    def 刷新列表(self):
        self._文件列表 = self._收集视频文件(self.视频目录)
        if self._当前索引 >= len(self._文件列表):
            self._当前索引 = 0

    def 打开(self, 是否重置进度: bool = True):
        self.刷新列表()
        if not self._文件列表:
            self.关闭()
            return
        if self._当前播放器 is None:
            self._当前索引 = 0 if 是否重置进度 else int(max(0, self._当前索引))
            当前路径 = self._文件列表[self._当前索引]
            self._当前播放器 = 全局视频循环播放器(
                当前路径,
                循环播放=False,
                最大输出帧率=self._最大输出帧率,
                最大输出尺寸=self._最大输出尺寸,
            )
            self._当前播放器.打开(是否重置进度=True)
            return
        if 是否重置进度:
            self._当前索引 = 0
            当前路径 = self._文件列表[self._当前索引]
            self._当前播放器.设置视频(当前路径, 是否重置进度=True)

    def 设置目录(self, 新目录: str, 是否重置进度: bool = True):
        新目录 = str(新目录 or "").strip()
        if not 新目录:
            return
        if os.path.abspath(新目录) == os.path.abspath(self.视频目录):
            if 是否重置进度:
                self.打开(是否重置进度=True)
            return
        self.视频目录 = 新目录
        self._当前索引 = 0
        self.关闭()
        self.打开(是否重置进度=True)

    def 关闭(self):
        if self._当前播放器 is not None:
            try:
                self._当前播放器.关闭()
            except Exception:
                pass
        self._当前播放器 = None

    def _切到下一个视频(self):
        if not self._文件列表:
            self._当前播放器 = None
            return
        self._当前索引 = (int(self._当前索引) + 1) % len(self._文件列表)
        当前路径 = self._文件列表[self._当前索引]
        if self._当前播放器 is None:
            self._当前播放器 = 全局视频循环播放器(
                当前路径,
                循环播放=False,
                最大输出帧率=self._最大输出帧率,
                最大输出尺寸=self._最大输出尺寸,
            )
            self._当前播放器.打开(是否重置进度=True)
        else:
            self._当前播放器.设置视频(当前路径, 是否重置进度=True)

    def 正在准备(self) -> bool:
        播放器 = getattr(self, "_当前播放器", None)
        if 播放器 is None:
            return False
        try:
            return bool(播放器.正在准备())
        except Exception:
            return False

    def 读取帧(self) -> pygame.Surface | None:
        if self._当前播放器 is None:
            self.打开(是否重置进度=False)
            if self._当前播放器 is None:
                return self._上一帧面

        尝试次数 = max(1, len(self._文件列表) if self._文件列表 else 1)
        for _ in range(尝试次数):
            if self._当前播放器 is None:
                break

            当前播放器 = self._当前播放器
            帧 = 当前播放器.读取帧()
            已到结尾 = bool(getattr(当前播放器, "已到结尾", lambda: False)())
            if 已到结尾:
                self._切到下一个视频()
                continue
            if isinstance(帧, pygame.Surface):
                self._上一帧面 = 帧
                return 帧
            if bool(getattr(当前播放器, "正在准备", lambda: False)()):
                return self._上一帧面
            self._切到下一个视频()

        return self._上一帧面

    def 读取覆盖帧(self, 目标宽: int, 目标高: int) -> pygame.Surface | None:
        if self._当前播放器 is None:
            self.打开(是否重置进度=False)
            if self._当前播放器 is None:
                return self._上一帧面

        尝试次数 = max(1, len(self._文件列表) if self._文件列表 else 1)
        for _ in range(尝试次数):
            if self._当前播放器 is None:
                break

            当前播放器 = self._当前播放器
            帧 = 当前播放器.读取覆盖帧(目标宽, 目标高)
            已到结尾 = bool(getattr(当前播放器, "已到结尾", lambda: False)())
            if 已到结尾:
                self._切到下一个视频()
                continue
            if isinstance(帧, pygame.Surface):
                self._上一帧面 = 帧
                return 帧
            if bool(getattr(当前播放器, "正在准备", lambda: False)()):
                return self._上一帧面
            self._切到下一个视频()

        return self._上一帧面
