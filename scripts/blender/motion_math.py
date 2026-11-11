"""运动检查用到的纯数学（不依赖 Blender，方便单元测试）。

四元数一律写成 (w, x, y, z)。
"""
import math


def quat_angle_deg(q1, q2):
    """两个朝向之间转过的角度（度），0–180。"""
    dot = abs(sum(a * b for a, b in zip(q1, q2)))
    n1 = math.sqrt(sum(a * a for a in q1))
    n2 = math.sqrt(sum(b * b for b in q2))
    c = min(1.0, dot / (n1 * n2 + 1e-15))
    return math.degrees(2 * math.acos(c))


def angular_speeds(quats):
    """逐帧角速度（度/帧）：第 i 个值 = 第 i 帧到第 i+1 帧转过的角度。"""
    return [quat_angle_deg(quats[i], quats[i + 1]) for i in range(len(quats) - 1)]


def linear_speeds(points):
    return [math.dist(points[i], points[i + 1]) for i in range(len(points) - 1)]


def speed_problems(speeds, max_speed, max_jump, first_frame=1, unit="°"):
    """找超速和转速突变的帧。返回 [(帧号, 说明)]。

    max_speed：每帧最多转/走多少；max_jump：相邻两帧的速度差最多多少（防止忽快忽慢、一顿一顿）。
    """
    out = []
    for i, s in enumerate(speeds):
        if s > max_speed + 1e-9:
            out.append((first_frame + i, f"速度 {s:.2f}{unit}/帧 > {max_speed}"))
    for i in range(1, len(speeds)):
        j = abs(speeds[i] - speeds[i - 1])
        if j > max_jump + 1e-9:
            out.append((first_frame + i, f"速度突变 {speeds[i - 1]:.2f}→{speeds[i]:.2f}{unit}/帧（差 {j:.2f} > {max_jump}）"))
    return out


def quat_from_axis_angle(axis, deg):
    x, y, z = axis
    n = math.sqrt(x * x + y * y + z * z)
    h = math.radians(deg) / 2
    s = math.sin(h) / n
    return (math.cos(h), x * s, y * s, z * s)
