# 恒星图统一构建器（2026-10-26 定稿：恒星按光谱类型统一外观，太阳除外）
#
# 1) 54 颗恒星（不含太阳）：同类型共用一张豆包 AI 代表图（generated-images/type_<tid>.png，
#    居中切圆：本体直径=画布70% → 圆外全透明），个体仅 ±12° 色相微调
#    （黑洞先例：一个类型一个外观）。
# 2) AI 源图缺失 → 程序化着色兜底（TYPE_DEFS.fallback 基色 + 颗粒纹理）。
# 3) 太阳独立处理：模糊压米粒纹理 → 梯度边缘 → 环带筛选 → Kasa 迭代圆拟合锁定日面 limb，
#    以拟合圆心为中心裁切，并只采样 limb 半径的 94%（激进：宁可多切，绝不允许偏移/光晕残留）。
#    输出后用同一拟合反向验证：盘心必须与画布中心重合（±3px）。
#
# 输出：docs/assets/planets/<id>.webp（恒星 + sun），全部 600×600、body_alpha 统一
# smoothstep(216-r,-2,6)，measureSphere sf≈0.375 与 venus 等行星一致。
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from star_types import TYPE_DEFS, map_subtype, hue_offset

SIZE, R_BODY = 600, 210.0
OUT = "docs/assets/planets/"
GEN = r"C:/Users/99432/code/WorkBuddy_workspace/generated-images"
# 太阳底图：优先豆包生成的 type_sun.png；不存在时回退旧图（仅兜底）
SUN_SRC = os.path.join(GEN, "type_sun.png")
if not os.path.exists(SUN_SRC):
    SUN_SRC = os.path.join(GEN, "Photorealistic_astronomy_rende_2026-10-25T14-02-06.png")
SUN_AGGR = 0.94   # 太阳激进采样：只取 limb 半径的 94%
REP_AGGR = 0.97   # 类型代表图保守采样：收敛检测的 2-5% 外扩

yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
rr_c = np.sqrt((xx - SIZE / 2 + 0.5) ** 2 + (yy - SIZE / 2 + 0.5) ** 2)


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# 与行星图（venus_circle.py）完全一致的盘面 alpha：r<=210 全不透明，218 外全透明
BODY_ALPHA = 255.0 * smoothstep(216.0 - rr_c, -2.0, 6.0)


# ---------- 通用：Kasa 迭代圆拟合（锁定 limb） ----------
def kasa_fit(xs, ys):
    A = np.stack([2 * xs, 2 * ys, np.ones_like(xs)], axis=1)
    b = xs * xs + ys * ys
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    a, c, d = float(sol[0]), float(sol[1]), float(sol[2])
    return a, c, float(np.sqrt(max(d + a * a + c * c, 1.0)))


def fit_limb(mx, cx, cy, R0, radii=None):
    """梯度边缘 + 环带筛选 + Kasa 迭代拟合。返回 (cx, cy, R)。"""
    im = Image.fromarray(np.clip(mx, 0, 255).astype(np.uint8), "L")
    g = np.asarray(im.filter(ImageFilter.GaussianBlur(4))).astype(np.float32)
    gy, gx = np.gradient(g)
    gm = np.sqrt(gx * gx + gy * gy)
    H, W = mx.shape
    yyw, xxw = np.mgrid[0:H, 0:W].astype(np.float32)
    R = R0
    for it, gate in enumerate((0.30, 0.18, 0.12)):
        dist = np.sqrt((xxw - cx) ** 2 + (yyw - cy) ** 2)
        ringm = np.abs(dist - R) < gate * R
        ys, xs = np.nonzero(ringm)
        if len(xs) < 200:
            break
        gmv = gm[ys, xs]
        keep = gmv >= np.percentile(gmv, 55)  # 只留强边缘（limb > 米粒纹理）
        xs, ys = xs[keep], ys[keep]
        if len(xs) < 200:
            break
        cx, cy, R = kasa_fit(xs.astype(np.float64), ys.astype(np.float64))
    return cx, cy, R


def limb_offset_on_output(path):
    """在 600×600 成品上反向拟合内容 limb，返回亮盘圆心相对画布中心的偏移 (dx,dy)。"""
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im).astype(np.float32)
    lum = a[:, :, :3].max(axis=2) * (a[:, :, 3] / 255.0)  # alpha 加权：透明区不参与
    cx, cy, R = fit_limb(lum, 300.0, 300.0, 195.0)
    return cx - 300.0, cy - 300.0, R


