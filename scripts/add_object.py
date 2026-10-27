#!/usr/bin/env python3
"""add_object.py — 通用天体录入引擎（AI 编排层的数据入口）。

设计目标（2026-10-26 用户拍板）：用户只给一个名字（甚至不知道类型），AI 负责
定位类别、拉取数据特征、录入 astro.json；图片交给 sync_images.py 按类别路由
（恒星/黑洞套模板；行星/星云/星系等可能需人工审核）。
add_object 写入 astro.json 成功后，**末尾会自动调用 sync_images.py --ids <新id>**
为新对象出图（可用 --no-sync 关闭）。

三种录入模式：
  --name  "天狼星"               AI 从自身知识起草（LLM 分类 + 抽取；知名天体给最佳近似值，仅真未知才 null）
  --facts "天狼星是大犬座主星…"  AI 从你提供的文本抽取（配合 agent 的 WebSearch 使用）
  --json  '{...}'               直接结构化录入（绕过 LLM，最可控）

通用逻辑（不随模式变）：
  - 按 category 套 schema 模板（复用 insert_* 的 base/star/ext 口径）
  - 有 M、R 即派生 重力/逃逸速度/密度（保证 lint 派生量校验自洽）
  - 自动登记 source_registry、填 image 占位（image_locked=False → sync_images 生成）
  - 幂等：id 已存在则原地更新（不重复追加），并打印摘要
  - --dry-run 只打印将写入的对象 + 图片计划 + 人工审核标记，不落盘、不调 sync_images
  - 写入成功后自动调用 sync_images.py 为新对象出图（--no-sync 可关闭）
  - 出图后自动重新生成站点页面并构建（gen_pages + mkdocs build --strict），
    --no-pages 可关闭（关闭后需手动 gen_pages + mkdocs build 才能在网页看到）

图片计划（仅打印/标记，真正出图在 sync_images.py）：
  star/sun        → 模板（build_star_images 按 subtype→9 类套用，无需新图，不需审核）
  black_hole      → 模板（gen_bigscale 程序化，无需审核）
  其余类别        → 程序化兜底 + 可选 NASA 真图，打印「需人工审核」标记
"""
import argparse
import json
import math
import re
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASTRO = ROOT / "docs" / "data" / "astro.json"
TODAY = date.today().isoformat()

# ---------------------------------------------------------------- 物理常量
M_SUN = 1.9884e30
L_SUN = 3.828e26
R_SUN_KM = 695700.0
RS_KM_PER_MSUN = 2.95325008
LY_KM = 9.4607e12
G = 6.674e-11

CATEGORIES = {"star", "planet", "dwarf_planet", "moon", "asteroid", "exoplanet",
              "black_hole", "nebula", "galaxy", "cluster", "structure", "comet"}
EXT_CATS = {"nebula", "galaxy", "cluster", "structure"}
DENSITY_CATS = {"planet", "dwarf_planet", "moon", "asteroid", "comet"}

# 新录入对象的初始 image_source（供 query.py --image-source 筛选）。
# 恒星套豆包模板；黑洞/大尺度/固态体先用程序化占位，后续可换 NASA 真图。
IMG_SRC_INIT = {
    "star": "doubao_template",
    "black_hole": "programmatic",
}


# ---------------------------------------------------------------- LLM 客户端
# 批量模式专用：只打豆包 :9090（用户确认豆包可联网，做两发一致性对拍）
DOUBAO_EP = [("http://127.0.0.1:9090/v1", "doubao-2.1")]


def llm_chat(system, user, model_pref=None, endpoints=None):
    """OpenAI 兼容：豆包(:9090) 默认优先，本地 llama-server(:8080) 兜底。

    返回 (助手文本, 来源标签) 元组；来源标签为 'llm_doubao' 或 'llm_local'，
    用于回填 astro.json 的 data_source，让用户能筛出"哪些数据是 AI 吐的、靠哪个模型"。

    稳定性：整轮（所有端点各试一次）失败后进行指数退避重试，最多 3 轮
    （退避 1s / 2s / 4s，封顶 8s）。豆包偶发 502 / 本地瞬时不可达时自动吸收，
    不轻易让单条抽取整体失败。
    """
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    if endpoints is None:
        # 豆包优先（默认 doubao-2.1）；本地 8080 作为兜底
        endpoints = [("http://127.0.0.1:9090/v1", model_pref or "doubao-2.1"),
                     ("http://127.0.0.1:8080/v1", model_pref)]
    last_err = None
    for attempt in range(3):
        for base, model in endpoints:
            try:
                payload = {"messages": messages, "temperature": 0.2, "max_tokens": 1600}
                if model:
                    payload["model"] = model
                req = urllib.request.Request(
                    base + "/chat/completions",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    d = json.loads(r.read().decode())
                text = d["choices"][0]["message"]["content"]
                src = "llm_doubao" if "9090" in base else "llm_local"
                return text, src
            except Exception as e:
                last_err = e
                continue
        if attempt < 2:
            time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"LLM 调用失败（已试本地+豆包，3 轮重试）：{last_err}")


