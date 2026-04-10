import os
import pygame


_混音器初始化已尝试 = False
_混音器可用 = False


def 确保pygame基础模块已初始化() -> None:
    try:
        if not pygame.display.get_init():
            pygame.display.init()
    except Exception:
        pass

    try:
        if not pygame.font.get_init():
            pygame.font.init()
    except Exception:
        pass


def 确保混音器已初始化(*, 允许重试: bool = False) -> bool:
    global _混音器初始化已尝试, _混音器可用

    try:
        if pygame.mixer.get_init():
            _混音器初始化已尝试 = True
            _混音器可用 = True
            return True
    except Exception:
        pass

    if bool(_混音器初始化已尝试) and (not bool(允许重试)):
        return bool(_混音器可用)

    _混音器初始化已尝试 = True
    try:
        pygame.mixer.init()
        _混音器可用 = bool(pygame.mixer.get_init())
    except Exception:
        _混音器可用 = False
    return bool(_混音器可用)


class 音乐管理:
    def __init__(self):
        确保pygame基础模块已初始化()
        self.可用 = bool(确保混音器已初始化(允许重试=True))
        self.当前路径 = None

    def 播放循环(self, 路径: str):
        if not self.可用:
            return
        if not 路径 or not os.path.isfile(路径):
            return
        if self.当前路径 == 路径 and pygame.mixer.music.get_busy():
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        try:
            pygame.mixer.music.load(路径)
            pygame.mixer.music.play(-1)
            self.当前路径 = 路径
        except Exception:
            pass

    def 停止(self):
        if not self.可用:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.当前路径 = None
