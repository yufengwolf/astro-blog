#!/usr/bin/env python3
"""gen_pages.py — 从 docs/data/astro.json 生成站点页面。

产物：
  docs/index.md          首页天体总览（搜索/筛选/排序工具页，卡片预渲染）
  docs/objects/<id>.md   天体详情页（结构化数据表 + 卫星链接 + 合成科普文章）
  docs/data.md           数据集下载页
  docs/data/astro_flat.csv  扁平 CSV（数据集下载用）

文章约定：docs/articles/<slug>.md 的正文会被合成进对应详情页（astro.json 的 article 字段）。
用法：python gen_pages.py [--root DIR] [--check]
  --check  只校验产物与 JSON 是否同步（不写盘），不同步则退出码 1
"""
import argparse
import csv
import io
import json
import math
import re
import sys
from pathlib import Path

REPO_URL = "https://github.com/yufengwolf/astro-blog"
SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
CAT_ZH = {"star": "恒星", "planet": "行星", "dwarf_planet": "矮行星",
          "moon": "卫星", "asteroid": "小行星", "exoplanet": "系外行星"}
AU_KM = 1.496e8


def sup(n):
    return str(n).translate(SUP)


def fmt_mass(kg):
    if kg is None:
        return None
    e = math.floor(math.log10(kg))
    return f"{kg / 10 ** e:.3g}×10{sup(e)} kg"


def fmt_radius(r):
    if r is None:
        return None
    return f"{r:,.1f} km" if r < 1000 else f"{r:,.0f} km"


def fmt_km(a):
    if a is None:
        return None
    return f"{a:,.0f} km"


def fmt_axis(a, parent):
    if a is None:
        return None
    s = fmt_km(a)
    if parent == "sun":
        s += f"（{a / AU_KM:.3g} AU）"
    return s


def fmt_temp(t):
    return None if t is None else f"{t} °C"


def fmt_period(d):
    if d is None:
        return None
    if d < 2:
        return f"{d:.2f} 天"
    if d < 1000:
        return f"{d:.1f} 天"
    return f"{d / 365.25:.1f} 年（{d:,.0f} 天）"


def fmt_rotation(h):
    if h is None:
        return None
    retro = h < 0
    h = abs(h)
    s = f"{h / 24:.2f} 天" if h >= 48 else f"{h:.2f} 小时"
    return ("逆行自转 · " if retro else "") + s


def fmt_velocity(v):
    if v is None:
        return None
    return f"{v:.3f} km/s" if v < 1 else f"{v:.2f} km/s"


def fmt_gravity(g):
    return None if g is None else f"{g:.2f} m/s²"


def fmt_pressure(p):
    if p is None:
        return None
    if p == 0:
        return "≈ 0（可忽略）"
    if p < 0.001:
        e = math.floor(math.log10(p))
        return f"{p / 10 ** e:.3g}×10{sup(e)} bar"
    return f"{p:g} bar"


def fmt_angle(x):
    return None if x is None else f"{x:.4g}°"


def fmt_ecc(e):
    return None if e is None else f"{e:.4g}"


def fmt_albedo(a):
    return None if a is None else f"{a:.2f}"


def fmt_yn(v):
    return {True: "是", False: "否", None: "未知"}[v]


def dash(v):
    return v if v is not None else "—"


def load_data(root):
    return json.loads((root / "docs" / "data" / "astro.json").read_text(encoding="utf-8"))


def article_body(root, slug):
    """返回 (文章标题, 正文)；没有则 (None, None)。文章源在仓库根 articles/（docs 外，不单独建页）。"""
    p = root / "articles" / f"{slug}.md"
    if not p.exists():
        return None, None
    text = re.sub(r"\A---\n.*?\n---\n", "", p.read_text(encoding="utf-8"), flags=re.S).strip()
    m = re.match(r"#\s+(.+)", text)
    title = m.group(1).strip() if m else None
    if m:
        text = text[m.end():].strip()
    return title, text


