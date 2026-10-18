---
description: "冥王星（Pluto）的天体数据：1.3×10²² kg、半径 1,188 km、密度 1.85 g/cm³、表面温度 -225 °C。数据整理自 NASA 公开资料。"
---

<div class="obj-hero">
  <div class="astro-img dwarf_planet"><img src="../assets/planets/pluto.webp" alt="冥王星" loading="lazy"></div>
  <div class="obj-hero-info">
    <span class="astro-badge dwarf_planet">矮行星</span>
    <h1>冥王星 <small>Pluto</small></h1>
    <p class="obj-tagline">曾被列为第九大行星，与卫星卡戎构成双天体系统</p>
    <div class="obj-keystats">
      <span>1.3×10²² kg</span>
      <span>1,188 km</span>
      <span>-225 °C</span>
      <span>1.85 g/cm³</span>
    </div>
  </div>
</div>

<p class="obj-parent">母天体：<a href="../sun/">太阳</a> · 分类：矮行星</p>

<div class="obj-compare-bar">
  <button type="button" id="astro-compare-toggle" class="cmp-btn" aria-expanded="false" aria-controls="astro-compare">⚖ 与其他天体对比</button>
  <span class="cmp-hint">从数据库中任选天体（可多选）逐参数对比，链接可分享</span>
</div>
<section class="obj-compare" id="astro-compare" hidden data-current="pluto">
  <div class="cmp-picker">
    <input type="search" id="cmp-search" placeholder="搜索要对比的天体（中/英文）…" aria-label="搜索对比天体">
    <ul class="cmp-results" id="cmp-results" hidden></ul>
  </div>
  <div class="cmp-table-wrap"><table class="cmp-table" id="cmp-table"></table></div>
  <p class="cmp-note">对比在该页本地完成；点击列标题旁的 × 可移除该天体。</p>