def _extract_prompts(name, category_hint, facts_text):
    """构造抽取用的 (system_prompt, user_prompt)。单条与批量两发共用。"""
    sys_p = (
        "你是天文数据库录入助手。根据用户提供的天体名称（及可选文本），"
        "输出严格 JSON，字段契约：\n"
        "{\n"
        '  "id": "ascii-slug 建议（可选，小写无空格，如 sirius_a）",\n'
        '  "name": "中文名（如 南河三）",\n'
        '  "name_en": "英文名",\n'
        '  "category": "star|planet|dwarf_planet|moon|asteroid|comet|black_hole|nebula|galaxy|cluster|structure",\n'
        '  "tagline": "一句话中文简介（≤40字）",\n'
        '  "parent": null 或 母天体 id（行星→恒星、卫星→行星、残骸→星云/星团等），\n'
        '  "subtype": "恒星类型/星云类型等细分（恒星务必给，如 红超巨星（M1Iab））",\n'
        '  "spectral_type": "恒星光谱型（如 M1Iab），非恒星为 null",\n'
        '  "constellation": "星座中文名（可选）",\n'
        '  "distance_ly": 数字或 null,\n'
        '  "physical": {\n'
        '     "mass_sun": 太阳质量数 或 null,\n'
        '     "mass_kg": kg 或 null,\n'
        '     "radius_sun": 太阳半径数（恒星）或 null,\n'
        '     "radius_km": km 或 null,\n'
        '     "radius_ly": 光年（延展天体 星云/星系/星团/结构）或 null,\n'
        '     "temp_k": 开尔文 或 null,\n'
        '     "lum_sun": 太阳光度数（恒星/星系）或 null,\n'
        '     "density_g_cm3": 或 null,\n'
        '     "albedo": 或 null,\n'
        '     "surface_pressure_bar": 或 null\n'
        "  },\n"
        '  "orbit": {\n'
        '     "semimajor_axis_au": 轨道半长轴(天文单位 AU) 或 null,\n'
        '     "orbital_period_years": 公转周期(年) 或 null,\n'
        '     "orbital_velocity_km_s": 轨道速度(km/s) 或 null,\n'
        '     "inclination_deg": 轨道倾角(度) 或 null,\n'
        '     "eccentricity": 偏心率(0~1) 或 null,\n'
        '     "obliquity_deg": 自转轴倾角(度) 或 null,\n'
        '     "rotation_period_hours": 自转周期(小时，逆向自转填负值) 或 null\n'
        '  },\n'
        '  "moons_count": 数字或 null,\n'
        '  "members": "已知成员描述（可选）",\n'
        '  "note": "补充说明（口径不确定时在此注明）",\n'
        '  "source_url": "最佳参考链接（优先 Wikipedia）",\n'
        '  "source_name": "来源名（如 Wikipedia · Sirius）"\n'
        "}\n"
        "规则：只输出 JSON，不要解释；类别必须从给定枚举中选；恒星的 subtype 必须含光谱字母（O/B/A/F/G/K/M）以便套用贴图模板。\n"
        "【数据填写原则（重要）】对知名/有文献记录的天体，务必给出训练知识中可知的【最佳近似值】"
        "（半径、质量、轨道半长轴/周期/偏心率等），允许近似，但量级与单位须合理；"
        "仅在【完全无法估计】时才填 null。不要把已知对象的关键物理/轨道字段置空——"
        "宁可给近似真值并在 note 注明不确定性，也不要留 null（留 null 等于没录入任何数据）。"
        "绝不编造明显荒谬的值（如把矮行星质量写成恒星量级）。"
    )
    if facts_text:
        user_p = (
            f"天体名称：{name}\n"
            f"用户补充/检索到的文本：\n{facts_text}\n\n"
            f"请从中抽取上述 JSON。"
            + (f"（类别提示：{category_hint}）" if category_hint else "")
        )
    else:
        user_p = (
            f"天体名称：{name}\n"
            "（无额外文本，请凭借天文知识尽量给出真实参数（半径/质量/轨道等），允许近似；"
            "仅在完全无法估计时填 null，勿把已知字段置空。）"
            + (f"（类别提示：{category_hint}）" if category_hint else "")
        )
    return sys_p, user_p


