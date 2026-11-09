#!/usr/bin/env python3
"""gen_viz_manifest.py — 生成 viz-manifest.json（3D 可视化覆盖契约）

设计目标（P3，经用户拍板，并随 astro-solar-3d 升级「天体级直达外链」调整）：
- 主站与 3D 仓库解耦：本文件是「哪些天体有 3D 模型、去哪个外链」的**唯一契约（表格）**。
- 当前**唯一**外部 3D 仓库：astro-solar-3d（Cloudflare Pages，已部署，支持天体级直达外链）。
- **架构约束（用户明确）**：当前仓库只做「消费者」——提供窗口（iframe）+ 地址
  （`go.html?body=<id>&embed=1`），**绝不硬编码「某天体 → 某场景 HTML」**。
  页面路由、场景选择、精简界面全部由外部仓库（astro-solar-3d）负责；本仓库只透传 id。
- **外部仓库填充表格**：astro-solar-3d 通过 `links.json` 发布「哪些天体有 3D、对应 go 链接」这张表，
  本仓库**消费**它（快照存于 `scripts/solar3d_links.json`，`--sync` 可从线上刷新）。
  即：当前仓库不维护「天体 → 3D」的映射清单，只声明「外部有就嵌、没有就优雅降级」。
- 外链格式（astro-solar-3d readme 规定）：
  - 万能入口 `go.html?body=<ID>`：只给 ID，外部仓库自动落到正确页面（太阳系/卫星系/银河系…）；
  - 追加 `&embed=1`：隐藏导航/菜单/控制面板，只留天体特写 + 信息卡（适合 iframe 嵌入）；
  - 默认界面即中文（`&lang=en` 才切英文），故本仓库不额外加 lang 参数。
- size-of-space 暂未纳入（用户尚未部署 CF Pages）；结构已预留，将来在 build() 加回第二个来源即可。

用法：
    python scripts/gen_viz_manifest.py            # 生成到仓库根 viz-manifest.json
    python scripts/gen_viz_manifest.py --dry-run  # 只打印匹配统计，不落盘
    python scripts/gen_viz_manifest.py --sync     # 从线上刷新 scripts/solar3d_links.json 快照
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOLAR3D_BASE = "https://astro-solar-3d.pages.dev"
LINKS_SNAPSHOT = ROOT / "scripts" / "solar3d_links.json"
LINKS_LIVE = "https://astro-solar-3d.pages.dev/links.json"

# 我库天体 id → 外部 links.json 的 id（仅收录确认存在的别名错配，绝不臆造）。
# 例：我库用 sgr_a_star，外部用 sagA（Sagittarius A*）；我库用 cyg_x1，外部用 cygx1。
ALIASES = {
    "cyg_x1": "cygx1",
    "sgr_a_star": "sagA",
    "alphacen_a": "alphaCen",
    "alphacen_b": "alphaCen",
    "51_pegasi_b": "peg51",
}


def _load_links_snapshot():
    if not LINKS_SNAPSHOT.exists():
        sys.exit(f"[错误] 缺少快照 {LINKS_SNAPSHOT}；请先运行 `python scripts/gen_viz_manifest.py --sync`")
    data = json.loads(LINKS_SNAPSHOT.read_text(encoding="utf-8"))
    # 去重（links.json 中同名跨页会重复，goUrl 一致，取首个即可）
    by_id = {}
    for b in data.get("bodies", []):
        bid = b.get("id")
        if bid and bid not in by_id:
            by_id[bid] = b
    return by_id


def build(data):
    """返回 (manifest, n_solar)。manifest: {oid: [entry, ...]}。"""
    links = _load_links_snapshot()
    objs = data["objects"]
    manifest = {}
    n_solar = 0
    for o in objs:
        oid = o["id"]
        ext_id = ALIASES.get(oid, oid)
        if ext_id not in links:
            continue
        b = links[ext_id]
        go = b.get("goUrl") or f"go.html?body={ext_id}"
        # CF Pages 会把 `go.html` 308 重定向到无后缀的干净 URL `go?...`，
        # 直接用规范地址（去掉 .html）可避免 iframe 多一次重定向。
        go = go.replace("go.html", "go", 1)
        name = b.get("name") or oid
        manifest[oid] = [{
            "repo": "solar-3d",
            "kind": "system",
            "title": "真实三维系统",
            "name": name,
            "src": f"{SOLAR3D_BASE}/{go}&embed=1",   # iframe 精简界面
            "full": f"{SOLAR3D_BASE}/{go}",          # 完整交互版（新标签打开）
        }]
        n_solar += 1
    return manifest, n_solar


def _sync():
    import urllib.request
    print(f"[sync] 拉取 {LINKS_LIVE} ...")
    try:
        req = urllib.request.Request(LINKS_LIVE, headers={"User-Agent": "mkdocs-blog-gen/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
        json.loads(raw)  # 校验
        LINKS_SNAPSHOT.write_text(raw, encoding="utf-8")
        print(f"[sync] 已刷新快照 -> {LINKS_SNAPSHOT} ({len(raw)} bytes)")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"[sync] 失败：{e}\n（可手动把 astro-solar-3d 部署产物的 links.json 复制到 {LINKS_SNAPSHOT}）")


def main():
    if "--sync" in sys.argv:
        _sync()
        return
    dry = "--dry-run" in sys.argv
    data = json.loads((ROOT / "docs" / "data" / "astro.json").read_text(encoding="utf-8"))
    manifest, n_solar = build(data)
    total = len(data["objects"])
    covered = len(manifest)
    out = {
        "version": 2,
        "generated_from": {
            "solar-3d": SOLAR3D_BASE,
            "links_snapshot": str(LINKS_SNAPSHOT.relative_to(ROOT)),
            "note": ("当前仅 astro-solar-3d 一个来源（size-of-space 待用户部署 CF Pages 后加回）。"
                     "src 统一为 `go.html?body=<id>&embed=1`，由外部仓库决定页面与渲染；"
                     "契约（哪些天体有 3D）来自外部仓库的 links.json 快照，改 3D 覆盖度后 "
                     "`--sync` 刷新快照或重跑本脚本即可。"),
        },
        "objects": {k: manifest[k] for k in sorted(manifest)},
    }
    if dry:
        print(f"[dry-run] 我库天体总数: {total}")
        print(f"[dry-run] 有 3D 覆盖: {covered} ({covered/total*100:.0f}%)")
        print(f"[dry-run]   └ solar-3d 命中: {n_solar}（size-of-space 暂未接入）")
        print(f"[dry-run]   别名对齐: { {k: ALIASES[k] for k in ALIASES if k in {o['id'] for o in data['objects']}} }")
        return
    (ROOT / "viz-manifest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 viz-manifest.json：{covered}/{total} 天体有 3D 覆盖"
          f"（solar-3d {n_solar} · size-of-space 暂未接入）")


if __name__ == "__main__":
    main()
