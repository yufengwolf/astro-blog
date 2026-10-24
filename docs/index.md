---
description: "收录 35 个天体的结构化数据：质量、半径、密度、表面温度、轨道周期与卫星数量，支持按分类筛选、按任意数值排序。"
---

<div class="astro-hero">
  <h1>天体数据库</h1>
  <p class="astro-hero-sub">35 个天体的质量 · 半径 · 密度 · 温度 · 轨道 · 卫星数据，一键筛选，按数值排序</p>
  <p class="astro-hero-stats">
    <span class="astro-stat"><b>1</b> 恒星</span>
    <span class="astro-stat"><b>8</b> 行星</span>
    <span class="astro-stat"><b>5</b> 矮行星</span>
    <span class="astro-stat"><b>21</b> 卫星</span>
  </p>
  <p class="astro-hero-links"><a href="#articles">科普文章</a><span class="sep">·</span><a href="objects/">天体库总表</a></p>
</div>

<div class="astro-toolbar">
  <input type="search" id="astro-search" placeholder="搜索天体名称（中/英文）…" aria-label="搜索天体">
  <div class="astro-chips" role="group" aria-label="按分类筛选">
    <button type="button" class="chip active" data-filter="all">全部</button>
    <button type="button" class="chip" data-filter="star">恒星</button>
    <button type="button" class="chip" data-filter="planet">行星</button>
    <button type="button" class="chip" data-filter="dwarf_planet">矮行星</button>
    <button type="button" class="chip" data-filter="moon">卫星</button>
  </div>
  <label class="astro-sort-label">排序
    <select id="astro-sort" aria-label="排序方式">
      <option value="name">名称</option>
      <option value="mass">质量 ↓</option>
      <option value="radius">半径 ↓</option>
      <option value="density">密度 ↓</option>
      <option value="temp">表面温度 ↓</option>
      <option value="period">轨道周期 ↓</option>
      <option value="moons">卫星数量 ↓</option>
    </select>
  </label>
</div>
<p class="astro-count" id="astro-count"></p>

