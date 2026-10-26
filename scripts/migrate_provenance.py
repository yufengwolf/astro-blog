#!/usr/bin/env python3
"""migrate_provenance.py — 一次性迁移：给 astro.json 所有对象回填机器可读的 provenance 字段。

注意：沿用既有 `verified`（核对日期，ISO 字符串，lint/gen_pages 依赖）语义，不改动它。
新增三个独立字段（均为新增，向后兼容）：
  image_source  图源：nasa（真实 NASA/ESA 照片）| programmatic（程序化生成）
                | doubao_template（恒星 9 光谱型模板复用）| doubao（豆包单图）
                | placeholder（占位待替换）
  data_source   数据源：authority（NSSDC/SBDB/事实表等权威源手录）| llm_doubao
                | llm_local | manual（历史手录深空，待审）
  data_verified 数据是否经人工校验：布尔（与 verified 日期字段区分——
                verified 是"核对日期"，data_verified 是"人是否确认过可靠"）

回填规则（纯从已有字段推导，不臆造）：
  image_source:
    - 恒星且 id=='sun'            -> nasa（SDO 真图）
    - 恒星（非太阳）              -> doubao_template（复用 9 类豆包模板）
    - 黑洞                        -> programmatic
    - 大尺度(nebula/galaxy/cluster/structure): 有 image_url -> nasa，否则 programmatic
    - 其余（行星/卫星/矮行星/小行星/彗星）: 有 image_url -> nasa，否则 programmatic
  data_source / data_verified:
    - 太阳系天体(sun/planet/dwarf_planet/moon/asteroid/comet) -> authority / True
      （历史上来自 NSSDC 事实表 / JPL SBDB / 官方数据，已在站上长期展示，视为已校验）
    - 新增的 procyon_a            -> llm_doubao / False
    - 其余深空(star 非太阳/nebula/galaxy/cluster/structure/black_hole) -> manual / False
      （历史手录或 AI 抽取，留作人工校验队列）

用法：python scripts/migrate_provenance.py            # 执行回填
      python scripts/migrate_provenance.py --check      # 只打印分布，不落盘
"""
import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASTRO = ROOT / "docs" / "data" / "astro.json"

SOLAR = {"sun", "planet", "dwarf_planet", "moon", "asteroid", "comet"}
DEEP = {"nebula", "galaxy", "cluster", "structure"}


def backfill(o: dict) -> dict:
    cat, oid = o["category"], o["id"]
    has_url = bool(o.get("image_url"))

    # ---- image_source ----
    if oid == "sun":
        isrc = "nasa"
    elif cat == "star":
        isrc = "doubao_template"
    elif cat == "black_hole":
        isrc = "programmatic"
    elif cat in DEEP:
        isrc = "nasa" if has_url else "programmatic"
    else:  # 行星/卫星/矮行星/小行星/彗星
        isrc = "nasa" if has_url else "programmatic"
    o["image_source"] = isrc

    # ---- data_source / data_verified ----
    if oid == "procyon_a":
        dsrc, verified = "llm_doubao", False
    elif cat in SOLAR or oid == "sun":
        # 注意：太阳的 category 是 "star"，需用 id 单独判定
        dsrc, verified = "authority", True
    else:
        dsrc, verified = "manual", False
    o["data_source"] = dsrc
    o["data_verified"] = verified

    # ---- 修正 procyon_a 的 credit（之前误标"程序化"，实为恒星豆包模板复用）----
    if oid == "procyon_a":
        o["image_credit"] = "AI 生成模板（豆包 9 光谱型代表图复用，非真实影像）"
    return o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只打印分布，不落盘")
    args = ap.parse_args()

    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    objs = data["objects"]
    for o in objs:
        backfill(o)

    isrc = Counter(o["image_source"] for o in objs)
    dsrc = Counter(o["data_source"] for o in objs)
    ver = Counter(o["data_verified"] for o in objs)
    print("=== image_source 分布 ===")
    for k, v in sorted(isrc.items(), key=lambda x: -x[1]):
        print(f"  {k:18s} {v}")
    print("=== data_source 分布 ===")
    for k, v in sorted(dsrc.items(), key=lambda x: -x[1]):
        print(f"  {k:18s} {v}")
    print(f"=== data_verified: True={ver.get(True,0)}  False={ver.get(False,0)} ===")

    if args.check:
        print("\n[check] 未落盘。")
        return 0

    ASTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(f"\n已回填 {len(objs)} 个对象 -> {ASTRO.relative_to(ROOT)}"
          f"（未改动既有 verified 日期字段）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
