#!/usr/bin/env python3
"""Launch the coordinate-picking GUI tool for image element identification.

Usage:
    launch_pick_coords.py <image> [--wait] [--python <interpreter>] [--tool-root <dir>]

Default: start the GUI and return immediately.
--wait: wait for the user to close the tool window, then print the coordinates.

Tool resolution order:
1. --tool-root (if given)
2. Local standard path: E:\\01.Codex\\02.软件输出\\选点工具 (latest version)
3. Tool bundled inside this skill: <skill>/assets/coords-tool (latest version)
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

LOCAL_TOOL_ROOT = Path(r"E:\01.Codex\02.软件输出\选点工具")
BUNDLED_REL = Path("assets") / "coords-tool"
KNOWN_PYTHONS = [
    Path(r"E:\01.Codex\一番\.venv\Scripts\python.exe"),
    Path(r"C:\Users\81426\AppData\Local\Programs\Python\Python310\python.exe"),
]


def skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def latest_version_dir(root: Path) -> Path:
    best, best_key = None, None
    for d in root.iterdir():
        if not d.is_dir():
            continue
        m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", d.name)
        if m:
            key = tuple(int(x) for x in m.groups())
            if best_key is None or key > best_key:
                best, best_key = d, key
    if best is None:
        raise FileNotFoundError(f"No tool version folder under: {root}")
    return best


def resolve_tool_dir(override=None) -> Path:
    candidates = []
    if override:
        candidates.append(Path(override))
    candidates.append(LOCAL_TOOL_ROOT)
    candidates.append(skill_dir() / BUNDLED_REL)
    for root in candidates:
        if root.is_dir():
            try:
                return latest_version_dir(root)
            except FileNotFoundError:
                continue
    raise FileNotFoundError(
        "选点工具未找到：请把工具放到标准目录 " + str(LOCAL_TOOL_ROOT) +
        "（版本文件夹），或保留技能自带的 assets/coords-tool 文件夹。"
    )


def find_python(override=None) -> str:
    candidates = []
    if override:
        candidates.append(Path(override))
    for p in KNOWN_PYTHONS:
        if p.is_file():
            candidates.append(p)
    candidates.append(Path(sys.executable))
    which = shutil.which("python")
    if which:
        candidates.append(Path(which))
    for py in candidates:
        try:
            r = subprocess.run(
                [str(py), "-c", "import PIL, tkinter"],
                capture_output=True, timeout=20,
            )
            if r.returncode == 0:
                return str(py)
        except Exception:
            continue
    raise RuntimeError(
        "未找到带 Pillow 与 tkinter 的 Python。请安装 Python 3.9+"
        "（Windows 官方安装包勾选 Tcl/Tk），然后执行: "
        "pip install -r <工具目录>/requirements.txt"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Launch the coordinate-picking tool")
    ap.add_argument("image", help="path to the image to open")
    ap.add_argument("--wait", action="store_true",
                    help="wait for the user to close the window, then print the coordinates")
    ap.add_argument("--python", default=None, help="override the Python interpreter")
    ap.add_argument("--tool-root", default=None, help="override the tool root directory")
    args = ap.parse_args()

    img = Path(args.image)
    if not img.is_file():
        print(f"图片不存在: {img}")
        return 2

    tool_dir = resolve_tool_dir(args.tool_root)
    script = tool_dir / "pick_coords.py"
    python = find_python(args.python)

    if args.wait:
        r = subprocess.run(
            [python, str(script), str(img)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        out = (r.stdout or "").strip()
        print(out if out else "(工具未输出坐标)")
        return r.returncode

    subprocess.Popen([python, str(script), str(img)])
    print(f"已启动: {tool_dir} 打开 {img}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