<div class="astro-grid">
  <article class="astro-card" data-category="star" data-name="太阳 Sun" data-mass="1.9884e+30" data-radius="695700" data-density="1.408" data-temp="5499" data-period="" data-moons="">
    <a class="astro-card-link" href="objects/sun/">
      <div class="astro-img star"><img src="assets/planets/sun.webp" alt="太阳" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">太阳<span class="en">Sun</span></div>
        <p class="astro-card-tagline">太阳系的中心恒星，独占太阳系总质量的 99.86%</p>
        <div class="astro-card-stats"><span>1.99×10³⁰ kg</span><span>695,700 km</span><span>5499 °C</span></div>
      </div>
      <span class="astro-badge star">恒星</span>
    </a>
  </article>
  <article class="astro-card" data-category="planet" data-name="水星 Mercury" data-mass="3.301e+23" data-radius="2439.7" data-density="5.429" data-temp="167" data-period="87.97" data-moons="0">
    <a class="astro-card-link" href="objects/mercury/">
      <div class="astro-img planet"><img src="assets/planets/mercury.webp" alt="水星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">水星<span class="en">Mercury</span></div>
        <p class="astro-card-tagline">离太阳最近的行星，一个太阳日比一个水星年还长</p>
        <div class="astro-card-stats"><span>3.3×10²³ kg</span><span>2,440 km</span><span>167 °C</span></div>
      </div>
      <span class="astro-badge planet">行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="planet" data-name="金星 Venus" data-mass="4.8685e+24" data-radius="6051.8" data-density="5.243" data-temp="464" data-period="224.7" data-moons="0">
    <a class="astro-card-link" href="objects/venus/">
      <div class="astro-img planet"><img src="assets/planets/venus.webp" alt="金星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">金星<span class="en">Venus</span></div>
        <p class="astro-card-tagline">被浓厚二氧化碳大气包裹的炽热世界，太阳系表面最热的行星</p>
        <div class="astro-card-stats"><span>4.87×10²⁴ kg</span><span>6,052 km</span><span>464 °C</span></div>
      </div>
      <span class="astro-badge planet">行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="planet" data-name="地球 Earth" data-mass="5.9724e+24" data-radius="6371.0" data-density="5.514" data-temp="15" data-period="365.26" data-moons="1">
    <a class="astro-card-link" href="objects/earth/">
      <div class="astro-img planet"><img src="assets/planets/earth.webp" alt="地球" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">地球<span class="en">Earth</span></div>
        <p class="astro-card-tagline">目前已知唯一存在生命的行星，约 71% 表面被液态水覆盖</p>
        <div class="astro-card-stats"><span>5.97×10²⁴ kg</span><span>6,371 km</span><span>15 °C</span></div>
      </div>
      <span class="astro-badge planet">行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="planet" data-name="火星 Mars" data-mass="6.4169e+23" data-radius="3389.5" data-density="3.934" data-temp="-59" data-period="686.98" data-moons="2">
    <a class="astro-card-link" href="objects/mars/">
      <div class="astro-img planet"><img src="assets/planets/mars.webp" alt="火星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">火星<span class="en">Mars</span></div>
        <p class="astro-card-tagline">红色的沙漠行星，拥有太阳系最高的火山与最深的峡谷</p>
        <div class="astro-card-stats"><span>6.42×10²³ kg</span><span>3,390 km</span><span>-59 °C</span></div>
      </div>
      <span class="astro-badge planet">行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="planet" data-name="木星 Jupiter" data-mass="1.89813e+27" data-radius="69911" data-density="1.326" data-temp="-110" data-period="4332.59" data-moons="95">
    <a class="astro-card-link" href="objects/jupiter/">
      <div class="astro-img planet"><img src="assets/planets/jupiter.webp" alt="木星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">木星<span class="en">Jupiter</span></div>
        <p class="astro-card-tagline">太阳系最大的行星，质量超过其余七颗行星的总和</p>
        <div class="astro-card-stats"><span>1.9×10²⁷ kg</span><span>69,911 km</span><span>-110 °C</span></div>
      </div>
      <span class="astro-badge planet">行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="planet" data-name="土星 Saturn" data-mass="5.6832e+26" data-radius="58232" data-density="0.687" data-temp="-140" data-period="10755.7" data-moons="274">
    <a class="astro-card-link" href="objects/saturn/">
      <div class="astro-img planet"><img src="assets/planets/saturn.webp" alt="土星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">土星<span class="en">Saturn</span></div>
        <p class="astro-card-tagline">以壮观环系闻名的气态巨行星，平均密度比水还小</p>
        <div class="astro-card-stats"><span>5.68×10²⁶ kg</span><span>58,232 km</span><span>-140 °C</span></div>
      </div>
      <span class="astro-badge planet">行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="planet" data-name="天王星 Uranus" data-mass="8.6813e+25" data-radius="25559" data-density="1.27" data-temp="-195" data-period="30589" data-moons="28">
    <a class="astro-card-link" href="objects/uranus/">
      <div class="astro-img planet"><img src="assets/planets/uranus.webp" alt="天王星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">天王星<span class="en">Uranus</span></div>
        <p class="astro-card-tagline">躺着自转的冰巨星，自转轴倾角约 98 度</p>
        <div class="astro-card-stats"><span>8.68×10²⁵ kg</span><span>25,559 km</span><span>-195 °C</span></div>
      </div>
      <span class="astro-badge planet">行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="planet" data-name="海王星 Neptune" data-mass="1.0241e+26" data-radius="24764" data-density="1.638" data-temp="-200" data-period="59800" data-moons="16">
    <a class="astro-card-link" href="objects/neptune/">
      <div class="astro-img planet"><img src="assets/planets/neptune.webp" alt="海王星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">海王星<span class="en">Neptune</span></div>
        <p class="astro-card-tagline">太阳系最外侧的行星，风速可达每小时 2100 公里</p>
        <div class="astro-card-stats"><span>1.02×10²⁶ kg</span><span>24,764 km</span><span>-200 °C</span></div>
      </div>
      <span class="astro-badge planet">行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="dwarf_planet" data-name="冥王星 Pluto" data-mass="1.303e+22" data-radius="1188.3" data-density="1.85" data-temp="-225" data-period="90560" data-moons="5">
    <a class="astro-card-link" href="objects/pluto/">
      <div class="astro-img dwarf_planet"><img src="assets/planets/pluto.webp" alt="冥王星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">冥王星<span class="en">Pluto</span></div>
        <p class="astro-card-tagline">曾被列为第九大行星，与卫星卡戎构成双天体系统</p>
        <div class="astro-card-stats"><span>1.3×10²² kg</span><span>1,188 km</span><span>-225 °C</span></div>
      </div>
      <span class="astro-badge dwarf_planet">矮行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="dwarf_planet" data-name="谷神星 Ceres" data-mass="9.3846e+20" data-radius="469.7" data-density="2.162" data-temp="" data-period="1682.0" data-moons="0">
    <a class="astro-card-link" href="objects/ceres/">
      <div class="astro-img dwarf_planet"><img src="assets/planets/ceres.webp" alt="谷神星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">谷神星<span class="en">Ceres</span></div>
        <p class="astro-card-tagline">小行星带中最大的天体，唯一位于内太阳系的矮行星</p>
        <div class="astro-card-stats"><span>9.38×10²⁰ kg</span><span>469.7 km</span><span>2.162 g/cm³</span></div>
      </div>
      <span class="astro-badge dwarf_planet">矮行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="dwarf_planet" data-name="鸟神星 Makemake" data-mass="" data-radius="" data-density="" data-temp="" data-period="112364.81" data-moons="1">
    <a class="astro-card-link" href="objects/makemake/">
      <div class="astro-img dwarf_planet"><img src="assets/planets/makemake.webp" alt="鸟神星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">鸟神星<span class="en">Makemake</span></div>
        <p class="astro-card-tagline">柯伊伯带最大的经典天体之一，表面覆盖甲烷冰</p>
        <div class="astro-card-stats"></div>
      </div>
      <span class="astro-badge dwarf_planet">矮行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="dwarf_planet" data-name="妊神星 Haumea" data-mass="" data-radius="" data-density="" data-temp="" data-period="103208.12" data-moons="2">
    <a class="astro-card-link" href="objects/haumea/">
      <div class="astro-img dwarf_planet"><img src="assets/planets/haumea.webp" alt="妊神星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">妊神星<span class="en">Haumea</span></div>
        <p class="astro-card-tagline">自转极快的椭球状矮行星，拥有光环</p>
        <div class="astro-card-stats"></div>
      </div>
      <span class="astro-badge dwarf_planet">矮行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="dwarf_planet" data-name="阋神星 Eris" data-mass="" data-radius="" data-density="" data-temp="" data-period="204516.66" data-moons="1">
    <a class="astro-card-link" href="objects/eris/">
      <div class="astro-img dwarf_planet"><img src="assets/planets/eris.webp" alt="阋神星" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">阋神星<span class="en">Eris</span></div>
        <p class="astro-card-tagline">质量最大的矮行星，它的发现促使冥王星降级</p>
        <div class="astro-card-stats"></div>
      </div>
      <span class="astro-badge dwarf_planet">矮行星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="月球 Moon" data-mass="7.346e+22" data-radius="1737.4" data-density="3.344" data-temp="-20" data-period="27.3217" data-moons="0">
    <a class="astro-card-link" href="objects/moon/">
      <div class="astro-img moon"><img src="assets/planets/moon.webp" alt="月球" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">月球<span class="en">Moon</span></div>
        <p class="astro-card-tagline">地球唯一的天然卫星，潮汐锁定使它永远以同一面朝向地球</p>
        <div class="astro-card-stats"><span>7.35×10²² kg</span><span>1,737 km</span><span>-20 °C</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="火卫一 Phobos" data-mass="1.06e+16" data-radius="11.27" data-density="1.9" data-temp="" data-period="0.31891" data-moons="0">
    <a class="astro-card-link" href="objects/phobos/">
      <div class="astro-img moon"><img src="assets/planets/phobos.webp" alt="火卫一" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">火卫一<span class="en">Phobos</span></div>
        <p class="astro-card-tagline">火星较大的卫星，正以每百年约 1.8 米的速度靠近火星</p>
        <div class="astro-card-stats"><span>1.06×10¹⁶ kg</span><span>11.3 km</span><span>1.9 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="火卫二 Deimos" data-mass="2400000000000000.0" data-radius="6.3" data-density="1.75" data-temp="" data-period="1.26244" data-moons="0">
    <a class="astro-card-link" href="objects/deimos/">
      <div class="astro-img moon"><img src="assets/planets/deimos.webp" alt="火卫二" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">火卫二<span class="en">Deimos</span></div>
        <p class="astro-card-tagline">火星较小的卫星，形状极不规则，表面覆盖细腻的风化层</p>
        <div class="astro-card-stats"><span>2.4×10¹⁵ kg</span><span>6.3 km</span><span>1.75 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="木卫一 Io" data-mass="8.932e+22" data-radius="1821.5" data-density="3.53" data-temp="" data-period="1.769138" data-moons="0">
    <a class="astro-card-link" href="objects/io/">
      <div class="astro-img moon"><img src="assets/planets/io.webp" alt="木卫一" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">木卫一<span class="en">Io</span></div>
        <p class="astro-card-tagline">太阳系火山活动最剧烈的天体，表面遍布硫磺沉积物</p>
        <div class="astro-card-stats"><span>8.93×10²² kg</span><span>1,822 km</span><span>3.53 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="木卫二 Europa" data-mass="4.8e+22" data-radius="1560.8" data-density="3.01" data-temp="" data-period="3.551181" data-moons="0">
    <a class="astro-card-link" href="objects/europa/">
      <div class="astro-img moon"><img src="assets/planets/europa.webp" alt="木卫二" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">木卫二<span class="en">Europa</span></div>
        <p class="astro-card-tagline">冰壳之下藏有全球性液态海洋，搜寻地外生命的热门目标</p>
        <div class="astro-card-stats"><span>4.8×10²² kg</span><span>1,561 km</span><span>3.01 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="木卫三 Ganymede" data-mass="1.4819e+23" data-radius="2631.2" data-density="1.94" data-temp="" data-period="7.154553" data-moons="0">
    <a class="astro-card-link" href="objects/ganymede/">
      <div class="astro-img moon"><img src="assets/planets/ganymede.webp" alt="木卫三" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">木卫三<span class="en">Ganymede</span></div>
        <p class="astro-card-tagline">太阳系最大的卫星，比水星还大，且拥有自己的磁场</p>
        <div class="astro-card-stats"><span>1.48×10²³ kg</span><span>2,631 km</span><span>1.94 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="木卫四 Callisto" data-mass="1.0759e+23" data-radius="2410.3" data-density="1.83" data-temp="" data-period="16.689017" data-moons="0">
    <a class="astro-card-link" href="objects/callisto/">
      <div class="astro-img moon"><img src="assets/planets/callisto.webp" alt="木卫四" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">木卫四<span class="en">Callisto</span></div>
        <p class="astro-card-tagline">太阳系撞击坑最密集的天体之一，表面几乎未被地质活动改造</p>
        <div class="astro-card-stats"><span>1.08×10²³ kg</span><span>2,410 km</span><span>1.83 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="土卫一 Mimas" data-mass="3.79e+19" data-radius="198.7" data-density="1.15" data-temp="" data-period="0.9424218" data-moons="0">
    <a class="astro-card-link" href="objects/mimas/">
      <div class="astro-img moon"><img src="assets/planets/mimas.webp" alt="土卫一" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">土卫一<span class="en">Mimas</span></div>
        <p class="astro-card-tagline">被称为'死星'的卫星，赫歇尔撞击坑占其表面的三分之一</p>
        <div class="astro-card-stats"><span>3.79×10¹⁹ kg</span><span>198.7 km</span><span>1.15 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="土卫二 Enceladus" data-mass="1.08e+20" data-radius="252.1" data-density="1.61" data-temp="" data-period="1.370218" data-moons="0">
    <a class="astro-card-link" href="objects/enceladus/">
      <div class="astro-img moon"><img src="assets/planets/enceladus.webp" alt="土卫二" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">土卫二<span class="en">Enceladus</span></div>
        <p class="astro-card-tagline">南极喷泉将地下海洋的物质直接送入太空的冰质小卫星</p>
        <div class="astro-card-stats"><span>1.08×10²⁰ kg</span><span>252.1 km</span><span>1.61 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="土卫三 Tethys" data-mass="6.18e+20" data-radius="530.7" data-density="0.985" data-temp="" data-period="1.887802" data-moons="0">
    <a class="astro-card-link" href="objects/tethys/">
      <div class="astro-img moon"><img src="assets/planets/tethys.webp" alt="土卫三" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">土卫三<span class="en">Tethys</span></div>
        <p class="astro-card-tagline">冰质卫星，表面的伊萨卡峡谷绵延约 2000 公里</p>
        <div class="astro-card-stats"><span>6.18×10²⁰ kg</span><span>530.7 km</span><span>0.985 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="土卫四 Dione" data-mass="1.1e+21" data-radius="561.4" data-density="1.478" data-temp="" data-period="2.736915" data-moons="0">
    <a class="astro-card-link" href="objects/dione/">
      <div class="astro-img moon"><img src="assets/planets/dione.webp" alt="土卫四" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">土卫四<span class="en">Dione</span></div>
        <p class="astro-card-tagline">冰质卫星，纵横的冰壳悬崖记录着古老的地质活动</p>
        <div class="astro-card-stats"><span>1.1×10²¹ kg</span><span>561.4 km</span><span>1.478 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="土卫五 Rhea" data-mass="2.31e+21" data-radius="763.8" data-density="1.236" data-temp="" data-period="4.5175" data-moons="0">
    <a class="astro-card-link" href="objects/rhea/">
      <div class="astro-img moon"><img src="assets/planets/rhea.webp" alt="土卫五" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">土卫五<span class="en">Rhea</span></div>
        <p class="astro-card-tagline">土星第二大卫星，由约三分之二的冰与三分之一的岩石构成</p>
        <div class="astro-card-stats"><span>2.31×10²¹ kg</span><span>763.8 km</span><span>1.236 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="土卫六 Titan" data-mass="1.3455e+23" data-radius="2575.5" data-density="1.881" data-temp="-179" data-period="15.945421" data-moons="0">
    <a class="astro-card-link" href="objects/titan/">
      <div class="astro-img moon"><img src="assets/planets/titan.webp" alt="土卫六" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">土卫六<span class="en">Titan</span></div>
        <p class="astro-card-tagline">太阳系唯一拥有浓厚大气的卫星，地表有液态甲烷的湖泊与河流</p>
        <div class="astro-card-stats"><span>1.35×10²³ kg</span><span>2,576 km</span><span>-179 °C</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="土卫七 Hyperion" data-mass="5.6e+18" data-radius="138.7" data-density="0.55" data-temp="" data-period="21.276609" data-moons="0">
    <a class="astro-card-link" href="objects/hyperion/">
      <div class="astro-img moon"><img src="assets/planets/hyperion.webp" alt="土卫七" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">土卫七<span class="en">Hyperion</span></div>
        <p class="astro-card-tagline">形状极不规则的卫星，混沌自转使它的朝向无法预测</p>
        <div class="astro-card-stats"><span>5.6×10¹⁸ kg</span><span>138.7 km</span><span>0.55 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="土卫八 Iapetus" data-mass="1.81e+21" data-radius="734.5" data-density="1.088" data-temp="" data-period="79.330183" data-moons="0">
    <a class="astro-card-link" href="objects/iapetus/">
      <div class="astro-img moon"><img src="assets/planets/iapetus.webp" alt="土卫八" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">土卫八<span class="en">Iapetus</span></div>
        <p class="astro-card-tagline">'阴阳脸'卫星，一面亮如雪一面黑如炭，赤道还有一道奇异山脊</p>
        <div class="astro-card-stats"><span>1.81×10²¹ kg</span><span>734.5 km</span><span>1.088 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="海卫一 Triton" data-mass="2.14e+22" data-radius="1353.4" data-density="2.05" data-temp="-235" data-period="5.876854" data-moons="0">
    <a class="astro-card-link" href="objects/triton/">
      <div class="astro-img moon"><img src="assets/planets/triton.webp" alt="海卫一" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">海卫一<span class="en">Triton</span></div>
        <p class="astro-card-tagline">沿逆行轨道运行的卫星，或为被俘获的柯伊伯带天体</p>
        <div class="astro-card-stats"><span>2.14×10²² kg</span><span>1,353 km</span><span>-235 °C</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="天卫五 Miranda" data-mass="6.6e+19" data-radius="235.8" data-density="1.2" data-temp="" data-period="1.413479" data-moons="0">
    <a class="astro-card-link" href="objects/miranda/">
      <div class="astro-img moon"><img src="assets/planets/miranda.webp" alt="天卫五" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">天卫五<span class="en">Miranda</span></div>
        <p class="astro-card-tagline">天王星系统中地质最奇特的卫星，断崖与沟槽密布</p>
        <div class="astro-card-stats"><span>6.6×10¹⁹ kg</span><span>235.8 km</span><span>1.2 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="天卫一 Ariel" data-mass="1.29e+21" data-radius="578.9" data-density="1.59" data-temp="" data-period="2.520379" data-moons="0">
    <a class="astro-card-link" href="objects/ariel/">
      <div class="astro-img moon"><img src="assets/planets/ariel.webp" alt="天卫一" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">天卫一<span class="en">Ariel</span></div>
        <p class="astro-card-tagline">天王星系统中最明亮的卫星，表面峡谷纵横</p>
        <div class="astro-card-stats"><span>1.29×10²¹ kg</span><span>578.9 km</span><span>1.59 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="天卫二 Umbriel" data-mass="1.22e+21" data-radius="584.7" data-density="1.46" data-temp="" data-period="4.144176" data-moons="0">
    <a class="astro-card-link" href="objects/umbriel/">
      <div class="astro-img moon"><img src="assets/planets/umbriel.webp" alt="天卫二" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">天卫二<span class="en">Umbriel</span></div>
        <p class="astro-card-tagline">天王星系统中最暗的卫星，表面古老撞击坑密布</p>
        <div class="astro-card-stats"><span>1.22×10²¹ kg</span><span>584.7 km</span><span>1.46 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="天卫三 Titania" data-mass="3.42e+21" data-radius="788.9" data-density="1.66" data-temp="" data-period="8.705867" data-moons="0">
    <a class="astro-card-link" href="objects/titania/">
      <div class="astro-img moon"><img src="assets/planets/titania.webp" alt="天卫三" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">天卫三<span class="en">Titania</span></div>
        <p class="astro-card-tagline">天王星最大的卫星，表面有巨大的地堑系统</p>
        <div class="astro-card-stats"><span>3.42×10²¹ kg</span><span>788.9 km</span><span>1.66 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
  <article class="astro-card" data-category="moon" data-name="天卫四 Oberon" data-mass="2.88e+21" data-radius="761.4" data-density="1.56" data-temp="" data-period="13.463234" data-moons="0">
    <a class="astro-card-link" href="objects/oberon/">
      <div class="astro-img moon"><img src="assets/planets/oberon.webp" alt="天卫四" loading="lazy"></div>
      <div class="astro-card-body">
        <div class="astro-card-title">天卫四<span class="en">Oberon</span></div>
        <p class="astro-card-tagline">天王星最外侧的大卫星，表面遍布撞击坑与深色物质</p>
        <div class="astro-card-stats"><span>2.88×10²¹ kg</span><span>761.4 km</span><span>1.56 g/cm³</span></div>
      </div>
      <span class="astro-badge moon">卫星</span>
    </a>
  </article>
</div>
<p class="astro-empty" id="astro-empty" hidden>没有匹配的天体，换个关键词或分类试试。</p>

<section class="astro-articles" id="articles">
  <h2>科普文章</h2>
  <p>每颗天体的数据页之下，附一篇深度科普：</p>
  <ul class="astro-article-list">
    <li><a href="objects/mercury/">水星（Mercury）</a></li>
    <li><a href="objects/venus/">金星（Venus）</a></li>
    <li><a href="objects/mars/">火星（Mars）</a></li>
    <li><a href="objects/jupiter/">木星（Jupiter）</a></li>
    <li><a href="objects/saturn/">土星（Saturn）</a></li>
    <li><a href="objects/pluto/">冥王星（Pluto）</a></li>
  </ul>
</section>

<section class="astro-note">
  <h2>数据说明</h2>
  <p>全部数值整理自 NASA 公开资料（公共领域），每个天体页面均标注来源与核对日期（最近核对：2026-10-18）。发现数据错误？欢迎到 <a href="https://github.com/yufengwolf/astro-blog/issues">GitHub Issues</a> 反馈。</p>
</section>

<p class="obj-version">数据版本 v1.4 · 收录 35 个天体（全部配图）</p>
