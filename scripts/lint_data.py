#!/usr/bin/env python3
"""astro.json 数据 lint：结构校验 + 派生量一致性 + 已知事实抽查。

派生量规则（与页面值互相印证）：
  - 密度   ≈ 质量 / (4/3·π·r³)        半径 ≥200km 才校验（不规则小天体球近似失效）
  - 轨道速度 ∈ [椭圆平均速度, 圆轨道速度]  见 ellipse_mean_factor() 推导
  - 逃逸速度 ≈ sqrt(2GM/r)             有质量和半径即校验
任何 error 都会以非零退出码结束，供人工流程/CI 把关。
"""
import json
import math
import sys
from datetime import datetime
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "docs" / "data" / "astro.json"
CATEGORIES = {"star", "star_system", "planet", "dwarf_planet", "moon", "asteroid", "exoplanet",
              "black_hole", "nebula", "galaxy", "cluster", "structure", "comet"}
# 密度 0.1~25 g/cm³ 只对固态天体有意义；恒星（超巨星极低）与延展天体
# （星系/星云/星团/大尺度结构/黑洞）不校验密度
DENSITY_CATS = {"planet", "dwarf_planet", "moon", "asteroid", "comet"}
# parent 允许的父分类（None 表示必须为空）。校验时比对 parent 对象的分类，
# 因此父对象可以出现在子对象之后（前向引用，如黑洞→其宿主星系）。
PARENT_RULES = {
    # star 允许指向另一颗恒星（双星/聚星系统的伴星）、聚星系统（聚星系统的组件星）、
    # 星云（超新星遗迹内的脉冲星）或星团（如 R136a1 属于 R136 星团）
    "star": {None, "star", "star_system", "nebula", "cluster"},
    # 聚星系统（多星系统父卡）：本身可为顶层，或从属于星团/星云等分组
    "star_system": {None, "star", "nebula", "cluster"},
    # planet/exoplanet 也允许父为 star_system：环双星/聚星系统行星（如 kepler_16b 绕双星 kepler_16）
    "planet": {"star", "star_system"},
    "dwarf_planet": {"star"},
    "moon": {"planet", "dwarf_planet"},
    "asteroid": {"star"},
    "exoplanet": {"star", "star_system"},
    "black_hole": {None, "galaxy", "star"},
    "nebula": {None, "galaxy", "star"},
    "galaxy": {None, "galaxy", "structure"},
    "cluster": {None, "galaxy", "nebula"},
    "structure": {None, "structure"},
    "comet": {"star"},
}
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


