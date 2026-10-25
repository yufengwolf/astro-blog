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

# 页面版本戳：每次数据/贴图批量更新时递增，用于访客（和自己）判断浏览器是否缓存了旧版
VERSION = "1.6"
VERIFIED = "2026-10-24"
SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
CAT_ZH = {"star": "恒星", "planet": "行星", "dwarf_planet": "矮行星",
          "moon": "卫星", "asteroid": "小行星", "exoplanet": "系外行星",
          "black_hole": "黑洞", "nebula": "星云", "galaxy": "星系",
          "cluster": "星团", "structure": "大尺度结构", "comet": "彗星"}
AU_KM = 1.496e8
# 恒星单位换算基准（详情页/卡片对恒星用 R☉/M☉/L☉ 展示，底层仍存 km/kg 供大小对比）
R_SUN_KM = 695700.0
M_SUN_KG = 1.9884e30
L_SUN_W = 3.828e26
LY_KM = 9.4607e12            # 1 光年（km）——延展天体以光年计径，底层换算 km 存储
# 延展天体：以光年计径、参与对比页时按「全幅=等效球径」绘制（非真实形状，示意）
EXT_CATS = {"nebula", "galaxy", "cluster", "structure"}
# 只有实体固态/流体天体展示平均密度（黑洞/星云/星系等无意义）
DENSITY_CATS = {"planet", "dwarf_planet", "moon", "asteroid", "comet"}
# 展示顺序（首页 chips / hero 统计 / 总表分类列）
CAT_ORDER = ("star", "planet", "dwarf_planet", "moon", "galaxy", "nebula",
             "cluster", "black_hole", "structure", "asteroid", "comet",
             "exoplanet")


def sup(n):
    return str(n).translate(SUP)


def sci(v, digits=3):
    """科学计数法（Unicode 上标），用于量级极端的物理量（白矮星表面重力、
    脉冲星逃逸速度、10⁶ K 级温度、千倍太阳半径等）。"""
    if v == 0:
        return "0"
    e = math.floor(math.log10(abs(v)))
    m = v / 10 ** e
    return f"{m:.{digits}g}×10{sup(e)}"


def num3(v):
    """中段值（1e-3 ~ 1e3）用普通计数法，极端值用科学计数法——
    与 astro-compare.js / compare.js 的 num3() 保持一致。"""
    if v == 0:
        return "0"
    if 1e-3 <= abs(v) < 1e3:
        return f"{v:.3g}"
    return sci(v)


def fmt_mass(kg, cat=None):
    if kg is None:
        return None
    if cat in ("star", "black_hole", "galaxy", "cluster", "structure", "nebula"):
        return f"{num3(kg / M_SUN_KG)} M☉"
    e = math.floor(math.log10(kg))
    return f"{kg / 10 ** e:.3g}×10{sup(e)} kg"


def fmt_radius(r, cat=None):
    if r is None:
        return None
    if cat == "star":
        rs = r / R_SUN_KM
        if rs < 0.001:
            return f"{sci(rs)} R☉"          # 脉冲星/白矮星：1.44×10⁻⁵ R☉
        if rs >= 1000:
            return f"{rs:,.0f} R☉"          # 红超巨星：1,260 R☉
        return f"{rs:.3g} R☉"
    if cat == "black_hole":
        # 黑洞半径 = 史瓦西半径；小恒星级黑洞用 km，大质量用 AU
        if r >= 1e8:
            return f"{r / AU_KM:.3g} AU"
        return f"{r:,.0f} km"
    if cat in EXT_CATS:
        return f"{r / LY_KM:,.0f} 光年"
    return f"{r:,.1f} km" if r < 1000 else f"{r:,.0f} km"


def fmt_lum(w, cat=None):
    if w is None:
        return None
    if cat in ("star", "galaxy"):
        return f"{num3(w / L_SUN_W)} L☉"
    return f"{w:.3g} W"


def fmt_distance(ly):
    """距离自适应单位：<1 万光年用「光年」，<1 亿用「万光年」，更大用「亿光年」。"""
    if ly is None:
        return None
    if ly < 1e4:
        return f"{ly:,.0f} 光年"
    if ly < 1e9:
        return f"{ly / 1e4:,.0f} 万光年"
    return f"{ly / 1e8:,.0f} 亿光年"


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


