import os
import pygame

from scenes.场景_加载页 import 场景_加载页


def 取项目根目录() -> str:
    当前文件 = os.path.abspath(__file__)
    当前目录 = os.path.dirname(当前文件)
    已检查 = set()

    for 起点 in [当前目录, os.getcwd()]:
        路径 = os.path.abspath(起点)
        while 路径 and 路径 not in 已检查:
            已检查.add(路径)
            if os.path.isdir(os.path.join(路径, "scenes")) and os.path.isdir(
                os.path.join(路径, "core")
            ):
                return 路径
            上级 = os.path.dirname(路径)
            if 上级 == 路径:
                break
            路径 = 上级

    return 当前目录


def 取可用封面路径(项目根目录: str) -> str:
    候选路径列表 = [
        os.path.join(项目根目录, "冷资源", "backimages", "选歌界面.png"),
        os.path.join(
            项目根目录, "UI-img", "选歌界面资源", "小星星", "大星星.png"
        ),
    ]

    for 候选路径 in 候选路径列表:
        if os.path.isfile(候选路径):
            return 候选路径
    return ""


def 取联网图标路径(项目根目录: str) -> str:
    候选路径列表 = [
        os.path.join(项目根目录, "UI-img", "联网图标.png"),
        os.path.join(项目根目录, "UI-img", "投币界面资源", "联网.png"),
        os.path.join(项目根目录, "UI-img", "投币界面资源", "联网图标.png"),
    ]
    for 候选路径 in 候选路径列表:
        if os.path.isfile(候选路径):
            return 候选路径
    return ""


def 取字体对象(字号: int, 是否粗体: bool = False) -> pygame.font.Font:
    try:
        from core.工具 import 获取字体

        return 获取字体(int(字号), 是否粗体=bool(是否粗体))
    except Exception:
        pygame.font.init()
        try:
            return pygame.font.SysFont(
                "Microsoft YaHei", int(字号), bold=bool(是否粗体)
            )
        except Exception:
            return pygame.font.Font(None, int(字号))


def 构建测试上下文(屏幕: pygame.Surface, 项目根目录: str) -> dict:
    return {
        "屏幕": 屏幕,
        "资源": {
            "根": 项目根目录,
            "投币_联网图标": 取联网图标路径(项目根目录),
        },
        "字体": {
            "投币_credit字": 取字体对象(28, 是否粗体=True),
        },
        "状态": {
            "投币数": 2,
            "每局所需信用": 3,
            "加载页_载荷": {},
        },
    }


def 构建测试载荷(项目根目录: str) -> dict:
    return {
        "歌名": "Debug Loading Song",
        "星级": 14,
        "bpm": 172,
        "人气": 9999,
        "sm路径": os.path.join(
            项目根目录, "songs", "debug_song", "debug_song.ssc"
        ),
        "封面路径": 取可用封面路径(项目根目录),
        "设置参数": {
            "速度": "x3.5",
            "镜像": "关",
            "隐藏": "关",
            "背景类型": "默认",
        },
        "设置参数文本": "设置参数：速度:x3.5  /  镜像:关  /  隐藏:关  /  背景:默认",
    }


def 主函数():
    pygame.init()
    pygame.font.init()

    项目根目录 = 取项目根目录()
    屏幕 = pygame.display.set_mode((1600, 900), pygame.RESIZABLE)
    pygame.display.set_caption("加载页调试入口")

    时钟 = pygame.time.Clock()
    上下文 = 构建测试上下文(屏幕, 项目根目录)
    测试载荷 = 构建测试载荷(项目根目录)

    场景 = 场景_加载页(上下文)
    场景.进入(测试载荷)

    是否运行 = True
    while 是否运行:
        for 事件 in pygame.event.get():
            if 事件.type == pygame.QUIT:
                是否运行 = False
                continue

            if 事件.type == pygame.VIDEORESIZE:
                屏幕 = pygame.display.set_mode(
                    (max(800, 事件.w), max(600, 事件.h)), pygame.RESIZABLE
                )
                上下文["屏幕"] = 屏幕

            if 事件.type == pygame.KEYDOWN:
                if 事件.key == pygame.K_F5:
                    测试载荷 = 构建测试载荷(项目根目录)
                    场景 = 场景_加载页(上下文)
                    场景.进入(测试载荷)
                    continue

            返回结果 = 场景.处理事件(事件)
            if isinstance(返回结果, dict):
                print("场景事件返回：", 返回结果)

        返回结果 = 场景.更新()
        if isinstance(返回结果, dict):
            print("场景更新返回：", 返回结果)

        场景.绘制()
        pygame.display.flip()
        时钟.tick(60)

    pygame.quit()


if __name__ == "__main__":
    主函数()