#!/usr/bin/env python3
"""gen_viz_manifest.py — 生成 viz-manifest.json（3D 可视化覆盖契约）

设计目标（P3，经用户拍板）：
- 主站与 3D 仓库解耦：本文件是「哪些天体有 3D 模型、去哪个外链」的**唯一契约（表格）**。
- 当前**唯一**外部 3D 仓库：astro-solar-3d（Cloudflare Pages，已部署）。
  * size-of-space 暂未纳入：用户尚未把它部署到 CF Pages（fork 带 deploy.yml 但未开 Pages），
    待部署后再在 build() 里加回第二个来源；本文件已为此预留结构。
- **关键架构约束（用户明确）**：
  * 当前仓库只做「消费者」——提供**窗口（iframe）+ 地址（`?view=<id>`）**，
    绝不硬编码「某天体 → 某场景 HTML」。场景选择由外部仓库决定。
  * 因此本文件只输出 `astro-solar-3d.pages.dev/?view=<id>`，把天体 id 透传给外部仓库；
    外部仓库（astro-solar-3d）负责实现「一个地址直接渲染该天体的 3D」——
    这是 astro-solar-3d 的改造需求，在**另一个 chat** 单独提，本仓库不碰。
  * 注意：astro-solar-3d 当前仅把 `?view=<id>` 用作「单页内的取景预设选择器」，
    全局「按 id 路由到对应天体场景」尚未实现；在那之前，详情页 3D 块可能只显示其落地页
    （降级态，属预期，待外部仓库改造后自愈）。

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

# ---- astro-solar-3d（Cloudflare Pages，已部署；本站 3D 唯一来源）----
SOLAR3D_BASE = "https://astro-solar-3d.pages.dev"
# 我库天体 id → astro-solar-3d 已具备内容（场景/模型）的天体集合。
# 当前仓库**不**在此决定具体场景 HTML；只把 id 透传为 `?view=<id>`，
# 由 astro-solar-3d 决定该 id 渲染成什么（地球单独 / 地月系统 / …… 都是外部仓库的事）。
# 集合含义：这些天体在 astro-solar-3d 里有专属或总览场景可锚定。
SOLAR3D_IDS = {
    "sun", "mercury", "venus", "earth", "moon", "mars", "phobos", "deimos",
    "jupiter", "io", "europa", "ganymede", "callisto",
    "saturn", "titan", "enceladus", "mimas", "tethys", "dione", "rhea",
    "iapetus", "hyperion",
    "uranus", "titania", "oberon", "ariel", "umbriel", "miranda",
    "neptune", "triton", "pluto", "charon", "milky_way",
}


def build(data):
    objs = data["objects"]
    my_ids = [o["id"] for o in objs]
    manifest = {}
    n_solar = 0
    for oid in my_ids:
        if oid in SOLAR3D_IDS:
            manifest[oid] = [{
                "repo": "solar-3d",
                "kind": "system",
                "title": "真实三维系统",
                "src": f"{SOLAR3D_BASE}/?view={oid}",
            }]
            n_solar += 1
    return manifest, n_solar


def main():
    dry = "--dry-run" in sys.argv
    data = json.loads((ROOT / "docs" / "data" / "astro.json").read_text(encoding="utf-8"))
    manifest, n_solar = build(data)
    total = len(data["objects"])
    covered = len(manifest)
    out = {
        "version": 1,
        "generated_from": {
            "solar-3d": SOLAR3D_BASE,
            "note": ("当前仅 astro-solar-3d 一个来源（size-of-space 待用户部署 CF Pages 后加回）。"
                     "src 统一为 `?view=<id>`，场景由外部仓库决定；改 3D 仓库覆盖度后重跑本脚本。"),
        },
        "objects": {k: manifest[k] for k in sorted(manifest)},
    }
    if dry:
        print(f"[dry-run] 我库天体总数: {total}")
        print(f"[dry-run] 有 3D 覆盖: {covered} ({covered/total*100:.0f}%)")
        print(f"[dry-run]   └ solar-3d 命中: {n_solar}（size-of-space 暂未接入）")
        return
    (ROOT / "viz-manifest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 viz-manifest.json：{covered}/{total} 天体有 3D 覆盖"
          f"（solar-3d {n_solar} · size-of-space 暂未接入）")


if __name__ == "__main__":
    main()