def fmt_temp(t, cat=None):
    if t is None:
        return None
    if cat in ("star", "nebula", "structure"):
        k = t + 273.15
        if k >= 1e6:
            return f"{sci(k)} K"            # 中子星表面：1.6×10⁶ K
        return f"{k:.0f} K"
    return f"{t} °C"


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
    if v >= 1e5:
        return f"{sci(v)} km/s"             # 中子星逃逸速度：1.93×10⁵ km/s
    return f"{v:.3f} km/s" if v < 1 else f"{v:.2f} km/s"


def fmt_gravity(g):
    if g is None:
        return None
    if g >= 1e4 or g < 0.01:
        return f"{sci(g)} m/s²"             # 白矮星 4.26×10⁶ / 超巨星 2.82×10⁻³
    return f"{g:.2f} m/s²"


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
    """返回 (文章标题, 正文)；没有则 (None, None)。文章源在仓库根 articles/（docs 外，不单独建页）。
    标题优先取正文 H1，其次 frontmatter 的 title 字段。"""
    p = root / "articles" / f"{slug}.md"
    if not p.exists():
        return None, None
    raw = p.read_text(encoding="utf-8")
    fm_title = None
    fm = re.match(r"\A---\n(.*?)\n---\n", raw, flags=re.S)
    if fm:
        mt = re.search(r"^title:\s*(.+)$", fm.group(1), flags=re.M)
        if mt:
            fm_title = mt.group(1).strip().strip('"').strip("'")
    text = re.sub(r"\A---\n.*?\n---\n", "", raw, flags=re.S).strip()
    m = re.match(r"#\s+(.+)", text)
    title = m.group(1).strip() if m else fm_title
    if m:
        text = text[m.end():].strip()
    return title, text


def img_block(o, base="", show_credit=False):
    """天体图片块。base 为图片相对路径前缀（相对页面 URL，非源文件路径）：
    首页 index.md（URL /）传 ""；详情页 objects/<id>.md（URL /objects/<id>/，
    use_directory_urls 默认开启）需退两级到站根，传 "../../"。
    show_credit=True 时附带影像署名（仅详情页；image_credit/image_url 字段，
    由 scripts/nasa_image.py 登记 NASA 真实影像时写入）。"""
    cat = o["category"]
    img = o.get("image")
    if img:
        inner = (f'<div class="astro-img {cat}">'
                 f'<img src="{base}{img}" alt="{o["name"]}" loading="lazy"></div>')
        if show_credit and o.get("image_credit"):
            credit = o["image_credit"]
            if o.get("image_url"):
                credit = (f'<a href="{o["image_url"]}" target="_blank" '
                          f'rel="noopener">{credit}</a>')
            inner += f'<div class="astro-img-credit">影像：{credit}</div>'
            return f'<div class="obj-hero-imgwrap">{inner}</div>'
        return inner
    return (f'<div class="astro-img {cat} astro-img-fallback">'
            f'<span>{o["name"][0]}</span></div>')


def article_entries(root, o):
    """该天体关联的文章 [(slug, title)]。兼容 article（单个 slug）与 articles（数组）两种字段。"""
    slugs = []
    if o.get("article"):
        slugs.append(o["article"])
    for a in o.get("articles") or []:
        slug = a["slug"] if isinstance(a, dict) else a
        if slug not in slugs:
            slugs.append(slug)
    entries = []
    for slug in slugs:
        title, _ = article_body(root, slug)
        entries.append((slug, title or slug))
    return entries