def _parse_json_obj(raw):
    """从 LLM 文本中提取首个平衡 JSON 对象；失败抛 RuntimeError。"""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise RuntimeError(f"LLM 未返回可用 JSON：{raw[:300]}")
    return json.loads(m.group(0))


def extract_with_llm(name, category_hint, facts_text):
    """单条模式：豆包优先 / 本地兜底。返回 (结构化 dict, 来源标签)。"""
    sys_p, user_p = _extract_prompts(name, category_hint, facts_text)
    raw, src = llm_chat(sys_p, user_p)
    return _parse_json_obj(raw), src


def extract_shot_doubao(name, category_hint, facts_text):
    """批量模式单发：强制只打豆包 :9090（用户确认豆包可联网）。返回结构化 dict。"""
    sys_p, user_p = _extract_prompts(name, category_hint, facts_text)
    raw, _ = llm_chat(sys_p, user_p, endpoints=DOUBAO_EP)
    return _parse_json_obj(raw)


# ---------------------------------------------------------------- 批量：两发一致性
# 用于「两发都打豆包」后比对的关键数值字段（路径相对于抽取 dict）
_COMPARE_FIELDS = [
    ("category", None),
    ("distance_ly", None),
    ("physical", "mass_sun"),
    ("physical", "mass_kg"),
    ("physical", "radius_sun"),
    ("physical", "radius_km"),
    ("physical", "radius_ly"),
    ("physical", "temp_k"),
    ("physical", "lum_sun"),
    ("orbit", "semimajor_axis_au"),
    ("orbit", "orbital_period_years"),
    ("orbit", "orbital_velocity_km_s"),
    ("orbit", "inclination_deg"),
    ("orbit", "eccentricity"),
    ("orbit", "obliquity_deg"),
    ("orbit", "rotation_period_hours"),
]


def _get_path(d, *path):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def compare_two(a, b, tol=0.15):
    """比对两发抽取结果，返回 (是否一致, 不一致字段描述列表)。

    一致 = category 完全相同，且所有【两边都给了值】的关键字段相对差 < tol。
    单边缺失（一侧有值、一侧 null）不计入不一致——那只是第 2 发漏填，并非
    给出矛盾值；真正的不一致信号是「两边都给了值却相差大」。

    注意：一致性≠准确——模型若系统性编造同一错值，两发也会一致。仅能过滤
    随机幻觉/格式错乱，最终核定仍靠人工（data_verified 保持 False）。
    """
    mism = []
    # category 必须一致（critical）
    if (a.get("category") or "") != (b.get("category") or ""):
        mism.append(f"category({a.get('category')}!={b.get('category')})")
    for path in _COMPARE_FIELDS[1:]:   # 跳过 index 0 的 category（已单独处理）
        va, vb = _get_path(a, *path), _get_path(b, *path)
        if va is None or vb is None:
            continue   # 单边缺失：不计入不一致（仅代表第 2 发漏填）
        try:
            fa, fb = float(va), float(vb)
        except (TypeError, ValueError):
            if str(va) != str(vb):
                mism.append("/".join(path) + "(文本不一致)")
            continue
        if abs(fa) < 1e-9 and abs(fb) < 1e-9:
            continue
        if abs(fa - fb) / max(abs(fa), abs(fb)) > tol:
            mism.append("/".join(path) + f"({va} vs {vb})")
    return (len(mism) == 0), mism


def batch_build_object(name, category_hint=None, facts=""):
    """批量单对象构建：豆包两发 → 一致性比对 → compose。

    返回 (obj_or_None, status, report_lines, needs_review)。
      status: "ok"(两发一致) / "ok_needs_review"(两发不一致或仅1发成功) / "failed"
    无论一致与否，data_verified 恒为 False（两发一致≠准确，仍需人工核定）。
    """
    # 第 1 发
    try:
        a = extract_shot_doubao(name, category_hint, facts)
    except Exception as e:
        return None, "failed", [f"  ✗ {name}: 豆包第1发抽取失败 {type(e).__name__}: {e}"], False
    # 第 2 发
    try:
        b = extract_shot_doubao(name, category_hint, facts)
    except Exception as e:
        # 第1发成功、第2发失败：仍可用第1发，但标待审
        if not a.get("category") and category_hint:
            a["category"] = category_hint
        o = compose(a, data_source="llm_doubao")
        o["note"] = (o.get("note") or "") + " 【2发仅1发成功，待人工核定】"
        return _attach_quality(o, [f"  ⚠ {name}: 第2发失败，采用第1发（待审）"], True)
    if not a.get("category") and category_hint:
        a["category"] = category_hint
    consistent, mism = compare_two(a, b)
    if consistent:
        a["note"] = (a.get("note") or "") + " 【2发一致】"
        o = compose(a, data_source="llm_doubao")
        return _attach_quality(o, [f"  ✓ {name}: 2发一致"], False)
    a["note"] = (a.get("note") or "") + " 【2发不一致:" + ";".join(mism) + "，待人工核定】"
    o = compose(a, data_source="llm_doubao")
    return _attach_quality(o, [f"  ⚠ {name}: 2发不一致 → {mism}（待审）"], True)