</section>
<script type="application/json" id="astro-compare-data">{"earth_id": "earth", "rows": [{"id": "sun", "name": "太阳", "en": "Sun", "cat": "恒星", "cat_key": "star", "parent": null, "mass": 1.9884e+30, "radius": 695700, "density": 1.408, "gravity": 274.0, "escape": 617.6, "temp": 5499, "pressure": 0.000868, "rotation": 609.12, "axis": null, "period": null, "velocity": null, "moons": null}, {"id": "mercury", "name": "水星", "en": "Mercury", "cat": "行星", "cat_key": "planet", "parent": "sun", "mass": 3.301e+23, "radius": 2439.7, "density": 5.429, "gravity": 3.7, "escape": 4.3, "temp": 167, "pressure": null, "rotation": 1407.6, "axis": 57910000, "period": 87.97, "velocity": 47.4, "moons": 0}, {"id": "venus", "name": "金星", "en": "Venus", "cat": "行星", "cat_key": "planet", "parent": "sun", "mass": 4.8685e+24, "radius": 6051.8, "density": 5.243, "gravity": 8.87, "escape": 10.36, "temp": 464, "pressure": 92, "rotation": -5832.5, "axis": 108210000, "period": 224.7, "velocity": 35.02, "moons": 0}, {"id": "earth", "name": "地球", "en": "Earth", "cat": "行星", "cat_key": "planet", "parent": "sun", "mass": 5.9724e+24, "radius": 6371.0, "density": 5.514, "gravity": 9.82, "escape": 11.19, "temp": 15, "pressure": 1, "rotation": 23.9345, "axis": 149600000, "period": 365.26, "velocity": 29.78, "moons": 1}, {"id": "mars", "name": "火星", "en": "Mars", "cat": "行星", "cat_key": "planet", "parent": "sun", "mass": 6.4169e+23, "radius": 3389.5, "density": 3.934, "gravity": 3.73, "escape": 5.03, "temp": -65, "pressure": 0.00636, "rotation": 24.6229, "axis": 227956000, "period": 686.98, "velocity": 24.08, "moons": 2}, {"id": "jupiter", "name": "木星", "en": "Jupiter", "cat": "行星", "cat_key": "planet", "parent": "sun", "mass": 1.89813e+27, "radius": 69911, "density": 1.326, "gravity": 25.92, "escape": 59.5, "temp": -110, "pressure": null, "rotation": 9.925, "axis": 778479000, "period": 4332.59, "velocity": 13.06, "moons": 95}, {"id": "saturn", "name": "土星", "en": "Saturn", "cat": "行星", "cat_key": "planet", "parent": "sun", "mass": 5.6832e+26, "radius": 58232, "density": 0.687, "gravity": 11.19, "escape": 35.5, "temp": -140, "pressure": null, "rotation": 10.656, "axis": 1432041000, "period": 10755.7, "velocity": 9.67, "moons": 274}, {"id": "uranus", "name": "天王星", "en": "Uranus", "cat": "行星", "cat_key": "planet", "parent": "sun", "mass": 8.6813e+25, "radius": 25559, "density": 1.27, "gravity": 8.87, "escape": 21.3, "temp": -195, "pressure": null, "rotation": -17.24, "axis": 2867000000, "period": 30589, "velocity": 6.8, "moons": 28}, {"id": "neptune", "name": "海王星", "en": "Neptune", "cat": "行星", "cat_key": "planet", "parent": "sun", "mass": 1.0241e+26, "radius": 24764, "density": 1.638, "gravity": 11.15, "escape": 23.5, "temp": -200, "pressure": null, "rotation": 16.11, "axis": 4515000000, "period": 59800, "velocity": 5.43, "moons": 16}, {"id": "pluto", "name": "冥王星", "en": "Pluto", "cat": "矮行星", "cat_key": "dwarf_planet", "parent": "sun", "mass": 1.303e+22, "radius": 1188.3, "density": 1.85, "gravity": 0.62, "escape": 1.21, "temp": -225, "pressure": 1e-05, "rotation": -153.29, "axis": 5906376272, "period": 90560, "velocity": 4.67, "moons": 5}, {"id": "ceres", "name": "谷神星", "en": "Ceres", "cat": "矮行星", "cat_key": "dwarf_planet", "parent": "sun", "mass": 9.3846e+20, "radius": 469.7, "density": 2.162, "gravity": 0.28, "escape": 0.51, "temp": null, "pressure": null, "rotation": 9.074, "axis": 413700000, "period": 1682.0, "velocity": 17.9, "moons": 0}, {"id": "moon", "name": "月球", "en": "Moon", "cat": "卫星", "cat_key": "moon", "parent": "earth", "mass": 7.346e+22, "radius": 1737.4, "density": 3.344, "gravity": 1.62, "escape": 2.38, "temp": -20, "pressure": null, "rotation": 655.72, "axis": 384400, "period": 27.3217, "velocity": 1.022, "moons": 0}, {"id": "phobos", "name": "火卫一", "en": "Phobos", "cat": "卫星", "cat_key": "moon", "parent": "mars", "mass": 1.06e+16, "radius": 11.27, "density": 1.9, "gravity": null, "escape": 0.0114, "temp": null, "pressure": null, "rotation": 7.654, "axis": 9378, "period": 0.31891, "velocity": 2.14, "moons": 0}, {"id": "deimos", "name": "火卫二", "en": "Deimos", "cat": "卫星", "cat_key": "moon", "parent": "mars", "mass": 2400000000000000.0, "radius": 6.3, "density": 1.75, "gravity": null, "escape": null, "temp": null, "pressure": null, "rotation": 30.299, "axis": 23459, "period": 1.26244, "velocity": 1.35, "moons": 0}, {"id": "io", "name": "木卫一", "en": "Io", "cat": "卫星", "cat_key": "moon", "parent": "jupiter", "mass": 8.932e+22, "radius": 1821.5, "density": 3.53, "gravity": 1.796, "escape": 2.56, "temp": null, "pressure": null, "rotation": 42.459, "axis": 421800, "period": 1.769138, "velocity": 17.34, "moons": 0}, {"id": "europa", "name": "木卫二", "en": "Europa", "cat": "卫星", "cat_key": "moon", "parent": "jupiter", "mass": 4.8e+22, "radius": 1560.8, "density": 3.01, "gravity": 1.314, "escape": 2.02, "temp": null, "pressure": null, "rotation": 85.228, "axis": 671100, "period": 3.551181, "velocity": 13.74, "moons": 0}, {"id": "ganymede", "name": "木卫三", "en": "Ganymede", "cat": "卫星", "cat_key": "moon", "parent": "jupiter", "mass": 1.4819e+23, "radius": 2631.2, "density": 1.94, "gravity": 1.428, "escape": 2.74, "temp": null, "pressure": null, "rotation": 171.709, "axis": 1070400, "period": 7.154553, "velocity": 10.88, "moons": 0}, {"id": "callisto", "name": "木卫四", "en": "Callisto", "cat": "卫星", "cat_key": "moon", "parent": "jupiter", "mass": 1.0759e+23, "radius": 2410.3, "density": 1.83, "gravity": 1.235, "escape": 2.44, "temp": null, "pressure": null, "rotation": 400.536, "axis": 1882700, "period": 16.689017, "velocity": 8.2, "moons": 0}, {"id": "mimas", "name": "土卫一", "en": "Mimas", "cat": "卫星", "cat_key": "moon", "parent": "saturn", "mass": 3.79e+19, "radius": 198.7, "density": 1.15, "gravity": 0.064, "escape": 0.159, "temp": null, "pressure": null, "rotation": 22.618, "axis": 185520, "period": 0.9424218, "velocity": 14.28, "moons": 0}, {"id": "enceladus", "name": "土卫二", "en": "Enceladus", "cat": "卫星", "cat_key": "moon", "parent": "saturn", "mass": 1.08e+20, "radius": 252.1, "density": 1.61, "gravity": 0.113, "escape": 0.239, "temp": null, "pressure": null, "rotation": 32.885, "axis": 238020, "period": 1.370218, "velocity": 12.62, "moons": 0}, {"id": "tethys", "name": "土卫三", "en": "Tethys", "cat": "卫星", "cat_key": "moon", "parent": "saturn", "mass": 6.18e+20, "radius": 530.7, "density": 0.985, "gravity": 0.146, "escape": 0.394, "temp": null, "pressure": null, "rotation": 45.307, "axis": 294660, "period": 1.887802, "velocity": 11.35, "moons": 0}, {"id": "dione", "name": "土卫四", "en": "Dione", "cat": "卫星", "cat_key": "moon", "parent": "saturn", "mass": 1.1e+21, "radius": 561.4, "density": 1.478, "gravity": 0.232, "escape": 0.51, "temp": null, "pressure": null, "rotation": 65.686, "axis": 377400, "period": 2.736915, "velocity": 10.03, "moons": 0}, {"id": "rhea", "name": "土卫五", "en": "Rhea", "cat": "卫星", "cat_key": "moon", "parent": "saturn", "mass": 2.31e+21, "radius": 763.8, "density": 1.236, "gravity": 0.264, "escape": 0.635, "temp": null, "pressure": null, "rotation": 108.42, "axis": 527040, "period": 4.5175, "velocity": 8.48, "moons": 0}, {"id": "titan", "name": "土卫六", "en": "Titan", "cat": "卫星", "cat_key": "moon", "parent": "saturn", "mass": 1.3455e+23, "radius": 2575.5, "density": 1.881, "gravity": 1.352, "escape": 2.64, "temp": -179, "pressure": 1.47, "rotation": 382.69, "axis": 1221870, "period": 15.945421, "velocity": 5.58, "moons": 0}, {"id": "hyperion", "name": "土卫七", "en": "Hyperion", "cat": "卫星", "cat_key": "moon", "parent": "saturn", "mass": 5.6e+18, "radius": 138.7, "density": 0.55, "gravity": null, "escape": null, "temp": null, "pressure": null, "rotation": null, "axis": 1500930, "period": 21.276609, "velocity": 5.05, "moons": 0}, {"id": "iapetus", "name": "土卫八", "en": "Iapetus", "cat": "卫星", "cat_key": "moon", "parent": "saturn", "mass": 1.81e+21, "radius": 734.5, "density": 1.088, "gravity": 0.223, "escape": 0.573, "temp": null, "pressure": null, "rotation": 1903.92, "axis": 3560850, "period": 79.330183, "velocity": 3.26, "moons": 0}, {"id": "triton", "name": "海卫一", "en": "Triton", "cat": "卫星", "cat_key": "moon", "parent": "neptune", "mass": 2.14e+22, "radius": 1353.4, "density": 2.05, "gravity": 0.78, "escape": 1.45, "temp": -235, "pressure": 1.4e-05, "rotation": 141.04, "axis": 354759, "period": 5.876854, "velocity": 4.39, "moons": 0}, {"id": "miranda", "name": "天卫五", "en": "Miranda", "cat": "卫星", "cat_key": "moon", "parent": "uranus", "mass": 6.6e+19, "radius": 235.8, "density": 1.2, "gravity": 0.079, "escape": 0.193, "temp": null, "pressure": null, "rotation": 33.923, "axis": 129900, "period": 1.413479, "velocity": 6.66, "moons": 0}, {"id": "ariel", "name": "天卫一", "en": "Ariel", "cat": "卫星", "cat_key": "moon", "parent": "uranus", "mass": 1.29e+21, "radius": 578.9, "density": 1.59, "gravity": 0.269, "escape": 0.559, "temp": null, "pressure": null, "rotation": 60.489, "axis": 190900, "period": 2.520379, "velocity": 5.51, "moons": 0}, {"id": "umbriel", "name": "天卫二", "en": "Umbriel", "cat": "卫星", "cat_key": "moon", "parent": "uranus", "mass": 1.22e+21, "radius": 584.7, "density": 1.46, "gravity": 0.238, "escape": 0.52, "temp": null, "pressure": null, "rotation": 99.46, "axis": 266000, "period": 4.144176, "velocity": 4.67, "moons": 0}, {"id": "titania", "name": "天卫三", "en": "Titania", "cat": "卫星", "cat_key": "moon", "parent": "uranus", "mass": 3.42e+21, "radius": 788.9, "density": 1.66, "gravity": 0.379, "escape": 0.773, "temp": null, "pressure": null, "rotation": 208.94, "axis": 436300, "period": 8.705867, "velocity": 3.64, "moons": 0}, {"id": "oberon", "name": "天卫四", "en": "Oberon", "cat": "卫星", "cat_key": "moon", "parent": "uranus", "mass": 2.88e+21, "radius": 761.4, "density": 1.56, "gravity": 0.346, "escape": 0.726, "temp": null, "pressure": null, "rotation": 323.12, "axis": 583500, "period": 13.463234, "velocity": 3.15, "moons": 0}]}</script>

