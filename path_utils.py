import os
import sys
import shutil


def is_frozen():
    """判断当前是否运行在 PyInstaller 打包后的 exe 环境中"""
    return getattr(sys, "frozen", False)


def bundle_dir():
    """
    Nuitka / 普通运行统一路径
    - 打包后：使用 exe 所在目录
    - 开发环境：使用当前 py 文件目录
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def app_dir():
    """
    返回“程序运行目录”：
    - 打包后：exe 所在目录
    - 开发环境：项目根目录
    """
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts):
    """
    只读资源路径：
    用于读取打包进去的资源文件，例如：
    - login.csv
    - model/best.pt
    - yolov5
    - 默认 config.json
    """
    return os.path.join(bundle_dir(), *parts)


def app_path(*parts):
    """
    运行时可写路径：
    用于程序运行过程中生成/修改的文件，例如：
    - history.csv
    - model/output
    - model/input
    - 实际使用中的 config.json
    """
    path = os.path.join(app_dir(), *parts)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


def ensure_runtime_file(rel_path):
    """
    确保运行目录下存在某个文件：
    - 如果运行目录没有，就从打包资源目录复制一份过去
    - 如果已经存在，就直接返回运行目录下的路径

    适合这种场景：
    - model/config.json 第一次运行时从资源复制出来
    - 后续程序再对它进行修改和保存
    """
    dst = app_path(rel_path)
    if not os.path.exists(dst):
        src = resource_path(rel_path)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    return dst