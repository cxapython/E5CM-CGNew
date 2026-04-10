import faulthandler
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import platform
import re
import sys
import threading
import time
from typing import Optional, Union


_初始化锁 = threading.Lock()
_已初始化 = False
_日志文件路径 = ""
_致命日志文件路径 = ""
_可读致命日志文件路径 = ""
_致命日志文件句柄 = None
_原始sys_excepthook = sys.excepthook
_原始threading_excepthook = getattr(threading, "excepthook", None)
_原始unraisablehook = getattr(sys, "unraisablehook", None)
_unicode转义匹配 = re.compile(r"\\u([0-9a-fA-F]{4})")


def _安全创建目录(目录: Path) -> None:
    try:
        目录.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _规范日志器(日志器或名称: Union[str, logging.Logger, None]) -> logging.Logger:
    if isinstance(日志器或名称, logging.Logger):
        return 日志器或名称
    名称 = str(日志器或名称 or "e5cm").strip() or "e5cm"
    return logging.getLogger(名称)


def _刷新所有日志处理器() -> None:
    根日志器 = logging.getLogger()
    for 处理器 in list(getattr(根日志器, "handlers", []) or []):
        try:
            处理器.flush()
        except Exception:
            continue


def _解码unicode转义文本(文本: str) -> str:
    文本值 = str(文本 or "")
    if "\\" not in 文本值:
        return 文本值

    def _替换函数(匹配):
        try:
            return chr(int(str(匹配.group(1) or "0"), 16))
        except Exception:
            return str(匹配.group(0) or "")

    try:
        return _unicode转义匹配.sub(_替换函数, 文本值)
    except Exception:
        return 文本值


def _刷新可读致命日志副本(致命文件路径: Path, 可读文件路径: Path) -> None:
    try:
        if not bool(致命文件路径.exists()):
            return
        原文 = 致命文件路径.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return
    try:
        可读文件路径.write_text(_解码unicode转义文本(原文), encoding="utf-8")
    except Exception:
        pass


def _sys未捕获异常钩子(exc_type, exc_value, exc_traceback):
    if exc_type is not None and issubclass(exc_type, KeyboardInterrupt):
        try:
            _原始sys_excepthook(exc_type, exc_value, exc_traceback)
            return
        except Exception:
            return
    日志器 = logging.getLogger("main.crash")
    try:
        日志器.critical(
            "未捕获异常（sys.excepthook）",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
    finally:
        _刷新所有日志处理器()


def _线程未捕获异常钩子(args):
    日志器 = logging.getLogger(f"thread.{getattr(args, 'thread', None) or 'unknown'}")
    try:
        日志器.critical(
            "线程未捕获异常（threading.excepthook）",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
    finally:
        _刷新所有日志处理器()
    if callable(_原始threading_excepthook):
        try:
            _原始threading_excepthook(args)
        except Exception:
            pass


def _不可抛出异常钩子(args):
    日志器 = logging.getLogger("main.unraisable")
    try:
        异常 = getattr(args, "exc_value", None)
        对象 = getattr(args, "object", None)
        日志器.error(
            "不可抛出异常（unraisablehook） object=%r",
            对象,
            exc_info=(
                getattr(args, "exc_type", type(异常)),
                异常,
                getattr(args, "exc_traceback", None),
            ),
        )
    finally:
        _刷新所有日志处理器()
    if callable(_原始unraisablehook):
        try:
            _原始unraisablehook(args)
        except Exception:
            pass


def _启用faulthandler(致命文件路径: Path):
    global _致命日志文件句柄
    try:
        _致命日志文件句柄 = open(
            str(致命文件路径),
            "a",
            encoding="utf-8",
            buffering=1,
        )
        faulthandler.enable(file=_致命日志文件句柄, all_threads=True)
    except Exception:
        _致命日志文件句柄 = None


def 初始化日志系统(运行根目录: Optional[str] = None, 控制台输出: bool = False) -> logging.Logger:
    global _已初始化, _日志文件路径, _致命日志文件路径, _可读致命日志文件路径
    with _初始化锁:
        if _已初始化:
            return logging.getLogger("main")

        根目录路径 = Path(str(运行根目录 or os.getcwd() or ".")).resolve()
        日志目录 = 根目录路径 / "state" / "logs"
        _安全创建目录(日志目录)
        日志文件 = 日志目录 / "runtime.log"
        致命文件 = 日志目录 / "fatal.log"
        可读致命文件 = 日志目录 / "fatal_readable.log"
        _日志文件路径 = str(日志文件)
        _致命日志文件路径 = str(致命文件)
        _可读致命日志文件路径 = str(可读致命文件)

        根日志器 = logging.getLogger()
        根日志器.setLevel(logging.INFO)
        for 处理器 in list(根日志器.handlers):
            try:
                根日志器.removeHandler(处理器)
            except Exception:
                continue

        文件处理器 = RotatingFileHandler(
            filename=str(日志文件),
            maxBytes=8 * 1024 * 1024,
            backupCount=4,
            encoding="utf-8",
        )
        格式器 = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        文件处理器.setFormatter(格式器)
        根日志器.addHandler(文件处理器)

        if bool(控制台输出):
            控制台处理器 = logging.StreamHandler(stream=sys.stdout)
            控制台处理器.setFormatter(格式器)
            根日志器.addHandler(控制台处理器)

        logging.captureWarnings(True)

        sys.excepthook = _sys未捕获异常钩子
        if hasattr(threading, "excepthook"):
            threading.excepthook = _线程未捕获异常钩子
        if hasattr(sys, "unraisablehook"):
            sys.unraisablehook = _不可抛出异常钩子

        _刷新可读致命日志副本(致命文件, 可读致命文件)
        _启用faulthandler(致命文件)

        主日志器 = logging.getLogger("main")
        主日志器.info("日志系统已初始化")
        主日志器.info(
            "运行信息 frozen=%s python=%s platform=%s cwd=%s pid=%s",
            bool(getattr(sys, "frozen", False)),
            str(sys.version).replace("\n", " "),
            platform.platform(),
            os.getcwd(),
            os.getpid(),
        )
        主日志器.info(
            "日志文件=%s 致命日志=%s 可读致命日志=%s",
            _日志文件路径,
            _致命日志文件路径,
            _可读致命日志文件路径,
        )
        _已初始化 = True
        return 主日志器


def 取日志器(名称: str = "main") -> logging.Logger:
    return logging.getLogger(str(名称 or "main").strip() or "main")


def 记录异常(
    日志器或名称: Union[str, logging.Logger, None],
    消息: str,
    异常: Optional[BaseException] = None,
) -> None:
    日志器 = _规范日志器(日志器或名称)
    消息文本 = str(消息 or "发生异常")
    if 异常 is None:
        日志器.exception(消息文本)
        return
    日志器.error(
        "%s | %s: %s",
        消息文本,
        type(异常).__name__,
        异常,
        exc_info=(type(异常), 异常, getattr(异常, "__traceback__", None)),
    )


def 记录信息(日志器或名称: Union[str, logging.Logger, None], 消息: str) -> None:
    _规范日志器(日志器或名称).info(str(消息 or ""))


def 记录警告(日志器或名称: Union[str, logging.Logger, None], 消息: str) -> None:
    _规范日志器(日志器或名称).warning(str(消息 or ""))


def 取日志文件路径() -> str:
    return str(_日志文件路径 or "")


def 取致命日志文件路径() -> str:
    return str(_致命日志文件路径 or "")


def 取可读致命日志文件路径() -> str:
    return str(_可读致命日志文件路径 or "")
