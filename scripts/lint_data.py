#!/usr/bin/env python3
"""astro.json 数据 lint：结构校验 + 派生量一致性 + 已知事实抽查。

派生量规则（与页面值互相印证）：
  - 密度   ≈ 质量 / (4/3·π·r³)        半径 ≥200km 才校验（不规则小天体球近似失效）
  - 轨道速度 ≈ 2π·a / T                有半长轴和周期即校验
  - 逃逸速度 ≈ sqrt(2GM/r)             有质量和半径即校验
任何 error 都会以非零退出码结束，供人工流程/CI 把关。
"""
import json
import math
import sys
from datetime import datetime
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "docs" / "data" / "astro.json"
CATEGORIES = {"star", "planet", "dwarf_planet", "moon", "asteroid", "exoplanet"}
KNOWN_ORDER = ["sun", "jupiter", "saturn", "neptune", "uranus", "earth",
               "venus", "mars", "mercury", "pluto"]  # 已知质量顺序（从大到小）

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def approx(a, b, tol):
    if a is None or b is None:
        return True
    if b == 0:
        return a == 0
    return abs(a - b) / abs(b) <= tol


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    objs = data.get("objects", [])
    by_id = {}
    for o in objs:
        oid = o.get("id")
        if not oid:
            err("存在缺少 id 的记录")
            continue
        if oid in by_id:
            err(f"id 重复: {oid}")
        by_id[oid] = o

        if o.get("category") not in CATEGORIES:
            err(f"{oid}: category 非法: {o.get('category')}")
        for f in ("name", "name_en", "tagline"):
            if not o.get(f):
                err(f"{oid}: 缺少字段 {f}")
        if len(o.get("tagline") or "") > 60:
            warn(f"{oid}: tagline 超过 60 字")
        if not o.get("sources"):
            err(f"{oid}: 缺少 sources")
        registry = data.get("source_registry") or {}
        for s in o.get("sources") or []:
            entry = registry.get(s)
            if not entry:
                err(f"{oid}: sources 引用未注册的来源 id: {s}")
            elif not entry.get("name") or not entry.get("url"):
                err(f"{oid}: 来源 {s} 注册条目缺少 name/url")
        try:
            datetime.strptime(o.get("verified") or "", "%Y-%m-%d")
        except ValueError:
            err(f"{oid}: verified 格式错误: {o.get('verified')}")

        parent, cat = o.get("parent"), o.get("category")
        if cat == "star" and parent is not None:
            err(f"{oid}: 恒星的 parent 必须为 null")
        if cat in ("planet", "dwarf_planet") and parent not in by_id:
            err(f"{oid}: 行星/矮行星的 parent 必须在库中")
        if cat == "moon" and (parent not in by_id
                              or by_id.get(parent, {}).get("category") not in ("planet", "dwarf_planet")):
            err(f"{oid}: 卫星的 parent 必须是行星或矮行星")
        if parent is not None and parent not in by_id:
            err(f"{oid}: parent {parent} 不在库中")

        ph, orb = o.get("physical") or {}, o.get("orbit") or {}
        m, r = ph.get("mass_kg"), ph.get("radius_km")
        if m is not None and not (1e10 <= m <= 1e35):
            err(f"{oid}: mass_kg 越界: {m}")
        if r is not None and not (1 <= r <= 1e12):
            err(f"{oid}: radius_km 越界: {r}")
        d = ph.get("density_g_cm3")
        # 恒星（红/蓝超巨星）平均密度极低（可达 1e-9 g/cm³），且“平均密度”概念对
        # 蓬松包层恒星不具参考意义，故密度 0.1~25 的下限对 star 分类豁免
        if cat != "star" and d is not None and not (0.1 <= d <= 25):
            err(f"{oid}: density_g_cm3 越界: {d}")
        t = ph.get("mean_temp_c")
        if t is not None and not (-273 <= t <= 60000):
            err(f"{oid}: mean_temp_c 越界: {t}")
        p = orb.get("orbital_period_days")
        if p is not None and not (0.01 <= p <= 1e7):
            err(f"{oid}: orbital_period_days 越界: {p}")
        rot = orb.get("rotation_period_hours")
        if rot is not None and not (-1e5 <= rot <= 1e5):
            err(f"{oid}: rotation_period_hours 越界: {rot}")

        if m and r and r >= 200:
            derived = m / (4 / 3 * math.pi * (r * 1000) ** 3) / 1000
            if d is not None and not approx(derived, d, 0.15):
                err(f"{oid}: 密度不一致：记录 {d} vs 由质量/半径派生 {derived:.3f}")

        a, T, v = orb.get("semimajor_axis_km"), orb.get("orbital_period_days"), orb.get("orbital_velocity_km_s")
        if a and T and v is not None:
            derived_v = 2 * math.pi * a * 1000 / (T * 86400) / 1000
            if not approx(derived_v, v, 0.06):
                err(f"{oid}: 轨道速度不一致：记录 {v} vs 由 2πa/T 派生 {derived_v:.3f}")

        esc = ph.get("escape_velocity_km_s")
        if m and r and esc is not None:
            derived_esc = math.sqrt(2 * 6.674e-11 * m / (r * 1000)) / 1000
            if not approx(derived_esc, esc, 0.10):
                err(f"{oid}: 逃逸速度不一致：记录 {esc} vs 由 sqrt(2GM/r) 派生 {derived_esc:.3f}")

        for name in (o.get("moons") or {}).get("notable") or []:
            sat = next((x for x in objs if x.get("name") == name), None)
            if sat and sat.get("parent") != oid:
                err(f"{oid}: notable 卫星「{name}」的 parent 是 {sat.get('parent')}，应为 {oid}")

    for x, y in zip(KNOWN_ORDER, KNOWN_ORDER[1:]):
        if x in by_id and y in by_id:
            mx = by_id[x]["physical"].get("mass_kg")
            my = by_id[y]["physical"].get("mass_kg")
            if mx and my and mx <= my:
                err(f"质量顺序违反: {x} 应大于 {y}")

    declared = data.get("meta", {}).get("object_count")
    if declared is not None and declared != len(objs):
        err(f"meta.object_count={declared} 与实际条数 {len(objs)} 不符")

    counts = {}
    for o in objs:
        counts[o.get("category")] = counts.get(o.get("category"), 0) + 1

    print(f"天体总数: {len(objs)}  分类分布: {counts}")
    for w in warnings:
        print(f"  [warn] {w}")
    for e in errors:
        print(f"  [ERROR] {e}")
    if errors:
        print(f"\n校验失败：{len(errors)} 个错误")
        return 1
    print("校验通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
