---
description: "下载星野笔记的天体数据集：151 个天体的质量、半径、密度、温度、轨道与卫星数据，JSON 与 CSV 两种格式。"
---

# 天体数据集

本站收录的 151 个天体的结构化数据，提供 JSON 与 CSV 两种格式下载。最近更新：2026-10-24。

<div class="dl-cards">
  <a class="dl-card" href="../data/astro.json" download>
    <b>astro.json</b><span>完整数据（含来源与核对日期）</span>
  </a>
  <a class="dl-card" href="../data/astro_flat.csv" download>
    <b>astro_flat.csv</b><span>扁平表格（Excel 可直接打开）</span>
  </a>
</div>

## 字段说明

| 字段 | 含义 | 单位 |
|---|---|---|
| mass_kg | 质量 | kg |
| radius_km | 平均半径 | km |
| density_g_cm3 | 平均密度 | g/cm³ |
| mean_temp_c | 平均表面温度 | °C |
| mean_temp_c_bb | 有效温度（black-body 口径） | °C |
| mean_temp_c_surface | 表面温度 | °C |
| albedo / albedo_bond / albedo_geometric | 反照率（主值 / Bond 口径 / Geometric 口径） | — |
| surface_pressure_bar | 表面气压 | bar |
| inclination_deg / eccentricity | 轨道倾角 / 偏心率 | ° / — |
| semimajor_axis_km | 轨道半长轴 | km |
| orbital_period_days | 轨道周期 | 天 |
| moons.count | 已确认卫星数 | 颗 |
| sources / verified | 数据来源 / 核对日期 | — |

## 许可与来源

数值数据整理自 NASA NSSDC / JPL / Wikipedia 等公开天文资料（公共领域或自由许可）；一句话简介为本站原创撰写。

主要数据源：
- NASA NSSDC Planetary Fact Sheet（八大行星+冥王星，2025-03-18 更新）https://nssdc.gsfc.nasa.gov/planetary/factsheet/
- NASA NSSDC Sun Fact Sheet（2024-05-09 更新）https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html
- NASA NSSDC Moon Fact Sheet https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html
- NASA NSSDC Mars Fact Sheet（2025-05-19 更新，含火卫一/二参数）https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html
- NASA NSSDC Jovian/Saturnian/Neptunian/Uranian Satellite Fact Sheets https://nssdc.gsfc.nasa.gov/planetary/factsheet/joviansatfact.html
- NASA/JPL Small-Body Database API（谷神星）https://ssd-api.jpl.nasa.gov/sbdb.api
- Wikipedia 各天体条目（黑洞/星云/星系/星团/大尺度结构，2026-10-24 核对）https://en.wikipedia.org/
- Event Horizon Telescope（M87* / 人马座 A* 黑洞照片）https://eventhorizontelescope.org/
- LIGO/Virgo 合作组 · GW190521 探测论文（2020）https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.125.101102
- Wikipedia 各天体条目（著名星云/星系/星团/小天体，2026-10-24 核对）https://en.wikipedia.org/
- LIGO/Virgo 合作组 · GW150914 探测论文（2016）https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.116.061102
- Wikipedia 各恒星条目（亮星/超巨星/双星/残骸/系外宿主，2026-10-24 核对）https://en.wikipedia.org/
- 诺贝尔物理学奖 2019 新闻稿（飞马座 51b 的发现）https://www.nobelprize.org/prizes/physics/2019/press-release/

## 待补充

TNO 三兄弟（鸟神星/妊神星/阋神星）物理参数待权威源实测值（当前诚实留 null）；北冕座 R 因无可靠距离数据未收录；m7/ngc4755 等 NASA 库无真图的天体保留程序化贴图
