import json
import os
import shutil
import tempfile
import unittest

import numpy as np
from PIL import Image

from _util import ROOT  # noqa: F401
import layout_check
import motion_math as mm
import seam_check
import sheet
import silhouette


class LayoutTest(unittest.TestCase):
    def probe(self, text_box):
        return {"output": [3840, 2160], "frames": [{"t": 0, "items": [
            {"name": "hero", "kind": "subject", "box": [1720, 880, 2120, 1280]},
            {"name": "title", "kind": "text", "box": text_box}]}]}

    def test_clear_text_is_green(self):
        red, rows = layout_check.check_probe(self.probe([2200, 1000, 2800, 1100]), centers=["hero"])
        self.assertFalse(red, rows)

    def test_text_too_close_is_red(self):
        red, rows = layout_check.check_probe(self.probe([2140, 1000, 2800, 1100]))
        self.assertTrue(red)
        self.assertAlmostEqual(rows[0]["min_gap_px_4k"], 20.0)

    def test_overlap_reports_negative_depth(self):
        red, rows = layout_check.check_probe(self.probe([2000, 1000, 2800, 1100]))
        self.assertTrue(red)
        self.assertLess(rows[0]["min_gap_px_4k"], 0)

    def test_scale_to_4k(self):
        p = {"output": [1920, 1080], "frames": [{"t": 0, "items": [
            {"name": "a", "kind": "subject", "box": [0, 0, 100, 100]},
            {"name": "b", "kind": "text", "box": [130, 0, 200, 50]}]}]}
        red, rows = layout_check.check_probe(p)
        self.assertFalse(red)
        self.assertAlmostEqual(rows[0]["min_gap_px_4k"], 60.0)

    def test_off_center_is_red(self):
        p = {"output": [3840, 2160], "frames": [{"t": 0, "items": [{"name": "hero", "kind": "subject", "box": [0, 0, 400, 400]}]}]}
        red, _ = layout_check.check_probe(p, centers=["hero"])
        self.assertTrue(red)

    def test_mask_mode(self):
        tmp = tempfile.mkdtemp()
        try:
            a = np.zeros((216, 384, 4), np.uint8)
            a[80:140, 160:220, 3] = 255
            Image.fromarray(a).save(os.path.join(tmp, "0001.png"))
            red, rows = layout_check.check_masks(tmp, 30, [{"name": "t", "from": 0, "to": 0, "box": [2300, 900, 2600, 1000]}], out_w=3840)
            self.assertFalse(red, rows)  # 物体右边缘 220*10=2200，离字 100 px
            red, rows = layout_check.check_masks(tmp, 30, [{"name": "t", "from": 0, "to": 0, "box": [2100, 900, 2600, 1000]}], out_w=3840)
            self.assertTrue(red)
        finally:
            shutil.rmtree(tmp)


def part(h, w, y0, y1, x0, x1):
    a = np.zeros((h, w), np.float64)
    a[y0:y1, x0:x1] = 1.0
    return a


class SeamTest(unittest.TestCase):
    def test_aligned_parts(self):
        top = part(400, 800, 100, 200, 200, 600)
        bot = part(400, 800, 200, 330, 200, 600)
        for side, (y, off) in seam_check.seam_offsets(top, bot).items():
            self.assertEqual(y, 199)
            self.assertAlmostEqual(off, 0.0, places=6)

    def test_narrow_lid(self):
        top = part(400, 800, 100, 200, 205, 595)
        bot = part(400, 800, 200, 330, 200, 600)
        r = seam_check.seam_offsets(top, bot)
        self.assertAlmostEqual(r["L"][1], 5.0, places=6)
        self.assertAlmostEqual(r["R"][1], -5.0, places=6)

    def test_shifted_lid(self):
        top = part(400, 800, 100, 200, 203, 603)
        bot = part(400, 800, 200, 330, 200, 600)
        r = seam_check.seam_offsets(top, bot)
        self.assertAlmostEqual(r["L"][1], 3.0, places=6)
        self.assertAlmostEqual(r["R"][1], 3.0, places=6)

    def test_cli_exit_codes(self):
        tmp = tempfile.mkdtemp()
        try:
            def save(a, n):
                rgba = np.zeros(a.shape + (4,), np.uint8)
                rgba[..., 3] = (a * 255).astype(np.uint8)
                Image.fromarray(rgba).save(os.path.join(tmp, n))
            save(part(216, 384, 50, 100, 100, 300), "top.png")
            save(part(216, 384, 100, 160, 100, 300), "ok.png")
            save(part(216, 384, 100, 160, 101, 301), "bad.png")
            self.assertEqual(seam_check.main(["--top-file", os.path.join(tmp, "top.png"), "--bottom-file", os.path.join(tmp, "ok.png")]), 0)
            # 1 px @384 宽 = 10 px @4K → 红
            self.assertEqual(seam_check.main(["--top-file", os.path.join(tmp, "top.png"), "--bottom-file", os.path.join(tmp, "bad.png")]), 1)
        finally:
            shutil.rmtree(tmp)