def img_block(o):
    cat = o["category"]
    img = o.get("image")
    if img:
        return (f'<div class="astro-img {cat}">'
                f'<img src="../{img}" alt="{o["name"]}" loading="lazy"></div>')
    return (f'<div class="astro-img {cat} astro-img-fallback">'
            f'<span>{o["name"][0]}</span></div>')


def build_index(data):
    objs = data["objects"]
    n = len(objs)
    cats = {}
    for o in objs:
        cats[o["category"]] = cats.get(o["category"], 0) + 1
    L = []
    L.append("---")
    L.append('description: "收录 %d 个太阳系天体的结构化数据：质量、半径、密度、表面温度、'
             '轨道周期与卫星数量，支持按分类筛选、按任意数值排序。"' % n)
    L.append("---")
    L.append("")
    L.append('<div class="astro-hero">')
    L.append("  <h1>太阳系天体数据库</h1>")
    L.append(f'  <p class="astro-hero-sub">{n} 个天体的质量 · 半径 · 密度 · 温度 · 轨道 · 卫星数据，一键筛选，按数值排序</p>')
    L.append('  <p class="astro-hero-stats">')
    for key in ("star", "planet", "dwarf_planet", "moon"):
        if cats.get(key):
            L.append(f'    <span class="astro-stat"><b>{cats[key]}</b> {CAT_ZH[key]}</span>')
    L.append("  </p>")
    L.append(f'  <p class="astro-hero-links"><a href="data/">下载数据集</a>'
             f'<span class="sep">·</span><a href="#articles">科普文章</a></p>')
    L.append("</div>")
    L.append("")
    L.append('<div class="astro-toolbar">')
    L.append('  <input type="search" id="astro-search" placeholder="搜索天体名称（中/英文）…" aria-label="搜索天体">')
    L.append('  <div class="astro-chips" role="group" aria-label="按分类筛选">')
    L.append('    <button type="button" class="chip active" data-filter="all">全部</button>')
    for key in ("star", "planet", "dwarf_planet", "moon"):
        if cats.get(key):
            L.append(f'    <button type="button" class="chip" data-filter="{key}">{CAT_ZH[key]}</button>')
    L.append("  </div>")
    L.append('  <label class="astro-sort-label">排序')
    L.append('    <select id="astro-sort" aria-label="排序方式">')
    L.append('      <option value="name">名称</option>')
    L.append('      <option value="mass">质量 ↓</option>')
    L.append('      <option value="radius">半径 ↓</option>')
    L.append('      <option value="density">密度 ↓</option>')
    L.append('      <option value="temp">表面温度 ↓</option>')
    L.append('      <option value="period">轨道周期 ↓</option>')
    L.append('      <option value="moons">卫星数量 ↓</option>')
    L.append("    </select>")
    L.append("  </label>")
    L.append("</div>")
    L.append('<p class="astro-count" id="astro-count"></p>')
    L.append("")
    L.append('<div class="astro-grid">')
    for o in objs:
        ph, orb = o.get("physical") or {}, o.get("orbit") or {}
        m, r = ph.get("mass_kg"), ph.get("radius_km")
        key_stat = fmt_temp(ph.get("mean_temp_c")) or (f"{ph['density_g_cm3']:g} g/cm³" if ph.get("density_g_cm3") else None)
        stats = [fmt_mass(m), fmt_radius(r), key_stat]
        stats_html = "".join(f"<span>{s}</span>" for s in stats if s)
        L.append(f'  <article class="astro-card" data-category="{o["category"]}"'
                 f' data-name="{o["name"]} {o["name_en"]}"'
                 f' data-mass="{m if m is not None else ""}"'
                 f' data-radius="{r if r is not None else ""}"'
                 f' data-density="{ph.get("density_g_cm3") if ph.get("density_g_cm3") is not None else ""}"'
                 f' data-temp="{ph.get("mean_temp_c") if ph.get("mean_temp_c") is not None else ""}"'
                 f' data-period="{orb.get("orbital_period_days") if orb.get("orbital_period_days") is not None else ""}"'
                 f' data-moons="{(o.get("moons") or {}).get("count") if (o.get("moons") or {}).get("count") is not None else ""}">')
        L.append(f'    <a class="astro-card-link" href="objects/{o["id"]}/">')
        L.append(f'      {img_block(o)}')
        L.append('      <div class="astro-card-body">')
        L.append(f'        <div class="astro-card-title">{o["name"]}<span class="en">{o["name_en"]}</span></div>')
        L.append(f'        <p class="astro-card-tagline">{o["tagline"]}</p>')
        L.append(f'        <div class="astro-card-stats">{stats_html}</div>')
        L.append("      </div>")
        L.append(f'      <span class="astro-badge {o["category"]}">{CAT_ZH[o["category"]]}</span>')
        L.append("    </a>")
        L.append("  </article>")
    L.append("</div>")
    L.append('<p class="astro-empty" id="astro-empty" hidden>没有匹配的天体，换个关键词或分类试试。</p>')
    L.append("")
    articles = [o for o in objs if o.get("article")]
    if articles:
        L.append('<section class="astro-articles" id="articles">')
        L.append("  <h2>科普文章</h2>")
        L.append("  <p>每颗天体的数据页之下，附一篇深度科普：</p>")
        L.append('  <ul class="astro-article-list">')
        for o in articles:
            L.append(f'    <li><a href="objects/{o["id"]}/">{o["name"]}（{o["name_en"]}）</a></li>')
        L.append("  </ul>")
        L.append("</section>")
        L.append("")
    meta = data["meta"]
    L.append('<section class="astro-note">')
    L.append("  <h2>数据说明</h2>")
    L.append(f'  <p>全部数值整理自 NASA 公开资料（公共领域），每个天体页面均标注来源与核对日期（最近核对：{meta["updated"]}）。'
             f'发现数据错误？欢迎到 <a href="{REPO_URL}/issues">GitHub Issues</a> 反馈。</p>')
    L.append(f'  <p><a href="data/">下载完整数据集（JSON / CSV）</a></p>')
    L.append("</section>")
    L.append("")
    return "\n".join(L)


