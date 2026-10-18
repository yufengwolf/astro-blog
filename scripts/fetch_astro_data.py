#!/usr/bin/env python3
"""fetch_astro_data.py — 从 NASA 公开源拉取天体数据，与 docs/data/astro.json 对比，生成变更报告。

设计原则：
- 只读不改：永不自动写 astro.json；所有变更由人审阅报告后手动合入
- 可复现：原始响应落盘 scripts/.cache/fetch/，--offline 可离线重放
- 礼貌抓取：单并发、请求间隔 1s、带 UA、失败退避（遵循 JPL SSD Fair Use Policy）

数据源（均为 NASA 公共领域资料）：
- NSSDC Planetary Fact Sheets（NASA Goddard，nssdc.gsfc.nasa.gov）
  sunfact / mercury / venus / earth / mars（含火卫一、二）/ jupiter / saturn /
  uranus / neptune / moon / pluto + jovian / saturnian / uranian / neptunian 卫星页
- JPL SBDB API（ssd-api.jpl.nasa.gov，免 key）：谷神星等小天体，冥王星交叉校验

用法：
  python scripts/fetch_astro_data.py                       # 全量拉取 + diff 报告
  python scripts/fetch_astro_data.py status                # 零网络本地体检（先看这个）
  python scripts/fetch_astro_data.py --objects mars,moon   # 针对性拉取（只拉对应源页）
  python scripts/fetch_astro_data.py --propose eris        # 为库外对象生成候选骨架
  python scripts/fetch_astro_data.py --source nssdc   # 只跑指定源（nssdc / sbdb，可逗号分隔）
  python scripts/fetch_astro_data.py --offline        # 不联网，用缓存原始数据
  python scripts/fetch_astro_data.py --tolerance 1.0  # 显著差异的相对阈值（%）
  python scripts/fetch_astro_data.py --verbose        # 打印每个对象抽取到的原始值

工作节奏建议：status 看清现状 → --objects 针对性拉取 → 审报告 → 手动合库。

产物：
  reports/astro_fetch_<时间戳>.md   变更报告（人读）
  reports/astro_fetch_latest.md     最新报告副本
  reports/propose_<id>.json         库外对象候选骨架（--propose）
  scripts/.cache/fetch/<源>/...     原始响应缓存

退出码：0 无显著差异；1 有显著差异；2 抓取或解析失败
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASTRO_JSON = ROOT / "docs" / "data" / "astro.json"
CACHE_DIR = ROOT / "scripts" / ".cache" / "fetch"
REPORT_DIR = ROOT / "reports"
NSSDC_BASE = "https://nssdc.gsfc.nasa.gov/planetary/factsheet/"
SBDB_URL = "https://ssd-api.jpl.nasa.gov/sbdb.api"

UA = "astro-notes-data-fetch/1.0 (personal static site; +https://github.com/yufengwolf/astro-blog)"
G_CODATA = 6.67430e-11  # m^3 kg^-1 s^-2（CODATA 2018）
AU_KM = 149597870.7
REQUEST_DELAY = 1.0     # 秒，请求间隔（JPL Fair Use）
TIMEOUT = 30
RETRIES = 3

# ---------------------------------------------------------------------------
# 基础工具：HTTP / HTML / 数值解析
# ---------------------------------------------------------------------------

_last_request_at = [0.0]


def http_get(url: str, binary: bool = False) -> bytes:
    """礼貌 GET：限速 + 退避重试。返回原始字节。"""
    for attempt in range(RETRIES):
        wait = REQUEST_DELAY - (time.monotonic() - _last_request_at[0])
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()
            _last_request_at[0] = time.monotonic()
            return data
        except urllib.error.HTTPError as e:
            # 4xx（除 429）重试无意义
            if 400 <= e.code < 500 and e.code != 429:
                raise
            if attempt == RETRIES - 1:
                raise
        except urllib.error.URLError:
            if attempt == RETRIES - 1:
                raise
        time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"unreachable: {url}")


def fetch_cached(source: str, name: str, url: str, offline: bool) -> str:
    """带磁盘缓存的抓取。缓存键 = source/name。"""
    path = CACHE_DIR / source / name
    if offline or path.exists():
        if not path.exists():
            raise FileNotFoundError(f"offline 模式但无缓存：{path}")
        return path.read_text(encoding="utf-8", errors="replace")
    data = http_get(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data.decode("utf-8", errors="replace")


_ENTITIES = {"&nbsp;": " ", "&plusmn;": "+-", "&amp;": "&", "&deg;": "°",
             "&lt;": "<", "&gt;": ">", "&#177;": "+-"}


def clean_text(s: str) -> str:
    """去 HTML 标签与实体；<sup>x</sup> → ^x（保留科学计数法可读性）。"""
    s = re.sub(r"<sup>(.*?)</sup>", r"^\1", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", "", s)
    for k, v in _ENTITIES.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s).strip()


_TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.I)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_PRE_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.S | re.I)
_H3_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S | re.I)


def parse_tables(html: str) -> list[list[list[str]]]:
    """HTML → 表格列表，每表 = 行列表，每行 = 单元格文本列表。"""
    tables = []
    for tbl in _TABLE_RE.findall(html):
        rows = []
        for tr in _ROW_RE.findall(tbl):
            cells = [clean_text(c) for c in _CELL_RE.findall(tr)]
            if any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def parse_pres(html: str) -> list[list[str]]:
    """HTML → <pre> 块列表，每块 = 清洗后的非空行。

    行内连续空白必须保留：NSSDC 的 <pre> 行靠多空格对齐标签与值
    （"Mass (10^24 kg)    5.9722"），parse_kv_line 依赖 \\s{2,} 切分。
    早期版本在此压缩为单空格，导致整节丢弃（earthfact 的 Bulk/Orbital
    全丢——见 test_fetch_astro.py 的回归用例）。
    """
    blocks = []
    for m in _PRE_RE.findall(html):
        text = m
        for k, v in _ENTITIES.items():
            text = text.replace(k, v)
        text = re.sub(r"<sup>(.*?)</sup>", r"^\1", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", "", text)
        lines = [ln.strip() for ln in text.splitlines()]
        blocks.append([ln for ln in lines if ln])
    return blocks


def normalize_captions(html: str) -> str:
    """卫星页用 <table><caption>节标题</caption>，行星页用 <h3>。
    把 caption 改写为表外 <h3>，统一走 split_sections 切节。"""
    return re.sub(
        r"(?is)<table([^>]*)>\s*<caption[^>]*>(.*?)</caption>",
        lambda m: f"<h3>{m.group(2)}</h3><table{m.group(1)}>",
        html,
    )


def split_sections(html: str) -> list[tuple[str, str]]:
    """按 <h3>/<h4> 标题切分页面：[(节标题, 节内 HTML), ...]。"""
    parts = re.split(r"(?i)<h[34][^>]*>(.*?)</h[34]>", html)
    out = []
    for i in range(1, len(parts) - 1, 2):
        out.append((clean_text(parts[i]), parts[i + 1]))
    return out


# ---------------------------------------------------------------------------
# 数值解析：NSSDC 的取值形态很杂（千分位、尾点、区间、上限、科学计数、S 标记）
# ---------------------------------------------------------------------------

@dataclass
class Val:
    """一个抽取值。flag 记录形态：None 普通 / range 区间 / upper 上限 / approx 约 /
    sync 同步自转 / text 文本 / missing 缺失。"""
    raw: str
    value: float | None
    flag: str | None = None

    @property
    def comparable(self) -> bool:
        return self.value is not None and self.flag in (None, "approx")


_NUM = r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"  # 兼容 ".0796" 前导点（SBDB 风格）


def parse_value(raw: str) -> Val:
    s = raw.strip()
    if s.endswith("."):  # NSSDC 千分位尾点风格："1,988,400."
        s = s[:-1].strip()
    if not s or s in {"-", "—", "–", "n/a", "N/A"}:
        return Val(raw, None, "missing")
    if s.upper() == "S":  # 卫星页同步自转标记
        return Val(raw, None, "sync")
    m = re.match(rf"^([<>~])\s*({_NUM})$", s)
    if m:
        v = float(m.group(2).replace(",", ""))
        return Val(raw, v, "upper" if m.group(1) == "<" else "approx")
    m = re.match(rf"^([<>~]?\s*[\d.,]+)\s*[x×*]\s*10\^\(?(-?\d+)\)?\s*(?:bar|mb|kg|km|K|C|°|m)?\s*(?:\([^)]*\))?\s*$", s)
    if m:  # 科学计数法，可带单位与尾部括号注释："3 x 10^-15 bar (2 x 10^-12 torr)"
        v = float(re.sub(r"[<>~\s,]", "", m.group(1)))
        return Val(raw, v * 10 ** int(m.group(2)), "approx" if "<" in m.group(1) or "~" in m.group(1) else None)
    m = re.match(rf"^({_NUM})\s*(?:-|–|to)\s*({_NUM})$", s)
    if m:  # 区间：取均值并标记，由人判断
        a = float(m.group(1).replace(",", ""))
        b = float(m.group(2).replace(",", ""))
        return Val(raw, (a + b) / 2, "range")
    m = re.match(rf"^({_NUM})\s*/\s*({_NUM})$", s)
    if m:  # 两半球值（土卫八反照率 "0.05 / 0.5"）：取均值
        a = float(m.group(1).replace(",", ""))
        b = float(m.group(2).replace(",", ""))
        return Val(raw, (a + b) / 2, "hemisphere")
    m = re.match(rf"^({_NUM})$", s)
    if m:
        return Val(raw, float(m.group(1).replace(",", "")), None)
    m = re.match(rf"^([<>~]?)\s*({_NUM})\s*(?:K|C|°|mb|bar|kg|km)?\b(.*)$", s)
    if m:  # 带单位/注释的前导数字："737 K (464 C)"、"~30,000 K"、"1014 mb"
        v = float(m.group(2).replace(",", ""))
        flag = None
        if m.group(1) == "<":
            flag = "upper"
        elif m.group(1) == "~":
            flag = "approx"
        return Val(raw, v, flag)
    return Val(raw, None, "text")


def unit_scale(label: str) -> tuple[float | None, str | None]:
    """从标签文本推断单位换算。(乘数, 备注)；无法换算返回 (None, 原因)。"""
    l = label.lower()
    if "radii" in l or "radius)" in l and "km" not in l:
        return None, "以行星半径为单位，跳过"
    rules = [
        (r"10\^24\s*kg", 1e24), (r"10\^20\s*kg", 1e20), (r"10\^15\s*kg", 1e15),
        (r"10\^12\s*kg", 1e12), (r"10\^6\s*km\^3/s\^2", 1e6), (r"10\^3\s*km", 1e3),
        (r"10\^6\s*km", 1e6), (r"\(km\^3/s\^2\)", 1.0), (r"\(km\)", 1.0),
        (r"\(m/s\^2\)", 1.0), (r"\(km/s\)", 1.0), (r"\(kg/m\^3\)", 1e-3),
        (r"\(deg\)", 1.0), (r"\(days\)", 1.0), (r"\(hrs\)", 1.0), (r"\(hours\)", 1.0),
        (r"\(au\)", AU_KM), (r"\(k\)", None), (r"\(mb\)", 1e-3), (r"\(bars?\)", 1.0),
    ]
    for pat, scale in rules:
        if re.search(pat, l):
            return scale, None
    return None, "标签无单位信息"


# ---------------------------------------------------------------------------
# 字段规格：NSSDC 行标签 → astro.json 字段（按序首个匹配生效；同字段取 prio 高者）
# ---------------------------------------------------------------------------

@dataclass
class Spec:
    key: str
    match: str
    conv: str          # raw/km/days/hrs/mass/dens/tempC/tempK/pressure/yesno/int/axis/gm
    prio: int = 0
    note: str = ""


SPECS = [
    Spec("moons_count", r"number of natural satellites", "int"),
    Spec("rings", r"planetary ring system", "yesno"),
    Spec("escape_velocity_km_s", r"escape velocity", "raw"),
    Spec("orbital_velocity_km_s", r"orbital velocity", "raw"),
    Spec("semimajor_axis_km", r"semi-?major axis", "axis"),
    Spec("orbital_period_days", r"sidereal\s+(orbit|revolution)\s+period", "days", prio=10),
    Spec("orbital_period_days", r"(orbit|orbital|revolution)\s*period", "days"),
    Spec("rotation_period_hours", r"rotation\s*period", "rot"),
    Spec("obliquity_deg", r"obliquity", "raw"),
    Spec("_incl_equator", r"inclination\s+(of|to)\s+.*equator", "raw"),  # 非黄道倾角，不参与对比
    Spec("inclination_deg", r"inclination.*ecliptic", "raw", prio=10),
    Spec("inclination_deg", r"inclination", "raw"),
    Spec("eccentricity", r"eccentricity", "raw"),
    Spec("albedo_geometric", r"geometric albedo", "raw", note="geometric"),
    Spec("albedo_bond", r"bond albedo", "raw", note="bond"),
    Spec("mean_temp_c", r"average temperature", "tempC", note="mean"),
    Spec("mean_temp_c", r"effective temperature", "tempK", note="effective"),
    Spec("mean_temp_c_bb", r"black-?body temperature", "tempK", note="black-body"),
    Spec("mean_temp_c_surface", r"^surface temperature", "tempRange", note="surface-range"),
    Spec("surface_pressure_bar", r"surface pressure", "pressure"),
    Spec("gravity_m_s2", r"gravity", "raw"),
    Spec("gm_km3_s2", r"^gm\b", "gm"),
    Spec("mass_kg", r"^mass\b", "mass"),
    Spec("radius_km", r"volumetric mean radius", "raw"),
    Spec("density_g_cm3", r"mean density", "dens"),
]


def convert(spec: Spec, val: Val, label: str) -> tuple[float | None, str | None]:
    """按规格把 Val 换算成 astro.json 口径。返回 (值, 备注)。"""
    note = spec.note
    if spec.conv == "yesno":  # 文本型必须先于 None 早退处理
        low = val.raw.strip().lower()
        if low.startswith("y"):
            return 1.0, note
        if low.startswith("n"):
            return 0.0, note
        return None, "text"
    if val.value is None:
        return None, val.flag
    v = val.value
    if spec.conv == "mass":
        scale, why = unit_scale(label)
        if scale is None:
            return None, why
        v *= scale
    elif spec.conv == "dens":
        scale, why = unit_scale(label)
        if scale is None:
            return None, why
        v *= scale
    elif spec.conv == "axis":
        scale, why = unit_scale(label)
        if scale is None:
            return None, why
        v *= scale
    elif spec.conv == "days":
        pass
    elif spec.conv == "rot":
        if re.search(r"\(days\)", label, re.I):
            v *= 24.0
    elif spec.conv == "tempC":
        m = re.search(r"\(([+-]?[\d.]+)\s*C\)", val.raw)
        if m:  # 页内直接给了摄氏值（如 "288 K (15 C)"）
            v = float(m.group(1))
        elif re.search(r"\bK\b", val.raw):
            v -= 273.15
    elif spec.conv == "tempK":
        v -= 273.15
    elif spec.conv == "tempRange":
        m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*K", val.raw)
        if not m:
            return None, "无法解析温度区间"
        v = (float(m.group(1)) + float(m.group(2))) / 2 - 273.15
        note = "NSSDC 为表面温度区间，取均值"
    elif spec.conv == "pressure":
        raw = val.raw.lower()
        if "microbar" in raw or "μbar" in raw:
            v *= 1e-6
        elif "mb" in raw:
            v *= 1e-3
        elif "pa" in raw and "bar" not in raw:
            v *= 1e-5
    elif spec.conv == "yesno":
        if val.raw.strip().lower().startswith("y"):
            v = 1.0
        elif val.raw.strip().lower().startswith("n"):
            v = 0.0
        else:
            return None, "text"
    elif spec.conv == "int":
        v = float(round(v))
    elif spec.conv == "gm":
        v *= 1e6
    if val.flag == "range":
        note = (note + "；" if note else "") + "NSSDC 为区间，取均值"
    if val.flag == "hemisphere":
        note = (note + "；" if note else "") + "NSSDC 为两半球值，取均值"
    if val.flag == "upper":
        note = (note + "；" if note else "") + "NSSDC 为上限值"
    return v, note


def apply_label(store: dict, label: str, raw: str, where: str) -> None:
    """把一行 (标签, 原始值) 按 SPECS 归入 store。"""
    for spec in SPECS:
        if not re.search(spec.match, label, re.I):
            continue
        val = parse_value(raw)
        v, note = convert(spec, val, label)
        if v is None and note in (None, "missing", "text"):
            return
        cur = store.get(spec.key)
        if cur is None or spec.prio > cur[2]:
            store[spec.key] = (v, note, spec.prio, where, val.flag, spec.conv)
        return


def parse_kv_line(line: str) -> tuple[str, str] | None:
    """<pre> 行 → (标签, 值)。按优先级尝试三种形态：

    1. 'Label: value'            冒号分隔（少数页面用）
    2. 'Label   value'           多空格对齐（NSSDC <pre> 标准形态）
    3. 'Label value'             单空格分隔的兜底：从行尾抓最后一个
                                 token，仅当它是数值（可带 <>~ 前缀）
                                 或 Yes/No 时才切分
    """
    m = re.match(r"^([A-Za-z][^:]{1,60}?)\s*:\s*(\S.*)$", line)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    parts = re.split(r"\s{2,}", line.strip())
    if len(parts) >= 2:
        return parts[0].strip(), " ".join(parts[1:]).strip()
    # 兜底：尾部 token 是数值或 Yes/No 才切（如 "Planetary ring system No"）
    m = re.match(r"^(.{1,60}?)\s+([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)?(?:\.\d+)?(?:[eE][+-]?\d+)?|[Yy]es|[Nn]o)$", line.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


# ---------------------------------------------------------------------------
# NSSDC 页面适配器
# ---------------------------------------------------------------------------

# 页面 → (对象 id, 页面角色)。角色：
#   planet  对比表/pre 双格式自动甄别的行星页
#   earth   纯 pre 格式（地球是比值基准）
#   sat     卫星参数页（表头驱动的 Bulk + Orbital 两张表）
#   mars    火星页 + "Satellites of Mars" 转置表
NSSDC_PAGES = {
    "sunfact": ("sun", "planet"),
    "mercuryfact": ("mercury", "planet"),
    "venusfact": ("venus", "planet"),
    "earthfact": ("earth", "earth"),
    "marsfact": ("mars", "mars"),
    "jupiterfact": ("jupiter", "planet"),
    "saturnfact": ("saturn", "planet"),
    "uranusfact": ("uranus", "planet"),
    "neptunefact": ("neptune", "planet"),
    "moonfact": ("moon", "planet"),
    "plutofact": ("pluto", "planet"),
    "joviansatfact": (None, "sat"),
    "saturniansatfact": (None, "sat"),
    "uraniansatfact": (None, "sat"),
    "neptuniansatfact": (None, "sat"),
}

# 卫星页页名 → 本站收录的卫星（页内名 → 本站 id）
SAT_PAGE_MOONS = {
    "joviansatfact": {"io": "io", "europa": "europa", "ganymede": "ganymede", "callisto": "callisto"},
    "saturniansatfact": {"mimas": "mimas", "enceladus": "enceladus", "tethys": "tethys",
                         "dione": "dione", "rhea": "rhea", "titan": "titan",
                         "hyperion": "hyperion", "iapetus": "iapetus"},
    "uraniansatfact": {"ariel": "ariel", "umbriel": "umbriel", "titania": "titania",
                       "oberon": "oberon", "miranda": "miranda"},
    "neptuniansatfact": {"triton": "triton"},
}

SAT_HEADER_SPECS = [  # 卫星表表头关键词 → (字段, 换算)
    (r"mass", "mass_kg", "mass"),
    (r"radius", "radius_km", "radius"),
    (r"mean density", "density_g_cm3", "dens"),
    (r"albedo", "albedo_geometric", "raw"),
    (r"semi-?major axis.*km", "semimajor_axis_km", "axis"),
    (r"orbital\s*period", "orbital_period_days", "days"),
    (r"rotation\s*period", "rotation_period_hours", "rot"),
    (r"inclination", "inclination_deg", "raw"),
    (r"eccentricity", "eccentricity", "raw"),
]


def norm_moon_name(cell: str) -> str:
    """'Io (I)' / 'Mimas (I)' → 'io'；'Titan (VI)' → 'titan'。"""
    name = re.sub(r"\s*\(.*?\)\s*", "", cell).strip().lower()
    return re.sub(r"[^a-z]", "", name)


def triaxial_mean(raw: str) -> Val:
    """'208 x 197 x 191' → 三轴均值；单值原样返回。"""
    parts = re.split(r"\s*[x×]\s*", raw.strip())
    if len(parts) == 3:
        try:
            nums = [float(p.replace(",", "")) for p in parts]
            return Val(raw, sum(nums) / 3, "range")  # range flag → 报告中提示三轴均值
        except ValueError:
            pass
    return parse_value(raw)


def extract_planet_page(html: str, role: str) -> dict:
    """行星页：对比表（Subject/Earth/Ratio）或 pre 键值对，自动甄别。"""
    store: dict = {}
    for title, content in split_sections(html):
        tables = parse_tables(content)
        used_table = False
        for tbl in tables:
            if len(tbl) < 2 or len(tbl[0]) < 3:
                continue
            header = [c.lower() for c in tbl[0]]
            if not any("earth" in h for h in header[1:]):
                continue  # 不是对比表（如卫星表），跳过
            for row in tbl[1:]:
                if len(row) < 2:
                    continue
                apply_label(store, row[0], row[1], f"{title}")
            used_table = True
        if used_table:
            continue
        for block in parse_pres(content):
            for line in block:
                kv = parse_kv_line(line)
                if kv:
                    apply_label(store, kv[0], kv[1], f"{title}")
    return store


def extract_mars_satellites(html: str, objs: dict) -> None:
    """marsfact 的 'Satellites of Mars' 转置表 → phobos / deimos。"""
    for title, content in split_sections(html):
        if "satellites of mars" not in title.lower():
            continue
        for tbl in parse_tables(content):
            if len(tbl) < 2 or not tbl[0] or tbl[0][0] != "":
                continue
            names = [norm_moon_name(c) for c in tbl[0][1:]]
            for row in tbl[1:]:
                if len(row) < 2 or not row[0]:
                    continue
                for name, raw in zip(names, row[1:]):
                    if name not in ("phobos", "deimos"):
                        continue
                    store = objs.setdefault(name, {})
                    if "radius" in row[0].lower() and "axis" in row[0].lower():
                        continue  # 三轴半径单独攒一起
                    apply_label(store, row[0], raw, f"{title}")
            # 三轴半径 → 均值
            radii = {}
            for row in tbl[1:]:
                m = re.match(r"(subplanetary|along-orbit|polar)\s+axis radius", row[0], re.I)
                if m and len(row) >= 2:
                    for name, raw in zip(names, row[1:]):
                        v = parse_value(raw)
                        if v.value is not None:
                            radii.setdefault(name, []).append(v.value)
            for name, vals in radii.items():
                if name in ("phobos", "deimos") and vals:
                    objs.setdefault(name, {})["radius_km"] = (
                        sum(vals) / len(vals), "三轴均值", 0, "Satellites of Mars", "range", "raw")


def extract_sat_page(html: str, page: str, objs: dict, only: set[str] | None = None) -> None:
    """卫星参数页：表头驱动的 Bulk / Orbital 两张表，行 = 卫星。
    only：限定只保留这些本站对象 id（--objects 精准拉取用）。"""
    wanted = SAT_PAGE_MOONS[page]
    if only:
        wanted = {k: v for k, v in wanted.items() if v in only}
        if not wanted:
            return
    for title, content in split_sections(html):
        for tbl in parse_tables(content):
            if len(tbl) < 2:
                continue
            header = tbl[0]
            if not header or header[0] != "":
                continue  # 数据行或分组行
            cols = []
            for cell in header[1:]:
                key = conv = None
                for pat, k, c in SAT_HEADER_SPECS:
                    if re.search(pat, cell, re.I):
                        key, conv = k, c
                        break
                cols.append((key, conv, cell))
            if not any(k for k, _, _ in cols):
                continue
            for row in tbl[1:]:
                if len(row) < 2 or not row[0]:
                    continue  # 分组标题行（如 'Galilean Satellites'）或空行
                name = norm_moon_name(row[0])
                if name not in wanted:
                    continue
                store = objs.setdefault(wanted[name], {})
                for (key, conv, hdr), raw in zip(cols, row[1:]):
                    if key is None:
                        continue
                    if key == "radius_km":
                        val = triaxial_mean(raw)
                    else:
                        val = parse_value(raw)
                    if val.flag == "sync":  # 同步自转：周期即自转，稍后回填
                        store["_sync"] = True
                        continue
                    v, note = convert(Spec(key, "", conv), val, hdr)
                    if v is None and note in (None, "missing", "text"):
                        continue
                    store[key] = (v, note, 0, f"{title}", val.flag, conv)
    # 同步自转回填：rotation = orbital period（小时）
    for oid, store in objs.items():
        if store.pop("_sync", False):
            per = store.get("orbital_period_days")
            if per and per[0] is not None:
                store["rotation_period_hours"] = (
                    per[0] * 24.0, "同步自转（= 轨道周期）", 0, "sat page", None, "rot")


def fetch_nssdc(offline: bool, only_pages: set[str] | None = None,
                only_objs: set[str] | None = None) -> tuple[dict, list[str]]:
    """抓取并解析 NSSDC 页面。返回 (对象→字段store, 页面 Last Updated 列表)。
    only_pages：限定页面；only_objs：限定对象（卫星页内过滤，火星页过滤火卫）。
    两者为 None 时全量。缓存命中时不会重新发起网络请求。"""
    objs: dict = {}
    dates = []
    for page, (oid, role) in NSSDC_PAGES.items():
        if only_pages and page not in only_pages:
            continue
        if only_objs and role != "sat" and oid not in only_objs:
            continue
        url = NSSDC_BASE + page + ".html"
        try:
            html = fetch_cached("nssdc", page + ".html", url, offline)
        except Exception as e:  # 单页失败不拖垮整体
            print(f"  [warn] NSSDC {page}: {e}", file=sys.stderr)
            continue
        html = normalize_captions(html)
        m = re.search(r"Last Updated:\s*([^<\n]+)", html)
        if m:
            dates.append(f"{page}: {m.group(1).strip()}")
        if role in ("planet", "earth"):
            store = extract_planet_page(html, role)
            if oid and store:
                objs[oid] = store
        elif role == "mars":
            if not only_objs or "mars" in only_objs:
                store = extract_planet_page(html, role)
                if store:
                    objs["mars"] = store
            if not only_objs or only_objs & {"phobos", "deimos"}:
                extract_mars_satellites(html, objs)
        elif role == "sat":
            extract_sat_page(html, page, objs, only_objs)
        print(f"  NSSDC {page}.html ✓" + (f"（{m.group(1).strip()}）" if m else ""))
    return objs, dates


# ---------------------------------------------------------------------------
# JPL SBDB
# ---------------------------------------------------------------------------

SBDB_OBJECTS = ["ceres", "pluto", "makemake", "haumea", "eris"]


def fetch_sbdb(offline: bool, only_objs: set[str] | None = None) -> tuple[dict, list[str]]:
    objs: dict = {}
    notes = []
    for sstr in SBDB_OBJECTS:
        if only_objs and sstr not in only_objs:
            continue
        url = f"{SBDB_URL}?sstr={sstr}&phys-par=1&full-prec=1"
        try:
            text = fetch_cached("sbdb", sstr + ".json", url, offline)
            d = json.loads(text)
        except Exception as e:
            print(f"  [warn] SBDB {sstr}: {e}", file=sys.stderr)
            continue
        if "object" not in d:
            print(f"  [warn] SBDB {sstr}: 无匹配对象", file=sys.stderr)
            continue
        store: dict = {}
        for p in d.get("phys_par", []):
            name, raw = p.get("name", ""), p.get("value")
            if raw is None:
                continue
            val = parse_value(str(raw))
            if name == "GM":
                store["mass_kg"] = (val.value * 1e9 / G_CODATA,
                                    f"SBDB GM/G 换算（G=CODATA 6.67430e-11），ref={p.get('ref')}",
                                    0, "sbdb", None, "gm")
            elif name == "diameter":
                store["radius_km"] = (val.value / 2, "SBDB diameter/2", 0, "sbdb", None, "raw")
            elif name == "density":
                store["density_g_cm3"] = (val.value, "SBDB", 0, "sbdb", None, "raw")
            elif name == "rot_per":
                store["rotation_period_hours"] = (val.value, "SBDB", 0, "sbdb", None, "raw")
            elif name == "albedo":
                store["albedo_geometric"] = (val.value, "SBDB", 0, "sbdb", None, "raw")
        for e in d.get("orbit", {}).get("elements", []):
            name, raw = e.get("name", ""), e.get("value")
            if raw is None:
                continue
            val = parse_value(str(raw))
            if name == "a":
                store["semimajor_axis_km"] = (val.value * AU_KM, "SBDB a(au)×AU", 0, "sbdb", None, "axis")
            elif name == "e":
                store["eccentricity"] = (val.value, "SBDB", 0, "sbdb", None, "raw")
            elif name == "i":
                store["inclination_deg"] = (val.value, "SBDB", 0, "sbdb", None, "raw")
            elif name == "per":
                store["orbital_period_days"] = (val.value, "SBDB", 0, "sbdb", None, "raw")
        if store:
            objs[sstr] = store
        sig = d.get("signature", {}).get("version", "?")
        soln = d.get("orbit", {}).get("soln_date") or d.get("orbit", {}).get("producer", "")
        notes.append(f"{sstr}: SBDB API v{sig}，轨道解 {soln or '?'}")
        print(f"  SBDB {sstr} ✓（{len(store)} 个字段）")
    return objs, notes


# ---------------------------------------------------------------------------
# 对比与报告
# ---------------------------------------------------------------------------

FIELDS = [
    ("physical.mass_kg", "质量 (kg)", "abs"),
    ("physical.radius_km", "平均半径 (km)", "abs"),
    ("physical.density_g_cm3", "密度 (g/cm³)", "abs"),
    ("physical.gravity_m_s2", "表面重力 (m/s²)", "abs"),
    ("physical.escape_velocity_km_s", "逃逸速度 (km/s)", "abs"),
    ("physical.albedo", "反照率", "abs"),
    ("physical.albedo_bond", "反照率(Bond)", "abs"),
    ("physical.albedo_geometric", "反照率(Geometric)", "abs"),
    ("physical.mean_temp_c", "平均温度 (°C)", "abs"),
    ("physical.mean_temp_c_bb", "平均温度 (°C, black-body 口径)", "abs"),
    ("physical.mean_temp_c_surface", "平均温度 (°C, 表面口径)", "abs"),
    ("physical.surface_pressure_bar", "表面气压 (bar)", "rel"),
    ("orbit.semimajor_axis_km", "半长轴 (km)", "abs"),
    ("orbit.orbital_period_days", "轨道周期 (天)", "abs"),
    ("orbit.orbital_velocity_km_s", "轨道速度 (km/s)", "abs"),
    ("orbit.inclination_deg", "轨道倾角 (°)", "abs"),
    ("orbit.eccentricity", "偏心率", "abs"),
    ("orbit.obliquity_deg", "转轴倾角 (°)", "abs"),
    ("orbit.rotation_period_hours", "自转周期 (h)", "abs"),
    ("moons.count", "卫星数", "abs"),
    ("rings", "环系", "bool"),
]


def get_path(obj: dict, path: str):
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def fmt(v, kind: str) -> str:
    if v is None:
        return "—"
    if kind == "bool":
        return "是" if v else "否"
    if isinstance(v, float):
        if v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e6):
            return f"{v:.4g}"
        return f"{v:g}"
    return str(v)


def compare(astro: dict, fetched: dict, tol_pct: float) -> list[dict]:
    """逐对象逐字段对比。返回差异行列表。"""
    rows = []
    for oid, store in sorted(fetched.items()):
        cur = astro.get(oid)
        if cur is None:
            rows.append({"obj": oid, "field": "*", "label": "对象", "cur": "不存在",
                         "new": "存在", "verdict": "新增对象", "note": "astro.json 中无此对象"})
            continue
        for path, label, kind in FIELDS:
            key = path.split(".")[-1]
            if key not in store:
                continue
            new_v, note, _prio, where, flag, _conv = store[key]
            old_v = get_path(cur, path)
            if new_v is None and flag not in ("sync",):
                continue
            if old_v is None:
                rows.append({"obj": oid, "field": path, "label": label, "cur": None,
                             "new": new_v, "verdict": "新增", "note": note or where, "flag": flag})
                continue
            if kind == "bool":
                same = bool(old_v) == bool(new_v)
                rel = 0.0 if same else 100.0
            else:
                if old_v == 0:
                    rel = 0.0 if new_v == 0 else 100.0
                else:
                    rel = abs(new_v - old_v) / abs(old_v) * 100
            if rel <= tol_pct:
                verdict = "一致"
            elif rel <= tol_pct * 5:
                verdict = "微小差异"
            else:
                verdict = "显著差异"
            # 反照率双口径：NSSDC/SBDB 同时给 Bond 与 Geometric，本站主字段 albedo 为
            # 合库时选定的展示主值（不参与对比），两个口径字段各自直接对比即可。
            # 自转周期符号约定：本站负值表逆行，源可能只给幅值
            if (path == "orbit.rotation_period_hours" and verdict != "一致"
                    and old_v and new_v and old_v * new_v < 0):
                rel2 = abs(abs(new_v) - abs(old_v)) / abs(old_v) * 100
                if rel2 <= tol_pct:
                    verdict, rel = "一致", rel2
                    note = "逆行自转：本站存负值，源给幅值，绝对值一致"
            rows.append({"obj": oid, "field": path, "label": label, "cur": old_v,
                         "new": new_v, "verdict": verdict, "rel": rel,
                         "note": note or "", "flag": flag})
    return rows


def write_report(rows: list[dict], astro: dict, fetched: dict,
                 src_notes: list[str], tol_pct: float, path: Path) -> int:
    sig = [r for r in rows if r["verdict"] == "显著差异"]
    minor = [r for r in rows if r["verdict"] == "微小差异"]
    new_objs = [r for r in rows if r["verdict"] == "新增对象"]
    add = [r for r in rows if r["verdict"] == "新增"]
    match = [r for r in rows if r["verdict"] == "一致"]
    now = datetime.now(timezone.utc).astimezone()
    L = []
    L.append("# 天体数据源核查报告")
    L.append("")
    L.append(f"- 生成时间：{now:%Y-%m-%d %H:%M:%S %Z}")
    L.append(f"- 数据源：NSSDC Planetary Fact Sheets（NASA Goddard，公共领域）+ JPL SBDB API（免 key，公共领域）")
    L.append(f"- 对比基准：`docs/data/astro.json`（{len(astro)} 个对象）")
    L.append(f"- 差异阈值：相对差异 ≤ {tol_pct:g}% 记为一致")
    L.append("")
    L.append("## 总览")
    L.append("")
    L.append("| 指标 | 数量 |")
    L.append("|---|---|")
    L.append(f"| 覆盖字段（一致） | {len(match)} |")
    L.append(f"| 微小差异（{tol_pct:g}%–{tol_pct * 5:g}%） | {len(minor)} |")
    L.append(f"| **显著差异（>{tol_pct * 5:g}%）** | **{len(sig)}** |")
    L.append(f"| 新增（现有库缺失） | {len(add)} |")
    L.append(f"| 未收录对象（源有数据） | {len(new_objs)} |")
    L.append("")
    objs_covered = sorted({r["obj"] for r in rows})
    objs_missing = sorted(set(astro) - set(fetched))
    objs_extra = sorted(set(fetched) - set(astro))
    L.append(f"本次源覆盖 {len(objs_covered)} 个对象（库内 {len(astro)} 个）：{', '.join(objs_covered)}")
    if objs_missing:
        L.append("")
        L.append(f"**库内对象源未覆盖**：{', '.join(objs_missing)}")
    if objs_extra:
        L.append("")
        L.append(f"**源有数据但库未收录**：{', '.join(objs_extra)}（是否扩收是产品决策，见下）")
    L.append("")
    if sig:
        L.append("## 显著差异明细（需人工判断）")
        L.append("")
        L.append("| 对象 | 字段 | astro.json 现值 | NASA 源值 | 相对差异 | 说明 |")
        L.append("|---|---|---|---|---|---|")
        for r in sig:
            L.append(f"| {r['obj']} | {r['label']} | {fmt(r['cur'], 'abs')} | "
                     f"{fmt(r['new'], 'abs')} | {r.get('rel', 0):.3g}% | {r.get('note', '') or '—'} |")
        L.append("")
    if minor:
        L.append("## 微小差异（舍入噪声，通常无需动作）")
        L.append("")
        L.append("| 对象 | 字段 | astro.json 现值 | NASA 源值 | 相对差异 |")
        L.append("|---|---|---|---|---|")
        for r in minor:
            L.append(f"| {r['obj']} | {r['label']} | {fmt(r['cur'], 'abs')} | "
                     f"{fmt(r['new'], 'abs')} | {r.get('rel', 0):.3g}% |")
        L.append("")
    if new_objs:
        L.append("## 未收录对象（NASA 源有数据，本站未收录）")
        L.append("")
        L.append("| 对象 | 源覆盖字段数 | 抽到的字段 |")
        L.append("|---|---|---|")
        for r in new_objs:
            store = fetched.get(r["obj"], {})
            key_list = sorted(k for k in store if not k.startswith("_"))
            L.append(f"| {r['obj']} | {len(key_list)} | {', '.join(key_list)} |")
        L.append("")
        L.append("> 是否扩收是产品决策：维持精选 32 个就忽略；若要扩收，需先补贴图与文章。")
        L.append("")
    if add:
        L.append("## 新增值（现有库为缺失，源有值）")
        L.append("")
        L.append("| 对象 | 字段 | NASA 源值 | 说明 |")
        L.append("|---|---|---|---|")
        for r in add:
            L.append(f"| {r['obj']} | {r['label']} | {fmt(r['new'], 'abs')} | {r.get('note', '') or '—'} |")
        L.append("")
    calib = [r for r in match if "口径" in (r.get("note") or "") or "逆行" in (r.get("note") or "")]
    if calib:
        L.append("## 口径甄别（自动判定为一致，但取值口径与默认不同）")
        L.append("")
        L.append("| 对象 | 字段 | astro.json 现值 | 甄别结果 |")
        L.append("|---|---|---|---|")
        for r in calib:
            L.append(f"| {r['obj']} | {r['label']} | {fmt(r['cur'], 'abs')} | {r['note']} |")
        L.append("")
    L.append("## 口径提示")
    L.append("")
    L.append("- **反照率**：NSSDC 同时给 Bond 与 Geometric 两种。本站 `albedo` 字段历史上混用"
             "（地球与气态巨行星取 Bond、月球与卫星取 Geometric），脚本已自动甄别口径，"
             "上表「一致」行的小数注即本站实际取用的口径；建议后续统一为 Geometric 或在数据页注明。")
    L.append("- **卫星页反照率精度**：NSSDC 卫星参数页只给 2 位有效数字（如土卫二 `1.0`、"
             "土卫五 `0.7`），与更精确的文献值差几个百分点属正常，勿据此改库。")
    L.append("- **温度**：行星页给「Average temperature」（平均），月球等只有「Black-body temperature」"
             "（有效温度口径），两者不可直接互替。")
    L.append("- **半径**：不规则卫星 NSSDC 给三轴尺寸（如 `208 x 197 x 191`），本站存三轴算术均值，"
             "与 JPL 的体积等效半径会有 ~0.5% 级差。")
    L.append("- **自转周期**：卫星页标记 `S` 表示同步自转（= 轨道周期），脚本已按此回填。")
    L.append("- **质量**：SBDB 质量由 GM/G 换算（G 取 CODATA 2018），与 NSSDC 直接给的质量可能存在"
             "末位差。")
    L.append("")
    L.append("## 数据源版本")
    L.append("")
    for n in src_notes:
        L.append(f"- {n}")
    L.append("")
    L.append("## 建议动作")
    L.append("")
    if sig or add:
        L.append("1. 逐条核对「显著差异明细」与「新增值」，确认是源更新还是本站口径差异；")
        L.append("2. 手动更新 `docs/data/astro.json`（同步更新对应 `sources`/`verified`）；")
        L.append("3. 跑 `python scripts/lint_data.py` → `python scripts/gen_pages.py` → "
                 "`python scripts/gen_pages.py --check` → `mkdocs build --strict`；")
        L.append("4.  commit push（Cloudflare Pages 自动构建）。")
    else:
        L.append("无需动作：全部字段与 NASA 源一致（在阈值内）。下次核查建议按季度节奏。")
    L.append("")
    path.write_text("\n".join(L), encoding="utf-8")
    return len(sig)


# ---------------------------------------------------------------------------
# status：零网络本地体检
# ---------------------------------------------------------------------------

CAT_ZH = {"star": "恒星", "planet": "行星", "dwarf_planet": "矮行星", "moon": "卫星"}


def status_report(astro: dict) -> int:
    """零网络本地体检：数据集全景——对象统计 / 字段填充矩阵 / 核对新鲜度 / 收录边界。
    随时可跑，不发起任何网络请求，用于"心里有数"后再决定针对性拉取什么。"""
    objs = list(astro.values())
    cats: dict[str, int] = {}
    for o in objs:
        cats[o["category"]] = cats.get(o["category"], 0) + 1
    print(f"== 数据集总览（{ASTRO_JSON.relative_to(ROOT)}）==")
    print(f"对象总数 {len(objs)}：" +
          " / ".join(f"{CAT_ZH.get(k, k)} {v}" for k, v in sorted(cats.items())))

    # 字段填充矩阵：physical/orbit 下库中出现过的全部标量字段
    keys: dict[str, set[str]] = {"physical": set(), "orbit": set()}
    for o in objs:
        for grp in ("physical", "orbit"):
            for k in (o.get(grp) or {}):
                keys[grp].add(k)
    print("\n== 字段填充矩阵（缺失对象清单）==")
    for grp in ("physical", "orbit"):
        print(f"[{grp}]")
        for k in sorted(keys[grp]):
            miss = [o["id"] for o in objs if (o.get(grp) or {}).get(k) is None]
            print(f"  {k:26s} {len(objs) - len(miss):2d}/{len(objs)}  "
                  f"缺失: {', '.join(miss) if miss else '—'}")

    # 每对象核对日期与源版本日期
    print("\n== 每对象核对新鲜度（verified / 源页面版本）==")
    today = date.today()
    stale = []
    for o in sorted(objs, key=lambda x: x.get("verified") or "9999"):
        v = o.get("verified") or "—"
        try:
            age = (today - date.fromisoformat(v)).days if v != "—" else None
        except ValueError:
            age = None
        sd = o.get("source_dates") or {}
        src = "; ".join(f"{k.replace('nssdc_', '').replace('fact', '')} {val}"
                        for k, val in sorted(sd.items())) or "—"
        if age is not None and age > 365:
            stale.append((o["id"], age))
        print(f"  {o['id']:10s} {CAT_ZH.get(o['category'], o['category']):4s} "
              f"verified={v:10s} {f'({age}天前)' if age is not None else '':8s} 源版本: {src}")
    if stale:
        print(f"  ⚠ 超过一年未核对：{', '.join(f'{i}({a}天)' for i, a in stale)}")

    # 收录边界：源有数据但库未收录
    print("\n== 收录边界（SBDB 有数据、本站未收录）==")
    extra = [s for s in SBDB_OBJECTS if s not in astro]
    if extra:
        print(f"  {', '.join(extra)}：SBDB 仅覆盖约 5 个轨道字段，缺物理参数/贴图/描述——"
              f"按既定决策维持精选不入队；如要入队：--propose {','.join(extra)}")
    else:
        print("  无")
    return 0


# ---------------------------------------------------------------------------
# propose：为库外对象生成候选 JSON 骨架
# ---------------------------------------------------------------------------

# 库外对象的元信息（公开史实，非测量数据；入队前仍应人工复核）
PROPOSE_META = {
    "eris":     ("阋神星", "Eris", "dwarf_planet", "迈克尔·布朗等", 2005),
    "haumea":   ("妊神星", "Haumea", "dwarf_planet", "迈克尔·布朗等", 2004),
    "makemake": ("鸟神星", "Makemake", "dwarf_planet", "迈克尔·布朗等", 2005),
}

_PROPOSE_PHYS = ["mass_kg", "radius_km", "density_g_cm3", "gravity_m_s2",
                 "escape_velocity_km_s", "mean_temp_c", "surface_pressure_bar",
                 "albedo", "albedo_bond", "albedo_geometric",
                 "mean_temp_c_bb", "mean_temp_c_surface"]
_PROPOSE_ORBIT = ["semimajor_axis_km", "orbital_period_days", "orbital_velocity_km_s",
                  "inclination_deg", "eccentricity", "obliquity_deg", "rotation_period_hours"]


def propose_objects(astro: dict, names: list[str], offline: bool) -> int:
    """为库外对象生成候选 JSON 骨架：源（SBDB）能填的填，填不上一律 null——不编造。
    产物落 reports/propose_<id>.json，人审后粘贴进 astro.json 的 objects 数组。"""
    today = date.today().isoformat()
    rc = 0
    for sstr in names:
        if sstr in astro:
            print(f"[skip] {sstr} 已在库中，无需 propose")
            continue
        url = f"{SBDB_URL}?sstr={sstr}&phys-par=1&full-prec=1"
        try:
            d = json.loads(fetch_cached("sbdb", sstr + ".json", url, offline))
        except Exception as e:
            print(f"[error] SBDB {sstr}: {e}", file=sys.stderr)
            rc = 2
            continue
        if "object" not in d:
            print(f"[error] SBDB {sstr}: SBDB 无匹配对象", file=sys.stderr)
            rc = 2
            continue
        store, _ = fetch_sbdb(offline, {sstr})
        st = store.get(sstr, {})
        zh, en, cat, disc, year = PROPOSE_META.get(
            sstr, (None, sstr.title(), "dwarf_planet", None, None))
        obj = {
            "id": sstr,
            "name": zh or sstr,
            "name_en": en,
            "category": cat,
            "parent": "sun",
            "tagline": None,
            "physical": {k: (st[k][0] if k in st and st[k][0] is not None else None)
                         for k in _PROPOSE_PHYS},
            "orbit": {k: (st[k][0] if k in st and st[k][0] is not None else None)
                      for k in _PROPOSE_ORBIT},
            "moons": {"count": None, "notable": []},
            "rings": None,
            "magnetic_field": None,
            "atmosphere": None,
            "discovery": {"known_since": None, "discoverer": disc, "year": year},
            "sources": ["jpl_sbdb"],
            "source_dates": {},
            "verified": today,
            "image": None,
        }
        REPORT_DIR.mkdir(exist_ok=True)
        path = REPORT_DIR / f"propose_{sstr}.json"
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        filled = [k for grp in ("physical", "orbit")
                  for k, v in obj[grp].items() if v is not None]
        missing = [k for grp in ("physical", "orbit")
                   for k, v in obj[grp].items() if v is None]
        print(f"\n== {sstr} 候选骨架 → {path.relative_to(ROOT)} ==")
        print(f"  源可填 {len(filled)} 项：{', '.join(filled) or '—'}")
        print(f"  留 null {len(missing)} 项（没有的数据不编造，待权威源或人工补充）："
              f"{', '.join(missing)}")
        print(f"  入队前还需人工补：tagline、贴图 docs/assets/planets/{en.lower()}.webp、"
              f"延伸文章（articles/）、sources 交叉校验")
    return rc


def pages_for_objects(oids: set[str]) -> set[str]:
    """对象 id → 需要拉取的 NSSDC 页名集合（卫星归系统页，火卫归 marsfact）。"""
    pages = set()
    for page, (poid, _role) in NSSDC_PAGES.items():
        if poid in oids:
            pages.add(page)
    for page, moons in SAT_PAGE_MOONS.items():
        if oids & set(moons.values()):
            pages.add(page)
    if oids & {"phobos", "deimos"}:
        pages.add("marsfact")
    return pages


def main() -> int:
    ap = argparse.ArgumentParser(description="从 NASA 公开源拉取天体数据并生成变更报告（只读 astro.json）")
    ap.add_argument("command", nargs="?", default=None, choices=["status"],
                    help="status = 零网络本地体检（对象/字段/新鲜度/收录边界），不拉取")
    ap.add_argument("--source", default="nssdc,sbdb", help="数据源：nssdc / sbdb，逗号分隔")
    ap.add_argument("--objects", default="",
                    help="限定对象（逗号分隔）：只拉取这些对象对应的源页，报告只含它们")
    ap.add_argument("--propose", default="",
                    help="为库外对象生成候选 JSON 骨架（逗号分隔）：源有的填、没有的留 null，不编造")
    ap.add_argument("--offline", action="store_true", help="不联网，用缓存原始数据")
    ap.add_argument("--tolerance", type=float, default=1.0, help="一致判定阈值（相对%%）")
    ap.add_argument("--verbose", action="store_true", help="打印每个对象抽取到的字段")
    args = ap.parse_args()

    astro = {o["id"]: o for o in json.loads(ASTRO_JSON.read_text(encoding="utf-8"))["objects"]}

    if args.command == "status":
        return status_report(astro)

    if args.propose:
        names = [s.strip() for s in args.propose.split(",") if s.strip()]
        return propose_objects(astro, names, args.offline)

    sources = [s.strip() for s in args.source.split(",") if s.strip()]
    only_objs = {s.strip() for s in args.objects.split(",") if s.strip()} or None
    only_pages = None
    if only_objs:
        only_pages = pages_for_objects(only_objs)
        known = set(astro) | set(SBDB_OBJECTS)
        unknown = only_objs - known
        if unknown:
            print(f"[warn] 未知对象 id（不在库也不在 SBDB 列表）：{', '.join(sorted(unknown))}"
                  f"；如需入队请改用 --propose", file=sys.stderr)
        if not only_pages and not (only_objs & set(SBDB_OBJECTS)):
            print("[error] 这些对象没有对应的 NSSDC 页面或 SBDB 数据", file=sys.stderr)
            return 2

    fetched: dict = {}
    src_notes: list[str] = []
    failed = False
    if "nssdc" in sources:
        print("== NSSDC Planetary Fact Sheets ==")
        try:
            objs, dates = fetch_nssdc(args.offline, only_pages, only_objs)
            fetched.update(objs)
            src_notes += [f"NSSDC {d}" for d in dates]
        except Exception as e:
            print(f"[error] NSSDC 源失败：{e}", file=sys.stderr)
            failed = True
    if "sbdb" in sources:
        print("== JPL SBDB API ==")
        try:
            objs, notes = fetch_sbdb(args.offline, only_objs)
            for k, v in objs.items():
                fetched.setdefault(k, {}).update(v)
            src_notes += notes
        except Exception as e:
            print(f"[error] SBDB 源失败：{e}", file=sys.stderr)
            failed = True

    if not fetched:
        print("[error] 没有拉到任何数据", file=sys.stderr)
        return 2

    if args.verbose:
        for oid in sorted(fetched):
            print(f"\n-- {oid} --")
            for k, (v, note, _p, where, flag, _c) in sorted(fetched[oid].items()):
                print(f"   {k:24s} = {v!r:24s} flag={flag} note={note} [{where}]")

    rows = compare(astro, fetched, args.tolerance)
    REPORT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"astro_fetch_{ts}.md"
    n_sig = write_report(rows, astro, fetched, src_notes, args.tolerance, path)
    latest = REPORT_DIR / "astro_fetch_latest.md"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    n_match = sum(1 for r in rows if r["verdict"] == "一致")
    print(f"\n报告：{path.relative_to(ROOT)}")
    print(f"字段对比 {len(rows)} 项：一致 {n_match}，"
          f"微小 {sum(1 for r in rows if r['verdict'] == '微小差异')}，"
          f"显著 {n_sig}，新增 {sum(1 for r in rows if r['verdict'] == '新增')}")
    if failed:
        return 2
    return 1 if n_sig else 0


if __name__ == "__main__":
    sys.exit(main())
