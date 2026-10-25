# AI 恒星图后处理 v2：光球边缘检测(径向剖面最陡下降) → 质心居中裁方(本体直径=画布70%)
#   → 水印涂黑 → 亮度alpha+标准光晕 → 600 webp，保证 measureSphere sf=0.5
import numpy as np
from PIL import Image

SRC = {
    "betelgeuse": r"C:/Users/99432/code/WorkBuddy_workspace/generated-images/doubao_betelgeuse.png",
    "vega": r"C:/Users/99432/code/WorkBuddy_workspace/generated-images/doubao_vega.png",
    "rigel": r"C:/Users/99432/code/WorkBuddy_workspace/generated-images/doubao_rigel.png",
}
OUT = "docs/assets/planets/"
SIZE, R_BODY = 600, 210.0
TARGET_FRAC = 2 * R_BODY / SIZE  # 本体直径占画布 70%

yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
r = np.sqrt((xx - SIZE / 2 + 0.5) ** 2 + (yy - SIZE / 2 + 0.5) ** 2)
# 标准光晕 alpha（与程序化版一致，保证 measureSphere sf=0.5）
t_aura = np.clip((r - 200.0) / 100.0, 0.0, 1.2)
aura = 45.0 + 210.0 * np.clip(1.0 - t_aura, 0, 1) ** 1.8
aura = np.minimum(aura, 255.0)
aura[r > 300] *= np.clip((345.0 - r[r > 300]) / 45.0, 0, 1)


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def measure_sf(a):
    lo_i, hi_i = 0.0, SIZE / 2

    def cover(R):
        m = (xx - SIZE / 2 + 0.5) ** 2 + (yy - SIZE / 2 + 0.5) ** 2 <= R * R
        return (a[m] >= 40).mean() if m.any() else 0

    for _ in range(10):
        mid = (lo_i + hi_i) / 2
        if cover(mid) >= 0.92:
            lo_i = mid
        else:
            hi_i = mid
    return lo_i / SIZE


