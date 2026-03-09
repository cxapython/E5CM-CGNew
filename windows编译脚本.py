# -*- coding: utf-8 -*-

import sys
import shutil
import subprocess
from pathlib import Path


def 获取项目根目录() -> Path:
    return Path(__file__).resolve().parent


def 获取编译结果目录(项目根目录: Path) -> Path:
    return 项目根目录 / "编译结果"


def 获取主程序路径(项目根目录: Path) -> Path:
    return 项目根目录 / "main.py"


def 检查依赖():
    print("=" * 60)
    print("📦 检查编译依赖")
    print("=" * 60)

    依赖映射 = {
        "pygame": "pygame",
        "cv2": "opencv-python",
        "PyInstaller": "pyinstaller",
    }

    缺失包列表 = []

    for 模块名, 包名 in 依赖映射.items():
        try:
            __import__(模块名)
            print(f"✓ {模块名} 已安装")
        except ImportError:
            print(f"✗ {模块名} 未安装")
            缺失包列表.append(包名)

    if 缺失包列表:
        print("\n需要安装以下依赖：")
        for 包名 in 缺失包列表:
            print(f"  - {包名}")

        print("\n是否现在安装？(y/n): ", end="")
        用户输入 = input().strip().lower()
        if 用户输入 != "y":
            print("✗ 编译中止")
            sys.exit(1)

        for 包名 in 缺失包列表:
            print(f"\n正在安装 {包名}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", 包名])

        print("\n✓ 依赖安装完成")

    print()


def 清理目录(路径对象: Path):
    if not 路径对象.exists():
        return

    if 路径对象.is_dir():
        shutil.rmtree(路径对象)
    else:
        路径对象.unlink()


def 清理旧文件(项目根目录: Path):
    print("🧹 清理旧的编译文件")

    待清理列表 = [
        获取编译结果目录(项目根目录),
        项目根目录 / "build",
        项目根目录 / "E5CM-CG.spec",
    ]

    for 路径对象 in 待清理列表:
        if 路径对象.exists():
            清理目录(路径对象)
            print(f"  ✓ 已删除: {路径对象}")

    print()


def 获取需要复制的目录列表(项目根目录: Path) -> list[tuple[Path, str]]:
    """
    这里采用“外部目录整体复制”策略：
    - exe 只负责把 Python 代码编译出来
    - 代码目录、资源目录全部复制到编译结果目录
    - songs 只认：打包专用资源/songs
    - json 只认：打包专用资源/json
    """
    目录名列表 = [
        "core",
        "scenes",
        "ui",
        "UI-img",
        "冷资源",
        "backmovies",
    ]

    复制列表: list[tuple[Path, str]] = []

    for 目录名 in 目录名列表:
        源目录 = 项目根目录 / 目录名
        if 源目录.exists():
            复制列表.append((源目录, 目录名))
        else:
            print(f"⚠ 缺少目录，稍后跳过: {源目录}")

    打包专用歌曲目录 = 项目根目录 / "打包专用资源" / "songs"
    if 打包专用歌曲目录.exists():
        复制列表.append((打包专用歌曲目录, "songs"))
    else:
        print(f"⚠ 未找到打包专用 songs 目录，已跳过: {打包专用歌曲目录}")

    打包专用配置目录 = 项目根目录 / "打包专用资源" / "json"
    if 打包专用配置目录.exists():
        复制列表.append((打包专用配置目录, "json"))
    else:
        print(f"⚠ 未找到打包专用 json 目录，已跳过: {打包专用配置目录}")

    return 复制列表


def 显示复制计划(复制列表: list[tuple[Path, str]]):
    print("📁 复制计划（保持开发环境目录结构）")
    if not 复制列表:
        print("  ⚠ 没有任何可复制目录")
        print()
        return

    for 源目录, 目标目录名 in 复制列表:
        print(f"  ✓ {源目录.name} -> 编译结果\\{目标目录名}")
    print()


def 构建_pyinstaller命令(项目根目录: Path) -> list[str]:
    图标路径 = 项目根目录 / "icon" / "app.ico"
    主程序路径 = 获取主程序路径(项目根目录)
    编译结果目录 = 获取编译结果目录(项目根目录)
    构建目录 = 项目根目录 / "build"

    if not 主程序路径.exists():
        raise FileNotFoundError(f"未找到主程序文件: {主程序路径}")

    命令列表 = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=E5CM-CG",
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--distpath={编译结果目录}",
        f"--workpath={构建目录}",
        f"--specpath={项目根目录}",
    ]

    if 图标路径.exists():
        命令列表.append(f"--icon={图标路径}")
        print(f"✓ 使用图标: {图标路径}")
    else:
        print(f"⚠ 未找到图标，继续无图标编译: {图标路径}")

    命令列表.append(str(主程序路径))
    return 命令列表


def 运行编译(命令列表: list[str]) -> bool:
    print("=" * 60)
    print("🏗️ 开始编译 main.py")
    print("=" * 60)
    print("说明：本次采用 onedir 模式，尽量保持运行环境与开发环境一致")
    print()

    try:
        结果对象 = subprocess.run(命令列表, check=False)
    except Exception as 异常对象:
        print(f"✗ 编译过程异常: {异常对象}")
        return False

    if 结果对象.returncode == 0:
        print("\n✓ 编译成功")
        return True

    print(f"\n✗ 编译失败，返回码: {结果对象.returncode}")
    return False


