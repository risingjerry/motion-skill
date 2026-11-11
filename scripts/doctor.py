#!/usr/bin/env python3
"""检查这台电脑能不能跑这个 Skill：缺什么、怎么装。退出码 0 = 必需的都齐了。

  python3 scripts/doctor.py          # 人看的表
  python3 scripts/doctor.py --json   # 给 Agent 读的 JSON
"""
import argparse
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def check():
    items = []

    def add(name, ok, required, detail, fix=""):
        items.append({"name": name, "ok": bool(ok), "required": required, "detail": detail, "fix": "" if ok else fix})

    v = sys.version_info
    add("Python ≥ 3.9", v >= (3, 9), True, platform.python_version(), "安装 Python 3.9 以上")
    for mod, pkg in (("numpy", "numpy"), ("PIL", "Pillow"), ("cv2", "opencv-python-headless")):
        try:
            m = importlib.import_module(mod)
            add(f"Python 包 {pkg}", True, True, getattr(m, "__version__", "已安装"))
        except ImportError:
            add(f"Python 包 {pkg}", False, True, "没装", "python3 -m pip install -r requirements.txt")

    node = shutil.which("node")
    if node:
        code, out = run(["node", "-v"])
        major = int(out.lstrip("v").split(".")[0]) if code == 0 and out.startswith("v") else 0
        add("Node.js ≥ 20", major >= 20, True, out, "安装 Node.js 20 以上：https://nodejs.org")
    else:
        add("Node.js ≥ 20", False, True, "没找到 node", "安装 Node.js 20 以上：https://nodejs.org")
    pw = os.path.isdir(os.path.join(ROOT, "node_modules", "playwright-core"))
    add("npm 依赖 playwright-core", pw, True, "已安装" if pw else "没装", "在仓库根目录运行：npm install")
    if node and pw:
        code, out = run(["node", "scripts/render.mjs", "doctor"], timeout=90)
        detail = out.splitlines()[-1] if out else ""
        add("无头浏览器（Chrome/Chromium）", code == 0, True, detail[:120],
            "安装 Google Chrome，或运行 npx playwright-core install chromium，或设置 CHROME_PATH")
    for tool in ("ffmpeg", "ffprobe"):
        add(tool, shutil.which(tool), True, shutil.which(tool) or "没找到",
            "macOS：brew install ffmpeg；Windows：winget install ffmpeg；Linux：apt install ffmpeg")

    blender = os.environ.get("BLENDER") or shutil.which("blender")
    if blender:
        code, out = run([blender, "--version"], timeout=120)
        add("Blender（可选，第三层）", code == 0, False, out.splitlines()[0] if out else blender)
    else:
        add("Blender（可选，第三层）", False, False, "没找到 blender 命令",
            "从 https://www.blender.org 下载；命令行找不到时设置环境变量 BLENDER=Blender 可执行文件路径")

    mac = platform.system() == "Darwin"
    ver = platform.mac_ver()[0] if mac else ""
    major = int(ver.split(".")[0]) if ver else 0
    swift = shutil.which("swift")
    add("macOS Vision 抠像（可选，剪影转场）", mac and major >= 14 and swift, False,
        f"macOS {ver}，swift {'有' if swift else '无'}" if mac else platform.system(),
        "非 macOS 或没有 swift：用 rembg / MediaPipe / 剪辑软件导出黑白蒙版，见 references/silhouette.md")
    return items


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    items = check()
    ready = all(i["ok"] for i in items if i["required"])
    if a.json:
        print(json.dumps({"ready": ready, "checks": items}, ensure_ascii=False, indent=1))
    else:
        for i in items:
            mark = "OK  " if i["ok"] else ("缺  " if i["required"] else "可选")
            print(f"{mark} {i['name']}：{i['detail']}")
            if i["fix"]:
                print(f"      → {i['fix']}")
        print("\n必需的都齐了，可以开始。" if ready else "\n还缺必需的东西，按上面的提示装好再来。")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