# ---------- AI 代表图检测与切圆 ----------
def detect_body(a0):
    """质心 + 光球硬边缘半径（径向剖面最陡下降）。返回 (cx, cy, body_r)。"""
    H, W = a0.shape[:2]
    mx = a0.max(axis=2)
    ring = np.concatenate([mx[:8].ravel(), mx[-8:].ravel(), mx[:, :8].ravel(), mx[:, -8:].ravel()])
    bg = float(np.median(ring))
    thr = max(30.0, bg + 15.0)
    mask = mx >= thr
    ys, xs = np.nonzero(mask)
    if mask.sum() < 1000:
        raise ValueError("bright mask too small")
    cx, cy = float(xs.mean()), float(ys.mean())
    yyw, xxw = np.mgrid[0:H, 0:W].astype(np.float32)
    rw = np.sqrt((xxw - cx) ** 2 + (yyw - cy) ** 2)
    nb = int(min(cx, cy, W - cx, H - cy) // 2)
    idx = np.clip((rw / 2).astype(np.int32), 0, nb)
    prof = np.bincount(idx.ravel(), weights=mx.ravel(), minlength=nb + 1)
    cnt = np.bincount(idx.ravel(), minlength=nb + 1)
    prof = np.where(cnt > 0, prof / np.maximum(cnt, 1), 0.0)[: nb + 1]
    k = np.array([1, 2, 3, 2, 1], dtype=np.float32)
    k /= k.sum()
    ps = np.convolve(prof, k, mode="same")
    plateau = float(np.median(ps[20:min(40, nb)])) if nb > 20 else float(ps[20])
    best_r, best_drop = -1, 0.0
    for rr in range(int(nb * 0.25), min(int(nb * 0.85), nb - 8)):
        drop = ps[rr] - ps[rr + 8]
        if ps[rr] > plateau * 0.4 and drop > best_drop:
            best_drop, best_r = drop, rr
    if best_r < 0 or best_drop < plateau * 0.15:
        below = np.nonzero(ps[int(nb * 0.25):] < plateau * 0.5)[0]
        best_r = int(nb * 0.25) + int(below[0]) if len(below) else int(nb * 0.45)
    return cx, cy, float(best_r * 2)


def center_crop_to_size(a0, cx, cy, side):
    """以 (cx,cy) 为中心裁 side×side（黑边 padding 兜底），缩放到 SIZE×SIZE。"""
    H, W = a0.shape[:2]
    pad = side // 2 + 4
    canvas = np.zeros((H + 2 * pad, W + 2 * pad, 3), dtype=np.float32)
    canvas[pad:pad + H, pad:pad + W] = a0
    cx += pad
    cy += pad
    x0 = max(0, min(int(round(cx - side / 2)), canvas.shape[1] - side))
    y0 = max(0, min(int(round(cy - side / 2)), canvas.shape[0] - side))
    crop = Image.fromarray(canvas[y0:y0 + side, x0:x0 + side].astype(np.uint8))
    return np.asarray(crop.resize((SIZE, SIZE), Image.LANCZOS)).astype(np.float32)


def cutout_rep(path):
    """AI 代表图 → 600×600 RGB（盘面居中、本体占 70%），水印涂黑 + 圆外清理。
    中心用 limb 圆拟合精锁定（陡降半径作初值），避免 AI 圆盘本身不居中。"""
    im = Image.open(path).convert("RGB")
    W = im.size[0]
    a0 = np.asarray(im).astype(np.float32)
    a0[int(W * 0.84):, int(W * 0.85):] = 0  # 右下水印
    mx = a0.max(axis=2)
    cx, cy, body_r = detect_body(a0)
    cx, cy, limb_r = fit_limb(mx, cx, cy, body_r)  # 精锁定 limb 圆心
    sample_r = limb_r * REP_AGGR
    yy0, xx0 = np.mgrid[0:a0.shape[0], 0:a0.shape[1]].astype(np.float32)
    a0[np.sqrt((xx0 - cx) ** 2 + (yy0 - cy) ** 2) > limb_r * 1.05] = 0  # 圆外清干净
    side = int(round(2 * sample_r / (2 * R_BODY / SIZE)))
    ph = center_crop_to_size(a0, cx, cy, side)
    print("  rep %-16s c=(%.1f,%.1f) steep_r=%.0f limb_r=%.0f sample=%.0f side=%d" % (
        os.path.basename(path), cx, cy, body_r, limb_r, sample_r, side))
    return ph


def rgba_out(rgb):
    rgb = np.where((BODY_ALPHA > 0)[..., None], rgb, 0)
    return np.dstack([rgb.astype(np.uint8), BODY_ALPHA.astype(np.uint8)])


# ---------- 个体色相微调 ----------
def hue_shift(rgb, deg):
    im = Image.fromarray(rgb.astype(np.uint8), "RGB").convert("HSV")
    h, s, v = im.split()
    hn = (np.asarray(h).astype(np.int32) + int(round(deg * 255.0 / 360.0))) % 256
    out = Image.merge("HSV", (Image.fromarray(hn.astype(np.uint8), "L"), s, v)).convert("RGB")
    return np.asarray(out).astype(np.float32)


# ---------- 程序化兜底（AI 源图缺失时） ----------
def smooth_noise(rng, cells, size=SIZE):
    small = rng.random((cells, cells)).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8), "L")
    im = im.resize((size, size), Image.BICUBIC)
    a = np.asarray(im).astype(np.float32) / 255.0
    return (a - a.min()) / (a.max() - a.min() + 1e-9)