def _attach_quality(o, report, needs_review):
    """把数据质量告警并入 report，严重缺失则强制 needs_review。"""
    _severe, _warns = data_quality_report(o)
    report.extend(_warns)
    if _severe:
        needs_review = True
        report.append("  ⚠ 数据严重不足（质量门红灯），建议补录 --facts/--json")
    return o, ("ok_needs_review" if needs_review else "ok"), report, needs_review


# ---------------------------------------------------------------- 归一化 + 合成
def normalize(cat, p):
    """p: physical 便捷字段 dict → 统一物理 dict（SI + 派生）。"""
    ph = {"mass_kg": None, "radius_km": None, "density_g_cm3": None,
          "gravity_m_s2": None, "escape_velocity_km_s": None,
          "mean_temp_c": None, "surface_pressure_bar": None, "albedo": None}
    m_kg = p.get("mass_kg")
    if m_kg is None and p.get("mass_sun") is not None:
        m_kg = p["mass_sun"] * M_SUN
    ph["mass_kg"] = m_kg

    r_km = p.get("radius_km")
    if r_km is None and p.get("radius_sun") is not None:
        r_km = p["radius_sun"] * R_SUN_KM
    if r_km is None and p.get("radius_ly") is not None and cat in EXT_CATS:
        r_km = p["radius_ly"] * LY_KM
    ph["radius_km"] = r_km

    if p.get("temp_k") is not None:
        ph["mean_temp_c"] = p["temp_k"] - 273.15
    if p.get("density_g_cm3") is not None:
        ph["density_g_cm3"] = p["density_g_cm3"]
    if p.get("albedo") is not None:
        ph["albedo"] = p["albedo"]
    if p.get("surface_pressure_bar") is not None:
        ph["surface_pressure_bar"] = p["surface_pressure_bar"]

    # 派生：重力 / 逃逸 / 密度（有 M、R 即可）
    if m_kg and r_km and r_km > 0:
        r_m = r_km * 1000.0
        ph["gravity_m_s2"] = G * m_kg / r_m ** 2
        ph["escape_velocity_km_s"] = (math.sqrt(2 * G * m_kg / r_m) / 1000.0)
        if ph["density_g_cm3"] is None and cat != "black_hole":
            ph["density_g_cm3"] = (m_kg / (4 / 3 * math.pi * r_m ** 3) / 1000.0)
    return ph