def detect_body(a0):
    """返回 (cx, cy, body_r)：质心 + 光球硬边缘半径（径向剖面最陡下降）"""
    H, W = a0.shape[:2]
    mx = a0.max(axis=2)
    # 背景电平：四周边框环中位数
    ring = np.concatenate([mx[:8].ravel(), mx[-8:].ravel(), mx[:, :8].ravel(), mx[:, -8:].ravel()])
    bg = float(np.median(ring))
    thr = max(30.0, bg + 15.0)
    mask = mx >= thr
    tot = mask.sum()
    if tot < 1000:
        raise ValueError("bright mask too small (%d px)" % tot)
    ys, xs = np.nonzero(mask)
    cx, cy = float(xs.mean()), float(ys.mean())  # 质心（暗斑不影响，质心由亮区主导）
    yyw, xxw = np.mgrid[0:H, 0:W].astype(np.float32)
    rw = np.sqrt((xxw - cx) ** 2 + (yyw - cy) ** 2)
    # 径向剖面：2px bin 的 mx 均值
    rmax_search = min(cx, cy, W - cx, H - cy) - 2
    nb = int(rmax_search // 2)
    idx = np.clip((rw / 2).astype(np.int32), 0, nb)
    prof = np.bincount(idx.ravel(), weights=mx.ravel(), minlength=nb + 1)
    cnt = np.bincount(idx.ravel(), minlength=nb + 1)
    prof = np.where(cnt > 0, prof / np.maximum(cnt, 1), 0.0)[: nb + 1]
    # 轻度平滑
    k = np.array([1, 2, 3, 2, 1], dtype=np.float32)
    k /= k.sum()
    ps = np.convolve(prof, k, mode="same")
    # 平台电平：r=40~80 处中位数（盘内）
    lo_i, hi_i = 20, min(40, nb)
    plateau = float(np.median(ps[lo_i:hi_i])) if hi_i > lo_i else float(ps[20])
    # 光球边缘 = 最陡 8px 下降，且下降起点仍在平台 40% 以上
    search_lo, search_hi = int(nb * 0.25), int(nb * 0.85)
    best_r, best_drop = -1, 0.0
    for rr in range(search_lo, min(search_hi, nb - 8)):
        drop = ps[rr] - ps[rr + 8]
        if ps[rr] > plateau * 0.4 and drop > best_drop:
            best_drop, best_r = drop, rr
    if best_r < 0 or best_drop < plateau * 0.15:
        # 兜底：半电平穿越
        below = np.nonzero(ps[search_lo:] < plateau * 0.5)[0]
        best_r = search_lo + int(below[0]) if len(below) else int(nb * 0.45)
    return cx, cy, float(best_r * 2), thr, bg  # bin 宽2px → 半径 = bin*2


def blackout_watermark(a0, W):
    # 右下角 15%×16% 方块涂黑（角部为暗太空，无缝；后续 alpha 处理使其透明）
    a0[int(W * 0.84):, int(W * 0.85):] = 0
    return a0


for sid, path in SRC.items():
    im = Image.open(path).convert("RGB")
    W = im.size[0]
    a0 = np.asarray(im).astype(np.float32)
    a0 = blackout_watermark(a0, W)  # 先去水印再检测/裁切
    cx, cy, body_r, thr, bg = detect_body(a0)
    # 圆外清理：1.08R 以外全部涂黑（用户要求只要圆形，辉光统一交给标准 aura）
    yy0, xx0 = np.mgrid[0:a0.shape[0], 0:a0.shape[1]].astype(np.float32)
    cen0 = np.sqrt((xx0 - cx) ** 2 + (yy0 - cy) ** 2)
    a0[cen0 > body_r * 1.08] = 0
    side = int(round(2 * body_r / TARGET_FRAC))
    # 目标裁窗可能超出原图 → 用黑边 padding 容纳，保证本体精确占 70%
    pad = side // 2 + 4
    canvas = np.zeros((W + 2 * pad, W + 2 * pad, 3), dtype=np.float32)
    canvas[pad:pad + W, pad:pad + W] = a0
    cx += pad; cy += pad
    x0 = int(round(cx - side / 2)); y0 = int(round(cy - side / 2))
    x0 = max(0, min(x0, canvas.shape[1] - side))
    y0 = max(0, min(y0, canvas.shape[0] - side))
    crop = Image.fromarray(canvas[y0:y0 + side, x0:x0 + side].astype(np.uint8)).resize((SIZE, SIZE), Image.LANCZOS)
    clamped = side > W
    ph = np.asarray(crop).astype(np.float32)
    lum = ph.mean(axis=2)

    # 亮度 alpha：本体不透明、辉光按亮度渐变（保留 AI 图的自然辉光层次）
    lum_alpha = smoothstep(lum, 12.0, 48.0) * 255.0
    alpha = np.maximum(lum_alpha, aura)
    # 被抬升区域（自然辉光不足处）用恒星自身边缘色补 RGB
    limb_r = R_BODY * 0.96
    edge_mask = (r > limb_r) & (r < limb_r + 60) & (lum_alpha > 60)
    glow_color = ph[edge_mask].mean(axis=0) if edge_mask.any() else np.array([200, 200, 230], dtype=np.float32)
    fall = 0.5 + 0.5 * np.clip(1.0 - (r - R_BODY) / 110.0, 0, 1)
    fill_rgb = np.clip(glow_color[None, None, :] * (0.6 + 0.4 * fall[..., None]), 0, 255)
    raised = (aura > lum_alpha + 1) & (lum < 60)
    rgb = np.where(raised[..., None], fill_rgb, ph)

    out = np.dstack([rgb.astype(np.uint8), np.clip(alpha, 0, 255).astype(np.uint8)])
    im_out = Image.fromarray(out, "RGBA")
    im_out.save(OUT + sid + ".webp", "WEBP", quality=88)
    print("%s | bg=%.0f thr=%.0f c=(%.0f,%.0f) body_r=%.0f side=%d%s | sf=%.4f" % (
        sid, bg, thr, cx, cy, body_r, side, " CLAMPED!" if clamped else "",
        measure_sf(np.asarray(im_out)[:, :, 3].astype(np.float32))))

# 视觉检查样张（白/深底）
for sid in SRC:
    s = Image.open(OUT + sid + ".webp").convert("RGBA")
    for bgc, suf in [((255, 255, 255, 255), "w"), ((30, 30, 40, 255), "d")]:
        bgp = Image.new("RGBA", s.size, bgc)
        bgp.alpha_composite(s)
        bgp.convert("RGB").save("_ai_%s_%s.png" % (sid, suf))
print("done")