## 物理参数

| 参数 | 数值 |
|---|---|
| 质量 | 1.3×10²² kg |
| 平均半径 | 1,188 km |
| 平均密度 | 1.85 g/cm³ |
| 表面重力 | 0.62 m/s² |
| 逃逸速度 | 1.21 km/s |
| 平均表面温度 | -225 °C |
| 表面气压 | 1×10⁻⁵ bar |
| 反照率 | — |

## 轨道参数

| 参数 | 数值 |
|---|---|
| 半长轴 | 5,906,376,272 km（39.5 AU） |
| 轨道周期 | 247.9 年（90,560 天） |
| 平均轨道速度 | 4.67 km/s |
| 轨道倾角 | 17.16° |
| 轨道偏心率 | 0.244 |
| 转轴倾角 | 119.5° |
| 自转周期 | 逆行自转 · 6.39 天 |

## 其他特征

| 项目 | 数值 |
|---|---|
| 大气成分 | — |
| 全球磁场 | 未知 |
| 环系 | 否 |
| 已确认卫星 | 5 颗（ notable：卡戎） |
| 发现 | 克莱德·汤博，1930 年 |

<section class="obj-source">
  <h2>数据来源</h2>
  <p>来源标识：nssdc_planetary_factsheet；核对日期：2026-10-18。数值整理自 NASA NSSDC / JPL 公开资料（公共领域）。发现错误请到 <a href="https://github.com/yufengwolf/astro-blog/issues">GitHub Issues</a> 反馈。</p>
