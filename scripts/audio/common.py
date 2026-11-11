"""声音脚本共用的小工具：用 ffmpeg 读写音频、测响度。只依赖 numpy 和 ffmpeg。"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np

SR = 48000


def need_ffmpeg():
    if not shutil.which(os.environ.get("FFMPEG", "ffmpeg")):
        sys.exit("找不到 ffmpeg。macOS：brew install ffmpeg；Windows：winget install ffmpeg；Linux：apt install ffmpeg")


def ff():
    return os.environ.get("FFMPEG", "ffmpeg")


def load(path, sr=SR):
    """读任意音频/视频里的声音，返回 (n, 2) float64，采样率 sr。"""
    need_ffmpeg()
    raw = subprocess.run([ff(), "-v", "error", "-i", path, "-vn", "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def save(a, path, sr=SR, codec="pcm_s24le"):
    need_ffmpeg()
    a = np.asarray(a, dtype=np.float32)
    if a.ndim == 1:
        a = np.stack([a, a], axis=1)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    subprocess.run([ff(), "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-", "-c:a", codec, path],
                   input=np.ascontiguousarray(a).tobytes(), check=True)
    return path


def measure(path_or_array, sr=SR):
    """用 ffmpeg 的 ebur128 测整体响度（LUFS）和真峰值（dBTP）。"""
    need_ffmpeg()
    tmp = None
    path = path_or_array
    if not isinstance(path_or_array, str):
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        save(path_or_array, tmp.name, sr, codec="pcm_f32le")
        path = tmp.name
    try:
        err = subprocess.run([ff(), "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
    finally:
        if tmp:
            os.unlink(tmp.name)
    summary = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    lufs = float(i.group(1)) if i else float("-inf")
    peak = float(tp.group(1)) if tp else float("-inf")
    return {"lufs": lufs, "true_peak": peak}


def db(x):
    return 10 ** (x / 20.0)


def oversample4(x):
    """用 FFT 补零做 4 倍过采样，估计采样点之间的真峰值。x: (n, 2)"""
    n = len(x)
    X = np.fft.rfft(x, axis=0)
    Y = np.zeros((4 * n // 2 + 1, x.shape[1]), dtype=complex)
    Y[: X.shape[0]] = X
    return np.fft.irfft(Y, n=4 * n, axis=0) * 4


if __name__ == "__main__":
    print(json.dumps(measure(sys.argv[1])))
