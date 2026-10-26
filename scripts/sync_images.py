#!/usr/bin/env python3
"""sync_images.py — 通用图片编排（AI 编排层的出图入口）。

给定 astro.json，按 category 路由到对应生成器，保证每个对象都有贴图：
  - star / sun    → 复用 build_star_images.py（按 subtype→9 类套 AI 模板）
  - bh/nebula/galaxy/cluster/structure → 复用 gen_bigscale_image.py（程序化，跳过已锁定/NASA 真图）
  - planet/moon/dwarf_planet/asteroid/comet → 新增「固态球体程序化兜底」生成器
                    （之前这类完全没有自动出图路径；NASA 真图由 nasa_image.py 锁定覆盖）

约定（与全站贴图体系一致）：600×600，本体盘占画布 70%（r=210），边缘平滑，圆外全透明，无光晕。
用法：
  python scripts/sync_images.py            # 补齐所有未锁定贴图
  python scripts/sync_images.py --ids a,b  # 只处理指定 id
  python scripts/sync_images.py --force    # 强制重制（含已存在的非锁定图）
  python scripts/sync_images.py --no-gen-star   # 跳过恒星（恒星已齐，省时）
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASTRO = ROOT / "docs" / "data" / "astro.json"
PLANET_DIR = ROOT / "docs" / "assets" / "planets"
SIZE, R_BODY = 600, 210.0
PY = "C:/Users/99432/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

SOLID_CATS = {"planet", "dwarf_planet", "moon", "asteroid", "comet"}
BIGSCALE_CATS = {"black_hole", "nebula", "galaxy", "cluster", "structure"}

# 固态天体兜底配色（RGB）：按类别给一个朴素但可信的球体色，避免千篇一律
SOLID_TINT = {
    "planet": (120, 160, 220),       # 偏蓝（类地/气态通用底）
    "dwarf_planet": (200, 180, 150),  # 偏暖灰（冥王星/谷神星系）
    "moon": (170, 170, 175),          # 灰白（卫星/月球）
    "asteroid": (150, 130, 110),      # 棕灰（岩石小天体）
    "comet": (180, 200, 210),         # 冷灰蓝（冰核）
}


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def body_alpha():
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    rr = np.sqrt((xx - SIZE / 2 + 0.5) ** 2 + (yy - SIZE / 2 + 0.5) ** 2)
    return 255.0 * smoothstep(216.0 - rr, -2.0, 6.0)


def gen_solid_body(oid, cat):
    """程序化固态球体兜底：带临边昏暗 + 左上高光的简单球面，圆外全透明，无光晕。"""
    rgba = body_alpha()
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    nx = (xx - SIZE / 2) / R_BODY
    ny = (yy - SIZE / 2) / R_BODY
    rr = np.sqrt(nx ** 2 + ny ** 2)
    inside = rr <= 1.0
    z = np.sqrt(np.clip(1.0 - rr ** 2, 0, 1))
    lx, ly, lz = -0.5, -0.5, 0.707
    diff = np.clip(-(nx * lx + ny * ly) + z * lz, 0, 1)
    base = np.array(SOLID_TINT.get(cat, (160, 160, 170)), dtype=np.float32)
    shade = np.clip(0.55 + 0.65 * diff, 0.35, 1.25)
    rgb = base[None, None, :] * shade[..., None]
    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = rgba.astype(np.uint8)
    out[~inside] = 0
    img = Image.fromarray(out, "RGBA")
    dst = PLANET_DIR / f"{oid}.webp"
    img.save(dst, "WEBP", quality=88)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="", help="只处理这些 id（逗号分隔）")
    ap.add_argument("--force", action="store_true", help="强制重制已存在的非锁定图")
    ap.add_argument("--no-gen-star", action="store_true", help="跳过恒星（恒星已齐，省时）")
    args = ap.parse_args()

    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    objs = data["objects"]
    by_id = {o["id"]: o for o in objs}
    only = set(args.ids.split(",")) if args.ids else None

    stars, bigscale, solid = [], [], []
    for o in objs:
        oid, cat = o["id"], o["category"]
        if only and oid not in only:
            continue
        locked = o.get("image_locked")
        dst = PLANET_DIR / f"{oid}.webp"
        exists = dst.exists()
        if cat == "star" or oid == "sun":
            if args.no_gen_star:
                continue
            stars.append(oid)
        elif cat in BIGSCALE_CATS:
            if locked and exists:
                continue  # NASA 真图锁定，不覆盖
            bigscale.append(oid)
        elif cat in SOLID_CATS:
            if locked and exists:
                continue  # NASA 真图锁定，不覆盖
            if exists and not args.force:
                continue
            solid.append(oid)
        else:
            print(f"  [skip] {oid}: 类别 {cat} 无生成器")

    made = []
    if stars:
        print(f"恒星（{len(stars)} 颗）→ build_star_images.py ...")
        subprocess.run([PY, "scripts/build_star_images.py"], cwd=str(ROOT), check=False)
    if bigscale:
        print(f"大尺度（{len(bigscale)}）→ gen_bigscale_image.py ...")
        cmd = [PY, "scripts/gen_bigscale_image.py"] + (["--force"] if args.force else [])
        cmd += ["--ids", ",".join(bigscale)]
        subprocess.run(cmd, cwd=str(ROOT), check=False)
    for oid in solid:
        cat = by_id[oid]["category"]
        gen_solid_body(oid, cat)
        made.append(oid)
    print(f"固态兜底生成 {len(made)} 张：{', '.join(made) if made else '(无)'}")
    print("sync_images 完成。恒星/大尺度由对应脚本输出，固态兜底见上行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
