# 恒星图批量生成器：按 subtype 光谱型着色，600x600 RGBA 透明底
# 设计约束：本体盘 r=210（直径 70%，与行星图一致）；光晕 alpha>=40 延伸到 r=300（内切圆）
#   → measureSphere 实测 sf 恒=0.5，与行星/黑洞等不透明图语义一致，对比比例精确
import json
import hashlib
import numpy as np
from PIL import Image

SIZE = 600
R_BODY = 210.0
OUT = "docs/assets/planets/"

# ---------- 光谱型 → 基色 (RGB) 与纹理参数 ----------
def classify(subtype):
    s = subtype or ""
    # 特殊类别优先
    if "白矮星" in s:
        return {"base": (228, 238, 255), "cells": 90, "gran": 0.04, "blobs": 0, "aura": 1.0, "tag": "WD"}
    if "中子星" in s or "脉冲星" in s or "磁星" in s:
        return {"base": (205, 225, 255), "cells": 100, "gran": 0.03, "blobs": 0, "aura": 1.6, "tag": "NS"}
    if "沃尔夫-拉叶" in s or "WN" in s:
        return {"base": (175, 210, 255), "cells": 80, "gran": 0.05, "blobs": 0, "aura": 1.3, "tag": "WR"}
    if "蓝变星" in s or "LBV" in s:
        return {"base": (185, 212, 255), "cells": 60, "gran": 0.07, "blobs": 0, "aura": 1.35, "tag": "LBV"}
    # 光谱字母（O/B/A/F/G/K/M）
    letter = None
    for ch, ln in (("M", 0.28), ("K", 0.22), ("G", 0.16), ("F", 0.12), ("A", 0.08), ("B", 0.05), ("O", 0.03)):
        idx = s.find(ch)
        if idx >= 0 and idx + 1 < len(s) and s[idx + 1].isdigit():
            letter = ch
            break
    giant = any(k in s for k in ("巨星", "超巨星", "特超巨星"))
    if letter == "M":
        deep = "超巨星" in s
        return {"base": (235, 118, 72) if deep else (255, 152, 98),
                "cells": 10 if deep else 22, "gran": 0.09, "blobs": (0.58, 0.24) if deep else (0.66, 0.16),
                "aura": 1.15 if deep else 0.95, "tag": "M-sg" if deep else "M"}
    if letter == "K":
        return {"base": (255, 198, 140), "cells": 34, "gran": 0.08, "blobs": (0.66, 0.14), "aura": 0.9, "tag": "K"}
    if letter == "G":
        return {"base": (255, 236, 185), "cells": 52, "gran": 0.07, "blobs": 0, "aura": 0.85, "tag": "G"}
    if letter == "F":
        return {"base": (255, 244, 220), "cells": 66, "gran": 0.06, "blobs": 0, "aura": 0.95, "tag": "F"}
    if letter == "A":
        return {"base": (202, 222, 255), "cells": 80, "gran": 0.05, "blobs": 0, "aura": 1.1, "tag": "A"}
    if letter in ("B", "O"):
        return {"base": (158, 192, 255), "cells": 84, "gran": 0.05, "blobs": 0, "aura": 1.25, "tag": "B"}
    # 兜底（食双星等无字母）：食双星 algol B8 / sheliak / almaaz F0 —— 按关键词
    if "食" in s:
        return {"base": (205, 222, 255), "cells": 70, "gran": 0.06, "blobs": 0, "aura": 1.0, "tag": "EB"}
    return {"base": (255, 230, 180), "cells": 52, "gran": 0.07, "blobs": 0, "aura": 0.9, "tag": "def"}


def smooth_noise(rng, cells, size=SIZE):
    """小随机阵列 → 平滑放大（PIL bicubic），返回 0..1"""
    small = rng.random((cells, cells)).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8), "L")
    im = im.resize((size, size), Image.BICUBIC)
    a = np.asarray(im).astype(np.float32) / 255.0
    return (a - a.min()) / (a.max() - a.min() + 1e-9)


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
r = np.sqrt((xx - SIZE / 2 + 0.5) ** 2 + (yy - SIZE / 2 + 0.5) ** 2)

# 光晕 alpha：r=200 处 255 → r=298 处 ~47（全程 >=40，保证 sf=0.5），r>300 羽化到 0
t_aura = np.clip((r - 200.0) / 100.0, 0.0, 1.2)
aura_alpha = 45.0 + 210.0 * np.clip((1.0 - t_aura), 0, 1) ** 1.8
aura_alpha = np.minimum(aura_alpha, 255.0)
aura_alpha[r > 300] *= np.clip((345.0 - r[r > 300]) / 45.0, 0, 1)

# 本体 alpha：r<208 全不透明，208-216 过渡
body_alpha = 255.0 * smoothstep(216.0 - r, -2.0, 6.0)

