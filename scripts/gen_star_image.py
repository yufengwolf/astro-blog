#!/usr/bin/env python3
"""gen_star_image.py — 程序化生成恒星贴图。

按黑体辐射色（温度 → RGB）生成 600×600 透明发光球体：
  - 本体实心球直径 420px（半径 210px），居中 → sf = 210/600 = 0.35，
    与对比页其它贴图「本体占画布高 70%」约定一致，保证大小对比准确；
  - 中心偏白（热核观感）+ 向边缘 limbdarkening（边缘变暗、显色）；
  - 球体外缘叠加极淡辉光（alpha 峰值 < 40），在深色主题下可见，但不会被
    对比页的球体测量算法（alpha>=40 才算实心）计入，故不影响比例。
太阳等有真实 NASA 影像的恒星默认跳过（只补程序化示意图缺失的恒星）。

用法：python gen_star_image.py [--root DIR] [--force] [--ids a,b,c]
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

SIZE = 600
CORE_R = 210          # 本体半径 px（直径 420，占画布高 70%）
EDGE = 2.0            # 本体边缘抗锯齿过渡 px
GLOW_PEAK = 35        # 辉光峰值 alpha（必须 < 40，避免被比例测量计入）
L_SUN_W = 3.828e26

CAT_COLOR_FALLBACK = (255, 200, 120)   # 缺温度时按类太阳色兜底


def blackbody_rgb(kelvin):
    """Tanner Helland 黑体色近似，返回 0-255 的 (R, G, B)。"""
    t = kelvin / 100.0
    if t <= 66:
        r = 255.0
    else:
        r = 329.698727446 * ((t - 60) ** -0.1332047592)
    if t <= 66:
        g = 99.4708025861 * math.log(t) - 161.1195681661
    else:
        g = 288.1221695283 * ((t - 60) ** -0.0755148492)
    if t >= 66:
        b = 255.0
    elif t <= 19:
        b = 0.0
    else:
        b = 138.5177312231 * math.log(t - 10) - 305.0447927307
    return (max(0.0, min(255.0, r)), max(0.0, min(255.0, g)), max(0.0, min(255.0, b)))


def generate(kelvin):
    kelvin = max(1000, min(40000, kelvin))
    base = np.array(blackbody_rgb(kelvin), dtype=float)
    y, x = np.ogrid[:SIZE, :SIZE]
    dist = np.sqrt((x - SIZE / 2) ** 2 + (y - SIZE / 2) ** 2)
    rn = np.clip(dist / CORE_R, 0.0, 1.0)          # 0 中心 → 1 本体边缘

    # 亮度：中心亮、边缘暗（limb darkening）
    brightness = 1.0 - 0.45 * rn ** 2
    # 中心偏白（热核观感）
    white_mix = (np.clip(1.0 - rn, 0.0, 1.0) ** 2) * 0.5
    rgb = base * brightness[..., None]
    rgb = rgb * (1.0 - white_mix[..., None]) + 255.0 * white_mix[..., None]

    # 本体实心 alpha（2px 抗锯齿过渡），球外为 0
    core_alpha = np.clip((CORE_R - dist) / EDGE, 0.0, 1.0) * 255.0
    # 外层辉光：从本体边缘向外柔和衰减，峰值 < 40
    glow_r = min(CORE_R * 1.5, SIZE / 2.0)
    g = np.clip(1.0 - (dist - CORE_R) / (glow_r - CORE_R), 0.0, 1.0)
    glow_alpha = np.where(dist > CORE_R, g ** 2.2 * GLOW_PEAK, 0.0)

    alpha = np.maximum(core_alpha, glow_alpha)
    img = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    img[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    img[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--force", action="store_true", help="已存在也重新生成（默认太阳等真实图跳过）")
    ap.add_argument("--ids", default=None, help="只生成指定 id（逗号分隔）；默认补全部缺失的恒星")
    args = ap.parse_args()
    root = Path(args.root)
    data = json.loads((root / "docs" / "data" / "astro.json").read_text(encoding="utf-8"))
    assets = root / "docs" / "assets" / "planets"
    assets.mkdir(parents=True, exist_ok=True)

    targets = []
    only = set(args.ids.split(",")) if args.ids else None
    for o in data["objects"]:
        if o.get("category") != "star":
            continue
        oid = o["id"]
        if only and oid not in only:
            continue
        img_rel = o.get("image")
        if not img_rel:
            continue
        # image 字段是相对站根的路径（形如 assets/planets/x.webp），
        # 真实文件位于 docs/ 下；不存在则生成到 docs/assets/planets/
        out = root / "docs" / img_rel if img_rel.endswith(".webp") else assets / f"{oid}.webp"
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and not args.force:
            print(f"跳过（已存在）: {out.name}")
            continue
        targets.append((oid, o, out))

    if not targets:
        print("没有需要生成的恒星贴图。")
        return 0

    for oid, o, out in targets:
        ph = o.get("physical") or {}
        tc = ph.get("mean_temp_c")
        # 恒星的 mean_temp_c 存储为「开尔文减去 273.15」的等效摄氏值
        kelvin = (tc + 273.15) if tc is not None else 5778.0
        im = generate(kelvin)
        im.save(out, "WEBP", lossless=True)
        print(f"已生成: {out.name}  (T≈{kelvin:.0f}K, 色 {tuple(blackbody_rgb(kelvin))})")
    print(f"\n完成，共生成 {len(targets)} 张恒星贴图。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