def build_object_index(data):
    """docs/objects/index.md — 天体库总表：一页看全部天体的关键数据。"""
    objs = data["objects"]
    L = []
    L.append("---")
    L.append('description: "太阳系全部 %d 个收录天体的关键数据总表：质量、半径、密度、温度、轨道周期与卫星数量。"' % len(objs))
    L.append("---")
    L.append("")
    L.append("# 天体库")
    L.append("")
    L.append(f"本站收录的全部 {len(objs)} 个太阳系天体。点击名称进入详情页（完整数据 + 科普文章）；"
             f"数值的含义与单位见[数据集字段说明](../data.md#字段说明)。")
    L.append("")
    L.append("| 天体 | 分类 | 母天体 | 质量 | 平均半径 | 密度 | 均温 | 轨道周期 | 卫星数 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    by_id = {o["id"]: o for o in objs}
    for o in objs:
        ph, orb = o.get("physical") or {}, o.get("orbit") or {}
        parent = by_id.get(o.get("parent"))
        pname = f'<a href="{parent["id"]}.md">{parent["name"]}</a>' if parent else "—"
        L.append("| [{name}]({id}.md) | {cat} | {parent} | {mass} | {radius} | {dens} | {temp} | {period} | {moons} |".format(
            name=o["name"], id=o["id"], cat=CAT_ZH[o["category"]], parent=pname,
            mass=dash(fmt_mass(ph.get("mass_kg"))),
            radius=dash(fmt_radius(ph.get("radius_km"))),
            dens=dash(f"{ph['density_g_cm3']:g} g/cm³" if ph.get("density_g_cm3") else None),
            temp=dash(fmt_temp(ph.get("mean_temp_c"))),
            period=dash(fmt_period(orb.get("orbital_period_days"))),
            moons=dash((o.get("moons") or {}).get("count")),
        ))
    L.append("")
    L.append('<p class="obj-nav">需要筛选排序？回到<a href="../">天体总览工具页</a>。</p>')
    L.append("")
    return "\n".join(L)


def build_object(root, o, by_id, order):
    oid = o["id"]
    ph, orb = o.get("physical") or {}, o.get("orbit") or {}
    cat = o["category"]
    L = []
    L.append("---")
    L.append(f'description: "{o["name"]}（{o["name_en"]}）的天体数据：{dash(fmt_mass(ph.get("mass_kg")))}、'
             f'半径 {dash(fmt_radius(ph.get("radius_km")))}、密度 {dash(f"{ph["density_g_cm3"]:g} g/cm³" if ph.get("density_g_cm3") else None)}、'
             f'表面温度 {dash(fmt_temp(ph.get("mean_temp_c")))}。数据整理自 NASA 公开资料。"')
    L.append("---")
    L.append("")
    L.append(f'<div class="obj-hero">')
    L.append(f'  {img_block(o)}')
    L.append('  <div class="obj-hero-info">')
    L.append(f'    <span class="astro-badge {cat}">{CAT_ZH[cat]}</span>')
    L.append(f'    <h1>{o["name"]} <small>{o["name_en"]}</small></h1>')
    L.append(f'    <p class="obj-tagline">{o["tagline"]}</p>')
    keys = [fmt_mass(ph.get("mass_kg")), fmt_radius(ph.get("radius_km")),
            fmt_temp(ph.get("mean_temp_c")), f"{ph['density_g_cm3']:g} g/cm³" if ph.get("density_g_cm3") else None]
    L.append('    <div class="obj-keystats">')
    for k in keys:
        if k:
            L.append(f"      <span>{k}</span>")
    L.append("    </div>")
    L.append("  </div>")
    L.append("</div>")
    L.append("")
    parent = by_id.get(o.get("parent"))
    if parent:
        L.append(f'<p class="obj-parent">母天体：<a href="../{parent["id"]}/">{parent["name"]}</a>'
                 f' · 分类：{CAT_ZH[cat]}</p>')
    else:
        L.append(f'<p class="obj-parent">分类：{CAT_ZH[cat]}</p>')
    L.append("")

    L.append("## 物理参数")
    L.append("")
    L.append("| 参数 | 数值 |")
    L.append("|---|---|")
    rows = [
        ("质量", fmt_mass(ph.get("mass_kg"))),
        ("平均半径", fmt_radius(ph.get("radius_km"))),
        ("平均密度", f"{ph['density_g_cm3']:g} g/cm³" if ph.get("density_g_cm3") else None),
        ("表面重力", fmt_gravity(ph.get("gravity_m_s2"))),
        ("逃逸速度", fmt_velocity(ph.get("escape_velocity_km_s"))),
        ("平均表面温度", fmt_temp(ph.get("mean_temp_c"))),
        ("表面气压", fmt_pressure(ph.get("surface_pressure_bar"))),
        ("反照率", fmt_albedo(ph.get("albedo"))),
    ]
    if o.get("spectral_type"):
        rows.append(("光谱型", o["spectral_type"]))
    if o.get("luminosity_w"):
        rows.append(("光度", f"{o['luminosity_w']:.3g} W"))
    for k, v in rows:
        L.append(f"| {k} | {dash(v)} |")
    L.append("")

    if any(orb.get(k) is not None for k in
           ("semimajor_axis_km", "orbital_period_days", "orbital_velocity_km_s",
            "inclination_deg", "eccentricity", "obliquity_deg", "rotation_period_hours")):
        L.append("## 轨道参数")
        L.append("")
        L.append("| 参数 | 数值 |")
        L.append("|---|---|")
        orows = [
            ("半长轴", fmt_axis(orb.get("semimajor_axis_km"), o.get("parent"))),
            ("轨道周期", fmt_period(orb.get("orbital_period_days"))),
            ("平均轨道速度", fmt_velocity(orb.get("orbital_velocity_km_s"))),
            ("轨道倾角", fmt_angle(orb.get("inclination_deg"))),
            ("轨道偏心率", fmt_ecc(orb.get("eccentricity"))),
            ("转轴倾角", fmt_angle(orb.get("obliquity_deg"))),
            ("自转周期", fmt_rotation(orb.get("rotation_period_hours"))),
        ]
        for k, v in orows:
            L.append(f"| {k} | {dash(v)} |")
        L.append("")

    L.append("## 其他特征")
    L.append("")
    L.append("| 项目 | 数值 |")
    L.append("|---|---|")
    if o.get("atmosphere"):
        L.append(f'| 大气成分 | {o["atmosphere"]} |')
    else:
        L.append("| 大气成分 | — |")
    L.append(f'| 全球磁场 | {fmt_yn(o.get("magnetic_field"))} |')
    L.append(f'| 环系 | {fmt_yn(o.get("rings"))} |')
    moons = o.get("moons") or {}
    if moons.get("count") is not None:
        notable = "、".join(
            f'<a href="../{s["id"]}/">{s["name"]}</a>' if s else nm
            for nm, s in ((nm, next((x for x in data_objs if x["name"] == nm), None)) for nm in (moons.get("notable") or [])))
        cell = f'{moons["count"]} 颗' + (f'（ notable：{notable}）' if notable else "")
        L.append(f"| 已确认卫星 | {cell} |")
    disc = o.get("discovery") or {}
    disc_str = disc.get("known_since") or (
        f'{disc.get("discoverer")}，{disc.get("year")} 年' if disc.get("discoverer") else "—")
    L.append(f'| 发现 | {disc_str} |')
    L.append("")

    L.append('<section class="obj-source">')
    L.append("  <h2>数据来源</h2>")
    srcs = "、".join(o.get("sources") or [])
    L.append(f'  <p>来源标识：{srcs or "—"}；核对日期：{o.get("verified") or "—"}。'
             f'数值整理自 NASA NSSDC / JPL 公开资料（公共领域）。'
             f'发现错误请到 <a href="{REPO_URL}/issues">GitHub Issues</a> 反馈。</p>')
    L.append("</section>")
    L.append("")

    art_title, art_body = article_body(root, o["article"]) if o.get("article") else (None, None)
    if art_body:
        L.append('<section class="obj-article">')
        L.append(f'  <h2>延伸阅读：{art_title or o["name"]}</h2>')
        L.append("")
        L.append(art_body)
        L.append("")
        L.append("</section>")
        L.append("")

    idx = order.index(oid)
    if idx > 0:
        prev = by_id[order[idx - 1]]
        L.append(f'<p class="obj-nav">← 上一颗：<a href="../{prev["id"]}/">{prev["name"]}</a></p>')
    if idx < len(order) - 1:
        nxt = by_id[order[idx + 1]]
        L.append(f'<p class="obj-nav">下一颗：<a href="../{nxt["id"]}/">{nxt["name"]}</a> →</p>')
    L.append("")
    return "\n".join(L)


def build_data_page(data, objs):
    meta = data["meta"]
    L = []
    L.append("---")
    L.append('description: "下载星野笔记的天体数据集：%d 个太阳系天体的质量、半径、密度、温度、轨道与卫星数据，JSON 与 CSV 两种格式。"' % len(objs))
    L.append("---")
    L.append("")
    L.append("# 天体数据集")
    L.append("")
    L.append(f"本站收录的 {len(objs)} 个天体的结构化数据，提供 JSON 与 CSV 两种格式下载。"
             f"最近更新：{meta['updated']}。")
    L.append("")
    L.append('<div class="dl-cards">')
    L.append('  <a class="dl-card" href="../data/astro.json" download>')
    L.append("    <b>astro.json</b><span>完整数据（含来源与核对日期）</span>")
    L.append("  </a>")
    L.append('  <a class="dl-card" href="../data/astro_flat.csv" download>')
    L.append("    <b>astro_flat.csv</b><span>扁平表格（Excel 可直接打开）</span>")
    L.append("  </a>")
    L.append("</div>")
    L.append("")
    L.append("## 字段说明")
    L.append("")
    L.append("| 字段 | 含义 | 单位 |")
    L.append("|---|---|---|")
    L.append("| mass_kg | 质量 | kg |")
    L.append("| radius_km | 平均半径 | km |")
    L.append("| density_g_cm3 | 平均密度 | g/cm³ |")
    L.append("| mean_temp_c | 平均表面温度 | °C |")
    L.append("| semimajor_axis_km | 轨道半长轴 | km |")
    L.append("| orbital_period_days | 轨道周期 | 天 |")
    L.append("| moons.count | 已确认卫星数 | 颗 |")
    L.append("| sources / verified | 数据来源 / 核对日期 | — |")
    L.append("")
    L.append("## 许可与来源")
    L.append("")
    L.append(f"{meta['license_note']}")
    L.append("")
    L.append("主要数据源：")
    for s in meta.get("primary_sources", []):
        L.append(f"- {s}")
    L.append("")
    L.append("## 待补充")
    L.append("")
    L.append(f"{meta.get('pending', '—')}")
    L.append("")
    return "\n".join(L)


def build_csv(objs):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["id", "name", "name_en", "category", "parent", "mass_kg", "radius_km",
                "density_g_cm3", "mean_temp_c", "semimajor_axis_km", "orbital_period_days",
                "moons_count", "verified"])
    for o in objs:
        ph, orb = o.get("physical") or {}, o.get("orbit") or {}
        w.writerow([o["id"], o["name"], o["name_en"], o["category"], o.get("parent") or "",
                    ph.get("mass_kg") if ph.get("mass_kg") is not None else "",
                    ph.get("radius_km") if ph.get("radius_km") is not None else "",
                    ph.get("density_g_cm3") if ph.get("density_g_cm3") is not None else "",
                    ph.get("mean_temp_c") if ph.get("mean_temp_c") is not None else "",
                    orb.get("semimajor_axis_km") if orb.get("semimajor_axis_km") is not None else "",
                    orb.get("orbital_period_days") if orb.get("orbital_period_days") is not None else "",
                    (o.get("moons") or {}).get("count") if (o.get("moons") or {}).get("count") is not None else "",
                    o.get("verified") or ""])
    return buf.getvalue()


