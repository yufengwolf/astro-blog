#!/usr/bin/env python3
"""add_object.py — 通用天体录入引擎（AI 编排层的数据入口）。

设计目标（2026-10-26 用户拍板）：用户只给一个名字（甚至不知道类型），AI 负责
定位类别、拉取数据特征、录入 astro.json；图片交给 sync_images.py 按类别路由
（恒星/黑洞套模板；行星/星云/星系等可能需人工审核）。
add_object 写入 astro.json 成功后，**末尾会自动调用 sync_images.py --ids <新id>**
为新对象出图（可用 --no-sync 关闭）。

三种录入模式：
  --name  "天狼星"               AI 从自身知识起草（LLM 分类 + 抽取，null 不编造）
  --facts "天狼星是大犬座主星…"  AI 从你提供的文本抽取（配合 agent 的 WebSearch 使用）
  --json  '{...}'               直接结构化录入（绕过 LLM，最可控）

通用逻辑（不随模式变）：
  - 按 category 套 schema 模板（复用 insert_* 的 base/star/ext 口径）
  - 有 M、R 即派生 重力/逃逸速度/密度（保证 lint 派生量校验自洽）
  - 自动登记 source_registry、填 image 占位（image_locked=False → sync_images 生成）
  - 幂等：id 已存在则原地更新（不重复追加），并打印摘要
  - --dry-run 只打印将写入的对象 + 图片计划 + 人工审核标记，不落盘、不调 sync_images
  - 写入成功后自动调用 sync_images.py 为新对象出图（--no-sync 可关闭）

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
import urllib.request
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
def llm_chat(system, user, model_pref=None):
    """OpenAI 兼容：豆包(:9090) 默认优先，本地 llama-server(:8080) 兜底。

    返回 (助手文本, 来源标签) 元组；来源标签为 'llm_doubao' 或 'llm_local'，
    用于回填 astro.json 的 data_source，让用户能筛出"哪些数据是 AI 吐的、靠哪个模型"。
    """
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    # 豆包优先（默认 doubao-2.1）；本地 8080 作为兜底
    endpoints = [("http://127.0.0.1:9090/v1", model_pref or "doubao-2.1"),
                 ("http://127.0.0.1:8080/v1", model_pref)]
    last_err = None
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
    raise RuntimeError(f"LLM 调用失败（已试本地+豆包）：{last_err}")


def extract_with_llm(name, category_hint, facts_text):
    """返回 (结构化 dict, 来源标签) 元组（见模块 docstring 的 JSON 契约）。"""
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
        '  "moons_count": 数字或 null,\n'
        '  "members": "已知成员描述（可选）",\n'
        '  "note": "补充说明（口径不确定时在此注明）",\n'
        '  "source_url": "最佳参考链接（优先 Wikipedia）",\n'
        '  "source_name": "来源名（如 Wikipedia · Sirius）"\n'
        "}\n"
        "规则：只输出 JSON，不要解释；拿不准的数值一律 null，绝不编造；"
        "类别必须从给定枚举中选；恒星的 subtype 必须含光谱字母（O/B/A/F/G/K/M）以便套用贴图模板。"
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
            "（无额外文本，请仅凭你的天文知识填写；不确定项填 null。）"
            + (f"（类别提示：{category_hint}）" if category_hint else "")
        )
    raw, src = llm_chat(sys_p, user_p)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise RuntimeError(f"LLM 未返回可用 JSON：{raw[:300]}")
    return json.loads(m.group(0)), src


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
    orbit_out = {
        "semimajor_axis_km": orbit.get("semimajor_axis_km"),
        "orbital_period_days": orbit.get("orbital_period_days"),
        "orbital_velocity_km_s": orbit.get("orbital_velocity_km_s"),
        "inclination_deg": orbit.get("inclination_deg"),
        "eccentricity": orbit.get("eccentricity"),
        "obliquity_deg": orbit.get("obliquity_deg"),
        "rotation_period_hours": orbit.get("rotation_period_hours"),
    }

    oid = obj_in.get("id") or slugify(obj_in.get("name_en") or obj_in.get("name") or cat)
    o = {
        "id": oid,
        "name": obj_in.get("name") or obj_in.get("name_en"),
        "name_en": obj_in.get("name_en") or obj_in.get("name"),
        "category": cat,
        "parent": obj_in.get("parent"),
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
        "image_credit": "程序化生成示意图（非真实影像）",
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
    if cat in ("star", "black_hole"):
        return ("template", "套用现有模板（恒星按 subtype→类型、黑洞程序化），无需新图、不需人工审核")
    return ("review", "程序化兜底 + 可选 NASA 真图；图片需人工审核（见 sync_images）")


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser(description="通用天体录入引擎（AI 编排层数据入口）")
    ap.add_argument("--name", help="只给名字 → LLM 起草（分类+抽取）")
    ap.add_argument("--category", help="类别提示（star/planet/...），可选")
    ap.add_argument("--facts", help="提供给 LLM 抽取的检索文本")
    ap.add_argument("--json", help="直接结构化 JSON 录入（绕过 LLM）")
    ap.add_argument("--src", help="参考链接（配合 --json/--name 手动指定来源）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不落盘")
    ap.add_argument("--force", action="store_true", help="已收录的对象也强制覆盖更新（默认跳过）")
    ap.add_argument("--no-sync", action="store_true", help="写入后不自动调用 sync_images 出图")
    args = ap.parse_args()

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
                    print(f"已收录，跳过：{x['id']}（{x.get('name')}）；如需覆盖更新请加 --force")
                    return 0

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
        for k, v in o.items():
            if v is not None or k not in old:
                old[k] = v
        print(f"更新已存在对象：{o['id']}")
    else:
        objs.append(o)
        print(f"新增对象：{o['id']}（{o['name']} / {o['name_en']}）")

    data["meta"]["object_count"] = len(objs)
    data["meta"]["updated"] = TODAY
    ASTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"astro.json 已更新（总数 {len(objs)}）；图片计划：[{plan_kind}] {plan_msg}")

    # 自动出图：刚写入的对象交给 sync_images 按类别路由生成/补全贴图
    if not args.no_sync:
        try:
            print("\n=== 自动调用 sync_images 出图 ===")
            subprocess.run([sys.executable, "scripts/sync_images.py", "--ids", o["id"]],
                           cwd=str(ROOT), check=False)
        except Exception as e:
            print(f"[warn] sync_images 调用失败（数据已写入，可手动补图）：{e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
