#!/usr/bin/env python3
"""生成 master 覆盖清单 CSV（全部 178 天体，含状态列，供用户填写）。"""
import json, csv
from pathlib import Path

ROOT = Path(r"C:/Users/99432/code/WorkBuddy_workspace/mkdocs-blog")
astro = json.loads((ROOT / "docs/data/astro.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "viz-manifest.json").read_text(encoding="utf-8"))
objs = astro["objects"] if isinstance(astro, dict) else astro
cov = manifest["objects"]

# 与 gen_viz_manifest.py 同步的别名表（用于显示"用了哪个外部 id"）
ALIASES = {"cyg_x1":"cygx1","sgr_a_star":"sagA","alphacen_a":"alphaCen",
           "alphacen_b":"alphaCen","51_pegasi_b":"peg51",
           "proxima_centauri":"proxima","proxima_centauri_b":"proxima",
           "omega_cen":"omegaCen","kepler_452":"kepler452","kepler_452b":"kepler452",
           "procyon_a":"procyon","sirius_a":"sirius","sirius_b":"sirius",
           "m45":"pleiades","pegasi_51":"peg51"}

rows = []
for o in objs:
    oid = o["id"]
    if oid in cov:
        ext = cov[oid][0]
        used = ALIASES.get(oid, oid)
        status = "已覆盖"
        ext_id_disp = used
        ext_name = ext.get("name", "")
    else:
        status = "待外部模型"
        ext_id_disp = ""
        ext_name = ""
    rows.append({
        "my_id": oid,
        "my_name_zh": o.get("name",""),
        "my_name_en": o.get("name_en",""),
        "category": o.get("category",""),
        "status": status,
        "used_external_id": ext_id_disp,
        "external_name": ext_name,
        "my_decision": "",   # 留空给用户填：确认ALIASES / 外部id=xxx / 外部暂无模型
    })

out = ROOT / "scripts" / "viz_coverage_todo.csv"
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["my_id","my_name_zh","my_name_en","category","status","used_external_id","external_name","my_decision"])
    w.writeheader(); w.writerows(rows)

covered = sum(1 for r in rows if r["status"]=="已覆盖")
print(f"已写 {out}")
print(f"总计 {len(rows)} | 已覆盖 {covered} | 待外部模型 {len(rows)-covered}")
print("前 12 行预览:")
for r in rows[:12]:
    print(f"  {r['my_id']:<18} {r['my_name_zh']:<10} {r['status']:<8} ext={r['used_external_id']}")
