---
description: "下载星野笔记的天体数据集：32 个太阳系天体的质量、半径、密度、温度、轨道与卫星数据，JSON 与 CSV 两种格式。"
---

# 天体数据集

本站收录的 32 个天体的结构化数据，提供 JSON 与 CSV 两种格式下载。最近更新：2026-10-18。

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
| semimajor_axis_km | 轨道半长轴 | km |
| orbital_period_days | 轨道周期 | 天 |
| moons.count | 已确认卫星数 | 颗 |
| sources / verified | 数据来源 / 核对日期 | — |

## 许可与来源

数值数据整理自 NASA 公开资料（公共领域）；一句话简介为本站原创撰写。

主要数据源：
- NASA NSSDC Planetary Fact Sheet（八大行星+冥王星，2025-03-18 更新）https://nssdc.gsfc.nasa.gov/planetary/factsheet/
- NASA NSSDC Sun Fact Sheet（2024-05-09 更新）https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html
- NASA NSSDC Moon Fact Sheet https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html
- NASA NSSDC Mars Fact Sheet（2025-05-19 更新，含火卫一/二参数）https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html
- NASA NSSDC Jovian/Saturnian/Neptunian/Uranian Satellite Fact Sheets https://nssdc.gsfc.nasa.gov/planetary/factsheet/joviansatfact.html
- NASA/JPL Small-Body Database API（谷神星）https://ssd-api.jpl.nasa.gov/sbdb.api

## 待补充

鸟神星、妊神星、阋神星（权威源暂无完整实测值，待文献核验后补充）；恒星与系外行星为下一批扩展方向
