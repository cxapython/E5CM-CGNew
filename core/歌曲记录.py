import json
import os
from typing import Dict


def _索引路径(项目根: str) -> str:
    return os.path.join(str(项目根 or os.getcwd()), "songs", "歌曲记录索引.json")


def 读取歌曲记录索引(项目根: str) -> Dict[str, dict]:
    路径 = _索引路径(项目根)
    if not os.path.isfile(路径):
        return {}
    for 编码 in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(路径, "r", encoding=编码) as f:
                数据 = json.load(f)
            if not isinstance(数据, dict):
                return {}

            是否已修正 = False
            结果: Dict[str, dict] = {}
            for 键, 项 in 数据.items():
                规范项 = _规范歌曲记录项(项, sm路径=str((项 or {}).get("sm路径", "") or ""))
                if 规范项 != 项:
                    是否已修正 = True
                结果[str(键)] = 规范项

            if 是否已修正:
                保存歌曲记录索引(项目根, 结果)
            return 结果
        except Exception:
            continue
    return {}


def 保存歌曲记录索引(项目根: str, 数据: Dict[str, dict]):
    路径 = _索引路径(项目根)
    os.makedirs(os.path.dirname(路径), exist_ok=True)
    with open(路径, "w", encoding="utf-8") as f:
        json.dump(dict(数据 or {}), f, ensure_ascii=False, indent=2)


def _歌曲键(sm路径: str, 项目根: str) -> str:
    sm路径 = str(sm路径 or "").strip()
    if not sm路径:
        return ""
    try:
        return os.path.relpath(sm路径, str(项目根 or os.getcwd())).replace("\\", "/")
    except Exception:
        return sm路径.replace("\\", "/")


def 取歌曲记录键(sm路径: str, 项目根: str) -> str:
    return _歌曲键(sm路径, 项目根)


def _规范歌曲记录项(项, 歌名: str = "", sm路径: str = "") -> dict:
    结果 = dict(项) if isinstance(项, dict) else {}
    try:
        结果["最高分"] = int(max(0, int(结果.get("最高分", 0) or 0)))
    except Exception:
        结果["最高分"] = 0
    try:
        结果["游玩次数"] = int(max(0, int(结果.get("游玩次数", 0) or 0)))
    except Exception:
        结果["游玩次数"] = 0
    if str(结果.get("歌名", "") or "") == "" and 歌名:
        结果["歌名"] = str(歌名 or "")
    if str(结果.get("sm路径", "") or "") == "" and sm路径:
        结果["sm路径"] = str(sm路径 or "")
    return 结果


def 取歌曲记录(项目根: str, sm路径: str, 歌名: str = "") -> dict:
    索引 = 读取歌曲记录索引(项目根)
    键 = _歌曲键(sm路径, 项目根)
    if not 键:
        return _规范歌曲记录项({}, 歌名=str(歌名 or ""), sm路径=str(sm路径 or ""))
    项 = 索引.get(键)
    if not isinstance(项, dict):
        项 = _规范歌曲记录项({}, 歌名=str(歌名 or ""), sm路径=str(sm路径 or ""))
        索引[键] = dict(项)
        保存歌曲记录索引(项目根, 索引)
    else:
        原项 = dict(项)
        项 = _规范歌曲记录项(项, 歌名=str(歌名 or ""), sm路径=str(sm路径 or ""))
        if 项 != 原项:
            索引[键] = dict(项)
            保存歌曲记录索引(项目根, 索引)
    return dict(项)


def 更新歌曲最高分(项目根: str, sm路径: str, 歌名: str, 分数: int) -> dict:
    索引 = 读取歌曲记录索引(项目根)
    键 = _歌曲键(sm路径, 项目根)
    if not 键:
        return {
            "是否新纪录": False,
            "最高分": int(max(0, 分数)),
            "旧最高分": 0,
            "游玩次数": 1,
        }
    项 = 索引.get(键)
    if not isinstance(项, dict):
        项 = _规范歌曲记录项({}, 歌名=str(歌名 or ""), sm路径=str(sm路径 or ""))
    else:
        项 = _规范歌曲记录项(项, 歌名=str(歌名 or ""), sm路径=str(sm路径 or ""))
    旧最高分 = int(项.get("最高分", 0) or 0)
    旧游玩次数 = int(项.get("游玩次数", 0) or 0)
    新分数 = int(max(0, 分数))
    是否新纪录 = bool(新分数 > 旧最高分)
    项["游玩次数"] = int(max(0, 旧游玩次数) + 1)
    if 是否新纪录:
        项["最高分"] = 新分数
        项["歌名"] = str(歌名 or 项.get("歌名", "") or "")
        项["sm路径"] = str(sm路径 or 项.get("sm路径", "") or "")
        索引[键] = dict(项)
        保存歌曲记录索引(项目根, 索引)
    else:
        索引[键] = dict(项)
        保存歌曲记录索引(项目根, 索引)
    return {
        "是否新纪录": 是否新纪录,
        "最高分": int(max(旧最高分, 新分数)),
        "旧最高分": int(旧最高分),
        "游玩次数": int(项.get("游玩次数", 0) or 0),
    }
