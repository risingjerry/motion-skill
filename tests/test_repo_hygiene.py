"""仓库卫生：不能有本机绝对路径、不能带音频/视频/3D 模型文件、脚本里不能写死个人目录。"""
import os
import re
import subprocess
import unittest

from _util import ROOT

TEXT_EXT = {".md", ".py", ".mjs", ".js", ".html", ".json", ".swift", ".txt", ".svg", ".yml", ".yaml", ".toml"}
BINARY_MEDIA = {".wav", ".mp3", ".aac", ".m4a", ".flac", ".mp4", ".mov", ".usdz", ".usd", ".usdc", ".glb", ".gltf", ".fbx", ".blend"}
ABS_PATH = re.compile(r"(/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+|[A-Za-z]:\\\\Users\\\\)")


def repo_files():
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        return [l for l in out.splitlines() if l]
    except (OSError, subprocess.CalledProcessError):
        files = []
        for d, dirs, fs in os.walk(ROOT):
            dirs[:] = [x for x in dirs if x not in {".git", "node_modules", "out", "__pycache__"}]
            files += [os.path.relpath(os.path.join(d, f), ROOT) for f in fs]
        return files


class HygieneTest(unittest.TestCase):
    def test_no_absolute_home_paths(self):
        bad = []
        for f in repo_files():
            if os.path.splitext(f)[1] not in TEXT_EXT or f.endswith("package-lock.json"):
                continue
            with open(os.path.join(ROOT, f), encoding="utf-8", errors="ignore") as fp:
                for i, line in enumerate(fp, 1):
                    if ABS_PATH.search(line):
                        bad.append(f"{f}:{i}")
        self.assertEqual(bad, [])

    def test_no_media_or_model_files(self):
        bad = [f for f in repo_files() if os.path.splitext(f)[1].lower() in BINARY_MEDIA]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