def build_index(data):
    objs = data["objects"]
    n = len(objs)
    cats = {}
    for o in objs:
        cats[o["category"]] = cats.get(o["category"], 0) + 1
    L = []
    L.append("---")
    L.append('description: "收录 %d 个天体的结构化数据：质量、半径、密度、表面温度、'
             '轨道周期与卫星数量，支持按分类筛选、按任意数值排序。"' % n)
    L.append("---")
    L.append("")
    L.append('<div class="astro-hero">')
    L.append("  <h1>天体数据库</h1>")
    L.append(f'  <p class="astro-hero-sub">{n} 个天体的质量、半径、密度、温度</p>')
    L.append(f'  <p class="astro-hero-links"><a href="#articles">科普文章</a>'
             f'<span class="sep">·</span><a href="objects/">天体库总表</a></p>')
    L.append("</div>")
    L.append("")
    L.append('<div class="astro-toolbar">')
    L.append('  <input type="search" id="astro-search" placeholder="搜索天体…" aria-label="搜索天体">')
    L.append('  <div class="astro-chips" role="group" aria-label="按分类筛选">')
    L.append(f'    <button type="button" class="chip active" data-filter="all">全部 {n}</button>')
    for key in CAT_ORDER:
        if cats.get(key):
            L.append(f'    <button type="button" class="chip" data-filter="{key}">{CAT_ZH[key]} {cats[key]}</button>')
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
        cat = o["category"]
        if cat == "star":
            key_stat = fmt_lum(o.get("luminosity_w"), cat) or fmt_temp(ph.get("mean_temp_c"), cat)
        elif cat == "galaxy":
            key_stat = fmt_lum(o.get("luminosity_w"), cat) or fmt_radius(r, cat)
        elif cat == "black_hole":
            key_stat = fmt_mass(m, cat)
        elif cat in EXT_CATS:
            key_stat = fmt_temp(ph.get("mean_temp_c"), cat) or fmt_radius(r, cat)
        else:
            key_stat = fmt_temp(ph.get("mean_temp_c"), cat) or (
                f"{ph['density_g_cm3']:g} g/cm³" if ph.get("density_g_cm3") else None)
        # stats 去重：key_stat 回退到 fmt_radius 时会与半径重复（如星云"150 光年"×2）
        stats = []
        for s in (fmt_mass(m, cat), fmt_radius(r, cat), key_stat):
            if s and s not in stats:
                stats.append(s)
        stats_html = "".join(f"<span>{s}</span>" for s in stats)
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
    L.append(f'  <p>全部数值整理自 NASA / JPL / Wikipedia 等公开天文资料，每个天体页面均标注来源与核对日期（最近核对：{meta["updated"]}）。'
             f'发现数据错误？欢迎到 <a href="{REPO_URL}/issues">GitHub Issues</a> 反馈。</p>')
    L.append("</section>")
    L.append("")
    L.append(f'<p class="obj-version">数据版本 v{VERSION} · 收录 {meta["object_count"]} 个天体（全部配图）</p>')
    L.append("")
    return "\n".join(L)