data_objs = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--check", action="store_true", help="只校验产物与 JSON 同步，不写盘")
    args = ap.parse_args()
    root = Path(args.root)
    data = load_data(root)
    objs = data["objects"]
    data_objs[:] = objs
    by_id = {o["id"]: o for o in objs}
    order = [o["id"] for o in objs]

    outputs = {"docs/index.md": build_index(data), "docs/data.md": build_data_page(data, objs),
               "docs/objects/index.md": build_object_index(data)}
    for o in objs:
        outputs[f"docs/objects/{o['id']}.md"] = build_object(root, o, by_id, order)
    csv_text = build_csv(objs)
    outputs["docs/data/astro_flat.csv"] = csv_text

    if args.check:
        stale = []
        for rel, content in outputs.items():
            p = root / rel
            norm = content.replace("\r\n", "\n")
            if not p.exists() or p.read_text(encoding="utf-8").replace("\r\n", "\n") != norm:
                stale.append(rel)
        if stale:
            print("以下产物与 astro.json 不同步：")
            for s in stale:
                print(f"  - {s}")
            print("请运行 python scripts/gen_pages.py 重新生成")
            return 1
        print(f"产物同步校验通过（{len(outputs)} 个文件）✓")
        return 0

    obj_dir = root / "docs" / "objects"
    obj_dir.mkdir(exist_ok=True)
    live = {f"docs/objects/{o['id']}.md" for o in objs}
    for p in obj_dir.glob("*.md"):
        rel = f"docs/objects/{p.name}"
        if rel not in live:
            p.unlink()
            print(f"清理过期详情页: {rel}")
    for rel, content in outputs.items():
        (root / rel).write_text(content, encoding="utf-8")
    print(f"已生成 {len(outputs)} 个文件：index.md / data.md / objects×{len(objs)} / astro_flat.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
