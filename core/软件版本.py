import json
import os

from core.常量与路径 import 取运行根目录


版本文件名 = "客户端版本.json"
默认版本号 = "v1.0.0"


def 获取版本文件路径(根目录: str | None = None) -> str:
    目标根目录 = str(根目录 or "").strip() or 取运行根目录()
    return os.path.join(os.path.abspath(目标根目录), "json", 版本文件名)


def 规范版本号(值: object, 默认值: str = "") -> str:
    文本 = str(值 or "").strip()
    if 文本:
        return 文本
    return str(默认值 or "").strip()


def 规范版本比较值(值: object) -> str:
    文本 = 规范版本号(值).replace(" ", "").lower()
    if 文本.startswith("v"):
        文本 = 文本[1:]
    return 文本


def 读取版本信息(根目录: str | None = None) -> dict:
    路径 = 获取版本文件路径(根目录)
    默认数据 = {"version": 默认版本号}

    try:
        if os.path.isfile(路径):
            with open(路径, "r", encoding="utf-8") as 文件:
                对象 = json.load(文件)
            if isinstance(对象, dict):
                结果 = dict(默认数据)
                结果.update(对象)
                return 结果
    except Exception:
        pass

    return dict(默认数据)


def 读取当前版本号(根目录: str | None = None, 默认值: str = 默认版本号) -> str:
    数据 = 读取版本信息(根目录)
    return 规范版本号(数据.get("version"), 默认值)


def 读取当前版本展示文本(
    根目录: str | None = None,
    软件名: str = "e舞成名重构版",
) -> str:
    版本号 = 读取当前版本号(根目录=根目录, 默认值=默认版本号)
    if not 版本号:
        return str(软件名 or "").strip()
    return f"{str(软件名 or '').strip()}{版本号}"
