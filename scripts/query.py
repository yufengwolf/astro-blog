#!/usr/bin/env python3
"""query.py — 天体库的"人工校验"筛选器。

用途：让你能一键筛出"哪些图是程序化/豆包生成/NASA 真图"、"哪些数据未经校验"、
"哪些关键字段缺失"，从而针对性地人工复核与增量更新。

筛选维度（可组合）：
  --image-source S   图源：nasa | programmatic | doubao_template | doubao | placeholder
  --data-source S    数据源：authority | llm_doubao | llm_local | manual
  --unverified       仅列 data_verified=False（未经人工校验的数据）
  --missing F1,F2    列出缺失这些物理字段的对象（如 --missing radius_km,mass_sun,distance_ly）
  --category C       按类别筛（如 nebula / galaxy / star）
  --name KW          名称/英文名模糊匹配

输出：
  （默认）表格：id | 类别 | 中文名 | 图源 | 数据源 | 校验 | 缺字段
  --csv              输出 CSV（含表头），便于粘贴到表格复核
  --count            只打印命中数量

示例：
  python scripts/query.py --image-source programmatic
  python scripts/query.py --unverified --category star
  python scripts/query.py --missing radius_km,mass_sun
  python scripts/query.py --data-source llm_doubao
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASTRO = ROOT / "docs" / "data" / "astro.json"

# 物理字段白名单（--missing 校验这些）
PHYS_KEYS = ("radius_km", "radius_sun", "mass_sun", "mass_kg", "temp_k",
             "lum_sun", "distance_ly", "density", "gravity", "escape_velocity")


def load():
    return json.loads(ASTRO.read_text(encoding="utf-8"))["objects"]


def has_field(o: dict, token: str) -> bool:
    """token 可为逻辑组名(radius/mass/distance)或具体物理字段名(radius_km 等)。"""
    phys = o.get("physical") or {}
    if token == "radius":
        return bool(phys.get("radius_km") or phys.get("radius_sun") or phys.get("radius_ly"))
    if token == "mass":
        return bool(phys.get("mass_sun") or phys.get("mass_kg"))
    if token == "distance":
        return bool(phys.get("distance_ly"))
    # 具体字段名
    return bool(phys.get(token))


def missing_fields(o: dict) -> list:
    """返回该对象缺失的逻辑组（radius/mass/distance）列表，用于展示。"""
    miss = []
    if not has_field(o, "radius"):
        miss.append("radius")
    if not has_field(o, "mass"):
        miss.append("mass")
    if o["category"] in ("star", "nebula", "galaxy", "cluster", "structure", "black_hole"):
        if not has_field(o, "distance"):
            miss.append("distance")
    return miss


def main() -> int:
    ap = argparse.ArgumentParser(description="天体库人工校验筛选器")
    ap.add_argument("--image-source")
    ap.add_argument("--data-source")
    ap.add_argument("--unverified", action="store_true")
    ap.add_argument("--missing", help="逗号分隔的物理字段，如 radius_km,mass_sun")
    ap.add_argument("--category")
    ap.add_argument("--name")
    ap.add_argument("--csv", action="store_true", help="输出 CSV")
    ap.add_argument("--count", action="store_true", help="只打印数量")
    args = ap.parse_args()

    missing_set = set(x.strip() for x in (args.missing or "").split(",") if x.strip())

    objs = load()
    out = []
    for o in objs:
        if args.image_source and o.get("image_source") != args.image_source:
            continue
        if args.data_source and o.get("data_source") != args.data_source:
            continue
        if args.unverified and o.get("data_verified"):
            continue
        if args.category and o.get("category") != args.category:
            continue
        if args.name:
            kw = args.name.lower()
            if kw not in (o.get("name", "") + o.get("name_en", "")).lower():
                continue
        mf = missing_fields(o)
        if missing_set:
            # 命中条件：缺失集合里任意一个 token 对应的字段确实缺失
            if not any(not has_field(o, t) for t in missing_set):
                continue
        out.append((o, mf))

    if args.count:
        print(len(out))
        return 0

    if args.csv:
        w = csv.writer(sys.stdout)
        w.writerow(["id", "category", "name", "name_en", "image_source",
                    "data_source", "data_verified", "missing"])
        for o, mf in out:
            w.writerow([o["id"], o["category"], o.get("name", ""),
                        o.get("name_en", ""), o.get("image_source", ""),
                        o.get("data_source", ""), o.get("data_verified", ""),
                        ",".join(mf)])
        return 0

    # 表格
    print(f"命中 {len(out)} 个：")
    print(f"{'id':22s} {'类别':10s} {'中文名':12s} {'图源':16s} {'数据源':12s} {'校验':5s} 缺字段")
    print("-" * 92)
    for o, mf in out:
        print(f"{o['id']:22s} {o['category']:10s} {(o.get('name') or ''):12s} "
              f"{(o.get('image_source') or ''):16s} {(o.get('data_source') or ''):12s} "
              f"{'Y' if o.get('data_verified') else 'N':5s} {','.join(mf)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
