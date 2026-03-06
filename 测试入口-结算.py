import json
import os
import sys

import pygame

from core.常量与路径 import 默认资源路径
from core.工具 import 获取字体
from scenes.场景_结算 import 场景_结算


def _取项目根目录() -> str:
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.path.abspath(os.getcwd())


def _读取json(path: str) -> dict:
    if not path or (not os.path.isfile(path)):
        return {}
    for 编码 in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(path, "r", encoding=编码) as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _创建窗口(尺寸: tuple[int, int], flags: int) -> pygame.Surface:
    请求flags = int(flags | pygame.DOUBLEBUF | pygame.HWSURFACE)
    try:
        return pygame.display.set_mode(尺寸, 请求flags, vsync=1)
    except TypeError:
        try:
            return pygame.display.set_mode(尺寸, 请求flags)
        except Exception:
            return pygame.display.set_mode(尺寸, flags)
    except Exception:
        try:
            return pygame.display.set_mode(尺寸, 请求flags)
        except Exception:
            return pygame.display.set_mode(尺寸, flags)


def _构建测试载荷(项目根: str, 玩家序号: int = 1) -> dict:
    加载页数据 = _读取json(os.path.join(项目根, "json", "加载页.json"))
    歌曲名 = str(加载页数据.get("歌曲名", "") or "Korean Girls Pop Song Party")
    封面路径 = str(加载页数据.get("封面路径", "") or "")
    if 封面路径 and not os.path.isabs(封面路径):
        封面路径 = os.path.join(
            项目根, 封面路径.replace("/", os.sep).replace("\\", os.sep)
        )
    背景图片路径 = str(加载页数据.get("背景图路径", "") or "")
    if 背景图片路径 and not os.path.isabs(背景图片路径):
        背景图片路径 = os.path.join(
            项目根, 背景图片路径.replace("/", os.sep).replace("\\", os.sep)
        )
    背景视频路径 = str(加载页数据.get("背景视频路径", "") or "")
    if 背景视频路径 and not os.path.isabs(背景视频路径):
        背景视频路径 = os.path.join(
            项目根, 背景视频路径.replace("/", os.sep).replace("\\", os.sep)
        )

    return {
        "玩家序号": int(2 if int(玩家序号) == 2 else 1),
        "曲目名": 歌曲名,
        "sm路径": str(加载页数据.get("sm路径", "") or ""),
        "模式": str(加载页数据.get("模式", "竞速") or "竞速"),
        "类型": str(加载页数据.get("类型", "竞速") or "竞速"),
        "本局最高分": 47764800,
        "本局最大combo": 832,
        "歌曲时长秒": 142.0,
        "谱面总分": 47764800,
        "百分比": "98.76%",
        "百分比数值": 98.76,
        "评级": "S",
        "是否评价S": True,
        "失败": False,
        "当前关卡": 1,
        "局数": 1,
        "结算前S数": 2,
        "结算后S数": 3,
        "累计S数": 3,
        "三把S赠送": False,
        "是否赠送第四把": False,
        "perfect数": 832,
        "cool数": 0,
        "good数": 0,
        "miss数": 0,
        "是否全连": True,
        "全连": True,
        "封面路径": 封面路径,
        "星级": int(加载页数据.get("星级", 7) or 7),
        "背景图片路径": 背景图片路径,
        "背景视频路径": 背景视频路径,
        "选歌原始索引": int(加载页数据.get("选歌原始索引", -1) or -1),
    }


def 主函数():
    项目根 = _取项目根目录()
    if 项目根 not in sys.path:
        sys.path.insert(0, 项目根)

    pygame.init()
    pygame.display.set_caption("测试入口 - 结算场景")

    屏幕 = _创建窗口((1280, 720), pygame.RESIZABLE)
    时钟 = pygame.time.Clock()
    资源 = 默认资源路径()
    状态 = {
        "玩家数": 1,
        "投币数": 3,
        "每局所需信用": 3,
    }
    上下文 = {
        "屏幕": 屏幕,
        "时钟": 时钟,
        "资源": 资源,
        "字体": {
            "大字": 获取字体(72),
            "中字": 获取字体(36),
            "小字": 获取字体(22),
            "投币_credit字": 获取字体(22),
        },
        "状态": 状态,
    }

    玩家序号 = 1
    当前载荷 = _构建测试载荷(项目根, 玩家序号=玩家序号)
    当前场景 = 场景_结算(上下文)
    当前场景.进入(dict(当前载荷))
    提示字体 = 获取字体(18)

    def _重建():
        nonlocal 当前场景, 当前载荷
        try:
            当前场景.退出()
        except Exception:
            pass
        当前场景 = 场景_结算(上下文)
        当前场景.进入(dict(当前载荷))

    运行中 = True
    while 运行中:
        时钟.tick_busy_loop(120)

        for 事件 in pygame.event.get():
            if 事件.type == pygame.QUIT:
                运行中 = False
                break

            if 事件.type == pygame.KEYDOWN and 事件.key == pygame.K_F5:
                _重建()
                continue

            if 事件.type == pygame.KEYDOWN and 事件.key in (pygame.K_1, pygame.K_KP1):
                玩家序号 = 1
                当前载荷 = _构建测试载荷(项目根, 玩家序号=玩家序号)
                _重建()
                continue

            if 事件.type == pygame.KEYDOWN and 事件.key in (pygame.K_2, pygame.K_KP2):
                玩家序号 = 2
                当前载荷 = _构建测试载荷(项目根, 玩家序号=玩家序号)
                _重建()
                continue

            if 事件.type == pygame.KEYDOWN and 事件.key == pygame.K_ESCAPE:
                运行中 = False
                break

            if 事件.type == pygame.VIDEORESIZE:
                屏幕 = _创建窗口(
                    (max(960, int(事件.w)), max(540, int(事件.h))), pygame.RESIZABLE
                )
                上下文["屏幕"] = 屏幕
                continue

            try:
                结果 = 当前场景.处理事件(事件)
            except Exception:
                结果 = None
            if isinstance(结果, dict):
                运行中 = False
                break

        if not 运行中:
            break

        try:
            更新结果 = 当前场景.更新()
        except Exception:
            更新结果 = None
        if isinstance(更新结果, dict):
            运行中 = False
            break

        当前场景.绘制()

        try:
            文本1 = "F5 重播结算  1=1P左侧  2=2P右侧  ESC退出"
            文本2 = f"当前玩家序号: {玩家序号}"
            图1 = 提示字体.render(文本1, True, (255, 240, 180)).convert_alpha()
            图2 = 提示字体.render(文本2, True, (190, 225, 255)).convert_alpha()
            背板宽 = int(max(图1.get_width(), 图2.get_width()) + 16)
            背板高 = int(图1.get_height() + 图2.get_height() + 18)
            背板 = pygame.Surface((背板宽, 背板高), pygame.SRCALPHA)
            背板.fill((0, 0, 0, 160))
            屏幕.blit(背板, (16, 16))
            屏幕.blit(图1, (24, 22))
            屏幕.blit(图2, (24, int(26 + 图1.get_height())))
        except Exception:
            pass

        pygame.display.flip()

    try:
        当前场景.退出()
    except Exception:
        pass
    pygame.quit()


if __name__ == "__main__":
    主函数()