def ellipse_mean_factor(e):
    """椭圆轨道「时间平均速度 / 圆轨道速度」= (2/π)·E(e)（第二类完全椭圆积分）。

    推导（偏近点角 E 换元，dt = (T/2π)(1-e·cosE)dE）：
        v = sqrt(GM/a)·sqrt((1+e·cosE)/(1-e·cosE))
        <v> = (1/T)∫v·dt = sqrt(GM/a)·(1/2π)∫₀^{2π} sqrt(1-e²cos²E) dE
            = (2πa/T)·(2/π)·E(e)
    e=0 时 E(0)=π/2，系数=1，退化为圆轨道速度 2πa/T。
    采用 1024 点梯形求积，e<0.99 时相对误差 <1e-9，避免引入 scipy 依赖。

    注意：2πa/T 只是**圆轨道**速度；对高偏心率轨道（如 Sedna e=0.849、
    Halley e=0.967）直接拿它当唯一真值，会把正确的「平均轨道速度」误判为错误。
    """
    if not e or e <= 0:
        return 1.0
    if e >= 1:
        return 0.0
    n = 1024
    return sum(math.sqrt(max(0.0, 1 - e * e * math.cos(2 * math.pi * i / n) ** 2))
               for i in range(n)) / n


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
        # 全站双语：英文名称与英文一句话简介是数据契约的一部分，缺一即视为不同步
        for f in ("name", "name_en", "tagline", "tagline_en"):
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

        ph, orb = o.get("physical") or {}, o.get("orbit") or {}
        cat = o.get("category")
        m, r = ph.get("mass_kg"), ph.get("radius_km")
        if m is not None and not (1e10 <= m <= 1e55):
            err(f"{oid}: mass_kg 越界: {m}")
        if r is not None and not (1 <= r <= 1e25):
            err(f"{oid}: radius_km 越界: {r}")
        d = ph.get("density_g_cm3")
        # 恒星（红/蓝超巨星）平均密度极低（可达 1e-9 g/cm³），延展天体（星系/
        # 星云/星团/大尺度结构/黑洞）无实心球密度概念，均豁免 0.1~25 区间
        if cat in DENSITY_CATS and d is not None and not (0.1 <= d <= 25):
            err(f"{oid}: density_g_cm3 越界: {d}")
        t = ph.get("mean_temp_c")
        # 中子星/磁星表面温度可达 10⁶ K 量级（如蟹云脉冲星约 1.6×10⁶ K），
        # 恒星类上限放宽到 1e7，其余天体维持 60000 K 防笔误
        t_max = 1e7 if cat in ("star", "star_system") else 60000
        if t is not None and not (-273 <= t <= t_max):
            err(f"{oid}: mean_temp_c 越界: {t}")
        p = orb.get("orbital_period_days")
        # 上限 1e9 天 ~ 274 万年：覆盖长周期束缚轨道（比邻星绕南门二 AB
        # P=547000 年 ≈ 2.0e8 天，Kervella et al. 2016），原 1e7 天会把这类真值判错。
        if p is not None and not (0.01 <= p <= 1e9):
            err(f"{oid}: orbital_period_days 越界: {p}")
        rot = orb.get("rotation_period_hours")
        if rot is not None and not (-1e5 <= rot <= 1e5):
            err(f"{oid}: rotation_period_hours 越界: {rot}")

        if m and r and r >= 200:
            derived = m / (4 / 3 * math.pi * (r * 1000) ** 3) / 1000
            if d is not None and not approx(derived, d, 0.15):
                err(f"{oid}: 密度不一致：记录 {d} vs 由质量/半径派生 {derived:.3f}")

        a, T, v = orb.get("semimajor_axis_km"), orb.get("orbital_period_days"), orb.get("orbital_velocity_km_s")
        e = orb.get("eccentricity") or 0
        if a and T and v is not None:
            # 数据源的「轨道速度」有两种常见口径：圆轨道速度 2πa/T，或椭圆轨道
            # 时间平均速度 (2πa/T)·f(e)。二者都是合法记录，故校验允许区间为
            # [平均速度×0.94, 圆速度×1.06]；e→0 时区间收窄回原 ±6% 严格校验。
            v_circ = 2 * math.pi * a * 1000 / (T * 86400) / 1000
            v_mean = v_circ * ellipse_mean_factor(e)
            lo, hi = v_mean * 0.94, v_circ * 1.06
            if not (lo <= v <= hi):
                # 附 vis-viva 物理区间，便于人工判断记录值是笔误还是别的速度口径
                if 0 <= e < 1 and e > 0:
                    bound = (v_circ * math.sqrt((1 - e) / (1 + e)),
                             v_circ * math.sqrt((1 + e) / (1 - e)))
                    extra = f"，vis-viva 物理区间 [{bound[0]:.3f}, {bound[1]:.3f}]"
                else:
                    extra = ""
                err(f"{oid}: 轨道速度不一致：记录 {v} vs 允许区间 "
                    f"[{lo:.3f}, {hi:.3f}]（2πa/T={v_circ:.3f}）{extra}")

        esc = ph.get("escape_velocity_km_s")
        if m and r and esc is not None:
            derived_esc = math.sqrt(2 * 6.674e-11 * m / (r * 1000)) / 1000
            if not approx(derived_esc, esc, 0.10):
                err(f"{oid}: 逃逸速度不一致：记录 {esc} vs 由 sqrt(2GM/r) 派生 {derived_esc:.3f}")

        for name in (o.get("moons") or {}).get("notable") or []:
            sat = next((x for x in objs if x.get("name") == name), None)
            if sat and sat.get("parent") != oid:
                err(f"{oid}: notable 卫星「{name}」的 parent 是 {sat.get('parent')}，应为 {oid}")

    # 第二遍：parent 结构校验（by_id 已完整，支持前向引用）
    # host_star：系外行星的宿主恒星未被本站收录时，parent 允许为 null，
    # 但必须显式登记宿主恒星名，归属可追溯（层级由 universe-data.json 承载）。
    for o in objs:
        oid, cat = o.get("id"), o.get("category")
        parent = o.get("parent")
        host_star = o.get("host_star")
        external_host = parent is None and bool(host_star) and cat in ("planet", "exoplanet")
        if external_host and not isinstance(host_star, str):
            err(f"{oid}: host_star 必须是宿主恒星名称字符串")
        allowed = PARENT_RULES.get(cat)
        if allowed is not None:
            if parent is None:
                if None not in allowed and not external_host:
                    err(f"{oid}: {cat} 的 parent 不能为空（宿主恒星未收录时请登记 host_star）")
            else:
                pcat = by_id.get(parent, {}).get("category")
                if pcat is None:
                    err(f"{oid}: parent {parent} 不在库中")
                elif pcat not in allowed:
                    err(f"{oid}: {cat} 的 parent 必须是 {sorted(str(a) for a in allowed)} "
                        f"之一的分类，当前 {parent} 是 {pcat}")
        if cat in ("planet", "dwarf_planet") and parent not in by_id and not external_host:
            err(f"{oid}: 行星/矮行星的 parent 必须在库中")
        if cat == "moon" and (parent not in by_id
                              or by_id.get(parent, {}).get("category") not in ("planet", "dwarf_planet")):
            err(f"{oid}: 卫星的 parent 必须是行星或矮行星")

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
