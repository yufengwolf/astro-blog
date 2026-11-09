#!/usr/bin/env python3
"""改进版覆盖分析：更强匹配（含 name_en<->外部id），输出可填表 CSV。"""
import json, re, csv
from pathlib import Path

ROOT = Path(r"C:/Users/99432/code/WorkBuddy_workspace/mkdocs-blog")
astro = json.loads((ROOT / "docs/data/astro.json").read_text(encoding="utf-8"))
links = json.loads((ROOT / "scripts/solar3d_links.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "viz-manifest.json").read_text(encoding="utf-8"))

objs = astro["objects"] if isinstance(astro, dict) else astro
ext_by_id = {}
for b in links.get("bodies", []):
    bid = b.get("id")
    if bid and bid not in ext_by_id:
        ext_by_id[bid] = b
ext_ids = list(ext_by_id)
ext_names = {b.get("name", "").lower(): bid for bid, b in ext_by_id.items() if b.get("name")}

# 已登记别名（含本打算新增的 8 个，先在本分析里当作已覆盖）
ALIASES = {"cyg_x1":"cygx1","sgr_a_star":"sagA","alphacen_a":"alphaCen",
           "alphacen_b":"alphaCen","51_pegasi_b":"peg51",
           "proxima_centauri":"proxima","proxima_centauri_b":"proxima",
           "omega_cen":"omegaCen","kepler_452":"kepler452","kepler_452b":"kepler452",
           "procyon_a":"procyon","sirius_a":"sirius","sirius_b":"sirius"}

def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def find(o):
    oid = o["id"]
    if oid in ALIASES and ALIASES[oid] in ext_by_id:
        return ("alias", ALIASES[oid], "high")
    if oid in ext_by_id:
        return ("direct", oid, "high")
    nid = norm(oid)
    for eid in ext_ids:
        if norm(eid) == nid:
            return ("norm_id", eid, "high")
    ne = norm(o.get("name_en") or "")
    if ne:
        for eid in ext_ids:
            if norm(eid) == ne:
                return ("name_en==id", eid, "high")
        for eid in ext_ids:
            ne2 = norm(eid)
            if len(ne) >= 4 and len(ne2) >= 4 and (ne in ne2 or ne2 in ne):
                return ("name_en~id", eid, "medium")
    for eid in ext_ids:
        ne2 = norm(eid)
        if len(nid) >= 4 and len(ne2) >= 4 and (nid in ne2 or ne2 in nid):
            return ("id~id", eid, "medium")
    nm = (o.get("name_en") or "").lower()
    if nm:
        for en, eid in ext_names.items():
            if len(en) >= 4 and (en in nm or nm in en):
                return ("name_en~extname", eid, "low")
    nz = (o.get("name") or "").lower()
    if nz:
        for en, eid in ext_names.items():
            if len(en) >= 2 and (en in nz or nz in en):
                return ("zh~extname", eid, "low")
    return (None, None, None)

cov = manifest["objects"]
covered_ids = set(cov)
rows = []
for o in objs:
    if o["id"] in covered_ids:
        continue
    meth, cand, conf = find(o)
    if cand is None:
        issue = "external_missing"
    else:
        issue = "id_mismatch"
    rows.append({
        "my_id": o["id"], "my_name_zh": o.get("name",""), "my_name_en": o.get("name_en",""),
        "category": o.get("category",""), "issue_type": issue,
        "external_id": cand or "", "external_name": (ext_by_id[cand].get("name","") if cand else ""),
        "match_method": meth or "", "confidence": conf or "",
        "action": ("补 ALIASES: %s -> %s" % (o["id"], cand)) if issue=="id_mismatch" else "外部暂无模型，需 astro-solar-3d 新增后 --sync",
    })

# 写 CSV
out_csv = ROOT / "scripts" / "viz_coverage_todo.csv"
with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["my_id","my_name_zh","my_name_en","category","issue_type","external_id","external_name","match_method","confidence","action"])
    w.writeheader(); w.writerows(rows)

mm = [r for r in rows if r["issue_type"]=="id_mismatch"]
em = [r for r in rows if r["issue_type"]=="external_missing"]
print(f"未覆盖总数: {len(rows)}  |  id_mismatch: {len(mm)}  |  external_missing: {len(em)}")
print(f"\n=== id_mismatch（疑似 id 错配，建议补 ALIASES）共 {len(mm)} ===")
for r in mm:
    print(f"  [{r['confidence']:<6}] {r['my_id']:<18} {r['my_name_zh']:<8} {r['my_name_en']:<22} -> {r['external_id']:<14} ({r['external_name']}) [{r['match_method']}]")
print(f"\n=== external_missing 按类别 ===")
from collections import Counter
c = Counter(r["category"] for r in em)
for cat, n in c.most_common():
    print(f"  {cat:<12} {n}")
print(f"\nCSV 已写: {out_csv}")