def fallback_disk(base_rgb, seed):
    rng = np.random.default_rng(seed)
    base = np.array(base_rgb, dtype=np.float32)
    gran = smooth_noise(rng, 52)
    bright = 1.0 + 0.07 * (gran - 0.5) * 2.0
    limb = np.clip(1.0 - 0.5 * np.clip(rr_c / R_BODY, 0, 1.4) ** 2.5, 0.42, 1.0)
    limb[rr_c > R_BODY] = 0.42
    core = 0.35 * (1.0 - np.clip(rr_c / R_BODY, 0, 1) ** 2)
    return np.clip(base[None, None, :] * (bright * limb)[..., None] + 255.0 * core[..., None] * 0.55, 0, 255)


# ---------- 太阳：limb 圆拟合 + 激进采样 ----------
def build_sun():
    im = Image.open(SUN_SRC).convert("RGB")
    W = im.size[0]
    a0 = np.asarray(im).astype(np.float32)
    a0[int(W * 0.82):, int(W * 0.84):] = 0  # 右下水印
    mx = a0.max(axis=2)
    # 初始中心/半径：亮区质心 + 覆盖率剖面
    mask = mx >= 60
    ys, xs = np.nonzero(mask)
    cx, cy = float(xs.mean()), float(ys.mean())
    yyw, xxw = np.mgrid[0:W, 0:W].astype(np.float32)
    dist0 = np.sqrt((xxw - cx) ** 2 + (yyw - cy) ** 2)
    nb = int(dist0.max() // 4) + 2
    bidx = np.clip((dist0 / 4).astype(np.int32), 0, nb).ravel()
    tot = np.bincount(bidx, minlength=nb + 1)
    hit = np.bincount(bidx, weights=(mx.ravel() >= 60).astype(np.float64), minlength=nb + 1)
    cov = hit / np.maximum(tot, 1)
    R0, miss = 0, 0
    for i in range(nb + 1):
        if cov[i] >= 0.35:
            R0, miss = i * 4, 0
        else:
            miss += 1
            if R0 > 0 and miss > 10:
                break
    # limb 精锁定
    cx, cy, limb_r = fit_limb(mx, cx, cy, max(R0, W * 0.25))
    sample_r = limb_r * SUN_AGGR  # 激进：多切 6% 边缘，保证无光晕/日珥残留
    side = int(round(2 * sample_r / (2 * R_BODY / SIZE)))
    a0[np.sqrt((xxw - cx) ** 2 + (yyw - cy) ** 2) > limb_r * 1.02] = 0
    ph = center_crop_to_size(a0, cx, cy, side)
    Image.fromarray(rgba_out(ph), "RGBA").save(OUT + "sun.webp", "WEBP", quality=90)
    # 反向验证：成品上重新拟合 limb，圆心必须贴画布中心
    dx, dy, Rv = limb_offset_on_output(OUT + "sun.webp")
    ok = abs(dx) <= 3 and abs(dy) <= 3
    print("sun: 初始c=(%.0f,%.0f) R0=%.0f -> limb c=(%.1f,%.1f) r=%.1f sample=%.0f side=%d"
          % (xs.mean(), ys.mean(), R0, cx, cy, limb_r, sample_r, side))
    print("sun 成品反向拟合: 圆心偏移 dx=%.1f dy=%.1f (R=%.0f) %s" % (dx, dy, Rv, "OK" if ok else "!! OFFSET"))
    return ok


# ---------- sf 离线校验（复刻 measureSphere） ----------
def measure_sf(path):
    a = np.asarray(Image.open(path).convert("RGBA"))[:, :, 3].astype(np.float32)
    lo, hi = 0.0, SIZE / 2

    def cover(R):
        m = (xx - SIZE / 2 + 0.5) ** 2 + (yy - SIZE / 2 + 0.5) ** 2 <= R * R
        return (a[m] >= 40).mean() if m.any() else 0

    for _ in range(10):
        mid = (lo + hi) / 2
        if cover(mid) >= 0.92:
            lo = mid
        else:
            hi = mid
    return lo / SIZE


# ---------- 样张 ----------
def composite(sid, bgc, name, ring=False):
    s = Image.open(OUT + sid + ".webp").convert("RGBA")
    bgp = Image.new("RGBA", s.size, bgc)
    bgp.alpha_composite(s)
    rgb = bgp.convert("RGB")
    if ring:
        d = ImageDraw.Draw(rgb)
        d.ellipse([300 - 210, 300 - 210, 300 + 210, 300 + 210], outline=(0, 255, 80), width=3)
    rgb.save(name)


def montage(ids, name, cell=112, dark=True):
    cols = 6
    rows = (len(ids) + cols - 1) // cols
    bg = (20, 20, 28) if dark else (250, 250, 250)
    fg = (200, 200, 200) if dark else (60, 60, 60)
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 16)), bg)
    dr = ImageDraw.Draw(sheet)
    for i, sid in enumerate(ids):
        im = Image.open(OUT + sid + ".webp").convert("RGBA")
        th = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
        th.alpha_composite(im.resize((cell, cell), Image.LANCZOS))
        x, y = (i % cols) * cell, (i // cols) * (cell + 16)
        sheet.paste(Image.new("RGB", (cell, cell), bg), (x, y), th)
        dr.text((x + 4, y + cell + 1), sid[:18], fill=fg)
    sheet.save(name)
    print("montage ->", name)


# ---------- 主流程 ----------
def main():
    with open("docs/data/astro.json", encoding="utf-8") as f:
        d = json.load(f)
    stars = [o for o in d["objects"] if o["category"] == "star" and o["id"] != "sun"]

    # 1) 类型代表图 → 居中切圆模板
    templates = {}
    for tid in TYPE_DEFS:
        p = os.path.join(GEN, "type_%s.png" % tid)
        if os.path.exists(p):
            templates[tid] = cutout_rep(p)
        else:
            print("  [fallback] 缺少 AI 源图:", p)
    print("templates ready:", ", ".join(templates) or "(none)")

    # 2) 每颗恒星 = 类型模板 + 个体色相微调（或程序化兜底）
    made = 0
    first_of_type = {}
    for o in stars:
        tid = map_subtype(o.get("subtype"))
        if tid in templates:
            rgb = hue_shift(templates[tid], hue_offset(o["id"]))
        else:
            rgb = fallback_disk(TYPE_DEFS[tid]["fallback"], int(o["id"].encode("utf-8").hex()[:8], 16))
        Image.fromarray(rgba_out(rgb), "RGBA").save(OUT + o["id"] + ".webp", "WEBP", quality=88)
        made += 1
        first_of_type.setdefault(tid, o["id"])
    print("star images written:", made)

    # 3) 太阳（独立路径：limb 拟合 + 激进采样）
    sun_ok = build_sun() if os.path.exists(SUN_SRC) else None
    if sun_ok is None:
        print("!! 缺少太阳 AI 原图:", SUN_SRC)

    # 4) 校验：sf 一致性 + 每类首星与太阳的 limb 圆心偏移
    print("--- sf ---")
    for sid in ["sun"] + [first_of_type[t] for t in templates]:
        print("sf(%s) = %.4f" % (sid, measure_sf(OUT + sid + ".webp")))
    print("--- limb 圆心偏移（应 |dx|,|dy| <= 3）---")
    for sid in (["sun"] if sun_ok else []) + [first_of_type[t] for t in templates]:
        dx, dy, R = limb_offset_on_output(OUT + sid + ".webp")
        flag = "OK" if abs(dx) <= 3 and abs(dy) <= 3 else "!! OFFSET"
        print("%-18s dx=%+.1f dy=%+.1f R=%.0f %s" % (sid, dx, dy, R, flag))

    # 5) 样张：太阳深/白底+基准圆、全量拼图（供用户查看）
    if sun_ok:
        composite("sun", (20, 20, 28, 255), "_sun_new_dark.png", ring=True)
        composite("sun", (255, 255, 255, 255), "_sun_new_white.png", ring=True)
    montage(["sun"] + [o["id"] for o in stars], "_stars_all_dark.png")


if __name__ == "__main__":
    main()
