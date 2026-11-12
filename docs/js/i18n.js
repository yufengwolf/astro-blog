/*!
 * i18n.js — 星野笔记全站中英双语运行时（原生 JS，无依赖）
 *
 * 设计：静态 Markdown / 生成页保持中文为唯一源文本，本文件在客户端按
 * <html data-lang> 做可逆替换。切换回中文时从 WeakMap 恢复原文，绝不丢失
 * 页面里的数据、链接或数值。名称 / 分类 / 简介走 gen_pages.py 生成的
 * i18n-data.js（按 id 索引，不做名称匹配），与宇宙层级页保持同一套口径。
 *
 * 全局接口：
 *   window.SITE_LANG                 当前语言 'zh' | 'en'
 *   window.siteT(key)                取 UI 文案（键见 UI）
 *   window.setSiteLang(lang)         切换并持久化 + 派发 site:langchange
 *   window.onSiteLang(fn)            注册语言变更回调
 */
(function () {
  'use strict';

  var STORE_KEY = 'astro-site-lang';
  var D = window.SITE_I18N_DATA || { names: {}, cats: {}, taglines: {} };

  // ---------------------------------------------------------------- UI 词表
  // [中文, English]。键供业务 JS 用 siteT() 取；中文列同时用于文本节点反查。
  var UI = {
    siteName: ['星野笔记', 'Starfield Notes'],
    navOverview: ['天体总览', 'Object Explorer'],
    navCompare: ['天体对比', 'Size Comparison'],
    navLibrary: ['天体库', 'Object Library'],
    navSolar: ['太阳系3D模型', 'Solar System 3D'],
    navUniverse: ['宇宙层级', 'Cosmic Hierarchy'],
    navData: ['天体数据集', 'Dataset'],
    headerAria: ['页眉', 'Header'],
    toc: ['目录', 'On this page'],
    search: ['搜索', 'Search'],
    prev: ['上一页', 'Previous'],
    next: ['下一页', 'Next'],
    paletteLight: ['切换浅色模式', 'Switch to light mode'],
    paletteDark: ['切换深色模式', 'Switch to dark mode'],
    langTitle: ['切换显示语言', 'Switch display language'],

    heroTitle: ['天体数据库', 'Celestial Object Database'],
    heroArticles: ['科普文章', 'Featured Articles'],
    heroLibrary: ['天体库总表', 'Full Object Table'],
    searchObjects: ['搜索天体…', 'Search objects…'],
    filterAria: ['按分类筛选', 'Filter by category'],
    all: ['全部', 'All'],
    sortBy: ['排序', 'Sort by'],
    sortAria: ['排序方式', 'Sort order'],
    sortName: ['名称', 'Name'],
    sortMass: ['质量', 'Mass'],
    sortRadius: ['直径', 'Diameter'],
    sortDensity: ['密度', 'Density'],
    sortTemp: ['表面温度', 'Surface temperature'],
    sortPeriod: ['轨道周期', 'Orbital period'],
    sortMoons: ['卫星数量', 'Moon count'],
    empty: ['没有匹配的天体，换个关键词或分类试试。', 'No matching objects. Try another keyword or category.'],
    articlesIntro: ['每颗天体的数据页之下，附一篇深度科普：', 'Each object data page includes an in-depth article:'],
    aboutData: ['数据说明', 'About the Data'],
    objectCount: ['显示 {shown} / {total} 个天体', 'Showing {shown} of {total} objects'],

    sectionPhysical: ['物理参数', 'Physical Properties'],
    sectionOrbit: ['轨道参数', 'Orbital Properties'],
    sectionFeatures: ['其他特征', 'Other Features'],
    thParameter: ['参数', 'Parameter'],
    thValue: ['数值', 'Value'],
    fMass: ['质量', 'Mass'],
    fDiameter: ['平均直径', 'Mean diameter'],
    fRadius: ['平均半径', 'Mean radius'],
    fGravity: ['表面重力', 'Surface gravity'],
    fEscape: ['逃逸速度', 'Escape velocity'],
    fTemp: ['平均表面温度', 'Mean surface temperature'],
    fSpectral: ['光谱型', 'Spectral type'],
    fStarType: ['恒星类型', 'Stellar type'],
    fLum: ['光度', 'Luminosity'],
    fDistance: ['距离', 'Distance'],
    fTilt: ['转轴倾角', 'Axial tilt'],
    fRotation: ['自转周期', 'Rotation period'],
    fAtmosphere: ['大气成分', 'Atmosphere'],
    fMagnetic: ['全球磁场', 'Global magnetic field'],
    fNote: ['备注', 'Notes'],
    fDiscovery: ['发现', 'Discovery'],
    fCategory: ['分类', 'Category'],
    fConstellation: ['星座', 'Constellation'],
    fSemimajor: ['半长轴', 'Semi-major axis'],
    fInclination: ['轨道倾角', 'Orbital inclination'],
    fEccentricity: ['轨道偏心率', 'Eccentricity'],
    fOrbVel: ['平均轨道速度', 'Mean orbital velocity'],
    fDensity: ['平均密度', 'Mean density'],
    fAlbedo: ['反照率', 'Albedo'],
    fMembers: ['已知成员', 'Known members'],
    fParent: ['母天体', 'Parent body'],
    fMoons: ['卫星', 'Moons'],
    fSources: ['数据来源', 'Sources'],
    fVerified: ['核对日期', 'Verified'],
    relatedArticles: ['相关文章', 'Related articles'],
    viz3d: ['3D 交互可视化', '3D interactive view'],
    imageCredit: ['影像：程序化示意图', 'Image: programmatic illustration'],
    openFullViz: ['打开完整交互版 ↗', 'Open full interactive view ↗'],
    prevObject: ['← 上一颗：', '← Previous: '],
    nextObject: ['下一颗：', 'Next: '],

    dlTitle: ['天体数据集', 'Celestial Object Dataset'],
    dlFields: ['字段说明', 'Field Reference'],
    dlLicense: ['许可与来源', 'License & Sources'],
    dlTodo: ['待补充', 'Pending'],
    dlFull: ['完整数据（含来源与核对日期）', 'Full data (with sources & verification dates)'],
    dlFlat: ['扁平表格（Excel 可直接打开）', 'Flat table (opens directly in Excel)'],
    thField: ['字段', 'Field'],
    thMeaning: ['含义', 'Meaning'],
    thUnit: ['单位', 'Unit'],

    cmpTitle: ['天体对比', 'Size Comparison'],
    objA: ['天体 A', 'Object A'],
    objB: ['天体 B', 'Object B'],
    scale: ['刻度', 'Scale'],
    linear: ['线性', 'Linear'],
    log: ['对数', 'Logarithmic'],
    cmpDetail: ['详细数据对比', 'Detailed Comparison'],
    cmpRatios: ['核心倍数', 'Key Ratios'],
    cmpParam: ['参数', 'Parameter'],
    rDiameter: ['直径', 'Diameter'],
    rVolume: ['体积', 'Volume'],
    rVolumeEq: ['体积（等效球）', 'Volume (equivalent sphere)'],
    rMass: ['质量', 'Mass'],
    rGravity: ['表面重力', 'Surface gravity'],
    rTemp: ['平均温度', 'Mean temperature'],
    rType: ['类型', 'Type'],
    allTypes: ['全部类型', 'All types'],
    noRadius: ['所选天体缺少半径数据，无法绘制大小对比。', 'Selected objects lack radius data; size comparison unavailable.'],
    shareHint: ['分享链接已更新：复制当前地址即可还原此对比组合。', 'Share link updated: copy the current URL to restore this comparison.'],
    cmpSphere: ['球体', 'Spheres'],
    cmpObject: ['天体', 'Objects'],
    cmpLogNote: ['按对数刻度绘制（非真实比例，仅让悬殊尺寸都可见）', 'Drawn on a logarithmic scale (not true scale; only to keep vastly different sizes visible)'],
    cmpLinearNote: ['按真实直径比例绘制', 'Drawn at true diameter ratio'],
    cmpExtNote: ['星系/星云等延展天体以等效球径示意（非真实形状），具体尺度以数字为准', 'Extended objects (galaxies / nebulae) are shown as equivalent spheres; trust the numbers, not the shape'],
    cmpDotNote: [' 在真实比例下已缩为一个点（旁标实际倍数），未作放大', ' is reduced to a dot at true scale (actual ratio shown), not enlarged'],
    cmpDotOnly: ['按真实比例仅 ', 'Only '],
    cmpDotUnder: ['不足 0.1', 'under 0.1'],
    cmpDotPx: [' 像素：仅为', ' px at true scale: just '],
    cmpOf: [' 的 ', ' of '],
    unitDays: ['天', 'd'],
    unitHours: ['小时', 'h'],
    retrograde: ['逆行 · ', 'Retrograde · '],

    solarTitle: ['太阳系 3D 模型', 'Solar System 3D Model'],
    solarBarTitle: ['太阳系 3D 交互站', 'Solar System 3D Interactive'],
    solarHome: ['↺ 重新选择', '↺ Choose again'],
    fullscreen: ['全屏', 'Fullscreen'],
    exitFullscreen: ['退出全屏', 'Exit fullscreen'],
    rotatePhone: ['请旋转手机至横屏，获得更大的观测视野', 'Rotate your phone to landscape for a wider view']
  };

  // 分类：与 universe-data.json 的 category_i18n 保持一致
  var CATS = {
    star: ['恒星', 'Star'], planet: ['行星', 'Planet'], moon: ['卫星', 'Moon'],
    galaxy: ['星系', 'Galaxy'], nebula: ['星云', 'Nebula'], cluster: ['星团', 'Cluster'],
    dwarf_planet: ['矮行星', 'Dwarf planet'], asteroid: ['小行星', 'Asteroid'],
    black_hole: ['黑洞', 'Black hole'], structure: ['大尺度结构', 'Large-scale structure'],
    comet: ['彗星', 'Comet']
  };

  // 反查表：中文原文 -> 英文（整串精确匹配，最长优先）
  var ZH2EN = {};
  Object.keys(UI).forEach(function (k) { ZH2EN[UI[k][0]] = UI[k][1]; });
  Object.keys(CATS).forEach(function (k) { ZH2EN[CATS[k][0]] = CATS[k][1]; });
  Object.keys(D.names || {}).forEach(function (id) {
    var pair = D.names[id];
    if (pair && pair[0] && pair[1] && pair[0] !== pair[1]) ZH2EN[pair[0]] = pair[1];
  });
  // 数据层自由文本译稿：由 gen_pages.py 按 id + 字段从 i18n_fields.json 构造，
  // 这里只做「中文原文整串相等」查找；源文案变动 → 命中失败 → 漂移检测报警。
  Object.keys(D.fields || {}).forEach(function (zh) { ZH2EN[zh] = D.fields[zh]; });
  // 常规值 / 固定短语（不属于 UI 词表，但作为整串出现）
  var EXTRA = {
    '是': 'Yes', '否': 'No', '无': 'None', '史前': 'Prehistoric', '自古已知': 'Known since antiquity',
    '天体': 'Object', '均温': 'Mean temp', '卫星数': 'Moons', '类型细分': 'Subtype',
    '分类：恒星': 'Category: Star', '分类：行星': 'Category: Planet',
    '分类：卫星': 'Category: Moon', '分类：矮行星': 'Category: Dwarf planet',
    '分类：星系': 'Category: Galaxy', '分类：星云': 'Category: Nebula',
    '分类：星团': 'Category: Cluster', '分类：黑洞': 'Category: Black hole',
    '分类：小行星': 'Category: Asteroid', '分类：彗星': 'Category: Comet',
    '分类：大尺度结构': 'Category: Large-scale structure',
    '数据来源：': 'Sources: ', '母天体：': 'Parent: ',
    '打开完整交互版 ↗': 'Open full interactive view ↗',
    // Material 主题内置文案 + 首页排序下拉（<option> 也参与整串替换）
    '正在初始化搜索引擎': 'Initializing search',
    '回到页面顶部': 'Back to top',
    '质量 ↓': 'Mass ↓', '直径 ↓': 'Diameter ↓', '密度 ↓': 'Density ↓',
    '表面温度 ↓': 'Surface temperature ↓', '轨道周期 ↓': 'Orbital period ↓',
    '卫星数量 ↓': 'Moon count ↓',
    // 数据集页字段说明表的整串值
    '有效温度（black-body 口径）': 'Effective temperature (black-body)',
    '表面温度': 'Surface temperature',
    '反照率（主值 / Bond 口径 / Geometric 口径）': 'Albedo (primary / Bond / Geometric)',
    '表面气压': 'Surface pressure',
    '轨道倾角 / 偏心率': 'Inclination / Eccentricity',
    '已确认卫星数': 'Confirmed moons',
    '数据来源 / 核对日期': 'Sources / Verified',
    // 字段说明表里两条长释义：整串精确匹配（源文案在 gen_pages.py 的静态模板里）
    '距离（恒星/星云/星系/黑洞为对地距离，单位光年）':
      'Distance (from Earth for stars / nebulae / galaxies / black holes; unit: light-years)',
    '类型细分（星云：发射/反射/行星状/超新星遗迹；星系：旋涡/椭圆/棒旋/不规则；恒星：黄矮星/红巨星/白矮星/中子星等）':
      'Subtype (nebulae: emission / reflection / planetary / supernova remnant; galaxies: spiral / elliptical / barred spiral / irregular; stars: yellow dwarf / red giant / white dwarf / neutron star, etc.)',
    '天': 'd', '颗': '—',
    // Material 主题内置 / 表格短词（整串精确匹配，不做模糊猜测）
    '跳转至内容': 'Skip to content', '跳转至': 'Skip to content',
    '轨道半长轴': 'Semi-major axis', '主要数据源：': 'Primary sources:',
    '待补充': 'Pending', '宇宙天体层级': 'Cosmic Hierarchy',
    '史前': 'Prehistoric', '自古已知': 'Known since antiquity',
    '影像：': 'Image: ', 'AIA 极紫外成像': 'AIA extreme-UV image',
    '直径 ': 'Diameter ', '质量 ': 'Mass ', '分类：': 'Category: ',
    '核对日期：': 'Verified: ', '核对）': ' verified)',
    '个天体已全部配图': ' objects, all illustrated'
  };
  Object.keys(EXTRA).forEach(function (k) { ZH2EN[k] = EXTRA[k]; });

  // 带数字 / 变量的文本：正则替换（保留数值，只换中文骨架）
  var PATTERNS = [
    [/^(\S+?) (\d+)$/, function (m, zh, num) { return (ZH2EN[zh] || zh) + ' ' + num; }],
    [/收录 (\d+) 个天体（全部配图）/, '$1 objects (all illustrated)'],
    [/本站收录的全部 (\d+) 个天体/, 'All $1 objects in this catalogue'],
    [/最近更新：/, 'Last updated: '],
    [/个天体的质量、直径、密度、温度/, ' objects: mass, diameter, density, temperature'],
    [/(\d+) 个天体的结构化数据，提供 JSON 与 CSV 两种格式下载/,
     '$1 objects with structured data, available as JSON and CSV'],
    [/选择任意两个天体（可按类型筛选）/, 'Pick any two objects (filterable by type)'],
    [/本站收录的/, 'This catalogue contains '],
    [/（核对日期：/, ' (verified: '],
    [/数据版本 v/, 'Data version v'],
    [/点击名称进入详情页（完整数据 \+ 科普文章）/, 'Click a name for the full data page and article'],
    [/需要筛选排序？回到/, 'Need filtering or sorting? Back to '],
    [/天体总览工具页/, 'the Object Explorer']
  ];

  // 数值单元格里的中文单位：只做「数字 + 单位」的有界换算，不碰正文散文。
  // 规则顺序敏感：万/亿光年、年（天）必须先于单字「年/天/光年」。
  var CELL_SUB = [
    [/（1 × 太阳直径）/g, ' (1 solar diameter)'],
    [/× 太阳直径/g, '× solar diameter'],
    [/× 地球直径/g, '× Earth diameter'],
    [/([\d,.]+)\s*万光年/g, '$1×10⁴ ly'],
    [/([\d,.]+)\s*亿光年/g, '$1×10⁸ ly'],
    [/([\d,.]+)\s*光年/g, '$1 ly'],
    [/([\d,.]+)\s*年\s*（([\d,]+)\s*天）/g, '$1 yr ($2 d)'],
    [/([\d,.]+)\s*天/g, '$1 d'],
    [/([\d,.]+)\s*小时/g, '$1 h'],
    [/颗/g, ''],
    [/光年/g, ' ly'],
    [/直径 /g, 'Diameter '],
    [/质量 /g, 'Mass '],
    [/分类：/g, 'Category: '],
    [/母天体：/g, 'Parent: '],
    [/数据来源：/g, 'Sources: '],
    [/；核对日期：/g, '; verified: '],
    [/（核对日期：/g, ' (verified: '],
    [/ 核对）/g, ' verified)'],
    [/个天体已全部配图/g, ' objects, all illustrated'],
    [/。数值整理自 NASA NSSDC \/ JPL \/ Wikipedia 等公开天文资料。发现错误请到 /g,
     '. Values compiled from NASA NSSDC / JPL / Wikipedia and other open sources. Report errors at '],
    [/ 反馈。/g, '.'],
    [/【AI复校 /g, '[AI review '],
    [/：填充:/g, ': filled '],
    [/颗（主要：/g, ' moons (notable: '],
    [/颗/g, ' moons']
  ];
  var CELL_SELECTOR = '.obj-data-block td, .md-typeset table td, .astro-card-stats span,' +
                      '.obj-summary, .obj-parent, .obj-version, .astro-img-credit,' +
                      '.obj-source p, .sizecmp-detail td, .sizecmp-ratios';

  // 块级静态文案：key 是元素 textContent 的规范化整串（精确匹配，不做模糊容错），
  // value 是可含内联标签的英文 HTML。源文案改动后此处若未同步，
  // check_site_i18n.js 的「译表漂移检测」会报错，绝不静默放行。
  var BLOCKS = {
    '全部数值整理自 NASA / JPL / Wikipedia 等公开天文资料，每个天体页面均标注来源与核对日期（最近核对：2026-11-12）。发现数据错误？欢迎到 GitHub Issues 反馈。':
      'All values compiled from NASA / JPL / Wikipedia and other open astronomical sources. Every object page lists its sources and verification date (last verified: 2026-11-12). Spotted an error? Please report it on <a href="https://github.com/yufengwolf/astro-blog/issues">GitHub Issues</a>.',
    '本站收录的全部 215 个天体。点击名称进入详情页（完整数据 + 科普文章）；需要筛选排序？回到天体总览工具页。':
      'All 215 objects in this catalogue. Click a name for the full data page and article. Need filtering or sorting? Back to <a href="../">the Object Explorer</a>.',
    '字段说明（下载 CSV 的原始单位：质量 kg · 半径 km · 密度 g/cm³ · 温度 ℃ · 半长轴 km · 周期 天 · 卫星数 颗）':
      'Field reference (raw units in the CSV: mass kg · radius km · density g/cm³ · temperature °C · semi-major axis km · period days · moon count)',
    '注意：本表描述的是 astro.json / CSV 的原始字段。radius_km 存的是半径；页面与卡片统一按「直径 = 2 × 半径」展示，主单位按量级自动切换 km / 光年，并辅以地球或太阳直径倍数、M⊕ / M☉、℃ 括注。':
      '<strong>Note:</strong> this table describes the <strong>raw fields</strong> in <code>astro.json</code> / CSV. <code>radius_km</code> stores the <strong>radius</strong>; pages and cards show <strong>diameter = 2 × radius</strong>, switching the primary unit between km and light-years by magnitude, with Earth/Solar diameter multiples, M⊕ / M☉ and °C annotations.',
    '需要筛选排序？回到天体总览工具页。': 'Need filtering or sorting? Back to <a href="../">the Object Explorer</a>.',
    '本站收录的 215 个天体的结构化数据，提供 JSON 与 CSV 两种格式下载。最近更新：2026-11-12。':
      'Structured data for all 215 objects in this catalogue, available as JSON and CSV. Last updated: 2026-11-12.',
    '数值数据整理自 NASA NSSDC / JPL / Wikipedia 等公开天文资料（公共领域或自由许可）；一句话简介为本站原创撰写。':
      'Numeric data compiled from NASA NSSDC / JPL / Wikipedia and other open sources (public domain or free licences); the one-line descriptions are written by this site.',
    '选择任意两个天体（可按类型筛选），下方会按真实直径比例绘制它们的球体，并列出体积、质量等关键数据的直观倍数。尺寸悬殊时较小的一方会按比例缩为一个点（附实际倍数说明），不再失真放大；本站收录的 177 个天体均可参与对比。':
      'Pick any two objects (filterable by type). Below they are drawn at their <strong>true diameter ratio</strong>, with intuitive ratios for volume, mass and other key figures. When sizes differ greatly the smaller one shrinks to <strong>a dot</strong> (with its actual ratio noted) rather than being enlarged; all 177 objects in this catalogue can be compared.',
    '下面是通过 iframe 嵌入的太阳系 3D 交互站主页（导航卡片）。首页列出「太阳系总览 / 地月 / 火星 / 木星 / 土星 / 天王星 / 海王星 / 冥王星」八个系统，点击任意卡片即可在下方窗口内直接打开对应系统，无需离开本页。点右上角「全屏」可铺满屏幕查看；手机端全屏建议横屏。':
      'Below is the <strong>home page</strong> of the Solar System 3D interactive site, embedded via <code>iframe</code> (navigation cards). It lists eight systems — Overview / Earth-Moon / Mars / Jupiter / Saturn / Uranus / Neptune / Pluto. <strong>Click any card to open that system in the frame below</strong> without leaving this page. Use the top-right "Fullscreen" button to fill the screen; landscape is recommended on phones.',
    '进入某个系统后，点上方「↺ 重新选择」可退回主页换另一个系统看。':
      'Inside a system, click "↺ Choose again" above to return to the home page and pick another system.',
    '鼠标拖拽旋转视角，滚轮缩放；悬停天体有白色描边，点击相机飞近并弹出资料卡。':
      'Drag to rotate, scroll to zoom; hovered objects get a white outline, and clicking flies the camera in and opens an info card.',
    '右上角面板可调节公转 / 自转速度、太阳亮度，以及「视觉放大 ×N」让小卫星清晰可见。':
      'The top-right panel adjusts orbital / rotation speed, solar brightness and "visual magnification ×N" to keep small moons visible.',
    '想更大？点「全屏」按钮，再点一次或按 Esc 退出。':
      'Want it larger? Click "Fullscreen", then click again or press Esc to exit.',
    '如果上面的窗口没有显示，可直接打开 astro-solar-3d.pages.dev。':
      'If the frame above does not load, open <a href="https://astro-solar-3d.pages.dev/">astro-solar-3d.pages.dev</a> directly.',
    '本页数据由仓库根目录的 universe-tree.json 驱动生成（经 scripts/universe_merge.py 按英文 id 唯一关联 universe-data.json 与 docs/data/astro.json）；数据源改动后随 mkdocs build 自动同步，无需手动操作。':
      'This page is generated from <code>universe-tree.json</code> in the repository root (<code>scripts/universe_merge.py</code> links <code>universe-data.json</code> and <code>docs/data/astro.json</code> by unique English id). Data changes sync automatically on <code>mkdocs build</code>.',
    '由外部 3D 项目（astro-solar-3d）提供，与本站数据独立维护；嵌入为精简界面，打开完整交互版 ↗。':
      'Provided by the external 3D project (astro-solar-3d), maintained separately from this site; embedded here as a compact view. <a href="https://astro-solar-3d.pages.dev/">Open the full interactive view ↗</a>.'
  };
  var BLOCK_SELECTOR = 'p, li, summary, blockquote, .solar-rotate, .astro-img-credit,' +
                       '.obj-summary, .obj-parent, .obj-viz-note, .obj-version';
  // 设计上刻意保留中文 / 不可见的元素，不算漏译
  var SKIP_SELECTOR = 'script,style,noscript,button,[data-cn-only],' +
                      '.astro-card-title .en,.obj-hero small';

  // 首页排序下拉：按 option 的 value 精确映射，绝不按显示文本猜测
  var SORT_OPTIONS = {
    name: 'Name', mass: 'Mass ↓', radius: 'Diameter ↓', density: 'Density ↓',
    temp: 'Surface temperature ↓', period: 'Orbital period ↓', moons: 'Moon count ↓'
  };

  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, OPTION: 1, CODE: 1, PRE: 1 };
  // 这些容器由业务脚本 / swapNames 独占管理，通用文本替换必须让路，
  // 否则会出现「先按中文映射改一遍、业务脚本又重渲染一遍」的互相覆盖。
  // 带 data-en 的元素由 translateDataEn() 按属性精确接管，同样跳过。
  var MANAGED = '.astro-card-title, .obj-hero h1, .astro-badge, .astro-card-tagline,' +
                '.obj-tagline, #astro-count, #uh, .sizecmp-viz-note,' +
                '.sizecmp-detail, .sizecmp-ratios, .sizecmp-share, .sizecmp-viz-canvas';
  var ATTRS = ['placeholder', 'title', 'aria-label', 'alt'];

  var lang = 'zh';
  try {
    var saved = localStorage.getItem(STORE_KEY);
    if (saved === 'en' || saved === 'zh') lang = saved;
  } catch (e) { /* 隐私模式忽略 */ }

  var textOrig = new WeakMap();
  var nameOrig = new WeakMap();   // swapNames 专用：与通用文本节点缓存隔离
  var attrOrig = new WeakMap();
  var blockOrig = new WeakMap();  // 块级文案：缓存原始 innerHTML，保证可逆
  var dataEnOrig = new WeakMap(); // data-en 元素：独立缓存，避免与块级缓存串味
  var listeners = [];
  var unmatched = [];             // 译表漂移检测：含中文却未登记的静态块

  function siteT(key) {
    var pair = UI[key];
    if (!pair) return key;
    return pair[lang === 'en' ? 1 : 0];
  }

  function currentHtmlLang() { return lang === 'en' ? 'en' : 'zh'; }

  // ---------------------------------------------------------------- 文本节点
  function translateText(root) {
    var walker = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT, null);
    var nodes = [], n;
    while ((n = walker.nextNode())) nodes.push(n);
    nodes.forEach(function (node) {
      var p = node.parentElement;
      if (!p || SKIP_TAGS[p.tagName]) return;
      if (p.closest(MANAGED) || p.closest('[data-i18n-block]') ||
          p.closest('[data-en],[data-en-html]')) return;
      if (!textOrig.has(node)) textOrig.set(node, node.nodeValue);
      var orig = textOrig.get(node);
      if (lang !== 'en') { node.nodeValue = orig; return; }
      var key = orig.trim();
      var out = null;
      if (Object.prototype.hasOwnProperty.call(ZH2EN, key)) {
        out = ZH2EN[key];
      } else {
        // 长文本可能同时命中多条规则（如「数据版本 v1.9 · 收录 177 个天体…」），
        // 逐条累积替换；一条都没命中就原样保留。
        var acc = orig, changed = false;
        for (var i = 0; i < PATTERNS.length; i++) {
          var rule = PATTERNS[i];
          var hit = acc.match(rule[0]);
          if (!hit) continue;
          acc = typeof rule[1] === 'function'
            ? rule[1].apply(null, hit)
            : acc.replace(rule[0], rule[1]);
          changed = true;
        }
        if (changed) { node.nodeValue = acc; return; }
      }
      node.nodeValue = out === null ? orig : orig.replace(key, out);
    });
  }

  function translateAttrs(root) {
    Array.prototype.forEach.call((root || document.body).querySelectorAll('[' + ATTRS.join('],[') + ']'), function (el) {
      if (!attrOrig.has(el)) {
        var snap = {};
        ATTRS.forEach(function (a) { if (el.hasAttribute(a)) snap[a] = el.getAttribute(a); });
        attrOrig.set(el, snap);
      }
      var snap = attrOrig.get(el);
      ATTRS.forEach(function (a) {
        if (!Object.prototype.hasOwnProperty.call(snap, a)) return;
        var orig = snap[a];
        if (lang !== 'en') { el.setAttribute(a, orig); return; }
        var val = ZH2EN[orig.trim()];
        if (val) el.setAttribute(a, orig.replace(orig.trim(), val));
      });
    });
  }

  // 块级静态文案：按规范化 textContent 精确整串匹配 BLOCKS，命中后整块换成英文
  // HTML（可含链接/加粗/code），并缓存原 innerHTML 保证可逆。未命中的含中文静态块
  // 记入 unmatched，供回归做「译表漂移检测」。
  function normText(s) { return (s || '').replace(/\s+/g, ' ').trim(); }

  function translateBlocks(root) {
    var scope = root || document.body;
    unmatched = [];
    Array.prototype.forEach.call(scope.querySelectorAll(BLOCK_SELECTOR), function (el) {
      // 父级块已被接管时，内部子元素必须跳过，否则会把父级写进去的英文
      // 当成子元素「原文」缓存，切回中文时错误恢复成英文。
      var owner = el.closest('[data-i18n-block]');
      if (owner && owner !== el) return;
      if (el.closest(MANAGED) || el.hasAttribute('data-en') || el.hasAttribute('data-en-html')) return;
      // 整块内容都由子元素上的 data-en 接管时（如文章列表 <li><a data-en>），
      // 不要再当静态块处理，否则会误报漂移、也可能把英文缓存成「原文」。
      var managedChild = Array.prototype.some.call(el.children, function (c) {
        return c.hasAttribute('data-en') || c.hasAttribute('data-en-html');
      });
      if (managedChild) return;
      if (!blockOrig.has(el)) blockOrig.set(el, el.innerHTML);
      var original = blockOrig.get(el);
      // 用缓存的原文算 key，避免切换语言后 textContent 变化导致二次匹配失败
      var probe = document.createElement('div');
      probe.innerHTML = original;
      var key = normText(probe.textContent);
      var en = BLOCKS[key];
      if (lang !== 'en') {
        if (el.hasAttribute('data-i18n-block')) {
          el.innerHTML = original;
          el.removeAttribute('data-i18n-block');
        }
        return;
      }
      if (en) {
        el.innerHTML = en;
        el.setAttribute('data-i18n-block', '1');
      } else {
        el.removeAttribute('data-i18n-block');
      }
    });
  }

  // 首页排序下拉：按 option.value 精确映射；compare.js 自建的 select 没有这些 value
  function translateOptions(root) {
    var sel = (root || document.body).querySelector('#astro-sort');
    if (!sel) return;
    Array.prototype.forEach.call(sel.options, function (op) {
      var en = SORT_OPTIONS[op.value];
      if (!en) return;
      if (!attrOrig.has(op)) attrOrig.set(op, { text: op.textContent });
      op.textContent = lang === 'en' ? en : attrOrig.get(op).text;
    });
  }

  function translateCells(root) {
    // 只在英文模式下对「当前文本」做一次有界单位换算。
    // 切回中文时 translateText 已从 textOrig 恢复原文，这里必须什么都不做，
    // 否则会再次从缓存原文重算并覆盖掉已翻译的整串文案。
    if (lang !== 'en') return;
    Array.prototype.forEach.call((root || document.body).querySelectorAll(CELL_SELECTOR), function (el) {
      var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
      var nodes = [], n;
      while ((n = walker.nextNode())) nodes.push(n);
      nodes.forEach(function (node) {
        if (!node.parentElement || SKIP_TAGS[node.parentElement.tagName]) return;
        var out = node.nodeValue;
        CELL_SUB.forEach(function (rule) { out = out.replace(rule[0], rule[1]); });
        node.nodeValue = out;
      });
    });
  }

  // data-en / data-en-html：生成模板里直接写好的英文文案，按属性精确关联。
  // 含动态数字（如「177 个天体」）的段落用这个，避免译表 key 随数字变化而失配。
  function applyDataEn(root) {
    var scope = root || document.body;
    Array.prototype.forEach.call(scope.querySelectorAll('[data-en],[data-en-html]'), function (el) {
      if (!dataEnOrig.has(el)) dataEnOrig.set(el, el.innerHTML);
      var original = dataEnOrig.get(el);
      if (lang !== 'en') { el.innerHTML = original; return; }
      var html = el.getAttribute('data-en-html');
      if (html !== null) el.innerHTML = html;
      else el.textContent = el.getAttribute('data-en');
    });
  }

  // 译表漂移检测：所有翻译手段（BLOCKS / ZH2EN / PATTERNS / CELL_SUB / data-en /
  // 业务脚本）都跑完后，仍含中文的静态说明块才算真漏译。放在末尾统一判定，
  // 避免把「由正则或词表在文本节点层翻译的块」误报成漂移。
  function detectDrift() {
    unmatched = [];
    if (lang === 'en') {
      Array.prototype.forEach.call(document.querySelectorAll(BLOCK_SELECTOR), function (el) {
        var owner = el.closest('[data-i18n-block]');
        if (owner && owner !== el) return;
        if (el.closest(MANAGED) || el.hasAttribute('data-en') ||
            el.hasAttribute('data-en-html') || el.closest(SKIP_SELECTOR)) return;
        var key = normText(el.textContent);
        if (key.length > 6 && /[\u4e00-\u9fff]/.test(key)) unmatched.push(key.slice(0, 90));
      });
    }
    window.SITE_I18N_UNMATCHED = unmatched.slice();
  }

  // ---------------------------------------------------------------- 名称互换
  // 保留原有「主名 + 小字别名」的版式，只交换主次：中文模式 中文/English，
  // 英文模式 English/中文。零改动生成模板，且不丢失任何一侧文字。
  function swapNames(root) {
    var scope = root || document.body;
    Array.prototype.forEach.call(scope.querySelectorAll('.astro-card-title'), function (el) {
      var first = el.firstChild;
      var alt = el.querySelector('.en');
      if (!first || first.nodeType !== 3 || !alt) return;
      if (!nameOrig.has(first)) nameOrig.set(first, { zh: first.nodeValue, en: alt.textContent });
      var pair = nameOrig.get(first);
      first.nodeValue = lang === 'en' ? pair.en : pair.zh;
      alt.textContent = lang === 'en' ? pair.zh.trim() : pair.en;
    });
    Array.prototype.forEach.call(scope.querySelectorAll('.obj-hero h1'), function (el) {
      var small = el.querySelector('small');
      if (!small) return;
      var first = el.firstChild;
      if (!first || first.nodeType !== 3) return;
      if (!nameOrig.has(first)) nameOrig.set(first, { zh: first.textContent, en: small.textContent });
      var pair = nameOrig.get(first);
      first.textContent = (lang === 'en' ? pair.en : pair.zh) + ' ';
      small.textContent = lang === 'en' ? pair.zh.trim() : pair.en.trim();
    });
    // 分类徽章按 class 映射，避免依赖中文文本
    Array.prototype.forEach.call(scope.querySelectorAll('.astro-badge'), function (el) {
      var key = (el.className.match(/\b(star|planet|moon|galaxy|nebula|cluster|dwarf_planet|asteroid|black_hole|structure|comet)\b/) || [])[1];
      if (!key || !CATS[key]) return;
      if (!nameOrig.has(el)) nameOrig.set(el, el.textContent);
      el.textContent = lang === 'en' ? CATS[key][1] : nameOrig.get(el);
    });
    // tagline：按 id 从 i18n-data.js 取译稿（卡片由 href 定位，详情页由路径定位）
    Array.prototype.forEach.call(scope.querySelectorAll('.astro-card-link'), function (link) {
      var m = (link.getAttribute('href') || '').match(/objects\/([^/]+)\//);
      var tag = link.querySelector('.astro-card-tagline');
      if (!m || !tag) return;
      var pair = (D.taglines || {})[m[1]];
      if (!pair) return;
      if (!nameOrig.has(tag)) nameOrig.set(tag, tag.textContent);
      tag.textContent = (lang === 'en' && pair[1]) ? pair[1] : nameOrig.get(tag);
    });
    Array.prototype.forEach.call(scope.querySelectorAll('.obj-tagline'), function (el) {
      // 详情页由 gen_pages.py 显式输出 data-obj-id；URL 正则仅作旧产物兜底
      var oid = el.getAttribute('data-obj-id');
      if (!oid) {
        var m = location.pathname.match(/objects\/([^/]+)\/?$/);
        oid = m && m[1];
      }
      var pair = oid && (D.taglines || {})[oid];
      if (!pair) return;
      if (!nameOrig.has(el)) nameOrig.set(el, el.textContent);
      el.textContent = (lang === 'en' && pair[1]) ? pair[1] : nameOrig.get(el);
    });
  }

  // ---------------------------------------------------------------- 顶栏按钮
  function mountLangButton() {
    var palette = document.querySelector('form[data-md-component="palette"]');
    if (!palette || document.getElementById('site-lang-btn')) return;
    var wrap = document.createElement('div');
    wrap.className = 'md-header__option site-lang-option';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'site-lang-btn';
    btn.className = 'md-header__button site-lang-btn';
    btn.innerHTML = '<span class="sl-zh">中</span><span class="sl-sep">/</span><span class="sl-en">EN</span>';
    btn.addEventListener('click', function () { setSiteLang(lang === 'zh' ? 'en' : 'zh'); });
    wrap.appendChild(btn);
    palette.parentNode.insertBefore(wrap, palette);
    updateLangButton();
  }

  function updateLangButton() {
    var btn = document.getElementById('site-lang-btn');
    if (!btn) return;
    btn.classList.toggle('is-en', lang === 'en');
    btn.setAttribute('aria-label', siteT('langTitle'));
    btn.setAttribute('title', siteT('langTitle'));
  }

  function applyAll() {
    document.documentElement.setAttribute('data-lang', lang);
    document.documentElement.setAttribute('lang', currentHtmlLang());
    translateBlocks(document.body);   // 先整块精确替换，命中的节点由 translateText 跳过
    translateText(document.body);
    translateAttrs(document.body);
    translateCells(document.body);
    translateOptions(document.body);
    swapNames(document.body);
    applyDataEn(document.body);
    updateLangButton();
    // 业务脚本通过 site:langchange 重渲染，需要在事件之后再判定漂移；
    // 但 boot 的首次 applyAll 未派发事件，这里先记一次，load 阶段会再覆盖。
    detectDrift();
    // 搜索框由 Material 动态注入，可能在首轮之后才出现
    var search = document.querySelector('.md-search__input');
    if (search && lang === 'en') search.setAttribute('placeholder', siteT('search'));
  }

  function setSiteLang(next, silent) {
    if (next !== 'zh' && next !== 'en') return;
    lang = next;
    window.SITE_LANG = lang;
    try { localStorage.setItem(STORE_KEY, lang); } catch (e) { /* ignore */ }
    applyAll();
    if (!silent) {
      document.dispatchEvent(new CustomEvent('site:langchange', { detail: { lang: lang } }));
    }
    // 业务脚本在 site:langchange 里重渲染，必须在事件之后再判定一次漂移
    detectDrift();
  }

  function onSiteLang(fn) { if (typeof fn === 'function') listeners.push(fn); }
  document.addEventListener('site:langchange', function (e) {
    listeners.forEach(function (fn) { try { fn(e.detail.lang); } catch (err) { /* ignore */ } });
  });

  window.SITE_LANG = lang;
  window.siteT = siteT;
  window.siteCat = function (key) { return CATS[key] ? CATS[key][lang === 'en' ? 1 : 0] : key; };
  window.siteName = function (id) {
    var p = (D.names || {})[id];
    return p ? p[lang === 'en' ? 1 : 0] : id;
  };
  window.setSiteLang = setSiteLang;
  window.onSiteLang = onSiteLang;
  window.applyI18n = applyAll;

  function boot() {
    mountLangButton();
    applyAll();
    // 页面内嵌脚本（宇宙层级页）比 extra_javascript 先执行，读到的仍是默认 zh。
    // 若用户已选英文，补发一次事件让各页按当前语言重渲染（不重复写 localStorage）。
    if (lang === 'en') {
      document.dispatchEvent(new CustomEvent('site:langchange', { detail: { lang: lang } }));
      detectDrift();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  window.addEventListener('load', function () { mountLangButton(); applyAll(); });
})();