with open("docs/data/astro.json", encoding="utf-8") as f:
    d = json.load(f)
stars = [o for o in d["objects"] if o["category"] == "star" and o["id"] != "sun"]

made = 0
for o in stars:
    spec = classify(o.get("subtype"))
    seed = int(hashlib.md5(o["id"].encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    base = np.array(spec["base"], dtype=np.float32)

    gran = smooth_noise(rng, spec["cells"])
    bright = 1.0 + spec["gran"] * (gran - 0.5) * 2.0
    # 对流斑块（M/K 型）：双倍频叠加更自然
    if spec["blobs"]:
        lo_t, scale = spec["blobs"]
        n_low = smooth_noise(rng, max(6, spec["cells"] // 4))
        n_fine = smooth_noise(rng, spec["cells"])
        blobs = 0.6 * n_low + 0.4 * n_fine
        blob_mask = smoothstep(blobs, lo_t, lo_t + 0.14)
        bright *= 1.0 - scale * blob_mask
    # 临边昏暗
    rn = np.clip(r / R_BODY, 0, 1.4)
    limb = np.clip(1.0 - 0.5 * rn ** 2.5, 0.42, 1.0)
    limb[r > R_BODY] = 0.42
    # 核心增白
    core = 0.35 * (1.0 - np.clip(r / R_BODY, 0, 1) ** 2)
    disk_rgb = np.clip(base[None, None, :] * (bright * limb)[..., None]
                       + 255.0 * core[..., None] * 0.55, 0, 255)
    # 光晕颜色：基色提亮，随半径衰减
    fall = 0.45 + 0.55 * np.clip(1.0 - (r - R_BODY) / 110.0, 0, 1)
    glow_rgb = np.clip(base[None, None, :] * 1.12 * fall[..., None], 0, 255)

    use_body = (body_alpha >= aura_alpha)
    alpha = np.where(use_body, body_alpha, aura_alpha)
    rgb = np.where(use_body[..., None], disk_rgb, glow_rgb)
    # 光晕强度整体缩放（NS/WR/LBV 更亮）
    a_scale = min(1.0, spec["aura"])
    alpha = np.where(use_body, body_alpha, aura_alpha * a_scale)

    out = np.dstack([rgb.astype(np.uint8), np.clip(alpha, 0, 255).astype(np.uint8)])
    Image.fromarray(out, "RGBA").save(OUT + o["id"] + ".webp", "WEBP", quality=88)
    made += 1
print("generated", made, "star images")

# ---------- 太阳：保留真实纹理，仅补光晕使实测 sf=0.5 ----------
p = OUT + "sun.webp"
sun = Image.open(p).convert("RGBA")
a = np.asarray(sun).astype(np.float32)
rgb_old, al_old = a[:, :, :3], a[:, :, 3]
sun_glow = np.array([255.0, 130.0, 60.0], dtype=np.float32)
new_alpha = np.maximum(al_old, aura_alpha)
raised = aura_alpha > al_old + 1
fall = 0.5 + 0.5 * np.clip(1.0 - (r - R_BODY) / 110.0, 0, 1)
glow_rgb = np.clip(sun_glow[None, None, :] * fall[..., None], 0, 255)
rgb_new = np.where(raised[..., None], glow_rgb, rgb_old)
out = np.dstack([rgb_new.astype(np.uint8), np.clip(new_alpha, 0, 255).astype(np.uint8)])
Image.fromarray(out, "RGBA").save(p, "WEBP", quality=90)
print("sun.webp aura-tuned")

# ---------- 验证：离线复刻 measureSphere（alpha>=40, 92% 覆盖, 二分） ----------
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

for sid in ["sun", "vega", "betelgeuse", "uy_scuti", "sirius_b", "crab_pulsar", "proxima_centauri"]:
    print("sf(%s) = %.4f (期望 0.5)" % (sid, measure_sf(OUT + sid + ".webp")))

# ---------- 视觉检查样张 ----------
for sid, bgcolor, name in [("vega", (255, 255, 255, 255), "_star_vega_w.png"),
                           ("betelgeuse", (255, 255, 255, 255), "_star_betelgeuse_w.png"),
                           ("uy_scuti", (30, 30, 40, 255), "_star_uy_scuti_d.png"),
                           ("crab_pulsar", (30, 30, 40, 255), "_star_crab_d.png"),
                           ("sun", (30, 30, 40, 255), "_star_sun_d.png"),
                           ("sun", (255, 255, 255, 255), "_star_sun_w.png")]:
    s = Image.open(OUT + sid + ".webp").convert("RGBA")
    bgp = Image.new("RGBA", s.size, bgcolor)
    bgp.alpha_composite(s)
    bgp.convert("RGB").save(name)
print("check images written")