def compose(obj_in, data_source="manual"):
    """obj_in: 来自 LLM/JSON 的结构化 dict → 完整 astro.json 对象（含派生）。

    data_source: 数据来源标签，回填 astro.json 供 query.py 筛选：
      'manual'（--json 直写）| 'llm_doubao'（豆包抽取）| 'llm_local'（本地模型抽取）
    """
    cat = obj_in["category"]
    if cat not in CATEGORIES:
        raise ValueError(f"非法 category: {cat}")
    p = obj_in.get("physical") or {}
    ph = normalize(cat, p)

    # 黑洞：radius = 史瓦西半径（覆盖 normalize 的 radius_km）
    if cat == "black_hole" and p.get("mass_sun") is not None:
        ph["radius_km"] = RS_KM_PER_MSUN * (ph["mass_kg"] / M_SUN)

    lum = None
    if p.get("lum_w") is not None:
        lum = p["lum_w"]
    elif p.get("lum_sun") is not None:
        lum = p["lum_sun"] * L_SUN

    orbit = obj_in.get("orbit") or {}
    # LLM 合同用 AU/年更自然 → 折算成站点 schema 的 km/天（无则沿用既有字段名）
    _a_au = orbit.get("semimajor_axis_au")
    _p_yr = orbit.get("orbital_period_years")
    orbit_out = {
        "semimajor_axis_km": (_a_au * 149597870.7) if _a_au is not None
                            else orbit.get("semimajor_axis_km"),
        "orbital_period_days": (_p_yr * 365.25) if _p_yr is not None
                              else orbit.get("orbital_period_days"),
        "orbital_velocity_km_s": orbit.get("orbital_velocity_km_s"),
        "inclination_deg": orbit.get("inclination_deg"),
        "eccentricity": orbit.get("eccentricity"),
        "obliquity_deg": orbit.get("obliquity_deg"),
        "rotation_period_hours": orbit.get("rotation_period_hours"),
    }

    oid = obj_in.get("id") or slugify(obj_in.get("name_en") or obj_in.get("name") or cat)
    parent = obj_in.get("parent")
    # 行星/矮行星默认绕太阳（太阳系语境）；卫星需用户/LLM 显式指定母行星，否则 lint 会提示
    if parent is None and cat in ("planet", "dwarf_planet"):
        parent = "sun"
    o = {
        "id": oid,
        "name": obj_in.get("name") or obj_in.get("name_en"),
        "name_en": obj_in.get("name_en") or obj_in.get("name"),
        "category": cat,
        "parent": parent,
        "tagline": (obj_in.get("tagline") or "")[:60],
        "physical": ph,
        "orbit": orbit_out,
        "moons": {"count": obj_in.get("moons_count"),
                  "notable": obj_in.get("moons_notable") or []},
        "rings": obj_in.get("rings"),
        "magnetic_field": obj_in.get("magnetic_field"),
        "atmosphere": obj_in.get("atmosphere"),
        "spectral_type": obj_in.get("spectral_type"),
        "luminosity_w": lum,
        "distance_ly": obj_in.get("distance_ly"),
        "constellation": obj_in.get("constellation"),
        "subtype": obj_in.get("subtype"),
        "members": obj_in.get("members"),
        "note": obj_in.get("note"),
        "discovery": obj_in.get("discovery") or {"known_since": None, "discoverer": None, "year": None},
        "sources": [],
        "verified": TODAY,
        "data_verified": False,   # 数据未经人工校验（区别于 verified=录入日期）
        "data_source": data_source,   # 来源标签，供 query.py --data-source 筛选
        "article": None,
        "image": f"assets/planets/{oid}.webp",
        "source_dates": {},
        "image_credit": "程序化示意图",
        "image_url": None,
        "image_source": IMG_SRC_INIT.get(cat, "programmatic"),  # 供 query.py --image-source 筛选
        "image_locked": False,   # 交给 sync_images 生成；NASA 真图会改为 True 锁定
    }
    src_url = obj_in.get("source_url")
    src_name = obj_in.get("source_name")
    if src_url and src_name:
        sid = "src_" + re.sub(r"[^a-z0-9]", "_", (obj_in.get("name_en") or oid).lower())[:24]
        o["sources"] = [sid]
        o["source_dates"] = {sid: TODAY}
        o["_new_source"] = (sid, src_name, src_url)
    return o


def slugify(s):
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "obj"


# ---------------------------------------------------------------- 图片计划
def image_plan(o):
    cat = o["category"]
    if cat == "star":
        return ("template", "套用现有豆包模板（恒星按 subtype→9 类），无需新图、不需人工审核")
    if cat == "black_hole":
        return ("template", "程序化生成（黑洞几何模板），无需新图、不需人工审核")
    if cat in ("planet", "dwarf_planet", "moon", "asteroid", "comet"):
        return ("review", "优先豆包 AI 生成（失败回退程序化兜底）；可后续换 NASA 真图；图片需人工审核")
    return ("review", "优先豆包 AI 占位（失败回退程序化兜底）；建议后续换 NASA 真图；图片需人工审核")


# ---------------------------------------------------------------- 数据质量告警
def data_quality_report(o):
    """检查关键物理/轨道参数是否缺失，返回 (是否严重缺失, 警告行列表)。

    目的：--name 模式走 AI 抽取，若模型又把知名天体的参数置空，这里亮红灯提示
    用户补录（--facts 或 --json --force），避免产生"有名无参数"的占位记录。
    """
    cat = o["category"]
    ph = o.get("physical") or {}
    orb = o.get("orbit") or {}
    warns, severe = [], False
    solid = cat in ("planet", "dwarf_planet", "moon", "asteroid", "comet")
    if solid:
        if ph.get("radius_km") is None and ph.get("mass_kg") is None:
            warns.append("  ⚠ 物理参数缺失：质量与半径均为空（详情页将缺核心尺寸/质量数据）")
            severe = True
        if orb.get("semimajor_axis_km") is None and orb.get("orbital_period_days") is None:
            warns.append("  ⚠ 轨道参数缺失：半长轴与周期均为空")
            severe = True
    if cat == "star" and ph.get("radius_km") is None and ph.get("luminosity_w") is None \
            and ph.get("lum_sun") is None:
        warns.append("  ⚠ 恒星参数缺失：半径与光度均为空")
        severe = True
    if cat in EXT_CATS and ph.get("radius_km") is None:
        warns.append("  ⚠ 延展天体尺寸缺失：radius_km（或 radius_ly）为空")
        severe = True
    return severe, warns


