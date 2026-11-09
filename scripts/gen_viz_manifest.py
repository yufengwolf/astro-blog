#!/usr/bin/env python3
"""gen_viz_manifest.py — 生成 viz-manifest.json（3D 可视化覆盖契约）

设计目标（P3）：
- 主站与 3D 仓库解耦：本文件是「哪些天体有 3D 模型、去哪个外链」的**唯一契约**。
- 两个外部 3D 仓库（各自独立部署、独立维护、独立演进）：
    * astro-solar-3d   : 真实三维太阳系（各行星/冥王星专属场景含卫星 + 银河系），
                         覆盖有限但「真 3D 系统」，作为主来源（kind=system）。
    * size-of-space    : 尺寸对比工具（hash 路由 #id），覆盖大量天体（含深空），
                         作为次来源（kind=scale）。
- 每个天体按 [solar-3d, size-of-space] 顺序列出可用 viz；gen_pages 取第一个作默认嵌入，
  多个则渲染来源切换按钮。无任何覆盖的天体不进 manifest → 详情页不渲染 3D 块（优雅降级）。

用法：
    python scripts/gen_viz_manifest.py            # 生成到仓库根 viz-manifest.json
    python scripts/gen_viz_manifest.py --dry-run  # 只打印匹配统计，不落盘

注意：本文件是「机械派生」的契约，修改 3D 仓库覆盖度后重跑即可；如需手动微调，
直接编辑生成的 viz-manifest.json 也行（二者择一，勿长期分叉）。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---- astro-solar-3d（Cloudflare Pages，已部署）----
SOLAR3D_BASE = "https://astro-solar-3d.pages.dev"
# 我库天体 id → astro-solar-3d 的场景 HTML（仅列确有专属/总览场景可锚定的天体）
SOLAR3D_SCENES = {
    "sun": "index.html",          # 太阳系总览（含太阳）
    "mercury": "index.html",      # 太阳系总览
    "venus": "index.html",        # 太阳系总览
    "earth": "earth-moon.html",
    "moon": "earth-moon.html",
    "mars": "mars.html",
    "phobos": "mars.html",
    "deimos": "mars.html",
    "jupiter": "jupiter.html",
    "io": "jupiter.html",
    "europa": "jupiter.html",
    "ganymede": "jupiter.html",
    "callisto": "jupiter.html",
    "saturn": "saturn.html",
    "titan": "saturn.html",
    "enceladus": "saturn.html",
    "mimas": "saturn.html",
    "tethys": "saturn.html",
    "dione": "saturn.html",
    "rhea": "saturn.html",
    "iapetus": "saturn.html",
    "hyperion": "saturn.html",
    "uranus": "uranus.html",
    "titania": "uranus.html",
    "oberon": "uranus.html",
    "ariel": "uranus.html",
    "umbriel": "uranus.html",
    "miranda": "uranus.html",
    "neptune": "neptune.html",
    "triton": "neptune.html",
    "pluto": "pluto.html",
    "charon": "pluto.html",
    "milky_way": "galaxy.html",
}

# ---- size-of-space（hash 路由 #id）----
# 线上部署：上游作者 LegendaCR 的 GitHub Pages 站点（实测可访问，非 404）。
#   我们自己的 fork yufengwolf/size-of-space 也带 deploy.yml，但**尚未在 GitHub 开启 Pages**，
#   故 yufengwolf.github.io/size-of-space 当前 404。要自建部署：去该 fork 的
#   Settings → Pages → Source 选 "GitHub Actions"，再 push main 触发 deploy.yml 即可；
#   部署成功后把本常量改回 https://yufengwolf.github.io/size-of-space。
# 注：本仓库的 SIZEOFSPACE_IDS 取自本地 fork 的 src/data/objects.ts（79 个，与上游一致），
#     因此指向上游站点时 id 全部有效。
SIZEOFSPACE_BASE = "https://legendacr.github.io/size-of-space"
# size-of-space 实际存在的对象 id（取自 src/data/objects.ts）
SIZEOFSPACE_IDS = {
    "67p", "alcyoneus", "aldebaran", "andromeda", "antares", "arcturus", "barnard68",
    "bennu", "betelgeuse", "bootes", "catseye", "ceres", "charon", "crab", "deimos",
    "deneb", "eagle", "earth", "earthmoon", "earthorbit", "enceladus", "europa",
    "ganymede", "gould", "halley", "heliosphere", "herculeswall", "hyperion", "ic1101",
    "io", "jupiter", "jupiterorbit", "laniakea", "lmc", "localgroup", "m87", "malin1",
    "mars", "mathilde", "mercury", "mercuryorbit", "milkyway", "moon", "neptune",
    "neutron", "omegacen", "oort", "orion", "phobos", "pillars", "pluto", "pollux",
    "proxima", "radcliffe", "rigel", "ring", "ryugu", "saturn", "sgra", "sirius",
    "siriusb", "sloanwall", "smc", "solarsystem", "stephenson218", "sun", "tarantula",
    "titan", "ton618", "trappist1", "universe", "uranus", "uyscuti", "vega", "venus",
    "vesta", "virgo", "virgosc", "vycma",
}
# 我库 id → size-of-space id 的非精确映射（其余精确同名直接命中）
SIZEOFSPACE_ALIASES = {
    "halley": "67p",
    "m31": "andromeda",
    "sgr_a_star": "sgra",
    "milky_way": "milkyway",
    "local_group": "localgroup",
    "hercules_corona_wall": "herculeswall",
    "stephenson_2_18": "stephenson218",
    "uy_scuti": "uyscuti",
    "trappist_1": "trappist1",
    "sirius_a": "sirius",
    "sirius_b": "siriusb",
    "virgo_cluster": "virgo",
    "m1": "crab",
    # 同一深空天体、id 命名不同（星云/星系在 size-of-space 用常见名而非梅西耶编号）
    "m42": "orion",
    "m16": "eagle",
    "m57": "ring",
}


def build(data):
    objs = data["objects"]
    my_ids = [o["id"] for o in objs]
    manifest = {}
    n_solar = 0
    n_scale = 0
    for oid in my_ids:
        entries = []
        if oid in SOLAR3D_SCENES:
            entries.append({
                "repo": "solar-3d",
                "kind": "system",
                "title": "真实三维系统",
                "src": f"{SOLAR3D_BASE}/{SOLAR3D_SCENES[oid]}",
            })
            n_solar += 1
        target = oid if oid in SIZEOFSPACE_IDS else SIZEOFSPACE_ALIASES.get(oid)
        if target and target in SIZEOFSPACE_IDS:
            entries.append({
                "repo": "size-of-space",
                "kind": "scale",
                "title": "尺寸对比",
                "src": f"{SIZEOFSPACE_BASE}/#{target}",
            })
            n_scale += 1
        if entries:
            manifest[oid] = entries
    return manifest, n_solar, n_scale


def main():
    dry = "--dry-run" in sys.argv
    data = json.loads((ROOT / "docs" / "data" / "astro.json").read_text(encoding="utf-8"))
    manifest, n_solar, n_scale = build(data)
    total = len(data["objects"])
    covered = len(manifest)
    multi = sum(1 for v in manifest.values() if len(v) > 1)
    out = {
        "version": 1,
        "generated_from": {
            "solar-3d": SOLAR3D_BASE,
            "size-of-space": SIZEOFSPACE_BASE,
            "note": "覆盖度随 3D 仓库演进；改后重跑本脚本或手工编辑此文件",
        },
        "objects": {k: manifest[k] for k in sorted(manifest)},
    }
    if dry:
        print(f"[dry-run] 我库天体总数: {total}")
        print(f"[dry-run] 有 3D 覆盖: {covered} ({covered/total*100:.0f}%)")
        print(f"[dry-run]   ├ solar-3d 命中: {n_solar}")
        print(f"[dry-run]   └ size-of-space 命中: {n_scale}")
        print(f"[dry-run] 多来源(可切换): {multi}")
        return
    (ROOT / "viz-manifest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 viz-manifest.json：{covered}/{total} 天体有 3D 覆盖"
          f"（solar-3d {n_solar} · size-of-space {n_scale} · 多来源 {multi}）")


if __name__ == "__main__":
    main()
