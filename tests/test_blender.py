"""Blender 部分的测试：机器上没有 blender 命令就跳过。只跑检查（不渲染），几秒钟。"""
import os
import shutil
import subprocess
import unittest

from _util import ROOT

BLENDER = os.environ.get("BLENDER") or shutil.which("blender")
STUDIO = os.path.join(ROOT, "scripts", "blender", "studio.py")


def run(*extra):
    cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", STUDIO, "--", "--demo", "--no-render",
           "--check", "Lid:Body", "--check-objects", "Lid", *extra]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


@unittest.skipUnless(BLENDER, "没有 blender 命令")
class BlenderTest(unittest.TestCase):
    def test_demo_is_green(self):
        r = run()
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertIn("MOTION_CHECK GREEN", r.stdout)

    def test_wrong_hinge_is_caught(self):
        r = run("--demo-variant", "wrong-hinge")
        self.assertEqual(r.returncode, 1)
        self.assertIn("MOTION_CHECK RED", r.stdout)

    def test_too_fast_is_caught(self):
        r = run("--max-deg", "3")
        self.assertEqual(r.returncode, 1)
        self.assertIn("RED", r.stdout)


if __name__ == "__main__":
    unittest.main()
