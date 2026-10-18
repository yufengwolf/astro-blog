#!/usr/bin/env python3
"""test_fetch_astro.py — fetch_astro_data.py 解析器回归测试。

锁住 NSSDC/SBDB 各种脏值形态的解析行为，防止后续改动回归。
运行：python scripts/test_fetch_astro.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_astro_data import (  # noqa: E402
    FIELDS, SPECS, Spec, apply_label, convert, extract_planet_page,
    parse_kv_line, parse_pres, parse_value, triaxial_mean,
)


class TestParseValue(unittest.TestCase):
    def check(self, raw, value, flag=None):
        v = parse_value(raw)
        self.assertAlmostEqual(v.value, value, delta=max(abs(value), 1.0) * 1e-12, msg=raw)
        self.assertEqual(v.flag, flag, raw)

    def test_plain(self):
        self.check("0.3844", 0.3844)
        self.check("6371.000", 6371.0)
        self.check("-0.08", -0.08)
        self.check("+11.8", 11.8)

    def test_thousands_and_trailing_dot(self):
        self.check("1,988,400.", 1988400.0)   # NSSDC 千分位 + 尾点
        self.check("695,700.", 695700.0)
        self.check("143,128", 143128.0)

    def test_leading_dot(self):
        self.check(".07969229514816586", 0.07969229514816586)  # SBDB 前导点
        self.check(".21430445064843", 0.21430445064843)

    def test_scientific_with_units_and_parens(self):
        self.check("3 x 10^-15 bar (2 x 10^-12 torr)", 3e-15)   # 月面气压
        self.check("1.571 x 10^7 K", 1.571e7)                   # 太阳核心温度
        self.check("5.1 x 10^18 kg", 5.1e18)
        self.check("0.379 x 10^20", 3.79e19)

    def test_approx_and_upper(self):
        self.check("~13 microbar", 13.0, "approx")
        self.check("~25,000 kg", 25000.0, "approx")
        self.check("<0.0002", 0.0002, "upper")

    def test_range_and_hemisphere(self):
        v = parse_value("18.28 - 28.58")
        self.assertAlmostEqual(v.value, 23.43)
        self.assertEqual(v.flag, "range")
        v = parse_value("0.05 / 0.5")          # 土卫八两半球反照率
        self.assertAlmostEqual(v.value, 0.275)
        self.assertEqual(v.flag, "hemisphere")

    def test_special_and_missing(self):
        self.assertEqual(parse_value("S").flag, "sync")         # 同步自转标记
        self.assertEqual(parse_value("-").flag, "missing")
        self.assertEqual(parse_value("—").flag, "missing")
        self.assertEqual(parse_value("").flag, "missing")

    def test_leading_number_with_annotation(self):
        self.check("737 K (464 C)", 737.0)      # 金星平均温度
        self.check("1014 mb", 1014.0)
        self.check("~30,000 K", 30000.0, "approx")


class TestConvert(unittest.TestCase):
    def conv(self, raw, key, label):
        spec = next(s for s in SPECS if s.key == key and s.conv != "raw") \
            if False else None  # 占位，下面直接构造
        return None

    def test_temp_average_with_celsius_paren(self):
        spec = Spec("mean_temp_c", r"average temperature", "tempC")
        v, _ = convert(spec, parse_value("288 K (15 C)"), "Average temperature")
        self.assertEqual(v, 15.0)               # 优先用页内摄氏值
        v, _ = convert(spec, parse_value("~214 K (-59 C)"), "Average temperature")
        self.assertEqual(v, -59.0)

    def test_temp_blackbody_kelvin(self):
        spec = Spec("mean_temp_c_bb", r"black-?body temperature", "tempK")
        v, _ = convert(spec, parse_value("270.4"), "Black-body temperature (K)")
        self.assertAlmostEqual(v, -2.75)

    def test_temp_surface_range(self):
        spec = Spec("mean_temp_c_surface", r"^surface temperature", "tempRange")
        v, note = convert(spec, parse_value("24 - 38 K (-247 - -233 C)"),
                          "Surface temperature")
        self.assertAlmostEqual(v, -242.15)
        self.assertIn("区间", note)

    def test_pressure_units(self):
        spec = Spec("surface_pressure_bar", r"surface pressure", "pressure")
        v, _ = convert(spec, parse_value("1014 mb"), "Surface pressure")
        self.assertAlmostEqual(v, 1.014)
        v, _ = convert(spec, parse_value("~13 microbar"), "Surface Pressure")
        self.assertAlmostEqual(v, 1.3e-5)
        v, _ = convert(spec, parse_value("3 x 10^-15 bar (2 x 10^-12 torr)"),
                       "Surface pressure (night)")
        self.assertAlmostEqual(v, 3e-15)

    def test_mass_and_density_units(self):
        spec = Spec("mass_kg", r"^mass\b", "mass")
        v, _ = convert(spec, parse_value("0.07346"), "Mass (10^24 kg)")
        self.assertAlmostEqual(v, 7.346e22, delta=7.346e22 * 1e-12)
        spec = Spec("density_g_cm3", r"mean density", "dens")
        v, _ = convert(spec, parse_value("3344"), "Mean density (kg/m^3)")
        self.assertAlmostEqual(v, 3.344)

    def test_axis_units(self):
        spec = Spec("semimajor_axis_km", r"semi-?major axis", "axis")
        v, _ = convert(spec, parse_value("149.598"), "Semimajor axis (10^6 km)")
        self.assertAlmostEqual(v, 149598000.0)
        v, _ = convert(spec, parse_value("227.956"), "Semimajor axis (10^6 km)")
        self.assertAlmostEqual(v, 227956000.0)
        # 以行星半径为单位的列必须跳过
        v, why = convert(spec, parse_value("5.91"), "Semi-major axis (Jovian Radii)")
        self.assertIsNone(v)

    def test_rotation_days_to_hours(self):
        spec = Spec("rotation_period_hours", r"rotation\s*period", "rot")
        v, _ = convert(spec, parse_value("0.31891"), "Sidereal rotation period (days)")
        self.assertAlmostEqual(v, 7.65384)

    def test_yesno(self):
        spec = Spec("rings", r"planetary ring system", "yesno")
        v, _ = convert(spec, parse_value("Yes"), "Planetary ring system")
        self.assertEqual(v, 1.0)
        v, _ = convert(spec, parse_value("No"), "Planetary ring system")
        self.assertEqual(v, 0.0)


class TestApplyLabel(unittest.TestCase):
    def test_label_routing(self):
        store = {}
        apply_label(store, "Mass (10^24 kg)", "5.9722", "Bulk parameters")
        self.assertAlmostEqual(store["mass_kg"][0], 5.9722e24)
        apply_label(store, "Volumetric mean radius (km)", "6371.000", "Bulk parameters")
        self.assertAlmostEqual(store["radius_km"][0], 6371.0)
        apply_label(store, "Escape velocity (km/s)", "11.186", "Bulk parameters")
        self.assertAlmostEqual(store["escape_velocity_km_s"][0], 11.186)
        # "Total mass of atmosphere" 不得误入 mass_kg
        apply_label(store, "Total mass of atmosphere", "5.1 x 10^18 kg", "Atmosphere")
        self.assertAlmostEqual(store["mass_kg"][0], 5.9722e24)
        # "Inclination of/to ... equator" 不是黄道倾角，不得进 inclination_deg
        apply_label(store, "Inclination of equator (deg)", "23.44", "Orbital parameters")
        self.assertNotIn("inclination_deg", store)
        apply_label(store, "Inclination to Earth equator (deg)", "18.28 - 28.58", "Orbital parameters")
        self.assertNotIn("inclination_deg", store)
        # 倾角优先级：ecliptic 优先于普通 orbit inclination
        apply_label(store, "Orbit inclination (deg)", "0.000", "Orbital parameters")
        self.assertAlmostEqual(store["inclination_deg"][0], 0.0)
        apply_label(store, "Inclination to ecliptic (deg)", "5.145", "Orbital parameters")
        self.assertAlmostEqual(store["inclination_deg"][0], 5.145)
        # obliquity 独立捕获
        apply_label(store, "Obliquity to orbit (deg)", "23.44", "Orbital parameters")
        self.assertAlmostEqual(store["obliquity_deg"][0], 23.44)

    def test_kv_line_forms(self):
        self.assertEqual(parse_kv_line("Mass (10^24 kg)     5.9722"),
                         ("Mass (10^24 kg)", "5.9722"))
        self.assertEqual(parse_kv_line("Average temperature: 288 K (15 C)"),
                         ("Average temperature", "288 K (15 C)"))

    def test_triaxial_mean(self):
        v = triaxial_mean("208 x 197 x 191")
        self.assertAlmostEqual(v.value, 198.666666, places=4)
        self.assertEqual(v.flag, "range")
        v = triaxial_mean("1821.5")
        self.assertEqual(v.value, 1821.5)
        self.assertIsNone(v.flag)


class TestNSSDCPreParsing(unittest.TestCase):
    """NSSDC <pre> 行的空白处理——2026-10-18 修复的整节丢弃 bug 回归锁。

    历史教训：parse_pres 曾把行内连续空白压缩成单空格，而 parse_kv_line
    依赖 \\s{2,} 切分标签与值，导致 earthfact（唯一纯 pre 格式行星页）的
    Bulk parameters 23 行 + Orbital parameters 14 行整节丢弃——earth 的
    质量/半径/反照率等字段从未参与任何一轮源核对。
    """

    def test_multispace_alignment_preserved(self):
        # parse_pres 不得压缩行内空白（NSSDC 靠多空格对齐）
        html = "<pre>Mass (10^24 kg)    5.9722\nGeometric albedo 0.434</pre>"
        blocks = parse_pres(html)
        self.assertEqual(len(blocks), 1)
        self.assertIn("Mass (10^24 kg)    5.9722", blocks[0])
        self.assertEqual(parse_kv_line(blocks[0][0]), ("Mass (10^24 kg)", "5.9722"))

    def test_kv_line_real_nssdc_rows(self):
        # earthfact Bulk parameters 真实行
        self.assertEqual(parse_kv_line("Volumetric mean radius (km) 6371.000"),
                         ("Volumetric mean radius (km)", "6371.000"))
        self.assertEqual(parse_kv_line("Bond albedo                 0.294"),
                         ("Bond albedo", "0.294"))
        self.assertEqual(parse_kv_line("Number of natural satellites 1"),
                         ("Number of natural satellites", "1"))
        self.assertEqual(parse_kv_line("Planetary ring system        No"),
                         ("Planetary ring system", "No"))

    def test_kv_line_tail_fallback(self):
        # 单空格分隔的兜底形态：尾部 token 是数值或 Yes/No 才切
        self.assertEqual(parse_kv_line("Escape velocity (km/s) 11.186"),
                         ("Escape velocity (km/s)", "11.186"))
        self.assertEqual(parse_kv_line("GM (x 10^6 km^3/s^2) 0.39860"),
                         ("GM (x 10^6 km^3/s^2)", "0.39860"))

    def test_prose_lines_not_parsed(self):
        # 注释/脚注/说明文本不得误切出 kv（尾部无数值）
        for line in ("Model GSFC-1283",
                     "Numbers do not add up to exactly 100% due to roundoff",
                     "Atmospheric composition (by volume, dry air):",
                     "* These represent mean apogee and perigee for the lunar orbit,"):
            self.assertIsNone(parse_kv_line(line), line)

    def test_earthfact_bulk_extracted_end_to_end(self):
        # 端到端：缓存里的 earthfact Bulk 节必须抽出反照率双口径
        cache = Path(__file__).resolve().parent / ".cache" / "fetch" / "nssdc" / "earthfact.html"
        if not cache.exists():
            self.skipTest("无 NSSDC 缓存（先跑一次联网抓取）")
        html = cache.read_text(encoding="utf-8", errors="replace")
        store = extract_planet_page(html, "earth")
        self.assertIn("albedo_bond", store, "earthfact Bond albedo 未抽出（空白 bug 复发？）")
        self.assertIn("albedo_geometric", store)
        self.assertAlmostEqual(store["albedo_bond"][0], 0.294)
        self.assertAlmostEqual(store["albedo_geometric"][0], 0.434)
        self.assertIn("mass_kg", store)
        self.assertAlmostEqual(store["mass_kg"][0], 5.9722e24)


class TestSchemaConsistency(unittest.TestCase):
    """FIELDS/SPECS 字段名与 astro.json 实际字段对齐（防漂移）。

    历史教训：SPECS 曾用 mean_temp_c_surf 而库与渲染用 mean_temp_c_surface，
    导致合入的表面温度下次核查被当"新增"重复报——字段名一处改处处改。
    """

    def test_fields_exist_in_astro_json(self):
        import json
        root = Path(__file__).resolve().parent.parent
        d = json.loads((root / "docs" / "data" / "astro.json").read_text(encoding="utf-8"))
        keys = set()
        for o in d["objects"]:
            for grp in ("physical", "orbit"):
                keys |= set((o.get(grp) or {}).keys())
            keys |= set((o.get("moons") or {}).keys())  # moons.count / notable
            if "rings" in o:
                keys.add("rings")  # 顶层布尔字段
        for path, _label, _kind in FIELDS:
            key = path.split(".")[-1]
            self.assertIn(key, keys, f"FIELDS 的 {path} 不在 astro.json 任何对象中（字段漂移）")

    def test_specs_keys_covered_by_fields(self):
        spec_keys = {s.key for s in SPECS if not s.key.startswith("_")}
        field_keys = {p.split(".")[-1] for p, _l, _k in FIELDS}
        # moons_count 在库中是 moons.count；gm_km3_s2 是换算中间量不入库
        whitelist = {"moons_count", "gm_km3_s2"}
        missing = (spec_keys - field_keys) - whitelist
        self.assertEqual(missing, set(), f"SPECS 有字段未被 FIELDS 覆盖：{missing}")


class TestApplyPropose(unittest.TestCase):
    """--apply 合库入口：查重 / 结构校验 / 落盘 / meta 同步。

    这是全链路唯一写库的路径，测试用临时目录 + monkeypatch 模块常量，
    不碰真实 astro.json。
    """

    def setUp(self):
        import json
        import tempfile
        import fetch_astro_data as fad
        self.fad = fad
        self.tmp = Path(tempfile.mkdtemp(prefix="apply_test_"))
        self.json_p = self.tmp / "astro.json"
        self.rep_dir = self.tmp / "reports"
        self.rep_dir.mkdir()
        self.json_p.write_text(json.dumps(
            {"objects": [{"id": "pluto", "name": "冥王星"}], "meta": {}},
            ensure_ascii=False), encoding="utf-8")
        self._orig_json, self._orig_rep = fad.ASTRO_JSON, fad.REPORT_DIR
        fad.ASTRO_JSON, fad.REPORT_DIR = self.json_p, self.rep_dir

    def tearDown(self):
        self.fad.ASTRO_JSON, self.fad.REPORT_DIR = self._orig_json, self._orig_rep
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _skeleton(self, oid="quaoar", **over):
        import json
        obj = {
            "id": oid, "name": "创神星", "name_en": "Quaoar",
            "category": "dwarf_planet", "parent": "sun", "tagline": None,
            "physical": {"mass_kg": 1.4e21}, "orbit": {"eccentricity": 0.04},
            "moons": {"count": 1, "notable": []}, "rings": None,
            "magnetic_field": None, "atmosphere": None,
            "discovery": {"known_since": None, "discoverer": None, "year": 2002},
            "sources": ["jpl_sbdb"], "source_dates": {},
            "verified": "2026-10-19", "image": None,
        }
        obj.update(over)
        (self.rep_dir / f"propose_{oid}.json").write_text(
            json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return obj

    def test_apply_inserts_and_syncs_meta(self):
        self._skeleton()
        astro = {"pluto": {"id": "pluto"}}
        rc = self.fad.apply_propose(astro, ["quaoar"])
        self.assertEqual(rc, 0)
        import json
        d = json.loads(self.json_p.read_text(encoding="utf-8"))
        self.assertEqual([o["id"] for o in d["objects"]], ["pluto", "quaoar"])
        self.assertEqual(d["meta"]["object_count"], 2)
        self.assertTrue(d["meta"]["updated"])

    def test_apply_skips_known(self):
        self._skeleton()
        astro = {"quaoar": {"id": "quaoar"}}
        rc = self.fad.apply_propose(astro, ["quaoar"])
        self.assertEqual(rc, 0)
        import json
        d = json.loads(self.json_p.read_text(encoding="utf-8"))
        self.assertEqual(len(d["objects"]), 1)  # 未重复插入

    def test_apply_rejects_bad_skeleton(self):
        import json
        (self.rep_dir / "propose_bad.json").write_text(json.dumps(
            {"id": "bad", "name": "", "category": "banana"}), encoding="utf-8")
        rc = self.fad.apply_propose({"pluto": {}}, ["bad"])
        self.assertEqual(rc, 2)
        d = json.loads(self.json_p.read_text(encoding="utf-8"))
        self.assertEqual(len(d["objects"]), 1)  # 拒绝合入

    def test_apply_missing_skeleton(self):
        rc = self.fad.apply_propose({"pluto": {}}, ["nope"])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