</section>

<section class="obj-articles">
  <h2>相关文章</h2>
  <ul class="astro-article-list">
    <li><a href="#article-pluto">冥王星比月球还小，当年凭什么是第九大行星？</a></li>
  </ul>
</section>

<section class="obj-article" id="article-pluto">
  <h2>延伸阅读：冥王星比月球还小，当年凭什么是第九大行星？</h2>

冥王星直径仅约2370公里，比月球更小，体积只有地球的约1/150，质量仅地球的0.0022倍。它能维持76年“第九大行星”身份，不是因为个头大，而是当年人类对柯伊伯带一无所知。2006年国际天文联合会投票，把它重新归类为矮行星。

![冥王星、月球、地球球体大小并排对比，黑色太空背景，标注各自直径，写实科学示意图](../assets/pluto-1.jpg)
## 尺度反差：曾经的第九行星，个头还不如月球
冥王星直径大约2370公里，月球直径约3474公里，冥王星直径大约只有月球的三分之二，不到地球的五分之一。如果把地球比作一个篮球，月球大约是网球，冥王星只有高尔夫球大小。

它的质量差距更夸张，只有月球质量的六分之一。如此微弱的引力，不足以清空轨道周边的碎片，这也是它被降级的核心原因。

冥王星的一年等于248个地球年。它的自转周期约6.4个地球日，自转很慢，一天漫长而冰冷。

## 极端偏心轨道：在柯伊伯带来回穿梭
冥王星位于海王星外侧的柯伊伯带，这片区域是太阳系外缘大量冰质小天体的聚集地。它的轨道偏心率极大，不是接近正圆，而是明显拉长的椭圆。

远日点时距离太阳约49.3天文单位，近日点约30.1天文单位，**近日点甚至比海王星轨道还要靠近太阳**。它和海王星存在轨道共振，不会相撞，却共享这片区域，轨道附近遍布大量柯伊伯带天体。

