#!/usr/bin/env python3
"""insert_bigscale2.py — 第二批扩充：著名星云/星系/星团 + GW150914 + 海山二 + 小天体（小行星/彗星/卫星）。

数据源：2026-10-24 核对 Wikipedia / NASA / LIGO 公开资料；每条带 sources + source_dates。
拿不准的字段（海山二的质量/半径/温度随大爆发剧变）诚实留 null 并在 note 说明。

新增类别：comet（彗星）——lint/gen_pages/JS/CSS 已同步支持。
幂等：已存在的 id 跳过，可重复运行。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASTRO = ROOT / "docs" / "data" / "astro.json"
TODAY = "2026-10-24"

LY_KM = 9.4607e12
M_SUN = 1.9884e30
L_SUN = 3.828e26
RS_KM = 2.95325008

SOURCES = {
    "wiki_m17": ("Wikipedia · Omega Nebula", "https://en.wikipedia.org/wiki/Omega_Nebula"),
    "wiki_m27": ("Wikipedia · Dumbbell Nebula", "https://en.wikipedia.org/wiki/Dumbbell_Nebula"),
    "wiki_ngc3372": ("Wikipedia · Carina Nebula", "https://en.wikipedia.org/wiki/Carina_Nebula"),
    "wiki_ngc7000": ("Wikipedia · North America Nebula", "https://en.wikipedia.org/wiki/North_America_Nebula"),
    "wiki_m101": ("Wikipedia · Pinwheel Galaxy", "https://en.wikipedia.org/wiki/Pinwheel_Galaxy"),
    "wiki_m64": ("Wikipedia · Black Eye Galaxy", "https://en.wikipedia.org/wiki/Black_Eye_Galaxy"),
    "wiki_m83": ("Wikipedia · Messier 83", "https://en.wikipedia.org/wiki/Messier_83"),
    "wiki_ngc5128": ("Wikipedia · Centaurus A", "https://en.wikipedia.org/wiki/Centaurus_A"),
    "wiki_ngc4038": ("Wikipedia · Antennae Galaxies", "https://en.wikipedia.org/wiki/Antennae_Galaxies"),
    "wiki_m11": ("Wikipedia · Wild Duck Cluster", "https://en.wikipedia.org/wiki/Wild_Duck_Cluster"),
    "wiki_m7": ("Wikipedia · Messier 7", "https://en.wikipedia.org/wiki/Messier_7"),
    "wiki_ngc4755": ("Wikipedia · NGC 4755（珠宝盒星团）", "https://en.wikipedia.org/wiki/NGC_4755"),
    "ligo_gw150914": ("LIGO/Virgo 合作组 · GW150914 探测论文（PRL 2016）",
                      "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.116.061102"),
    "wiki_etacarinae": ("Wikipedia · Eta Carinae", "https://en.wikipedia.org/wiki/Eta_Carinae"),
    "wiki_vesta": ("Wikipedia · 4 Vesta", "https://en.wikipedia.org/wiki/4_Vesta"),
    "wiki_halley": ("Wikipedia · Halley's Comet", "https://en.wikipedia.org/wiki/Halley%27s_Comet"),
    "wiki_iapetus": ("Wikipedia · Iapetus (moon)", "https://en.wikipedia.org/wiki/Iapetus_(moon)"),
}


def ly(x):
    return x * LY_KM


def msun(n):
    return n * M_SUN


def rsun(n):
    return n * RS_KM


def lsun(n):
    return n * L_SUN


def base(oid, name, name_en, cat, tagline, parent=None, **kw):
    o = {
        "id": oid, "name": name, "name_en": name_en, "category": cat,
        "parent": parent, "tagline": tagline,
        "physical": {"mass_kg": None, "radius_km": None, "density_g_cm3": None,
                     "gravity_m_s2": None, "escape_velocity_km_s": None,
                     "mean_temp_c": None, "surface_pressure_bar": None, "albedo": None},
        "orbit": {"semimajor_axis_km": None, "orbital_period_days": None,
                  "orbital_velocity_km_s": None, "inclination_deg": None,
                  "eccentricity": None, "obliquity_deg": None,
                  "rotation_period_hours": None},
        "moons": {"count": None, "notable": []},
        "rings": None, "magnetic_field": None, "atmosphere": None,
        "spectral_type": None, "luminosity_w": None, "distance_ly": None,
        "constellation": None, "subtype": None, "members": None, "note": None,
        "discovery": {"known_since": None, "discoverer": None, "year": None},
        "sources": [], "verified": TODAY, "article": None,
        "image": f"assets/planets/{oid}.webp", "source_dates": {},
        "image_credit": "程序化生成示意图（非真实影像）", "image_url": None,
        "image_locked": True,
    }
    for k, v in kw.items():
        if k in ("physical", "orbit", "discovery") and isinstance(v, dict):
            o[k].update(v)
        else:
            o[k] = v
    srcs = kw.get("srcs") or []
    if srcs:
        o["sources"] = list(srcs)
        o["source_dates"] = {s: TODAY for s in srcs}
    return o


def neb(oid, name, name_en, tagline, radius_ly, dist_ly, known, **kw):
    ph = {"radius_km": ly(radius_ly)}
    ph.update(kw.pop("physical", None) or {})
    return base(oid, name, name_en, "nebula", tagline, parent="milky_way",
                physical=ph, distance_ly=dist_ly,
                discovery={"known_since": known}, **kw)


def gal(oid, name, name_en, tagline, radius_ly, dist_ly, known, **kw):
    ph = {"radius_km": ly(radius_ly)}
    ph.update(kw.pop("physical", None) or {})
    return base(oid, name, name_en, "galaxy", tagline,
                physical=ph, distance_ly=dist_ly,
                discovery={"known_since": known}, **kw)


def clu(oid, name, name_en, tagline, radius_ly, dist_ly, known, **kw):
    ph = {"radius_km": ly(radius_ly)}
    ph.update(kw.pop("physical", None) or {})
    return base(oid, name, name_en, "cluster", tagline, parent="milky_way",
                physical=ph, distance_ly=dist_ly,
                discovery={"known_since": known}, **kw)


OBJS = [
    # ---------------------------------------------------------- 星云（4）
    neb("m17", "天鹅星云", "Omega Nebula", "银河系中最亮的发射星云之一，形似一只展翅的天鹅",
        20, 5500, "1745 年 de Chéseaux 记录，1764 年梅西耶编目",
        subtype="H II 区 / 发射星云", members=1000, constellation="人马座",
        srcs=["wiki_m17"],
        note="人马座方向的巨大恒星形成区，内含疏散星团 NGC 6618；可见光下呈天鹅/马蹄形。"),
    neb("m27", "哑铃星云", "Dumbbell Nebula", "人类发现的第一个行星状星云，形似一只哑铃",
        1.25, 1227, "1764 年梅西耶发现",
        subtype="行星状星云", constellation="狐狸座",
        srcs=["wiki_m27"],
        note="垂死恒星抛出的气壳，中心白矮星；是梅西耶目录中第一个行星状星云。"),
    neb("ngc3372", "船底座星云", "Carina Nebula", "全天最大最亮的星云之一，藏着最不稳定的巨星海山二",
        230, 7500, "1751-52 年拉卡伊发现",
        subtype="发射星云（含高光度蓝变星）", members=14000, constellation="船底座",
        srcs=["wiki_ngc3372"],
        note="等效直径口径不一（约 260~460 光年，取决于是否计入外围暗星云结构）；"
             "内部包含海山二、钥匙孔星云与多个大质量星团。"),
    neb("ngc7000", "北美洲星云", "North America Nebula", "形状酷似北美洲大陆的发射星云",
        45, 2590, "1786 年赫歇尔记录",
        subtype="发射星云（H II 区）", constellation="天鹅座",
        srcs=["wiki_ngc7000"],
        note="与鹈鹕星云（IC 5070）同属一个巨大 H II 区，被尘埃带分隔成两块。"),
    # ---------------------------------------------------------- 星系（5）
    gal("m101", "风车星系", "Pinwheel Galaxy", "正面朝我们的旋涡星系，旋臂上缀满红色恒星育婴室",
        85000, 21000000, "1781 年 Méchain 发现",
        subtype="旋涡星系（Sc）", constellation="大熊座",
        luminosity_w=lsun(2.6e10), srcs=["wiki_m101"],
        note="2011 年哈勃以 51 幅图拼接成其迄今最大最清晰的旋涡全景。"),
    gal("m64", "黑眼星系", "Black Eye Galaxy", "壮丽旋臂前横着一条暗尘埃带，像一只乌黑的眼睛",
        27000, 24000000, "1779 年梅西耶记录",
        subtype="旋涡星系（Sb）", constellation="后发座",
        srcs=["wiki_m64"],
        note="又名睡美人星系；外盘气体反向旋转，被认为是远古星系并合的遗迹。"),
    gal("m83", "南风车星系", "Southern Pinwheel Galaxy", "南天最亮的旋涡星系之一，恒星爆发此起彼伏",
        27500, 15000000, "1752 年拉卡伊发现",
        subtype="棒旋星系（星暴星系）", constellation="长蛇座",
        srcs=["wiki_m83"],
        note="已观测到 6 次超新星爆发，是业余与专业观测的常客。"),
    gal("ngc5128", "半人马 A", "Centaurus A", "被一条厚重尘埃带拦腰横穿的并合遗迹星系",
        30000, 13000000, "1826 年 James Dunlop 发现",
        subtype="透镜/椭圆星系（并合遗迹）", constellation="半人马座",
        srcs=["wiki_ngc5128"],
        note="距离最近的射电星系之一（射电源 Cen A）；中心超大质量黑洞喷流长达数千光年。"),
    gal("ngc4038", "天线星系", "Antennae Galaxies", "两个正在撕扯合并的旋涡星系，甩出两条长长的潮汐尾",
        250000, 62000000, "1785 年赫歇尔发现",
        subtype="并合星系对（触须星系）", constellation="乌鸦座",
        srcs=["wiki_ngc4038"],
        note="等效半径含两条潮汐尾（NGC 4038 与 NGC 4039 两核相距约 2.5 万光年）；"
             "合并触发的星暴诞生了数万个星团。"),
    # ---------------------------------------------------------- 星团（3）
    clu("m11", "野鸭星团", "Wild Duck Cluster", "数千颗恒星挤成三角阵，像一群列队飞翔的野鸭",
        25, 6200, "1681 年基希发现",
        subtype="疏散星团", members=2900, constellation="盾牌座",
        srcs=["wiki_m11"],
        note="已知成员最多的疏散星团之一；盾牌座恒星云中的亮团。"),
    clu("m7", "托勒密星团", "Ptolemy Cluster", "两千年前就被古人记进星表的疏散星团",
        11.5, 980, "公元 130 年托勒密《天文学大成》记录",
        subtype="疏散星团", members=100, constellation="天蝎座",
        srcs=["wiki_m7"],
        note="少数被古人 naked-eye 记录的深空天体，肉眼即见的一大团星光。"),
    clu("ngc4755", "珠宝盒星团", "Jewel Box Cluster", "蓝超巨星与红超巨星挤在一起，像一匣彩色宝石",
        9.3, 6437, "1751-52 年拉卡伊发现",
        subtype="疏散星团", members=100, constellation="南十字座",
        srcs=["wiki_ngc4755"],
        note="年龄仅约 700 万年；南十字座附近的彩色小团，肉眼借双筒可见。"),
    # ---------------------------------------------------------- 黑洞（1）
    base("gw150514", "GW150914 并合黑洞", "GW150914", "black_hole",
         "人类第一个直接探测到的引力波事件：双黑洞并合",
         physical={"mass_kg": msun(62), "radius_km": rsun(62)},
         distance_ly=1300000000,
         discovery={"known_since": "2015 年 9 月 14 日（LIGO 探测，2016 年公布）"},
         subtype="双黑洞并合（引力波事件）",
         srcs=["ligo_gw150914"],
         note="初态为 36 M☉ + 29 M☉ 双黑洞，并合后约 62 M☉，约 3 M☉ 质量以引力波形式释放；"
              "距离按红移 z≈0.09 的光度距离估算。"),
    # ---------------------------------------------------------- 恒星（1）
    base("eta_carinae", "海山二", "Eta Carinae", "star",
         "银河系内最亮的高光度蓝变星，随时可能爆发为超新星",
         physical={},
         luminosity_w=lsun(5e6),
         distance_ly=7500,
         spectral_type="LBV",
         constellation="船底座",
         discovery={"known_since": "自古已知（南天亮星）"},
         srcs=["wiki_etacarinae"],
         note="质量（约 100~150 M☉）、半径（约 60~800 R☉）与温度随 1843 年"
              "「假超新星」大爆发剧烈变化，无法给出单一数值，故留 null；"
              "周身被自己抛出的 Homunculus 星云包裹。"),
    # ---------------------------------------------------------- 小行星（1）
    base("vesta", "灶神星", "4 Vesta", "asteroid",
         "小行星带的巨型原行星，南极有一个直径 500 公里的超级撞击坑",
         parent="sun",
         physical={"mass_kg": 2.59076e20, "radius_km": 262.7,
                   "density_g_cm3": 3.456, "gravity_m_s2": 0.25,
                   "escape_velocity_km_s": 0.36, "albedo": 0.42,
                   "mean_temp_c": -60},
         orbit={"semimajor_axis_km": 3.5338e8, "orbital_period_days": 1325.5,
                "orbital_velocity_km_s": 19.34, "inclination_deg": 7.14,
                "eccentricity": 0.0887, "rotation_period_hours": 5.342},
         discovery={"known_since": "1807 年 3 月 29 日", "discoverer": "Heinrich Olbers", "year": 1807},
         srcs=["wiki_vesta"],
         note="小行星带第二大天体、已分异的原行星（铁核+岩幔+壳）；HED 陨石的母体；"
              "南极 Rheasilvia 撞击坑直径约 500 km、坑底中央峰高约 20 km。"),
    # ---------------------------------------------------------- 彗星（1）
    base("halley", "哈雷彗星", "1P/Halley", "comet",
         "每 76 年回归一次的著名周期彗星，肉眼可见的脏雪球",
         parent="sun",
         physical={"mass_kg": 2.2e14, "radius_km": 5.5,
                   "density_g_cm3": 0.6, "albedo": 0.04},
         orbit={"semimajor_axis_km": 2.6677e9, "orbital_period_days": 27509,
                "orbital_velocity_km_s": 7.05, "inclination_deg": 162.26,
                "eccentricity": 0.9671, "rotation_period_hours": 52.8},
         discovery={"known_since": "公元前 240 年中国星孛记录；1758 年按哈雷预言如期回归"},
         srcs=["wiki_halley"],
         note="核体约 15×8×8 km 花生形；轨道逆行（倾角 162°）；近日点速度可达 54.6 km/s；"
              "1986 年回归由乔托号飞船近距离拍摄，下次回归为 2061 年 7 月。"),
]


def main():
    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    objs = data["objects"]
    have = {o["id"] for o in objs}

    reg = data.setdefault("source_registry", {})
    added_src = 0
    for sid, (name, url) in SOURCES.items():
        if sid not in reg:
            reg[sid] = {"name": name, "url": url}
            added_src += 1

    added, skipped = [], []
    for o in OBJS:
        if o["id"] in have:
            skipped.append(o["id"])
            continue
        objs.append(o)
        added.append(o["id"])

    data["meta"]["object_count"] = len(objs)
    data["meta"]["updated"] = TODAY
    data["meta"]["pending"] = (
        "TNO 三兄弟（鸟神星/妊神星/阋神星）物理参数待权威源实测值（当前诚实留 null）；"
        "m7/ngc4755 等 NASA 库无真图的天体保留程序化贴图；系外行星为后续扩展方向"
    )
    ps = data["meta"].setdefault("primary_sources", [])
    for extra in (
        "Wikipedia 各天体条目（著名星云/星系/星团/小天体，2026-10-24 核对）https://en.wikipedia.org/",
        "LIGO/Virgo 合作组 · GW150914 探测论文（2016）https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.116.061102",
    ):
        if extra not in ps:
            ps.append(extra)

    ASTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(f"新增 {len(added)} 个天体：{', '.join(added)}")
    if skipped:
        print(f"跳过已存在 {len(skipped)} 个：{', '.join(skipped)}")
    print(f"来源登记新增 {added_src} 条；对象总数 {len(objs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
