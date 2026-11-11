#!/usr/bin/env python3
"""gen_pages.py — 从 docs/data/astro.json 生成站点页面。

产物：
  docs/index.md          首页天体总览（搜索/筛选/排序工具页，卡片预渲染）
  docs/objects/<id>.md   天体详情页（结构化数据表 + 卫星链接 + 合成科普文章）
  docs/data.md           数据集下载页
  docs/data/astro_flat.csv  扁平 CSV（数据集下载用）
  docs/js/i18n-data.js   全站双语数据（天体名 / 分类 / 简介，按 id 索引）

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
from html import escape as html_escape
from pathlib import Path

REPO_URL = "https://github.com/yufengwolf/astro-blog"

# 数据层自由文本英文译稿（按 id + 字段索引）。文件不存在时双语功能自动退化为中文，
# 译稿由 scripts/translate_fields.py 生成/增量维护，属可审阅数据、进 git。
FIELD_EN_FILE = Path(__file__).resolve().parent.parent / "docs/data/i18n_fields.json"


def load_field_en():
    try:
        return json.loads(FIELD_EN_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"objects": {}, "meta": {}}


FIELD_EN = load_field_en()


def en_attr(en):
    """生成 data-en 属性；无译稿时返回空串（该单元保持中文，由 i18n 词表兜底）。"""
    if not en:
        return ""
    return f' data-en="{html_escape(str(en), quote=True)}"'


def fen(oid, field):
    return (FIELD_EN.get("objects", {}).get(oid) or {}).get(field)

# 页面版本戳：每次数据/贴图/页面布局批量更新时递增，用于访客（和自己）判断浏览器是否缓存了旧版
VERSION = "1.9"
VERIFIED = "2026-10-24"
SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
CAT_ZH = {"star": "恒星", "planet": "行星", "dwarf_planet": "矮行星",
          "moon": "卫星", "asteroid": "小行星", "exoplanet": "系外行星",
          "black_hole": "黑洞", "nebula": "星云", "galaxy": "星系",
          "cluster": "星团", "structure": "大尺度结构", "comet": "彗星"}
# ---- 展示单位基准 ----
# 底层 astro.json 一律存 SI/天文基本单位（km / kg / W / ℃ 等效值），radius_km 存的是
# **半径**（已抽样核对：m42 半径 12 光年、note 明写「直径约 24 光年」；黑洞 note
# 明写「史瓦西半径约 128 AU」）。展示层统一换算成「直径 = 2 × 半径」，零数据迁移。
R_SUN_KM = 695700.0
M_SUN_KG = 1.9884e30
L_SUN_W = 3.828e26
R_EARTH_KM = 6371.0
M_EARTH_KG = 5.9722e24
AU_KM = 1.496e8
LY_KM = 9.4607e12            # 1 光年（km）
D_SUN_KM = 2 * R_SUN_KM
D_EARTH_KM = 2 * R_EARTH_KM
# 主单位阈值：直径超过 1e12 km（≈0.106 光年）改用光年，避免出现 13 位 km 数字
DIAM_LY_MIN_KM = 1e12
# 辅单位基准阈值：直径 ≥ 半个太阳直径用「× 太阳直径」，否则用「× 地球直径」；
# 质量 ≥ 0.01 M☉ 用 M☉，否则用 M⊕。纯按量级，不再按 category 硬编码主单位。
DIAM_SUN_MIN_KM = 0.5 * D_SUN_KM
MASS_SUN_MIN_KG = 0.01 * M_SUN_KG
# 延展天体：以光年计径、参与对比页时按「全幅=等效球径」绘制（非真实形状，示意）
EXT_CATS = {"nebula", "galaxy", "cluster", "structure"}
# 只有实体固态/流体天体展示平均密度（黑洞/星云/星系等无意义）
DENSITY_CATS = {"planet", "dwarf_planet", "moon", "asteroid", "comet"}
# 有「表面温度」概念的类别：温度主单位统一 K，这些类别额外括注 ℃
SURFACE_TEMP_CATS = DENSITY_CATS | {"exoplanet"}
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


def fmt_mass(kg, cat=None, compact=False):
    """质量：主单位一律 kg 科学计数；辅单位按量级给 M☉ / M⊕。

    compact=True 用于首页卡片、总表、SEO description 等空间有限处（只给主单位）。
    改单位规则时只需改本函数：对比页不再自己实现，改读 payload 里的 mass_text。
    """
    if kg is None:
        return None
    main = f"{sci(kg)} kg"
    if compact:
        return main
    if kg >= MASS_SUN_MIN_KG:
        return f"{main}（{num3(kg / M_SUN_KG)} M☉）"
    return f"{main}（{num3(kg / M_EARTH_KG)} M⊕）"


def size_label(cat):
    """展示口径统一为「直径」；黑洞是事件视界，延展天体是等效球径。"""
    if cat == "black_hole":
        return "事件视界直径"
    if cat in EXT_CATS:
        return "直径（等效球径）"
    if cat == "star":
        return "直径"
    return "平均直径"


def fmt_diameter(r, cat=None, compact=False):
    """半径(km) → 直径展示：主单位按量级（km / 光年），辅单位保留专业倍数。

    - d ≥ 1e12 km → 光年（星云/星系/大尺度结构，不给 km 辅单位：13 位数字无意义）
    - 其余 → km（≥1e9 用科学计数，≥1000 千分位整数，更小保留 1 位小数）
    - 辅单位：黑洞给 AU；直径 ≥ 0.5 D☉ 给「× 太阳直径」；否则「× 地球直径」
    底层 radius_km 保持半径原值不变，对比页 payload 也仍传 radius（半径比 = 直径比）。
    """
    if r is None:
        return None
    d = 2 * r
    if d >= DIAM_LY_MIN_KM:
        ly = d / LY_KM
        return f"{ly:,.0f} 光年" if ly >= 100 else f"{num3(ly)} 光年"
    if d >= 1e9:
        main = f"{sci(d)} km"
    elif d >= 1000:
        main = f"{d:,.0f} km"
    else:
        main = f"{d:,.1f} km"
    if compact:
        return main
    if cat == "black_hole" and d >= 1e8:
        return f"{main}（{d / AU_KM:,.0f} AU）"
    if d >= DIAM_SUN_MIN_KM:
        return f"{main}（{num3(d / D_SUN_KM)} × 太阳直径）"
    return f"{main}（{num3(d / D_EARTH_KM)} × 地球直径）"


def fmt_lum(w, cat=None, compact=False):
    """光度：主单位 W 科学计数，辅单位 L☉（仅在完整格式）。"""
    if w is None:
        return None
    main = f"{sci(w)} W"
    return main if compact else f"{main}（{num3(w / L_SUN_W)} L☉）"


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


def fmt_temp(t, cat=None, compact=False):
    """温度：底层 mean_temp_c 存的是「开尔文 − 273.15」等效摄氏值。

    v1.8 起主单位统一 K（此前恒星/星云显示 K、行星显示 °C，同一字段双口径）；
    有表面温度的固态天体在完整格式下额外括注 ℃，兼顾直观与专业。
    """
    if t is None:
        return None
    k = float(t) + 273.15
    if k >= 1e6:
        main = f"{sci(k)} K"                # 中子星表面：1.6×10⁶ K
    elif k >= 1000:
        main = f"{k:,.0f} K"
    else:
        main = f"{k:.0f} K"
    if compact or cat not in SURFACE_TEMP_CATS:
        return main
    # 统一保留 1 位小数（:g 去掉多余尾零），避免 K→℃ 换算的浮点噪声裸露
    v = round(float(t), 1)
    return f"{main}（{v:g} °C）"


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


def table_html(rows, en_map=None):
    """两列参数表 → 裸 HTML <table> 行列表。

    en_map: {单元格中文原文: 英文译稿}，由调用方按天体 id + 字段从
    docs/data/i18n_fields.json 构造，只做精确整串查找，不做名称归一化。

    空值行（None / "" / "—"）直接不渲染：稀疏天体不再出现整列破折号，
    太阳的轨道表从 7 行缩到实际有值的 2 行。全空时返回空列表，
    调用方据此跳过整个区块（不再输出只有表头的空表）。

    用 HTML 而非 Markdown 表格：可精确控制 DOM 结构，供 .obj-data-grid
    在桌面排成双列；同时长文本里的 "|" 不会破坏表格语法。
    表格不带 class，Material 的 .md-typeset table 样式照常生效。
    """
    kept = [(k, v) for k, v in rows if v is not None and v != "" and v != "—"]
    if not kept:
        return []
    out = ["<table>", "<thead><tr><th>参数</th><th>数值</th></tr></thead>", "<tbody>"]
    for k, v in kept:
        en = (en_map or {}).get(v) if isinstance(v, str) else None
        out.append(f'<tr><th scope="row">{k}</th><td{en_attr(en)}>{v}</td></tr>')
    out += ["</tbody>", "</table>"]
    return out


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
    由 scripts/nasa_image.py 登记 NASA 真实影像时写入）。
    影像署名的英文译稿按天体 id 从 i18n_fields.json 精确取，不做文本匹配。
    署名含来源链接时必须用 data-en-html 整块替换：data-en 走 textContent
    赋值，会把 <a> 抹掉，切回中文也无法还原链接。"""
    cat = o["category"]
    img = o.get("image")
    credit_en = fen(o.get("id"), "image_credit") if show_credit else None
    if img:
        inner = (f'<div class="astro-img {cat}">'
                 f'<img src="{base}{img}" alt="{o["name"]}" loading="lazy"></div>')
        if show_credit and o.get("image_credit"):
            credit = o["image_credit"]
            en_credit = credit_en or credit  # 无译稿时安全降级为原文
            if o.get("image_url"):
                href = html_escape(str(o["image_url"]), quote=True)
                credit = (f'<a href="{href}" target="_blank" rel="noopener">{credit}</a>')
                en_credit = (f'<a href="{href}" target="_blank" rel="noopener">{en_credit}</a>')
            en_html = "Image: " + en_credit
            inner += (f'<div class="astro-img-credit"'
                      f' data-en-html="{html_escape(en_html, quote=True)}">'
                      f'影像：{credit}</div>')
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
    L.append('description: "收录 %d 个天体的结构化数据：质量、直径、密度、表面温度、'
             '轨道周期与卫星数量，支持按分类筛选、按任意数值排序。"' % n)
    L.append("---")
    L.append("")
    L.append('<div class="astro-hero">')
    L.append("  <h1>天体数据库</h1>")
    L.append(f'  <p class="astro-hero-sub">{n} 个天体的质量、直径、密度、温度</p>')
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
    L.append('      <option value="radius">直径 ↓</option>')
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
        # 卡片用 compact 格式（只给主单位），避免辅单位把三行 stats 撑得过长
        if cat == "star":
            key_stat = fmt_lum(o.get("luminosity_w"), cat, True) or fmt_temp(ph.get("mean_temp_c"), cat, True)
        elif cat == "galaxy":
            key_stat = fmt_lum(o.get("luminosity_w"), cat, True) or fmt_diameter(r, cat, True)
        elif cat == "black_hole":
            key_stat = fmt_mass(m, cat, True)
        elif cat in EXT_CATS:
            key_stat = fmt_temp(ph.get("mean_temp_c"), cat, True) or fmt_diameter(r, cat, True)
        else:
            key_stat = fmt_temp(ph.get("mean_temp_c"), cat, True) or (
                f"{ph['density_g_cm3']:g} g/cm³" if ph.get("density_g_cm3") else None)
        # stats 去重：key_stat 回退到 fmt_diameter 时会与直径重复（如星云"300 光年"×2）
        stats = []
        for s in (fmt_mass(m, cat, True), fmt_diameter(r, cat, True), key_stat):
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
            # 中文形态「水星（Mercury）」是复合串，无法整串命中译表；
            # 用 data-en 按 id 精确给出英文名（不做名称匹配）。
            en = html_escape(str(o["name_en"]), quote=True)
            L.append(f'    <li><a href="objects/{o["id"]}/" data-en="{en}">'
                     f'{o["name"]}（{o["name_en"]}）</a></li>')
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
    L.append('description: "本站收录的全部 %d 个天体的关键数据总表：质量、直径、密度、温度、轨道周期与卫星数量。"' % len(objs))
    L.append("---")
    L.append("")
    L.append("# 天体库")
    L.append("")
    L.append(f"本站收录的全部 {len(objs)} 个天体。点击名称进入详情页（完整数据 + 科普文章）；"
             f"需要筛选排序？回到<a href=\"../\">天体总览工具页</a>。")
    L.append("")
    L.append("| 天体 | 分类 | 母天体 | 质量 | 直径 | 密度 | 均温 | 距离 | 轨道周期 | 卫星数 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    by_id = {o["id"]: o for o in objs}
    for o in objs:
        ph, orb = o.get("physical") or {}, o.get("orbit") or {}
        parent = by_id.get(o.get("parent"))
        pname = f'<a href="{parent["id"]}.md">{parent["name"]}</a>' if parent else "—"
        L.append("| [{name}]({id}.md) | {cat} | {parent} | {mass} | {radius} | {dens} | {temp} | {dist} | {period} | {moons} |".format(
            name=o["name"], id=o["id"], cat=CAT_ZH[o["category"]], parent=pname,
            mass=dash(fmt_mass(ph.get("mass_kg"), o["category"], True)),
            radius=dash(fmt_diameter(ph.get("radius_km"), o["category"], True)),
            dens=dash(f"{ph['density_g_cm3']:g} g/cm³" if (ph.get("density_g_cm3") and o["category"] in DENSITY_CATS) else None),
            temp=dash(fmt_temp(ph.get("mean_temp_c"), o["category"], True)),
            dist=dash(fmt_distance(o.get("distance_ly"))),
            period=dash(fmt_period(orb.get("orbital_period_days"))),
            moons=dash((o.get("moons") or {}).get("count")),
        ))
    L.append("")
    # md_in_html 扩展已启用：details 必须声明 markdown="1"，内部表格才会被解析成
    # 真正的 <table>（否则整段以纯文本 "| 字段 | 含义 |" 显示）。
    L.append('<details class="obj-fields" markdown="1">')
    L.append('<summary data-en="Field reference (raw units in the CSV: mass kg · radius km · density g/cm³ · temperature °C · semi-major axis km · period days · moon count)">字段说明（下载 CSV 的原始单位：质量 kg · 半径 km · 密度 g/cm³ · 温度 ℃ · 半长轴 km · 周期 天 · 卫星数 颗）</summary>')
    L.append("")
    L.append('<p data-en-html="&lt;strong&gt;Note:&lt;/strong&gt; this table describes the &lt;strong&gt;raw fields&lt;/strong&gt; in &lt;code&gt;astro.json&lt;/code&gt; / CSV. &lt;code&gt;radius_km&lt;/code&gt; stores the &lt;strong&gt;radius&lt;/strong&gt;; pages and cards show &lt;strong&gt;diameter = 2 × radius&lt;/strong&gt;, switching the primary unit between km and light-years by magnitude, with Earth/Solar diameter multiples, M⊕ / M☉ and °C annotations."><strong>注意：</strong>本表描述的是 <code>astro.json</code> / CSV 的<strong>原始字段</strong>。'
             '<code>radius_km</code> 存的是<strong>半径</strong>；页面与卡片统一按「直径 = 2 × 半径」展示，'
             '主单位按量级自动切换 km / 光年，并辅以地球或太阳直径倍数、M⊕ / M☉、℃ 括注。</p>')
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
            # v1.8 起：单位字符串由生成器统一产出（全站唯一实现），compare.js
            # 直接读这些字段，不再自带第二套 fmtRadius/fmtMassCat/fmtTemp/fmtLum。
            # 半径仍按原值传给可视化（半径比 = 直径比，缩放计算不受影响）。
            "diameter_text": fmt_diameter(ph.get("radius_km"), o["category"]),
            "mass_text": fmt_mass(ph.get("mass_kg"), o["category"]),
            "temp_text": fmt_temp(ph.get("mean_temp_c"), o["category"]),
            "lum_text": fmt_lum(o.get("luminosity_w"), o["category"]),
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
    en_intro = (f"Pick any two objects (filterable by type); below, spheres are drawn to true diameter scale, "
               f"listing intuitive multiples of volume, mass and other key data. When sizes differ vastly, "
               f"the smaller one is scaled to a dot (with actual ratio noted), avoiding distortion; "
               f"all {n} catalogued objects can be compared.")
    zh_intro = (f"选择任意两个天体（可按类型筛选），下方会按<strong>真实直径比例</strong>绘制它们的球体，"
               f"并列出体积、质量等关键数据的直观倍数。尺寸悬殊时较小的一方会按比例缩为<strong>一个点</strong>"
               f"（附实际倍数说明），不再失真放大；本站收录的 {n} 个天体均可参与对比。")
    L.append(f'<p data-en="{en_intro}">{zh_intro}</p>')
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


# ---- 3D 可视化覆盖契约（P3：viz-manifest.json）----
# 主站与 3D 仓库解耦：哪些天体有 3D 模型、去哪个外链，全在 viz-manifest.json。
# 缺失条目 = 该天体无 3D 覆盖 → 详情页不渲染 3D 块（优雅降级）。
VIZ_MANIFEST = {}
VIZ_REPO_NAME = {"solar-3d": "astro-solar-3d"}


def load_viz_manifest(root):
    p = root / "viz-manifest.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("objects", {})
    except Exception:
        return {}


def viz_block(oid):
    """详情页 3D 嵌入块：复用 .solar-embed 组件（全屏/铺满/源切换由 solar-embed.js 处理）。

    无覆盖 → 返回空字符串（不渲染）。多来源 → 渲染来源切换按钮，默认嵌入第一个。
    """
    entries = VIZ_MANIFEST.get(oid)
    if not entries:
        return ""
    primary = entries[0]
    src_btns = ""
    if len(entries) > 1:
        btns = "".join(
            f'<button type="button" class="solar-src-btn" data-src="{e["src"]}">{e["title"]}</button>'
            for e in entries)
        src_btns = btns
    repos = "、".join(VIZ_REPO_NAME.get(e["repo"], e["repo"]) for e in entries)
    title_attr = primary.get("name") or primary["title"]
    full = primary.get("full", primary["src"])
    return (
        '<div class="solar-embed obj-viz">\n'
        '  <div class="solar-bar">\n'
        '    <span class="solar-title">3D 交互可视化</span>\n'
        f'    <span class="solar-bar-btns">{src_btns}</span>\n'
        '  </div>\n'
        '  <div class="solar-frame">\n'
        f'    <iframe src="{primary["src"]}" title="{title_attr} 三维模型" '
        'loading="lazy" allowfullscreen allow="fullscreen"></iframe>\n'
        '  </div>\n'
        f'  <p class="obj-viz-note">由外部 3D 项目（{repos}）提供，与本站数据独立维护；'
        f'嵌入为精简界面，<a href="{full}" target="_blank" rel="noopener">打开完整交互版 ↗</a>。</p>\n'
        '</div>'
    )


def build_object(root, o, by_id, order, registry=None):
    oid = o["id"]
    ph, orb = o.get("physical") or {}, o.get("orbit") or {}
    cat = o["category"]
    # 数据层自由文本译稿：按 id + 字段取出，再以「中文原文」为精确键供表格渲染。
    # 源文案改动后这里查不到 → 单元保持中文，由 i18n.js 漂移检测暴露。
    fmap = FIELD_EN.get("objects", {}).get(oid, {})
    en_map = {}
    for f in ("subtype", "note", "atmosphere", "spectral_type", "constellation",
              "image_credit", "members", "host_star"):
        v = o.get(f)
        if isinstance(v, str) and v and fmap.get(f):
            en_map[v] = fmap[f]
    L = []
    L.append("---")
    # SEO description 用 compact 格式控制长度，且必须给「直径」口径（v1.8 起）
    desc_mass = dash(fmt_mass(ph.get("mass_kg"), cat, True))
    desc_diameter = dash(fmt_diameter(ph.get("radius_km"), cat, True))
    size_lbl = size_label(cat)
    if cat in ("star", "galaxy"):
        desc_extra = f'光度 {dash(fmt_lum(o.get("luminosity_w"), cat, True))}'
    elif cat == "black_hole" or cat in EXT_CATS:
        desc_extra = f'距离 {dash(fmt_distance(o.get("distance_ly")))}'
    else:
        desc_extra = f'密度 {dash(f"{ph["density_g_cm3"]:g} g/cm³" if ph.get("density_g_cm3") else None)}'
    L.append(f'description: "{o["name"]}（{o["name_en"]}）的天体数据：{desc_mass}、'
             f'{size_lbl} {desc_diameter}、{desc_extra}、'
             f'温度 {dash(fmt_temp(ph.get("mean_temp_c"), cat, True))}。数据整理自公开天文资料。"')
    # 详情页去掉右侧 TOC 栏：正文列从 ~764px 放宽到 ~1006px（1440 视口），
    # 给双列参数表与后续 3D 嵌入腾出宽度；页面短、标题少，TOC 价值低于宽度
    L.append("hide:")
    L.append("  - toc")
    L.append("---")
    L.append("")
    L.append(f'<div class="obj-hero">')
    L.append(f'  {img_block(o, "../../", show_credit=True)}')
    L.append('  <div class="obj-hero-info">')
    L.append(f'    <span class="astro-badge {cat}">{CAT_ZH[cat]}</span>')
    L.append(f'    <h1>{o["name"]} <small>{o["name_en"]}</small></h1>')
    L.append(f'    <p class="obj-tagline" data-obj-id="{o["id"]}">{o["tagline"]}</p>')
    # 速览摘要：只留 2 个最具辨识度的量，压成单行（compact 保证移动端不折成多行）。
    # 完整带辅单位的明细统一放在下面的「物理参数」表，避免同屏重复。
    summary = []
    size = fmt_diameter(ph.get("radius_km"), cat, True)
    mass = fmt_mass(ph.get("mass_kg"), cat, True)
    if size:
        summary.append(f"{size_lbl} {size}")
    if mass:
        summary.append(f"质量 {mass}")
    if summary:
        L.append(f'    <p class="obj-summary">{" · ".join(summary)}</p>')
    L.append("  </div>")
    L.append("</div>")
    L.append("")
    parent = by_id.get(o.get("parent"))
    if parent:
        L.append(f'<p class="obj-parent">母天体：<a href="../{parent["id"]}/">{parent["name"]}</a>'
                 f' · 分类：{CAT_ZH[cat]}</p>')
    else:
        L.append(f'<p class="obj-parent">分类：{CAT_ZH[cat]}</p>')

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
        phys_rows = [
            ("质量", fmt_mass(ph.get("mass_kg"), cat)),
            ("事件视界直径", fmt_diameter(ph.get("radius_km"), cat)),
            ("距离", fmt_distance(o.get("distance_ly"))),
        ]
    elif cat in ("asteroid", "comet"):
        # 小天体：实心球参数大多不适用（彗星是脏雪球、形状不规则），只列有意义的量
        phys_rows = [
            ("质量", fmt_mass(ph.get("mass_kg"), cat)),
            ("平均直径", fmt_diameter(ph.get("radius_km"), cat)),
            *([("平均密度", f"{ph['density_g_cm3']:g} g/cm³")]
              if ph.get("density_g_cm3") else []),
            ("反照率", albedo_text()),
        ]
    elif cat in EXT_CATS:
        phys_rows = [
            ("质量", fmt_mass(ph.get("mass_kg"), cat)),
            ("直径（等效球径）", fmt_diameter(ph.get("radius_km"), cat)),
            *([("光度", fmt_lum(o.get("luminosity_w"), cat))] if o.get("luminosity_w") else []),
            *([("平均温度", fmt_temp(ph.get("mean_temp_c"), cat))]
              if ph.get("mean_temp_c") is not None else []),
            ("距离", fmt_distance(o.get("distance_ly"))),
            *([("类型", o["subtype"])] if o.get("subtype") else []),
        ]
    else:
        phys_rows = [
            ("质量", fmt_mass(ph.get("mass_kg"), cat)),
            ("平均直径", fmt_diameter(ph.get("radius_km"), cat)),
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
        phys_rows.append(("光谱型", o["spectral_type"]))
    if cat == "star" and o.get("subtype"):
        phys_rows.append(("恒星类型", o["subtype"]))
    if cat == "star" and o.get("luminosity_w"):
        phys_rows.append(("光度", fmt_lum(o["luminosity_w"], cat)))
    if o.get("distance_ly") is not None and cat == "star":
        phys_rows.append(("距离", fmt_distance(o["distance_ly"])))
    if o.get("constellation"):
        phys_rows.append(("星座", o["constellation"]))
    blocks = []
    t = table_html(phys_rows, en_map)
    if t:
        blocks.append(("物理参数", "physical", t))

    orows = [
        ("半长轴", fmt_axis(orb.get("semimajor_axis_km"), o.get("parent"))),
        ("轨道周期", fmt_period(orb.get("orbital_period_days"))),
        ("平均轨道速度", fmt_velocity(orb.get("orbital_velocity_km_s"))),
        ("轨道倾角", fmt_angle(orb.get("inclination_deg"))),
        ("轨道偏心率", fmt_ecc(orb.get("eccentricity"))),
        ("转轴倾角", fmt_angle(orb.get("obliquity_deg"))),
        ("自转周期", fmt_rotation(orb.get("rotation_period_hours"))),
    ]
    t = table_html(orows, en_map)
    if t:
        blocks.append(("轨道参数", "orbit", t))

    feat_rows = []
    if cat in EXT_CATS or cat == "black_hole":
        # 延展天体/黑洞：无大气/磁场/环系/卫星等固态天体概念，改列类型与备注
        if o.get("subtype"):
            feat_rows.append(("类型", o["subtype"]))
        if o.get("members"):
            feat_rows.append(("已知成员", o["members"]))
        if o.get("note"):
            feat_rows.append(("备注", o["note"]))
    else:
        if o.get("atmosphere"):
            feat_rows.append(("大气成分", o["atmosphere"]))
        # 三态里 None 表示「根本没有这项数据」，不再输出「未知」占位行；False 才是明确的「否」
        if o.get("magnetic_field") is not None:
            feat_rows.append(("全球磁场", fmt_yn(o["magnetic_field"])))
        if o.get("rings") is not None:
            feat_rows.append(("环系", fmt_yn(o["rings"])))
        if cat == "star":
            # 恒星补充：双星/聚星成员数（members）与备注（note）
            if o.get("members"):
                feat_rows.append(("已知成员", o["members"]))
            if o.get("note"):
                feat_rows.append(("备注", o["note"]))
    moons = o.get("moons") or {}
    if moons.get("count") is not None:
        notable = "、".join(
            f'<a href="../{s["id"]}/">{s["name"]}</a>' if s else nm
            for nm, s in ((nm, next((x for x in data_objs if x["name"] == nm), None)) for nm in (moons.get("notable") or [])))
        cell = f'{moons["count"]} 颗' + (f'（主要：{notable}）' if notable else "")
        feat_rows.append(("已确认卫星", cell))
    disc = o.get("discovery") or {}
    disc_str = disc.get("known_since") or (
        f'{disc.get("discoverer")}，{disc.get("year")} 年' if disc.get("discoverer") else None)
    if disc_str:
        feat_rows.append(("发现", disc_str))
    t = table_html(feat_rows, en_map)
    if t:
        blocks.append(("其他特征", "features", t))

    L.append("")  # 与 obj-parent 的 raw HTML 块显式分隔，避免被合并进同一块解析
    # P3：3D 交互可视化块（有覆盖才渲染；无则优雅降级）。放在 hero 正下方、数据栅格之前，
    # 让访客先看到该天体的真 3D / 尺寸对比，再读参数表；无覆盖的天体则不渲染（不占位置）。
    vb = viz_block(oid)
    if vb:
        L.append("")
        L.append(vb)
        L.append("")
    # 三张参数表装进同一个 grid：桌面双列、移动单列，消除全宽竖排造成的右侧空白。
    # 输出为单个 raw HTML 块（块内不插空行，否则 Python-Markdown 会提前结束 HTML 块）。
    if blocks:
        L.append('<div class="obj-data-grid">')
        for title, anchor, t in blocks:
            L.append('<section class="obj-data-block">')
            L.append(f'<h2 id="{anchor}">{title}</h2>')
            L.extend(t)
            L.append('</section>')
        L.append('</div>')
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
    # 「主要数据源：」与列表之间必须留空行，否则整段被 Markdown 塞进一个 <p>，
    # 既渲染不出 <ul>，也让 i18n.js 按整串精确匹配的数据层译表无法命中。
    L.append("主要数据源：")
    L.append("")
    for s in meta.get("primary_sources", []):
        L.append(f"- {s}")
    L.append("")
    L.append("## 待补充")
    L.append("")
    L.append(f"{meta.get('pending', '—')}")
    L.append("")
    return "\n".join(L)


# 全站双语：分类英文名与 i18n.js 的 CATS、universe-data.json 的 category_i18n 同口径
CAT_EN = {"star": "Star", "planet": "Planet", "dwarf_planet": "Dwarf planet",
          "moon": "Moon", "galaxy": "Galaxy", "nebula": "Nebula",
          "cluster": "Cluster", "black_hole": "Black hole",
          "structure": "Large-scale structure", "asteroid": "Asteroid",
          "comet": "Comet", "exoplanet": "Exoplanet"}


def build_i18n_data(data):
    """docs/js/i18n-data.js — 全站双语数据（按 id 索引，不做名称匹配）。

    i18n.js 只读这份数据：天体名 / 分类 / 一句话简介的中英双份。
    tagline_en 缺省时该条只有中文，英文模式自动保留中文原文（安全降级）。
    fields 是数据层自由文本（类型细分 / 备注 / 大气 / 星座 / 影像署名 / 来源清单）
    的精确整串译表，按 astro.json 的 id + 字段从 i18n_fields.json 构造：
    运行时只做「中文原文整串相等」查找，不是名称模糊匹配。
    """
    objs = data["objects"]
    by_id = {o["id"]: o for o in objs}
    fields = {}
    for oid, fmap in FIELD_EN.get("objects", {}).items():
        src = by_id.get(oid, {})
        for f, en in fmap.items():
            zh = src.get(f)
            if isinstance(zh, str) and zh and isinstance(en, str) and en:
                fields[zh] = en
    for zh, en in zip(data["meta"].get("primary_sources", []),
                      FIELD_EN.get("meta", {}).get("primary_sources", [])):
        if en:
            fields[zh] = en
    p_zh = data["meta"].get("pending")
    p_en = FIELD_EN.get("meta", {}).get("pending")
    if p_zh and p_en:
        fields[p_zh] = p_en
    payload = {
        "names": {o["id"]: [o["name"], o["name_en"]] for o in objs},
        "cats": {k: [CAT_ZH[k], CAT_EN[k]] for k in CAT_ZH},
        "taglines": {o["id"]: [o["tagline"], o.get("tagline_en") or None]
                     for o in objs if o.get("tagline")},
        "fields": fields,
    }
    return ("/* 由 scripts/gen_pages.py 从 docs/data/astro.json 生成，请勿手改 */\n"
            "window.SITE_I18N_DATA = "
            + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")


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
    global VIZ_MANIFEST
    VIZ_MANIFEST = load_viz_manifest(root)

    outputs = {"docs/index.md": build_index(data), "docs/data.md": build_data_page(data, objs),
               "docs/compare.md": build_compare(data),
               "docs/objects/index.md": build_object_index(data),
               "docs/js/i18n-data.js": build_i18n_data(data)}
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
