#!/usr/bin/env python3
"""gen_bigscale_image.py — 为大尺度天体（黑洞/星云/星系/星团/大尺度结构）生成程序化贴图。

与 NASA 真图流水线（scripts/nasa_image.py）互补：先由本脚本全量生成兜底示意图，
再用 nasa_image.py --auto-batch 逐张覆盖为 NASA 真图（覆盖失败的保留本脚本产物）。

约定（与既有贴图体系一致）：
  - 600×600 RGBA，四边 5% alpha 渐隐，融入整站深色星空底
  - 黑洞：黑色视界圆盘（半径 210px = 画布高 35%，与本站球体贴图本体占比一致，
    对比页 measureSphere 测得的本体比例即 0.35）+ 琥珀色吸积环 + 低 alpha 辉光
  - 延展天体（星云/星系/星团/结构）：全幅即天体本身，对比页按「全幅=等效球径」绘制
用法：python scripts/gen_bigscale_image.py [--force] [--ids id1,id2]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASTRO = ROOT / "docs" / "data" / "astro.json"
PLANET_DIR = ROOT / "docs" / "assets" / "planets"
SIZE = 600


# ---------------------------------------------------------------- 基础工具
def value_noise(h, w, seed, res):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, res[0]), max(2, res[1])))
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(img, dtype=np.float64) / 255.0


def fbm(h, w, seed, octaves=5, base=4, gain=0.55):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        res_r = base * (2 ** o)
        res_c = max(2, int(res_r * w / h))
        total += amp * value_noise(h, w, seed + o * 977, (res_r, res_c))
        norm += amp
        amp *= gain
    return total / norm


def feather_alpha(h, w, frac=0.05):
    yy, xx = np.mgrid[0:h, 0:w]
    f = max(6, int(min(h, w) * frac))
    edge = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]).astype(np.float64)
    return np.clip(edge / f, 0, 1)


def colorize(f, stops):
    """f: [0,1] 场；stops: [(pos, (r,g,b)), ...] 按 pos 插值出 RGB [0,1]。"""
    pos = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], dtype=np.float64) / 255.0
    out = np.empty(f.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(f, pos, cols[:, c])
    return out


def starfield(n, h, w, seed, rmax=1.6, rmin=0.5, tint=None):
    rng = np.random.default_rng(seed)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        x, y = rng.random() * w, rng.random() * h
        r = rmin + rng.random() * (rmax - rmin)
        b = 120 + rng.random() * 135
        if tint:
            col = tuple(int(c * b / 255) for c in tint)
        else:
            col = (int(b), int(b * 0.96), int(b * 0.90))
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))
    return layer


def galaxy_blob(draw, cx, cy, rx, ry, col, alpha):
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col + (int(alpha),))


def save(oid, rgb, alpha, extra_layers=None):
    """rgb/alpha: float [0,1]/(0..255)；extra_layers: RGBA PIL 图叠加上去。"""
    h, w = SIZE, SIZE
    fa = feather_alpha(h, w)
    if extra_layers:
        base = np.asarray(extra_layers[0].convert("RGBA"), dtype=np.float64)
        for lay in extra_layers[1:]:
            la = np.asarray(lay.convert("RGBA"), dtype=np.float64)
            laa = (la[..., 3:4] / 255.0)
            base = la * laa + base * (1 - laa)
        rgb = base[..., :3] / 255.0
        alpha = base[..., 3]
    a = np.clip(alpha, 0, 255) * fa
    rgba = np.dstack([np.clip(rgb * 255, 0, 255), a]).astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    PLANET_DIR.mkdir(parents=True, exist_ok=True)
    dst = PLANET_DIR / f"{oid}.webp"
    img.save(dst, "WEBP", quality=85)
    return dst


# ---------------------------------------------------------------- 黑洞
def draw_blackhole(oid, seed):
    """EHT 风格：黑盘 + 不对称琥珀环 + 外辉光（辉光 alpha<40 不干扰球体测量）。"""
    h = w = SIZE
    c = SIZE / 2
    disk_r = 210.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    dx, dy = xx - c, yy - c
    r = np.hypot(dx, dy)
    # 辉光（半径 210~320，峰值 alpha ~38，低于 measureSphere 的 40 阈值）
    glow = np.clip(1 - (r - disk_r) / 110.0, 0, 1) ** 2.0 * 38
    glow *= (r > disk_r)
    # 吸积环：环带 208~226，底部更亮（EHT 观测的 Doppler 增亮），厚度噪声扰动
    ring = np.clip(1 - np.abs(r - (disk_r + 9)) / 10.0, 0, 1)
    theta = np.arctan2(dy, dx)
    asym = 0.55 + 0.45 * np.clip(np.sin(theta - np.pi / 2), 0, 1)   # 下方亮
    ring *= asym
    ring *= 0.75 + 0.25 * fbm(h, w, seed, octaves=3, base=8)
    ring_a = np.clip(ring * 255, 0, 255)
    # 盘内缘热流（贴盘一圈亮线）
    inner = np.clip(1 - np.abs(r - disk_r) / 3.0, 0, 1) * 200
    rgb = np.zeros((h, w, 3))
    warm = np.array([255, 176, 92], dtype=np.float64) / 255.0
    hot = np.array([255, 226, 170], dtype=np.float64) / 255.0
    glow_rgb = np.array([210, 130, 60], dtype=np.float64) / 255.0
    ring_rgb = (warm[None, None, :] * (1 - ring[..., None] * 0.4)
                + hot[None, None, :] * (ring[..., None] * 0.4))
    inner_rgb = hot[None, None, :] * (inner[..., None] / 255.0)
    glow_full = glow_rgb[None, None, :] * (glow[..., None] / 36.0)
    rgb = ring_rgb + inner_rgb + glow_full
    alpha = ring_a + inner + glow
    # 黑盘（不透明，压掉所有盘内内容）
    disk = r <= disk_r
    rgb[disk] = 0
    alpha[disk] = 255
    return save(oid, rgb, alpha)


# ---------------------------------------------------------------- 星云
def nebula_cloud(oid, seed, stops, core=True, ring=None, arc=None,
                 lobes=None, dark_horse=False):
    h = w = SIZE
    f = fbm(h, w, seed, octaves=6, base=3)
    f2 = fbm(h, w, seed + 4242, octaves=5, base=6)
    # 对比度：阈值取噪声均值上方 0.3σ 处，再 ×3 拉伸——云体 alpha 130~235
    field = np.clip((f * 0.8 + f2 * 0.5 - 0.46) * 3.0, 0, 1) ** 1.2
    rgb = colorize(field, stops)
    alpha = field * 235
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    dx, dy = xx - w / 2, yy - h / 2
    r = np.hypot(dx, dy) / (w / 2)
    th = np.arctan2(dy, dx)

    if core:
        g = np.exp(-(r / 0.16) ** 2)
        rgb += (np.array([255, 246, 235], dtype=np.float64) / 255.0)[None, None, :] * g[..., None] * 0.9
        alpha += g * 120
    if ring:                                    # 环状（行星状/玫瑰星云）
        r0, r1, col = ring
        band = np.clip(1 - np.abs(r - r0) / ((r1 - r0) / 2), 0, 1) ** 1.5
        rgb = rgb * (1 - band[..., None] * 0.85) + (np.array(col)[None, None, :] / 255.0) * band[..., None] * 0.85
        alpha = np.clip(alpha + band * 200, 0, 255)
    if arc:                                     # 圆弧（巴纳德环）
        r0, thick, span, col = arc
        a0, a1 = span
        in_ang = (((th - a0) % (2 * np.pi)) <= (a1 - a0))
        band = np.clip(1 - np.abs(r - r0) / (thick / 2), 0, 1) ** 1.8 * in_ang
        rgb = rgb * (1 - band[..., None] * 0.8) + (np.array(col)[None, None, :] / 255.0) * band[..., None] * 0.8
        alpha = np.clip(alpha + band * 190, 0, 255)
    if lobes:                                   # 双极瓣（M2-9）
        (cx1, cy1, rx1, ry1, cx2, cy2, rx2, ry2, col) = lobes
        l1 = np.clip(1 - np.hypot(dx - cx1, dy - cy1) / rx1, 0, 1)
        l2 = np.clip(1 - np.hypot(dx - cx2, dy - cy2) / rx2, 0, 1)
        lobe = np.clip(l1 * 0.9 + l2 * 0.9, 0, 1) ** 1.4
        rgb = rgb * (1 - lobe[..., None] * 0.85) + (np.array(col)[None, None, :] / 255.0) * lobe[..., None] * 0.85
        alpha = np.clip(alpha + lobe * 210, 0, 255)
    if dark_horse:                              # 马头星云：暗剪影 + Hα 背景
        bg = np.clip(f * 1.2 - 0.25, 0, 1) ** 1.4
        rgb = colorize(bg, [(0, (10, 6, 14)), (0.5, (120, 40, 60)), (1, (235, 120, 130))])
        alpha = bg * 230
        # 马头剪影（头 + 口鼻朝左，颈向右下伸）
        head = np.clip(1 - np.hypot((dx + 55) / 105, (dy - 5) / 78), 0, 1)
        snout = np.clip(1 - np.hypot((dx + 145) / 46, (dy + 30) / 30), 0, 1)
        neck = np.clip(1 - np.hypot((dx + 15) / 62, (dy + 45) / 95), 0, 1)
        sil = np.clip(head + snout + neck, 0, 1)
        alpha = alpha * (1 - sil * 0.985)
    # 星点
    lay = starfield(90, h, w, seed + 7)
    la = np.asarray(lay, dtype=np.float64)
    alpha = np.clip(alpha + la[..., 3] * 0.9, 0, 255)
    rgb = rgb * (1 - la[..., 3:4] / 255.0 * 0.9) + la[..., :3] / 255.0 * (la[..., 3:4] / 255.0 * 0.9)
    return save(oid, rgb, alpha)


NEBULA_STYLES = {
    # 粉红发射 + 青绿（猎户座经典三色）
    "m42": dict(stops=[(0, (8, 4, 12)), (0.35, (120, 30, 70)), (0.7, (225, 90, 110)), (1, (255, 220, 200))]),
    # 蓝白 + 粉红丝状（蟹状）
    "m1": dict(stops=[(0, (6, 8, 18)), (0.4, (60, 90, 170)), (0.75, (200, 170, 220)), (1, (255, 235, 240))]),
    # 棕黄尘埃柱 + 青绿
    "m16": dict(stops=[(0, (10, 8, 6)), (0.4, (130, 95, 60)), (0.72, (215, 175, 120)), (1, (255, 240, 210))]),
    # 粉红 + 蓝（三叶星云三色）
    "m20": dict(stops=[(0, (8, 6, 16)), (0.38, (70, 50, 130)), (0.68, (215, 100, 140)), (1, (255, 225, 235))]),
    # 粉红 + 暗带
    "m8": dict(stops=[(0, (10, 6, 10)), (0.4, (140, 45, 80)), (0.72, (230, 110, 130)), (1, (255, 225, 215))]),
    # 玫红玫瑰
    "rosette": dict(stops=[(0, (12, 6, 10)), (0.45, (150, 50, 85)), (0.8, (235, 130, 150)), (1, (255, 225, 225))]),
    # 蜘蛛星云：亮粉白 + 青绿旋纹
    "tarantula": dict(stops=[(0, (8, 12, 14)), (0.35, (40, 120, 120)), (0.65, (200, 140, 160)), (1, (255, 240, 245))]),
}


def draw_nebula(oid, seed):
    st = NEBULA_STYLES.get(oid, dict(stops=[(0, (8, 6, 12)), (0.5, (150, 60, 90)), (1, (255, 220, 210))]))
    kw = dict(stops=st["stops"])
    if oid == "m57":
        kw.update(ring=(0.38, 0.16, (120, 235, 190)), core=False)
    elif oid == "rosette":
        kw.update(ring=(0.40, 0.22, st["stops"][2][1]), core=False)
    elif oid == "ngc7293":
        kw.update(ring=(0.40, 0.20, (210, 120, 80)), core=True)
    elif oid == "m2_9":
        kw.update(lobes=(-150, 0, 120, 78, 150, 0, 120, 78, (235, 140, 70)), core=True)
    elif oid == "barnards_loop":
        kw.update(arc=(0.42, 0.13, (0.35, 4.4), (200, 80, 85)), core=False)
    elif oid == "horsehead":
        kw.update(dark_horse=True)
    else:
        kw.update(core=True)
    return nebula_cloud(oid, seed, **kw)


# ---------------------------------------------------------------- 星系
def draw_galaxy(oid, seed):
    h = w = SIZE
    c = SIZE / 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    dx, dy = xx - c, yy - c
    kind = {
        "milky_way": "spiral", "m31": "spiral", "m33": "spiral", "m51": "spiral",
        "m81": "spiral", "m104": "edge", "ngc1300": "barred",
        "m87": "elliptical", "ic1101": "elliptical",
        "lmc": "irregular", "smc": "irregular", "m82": "cigar",
        "stephens_quintet": "group",
    }.get(oid, "spiral")
    # 侧视星系纵向压扁（m104 草帽 / m82 雪茄）
    qy = {"m104": 0.38, "m82": 0.20}.get(oid, 1.0)
    ry = dy / qy
    r = np.hypot(dx, ry) / (c * 0.92)          # 归一化等效半径
    th = np.arctan2(ry, dx)
    rr = np.maximum(r, 0.04)
    rgb = np.zeros((h, w, 3))
    alpha = np.zeros((h, w))
    arm_col = np.array([170, 195, 255]) / 255.0      # 旋臂蓝白
    core_col = np.array([255, 238, 195]) / 255.0     # 核球黄白
    hii_col = np.array([255, 150, 170]) / 255.0      # 恒星形成区粉红

    def ang_dist(a, b):
        return np.abs(((a - b + np.pi) % (2 * np.pi)) - np.pi)

    if kind in ("spiral", "barred", "edge"):
        # 指数盘 + 双臂对数螺线 + 核球 + 尘埃暗带 + HII 云气
        if kind == "edge":
            # 侧视（草帽星系）：大核球 + 薄盘，暖黄色，中央尘埃带
            disk = np.exp(-rr / 0.5) * 1.35
            bulge = np.exp(-(rr / 0.22) ** 2) * 1.35
            arm = np.zeros((h, w))
        else:
            disk = np.exp(-rr / 0.42)
            bulge = np.exp(-(rr / 0.14) ** 2)
            pitch = 0.62
            base = np.log(rr) / pitch               # 螺线角位置 θ = ln(r)/pitch
            d1 = ang_dist(th, base)
            d2 = ang_dist(th, base + np.pi)         # 第二条臂（相差 180°）
            arm = np.maximum(np.exp(-(d1 / 0.26) ** 2),
                             np.exp(-(d2 / 0.26) ** 2)) * np.exp(-rr / 0.6)
        if kind == "barred":                        # 中央棒
            bar = np.exp(-(ry / 26.0) ** 2) * np.exp(-(np.abs(dx) / 110.0) ** 2)
            disk = disk + bar * 0.9
        bulge = np.exp(-(rr / 0.14) ** 2)
        dust = fbm(h, w, seed + 31, octaves=4, base=6)
        clouds = np.clip(fbm(h, w, seed + 77, octaves=6, base=4) - 0.5, 0, 1) * 2.2
        bright = disk * 0.5 + arm * 0.95 + bulge * 1.1 + clouds * 0.4
        bright *= (1 - 0.5 * np.clip(dust - 0.55, 0, 1))
        bright = np.clip(bright, 0, 1.5) / 1.5
        if kind == "edge":
            # 侧视配色：核球/盘以暖黄为主（老年星族），旋臂蓝仅少量
            rgb = (core_col[None, None, :] * np.clip(bulge * 1.8, 0, 1)[..., None]
                   + core_col[None, None, :] * np.clip(disk, 0, 1)[..., None] * 0.75
                   + arm_col[None, None, :] * np.clip(disk, 0, 1)[..., None] * 0.25)
            rgb = rgb / np.clip(rgb.max(), 0.75, 2.0)
            alpha = bright * 255
            lane = np.exp(-(dy / (c * 0.05)) ** 2)      # 中央尘埃带
            alpha = alpha * (1 - 0.55 * lane)
        else:
            arm_w = np.clip(arm * 2.0, 0, 1)
            bulge_w = np.clip(bulge * 2.2, 0, 1)
            disk_w = np.clip(disk, 0, 1) * 0.45
            hii_w = np.clip(clouds - 0.5, 0, 1) * arm_w
            rgb = (arm_col[None, None, :] * arm_w[..., None]
                   + core_col[None, None, :] * bulge_w[..., None]
                   + arm_col[None, None, :] * disk_w[..., None]
                   + hii_col[None, None, :] * hii_w[..., None])
            rgb = rgb / np.clip(rgb.max(), 0.75, 2.0)
            alpha = bright * 255
    elif kind == "elliptical":
        prof = np.exp(-(rr / 0.36) ** 0.25)         # de Vaucouleurs-ish
        col = np.array([255, 232, 185]) / 255.0
        rgb = col[None, None, :] * prof[..., None]
        alpha = prof * 250
        if oid == "ic1101":                         # 极大漫晕
            halo = np.exp(-(rr / 0.9) ** 0.6) * 0.4
            rgb = rgb + col[None, None, :] * halo[..., None] * 0.5
            alpha = np.clip(alpha + halo * 130, 0, 255)
    elif kind == "cigar":                           # M82 侧视雪茄 + 星暴红丝
        el = np.exp(-(dx / (c * 0.72)) ** 2 - (ry / (c * 0.16)) ** 2)
        fil = np.clip(fbm(h, w, seed + 5, octaves=5, base=5) - 0.45, 0, 1) * el * 1.6
        rgb = ((np.array([255, 240, 220]) / 255.0)[None, None, :] * el[..., None] * 0.8
               + (np.array([235, 115, 95]) / 255.0)[None, None, :] * fil[..., None])
        alpha = np.clip((el * 0.85 + fil * 0.8) * 255, 0, 255)
    elif kind == "irregular":
        f = fbm(h, w, seed + 13, octaves=5, base=4)
        field = np.clip((f - 0.42) * 2.2, 0, 1) ** 1.4
        bar = np.exp(-(ry / 22.0) ** 2) * np.exp(-(np.abs(dx) / 110.0) ** 2)
        field = np.clip(field + bar * 0.6, 0, 1.2) / 1.2
        rgb = colorize(field, [(0, (25, 35, 65)), (0.5, (140, 165, 215)), (1, (255, 245, 230))])
        alpha = field * 235
    elif kind == "group":                           # 斯蒂芬五重
        lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        spots = [(-190, -60, 26, (255, 225, 170)), (-80, 40, 30, (255, 215, 150)),
                 (60, -70, 24, (255, 230, 180)), (170, 30, 28, (255, 220, 160)),
                 (20, 130, 16, (170, 200, 255))]
        for (sx, sy, sr, col) in spots:
            galaxy_blob(d, c + sx, c + sy, sr * 1.6, sr, col, 235)
            galaxy_blob(d, c + sx, c + sy, sr * 0.7, sr * 0.5, (255, 255, 240), 200)
        arr = np.asarray(lay, dtype=np.float64)
        rgb = arr[..., :3] / 255.0
        alpha = arr[..., 3]
    # 统一加星点
    lay = starfield(90 if kind != "group" else 60, h, w, seed + 3, rmax=1.3, rmin=0.5)
    la = np.asarray(lay, dtype=np.float64)
    wgt = la[..., 3:4] / 255.0
    rgb = rgb * (1 - wgt * 0.85) + la[..., :3] / 255.0 * wgt * 0.85
    alpha = np.clip(alpha + la[..., 3] * 0.85, 0, 255)
    return save(oid, rgb, alpha)


# ---------------------------------------------------------------- 星团
def draw_cluster(oid, seed):
    h = w = SIZE
    kind = "globular" if oid in ("m13", "m22", "omega_cen") else \
           "massive" if oid == "r136" else "open"
    rng = np.random.default_rng(seed)
    n = {"globular": 2600, "open": 560, "massive": 300}[kind]
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if kind == "open":
        # 疏散星团：淡暖光晕 + 松散星点（毕星团这类近距离星团肉眼就是一摊星光）
        f = fbm(h, w, seed, octaves=4, base=3)
        halo = np.clip(np.exp(-(np.hypot(*np.mgrid[0:h, 0:w].astype(np.float64)
                                        - h / 2) / (h * 0.40)) ** 2) * (0.5 + f * 0.5), 0, 1)
        bg = np.zeros((h, w, 4))
        bg[..., :3] = np.array([215, 205, 185]) / 255.0 * halo[..., None]
        bg[..., 3] = halo * 85
        lay = Image.fromarray(bg.astype(np.uint8), "RGBA")
        d = ImageDraw.Draw(lay)
    elif kind == "globular":
        # 星云状弥散背景（球状星团的远星糊成一片）
        f = fbm(h, w, seed, octaves=4, base=3)
        halo = np.clip(np.exp(-(np.hypot(*np.mgrid[0:h, 0:w].astype(np.float64)
                                        - h / 2) / (h * 0.34)) ** 2) * (0.5 + f * 0.5), 0, 1)
        bg = np.zeros((h, w, 4))
        bg[..., :3] = np.array([235, 225, 200]) / 255.0 * halo[..., None]
        bg[..., 3] = halo * 110
        lay = Image.fromarray(bg.astype(np.uint8), "RGBA")
        d = ImageDraw.Draw(lay)
    elif kind == "massive":
        f = fbm(h, w, seed, octaves=5, base=3)
        halo = np.clip(np.exp(-(np.hypot(*np.mgrid[0:h, 0:w].astype(np.float64)
                                        - h / 2) / (h * 0.30)) ** 2) * (0.4 + f * 0.6), 0, 1)
        bg = np.zeros((h, w, 4))
        bg[..., :3] = np.array([200, 160, 200]) / 255.0 * halo[..., None] * 0.8
        bg[..., 3] = halo * 120
        lay = Image.fromarray(bg.astype(np.uint8), "RGBA")
        d = ImageDraw.Draw(lay)
    for _ in range(n):
        # 径向分布：中心浓、外围疏（P(r) ∝ r）
        rr = (rng.random() ** (0.62 if kind == "globular" else 0.85)) * (h * (0.46 if kind != "open" else 0.48))
        ang = rng.random() * 2 * np.pi
        x, y = h / 2 + rr * np.cos(ang), h / 2 + rr * np.sin(ang)
        if not (2 < x < w - 2 and 2 < y < h - 2):
            continue
        if kind == "globular":
            b = 110 + rng.random() * 145
            col = (int(b), int(b * 0.97), int(b * 0.88))
            rad = 0.6 + rng.random() * 1.5
        elif kind == "massive":
            b = 160 + rng.random() * 95
            col = (int(b * 0.85), int(b * 0.9), int(b))
            rad = 0.8 + rng.random() * 2.0
        else:
            blue = rng.random() < 0.4
            b = 150 + rng.random() * 105
            col = (int(b * 0.8), int(b * 0.9), int(b)) if blue else (int(b), int(b * 0.95), int(b * 0.8))
            rad = 0.7 + rng.random() * 1.6
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=col + (255,))
    if kind == "massive":                          # R136a1 级别的超亮星
        for _ in range(7):
            ang = rng.random() * 2 * np.pi
            rr = rng.random() * h * 0.06
            x, y = h / 2 + rr * np.cos(ang), h / 2 + rr * np.sin(ang)
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 255, 255, 255))
    arr = np.asarray(lay, dtype=np.float64)
    rgb, alpha = arr[..., :3] / 255.0, arr[..., 3]
    return save(oid, rgb, alpha)


# ---------------------------------------------------------------- 大尺度结构
def draw_structure(oid, seed):
    h = w = SIZE
    c = SIZE / 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    dx, dy = xx - c, yy - c
    r = np.hypot(dx, dy) / (c * 0.95)
    th = np.arctan2(dy, dx)
    rgb = np.zeros((h, w, 3))
    alpha = np.zeros((h, w))
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)

    if oid == "local_group":
        spots = [(0, 0, 30), (-120, -70, 22), (150, 60, 16), (70, -150, 13),
                 (-160, 90, 12), (200, -120, 10), (-60, 170, 10), (110, 150, 9)]
        for (sx, sy, sr) in spots:
            galaxy_blob(d, c + sx, c + sy, sr * 1.5, sr, (255, 230, 180), 230)
        for i in range(40):
            x, y = rng_pt(seed + i)
            galaxy_blob(d, x, y, 4 + (i % 3), 3 + (i % 3), (220, 210, 230), 170)
    elif oid == "virgo_cluster":
        for i in range(150):
            x, y = rng_pt(seed + i * 3)
            rad = 2.5 + (i % 4)
            galaxy_blob(d, x, y, rad * 1.5, rad, (255, 225, 175), 200)
        galaxy_blob(d, c + 40, c - 20, 34, 22, (255, 245, 220), 240)   # M87
    elif oid == "laniakea":
        # 宇宙网：几条长丝 + 节点
        for k in range(7):
            pts = []
            for t in np.linspace(0, 1, 60):
                ang = t * np.pi * 1.6 + k * 0.9
                rr = 60 + 240 * t + 60 * np.sin(t * 9 + k)
                pts.append((c + rr * np.cos(ang), c + rr * np.sin(ang)))
            d.line(pts, fill=(150, 180, 230, 175), width=5)
        for i in range(60):
            x, y = rng_pt(seed + i * 5)
            galaxy_blob(d, x, y, 7, 5, (255, 235, 200), 215)
    elif oid == "great_attractor":
        # 中心致密团 + 向心流线
        for k in range(46):
            ang = k * (2 * np.pi / 46)
            pts = []
            for t in np.linspace(0.18, 0.95, 40):
                rr = t * c * 0.95
                wob = 14 * np.sin(t * 12 + k)
                pts.append((c + rr * np.cos(ang) - wob * np.sin(ang),
                            c + rr * np.sin(ang) + wob * np.cos(ang)))
            d.line(pts, fill=(170, 140, 200, 90), width=2)
        galaxy_blob(d, c, c, 52, 40, (255, 220, 170), 245)
        galaxy_blob(d, c, c, 24, 18, (255, 250, 235), 255)
        for i in range(30):
            x, y = rng_pt(seed + i * 7)
            galaxy_blob(d, x, y, 4, 3, (230, 215, 240), 160)
    elif oid == "hercules_corona_wall":
        # 横贯画面的巨墙
        band = np.clip(1 - np.abs(dy / (c * 0.42)), 0, 1) ** 1.3
        f = fbm(h, w, seed, octaves=6, base=3)
        wall = band * np.clip(f * 1.3 - 0.3, 0, 1)
        rgb = colorize(wall, [(0, (10, 8, 16)), (0.5, (90, 70, 140)), (1, (220, 200, 255))])
        alpha = np.clip(wall * 220, 0, 255)
    elif oid == "cmb":
        # 全天图：椭圆轮廓内红/蓝斑点（约 1e-5 起伏的艺术夸张）
        f = fbm(h, w, seed, octaves=5, base=5)
        f2 = fbm(h, w, seed + 99, octaves=4, base=9)
        mott = np.clip((f - 0.5) * 2.4, -1, 1)
        sky = (np.hypot(dx, dy) / (c * 0.92)) <= 1.0
        cold = np.array([70, 110, 220]) / 255.0
        warm = np.array([230, 90, 70]) / 255.0
        mid = np.array([12, 10, 24]) / 255.0
        pos = np.clip(mott, 0, 1)[..., None]
        rgb = np.where(mott[..., None] >= 0,
                       mid[None, None, :] * (1 - pos) + warm[None, None, :] * pos,
                       mid[None, None, :] * (1 - (-mott[..., None])) + cold[None, None, :] * (-mott[..., None]))
        alpha = sky * (60 + np.abs(mott) * 150)
    elif oid == "observable_universe":
        # 球壳 + 内部宇宙网
        sph = np.clip(1 - r, 0, 1)
        f = fbm(h, w, seed, octaves=5, base=4)
        web = np.clip(f - 0.48, 0, 1) ** 1.4
        rgb = colorize(web, [(0, (8, 6, 18)), (0.6, (70, 60, 130)), (1, (200, 190, 255))])
        rgb += (np.array([120, 160, 255]) / 255.0)[None, None, :] * (sph[..., None] * 0.10)
        alpha = np.clip(web * 190 + sph * 26, 0, 255)
        edge = np.clip(1 - np.abs(r - 0.97) / 0.06, 0, 1)
        rgb += (np.array([150, 180, 255]) / 255.0)[None, None, :] * (edge[..., None] * 0.5)
        alpha = np.clip(alpha + edge * 120, 0, 255)

    if oid in ("local_group", "virgo_cluster", "laniakea", "great_attractor"):
        la = np.asarray(lay, dtype=np.float64)
        wgt = la[..., 3:4] / 255.0
        rgb = rgb * (1 - wgt) + la[..., :3] / 255.0 * wgt
        alpha = np.clip(alpha + la[..., 3], 0, 255)
    lay2 = starfield(110, h, w, seed + 11)
    la2 = np.asarray(lay2, dtype=np.float64)
    wgt2 = la2[..., 3:4] / 255.0
    rgb = rgb * (1 - wgt2 * 0.8) + la2[..., :3] / 255.0 * wgt2 * 0.8
    alpha = np.clip(alpha + la2[..., 3] * 0.8, 0, 255)
    return save(oid, rgb, alpha)


def rng_pt(seed):
    rng = np.random.default_rng(seed * 31 + 7)
    return rng.random() * SIZE, rng.random() * SIZE


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="已存在贴图也重新生成")
    ap.add_argument("--ids", default="", help="只生成这些 id（逗号分隔）")
    args = ap.parse_args()
    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    only = set(args.ids.split(",")) if args.ids else None
    made, skip = [], []
    for o in data["objects"]:
        oid, cat = o["id"], o["category"]
        if cat not in ("black_hole", "nebula", "galaxy", "cluster", "structure"):
            continue
        if only and oid not in only:
            continue
        dst = PLANET_DIR / f"{oid}.webp"
        if dst.exists() and not args.force:
            skip.append(oid)
            continue
        seed = abs(hash(oid)) % (2 ** 31)
        if cat == "black_hole":
            draw_blackhole(oid, seed)
        elif cat == "nebula":
            draw_nebula(oid, seed)
        elif cat == "galaxy":
            draw_galaxy(oid, seed)
        elif cat == "cluster":
            draw_cluster(oid, seed)
        else:
            draw_structure(oid, seed)
        made.append(oid)
    print(f"生成 {len(made)} 张：{', '.join(made)}")
    if skip:
        print(f"跳过已存在 {len(skip)} 张（--force 可重制）：{', '.join(skip)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
