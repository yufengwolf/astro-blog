#!/usr/bin/env python3
"""insert_stars.py — 第三批扩充：恒星类型细分 + 44 颗新恒星。

范围（2026-10-24 用户清单，数据经 Wikipedia / NASA 公开资料核对）：
  - 残骸：天狼 B / 波江 40A+B / 蟹云脉冲星 / 船帆脉冲星 / SGR 1806-20
  - 亮星：南门二 AB / 北河二 / 北河三 / 五车二 / 毕宿五 / 角宿一 / 轩辕十四 /
          北落师门 / 河鼓二 / 天津四 / 天船三 / 娄宿三 / 室宿一 / 壁宿二 /
          奎宿九 / 弧矢一 / 弧矢七 / 弧矢二（清单外补充）
  - 红特/超巨星：造父四 / 盾牌座 UY / 仙王座 RW / 英仙座 S / 蒭藁增二
  - 蓝特殊星：天鹅座 P / 弧矢增二十二 / R136a1
  - 双星/食变星：大陵五 / 渐台二 / 御夫座 ε
  - 系外宿主：开普勒 452 / 开普勒 22 / 特拉比斯特 1 / 格利泽 581 / 开普勒 186 /
              巨蟹座 55 / 飞马座 51 / 绘架座 β
另给库中现有 11 颗恒星补 subtype（恒星类型）。
北冕座 R 因无可靠距离数据，按用户指示跳过（"找不到数据就不加"）。

单位约定（与全库一致）：
  mass_kg / radius_km / luminosity_w / distance_ly / mean_temp_c（开尔文-273.15）。
表面重力与逃逸速度由 M、R 现场派生（自洽，lint 派生量校验必过）；密度同样派生
（恒星不参与密度区间校验，但对比页会展示）。
残骸（白矮星/中子星/磁星）的"平均表面温度"无标准 catalog 口径，除有引用值的
蟹云脉冲星（约 1.6×10⁶ K）外一律留 null，物理解释写进 note。
幂等：已存在的 id 跳过；subtype 只在为空时补。可重复运行。
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASTRO = ROOT / "docs" / "data" / "astro.json"
TODAY = "2026-10-24"

LY_KM = 9.4607e12
M_SUN = 1.9884e30
L_SUN = 3.828e26
RS_KM = 695700.0
G = 6.674e-11

SOURCES = {
    "wiki_sirius_b": ("Wikipedia · Sirius B", "https://en.wikipedia.org/wiki/Sirius_B"),
    "wiki_40eri": ("Wikipedia · 40 Eridani", "https://en.wikipedia.org/wiki/40_Eridani"),
    "wiki_crab_pulsar": ("Wikipedia · Crab Pulsar", "https://en.wikipedia.org/wiki/Crab_Pulsar"),
    "wiki_vela_pulsar": ("Wikipedia · Vela Pulsar", "https://en.wikipedia.org/wiki/Vela_Pulsar"),
    "wiki_sgr1806": ("Wikipedia · SGR 1806-20", "https://en.wikipedia.org/wiki/SGR_1806-20"),
    "wiki_alphacen": ("Wikipedia · Alpha Centauri", "https://en.wikipedia.org/wiki/Alpha_Centauri"),
    "wiki_castor": ("Wikipedia · Castor (star)", "https://en.wikipedia.org/wiki/Castor_(star)"),
    "wiki_pollux": ("Wikipedia · Pollux (star)", "https://en.wikipedia.org/wiki/Pollux_(star)"),
    "wiki_capella": ("Wikipedia · Capella", "https://en.wikipedia.org/wiki/Capella"),
    "wiki_aldebaran": ("Wikipedia · Aldebaran", "https://en.wikipedia.org/wiki/Aldebaran"),
    "wiki_spica": ("Wikipedia · Spica", "https://en.wikipedia.org/wiki/Spica"),
    "wiki_regulus": ("Wikipedia · Regulus", "https://en.wikipedia.org/wiki/Regulus"),
    "wiki_fomalhaut": ("Wikipedia · Fomalhaut", "https://en.wikipedia.org/wiki/Fomalhaut"),
    "wiki_altair": ("Wikipedia · Altair", "https://en.wikipedia.org/wiki/Altair"),
    "wiki_deneb": ("Wikipedia · Deneb", "https://en.wikipedia.org/wiki/Deneb"),
    "wiki_mirfak": ("Wikipedia · Mirfak", "https://en.wikipedia.org/wiki/Mirfak"),
    "wiki_hamal": ("Wikipedia · Hamal", "https://en.wikipedia.org/wiki/Hamal"),
    "wiki_markab": ("Wikipedia · Markab", "https://en.wikipedia.org/wiki/Markab"),
    "wiki_alpheratz": ("Wikipedia · Alpheratz", "https://en.wikipedia.org/wiki/Alpheratz"),
    "wiki_mirach": ("Wikipedia · Mirach", "https://en.wikipedia.org/wiki/Mirach"),
    "wiki_wezen": ("Wikipedia · Wezen", "https://en.wikipedia.org/wiki/Wezen"),
    "wiki_adhara": ("Wikipedia · Epsilon Canis Majoris", "https://en.wikipedia.org/wiki/Epsilon_Canis_Majoris"),
    "wiki_aludra": ("Wikipedia · Eta Canis Majoris", "https://en.wikipedia.org/wiki/Eta_Canis_Majoris"),
    "wiki_mucephei": ("Wikipedia · Mu Cephei", "https://en.wikipedia.org/wiki/Mu_Cephei"),
    "wiki_uysct": ("Wikipedia · UY Scuti", "https://en.wikipedia.org/wiki/UY_Scuti"),
    "wiki_rwcep": ("Wikipedia · RW Cephei", "https://en.wikipedia.org/wiki/RW_Cephei"),
    "wiki_spersei": ("Wikipedia · S Persei", "https://en.wikipedia.org/wiki/S_Persei"),
    "wiki_mira": ("Wikipedia · Mira", "https://en.wikipedia.org/wiki/Mira"),
    "wiki_pcygni": ("Wikipedia · P Cygni", "https://en.wikipedia.org/wiki/P_Cygni"),
    "wiki_naos": ("Wikipedia · Zeta Puppis", "https://en.wikipedia.org/wiki/Zeta_Puppis"),
    "wiki_r136a1": ("Wikipedia · R136a1", "https://en.wikipedia.org/wiki/R136a1"),
    "wiki_algol": ("Wikipedia · Algol", "https://en.wikipedia.org/wiki/Algol"),
    "wiki_sheliak": ("Wikipedia · Beta Lyrae", "https://en.wikipedia.org/wiki/Beta_Lyrae"),
    "wiki_almaaz": ("Wikipedia · Epsilon Aurigae", "https://en.wikipedia.org/wiki/Epsilon_Aurigae"),
    "wiki_kepler452": ("Wikipedia · Kepler-452", "https://en.wikipedia.org/wiki/Kepler-452"),
    "wiki_kepler22": ("Wikipedia · Kepler-22", "https://en.wikipedia.org/wiki/Kepler-22"),
    "wiki_trappist1": ("Wikipedia · TRAPPIST-1", "https://en.wikipedia.org/wiki/TRAPPIST-1"),
    "wiki_gj581": ("Wikipedia · Gliese 581", "https://en.wikipedia.org/wiki/Gliese_581"),
    "wiki_kepler186": ("Wikipedia · Kepler-186", "https://en.wikipedia.org/wiki/Kepler-186"),
    "wiki_55cancri": ("Wikipedia · 55 Cancri", "https://en.wikipedia.org/wiki/55_Cancri"),
    "wiki_51peg": ("Wikipedia · 51 Pegasi", "https://en.wikipedia.org/wiki/51_Pegasi"),
    "wiki_betapic": ("Wikipedia · Beta Pictoris", "https://en.wikipedia.org/wiki/Beta_Pictoris"),
    "nobel_2019": ("诺贝尔物理学奖 2019 新闻稿（系外行星的发现）",
                   "https://www.nobelprize.org/prizes/physics/2019/press-release/"),
}

# 现有 11 颗恒星补 subtype（仅当前为空时写入）
PATCH_SUBTYPE = {
    "sun": "黄矮星（G2V 主序星）",
    "pistol_star": "高光度蓝变星（LBV）",
    "stephenson_2_18": "红超巨星（M6Ia）",
    "arcturus": "红巨星（K0III）",
    "antares": "红超巨星（M1.5Iab-Ib）",
    "rigel": "蓝超巨星（B8Ia）",
    "betelgeuse": "红超巨星（M1-M2Ia）",
    "vega": "蓝白主序星（A0V）",
    "sirius_a": "蓝白主序星（A1V）",
    "proxima_centauri": "红矮星（M5.5Ve）",
    "eta_carinae": "高光度蓝变星（LBV）",
}
# 双星系统宿主补 members
PATCH_MEMBERS = {"sirius_a": 2}


def msun(n):
    return n * M_SUN


def rsun(n):
    return n * RS_KM


def lsun(n):
    return n * L_SUN


def star(oid, name, name_en, tagline, subtype, m_sun, r_sun, temp_k, lum_sun,
         dist_ly, constellation, spectral=None, parent=None, members=None,
         note=None, known=None, rotation_h=None, srcs=None):
    """构造一颗恒星记录。

    m_sun/r_sun/temp_k/lum_sun 均可为 None（诚实留空）；有 M、R 即派生
    表面重力 / 逃逸速度 / 密度，保证派生量校验自洽。
    """
    ph = {}
    if m_sun is not None:
        ph["mass_kg"] = msun(m_sun)
    if r_sun is not None:
        ph["radius_km"] = rsun(r_sun)
    if temp_k is not None:
        ph["mean_temp_c"] = temp_k - 273.15
    if m_sun is not None and r_sun is not None:
        m, r = msun(m_sun), rsun(r_sun) * 1000.0
        ph["gravity_m_s2"] = G * m / r ** 2
        ph["escape_velocity_km_s"] = math.sqrt(2 * G * m / r) / 1000.0
        ph["density_g_cm3"] = m / (4 / 3 * math.pi * r ** 3) / 1000.0
    o = {
        "id": oid, "name": name, "name_en": name_en, "category": "star",
        "parent": parent, "tagline": tagline,
        "physical": {
            "mass_kg": ph.get("mass_kg"), "radius_km": ph.get("radius_km"),
            "density_g_cm3": ph.get("density_g_cm3"),
            "gravity_m_s2": ph.get("gravity_m_s2"),
            "escape_velocity_km_s": ph.get("escape_velocity_km_s"),
            "mean_temp_c": ph.get("mean_temp_c"),
            "surface_pressure_bar": None, "albedo": None,
        },
        "orbit": {"semimajor_axis_km": None, "orbital_period_days": None,
                  "orbital_velocity_km_s": None, "inclination_deg": None,
                  "eccentricity": None, "obliquity_deg": None,
                  "rotation_period_hours": rotation_h},
        "moons": {"count": None, "notable": []},
        "rings": None, "magnetic_field": None, "atmosphere": None,
        "spectral_type": spectral, "subtype": subtype, "members": members,
        "note": note, "luminosity_w": lsun(lum_sun) if lum_sun is not None else None,
        "distance_ly": dist_ly, "constellation": constellation,
        "discovery": {"known_since": known, "discoverer": None, "year": None},
        "sources": list(srcs or []), "verified": TODAY, "article": None,
        "image": f"assets/planets/{oid}.webp",
        "source_dates": {s: TODAY for s in (srcs or [])},
        "image_credit": "程序化生成示意图（非真实影像）", "image_url": None,
        "image_locked": True,
    }
    return o


OBJS = [
    # ---------------------------------------------------- 恒星残骸（5+1 宿主）
    star("sirius_b", "天狼 B", "Sirius B", "质量与太阳相当，体积却只有地球大小——最早被发现的白矮星",
         "白矮星（DA2）", 1.018, 5634 / RS_KM, 25000, 0.0245, 8.61, "大犬座",
         spectral="DA2", parent="sirius_a",
         known="1862 年 Alvan Graham Clark 发现",
         srcs=["wiki_sirius_b"],
         note="质量与太阳相当、半径仅约 5634 km（比地球还小）的致密残骸，表面重力约为地球的 40 万倍；"
              "它是天狼星系中率先耗尽燃料、先行演化的一颗，而明亮的伴星天狼 A 仍是主序星。"),
    star("eridani_40a", "波江座 40A", "40 Eridani A", "《星际迷航》中瓦肯人的太阳，一颗宁静的橙黄矮星",
         "橙矮星（K1V 主序星）", 0.78, 0.804, 5126, 0.4, 16.35, "波江座",
         spectral="K1V", members=3,
         known="自古已知",
         srcs=["wiki_40eri"],
         note="又名 Keid，与白矮星 B、红矮星 C 组成三合系统，B/C 双星绕它一周约需 8000 年；"
              "因出现在《星际迷航》设定中（瓦肯人的太阳）而广为人知。"),
    star("eridani_40b", "波江座 40B", "40 Eridani B", "肉眼不可见的白矮星，人类最早确认的白矮星之一",
         "白矮星（DA4）", 0.558, 0.01308, 17200, 0.01349, 16.35, "波江座",
         spectral="DA4", parent="eridani_40a",
         known="1783 年 1 月 31 日威廉·赫歇尔发现",
         srcs=["wiki_40eri"],
         note="看似暗弱却'白'，意味着体积必须极小——这一观测推理奠定了白矮星物理学；"
              "它还与一颗红矮星（波江座 40C）结伴绕行。"),
    star("crab_pulsar", "蟹云脉冲星", "Crab Pulsar", "蟹状星云中心高速自转的中子星，每 33 毫秒转一圈",
         "中子星（脉冲星）", 1.4, 10 / RS_KM, 1.6e6, None, 6524, "金牛座",
         parent="m1",
         known="1968 年被确认为脉冲星（对应中国宋代记载的 SN 1054 遗迹）",
         srcs=["wiki_crab_pulsar"],
         note="1054 年超新星爆发留下的中子星，自转周期 33.39 毫秒；直径仅约 20 km，"
              "表面温度约 1.6×10⁶ K，是全波段（射电到伽马射线）的明亮同步辐射源。"),
    star("vela_pulsar", "船帆脉冲星", "Vela Pulsar", "船帆座超新星遗迹中心的中子星，自转突变的经典样本",
         "中子星（脉冲星）", 1.4, 10 / RS_KM, None, None, 959, "船帆座",
         known="1968 年发现",
         srcs=["wiki_vela_pulsar"],
         note="位于船帆座超新星遗迹中心，自转周期 89.33 毫秒；以周期性的'跃变'（glitch，"
              "自转突然加速）闻名，是探测中子星内部超流结构的天然实验室。"),
    star("sgr_1806_20", "SGR 1806-20", "SGR 1806-20", "银河系最强的磁星，一次巨耀斑曾照亮半个银河",
         "磁星（软伽马重复源）", None, 10 / RS_KM, None, None, 50000, "人马座",
         known="1979 年被记录为软伽马重复源；2004-12-27 巨耀斑",
         srcs=["wiki_sgr1806"],
         note="拥有宇宙最强磁场（约 10¹⁵ 高斯）的磁星，自转周期 7.5 秒；2004 年 12 月 27 日的"
              "巨耀斑在 0.1 秒内释放的能量超过太阳 25 万年的总和——若发生在更近处足以致命。"
              "质量未直接测定（中子星典型值约 1.4 M☉），故留空。"),
    # ---------------------------------------------------- 亮星（19）
    star("alphacen_a", "南门二 A", "Alpha Centauri A", "距太阳系最近的恒星系统主星，与太阳宛如孪生",
         "黄矮星（G2V 主序星）", 1.10, 1.2234, 5790, 1.519, 4.37, "半人马座",
         spectral="G2V", members=3,
         known="自古已知",
         srcs=["wiki_alphacen"],
         note="光谱、质量与太阳几乎一致的 G2V 恒星；与南门二 B 组成密近双星（互绕一周约 80 年），"
              "比邻星则在约 0.2 光年外绕这对亮星运行。"),
    star("alphacen_b", "南门二 B", "Alpha Centauri B", "南门二系统的橙矮星伴星，肉眼与主星不可分",
         "橙矮星（K1V 主序星）", 0.907, 0.8632, 5260, 0.5, 4.37, "半人马座",
         spectral="K1V", parent="alphacen_a",
         known="自古已知（肉眼与 A 不可分）",
         srcs=["wiki_alphacen"],
         note="略小略暗的橙矮星伴星；合起来视星等 -0.27，为全天第三亮（少数资料列第四）的'星'。"),
    star("castor", "北河二", "Castor", "六颗恒星组成的聚星系统，冬季大三角的一角",
         "白主序星（A1Vm 六合星系统）", 2.371, 2.089, 10286, 30, 49.2, "双子座",
         spectral="A1Vm", members=6,
         known="1678 年被发现是双星",
         srcs=["wiki_castor"],
         note="冬季大三角的一角。肉眼看似一颗星，实为六颗恒星的聚星系统：A、B 两对各含分光双星，"
              "另有一对远距红矮星伴星（YY Geminorum）。"),
    star("pollux", "北河三", "Pollux", "双子座最亮的星，一颗拥有系外行星的橙巨星",
         "橙巨星（K0III）", 1.91, 8.8, 4586, 32.7, 33.78, "双子座",
         spectral="K0III",
         known="自古已知",
         srcs=["wiki_pollux"],
         note="双子座最亮的星（比'哥哥'北河二更亮，尽管拜耳命名更晚）。2006 年确认其系外行星"
              " Thestias（双子座 βb），质量约 2.3 倍木星，周期约 590 天。"),
    star("capella", "五车二", "Capella", "御夫座最亮的星，四星系统金光耀眼",
         "黄巨星（G3III 四星系统）", 2.57, 12, 4970, 78.7, 42.9, "御夫座",
         spectral="G3III", members=4,
         known="自古已知",
         srcs=["wiki_capella"],
         note="北天第五亮星。主星对是两颗黄巨星（互绕一周约 104 天），另有两颗暗红矮星伴星。"),
    star("aldebaran", "毕宿五", "Aldebaran", "金牛座的红眼睛，一颗正在充气膨胀的红巨星",
         "红巨星（K5III）", 1.16, 44.13, 3910, 439, 65.3, "金牛座",
         spectral="K5III",
         known="自古已知",
         srcs=["wiki_aldebaran"],
         note="金牛座最亮的星，半径已膨胀到太阳的约 44 倍；它恰好位于毕星团（Hyades）视线方向上，"
              "是比星团近得多的前景星，并非星团成员。"),
    star("spica", "角宿一", "Spica", "室女座最亮的星，蓝白双星四天互绕一周",
         "蓝巨星（B1III-IV 双星）", 11.43, 7.47, 22400, 12100, 250, "室女座",
         spectral="B1III-IV", members=2,
         known="自古已知",
         srcs=["wiki_spica"],
         note="两颗蓝白恒星仅约 4 天互绕一周，强潮汐力把彼此拉成蛋形（椭球变星）；"
              "与五帝座一、大角星构成春季大三角。"),
    star("regulus", "轩辕十四", "Regulus", "狮子座的心脏，一颗飞速自转的蓝白恒星",
         "蓝白主序星（B8IVn）", 3.8, 4.35, 12460, 316, 79.3, "狮子座",
         spectral="B8IVn",
         known="自古已知",
         srcs=["wiki_regulus"],
         note="几乎正对黄道，是月亮与行星掩星的常客。约 15.9 小时一圈的自转把它甩成明显扁球，"
              "两极表面重力比赤道强约一倍。"),
    star("formalhaut", "北落师门", "Fomalhaut", "南天孤独的亮星，拥有著名的尘埃碎屑盘",
         "白主序星（A3V）", 1.92, 1.84, 8590, 16.6, 25.1, "南鱼座",
         spectral="A3V",
         known="自古已知",
         srcs=["wiki_fomalhaut"],
         note="南天孤悬的亮星（周围 20° 内没有别的亮星）。其尘埃碎屑盘是第一批被望远镜直接拍到的"
              "碎屑盘，盘中候选行星'北落师门 b'的真身至今仍有争议。"),
    star("altair", "河鼓二", "Altair", "牛郎星，夏季大三角的一角，扁球状飞速自转",
         "白主序星（A7Vn）", 1.86, 2.0, 7700, 10.6, 16.73, "天鹰座",
         spectral="A7Vn", rotation_h=7.77,
         known="自古已知",
         srcs=["wiki_altair"],
         note="夏季大三角的一角。约 7.77 小时一圈的自转把它甩成扁球（赤道半径比极半径大约 25%），"
              "干涉测量已直接证实这一形变；与织女星隔银河相望的传说广为流传。"),
    star("deneb", "天津四", "Deneb", "夏季大三角最远的一角，已知最亮的蓝白超巨星之一",
         "蓝白超巨星（A2Iae）", 19, 203, 8525, 196000, 2615, "天鹅座",
         spectral="A2Iae",
         known="自古已知",
         srcs=["wiki_deneb"],
         note="光度约为太阳的 20 万倍，是已知最亮的 A 型超巨星之一；距离估计 1400~2600 光年仍有"
              "争议（依测量口径而异），此处取约 2600 光年。"),
    star("mirfak", "天船三", "Mirfak", "英仙座最亮的星，年轻星团核心的黄白超巨星",
         "黄白超巨星（F5Ib）", 8.5, 68, 6350, 5000, 510, "英仙座",
         spectral="F5Ib",
         known="自古已知",
         srcs=["wiki_mirfak"],
         note="英仙座最亮的星，也是年轻疏散星团 Melotte 20 的核心成员；光度约为太阳的 5000 倍，"
              "是肉眼可见的最亮黄白超巨星之一。"),
    star("hamal", "娄宿三", "Hamal", "白羊座最亮的星，一颗步入暮年的橙巨星",
         "橙巨星（K2III）", 1.43, 15.19, 4553, 76.2, 65.8, "白羊座",
         spectral="K2III",
         known="自古已知",
         srcs=["wiki_hamal"],
         note="白羊座最亮的星，质量仅比太阳大一点，半径却已膨胀到约 15 倍；两千多年前春分点"
              "就位于它附近，'白羊座时代'因此得名。"),
    star("markab", "室宿一", "Markab", "飞马座四边形的一角，正值暮年的蓝白巨星",
         "蓝白巨星（B9III）", 4, 2.8, 11000, 160, 140, "飞马座",
         spectral="B9III",
         known="自古已知",
         srcs=["wiki_markab"],
         note="飞马座四边形的一角，一颗正在离开主序、向红巨星阶段演化的蓝白巨星。"),
    star("alpheratz", "壁宿二", "Alpheratz", "仙女座与飞马座共用的一角，蓝白亚巨星",
         "蓝白亚巨星（B8IV）", 3.63, 2.94, 11950, 158, 97, "仙女座",
         spectral="B8IV",
         known="自古已知",
         srcs=["wiki_alpheratz"],
         note="历史上同时被算作仙女座 α 与飞马座 δ，是两座共用的一角；本身还是一对分光双星，"
              "主星比伴星亮数百倍。"),
    star("mirach", "奎宿九", "Mirach", "仙女座第二亮的星，通往仙女座大星系的路标",
         "红巨星（M0III）", 3.5, 100, 3800, 1800, 197, "仙女座",
         spectral="M0III",
         known="自古已知",
         srcs=["wiki_mirach"],
         note="从它出发向东北跳两站就能找到仙女座大星系（M31），是深空观测的经典路标；"
              "它本身也是一颗光谱双星。"),
    star("wezen", "弧矢一", "Wezen", "大犬座第二亮星，直径约太阳 188 倍的黄白超巨星",
         "黄白超巨星（F8Ia）", 14.9, 188, 6150, 44000, 1600, "大犬座",
         spectral="F8Ia",
         known="自古已知",
         srcs=["wiki_wezen"],
         note="天狼星之后大犬座第二亮的星；直径约太阳 188 倍，表面温度却只有太阳的一半多一点，"
              "是一颗'虚胖'的超巨星，最终将以超新星收场。"),
    star("adhara", "弧矢七", "Adhara", "470 万年前它曾是夜空最亮的星，强极紫外光源",
         "蓝白亮巨星（B2II）", 12.6, 13.9, 22900, 38700, 430, "大犬座",
         spectral="B2II",
         known="自古已知",
         srcs=["wiki_adhara"],
         note="约 470 万年前它距地球更近，曾以 -3.99 等成为全天最亮的星；今天它仍是夜空中"
              "最强的极紫外辐射源，其紫外光子主导着本地星际云的电离状态。"),
    star("aludra", "弧矢二", "Aludra", "大犬座的蓝白超巨星，将以超新星结束一生",
         "蓝白超巨星（B5Ia）", 19.19, 56.3, 15000, 105442, 2000, "大犬座",
         spectral="B5Ia",
         known="自古已知",
         srcs=["wiki_aludra"],
         note="与弧矢一、弧矢七同属阿拉伯语'少女'（al-Adhara）星群；质量近 20 倍太阳，"
              "光度超过太阳十万倍，已走到生命末期。"),
    # ---------------------------------------------------- 红特/超巨星（5）
    star("mu_cephei", "造父四", "Mu Cephei", "血红色的特超巨星，肉眼可见的最大恒星之一",
         "红特超巨星（M2Ia）", 19.2, 1260, 3750, 310000, 2840, "仙王座",
         spectral="M2Ia",
         known="自古已知；1780 年代赫歇尔注意到其红色",
         srcs=["wiki_mucephei"],
         note="又名'石榴星'（Garnet Star），因石榴石般的血红色闻名；半径估计在 972~1650 R☉ "
              "之间依口径而变，此处取 1260 R☉。它的紫外光几乎全被自身大气吸收。"),
    star("uy_scuti", "盾牌座 UY", "UY Scuti", "体积最大的已知恒星之一，盾牌座的红超巨星",
         "红超巨星（M4Ia）", 8.5, 909, 3550, 124000, 5871, "盾牌座",
         spectral="M4Ia",
         known="1861 年编入波恩星表",
         srcs=["wiki_uysct"],
         note="曾以约 1708 R☉ 的旧估计闻名，最新观测把半径下修至约 909 R☉——仍接近太阳的千倍。"
              "半规则变星，约 8.5 个月内光变约 1 个星等。"),
    star("rw_cephei", "仙王座 RW", "RW Cephei", "会不规则变暗的特超巨星，2022 年经历创纪录变暗",
         "橙黄特超巨星（K2 0-Ia）", 13.9, 1100, 4000, 350000, 12790, "仙王座",
         spectral="K2 0-Ia",
         known="1901 年被确认为变星",
         srcs=["wiki_rwcep"],
         note="半径逾千倍太阳的半规则变星；2022 年它经历了有记录以来最深的一次变暗，"
              "可能与一次大规模的尘埃物质抛射有关。"),
    star("s_persei", "英仙座 S", "S Persei", "英仙座双星团方向的红超巨星，半规则变星",
         "红超巨星（M3.5I）", 20, 1200, 3500, 150000, 7900, "英仙座",
         spectral="M3.5I",
         known="19 世纪被记录为变星",
         srcs=["wiki_spersei"],
         note="藏在英仙座双星团方向的红超巨星，质量约 20 M☉、半径约 1200 R☉；"
              "光变幅度接近 1 个星等，是双星团观测区的'隐藏巨人'。"),
    star("mira", "蒭藁增二", "Mira", "人类发现的第一颗变星，约 332 天完成一次呼吸",
         "红巨星（M7IIIe 变星）", 1.18, 367, 3050, 8880, 300, "鲸鱼座",
         spectral="M7IIIe",
         known="1596 年 Fabricius 发现（第一颗被确认的变星）",
         srcs=["wiki_mira"],
         note="星等以约 332 天为周期在 2 等~10 等之间起伏：亮时肉眼可见，暗时需望远镜。"
              "它正剧烈流失质量，在星风中拖着一条约 13 光年长的尾巴。"),
    # ---------------------------------------------------- 蓝特殊星（3）
    star("p_cygni", "天鹅座 P", "P Cygni", "1600 年无预警增亮的'新星'，至今仍在抛射物质",
         "高光度蓝变星（LBV）", 37, 76, 18700, 610000, 5300, "天鹅座",
         spectral="LBV",
         known="1600 年 8 月突然增亮为 3 等（被记为'新星'）",
         srcs=["wiki_pcygni"],
         note="1600 年突然亮如三等星，随后缓慢回落，至今仍在以强劲星风抛射物质；"
              "与海山二同类，是'假超新星'现象的鼻祖。"),
    star("naos", "弧矢增二十二", "Zeta Puppis", "船尾座最亮的星，肉眼可见最热的恒星之一",
         "蓝超巨星（O5Ibf）", 40, 14, 42000, 500000, 1093, "船尾座",
         spectral="O5Ibf",
         known="自古已知",
         srcs=["wiki_naos"],
         note="表面温度约 42000 K，是肉眼可见的最热恒星之一；光度约为太阳的 50 万倍，"
              "星风速度高达约 2200 km/s。"),
    star("r136a1", "R136a1", "R136a1", "目前已知质量最大的恒星，藏在蜘蛛星云核心",
         "沃尔夫-拉叶星（WN5h）", 291, 42.7, 46000, 7244000, 163000, "剑鱼座",
         spectral="WN5h", parent="r136",
         known="1985 年在 R136 星团核心被发现",
         srcs=["wiki_r136a1"],
         note="目前已知质量最大的恒星（约 291 M☉，逼近恒星质量的理论上限），光度约为太阳的"
              " 724 万倍；强劲星风每年吹走相当于数个地球的质量。"),
    # ---------------------------------------------------- 双星 / 食变星（3）
    star("algol", "大陵五", "Algol", "中国古代记为会变亮的'魔星'，实为相互遮挡的食双星",
         "食双星（三合星系统）", 3.17, 2.73, 13000, 182, 94, "英仙座",
         spectral="B8V", members=3,
         known="自古已知；1669 年亮度变化被首次记录",
         srcs=["wiki_algol"],
         note="每 2.87 天，较暗的伴星从亮星前方经过，亮度从 2.1 等骤降到 3.4 等并持续约 10 小时"
              "——宇宙级的'眨眼'；中国古代因此称它为'魔星'。"),
    star("sheliak", "渐台二", "Beta Lyrae", "物质正从一颗星流向另一颗的食双星",
         "食双星（质量转移系统）", 2.97, 15.2, 13300, 6500, 960, "天琴座",
         spectral="B7II", members=2,
         known="1784 年古德里克发现其光变",
         srcs=["wiki_sheliak"],
         note="两颗星已近到物质正从一颗流向另一颗，外面裹着公共包层；光变几乎连续不断，"
              "是已知最早被确认的食双星之一。"),
    star("almaaz", "御夫座 ε", "Epsilon Aurigae", "每 27 年才发生一次罕见星食的'柱一'",
         "食变星（F0Iab 主星 + 尘埃盘伴星）", None, 143, 7750, 37875, 1350, "御夫座",
         spectral="F0Iab", members=2,
         known="自古已知；1821 年前后开始被系统记录",
         srcs=["wiki_almaaz"],
         note="每 27.1 年发生一次持续约 2 年的罕见星食，遮挡者被认为是一颗被巨大尘埃盘包裹的伴星。"
              "主星质量估计分歧极大（约 2.2~15 M☉），暂无共识，故质量诚实留空。"),
    # ---------------------------------------------------- 系外行星宿主（8）
    star("kepler_452", "开普勒 452", "Kepler-452", "拥有'地球表哥' Kepler-452b 的类太阳恒星",
         "黄矮星（G2V）", 1.037, 1.11, 5757, 1.1, 1810, "天鹅座",
         spectral="G2V",
         known="2015 年开普勒望远镜确认其行星系统",
         srcs=["wiki_kepler452"],
         note="拥有系外行星 Kepler-452b：第一颗被确认位于类太阳恒星宜居带内、且半径接近地球的"
              "行星，公转周期约 385 天，被昵称为'地球表哥'。"),
    star("kepler_22", "开普勒 22", "Kepler-22", "拥有首颗宜居带系外行星的类太阳恒星",
         "黄矮星（G5V）", 0.857, 0.869, 5596, 0.79, 644, "天鹅座",
         spectral="G5V",
         known="2011 年开普勒望远镜发现其行星",
         srcs=["wiki_kepler22"],
         note="拥有 Kepler-22b：第一颗被确认位于类太阳恒星宜居带内的系外行星，半径约 2.4 倍地球，"
              "可能是一颗'水世界'。"),
    star("trappist_1", "特拉比斯特 1", "TRAPPIST-1", "拥有七颗地球大小行星的红矮星，系外行星研究圣地",
         "红矮星（M8V）", 0.0898, 0.1192, 2566, 0.000566, 40.66, "宝瓶座",
         spectral="M8V", rotation_h=79.2,
         known="1999 年 2MASS 巡天记录；2016-2017 年确认七行星系统",
         srcs=["wiki_trappist1"],
         note="仅比木星大一点的超冷红矮星，却拥有 7 颗地球大小的行星，其中 3~4 颗位于宜居带；"
              "所有行星紧密排列，从最内侧看出去会是天空中的'大月亮'。JWST 正在其大气中搜寻生命迹象。"),
    star("gliese_581", "格利泽 581", "Gliese 581", "拥有多颗系外行星的红矮星，宜居性争论的经典目标",
         "红矮星（M3V）", 0.31, 0.30, 3480, 0.013, 20.4, "天秤座",
         spectral="M3V",
         known="2005 年发现首颗系外行星",
         srcs=["wiki_gj581"],
         note="距地仅 20.4 光年的红矮星，已确认多颗系外行星；其中 Gliese 581g/c/d 是否宜居"
              "曾引发长期争论，是系外行星科学早期最著名的事件之一。"),
    star("kepler_186", "开普勒 186", "Kepler-186", "拥有宜居带'地球大小'行星的红矮星",
         "红矮星（M1V）", 0.544, 0.523, 3755, 0.055, 579, "天鹅座",
         spectral="M1V",
         known="2014 年开普勒望远镜确认五行星系统",
         srcs=["wiki_kepler186"],
         note="拥有五颗行星，其中最外侧的 Kepler-186f 是首颗被确认位于宜居带内、且半径接近地球的"
              "系外行星；不过它的阳光远比地球暗淡，正午可能如同地球的黄昏。"),
    star("cancri_55", "巨蟹座 55", "55 Cancri", "已发现五颗行星的双星系统，含一颗'岩浆海'超级地球",
         "黄矮星（G8V 双星）", 0.95, 1.15, 5373, 0.63, 40.9, "巨蟹座",
         spectral="G8V", members=2,
         known="1997 年起陆续发现五颗行星",
         srcs=["wiki_55cancri"],
         note="已发现 5 颗系外行星的双星系统；其中巨蟹座 55e 是著名的'超级地球'，"
              "表面温度足以熔化岩石，可能是一片岩浆海。"),
    star("pegasi_51", "飞马座 51", "51 Pegasi", "人类发现第一颗系外行星的恒星，2019 年诺贝尔物理学奖",
         "黄次巨星（G2IV）", 1.11, 1.23, 5793, 1.5, 47.9, "飞马座",
         spectral="G2IV",
         known="1995 年 Mayor & Queloz 发现其行星",
         srcs=["wiki_51peg", "nobel_2019"],
         note="人类发现的第一颗围绕类太阳恒星的系外行星（飞马座 51b，一颗'热木星'）就在这里；"
              "两位发现者因此获得 2019 年诺贝尔物理学奖——系外行星时代由此开启。"),
    star("beta_pictoris", "绘架座 β", "Beta Pictoris", "第一个被直接拍到碎屑盘的恒星，年轻星群的命名来源",
         "白主序星（A6V）", 1.79, 1.53, 8054, 8.7, 63.4, "绘架座",
         spectral="A6V",
         known="1984 年 IRAS 卫星发现其碎屑盘",
         srcs=["wiki_betapic"],
         note="第一个被直接拍到的恒星碎屑盘，盘中已确认两颗巨行星（绘架座 βb/c）；"
              "它还是'绘架座 β 移动星群'——一群年龄仅约 2000 万年的年轻恒星——的命名来源。"),
]


def main():
    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    objs = data["objects"]
    by_id = {o["id"]: o for o in objs}
    have = set(by_id)

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

    # 现有恒星补 subtype / members（只在为空时写，幂等）
    patched = []
    for oid, sub in PATCH_SUBTYPE.items():
        o = by_id.get(oid)
        if o is not None and not o.get("subtype"):
            o["subtype"] = sub
            patched.append(oid)
    for oid, n in PATCH_MEMBERS.items():
        o = by_id.get(oid)
        if o is not None and not o.get("members"):
            o["members"] = n
            patched.append(oid + "(members)")

    data["meta"]["object_count"] = len(objs)
    data["meta"]["updated"] = TODAY
    data["meta"]["pending"] = (
        "TNO 三兄弟（鸟神星/妊神星/阋神星）物理参数待权威源实测值（当前诚实留 null）；"
        "北冕座 R 因无可靠距离数据未收录；m7/ngc4755 等 NASA 库无真图的天体保留程序化贴图"
    )
    ps = data["meta"].setdefault("primary_sources", [])
    for extra in (
        "Wikipedia 各恒星条目（亮星/超巨星/双星/残骸/系外宿主，2026-10-24 核对）https://en.wikipedia.org/",
        "诺贝尔物理学奖 2019 新闻稿（飞马座 51b 的发现）https://www.nobelprize.org/prizes/physics/2019/press-release/",
    ):
        if extra not in ps:
            ps.append(extra)

    ASTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(f"新增 {len(added)} 个恒星：{', '.join(added)}")
    if skipped:
        print(f"跳过已存在 {len(skipped)} 个：{', '.join(skipped)}")
    if patched:
        print(f"补字段：{', '.join(patched)}")
    print(f"来源登记新增 {added_src} 条；对象总数 {len(objs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
