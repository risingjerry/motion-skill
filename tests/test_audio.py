import json
import os
import shutil
import tempfile
import unittest

import numpy as np

from _util import ROOT  # noqa: F401  （设置 sys.path）
import common
import mix
import synth

HAS_FFMPEG = shutil.which("ffmpeg") is not None


@unittest.skipUnless(HAS_FFMPEG, "需要 ffmpeg")
class AudioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="motion-skill-audio-")
        synth.main(["kit", os.path.join(cls.tmp, "sfx")])
        synth.main(["bed", os.path.join(cls.tmp, "bed.wav"), "--duration", "12", "--hit", "7.5"])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_kit_files(self):
        meta = json.load(open(os.path.join(self.tmp, "sfx", "kit.json"), encoding="utf-8"))
        self.assertEqual(set(meta["sounds"]), set(synth.KIT))
        for name in synth.KIT:
            x = common.load(os.path.join(self.tmp, "sfx", f"{name}.wav"))
            self.assertGreater(len(x), 100)
            self.assertLess(np.abs(x).max(), 1.0)

    def test_hit_detection(self):
        x = common.load(os.path.join(self.tmp, "bed.wav"))
        self.assertAlmostEqual(mix.find_hit(x), 7.5, delta=0.025)  # 误差小于 30 fps 下的一帧

    def test_resolve_time(self):
        b = {"flip": 1.4, "screen-left": 2.0}
        self.assertAlmostEqual(mix.resolve_time("beat:flip+0.75", b), 2.15)
        self.assertAlmostEqual(mix.resolve_time("beat:screen-left-0.5", b), 1.5)
        self.assertAlmostEqual(mix.resolve_time("beat:screen-left", b), 2.0)
        self.assertEqual(mix.resolve_time(3, b), 3.0)

    def test_mix_alignment_loudness(self):
        spec = {
            "duration": 6.0,
            "beats": "beats.json",
            "music": {"file": "bed.wav", "hit_in_file": "json", "hit_at": "beat:land", "fade_out": [5.5, 6.0]},
            "cues": [{"file": "sfx/click.wav", "at": "beat:tap", "align": "onset", "gain_db": -3}],
            "duck": {"depth_db": 4},
            "loudness": {"lufs": -14, "true_peak": -1.0},
        }
        with open(os.path.join(self.tmp, "beats.json"), "w") as f:
            json.dump({"beats": {"land": 4.0, "tap": 1.0}}, f)
        p = os.path.join(self.tmp, "s.json")
        with open(p, "w") as f:
            json.dump(spec, f)
        out = os.path.join(self.tmp, "mix.wav")
        rep = mix.run(p, out, quiet=True)
        self.assertAlmostEqual(rep["music"]["music_starts_at"], 4.0 - 7.5, places=3)
        self.assertAlmostEqual(rep["wav"]["lufs"], -14.0, delta=0.5)
        self.assertLessEqual(rep["wav"]["true_peak"], -1.0)
        y = common.load(out)
        self.assertAlmostEqual(len(y) / common.SR, 6.0, delta=0.01)
        # 配乐最重的一拍应落在 4.0 秒附近
        self.assertAlmostEqual(mix.find_hit(y), 4.0, delta=0.035)

    def test_offset_only_shifts(self):
        base = {"duration": 3.0, "cues": [{"file": "sfx/pop.wav", "at": 1.0, "align": "start"}], "loudness": {"lufs": -20, "true_peak": -1}}
        outs = []
        for off in (0.0, 0.25):
            p = os.path.join(self.tmp, f"o{off}.json")
            with open(p, "w") as f:
                json.dump({**base, "offset": off}, f)
            o = os.path.join(self.tmp, f"o{off}.wav")
            mix.run(p, o, quiet=True)
            outs.append(common.load(o)[:, 0])
        a, b = outs
        s = int(0.25 * common.SR)
        onset_a = int(np.argmax(np.abs(a) > 1e-3))
        onset_b = int(np.argmax(np.abs(b) > 1e-3))
        self.assertAlmostEqual(onset_b - onset_a, s, delta=2)


if __name__ == "__main__":
    unittest.main()