# ---------------------------------------------------------------- 批量模式
def read_names(path):
    """读取批量文件：每行一个天体名；空行与 # 开头注释忽略。"""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"批量文件不存在：{path}")
    names = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        names.append(s)
    return names


def _batch_worker(name, category_hint, facts, force, existing, lock, used):
    """批量 worker：预检 → 两发抽取 → compose。返回 (obj, status, report, needs_review)。"""
    q = name.strip().lower().replace(" ", "")
    with lock:
        for x in existing:
            xn = str(x.get("name", "")).lower().replace(" ", "")
            xen = str(x.get("name_en", "")).lower().replace(" ", "")
            xid = str(x.get("id", "")).lower().replace(" ", "")
            if q and (q == xn or q == xen or q == xid):
                if not force:
                    return None, "skip", [f"  ⊘ 跳过（已存在）：{name} → {x['id']}"], False
        if q in used:
            return None, "skip", [f"  ⊘ 跳过（批次内重复）：{name}"], False
        used.add(q)
    o, status, rep, nr = batch_build_object(name, category_hint, facts)
    if status == "failed":
        return None, "failed", rep, False
    return o, status, rep, nr


def batch_mode(args):
    """批量录入：三阶段解耦（数据 → 出图 → 构建），限流并发抽数、写盘一次。"""
    names = read_names(args.batch)
    if not names:
        print("批量文件为空（无任何天体名）。")
        return 1
    data0 = json.loads(ASTRO.read_text(encoding="utf-8"))
    existing = data0["objects"]
    print(f"批量录入：读取 {len(names)} 个名字，并发抽取（豆包 2 发一致性，pool=3）...")

    lock = threading.Lock()
    used = set()
    results = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(_batch_worker, n, args.category, "", args.force, existing, lock, used)
                for n in names]
        for f in as_completed(futs):
            results.append(f.result())

    ok_objs = [r[0] for r in results if r and r[1] in ("ok", "ok_needs_review") and r[0]]
    skipped = [r for r in results if r and r[1] == "skip"]
    failed = [r for r in results if r and r[1] == "failed"]
    reviewed = [r for r in results if r and r[3] and r[1] in ("ok", "ok_needs_review")]

    # 逐条状态行
    for r in results:
        if not r:
            continue
        for line in r[2]:
            print(line)

    print("=" * 60)
    print(f"录入统计：新增 {len(ok_objs)} / 跳过 {len(skipped)} / 失败 {len(failed)} / 待审 {len(reviewed)}")
    if not ok_objs:
        print("无新增对象，结束。")
        return 0

    if args.dry_run:
        print("=== DRY-RUN：以下对象将被写入（不落盘、不出图）===")
        for o in ok_objs:
            print(f"  + {o['id']} ({o.get('name')}/{o.get('name_en')}) cat={o['category']} "
                  f"src={o['data_source']} verified={o['data_verified']}")
        return 0

    # 阶段1：写盘一次（单线程，避免并发写损坏 astro.json）
    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    objs = data["objects"]
    reg = data.setdefault("source_registry", {})
    new_srcs = []
    added = set(x["id"] for x in objs)
    written = 0
    for o in ok_objs:
        # 批次内重复 id 保护 / 库中已存在保护
        if o["id"] in added:
            print(f"  ⊘ 跳过（id 重复）：{o['id']}")
            continue
        ns = o.pop("_new_source", None)
        if ns:
            new_srcs.append(ns)
        by = {x["id"]: x for x in objs}
        if o["id"] in by:
            if not args.force:
                continue
            old = by[o["id"]]
            _old_img = {ik: old.get(ik) for ik in
                        ("image_source", "image_credit", "image_url", "image_locked")}
            for k, v in o.items():
                if v is not None or k not in old:
                    old[k] = v
            if _old_img.get("image_source") in ("doubao", "doubao_template", "nasa") \
                    and o.get("image_source") == "programmatic":
                for ik in ("image_source", "image_credit", "image_url", "image_locked"):
                    if ik in _old_img:
                        old[ik] = _old_img[ik]
        else:
            objs.append(o)
            added.add(o["id"])
        written += 1
    for sid, sname, surl in new_srcs:
        if sid not in reg:
            reg[sid] = {"name": sname, "url": surl}
    data["meta"]["object_count"] = len(objs)
    data["meta"]["updated"] = TODAY
    ASTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 astro.json（实际新增 {written} / 候选 {len(ok_objs)} 个对象，"
          f"data_verified 均=False 待人工核定）。")

    # 阶段2：出图（串行调用 sync_images，避免其内部 set_image_meta 并发写竞争）
    if not args.no_sync:
        ids = [o["id"] for o in ok_objs if o["id"] in added]
        if ids:
            print(f"阶段2 出图（豆包优先+程序化兜底，{len(ids)} 个）...")
            subprocess.run([sys.executable, "scripts/sync_images.py", "--ids", ",".join(ids)],
                           cwd=str(ROOT), check=False)

    # 阶段3：构建一次
    if not args.no_pages:
        print("阶段3 重新生成页面并构建（一次性）...")
        subprocess.run([sys.executable, "scripts/gen_pages.py"], cwd=str(ROOT), check=False)
        build = subprocess.run([sys.executable, "-m", "mkdocs", "build", "--strict"],
                               cwd=str(ROOT), check=False)
        if build.returncode != 0:
            print("[warn] mkdocs build 失败（数据/图片已写入，可手动 mkdocs build 排查）")

    # 待审核清单
    if reviewed:
        print("-" * 60)
        print(f"待审核清单（{len(reviewed)} 个：两发不一致 / 仅1发成功 / 质量门红灯）：")
        for r in reviewed:
            o = r[0]
            print(f"  - {o['id']} ({o.get('name')}): {r[2][-1] if r[2] else ''}")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser(description="通用天体录入引擎（AI 编排层数据入口）")
    ap.add_argument("--name", help="只给名字 → LLM 起草（分类+抽取）")
    ap.add_argument("--category", help="类别提示（star/planet/...），可选")
    ap.add_argument("--facts", help="提供给 LLM 抽取的检索文本")
    ap.add_argument("--json", help="直接结构化 JSON 录入（绕过 LLM）")
    ap.add_argument("--src", help="参考链接（配合 --json/--name 手动指定来源）")
    ap.add_argument("--batch", help="批量录入：从文件读取天体名（每行一个，# 开头为注释）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不落盘")
    ap.add_argument("--force", action="store_true", help="已收录的对象也强制覆盖更新（默认跳过）")
    ap.add_argument("--no-sync", action="store_true", help="写入后不自动调用 sync_images 出图")
    ap.add_argument("--no-pages", action="store_true",
                    help="写入+出图后不自动重新生成页面/构建（仍可用 gen_pages + mkdocs build 手动）")
    args = ap.parse_args()

    if args.batch:
        return batch_mode(args)

    if not (args.name or args.json):
        ap.print_help()
        return 1

    # 预检：已收录则直接跳过（避免无谓调用 LLM）
    _data = json.loads(ASTRO.read_text(encoding="utf-8"))
    _existing = _data["objects"]
    if args.json:
        j = json.loads(args.json)
        gid = j.get("id") or slugify(j.get("name_en") or j.get("name") or "")
        if gid in {x["id"] for x in _existing} and not args.force:
            print(f"已收录，跳过：{gid}；如需覆盖更新请加 --force")
            return 0
    elif args.name:
        q = args.name.strip().lower().replace(" ", "")
        for x in _existing:
            for n in (str(x.get("name", "")), str(x.get("name_en", ""))):
                if q and q == n.lower().replace(" ", ""):
                    if not args.force:
                        print(f"已收录，跳过：{x['id']}（{x.get('name')}）；如需覆盖更新请加 --force")
                        return 0
                    # --force：继续走抽取→覆盖流程（不在此提前 return）

    if args.json:
        obj_in = json.loads(args.json)
        src = "manual"
    else:
        facts = args.facts or ""
        if args.src:
            facts += f"\n参考链接：{args.src}"
        obj_in, src = extract_with_llm(args.name, args.category, facts)

    if not obj_in.get("category") and args.category:
        obj_in["category"] = args.category
    o = compose(obj_in, data_source=src)
    # 数据质量告警：知名天体若关键参数仍被模型置空，亮红灯提示补录
    _severe, _warns = data_quality_report(o)
    for _w in _warns:
        print(_w)
    if _severe:
        print("  ⚠ 数据严重不足：当前记录近乎占位。建议补录方式：")
        print("    · --facts \"<从 Wikipedia 等复制的真值文本>\" 重新抽取，或")
        print("    · --json '{...}' 直接录入已知参数（加 --force 覆盖本记录）")
    plan_kind, plan_msg = image_plan(o)

    if args.dry_run:
        print("=== DRY-RUN：将写入的对象 ===")
        print(json.dumps(o, ensure_ascii=False, indent=2))
        print("\n=== 图片计划 ===")
        print(f"  [{plan_kind}] {plan_msg}")
        if plan_kind == "review":
            print("  ⚠ 需人工审核：行星/星云/星系等贴图可能需替换 NASA 真图")
        return 0

    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    objs = data["objects"]
    by_id = {x["id"]: x for x in objs}
    reg = data.setdefault("source_registry", {})
    new_src = o.pop("_new_source", None)
    if new_src:
        sid, sname, surl = new_src
        if sid not in reg:
            reg[sid] = {"name": sname, "url": surl}

    if o["id"] in by_id:
        if not args.force:
            print(f"已收录，跳过：{o['id']}（{by_id[o['id']].get('name')}）；"
                  f"如需覆盖更新请加 --force")
            return 0
        old = by_id[o["id"]]
        # 保留既有影像来源：重抽取数据不应把已生成/锁定的图片标记回退成占位
        _old_img = {ik: old.get(ik) for ik in
                    ("image_source", "image_credit", "image_url", "image_locked")}
        for k, v in o.items():
            if v is not None or k not in old:
                old[k] = v
        if _old_img.get("image_source") in ("doubao", "doubao_template", "nasa") \
                and o.get("image_source") == "programmatic":
            for ik in ("image_source", "image_credit", "image_url", "image_locked"):
                if ik in _old_img:
                    old[ik] = _old_img[ik]
        print(f"更新已存在对象：{o['id']}")
    else:
        objs.append(o)
        print(f"新增对象：{o['id']}（{o['name']} / {o['name_en']}）")

    data["meta"]["object_count"] = len(objs)
    data["meta"]["updated"] = TODAY
    ASTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 自动出图：刚写入的对象交给 sync_images 按类别路由生成/补全贴图
    if not args.no_sync:
        try:
            subprocess.run([sys.executable, "scripts/sync_images.py", "--ids", o["id"]],
                           cwd=str(ROOT), check=False)
        except Exception as e:
            print(f"[warn] sync_images 调用失败（数据已写入，可手动补图）：{e}")

    # 自动重新生成站点页面 + 构建，否则网页上不会显示新对象
    if not args.no_pages:
        try:
            subprocess.run([sys.executable, "scripts/gen_pages.py"], cwd=str(ROOT), check=False)
            build = subprocess.run([sys.executable, "-m", "mkdocs", "build", "--strict"],
                                   cwd=str(ROOT), check=False)
            if build.returncode != 0:
                print("[warn] mkdocs build 失败（数据/图片已写入，可手动 `mkdocs build` 排查）")
        except Exception as e:
            print(f"[warn] 页面生成/构建失败（数据已写入，可手动 gen_pages + mkdocs build）：{e}")

    # ----------------------------- 清晰总结块 -----------------------------
    ph = o.get("physical") or {}
    src_tag = {"llm_doubao": "豆包抽取", "llm_local": "本地模型抽取", "manual": "手动录入"}.get(
        o.get("data_source"), o.get("data_source"))
    r = ph.get("radius_km")
    m = ph.get("mass_kg")
    d = o.get("distance_ly")
    lines = []
    lines.append("=" * 60)
    lines.append(f"【数据】{'新增' if o['id'] not in by_id or not args.force else '更新'}"
                 f"：{o['id']}（{o.get('name')} / {o.get('name_en')}）")
    lines.append(f"  类别：{o['category']}  |  数据来源：{src_tag}"
                 f"（data_verified={o.get('data_verified')}，待人工校验）")
    lines.append("  关键字段：")
    lines.append(f"    半径：{r:.0f} km" if r else "    半径：未提供")
    lines.append(f"    质量：{m:.3e} kg" if m else "    质量：未提供")
    lines.append(f"    距离：{d:.1f} ly" if d else "    距离：未提供")
    if o.get("spectral_type"):
        lines.append(f"    光谱型：{o.get('spectral_type')}")
    if o.get("subtype"):
        lines.append(f"    细分类型：{o.get('subtype')}")
    srcs = o.get("sources") or []
    if srcs:
        lines.append(f"  参考来源：{', '.join(srcs)}")
    lines.append(f"【图片】计划：[{plan_kind}] {plan_msg}")
    final_o = next((x for x in json.loads(ASTRO.read_text(encoding="utf-8"))["objects"]
                    if x["id"] == o["id"]), o)
    lines.append(f"  当前图片来源：{final_o.get('image_source')}"
                 f"（恒星/黑洞=模板，固态/大尺度=豆包优先+程序化兜底，NASA 真图需你手动锁定）")
    lines.append("【页面】已自动重新生成站点页面并构建；刷新网页即可看到。")
    if args.no_pages:
        lines.append("  ⚠ 本次跳过了页面生成（--no-pages）；需手动：")
        lines.append("    python scripts/gen_pages.py && mkdocs build --strict")
    lines.append("=" * 60)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
