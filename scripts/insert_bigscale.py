#!/usr/bin/env python3
"""insert_bigscale.py — 向 astro.json 批量录入大尺度天体（黑洞/星云/星系/星团/大尺度结构）。

数据源：2026-10-24 多轮 Web 检索校准（Wikipedia / NASA / ESA / EHT / LIGO 公开资料），
每条对象带 sources + source_dates + verified。口径不确定的字段（质量、等效直径）在
note 中注明取值范围；宁缺毋滥——拿不准的一律 null，不编造。

单位约定：
  - 黑洞 radius_km = 史瓦西半径（= 2.95325 km × M/M☉）
  - 延展天体（nebula/galaxy/cluster/structure）radius_km = 等效球半径（光年换算 km）
  - 质量统一 kg（底层），展示层按类目转 M☉
幂等：已存在的 id 跳过，可重复运行。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASTRO = ROOT / "docs" / "data" / "astro.json"
TODAY = "2026-10-24"

LY_KM = 9.4607e12                 # 1 光年 km
M_SUN = 1.9884e30                 # kg
L_SUN = 3.828e26                  # W
RS_KM = 2.95325008                # 史瓦西半径 km / M☉


def ly(km_ly):
    return km_ly * LY_KM


def msun(n):
    return n * M_SUN


def rsun(n):
    return n * RS_KM


def lsun(n):
    return n * L_SUN


# ---------------------------------------------------------------- 来源登记
SOURCES = {
    # 黑洞
    "wiki_m87bh": ("Wikipedia · M87*", "https://en.wikipedia.org/wiki/Messier_87#Supermassive_black_hole"),
    "wiki_sgr_a": ("Wikipedia · Sagittarius A*", "https://en.wikipedia.org/wiki/Sagittarius_A*"),
    "wiki_ton618": ("Wikipedia · TON 618", "https://en.wikipedia.org/wiki/TON_618"),
    "wiki_ic1101": ("Wikipedia · IC 1101", "https://en.wikipedia.org/wiki/IC_1101"),
    "wiki_gw190521": ("Wikipedia · GW190521", "https://en.wikipedia.org/wiki/GW190521"),
    "wiki_cygx1": ("Wikipedia · Cygnus X-1", "https://en.wikipedia.org/wiki/Cygnus_X-1"),
    "wiki_v404": ("Wikipedia · V404 Cygni", "https://en.wikipedia.org/wiki/V404_Cygni"),
    "eht": ("Event Horizon Telescope 合作组", "https://eventhorizontelescope.org/"),
    "ligo_gw190521": ("LIGO/Virgo 合作组 · GW190521（PhysRevLett 2020）",
                      "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.125.101102"),
    # 星云
    "wiki_m42": ("Wikipedia · Orion Nebula", "https://en.wikipedia.org/wiki/Orion_Nebula"),
    "wiki_m1": ("Wikipedia · Crab Nebula", "https://en.wikipedia.org/wiki/Crab_Nebula"),
    "wiki_m16": ("Wikipedia · Eagle Nebula", "https://en.wikipedia.org/wiki/Eagle_Nebula"),
    "wiki_m20": ("Wikipedia · Trifid Nebula", "https://en.wikipedia.org/wiki/Trifid_Nebula"),
    "wiki_m8": ("Wikipedia · Lagoon Nebula", "https://en.wikipedia.org/wiki/Lagoon_Nebula"),
    "wiki_horsehead": ("Wikipedia · Horsehead Nebula", "https://en.wikipedia.org/wiki/Horsehead_Nebula"),
    "wiki_m57": ("Wikipedia · Ring Nebula", "https://en.wikipedia.org/wiki/Ring_Nebula"),
    "wiki_ngc7293": ("Wikipedia · Helix Nebula", "https://en.wikipedia.org/wiki/Helix_Nebula"),
    "wiki_m2_9": ("Wikipedia · M2-9", "https://en.wikipedia.org/wiki/M2-9"),
    "wiki_rosette": ("Wikipedia · Rosette Nebula", "https://en.wikipedia.org/wiki/Rosette_Nebula"),
    "wiki_barnard": ("Wikipedia · Barnard's Loop", "https://en.wikipedia.org/wiki/Barnard%27s_Loop"),
    "wiki_tarantula": ("Wikipedia · Tarantula Nebula", "https://en.wikipedia.org/wiki/Tarantula_Nebula"),
    # 星系
    "wiki_milkyway": ("Wikipedia · Milky Way", "https://en.wikipedia.org/wiki/Milky_Way"),
    "wiki_m31": ("Wikipedia · Andromeda Galaxy", "https://en.wikipedia.org/wiki/Andromeda_Galaxy"),
    "wiki_m33": ("Wikipedia · Triangulum Galaxy", "https://en.wikipedia.org/wiki/Triangulum_Galaxy"),
    "wiki_lmc": ("Wikipedia · Large Magellanic Cloud", "https://en.wikipedia.org/wiki/Large_Magellanic_Cloud"),
    "wiki_smc": ("Wikipedia · Small Magellanic Cloud", "https://en.wikipedia.org/wiki/Small_Magellanic_Cloud"),
    "wiki_m87g": ("Wikipedia · Messier 87", "https://en.wikipedia.org/wiki/Messier_87"),
    "wiki_m104": ("Wikipedia · Sombrero Galaxy", "https://en.wikipedia.org/wiki/Sombrero_Galaxy"),
    "wiki_m51": ("Wikipedia · Whirlpool Galaxy", "https://en.wikipedia.org/wiki/Whirlpool_Galaxy"),
    "wiki_m81": ("Wikipedia · Messier 81", "https://en.wikipedia.org/wiki/Messier_81"),
    "wiki_m82": ("Wikipedia · Messier 82", "https://en.wikipedia.org/wiki/Messier_82"),
    "wiki_ngc1300": ("Wikipedia · NGC 1300", "https://en.wikipedia.org/wiki/NGC_1300"),
    "wiki_quintet": ("Wikipedia · Stephan's Quintet", "https://en.wikipedia.org/wiki/Stephan%27s_Quintet"),
    # 星团
    "wiki_m45": ("Wikipedia · Pleiades", "https://en.wikipedia.org/wiki/Pleiades"),
    "wiki_hyades": ("Wikipedia · Hyades", "https://en.wikipedia.org/wiki/Hyades"),
    "wiki_m44": ("Wikipedia · Beehive Cluster", "https://en.wikipedia.org/wiki/Beehive_Cluster"),
    "wiki_m67": ("Wikipedia · Messier 67", "https://en.wikipedia.org/wiki/Messier_67"),
    "wiki_r136": ("Wikipedia · R136", "https://en.wikipedia.org/wiki/R136"),
    "wiki_m13": ("Wikipedia · Messier 13", "https://en.wikipedia.org/wiki/Messier_13"),
    "wiki_m22": ("Wikipedia · Messier 22", "https://en.wikipedia.org/wiki/Messier_22"),
    "wiki_omegacen": ("Wikipedia · Omega Centauri", "https://en.wikipedia.org/wiki/Omega_Centauri"),
    # 大尺度结构
    "wiki_localgroup": ("Wikipedia · Local Group", "https://en.wikipedia.org/wiki/Local_Group"),
    "wiki_virgo": ("Wikipedia · Virgo Cluster", "https://en.wikipedia.org/wiki/Virgo_Cluster"),
    "wiki_laniakea": ("Wikipedia · Laniakea Supercluster", "https://en.wikipedia.org/wiki/Laniakea_Supercluster"),
    "wiki_attractor": ("Wikipedia · Great Attractor", "https://en.wikipedia.org/wiki/Great_Attractor"),
    "wiki_hcbgw": ("Wikipedia · Hercules–Corona Borealis Great Wall",
                   "https://en.wikipedia.org/wiki/Hercules%E2%80%93Corona_Borealis_Great_Wall"),
    "wiki_cmb": ("Wikipedia · Cosmic microwave background", "https://en.wikipedia.org/wiki/Cosmic_microwave_background"),
    "wiki_obsuniverse": ("Wikipedia · Observable universe", "https://en.wikipedia.org/wiki/Observable_universe"),
}


def base(oid, name, name_en, cat, tagline, parent=None, **kw):
    """通用骨架：填齐 schema 字段， kw 覆盖。"""
    o = {
        "id": oid,
        "name": name,
        "name_en": name_en,
        "category": cat,
        "parent": parent,
        "tagline": tagline,
        "physical": {
            "mass_kg": None, "radius_km": None, "density_g_cm3": None,
            "gravity_m_s2": None, "escape_velocity_km_s": None,
            "mean_temp_c": None, "surface_pressure_bar": None, "albedo": None,
        },
        "orbit": {
            "semimajor_axis_km": None, "orbital_period_days": None,
            "orbital_velocity_km_s": None, "inclination_deg": None,
            "eccentricity": None, "obliquity_deg": None,
            "rotation_period_hours": None,
        },
        "moons": {"count": None, "notable": []},
        "rings": None,
        "magnetic_field": None,
        "atmosphere": None,
        "spectral_type": None,
        "luminosity_w": None,
        "distance_ly": None,
        "constellation": None,
        "subtype": None,
        "members": None,
        "note": None,
        "discovery": {"known_since": None, "discoverer": None, "year": None},
        "sources": [],
        "verified": TODAY,
        "article": None,
        "image": f"assets/planets/{oid}.webp",
        "source_dates": {},
        "image_credit": "程序化生成示意图（非真实影像）",
        "image_url": None,
        "image_locked": True,
    }
    for k, v in kw.items():
        if k in ("physical", "orbit", "discovery") and isinstance(v, dict):
            o[k].update(v)
        else:
            o[k] = v
    # sources 便捷写法：srcs=[...] -> sources + source_dates
    srcs = kw.get("srcs") or []
    if srcs:
        o["sources"] = list(srcs)
        o["source_dates"] = {s: TODAY for s in srcs}
    return o


def bh(oid, name, name_en, mass_sun, dist_ly, tagline, known, **kw):
    """黑洞：radius = 史瓦西半径。"""
    ph = {"mass_kg": msun(mass_sun), "radius_km": rsun(mass_sun)}
    ph.update(kw.pop("physical", None) or {})
    return base(oid, name, name_en, "black_hole", tagline,
                physical=ph, distance_ly=dist_ly,
                discovery={"known_since": known}, **kw)


def ext(oid, name, name_en, cat, tagline, radius_ly, dist_ly, known, **kw):
    """延展天体：radius = 等效球半径（光年）。"""
    ph = {"radius_km": ly(radius_ly)}
    ph.update(kw.pop("physical", None) or {})
    return base(oid, name, name_en, cat, tagline,
                physical=ph, distance_ly=dist_ly,
                discovery={"known_since": known}, **kw)


OBJS = []

# ================================================================ 黑洞 ×7
OBJS += [
    bh("m87_star", "M87*", "M87*", 6.5e9, 5.4e7,
       "人类拍下的第一张黑洞照片主角，室女座星系团中心的超大质量黑洞",
       "2019 年（EHT 发布首张黑洞照片）",
       parent="m87", constellation="室女座", subtype="超大质量黑洞",
       note="史瓦西半径约 128 AU，比海王星轨道还大；吸积盘喷流延伸数千光年。",
       srcs=["wiki_m87bh", "eht"]),
    bh("sgr_a_star", "人马座 A*", "Sagittarius A*", 4.297e6, 27000,
       "银河系中心的超大质量黑洞，2022 年人类拍下第二张黑洞照片",
       "1974 年（射电源发现）；2022 年 EHT 成像",
       parent="milky_way", constellation="人马座", subtype="超大质量黑洞",
       note="史瓦西半径约 0.085 AU（约 1270 万 km）；周围恒星轨道数十年跟踪定轨。",
       srcs=["wiki_sgr_a", "eht"]),
    bh("ton618", "TON 618", "TON 618", 6.6e10, 1.82e10,
       "已知质量最大的黑洞之一，660 亿倍太阳质量的类星体引擎",
       "1957 年（Tonantzintla 射电源表）",
       constellation="猎犬座", subtype="类星体（超大质量黑洞）",
       note="史瓦西半径约 1300 AU；光度约 4×10⁴⁰ W。2019 年复测给出更低质量"
            "（约 407 亿 M☉），此处取经典估值 660 亿 M☉。",
       srcs=["wiki_ton618"]),
    bh("ic1101_bh", "IC 1101 中心黑洞", "IC 1101 black hole", 5.0e10, 1.045e9,
       "IC 1101 星系核心的黑洞，质量估值在天文界争议极大",
       "随 IC 1101 中心结构估算",
       parent="ic1101", constellation="巨蛇座", subtype="超大质量黑洞",
       note="文献估值 400~1000 亿 M☉，此处取中值 500 亿 M☉，仅供数量级参考。",
       srcs=["wiki_ic1101"]),
    bh("gw190521", "GW190521", "GW190521", 142, 1.7e10,
       "人类确认的第一个中等质量黑洞，双黑洞并合的产物",
       "2019-05-21（LIGO/Virgo 探测到并合信号）",
       constellation="半人马座", subtype="中等质量黑洞",
       note="由 85 M☉ + 66 M☉ 两个黑洞并合而成，约 8 M☉ 以引力波形式辐射；"
            "信号仅持续 0.1 秒。距离为光度距离（宇宙膨胀所致，大于共动距离）。",
       srcs=["wiki_gw190521", "ligo_gw190521"]),
    bh("cyg_x1", "天鹅座 X-1", "Cygnus X-1", 21.2, 7240,
       "人类确认的第一个恒星级黑洞，霍金打赌输掉的那位",
       "1964 年（探空火箭 X 射线源）；1990 年代确认黑洞",
       constellation="天鹅座", subtype="恒星级黑洞（X 射线双星）",
       note="2021 年 VLBA 精确测量：21.2 M☉、7240 光年；视界面自转速度 ≥95% 光速。",
       srcs=["wiki_cygx1"]),
    bh("v404_cyg", "V404 天鹅座", "V404 Cygni", 9.0, 7800,
       "低质量 X 射线双星，2015 年剧烈爆发出名的黑洞",
       "1989 年（Ginga X 射线爆发发现）",
       constellation="天鹅座", subtype="恒星级黑洞（X 射线双星）",
       note="质量估值 9~12 M☉，此处取 9 M☉；2015 年 6 月爆发为当时 50 年来最亮的 X 射线亮斑之一。",
       srcs=["wiki_v404"]),
]

# ================================================================ 星云 ×12
OBJS += [
    ext("m42", "猎户座大星云", "Orion Nebula (M42)", "nebula",
        "冬夜最亮的星云，银河系最近的恒星摇篮之一",
        12, 1344, "1610 年（Peiresc 发现）",
        constellation="猎户座", subtype="发射星云（H II 区）",
        physical={"mean_temp_c": 9727},
        note="直径约 24 光年；气体云质量约 2000 M☉，内部正在形成上千颗恒星。",
        srcs=["wiki_m42"]),
    ext("m1", "蟹状星云", "Crab Nebula (M1)", "nebula",
        "北宋天文学家见证的超新星残骸，宇宙中最著名的遗迹星云",
        5.5, 6500, "1054 年（中国记录超新星）；1731 年 Messier 编目",
        constellation="金牛座", subtype="超新星遗迹",
        note="直径约 11 光年；1054 年爆发的超新星残骸，中心有 33 毫秒脉冲星。",
        srcs=["wiki_m1"]),
    ext("m16", "鹰状星云", "Eagle Nebula (M16)", "nebula",
        "哈勃「创生之柱」的故乡，巨蛇座里的恒星工厂",
        35, 7000, "1746 年（Chéseaux 发现）",
        constellation="巨蛇座", subtype="发射星云（H II 区）",
        note="直径约 70 光年；1995 年哈勃拍摄的「创生之柱」是有史以来最著名的天文照片之一。",
        srcs=["wiki_m16"]),
    ext("m20", "三叶星云", "Trifid Nebula (M20)", "nebula",
        "发射、反射与暗带三合一的彩色星云，人马座里的调色盘",
        20, 5200, "1764 年（Messier 发现）",
        constellation="人马座", subtype="发射 + 反射混合星云",
        note="直径约 40 光年；三条尘埃暗带把星云切成三瓣，故得名。",
        srcs=["wiki_m20"]),
    ext("m8", "礁湖星云", "Lagoon Nebula (M8)", "nebula",
        "人马座里的巨大发射星云，肉眼可见的银河宝库",
        45, 4100, "1654 年（Hodierna 发现）",
        constellation="人马座", subtype="发射星云（H II 区）",
        note="视尺寸 110×50 光年（椭圆），等效口径取约 90 光年；内部含疏散星团 NGC 6530。",
        srcs=["wiki_m8"]),
    ext("horsehead", "马头星云", "Horsehead Nebula", "nebula",
        "猎户座腰带旁的暗尘埃剪影，夜空最 recognizable 的剪影",
        1.75, 1375, "1888 年（Fleming 在照相底片上发现）",
        constellation="猎户座", subtype="暗星云",
        note="直径约 3.5 光年；本身不发光，是背景发射星云 IC 434 前的尘埃暗带。",
        srcs=["wiki_horsehead"]),
    ext("m57", "环状星云", "Ring Nebula (M57)", "nebula",
        "天琴座里的太空烟圈，恒星暮年的典型肖像",
        1.3, 2300, "1779 年（Messier 发现）",
        constellation="天琴座", subtype="行星状星云",
        note="直径约 2.6 光年；濒死恒星抛出的气壳，中央可见白矮星。",
        srcs=["wiki_m57"]),
    ext("ngc7293", "螺旋星云", "Helix Nebula (NGC 7293)", "nebula",
        "宝瓶座里的「上帝之眼」，离地球最近的行星状星云",
        2.87, 680, "1824 年（Harding 发现）",
        constellation="宝瓶座", subtype="行星状星云",
        note="直径约 5.7 光年；形似巨眼，又近又大，是行星状星云的代表。",
        srcs=["wiki_ngc7293"]),
    ext("m2_9", "双喷射星星云", "M2-9 (Twin Jet Nebula)", "nebula",
        "蛇夫座里的蝶翼状星云，双极喷流的活样本",
        0.7, 2100, "1952 年（Minkowski 发现）",
        constellation="蛇夫座", subtype="双极行星状星云",
        note="直径约 1.4 光年；双星系统相互作用塑造出对称的双翼结构。",
        srcs=["wiki_m2_9"]),
    ext("rosette", "玫瑰星云", "Rosette Nebula", "nebula",
        "麒麟座里盛开的宇宙玫瑰，直径逾百光年的发射星云",
        65, 5000, "1690 年（Flamsteed 发现）",
        constellation="麒麟座", subtype="发射星云（H II 区）",
        note="直径约 130 光年；NOIRLab 2024 年新研究给出更近距离（约 2600 光年）与更小尺度（约 55 光年），"
             "此处取经典值。",
        srcs=["wiki_rosette"]),
    ext("barnards_loop", "巴纳德环", "Barnard's Loop", "nebula",
        "横跨猎户座大半边的巨大圆弧，可能源于数百万年前的一次超新星",
        150, 1600, "1895 年（Barnard 拍照发现）",
        constellation="猎户座", subtype="发射星云（H II 区）",
        note="直径约 300 光年；猎户座分子云复合体被电离的边缘。",
        srcs=["wiki_barnard"]),
    ext("tarantula", "蜘蛛星云", "Tarantula Nebula (30 Doradus)", "nebula",
        "大麦哲伦云里的巨型恒星工厂，本星系群最活跃的星云",
        500, 163000, "1751 年（Lacaille 发现）",
        parent="lmc", constellation="剑鱼座", subtype="发射星云（H II 区）",
        note="直径约 1000 光年；若放到银河系位置，其光辉足以投出物体阴影。",
        srcs=["wiki_tarantula"]),
]

# ================================================================ 星系 ×13
OBJS += [
    ext("milky_way", "银河系", "Milky Way", "galaxy",
        "我们的家园星系，太阳系所在的棒旋星系",
        50000, None, "史前",
        subtype="棒旋星系（SBbc）",
        physical={"mass_kg": msun(1.5e12)},
        luminosity_w=lsun(2.5e10),
        members="约 4000 亿颗恒星",
        note="直径约 10 万光年（不同口径 10~20 万光年）；太阳距银心约 2.6 万光年，"
             "绕银心一周约 2.3 亿年。",
        srcs=["wiki_milkyway"]),
    ext("m31", "仙女座星系", "Andromeda Galaxy (M31)", "galaxy",
        "本星系群最大的星系，肉眼可见的银河系近邻",
        110000, 2.54e6, "964 年（Al-Sufi 记录）；1923 年哈勃证明是河外星系",
        parent="local_group", constellation="仙女座",
        subtype="旋涡星系（SA(s)b）",
        physical={"mass_kg": msun(1.5e12)},
        members="约 1 万亿颗恒星",
        note="直径约 22 万光年；约 40 亿年后将与银河系并合。",
        srcs=["wiki_m31"]),
    ext("m33", "三角座星系", "Triangulum Galaxy (M33)", "galaxy",
        "本星系群第三大星系，肉眼极限的松散旋涡",
        30560, 2.88e6, "1654 年前（Hodierna 记录）",
        parent="local_group", constellation="三角座",
        subtype="旋涡星系（SA(s)cd）",
        physical={"mass_kg": msun(5e10)},
        members="约 400 亿颗恒星",
        note="直径约 6.1 万光年（D25 口径）；距离估值 238~307 万光年，取 288 万。",
        srcs=["wiki_m33"]),
    ext("lmc", "大麦哲伦云", "Large Magellanic Cloud", "galaxy",
        "银河系最大的卫星星系，南天夜空中挂着的模糊云块",
        7000, 160000, "1519 年（麦哲伦环球记录）",
        parent="milky_way", constellation="剑鱼座 / 山案座",
        subtype="不规则（麦哲伦型）矮星系",
        physical={"mass_kg": msun(1e10)},
        members="约 100 亿颗恒星",
        note="直径约 1.4 万光年；蜘蛛星云的宿主。",
        srcs=["wiki_lmc"]),
    ext("smc", "小麦哲伦云", "Small Magellanic Cloud", "galaxy",
        "大麦哲伦云的伴侣，南天第二矮星系",
        3500, 200000, "1519 年（麦哲伦环球记录）",
        parent="milky_way", constellation="杜鹃座",
        subtype="不规则矮星系",
        physical={"mass_kg": msun(6.5e9)},
        members="数亿颗恒星",
        note="直径约 7000 光年；与大麦哲伦云之间有气体桥相连。",
        srcs=["wiki_smc"]),
    ext("m87", "室女座 A（M87）", "Messier 87", "galaxy",
        "室女座星系团中心的巨型椭圆星系，万亿级恒星都会",
        120000, 5.4e7, "1781 年（Messier 发现）",
        parent="virgo_cluster", constellation="室女座",
        subtype="巨型椭圆星系（E0）",
        physical={"mass_kg": msun(2.4e12)},
        members="数万亿颗恒星 + 著名喷流",
        note="直径口径 12~24 万光年，取 24 万光年；中心黑洞 M87* 另有条目。",
        srcs=["wiki_m87g"]),
    ext("m104", "草帽星系", "Sombrero Galaxy (M104)", "galaxy",
        "侧视的旋涡星系，草帽外形来自它巨大的核球与尘埃环",
        25000, 3.1e7, "1781 年（Messier 私人记录，1921 年正式入表）",
        parent="virgo_cluster", constellation="室女座",
        subtype="旋涡星系（Sa/Sb，侧视）",
        physical={"mass_kg": msun(8e11)},
        members="约 8000 亿颗恒星",
        note="直径约 5 万光年（D25 口径）；核球与侧视尘埃环构成「草帽」外形。",
        srcs=["wiki_m104"]),
    ext("m51", "涡状星系", "Whirlpool Galaxy (M51)", "galaxy",
        "人类发现旋涡结构的第一个星系，与伴星系共舞的经典标范",
        38450, 2.8e7, "1773 年（Messier）；1845 年 Rosse 发现旋涡结构",
        constellation="猎犬座", subtype="旋涡星系（SA(s)bc pec）",
        physical={"mass_kg": msun(1.6e11)},
        members="含伴星系 NGC 5195（M51b）",
        note="直径约 7.7 万光年；距离估值 2300~3100 万光年，取 2800 万。",
        srcs=["wiki_m51"]),
    ext("m81", "波德星系", "Messier 81", "galaxy",
        "北斗七星附近的完美旋涡，与 M82 组成经典相互作用对",
        47000, 1.2e7, "1774 年（Bode 发现）",
        constellation="大熊座", subtype="旋涡星系（SA(s)ab）",
        members="与 M82 构成相互作用星系对",
        note="直径约 9.4 万光年（WISE 口径）。",
        srcs=["wiki_m81"]),
    ext("m82", "雪茄星系", "Messier 82 (Cigar Galaxy)", "galaxy",
        "著名的星暴星系，恒星诞生的速度是银河系的十倍",
        18500, 1.2e7, "1774 年（Bode 发现）",
        parent="m81", constellation="大熊座", subtype="星暴不规则星系",
        note="直径约 3.7 万光年；与 M81 的引力相互作用触发剧烈星暴。",
        srcs=["wiki_m82"]),
    ext("ngc1300", "NGC 1300", "NGC 1300", "galaxy",
        "棒旋星系的教科书标本，波江座里的巨大风车",
        55000, 6.1e7, "1835 年（Herschel 发现）",
        constellation="波江座", subtype="棒旋星系（SBbc）",
        note="直径约 11 万光年；中央棒结构与两端伸出的旋臂极其规整。",
        srcs=["wiki_ngc1300"]),
    ext("ic1101", "IC 1101", "IC 1101", "galaxy",
        "已知直径最大的星系之一，宇宙中的巨型椭圆巨兽",
        850000, 1.045e9, "1793 年（Herschel 发现）",
        constellation="巨蛇座", subtype="巨型椭圆星系（cD）",
        note="2024 年 A&A 研究测得直径约 170 万光年；不同口径争议极大，"
             "星系晕或延展至约 600 万光年。此处取 170 万光年（半径 85 万）。",
        srcs=["wiki_ic1101"]),
    ext("stephens_quintet", "斯蒂芬五重星系", "Stephan's Quintet", "galaxy",
        "五个星系的引力共舞，韦布镜头下的宇宙慢镜头并合",
        175000, 2.9e8, "1877 年（Stephan 发现）",
        constellation="飞马座", subtype="致密星系群",
        members="NGC 7317 / 7318A / 7318B / 7319 / 7320",
        note="群跨度约 35 万光年；其中 4 个星系正经历并合与潮汐撕裂（NGC 7320 只是前景星系）。",
        srcs=["wiki_quintet"]),
]

# ================================================================ 星团 ×8
OBJS += [
    ext("m45", "昴星团", "Pleiades (M45)", "cluster",
        "七姐妹星团，冬夜最易辨认的蓝色小勺",
        7.1, 444, "史前（梅西耶 1769 年编目）",
        parent="milky_way", constellation="金牛座", subtype="疏散星团",
        physical={"mass_kg": msun(8e2)},
        members="约 1000 颗成员星",
        note="直径约 14 光年；年龄约 1 亿年，蓝色反射星云包裹着年轻恒星。",
        srcs=["wiki_m45"]),
    ext("hyades", "毕星团", "Hyades", "cluster",
        "金牛座的 V 形头部，离太阳最近的疏散星团之一",
        7.35, 153, "史前（古希腊已有记载）",
        parent="milky_way", constellation="金牛座", subtype="疏散星团",
        physical={"mass_kg": msun(4e2)},
        members="约 300~400 颗成员星",
        note="直径约 15 光年；年龄约 6.25 亿年，构成金牛座头部的 V 字形。",
        srcs=["wiki_hyades"]),
    ext("m44", "蜂巢星团", "Beehive Cluster (M44)", "cluster",
        "巨蟹座腹中的蜂巢，双筒望远镜里的经典星团",
        8, 577, "公元前 260 年（Aratus）；1764 年 Messier 编目",
        parent="milky_way", constellation="巨蟹座", subtype="疏散星团",
        physical={"mass_kg": msun(5.5e2)},
        members="约 1000 颗成员星",
        note="直径约 16 光年；年龄约 6~7 亿年，是肉眼勉强可见的疏散星团。",
        srcs=["wiki_m44"]),
    ext("m67", "梅西耶 67", "Messier 67", "cluster",
        "著名的古老疏散星团，曾被猜想为太阳的出生地",
        10, 2700, "1779 年（Koehler 发现）",
        parent="milky_way", constellation="巨蟹座", subtype="疏散星团",
        physical={"mass_kg": msun(1.1e3)},
        members="500 余颗成员星",
        note="直径约 20 光年；年龄约 40 亿年，超过 100 颗类太阳恒星。",
        srcs=["wiki_m67"]),
    ext("r136", "R136 星团", "R136", "cluster",
        "蜘蛛星云核心的超级星团，已知最亮恒星的故乡",
        5, 163000, "1826 年（30 Dor 编目）；R136 于 20 世纪分解",
        parent="tarantula", constellation="剑鱼座", subtype="大质量星团（OB 星团）",
        physical={"mass_kg": msun(1e5)},
        members="含已知最亮恒星之一 R136a1（约 215~315 M☉）",
        note="直径约 10 光年；年龄仅 100~200 万年，包含数颗百倍太阳质量的巨星。",
        srcs=["wiki_r136"]),
    ext("m13", "武仙座球状星团", "Messier 13", "cluster",
        "北天最壮观的球状星团，武仙座里的 30 万颗恒星球",
        72.5, 22200, "1714 年（Halley 发现）",
        parent="milky_way", constellation="武仙座", subtype="球状星团",
        physical={"mass_kg": msun(6e5)},
        members="约 30 万颗成员星",
        note="直径约 145 光年；1974 年阿雷西博曾向它发射过第一条人类电报。",
        srcs=["wiki_m13"]),
    ext("m22", "梅西耶 22", "Messier 22", "cluster",
        "人马座里的明亮球状星团，肉眼可见的古老恒星城",
        50, 10600, "1665 年（Ihle 发现）",
        parent="milky_way", constellation="人马座", subtype="球状星团",
        members="数十万颗成员星",
        note="直径约 100 光年；最亮的球状星团之一，双筒望远镜即可分辨单颗恒星。",
        srcs=["wiki_m22"]),
    ext("omega_cen", "半人马座 ω", "Omega Centauri", "cluster",
        "银河系最大的球状星团，疑为被吞噬矮星系的残核",
        83, 15800, "公元 150 年（托勒密记为「星」）；1677 年哈雷确认非恒星",
        parent="milky_way", constellation="半人马座", subtype="球状星团",
        physical={"mass_kg": msun(4e6)},
        members="约 1000 万颗成员星",
        note="直径约 170 光年；质量与星族异常，可能是被银河系吞并的矮星系核心。",
        srcs=["wiki_omegacen"]),
]

# ================================================================ 大尺度结构 ×7
OBJS += [
    ext("local_group", "本星系群", "Local Group", "structure",
        "银河系所属的星系社群，80 多个星系的小团体",
        5e6, None, "1920 年代（哈勃确立河外星系后）",
        subtype="星系群",
        physical={"mass_kg": msun(3e12)},
        members="80 余个星系（含银河系、仙女座、三角座、大小麦哲伦云等）",
        note="直径约 1000 万光年；总质量估值 2~5×10¹² M☉（银河系 + 仙女座合计已约 3×10¹² M☉）。",
        srcs=["wiki_localgroup"]),
    ext("virgo_cluster", "室女座星系团", "Virgo Cluster", "structure",
        "离我们最近的大型星系团，上千个星系的引力都会",
        7.5e6, 5.4e7, "1781 年（Messier 记录成员）；1950 年代确认为星系团",
        parent="laniakea", constellation="室女座", subtype="星系团",
        physical={"mass_kg": msun(1.2e15)},
        members="约 1300~2000 个星系",
        note="直径约 1500 万光年；本星系群正被它牵引着下落。",
        srcs=["wiki_virgo"]),
    ext("laniakea", "拉尼亚凯亚超星系团", "Laniakea Supercluster", "structure",
        "银河系所在的家园超星系团，十万个星系的洪流盆地",
        2.6e8, 2.5e8, "2014 年（Tully 等定义）",
        subtype="超星系团",
        physical={"mass_kg": msun(1e17)},
        members="约 10 万个星系",
        note="直径约 5.2 亿光年；2014 年 Tully 等基于星系流场定义，"
             "后续研究认为它并非引力束缚结构。",
        srcs=["wiki_laniakea"]),
    ext("great_attractor", "巨引源", "Great Attractor", "structure",
        "隐匿在银河盘面背后的引力深渊，牵引着本超星系团",
        2e8, 2e8, "1987 年（Dressler 命名）",
        parent="laniakea", constellation="矩尺座 / 南三角座", subtype="引力异常区域",
        physical={"mass_kg": msun(1e16)},
        note="区域尺度约 4 亿光年；位于银河隐匿带（Zone of Avoidance）后方，"
             "通过星系本动速度发现。中心近矩尺座星系团（ACO 3627）；质量构成仍有争议。",
        srcs=["wiki_attractor"]),
    ext("hercules_corona_wall", "武仙-北冕座长城", "Hercules–Corona Borealis Great Wall", "structure",
        "已知最大的宇宙结构之一，横跨百亿光年的星系巨墙",
        5e9, 1e10, "2013 年（Horvath 等发现）",
        constellation="武仙座 — 北冕座", subtype="宇宙长城（星系丝状结构）",
        physical={"mass_kg": msun(1e18)},
        note="直径约 100 亿光年（共动尺度，口径存在争议）；2013 年基于伽马射线暴分布发现。",
        srcs=["wiki_hcbgw"]),
    ext("cmb", "宇宙微波背景", "Cosmic Microwave Background", "structure",
        "大爆炸的余晖，宇宙最古老的光（最后散射面）",
        4.57e10, 4.57e10, "1965 年（Penzias & Wilson 发现）",
        parent="observable_universe", subtype="宇宙微波背景辐射（最后散射面）",
        physical={"mean_temp_c": -270.425},
        note="共动距离约 457 亿光年；温度 2.725 K，起伏仅约 10⁻⁵，"
             "这些起伏是今天所有星系结构的种子。",
        srcs=["wiki_cmb"]),
    ext("observable_universe", "可观测宇宙", "Observable Universe", "structure",
        "以地球为球心的粒子视界，人类信息的全部边疆",
        4.65e10, None, "现代宇宙学概念（哈勃定律，1929）",
        subtype="可观测宇宙（粒子视界）",
        physical={"mass_kg": 1.5e53, "mean_temp_c": -270.42},
        members="估计约 2 万亿个星系",
        note="半径约 465 亿光年（共动距离）；年龄约 138 亿年；"
             "普通物质 4.9%、暗物质 26.8%、暗能量 68.3%。",
        srcs=["wiki_obsuniverse"]),
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
        "黑洞/星云/星系/星团/大尺度结构 47 个天体的贴图以 NASA 真图优先、程序化兜底；"
        "系外行星为后续扩展方向"
    )
    ps = data["meta"].setdefault("primary_sources", [])
    for extra in (
        "Wikipedia 各天体条目（黑洞/星云/星系/星团/大尺度结构，2026-10-24 核对）https://en.wikipedia.org/",
        "Event Horizon Telescope（M87* / 人马座 A* 黑洞照片）https://eventhorizontelescope.org/",
        "LIGO/Virgo 合作组 · GW190521 探测论文（2020）https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.125.101102",
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