def build_object_index(data):
    """docs/objects/index.md — 天体库总表：一页看全部天体的关键数据。"""
    objs = data["objects"]
    L = []
    L.append("---")
    L.append('description: "本站收录的全部 %d 个天体的关键数据总表：质量、半径、密度、温度、轨道周期与卫星数量。"' % len(objs))
    L.append("---")
    L.append("")
    L.append("# 天体库")
    L.append("")
    L.append(f"本站收录的全部 {len(objs)} 个天体。点击名称进入详情页（完整数据 + 科普文章）；"
             f"需要筛选排序？回到<a href=\"../\">天体总览工具页</a>。")
    L.append("")
    L.append("| 天体 | 分类 | 母天体 | 质量 | 半径/大小 | 密度 | 均温 | 距离 | 轨道周期 | 卫星数 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    by_id = {o["id"]: o for o in objs}
    for o in objs:
        ph, orb = o.get("physical") or {}, o.get("orbit") or {}
        parent = by_id.get(o.get("parent"))
        pname = f'<a href="{parent["id"]}.md">{parent["name"]}</a>' if parent else "—"
        L.append("| [{name}]({id}.md) | {cat} | {parent} | {mass} | {radius} | {dens} | {temp} | {dist} | {period} | {moons} |".format(
            name=o["name"], id=o["id"], cat=CAT_ZH[o["category"]], parent=pname,
            mass=dash(fmt_mass(ph.get("mass_kg"), o["category"])),
            radius=dash(fmt_radius(ph.get("radius_km"), o["category"])),
            dens=dash(f"{ph['density_g_cm3']:g} g/cm³" if (ph.get("density_g_cm3") and o["category"] in DENSITY_CATS) else None),
            temp=dash(fmt_temp(ph.get("mean_temp_c"), o["category"])),
            dist=dash(fmt_distance(o.get("distance_ly"))),
            period=dash(fmt_period(orb.get("orbital_period_days"))),
            moons=dash((o.get("moons") or {}).get("count")),
        ))
    L.append("")
    L.append('<details class="obj-fields">')
    L.append("<summary>字段说明（质量 kg · 半径 km · 密度 g/cm³ · 温度 °C · 半长轴 km · 周期 天 · 卫星数 颗）</summary>")
    L.append("")
    L.append("| 字段 | 含义 | 单位 |")
    L.append("|---|---|---|")
    L.append("| mass_kg | 质量 | kg |")
    L.append("| radius_km | 平均半径 | km |")
    L.append("| density_g_cm3 | 平均密度 | g/cm³ |")
    L.append("| mean_temp_c | 平均表面温度 | °C |")
    L.append("| mean_temp_c_bb | 有效温度（black-body 口径） | °C |")
    L.append("| mean_temp_c_surface | 表面温度 | °C |")
    L.append("| albedo / albedo_bond / albedo_geometric | 反照率（主值 / Bond 口径 / Geometric 口径） | — |")
    L.append("| surface_pressure_bar | 表面气压 | bar |")
    L.append("| inclination_deg / eccentricity | 轨道倾角 / 偏心率 | ° / — |")
    L.append("| semimajor_axis_km | 轨道半长轴 | km |")
    L.append("| orbital_period_days | 轨道周期 | 天 |")
    L.append("| moons.count | 已确认卫星数 | 颗 |")
    L.append("| distance_ly | 距离（恒星/星云/星系/黑洞为对地距离，单位光年） | 光年 |")
    L.append("| subtype | 类型细分（星云：发射/反射/行星状/超新星遗迹；星系：旋涡/椭圆/棒旋/不规则；恒星：黄矮星/红巨星/白矮星/中子星等） | — |")
    L.append("")
    L.append("</details>")
    L.append("")
    L.append('<p class="obj-nav">需要筛选排序？回到<a href="../">天体总览工具页</a>。</p>')
    L.append("")
    return "\n".join(L)


def sizecompare_payload(objs, img_prefix="../"):
    """天体对比页内嵌精简数据（含相对图片路径，供前端按真实比例绘制球体）。"""
    rows = []
    for o in objs:
        ph, orb = o.get("physical") or {}, o.get("orbit") or {}
        img = o.get("image")
        r = o.get("rings")
        rows.append({
            "id": o["id"], "name": o["name"], "en": o["name_en"],
            "cat": CAT_ZH[o["category"]], "cat_key": o["category"],
            "mass": ph.get("mass_kg"), "radius": ph.get("radius_km"),
            "density": ph.get("density_g_cm3"), "gravity": ph.get("gravity_m_s2"),
            "escape": ph.get("escape_velocity_km_s"), "temp": ph.get("mean_temp_c"),
            "lum": o.get("luminosity_w"), "distance": o.get("distance_ly"),
            "rotation": orb.get("rotation_period_hours"),
            "subtype": o.get("subtype"),
            "rings": bool(r) if r is not None else False,
            "image": (img_prefix + img) if img else None,
            # 延展天体（星云/星系/星团/大尺度结构）：贴图全幅≈天体本身，
            # 对比页按「全幅=等效球径」绘制（非真实形状，示意），跳过球体测量
            "ext": o["category"] in EXT_CATS,
        })
    return json.dumps({"rows": rows}, ensure_ascii=False)


def build_compare(data):
    """docs/compare.md — 天体对比工具页：两个天体选择框 + 按真实直径比例绘制球体 +
    体积/质量等直观倍数数据。纯前端渲染（内嵌数据），无后台。"""
    objs = data["objects"]
    n = len(objs)
    L = []
    L.append("---")
    L.append('description: "选择任意两个天体，按真实直径比例直观对比大小、体积与质量，支持一键交换与分享链接。"')
    L.append("---")
    L.append("")
    L.append("# 天体对比")
    L.append("")
    L.append(f"选择任意两个天体（可按类型筛选），下方会按**真实直径比例**绘制它们的球体，并列出体积、质量等关键数据的直观倍数。"
             f"尺寸悬殊时较小的一方会按比例缩为**一个点**（附实际倍数说明），不再失真放大；本站收录的 {n} 个天体均可参与对比。")
    L.append("")
    L.append('<div class="sizecmp-bar">')
    L.append('  <div class="sizecmp-pick">')
    L.append('    <span class="sizecmp-label">天体 A</span>')
    L.append('    <select id="sizecmp-cat-a" class="sizecmp-select sizecmp-cat" aria-label="筛选天体 A 的类型"></select>')
    L.append('    <select id="sizecmp-a" class="sizecmp-select" aria-label="选择天体 A"></select>')
    L.append("  </div>")
    L.append('  <div class="sizecmp-pick">')
    L.append('    <span class="sizecmp-label">天体 B</span>')
    L.append('    <select id="sizecmp-cat-b" class="sizecmp-select sizecmp-cat" aria-label="筛选天体 B 的类型"></select>')
    L.append('    <select id="sizecmp-b" class="sizecmp-select" aria-label="选择天体 B"></select>')
    L.append("  </div>")
    L.append("</div>")
    L.append("")
    L.append('<div class="sizecmp-scale" id="sizecmp-scale" hidden>')
    L.append('  <span class="sizecmp-scale-label">刻度</span>')
    L.append('  <button type="button" data-mode="linear">线性</button>')
    L.append('  <button type="button" data-mode="log">对数</button>')
    L.append("</div>")
    L.append("")
    L.append('<div class="sizecmp-viz">')
    L.append('  <div id="sizecmp-viz-canvas" class="sizecmp-viz-canvas"></div>')
    L.append('  <p class="sizecmp-viz-note" id="sizecmp-viz-note"></p>')
    L.append("</div>")
    L.append("")
    L.append("<h2>详细数据对比</h2>")
    L.append('<div class="sizecmp-detail" id="sizecmp-detail"></div>')
    L.append("")
    L.append("<h2>核心倍数</h2>")
    L.append('<div class="sizecmp-ratios" id="sizecmp-ratios"></div>')
    L.append("")
    L.append('<p class="sizecmp-share" id="sizecmp-share"></p>')
    L.append("")
    L.append(f'<script type="application/json" id="astro-sizecompare-data">{sizecompare_payload(objs)}</script>')
    L.append("")
    return "\n".join(L)


def build_object(root, o, by_id, order, registry=None):
    oid = o["id"]
    ph, orb = o.get("physical") or {}, o.get("orbit") or {}
    cat = o["category"]
    L = []
    L.append("---")
    desc_mass = dash(fmt_mass(ph.get("mass_kg"), cat))
    desc_radius = dash(fmt_radius(ph.get("radius_km"), cat))
    radius_label = {"black_hole": "史瓦西半径", "star": "半径"}.get(
        cat, "半径/大小" if cat in EXT_CATS else "平均半径")
    if cat == "star":
        desc_extra = f'光度 {dash(fmt_lum(o.get("luminosity_w"), cat))}'
    elif cat == "galaxy":
        desc_extra = f'光度 {dash(fmt_lum(o.get("luminosity_w"), cat))}'
    elif cat == "black_hole":
        desc_extra = f'距离 {dash(fmt_distance(o.get("distance_ly")))}'
    elif cat in EXT_CATS:
        desc_extra = f'距离 {dash(fmt_distance(o.get("distance_ly")))}'
    else:
        desc_extra = f'密度 {dash(f"{ph["density_g_cm3"]:g} g/cm³" if ph.get("density_g_cm3") else None)}'
    L.append(f'description: "{o["name"]}（{o["name_en"]}）的天体数据：{desc_mass}、'
             f'{radius_label} {desc_radius}、{desc_extra}、'
             f'表面温度 {dash(fmt_temp(ph.get("mean_temp_c"), cat))}。数据整理自公开天文资料。"')
    L.append("---")
    L.append("")
    L.append(f'<div class="obj-hero">')
    L.append(f'  {img_block(o, "../../", show_credit=True)}')
    L.append('  <div class="obj-hero-info">')
    L.append(f'    <span class="astro-badge {cat}">{CAT_ZH[cat]}</span>')
    L.append(f'    <h1>{o["name"]} <small>{o["name_en"]}</small></h1>')
    L.append(f'    <p class="obj-tagline">{o["tagline"]}</p>')
    dist = fmt_distance(o.get("distance_ly"))
    if cat == "star":
        keys = [fmt_mass(ph.get("mass_kg"), cat), fmt_radius(ph.get("radius_km"), cat),
                fmt_temp(ph.get("mean_temp_c"), cat), fmt_lum(o.get("luminosity_w"), cat)]
    elif cat == "black_hole":
        keys = [fmt_mass(ph.get("mass_kg"), cat), fmt_radius(ph.get("radius_km"), cat), dist]
    elif cat == "galaxy":
        keys = [fmt_mass(ph.get("mass_kg"), cat), fmt_radius(ph.get("radius_km"), cat),
                fmt_lum(o.get("luminosity_w"), cat), dist]
    elif cat in EXT_CATS:
        keys = [fmt_mass(ph.get("mass_kg"), cat), fmt_radius(ph.get("radius_km"), cat), dist]
    else:
        keys = [fmt_mass(ph.get("mass_kg"), cat), fmt_radius(ph.get("radius_km"), cat),
                fmt_temp(ph.get("mean_temp_c"), cat),
                f"{ph['density_g_cm3']:g} g/cm³" if ph.get("density_g_cm3") else None]
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

    L.append("## 物理参数")
    L.append("")
    L.append("| 参数 | 数值 |")
    L.append("|---|---|")
    def albedo_text():
        a = ph.get("albedo")
        ab, ag = ph.get("albedo_bond"), ph.get("albedo_geometric")
        base = fmt_albedo(a)
        if ab is not None and ag is not None:
            return f"{base}（Bond {ab:g} / Geometric {ag:g}）"
        if ab is not None and a is not None and abs(a - ab) < 1e-9:
            return f"{base}（Bond 口径）"
        if ag is not None and a is not None and abs(a - ag) < 1e-9:
            return f"{base}（Geometric 口径）"
        return base

    if cat == "black_hole":
        # 黑洞：实心球参数（密度/重力/逃逸/气压/反照率）均无意义，只列口径清晰的量
        rows = [
            ("质量", fmt_mass(ph.get("mass_kg"), cat)),
            ("史瓦西半径", fmt_radius(ph.get("radius_km"), cat)),
            ("距离", fmt_distance(o.get("distance_ly"))),
        ]
    elif cat in ("asteroid", "comet"):
        # 小天体：实心球参数大多不适用（彗星是脏雪球、形状不规则），只列有意义的量
        rows = [
            ("质量", fmt_mass(ph.get("mass_kg"), cat)),
            ("平均半径", fmt_radius(ph.get("radius_km"), cat)),
            *([("平均密度", f"{ph['density_g_cm3']:g} g/cm³")]
              if ph.get("density_g_cm3") else []),
            ("反照率", albedo_text()),
        ]
    elif cat in EXT_CATS:
        rows = [
            ("质量", fmt_mass(ph.get("mass_kg"), cat)),
            ("半径 / 大小", fmt_radius(ph.get("radius_km"), cat)),
            *([("光度", fmt_lum(o.get("luminosity_w"), cat))] if o.get("luminosity_w") else []),
            *([("平均温度", fmt_temp(ph.get("mean_temp_c"), cat))]
              if ph.get("mean_temp_c") is not None else []),
            ("距离", fmt_distance(o.get("distance_ly"))),
            *([("类型", o["subtype"])] if o.get("subtype") else []),
        ]
    else:
        rows = [
            ("质量", fmt_mass(ph.get("mass_kg"), cat)),
            ("平均半径", fmt_radius(ph.get("radius_km"), cat)),
            *([("平均密度", f"{ph['density_g_cm3']:g} g/cm³")]
              if ph.get("density_g_cm3") and cat in DENSITY_CATS else []),
            ("表面重力", fmt_gravity(ph.get("gravity_m_s2"))),
            ("逃逸速度", fmt_velocity(ph.get("escape_velocity_km_s"))),
            ("平均表面温度", fmt_temp(ph.get("mean_temp_c"), cat)),
            *([("有效温度（black-body 口径）", fmt_temp(ph["mean_temp_c_bb"], cat))]
              if ph.get("mean_temp_c_bb") is not None else []),
            *([("表面温度", fmt_temp(ph["mean_temp_c_surface"], cat))]
              if ph.get("mean_temp_c_surface") is not None else []),
            ("表面气压", fmt_pressure(ph.get("surface_pressure_bar"))),
            ("反照率", albedo_text()),
        ]
    if o.get("spectral_type"):
        rows.append(("光谱型", o["spectral_type"]))
    if cat == "star" and o.get("subtype"):
        rows.append(("恒星类型", o["subtype"]))
    if cat == "star" and o.get("luminosity_w"):
        rows.append(("光度", fmt_lum(o["luminosity_w"], cat)))
    if o.get("distance_ly") is not None and cat == "star":
        rows.append(("距离", fmt_distance(o["distance_ly"])))
    if o.get("constellation"):
        rows.append(("星座", o["constellation"]))
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
    if cat in EXT_CATS or cat == "black_hole":
        # 延展天体/黑洞：无大气/磁场/环系/卫星等固态天体概念，改列类型与备注
        if o.get("subtype"):
            L.append(f'| 类型 | {o["subtype"]} |')
        if o.get("members"):
            L.append(f'| 已知成员 | {o["members"]} |')
        if o.get("note"):
            L.append(f'| 备注 | {o["note"]} |')
    else:
        if o.get("atmosphere"):
            L.append(f'| 大气成分 | {o["atmosphere"]} |')
        else:
            L.append("| 大气成分 | — |")
        L.append(f'| 全球磁场 | {fmt_yn(o.get("magnetic_field"))} |')
        L.append(f'| 环系 | {fmt_yn(o.get("rings"))} |')
        if cat == "star":
            # 恒星补充：双星/聚星成员数（members）与备注（note）
            if o.get("members"):
                L.append(f'| 已知成员 | {o["members"]} |')
            if o.get("note"):
                L.append(f'| 备注 | {o["note"]} |')
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
    registry = registry or {}
    links = []
    for s in o.get("sources") or []:
        entry = registry.get(s)
        if entry:
            links.append(f'<a href="{entry["url"]}" target="_blank" rel="noopener">{entry["name"]}</a>')
        else:
            links.append(s)
    srcs = "、".join(links) if links else "—"
    L.append(f'  <p>数据来源：{srcs}；核对日期：{o.get("verified") or "—"}。'
             f'数值整理自 NASA NSSDC / JPL / Wikipedia 等公开天文资料。'
             f'发现错误请到 <a href="{REPO_URL}/issues">GitHub Issues</a> 反馈。</p>')
    L.append("</section>")
    L.append("")

    entries = article_entries(root, o)
    if entries:
        L.append('<section class="obj-articles">')
        L.append("  <h2>相关文章</h2>")
        L.append('  <ul class="astro-article-list">')
        for slug, title in entries:
            L.append(f'    <li><a href="#article-{slug}">{title}</a></li>')
        L.append("  </ul>")
        L.append("</section>")
        L.append("")
        for slug, title in entries:
            _, art_body = article_body(root, slug)
            if not art_body:
                continue
            L.append(f'<section class="obj-article" id="article-{slug}">')
            L.append(f'  <h2>延伸阅读：{title}</h2>')
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
    L.append(f'<p class="obj-version">数据版本 v{VERSION}（{VERIFIED} 核对）· {len(order)} 个天体已全部配图</p>')
    L.append("")
    return "\n".join(L)


def build_data_page(data, objs):
    meta = data["meta"]
    L = []
    L.append("---")
    L.append('description: "下载星野笔记的天体数据集：%d 个天体的质量、半径、密度、温度、轨道与卫星数据，JSON 与 CSV 两种格式。"' % len(objs))
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
    L.append("| mean_temp_c_bb | 有效温度（black-body 口径） | °C |")
    L.append("| mean_temp_c_surface | 表面温度 | °C |")
    L.append("| albedo / albedo_bond / albedo_geometric | 反照率（主值 / Bond 口径 / Geometric 口径） | — |")
    L.append("| surface_pressure_bar | 表面气压 | bar |")
    L.append("| inclination_deg / eccentricity | 轨道倾角 / 偏心率 | ° / — |")
    L.append("| semimajor_axis_km | 轨道半长轴 | km |")
    L.append("| orbital_period_days | 轨道周期 | 天 |")
    L.append("| moons.count | 已确认卫星数 | 颗 |")
    L.append("| sources / verified | 数据来源 / 核对日期 | — |")
    L.append("")
    L.append("## 许可与来源")
    L.append("")
    L.append(f"数值数据整理自 NASA NSSDC / JPL / Wikipedia 等公开天文资料（公共领域或自由许可）；一句话简介为本站原创撰写。")
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
               "docs/compare.md": build_compare(data),
               "docs/objects/index.md": build_object_index(data)}
    for o in objs:
        outputs[f"docs/objects/{o['id']}.md"] = build_object(
            root, o, by_id, order, data.get("source_registry") or {})
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
    live = {f"docs/objects/{o['id']}.md" for o in objs} | {"docs/objects/index.md"}
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
