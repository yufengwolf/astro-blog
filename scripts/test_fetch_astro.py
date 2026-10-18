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
    FIELDS, SPECS, Spec, apply_label, convert, parse_kv_line, parse_value, triaxial_mean,
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
        spec = Spec("mean_temp_c_surf", r"^surface temperature", "tempRange")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