def 复制目录(源目录: Path, 目标目录: Path):
    if 目标目录.exists():
        shutil.rmtree(目标目录)
    shutil.copytree(源目录, 目标目录)


def 复制文件(源文件: Path, 目标文件: Path):
    目标文件.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(源文件, 目标文件)


def 复制外部目录到输出目录(项目根目录: Path, 复制列表: list[tuple[Path, str]]):
    print("📦 复制外部目录到编译结果目录")

    编译结果目录 = 获取编译结果目录(项目根目录)
    程序目录 = 编译结果目录 / "E5CM-CG"

    if not 程序目录.exists():
        raise FileNotFoundError(f"未找到 PyInstaller 输出目录: {程序目录}")

    for 源目录, 目标目录名 in 复制列表:
        if not 源目录.exists():
            print(f"  ✗ 不存在，跳过: {源目录}")
            continue

        目标目录 = 程序目录 / 目标目录名
        try:
            复制目录(源目录, 目标目录)
            print(f"  ✓ 复制目录: {源目录} -> {目标目录}")
        except Exception as 异常对象:
            print(f"  ✗ 复制失败: {源目录} -> {异常对象}")

    print()


def 复制说明文件(项目根目录: Path):
    编译结果目录 = 获取编译结果目录(项目根目录)
    程序目录 = 编译结果目录 / "E5CM-CG"
    说明文件路径 = 程序目录 / "启动说明.txt"

    内容 = "\n".join(
        [
            "E5CM-CG 打包结果说明",
            "",
            "1. 请从当前目录运行 E5CM-CG.exe",
            "2. 不要单独拿走 exe 文件，需保持整个目录结构完整",
            "3. 本打包方式为 onedir，目的是尽量保持与开发环境一致",
            "4. 若仍有路径错误，请优先检查项目代码里是否写死了 __file__ / cwd / 根目录推断逻辑",
            "",
        ]
    )

    说明文件路径.write_text(内容, encoding="utf-8")


def 验证编译结果(项目根目录: Path, 复制列表: list[tuple[Path, str]]) -> bool:
    print("🔍 验证编译结果")

    编译结果目录 = 获取编译结果目录(项目根目录)
    程序目录 = 编译结果目录 / "E5CM-CG"
    主程序路径 = 程序目录 / "E5CM-CG.exe"

    全部正常 = True

    if 主程序路径.exists():
        print(f"  ✓ 主程序存在: {主程序路径}")
    else:
        print(f"  ✗ 主程序缺失: {主程序路径}")
        全部正常 = False

    for _, 目标目录名 in 复制列表:
        目标目录 = 程序目录 / 目标目录名
        if 目标目录.exists():
            print(f"  ✓ 目录存在: {目标目录}")
        else:
            print(f"  ✗ 目录缺失: {目标目录}")
            全部正常 = False

    print()
    return 全部正常


def 清理临时编译文件(项目根目录: Path):
    print("🧹 清理临时文件")

    待清理列表 = [
        项目根目录 / "build",
        项目根目录 / "E5CM-CG.spec",
        项目根目录 / "__pycache__",
    ]

    for 路径对象 in 待清理列表:
        if not 路径对象.exists():
            continue

        try:
            清理目录(路径对象)
            print(f"  ✓ 删除: {路径对象}")
        except Exception as 异常对象:
            print(f"  ⚠ 删除失败: {路径对象} -> {异常对象}")

    print()


def 主程序():
    项目根目录 = 获取项目根目录()
    编译结果目录 = 获取编译结果目录(项目根目录)

    print()
    print("=" * 60)
    print("🎮 E5CM-CG 极简一致性打包脚本")
    print("=" * 60)
    print(f"项目根目录: {项目根目录}")
    print(f"输出目录: {编译结果目录}")
    print()

    检查依赖()
    清理旧文件(项目根目录)

    复制列表 = 获取需要复制的目录列表(项目根目录)
    显示复制计划(复制列表)

    命令列表 = 构建_pyinstaller命令(项目根目录)
    是否成功 = 运行编译(命令列表)
    if not 是否成功:
        print("\n❌ 编译失败，请先看 PyInstaller 上面的真实报错")
        sys.exit(1)

    复制外部目录到输出目录(项目根目录, 复制列表)
    复制说明文件(项目根目录)

    验证通过 = 验证编译结果(项目根目录, 复制列表)
    if not 验证通过:
        print("\n⚠ 编译完成，但结果不完整，请检查缺失目录")
        sys.exit(1)

    清理临时编译文件(项目根目录)

    print("=" * 60)
    print("✨ 编译成功")
    print("=" * 60)
    print(f"输出位置: {编译结果目录 / 'E5CM-CG'}")
    print(f"启动文件: {编译结果目录 / 'E5CM-CG' / 'E5CM-CG.exe'}")
    print("目录结构已尽量保持与开发环境一致")
    print()


if __name__ == "__main__":
    try:
        主程序()
    except KeyboardInterrupt:
        print("\n⚠ 编译被中止")
        sys.exit(1)
    except Exception as 异常对象:
        print(f"\n❌ 发生错误: {异常对象}")
        import traceback
        traceback.print_exc()
        sys.exit(1)