class MotionMathTest(unittest.TestCase):
    def test_angles(self):
        q0 = (1, 0, 0, 0)
        q = mm.quat_from_axis_angle((0, 0, 1), 30)
        self.assertAlmostEqual(mm.quat_angle_deg(q0, q), 30, places=6)
        self.assertAlmostEqual(mm.quat_angle_deg(q, tuple(-c for c in q)), 0, places=4)

    def test_speed_problems(self):
        qs = [mm.quat_from_axis_angle((1, 0, 0), a) for a in (0, 2, 4, 6, 8)]
        self.assertEqual(mm.speed_problems(mm.angular_speeds(qs), 6, 1.5), [])
        qs = [mm.quat_from_axis_angle((1, 0, 0), a) for a in (0, 2, 4, 12, 14)]
        probs = mm.speed_problems(mm.angular_speeds(qs), 6, 1.5)
        frames = sorted({f for f, _ in probs})
        self.assertEqual(frames, [3, 4])


class SilhouetteTest(unittest.TestCase):
    def test_draw_circle(self):
        tmp = tempfile.mkdtemp()
        try:
            m = np.zeros((108, 192), np.uint8)
            yy, xx = np.mgrid[:108, :192]
            m[(xx - 96) ** 2 + (yy - 54) ** 2 < 30 ** 2] = 255
            m[10:14, 10:14] = 255   # 小噪点：应被去掉（只留最大块）
            m[52:56, 94:98] = 0     # 小洞：应被补上
            os.makedirs(os.path.join(tmp, "m"))
            Image.fromarray(m).save(os.path.join(tmp, "m", "0001.png"))
            rc = silhouette.main(["draw", os.path.join(tmp, "m"), os.path.join(tmp, "o"), "--size", "384x216", "--sigma", "0"])
            self.assertEqual(rc, 0)
            out = np.asarray(Image.open(os.path.join(tmp, "o", "0001.png")).convert("L"))
            self.assertEqual(out.shape, (216, 384))
            self.assertEqual(out[108, 192], 0)       # 中心是剪影（黑）
            self.assertEqual(out[24, 24], 255)       # 噪点被去掉（白底）
            dark = (out < 128).mean()
            self.assertAlmostEqual(dark, np.pi * 60 ** 2 / (384 * 216), delta=0.01)
        finally:
            shutil.rmtree(tmp)

    def test_crop_zooms_in(self):
        m = np.zeros((100, 100), np.uint8)
        m[40:60, 40:60] = 1
        full = silhouette.draw_frame(m, (200, 200), (0, 0, 100, 100), (0, 0, 0), (255, 255, 255), 0)
        close = silhouette.draw_frame(m, (200, 200), (40, 40, 20, 20), (0, 0, 0), (255, 255, 255), 0)
        self.assertLess((full[..., 0] < 128).mean(), 0.05)
        # 轮廓走在边界像素的中心，所以比蒙版小半个像素；特写放大后约占 90%
        self.assertGreater((close[..., 0] < 128).mean(), 0.85)


class SheetTest(unittest.TestCase):
    def test_tile(self):
        tmp = tempfile.mkdtemp()
        try:
            paths = []
            for i in range(5):
                p = os.path.join(tmp, f"{i}.png")
                Image.new("RGB", (320, 180), (i * 40, 0, 0)).save(p)
                paths.append(p)
            out = os.path.join(tmp, "s.jpg")
            self.assertEqual(sheet.main(["images", out, *paths, "--cols", "3", "--width", "160"]), 0)
            im = Image.open(out)
            self.assertEqual(im.width, 3 * 160 + 4 * 8)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