这就是关键矛盾：行星的判定标准要求天体**清空轨道附近区域**，冥王星做不到。柯伊伯带还有阋神星、鸟神星等同类冰质天体，阋神星质量甚至略大于冥王星。如果冥王星保留行星身份，柯伊伯带会多出一大堆行星，行星定义就失去意义。

## 汤博区：冥王星独一无二的心形冰原
2015年新视野号飞掠冥王星，传回人类第一组高清影像，最震撼的发现就是心形平原汤博区。这片巨大的浅色区域，以冥王星发现者汤博命名。

汤博区主体是氮冰平原，表层覆盖流动的氮冰，下方存在固态甲烷冰、一氧化碳冰。氮冰可以缓慢流动，类似冰川，却没有高山挤压形成的褶皱。新视野号没有在这里发现大量撞击坑，说明这片区域地质年龄很年轻，可能不足1亿年。

![冥王星表面特写，突出心形汤博区，暗色区域与明亮冰原对比，深空科学实拍风格](../assets/pluto-2.jpg)
这片冰原颠覆了旧认知：很多人以为冥王星是死寂、布满古老陨石坑的冰球，但它仍存在活跃的地表重塑。内部放射性元素衰变产生热量，维持地表冰层缓慢运动。

## 冰壳与低温：很冷，但不是太阳系最冷天体
冥王星表面平均温度大约-232℃。这里遍布氮冰、甲烷冰，当靠近太阳时，表层氮冰会少量升华，形成一层极薄的大气；远离太阳时大气会重新凝结落回地表。

很多人默认离太阳越远就越冷，冥王星理应是太阳系最冷天体。事实并非如此。月球南北极永久阴影坑，温度可以低至-249℃，比冥王星表面更冷。这些深坑永远接收不到阳光，没有大气保温，热量持续散失。

冥王星虽远，但仍能接收到微弱的太阳辐射，稀薄大气还会产生一定保温效应，所以温度高于月球永久阴影坑。

## 2006除名争议：不是“开除”，是重新定义
2006年IAU确立三条行星判定标准：
1. 围绕太阳公转
2. 自身引力足以塑造成球形
3. 清空轨道周边的天体

冥王星满足前两条，但第三条无法达标。这次投票不是科学家单纯“嫌弃冥王星太小”，而是阋神星的发现，迫使天文学界统一行星定义。

争议一直延续至今。反对者认为，**清空轨道**这个标准带有主观色彩，投票参与人数有限，不该仅凭一次投票就改写冥王星的身份。不少行星科学家至今仍主张恢复冥王星的行星地位。支持者则认为，分类体系要统一，不能双重标准。

> 冥王星的身份争议，本质是人类对太阳系边界认知更新的产物，不是天体本身发生了变化。

## 常见误区
- 很多人以为冥王星被踢出太阳系。其实它依旧在太阳系，只是分类从行星改成矮行星，位置没有任何改变。
- 很多人以为冥王星完全没有大气。它存在稀薄大气，由氮气、甲烷、一氧化碳组成，只是大气会随轨道远近反复凝结、消散。
- 很多人以为汤博区是撞击坑。心形轮廓不是撞击形成，是氮冰沉积、地表物质迁移共同塑造的平原。
- 很多人以为冥王星和海王星会相撞。二者存在3:2轨道共振，轨道交叉，但永远不会相遇。

## 常见问题
**Q：冥王星最大的卫星叫什么？**
A：冥卫一卡戎，体积很大，二者质心落在冥王星外部，可看作一对双矮行星系统。

**Q：柯伊伯带还有哪些矮行星？**
A：阋神星、鸟神星、妊神星，加上谷神星，共同构成IAU认可的五颗矮行星。

**Q：新视野号之后还有探测器造访冥王星吗？**
A：目前没有新的冥王星探测任务，后续只有远距离观测。

**Q：冥王星表面的冰是水冰吗？**
A：表层主要是氮冰、甲烷冰；水冰埋藏在更深处，构成冥王星坚硬的岩石冰壳。

同轨道区域其他天体的总质量数倍于冥王星，它无力清除周边物质，这是它无法回到行星行列的硬性事实。

</section>

<p class="obj-nav">← 上一颗：<a href="../neptune/">海王星</a></p>
<p class="obj-nav">下一颗：<a href="../ceres/">谷神星</a> →</p>

<p class="obj-version">数据版本 v1.1（2026-10-18 核对）· 32 个天体已全部配图</p>
