# 金星切圆：NASA S91-50688 全盘雷达图 → 圆盘检测 → 70%裁方(padding) → 盘内不透明+标准光晕 → 600 webp sf=0.5
import numpy as np
from PIL import Image

SRC = "_venus_src.jpg"
OUT = "docs/assets/planets/venus.webp"
SIZE, R_BODY = 600, 210.0
TARGET_FRAC = 2 * R_BODY / SIZE

im = Image.open(SRC).convert("RGB")
W = im.size[0]
a0 = np.asarray(im).astype(np.float32)
mx = a0.max(axis=2)

# 圆盘检测：径向剖面最陡下降（与 AI 星同一逻辑）
mask = mx >= 60
ys, xs = np.nonzero(mask)
cx, cy = float(xs.mean()), float(ys.mean())
yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
cen = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
nb = int(min(cx, cy, W - cx, W - cy) // 2)
idx = np.clip((cen / 2).astype(np.int32), 0, nb)
prof = np.bincount(idx.ravel(), weights=mx.ravel(), minlength=nb + 1)
cnt = np.bincount(idx.ravel(), minlength=nb + 1)
prof = np.where(cnt > 0, prof / np.maximum(cnt, 1), 0.0)[: nb + 1]
k = np.array([1, 2, 3, 2, 1], dtype=np.float32); k /= k.sum()
ps = np.convolve(prof, k, mode="same")
best_r, best_drop = -1, 0.0
for rr in range(30, nb - 8):
    drop = ps[rr] - ps[rr + 8]
    if ps[rr] > 40 and drop > best_drop:
        best_drop, best_r = drop, rr
body_r = best_r * 2
print("venus disk: c=(%.0f,%.0f) body_r=%d (img W=%d)" % (cx, cy, body_r, W))

# 裁方（黑边 padding 保证本体精确 70%）
side = int(round(2 * body_r / TARGET_FRAC))
pad = side // 2 + 4
canvas = np.zeros((W + 2 * pad, W + 2 * pad, 3), dtype=np.float32)
canvas[pad:pad + W, pad:pad + W] = a0
cx += pad; cy += pad
x0 = max(0, min(int(round(cx - side / 2)), canvas.shape[1] - side))
y0 = max(0, min(int(round(cy - side / 2)), canvas.shape[0] - side))
crop = Image.fromarray(canvas[y0:y0 + side, x0:x0 + side].astype(np.uint8)).resize((SIZE, SIZE), Image.LANCZOS)
ph = np.asarray(crop).astype(np.float32)

# 标准光晕（与恒星一致 → sf=0.5）
yy2, xx2 = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
r = np.sqrt((xx2 - SIZE / 2 + 0.5) ** 2 + (yy2 - SIZE / 2 + 0.5) ** 2)
t_aura = np.clip((r - 200.0) / 100.0, 0.0, 1.2)
aura = 45.0 + 210.0 * np.clip(1.0 - t_aura, 0, 1) ** 1.8
aura = np.minimum(aura, 255.0)
aura[r > 300] *= np.clip((345.0 - r[r > 300]) / 45.0, 0, 1)

# 盘内不透明（边缘 3px 平滑防锯齿）+ 光晕
disk_alpha = np.clip((R_BODY + 3 - r) * 85.0, 0, 255)  # r<=207 → 255
alpha = np.maximum(disk_alpha, aura)

out = np.dstack([ph.astype(np.uint8), alpha.astype(np.uint8)])
Image.fromarray(out, "RGBA").save(OUT, "WEBP", quality=88)

# 校验 sf（复刻 measureSphere）
def cover(R):
    m = (xx2 - SIZE / 2 + 0.5) ** 2 + (yy2 - SIZE / 2 + 0.5) ** 2 <= R * R
    return (alpha[m] >= 40).mean() if m.any() else 0
lo, hi = 0.0, SIZE / 2
for _ in range(10):
    mid = (lo + hi) / 2
    if cover(mid) >= 0.92: lo = mid
    else: hi = mid
print("venus side=%d body_frac=%.4f sf=%.4f" % (side, body_r / side, lo / SIZE))

# 样张
s = Image.open(OUT).convert("RGBA")
for bgc, suf in [((255, 255, 255, 255), "w"), ((30, 30, 40, 255), "d")]:
    bgp = Image.new("RGBA", s.size, bgc); bgp.alpha_composite(s)
    bgp.convert("RGB").save("_venus_%s.png" % suf)
print("done")
