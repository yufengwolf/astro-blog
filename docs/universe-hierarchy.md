---
title: 宇宙天体层级
hide:
  - toc
---

<p id="uh-intro">下面按「引力从属 / 包含关系」组织的天体层级思维导图，从「可观测宇宙」一路下钻到行星、卫星、星团与星云。层级数据由 universe-data.json 提供，天体详情与仓库数据（astro.json）按英文 id 唯一关联；命名遵循统一规范，类型与归属严格按天体真实性质挂接。名称右侧带 ↗ 的节点可跳转本站详情卡片；搜索支持中文名、英文名与 M/NGC 等规范编号，右上角可切换中文 / EN。</p>

<section id="uh" class="uh" data-lang="zh">
  <div class="uh-bar">
    <label class="uh-search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>
      <input id="uh-q" type="text" placeholder="搜索天体名称 / 类型 / 英文名…" autocomplete="off">
    </label>
    <button class="uh-btn" id="uh-expand">展开全部</button>
    <button class="uh-btn" id="uh-collapse">折叠全部</button>
  </div>
  <div class="uh-chips" id="uh-chips"></div>
  <div class="uh-crumb" id="uh-crumb"></div>
  <div class="uh-tree" id="uh-tree"></div>
  <div class="uh-legend" id="uh-legend"></div>
</section>

<style>
.uh-bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:4px 0 8px}
.uh-search{flex:1 1 240px;min-width:200px;display:flex;align-items:center;gap:8px;
  background:var(--md-default-fg-color--lightest,rgba(125,125,125,.10));
  border:1px solid var(--md-default-fg-color--lightest,rgba(125,125,125,.16));
  border-radius:8px;padding:8px 12px;transition:.15s}
.uh-search:focus-within{border-color:var(--md-accent-fg-color,#7c4dff);
  background:var(--md-default-fg-color--lighter,rgba(125,125,125,.14))}
.uh-search svg{width:16px;height:16px;fill:var(--md-default-fg-color--light,#9aa6c4);flex:none}
.uh-search input{flex:1;background:transparent;border:0;outline:0;
  color:var(--md-default-fg-color,#e6edf6);font-size:.9rem;font-family:inherit}
.uh-btn{background:var(--md-default-fg-color--lightest,rgba(125,125,125,.10));
  border:1px solid var(--md-default-fg-color--lightest,rgba(125,125,125,.16));
  color:var(--md-default-fg-color,#e6edf6);border-radius:8px;padding:7px 12px;cursor:pointer;
  font-size:.85rem;font-family:inherit;transition:.15s}
.uh-btn:hover{background:var(--md-default-fg-color--lighter,rgba(125,125,125,.18));
  border-color:var(--md-accent-fg-color,#7c4dff)}
.uh-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.uh-chip{font-size:.75rem;padding:4px 10px;border-radius:999px;
  border:1px solid var(--md-default-fg-color--lightest,rgba(125,125,125,.16));
  background:var(--md-default-fg-color--lightest,rgba(125,125,125,.10));
  color:var(--md-default-fg-color--light,#9aa6c4);cursor:pointer;user-select:none;
  transition:.15s;display:flex;align-items:center;gap:5px}
.uh-chip .uh-dot{width:8px;height:8px;border-radius:50%}
.uh-chip.on{color:var(--md-accent-fg-color,#7c4dff);border-color:var(--md-accent-fg-color,#7c4dff);
  background:color-mix(in srgb,var(--md-accent-fg-color,#7c4dff) 16%,transparent)}
.uh-crumb{margin:14px 0 6px;font-size:.75rem;color:var(--md-default-fg-color--light,#9aa6c4);
  min-height:18px;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.uh-crumb b{color:var(--md-primary-fg-color,#7c4dff)}
.uh-crumb .uh-sep{opacity:.5}
.uh-tree{margin-top:6px}
.uh-node{position:relative}
.uh-children{margin-left:14px;padding-left:12px;
  border-left:1px solid var(--md-default-fg-color--lightest,rgba(125,125,125,.18))}
.uh-children.collapsed{display:none}
.uh-head{display:flex;align-items:center;gap:7px;padding:5px 8px;border-radius:7px;
  cursor:pointer;transition:.12s;line-height:1.3}
.uh-head:hover{background:var(--md-default-fg-color--lightest,rgba(125,125,125,.08))}
.uh-arrow{width:16px;height:16px;flex:none;display:inline-flex;align-items:center;justify-content:center;
  fill:var(--md-default-fg-color--light,#9aa6c4);transition:transform .15s}
.uh-arrow svg{width:14px;height:14px;display:block}
.uh-arrow.leaf{opacity:0}
.uh-arrow.open{transform:rotate(90deg)}
.uh-nm{font-weight:600;color:var(--md-default-fg-color,#e6edf6)}
.uh-alias{font-weight:400;font-size:.78rem;margin-left:6px;
  color:var(--md-default-fg-color--light,#9aa6c4);opacity:.85}
[data-lang="en"] .uh-alias[data-cn-only]{display:none}
.uh-nm a{color:inherit;text-decoration:none}
.uh-nm a:hover{text-decoration:underline}
.uh-badge{font-size:.7rem;padding:1px 8px;border-radius:999px;color:#10202b;font-weight:700;white-space:nowrap}
.uh-link{flex:none;margin-left:6px;color:var(--md-accent-fg-color,#7c4dff);font-size:.8rem;
  text-decoration:none;opacity:.65;transition:.15s}
.uh-link:hover{opacity:1;text-decoration:underline}
.uh-cnt{font-size:.7rem;color:var(--md-default-fg-color--light,#9aa6c4);margin-left:auto;flex:none}
.uh-nm mark{background:var(--md-primary-fg-color,#7c4dff);color:#fff;border-radius:3px;padding:0 1px}
.uh-empty{color:var(--md-default-fg-color--light,#9aa6c4);text-align:center;padding:30px;font-size:.85rem}
.uh-legend{margin-top:22px;border-top:1px solid var(--md-default-fg-color--lightest,rgba(125,125,125,.18));
  padding-top:12px;display:flex;flex-wrap:wrap;gap:10px;font-size:.7rem;color:var(--md-default-fg-color--light,#9aa6c4)}
.uh-legend span{display:flex;align-items:center;gap:5px}
.uh-legend i{width:9px;height:9px;border-radius:50%;display:inline-block}
@media (max-width:560px){
  .uh-children{margin-left:9px;padding-left:9px}
}
</style>

<script id="uh-data" type="application/json">{"_convention":["一、事实源分工：本文件是「宇宙层级」的**层级拓扑**事实源，定义节点位置、容器与归属；天体的中文名、英文名、物理属性与来源一律以 docs/data/astro.json 为唯一事实源。天体节点在本文件保留 name / name_en 仅作人审阅镜像，须与 astro.json 字节级一致（融合脚本强校验），不得作为关联依据。","二、稳定 id：每个节点必须有 id，全局唯一、仅 ASCII [a-z0-9._-]、一经确定不再改动。本站天体节点的 id 等于 astro.json 的 id；层级容器与本站未收录天体使用 c. 前缀命名空间。id 不随任何语言翻译改变。","三、唯一匹配：融合只按 id 做双向 1:1 精确关联，禁止 lower / 去空白 / 去括号 / 星尾差异 / alias 兜底等任何名称模糊匹配。id 缺失、重复或找不到对应天体立即报错，改数据而不放宽匹配。","四、编号天体：有通用中文名的用「中文名（编号）」，例如 猎户座大星云（M42）；无通用中文名、仅星表编号的用「编号（中文类别）」，例如 M5（球状星团）。编号放 alias，不参与匹配。","五、大小写有语义：多星系统成员用「系统名 + 大写字母」（天狼星A、南门二B），系外行星用「宿主名 + 小写字母」（比邻星b、开普勒16b）。大小写不可忽略，但大小写只影响展示，不影响 id 关联。","六、天然卫星用「主星简称 + 卫 + 中文序号（西方名）」，例如 木卫一（伊奥）；引力波事件、类星体等非正式天体须显式标注性质。","七、格式：括号统一全角「（）」；名称内禁止斜杠「/」；罗马数字用半角 I/II/III；拉丁编号与序号间保留一个半角空格（IC 10、NGC 147），中文与类别词之间不加空格。","八、type 只写纯粹类型名（光谱型/形态/类别），补充说明与不确定表述一律放 info；category 取自受控词表：宇宙结构/星系/星云/恒星/行星/卫星/星团/矮行星/小行星/彗星/黑洞/其他。顶层 type_i18n / category_i18n 为对应英文词表，全节点共用。","九、双语：每个节点都有 name_en（本站天体镜像自 astro.json.name_en，容器在本文件定义）；alias 为通用编号不翻译。页面按语言切换展示，切换只读取双语字段，不依赖任何名称匹配。","十、归属严格：每个节点的父节点必须反映真实引力从属或包含关系。已确证的精确挂接；无确证依据的放进明确标注「归属未细化」的容器，绝不按类别臆测塞进某个超星系团或旋臂。改任一数据源后随 mkdocs build 自动重生页面。","十一、非结构区块：不属于引力束缚宇宙结构的内容（如宇宙微波背景、引力波探测事件、遥远类星体/AGN）统一放入顶层 non_structure 数组，由页面单独渲染为「非结构·宇宙学现象」区块，不参与主层级树的搜索/筛选/折叠。"],"type_i18n":{"天然卫星":"Natural Satellite","系外行星":"Exoplanet","疏散星团":"Open Cluster","发射星云":"Emission Nebula","矮行星":"Dwarf Planet","旋涡星系":"Spiral Galaxy","红超巨星":"Red Supergiant","球状星团":"Globular Cluster","A 型主序星":"A-type Main Sequence Star","类地行星":"Terrestrial Planet","M 型矮星":"M-type Dwarf","B 型主序星":"B-type Main Sequence Star","红矮星":"Red Dwarf","G 型主序星":"G-type Main Sequence Star","行星状星云":"Planetary Nebula","星系群":"Galaxy Group","超大质量黑洞":"Supermassive Black Hole","主旋臂":"Major Spiral Arm","高光度蓝变星":"Luminous Blue Variable","小行星":"Asteroid","双星系统":"Binary Star System","白矮星":"White Dwarf","红巨星":"Red Giant","F 型超巨星":"F-type Supergiant","K 型主序星":"K-type Main Sequence Star","脉冲星行星":"Pulsar Planet","恒星级黑洞":"Stellar-Mass Black Hole","不规则矮星系":"Irregular Dwarf Galaxy","矮椭球星系":"Dwarf Spheroidal Galaxy","富星系团":"Rich Galaxy Cluster","巨椭圆星系":"Giant Elliptical Galaxy","超星系团":"Supercluster","棒旋星系":"Barred Spiral Galaxy","恒星系统":"Stellar System","行星分组":"Planetary Group","气态巨行星":"Gas Giant","冰巨行星":"Ice Giant","恒星分组":"Stellar Group","K1V 橙矮星":"K1V Orange Dwarf","G 型巨星":"G-type Giant","天体分组":"Object Group","蓝超巨星":"Blue Supergiant","脉冲星":"Pulsar","B 型超巨星":"B-type Supergiant","食双星":"Eclipsing Binary","星团分组":"Cluster Group","矮椭圆卫星星系":"Dwarf Elliptical Satellite Galaxy","矮椭球卫星星系":"Dwarf Spheroidal Satellite Galaxy","矮椭圆星系":"Dwarf Elliptical Galaxy","类星体":"Quasar","引力波事件":"Gravitational-Wave Event","宇宙边界":"Cosmic Boundary","超星系团复合体":"Supercluster Complex","星系核心区域":"Galactic Core Region","星系盘":"Galactic Disk","亮巨星":"Bright Giant","次级旋臂":"Minor Spiral Arm","G2V 黄矮星":"G2V Yellow Dwarf","小行星带":"Asteroid Belt","原行星":"Protoplanet","外海王星天体带":"Trans-Neptunian Belt","彗星储库":"Comet Reservoir","彗星":"Comet","半人马小行星":"Centaur Asteroid","三合星系统":"Triple Star System","G2V 主序星":"G2V Main Sequence Star","M5.5V 红矮星":"M5.5V Red Dwarf","M4V 红矮星":"M4V Red Dwarf","A1V 主序星":"A1V Main Sequence Star","F5IV 主序星":"F5IV Main Sequence Star","A0V 主序星":"A0V Main Sequence Star","A7V 主序星":"A7V Main Sequence Star","四合星系统":"Quadruple Star System","六合星系统":"Sextuple Star System","M 型红矮星":"M-type Red Dwarf","旋臂":"Spiral Arm","磁星":"Magnetar","K 型巨星":"K-type Giant","M 型红巨星":"M-type Red Giant","米拉变星":"Mira Variable","O 型星":"O-type Star","星云分组":"Nebula Group","超新星遗迹":"Supernova Remnant","反射星云":"Reflection Nebula","暗星云":"Dark Nebula","恒星系统分组":"Stellar System Group","主序星":"Main Sequence Star","脉冲星系统":"Pulsar System","黑洞分组":"Black Hole Group","星系晕":"Galactic Halo","卫星星系分组":"Satellite Galaxy Group","沃尔夫-拉叶星":"Wolf-Rayet Star","矮不规则星系":"Dwarf Irregular Galaxy","星暴星系":"Starburst Galaxy","透镜状星系":"Lenticular Galaxy","引力异常区域":"Gravitational Anomaly Region","星系分组":"Galaxy Grouping","相互作用星系":"Interacting Galaxy","致密星系群":"Compact Galaxy Group","超巨椭圆星系":"Supergiant Elliptical Galaxy","耀变体":"Blazar","活动星系核":"Active Galactic Nucleus","事件分组":"Event Group","巨型宇宙纤维":"Giant Cosmic Filament","宇宙背景辐射":"Cosmic Background Radiation","椭圆星系":"Elliptical Galaxy"},"category_i18n":{"宇宙结构":"Cosmic Structure","星系":"Galaxy","星云":"Nebula","恒星":"Star","行星":"Planet","卫星":"Moon","星团":"Cluster","矮行星":"Dwarf Planet","小行星":"Asteroid","彗星":"Comet","黑洞":"Black Hole","其他":"Other"},"id":"observable_universe","name":"可观测宇宙","name_en":"Observable Universe","type":"宇宙边界","category":"宇宙结构","info":"半径约 465 亿光年，基于 ΛCDM 标准宇宙学模型","source":"NASA / ΛCDM","children":[{"id":"c.pisces-cetus-supercluster-complex","name":"双鱼-鲸鱼座超星系团复合体","name_en":"Pisces-Cetus Supercluster Complex","type":"超星系团复合体","category":"宇宙结构","info":"拉尼亚凯亚超星系团所属的更大尺度纤维结构","source":"Tully et al. 2014","children":[{"id":"laniakea","name":"拉尼亚凯亚超星系团","name_en":"Laniakea Supercluster","type":"超星系团","category":"宇宙结构","info":"引力中心为巨引源；包含本星系群、室女座星系团、M81 星系群等","source":"Tully et al. 2014","children":[{"id":"local_group","name":"本星系群","name_en":"Local Group","type":"星系群","category":"宇宙结构","info":"约 50 余个星系，无中心巨椭圆星系","source":"NASA","children":[{"id":"milky_way","name":"银河系","name_en":"Milky Way","type":"棒旋星系","category":"星系","info":"直径约 10 万光年，包含数千亿颗恒星","source":"ESA","children":[{"id":"c.galactic-center","name":"银核","name_en":"Galactic Center","type":"星系核心区域","category":"宇宙结构","info":"高密度恒星核心，包含中心超大质量黑洞","source":"EHT","children":[{"id":"sgr_a_star","name":"人马座A*","name_en":"Sagittarius A*","type":"超大质量黑洞","category":"黑洞","alias":"Sgr A*","info":"银河系中心黑洞，约 430 万倍太阳质量","source":"EHT 2022","repo_id":"sgr_a_star"}]},{"id":"c.galactic-disk","name":"银盘","name_en":"Galactic Disk","type":"星系盘","category":"宇宙结构","info":"银河系恒星、星云主要分布区域，分为多条旋臂","source":"ESA","children":[{"id":"c.scutum-centaurus-arm","name":"盾牌-半人马臂","name_en":"Scutum-Centaurus Arm","type":"主旋臂","category":"宇宙结构","info":"银河系内侧主旋臂","children":[{"id":"eta_carinae","name":"海山二","name_en":"Eta Carinae","type":"高光度蓝变星","category":"恒星","info":"双星系统；质量巨大、极不稳定，光度极高","source":"ESA","repo_id":"eta_carinae"},{"id":"canopus","name":"老人星","name_en":"Canopus","type":"亮巨星","category":"恒星","info":"全天第二亮恒星，光谱型 A9 II","source":"NASA","repo_id":"canopus"}]},{"id":"c.perseus-arm","name":"英仙臂","name_en":"Perseus Arm","type":"主旋臂","category":"宇宙结构","info":"外侧主旋臂，含大量亮星云与星团","children":[{"id":"c.m36-open-cluster","name":"M36（疏散星团）","name_en":"M36 (Open Cluster)","type":"疏散星团","category":"星团","alias":"M36","info":"年轻疏散星团"},{"id":"c.m37-open-cluster","name":"M37（疏散星团）","name_en":"M37 (Open Cluster)","type":"疏散星团","category":"星团","alias":"M37","info":"银河系最富疏散星团之一"},{"id":"c.m38-open-cluster","name":"M38（疏散星团）","name_en":"M38 (Open Cluster)","type":"疏散星团","category":"星团","alias":"M38"}]},{"id":"c.orion-arm-local-spur","name":"猎户臂（本地臂）","name_en":"Orion Arm (Local Spur)","type":"次级旋臂","category":"宇宙结构","info":"太阳所在的次级旋臂","source":"NASA","children":[{"id":"c.solar-system","name":"太阳系统","name_en":"Solar System","type":"恒星系统","category":"宇宙结构","info":"G2V 黄矮星太阳的引力系统","source":"NASA","children":[{"id":"sun","name":"太阳","name_en":"Sun","type":"G2V 黄矮星","category":"恒星","info":"太阳系中心恒星，独占太阳系总质量 99.86%","repo_id":"sun"},{"id":"c.inner-planetary-system","name":"内行星系统","name_en":"Inner Planetary System","type":"行星分组","category":"宇宙结构","children":[{"id":"mercury","name":"水星","name_en":"Mercury","type":"类地行星","category":"行星","info":"无卫星","repo_id":"mercury"},{"id":"venus","name":"金星","name_en":"Venus","type":"类地行星","category":"行星","info":"无卫星","repo_id":"venus"},{"id":"earth","name":"地球","name_en":"Earth","type":"类地行星","category":"行星","children":[{"id":"moon","name":"月球","name_en":"Moon","type":"天然卫星","category":"卫星","repo_id":"moon"}],"repo_id":"earth"},{"id":"mars","name":"火星","name_en":"Mars","type":"类地行星","category":"行星","children":[{"id":"phobos","name":"火卫一","name_en":"Phobos","type":"天然卫星","category":"卫星","alias":"福波斯","repo_id":"phobos"},{"id":"deimos","name":"火卫二","name_en":"Deimos","type":"天然卫星","category":"卫星","alias":"德莫斯","repo_id":"deimos"}],"repo_id":"mars"}]},{"id":"c.main-asteroid-belt","name":"主小行星带","name_en":"Main Asteroid Belt","type":"小行星带","category":"宇宙结构","children":[{"id":"ceres","name":"谷神星","name_en":"Ceres","type":"矮行星","category":"矮行星","repo_id":"ceres"},{"id":"vesta","name":"灶神星","name_en":"4 Vesta","type":"原行星","category":"小行星","repo_id":"vesta"},{"id":"pallas","name":"智神星","name_en":"Pallas","type":"小行星","category":"小行星","repo_id":"pallas"},{"id":"juno","name":"婚神星","name_en":"Juno","type":"小行星","category":"小行星","repo_id":"juno"},{"id":"hygiea","name":"健神星","name_en":"Hygiea","type":"小行星","category":"小行星","repo_id":"hygiea"}]},{"id":"c.outer-planetary-system","name":"外行星系统","name_en":"Outer Planetary System","type":"行星分组","category":"宇宙结构","children":[{"id":"jupiter","name":"木星","name_en":"Jupiter","type":"气态巨行星","category":"行星","info":"已知卫星极多，此处列出知名大卫星","children":[{"id":"io","name":"木卫一","name_en":"Io","type":"天然卫星","category":"卫星","alias":"伊奥","repo_id":"io"},{"id":"europa","name":"木卫二","name_en":"Europa","type":"天然卫星","category":"卫星","alias":"欧罗巴","repo_id":"europa"},{"id":"ganymede","name":"木卫三","name_en":"Ganymede","type":"天然卫星","category":"卫星","alias":"盖尼米德","repo_id":"ganymede"},{"id":"callisto","name":"木卫四","name_en":"Callisto","type":"天然卫星","category":"卫星","alias":"卡利斯托","repo_id":"callisto"},{"id":"amalthea","name":"木卫五","name_en":"Amalthea","type":"天然卫星","category":"卫星","alias":"阿马尔忒亚","repo_id":"amalthea"},{"id":"himalia","name":"木卫六","name_en":"Himalia","type":"天然卫星","category":"卫星","alias":"希玛利亚","repo_id":"himalia"},{"id":"elara","name":"木卫七","name_en":"Elara","type":"天然卫星","category":"卫星","alias":"伊拉拉","repo_id":"elara"},{"id":"pasiphae","name":"木卫八","name_en":"Pasiphae","type":"天然卫星","category":"卫星","alias":"帕西法尔","repo_id":"pasiphae"}],"repo_id":"jupiter"},{"id":"saturn","name":"土星","name_en":"Saturn","type":"气态巨行星","category":"行星","info":"行星环系统，卫星数量极多，列出经典知名卫星","children":[{"id":"titan","name":"土卫六","name_en":"Titan","type":"天然卫星","category":"卫星","alias":"泰坦","repo_id":"titan"},{"id":"enceladus","name":"土卫二","name_en":"Enceladus","type":"天然卫星","category":"卫星","alias":"恩克拉多斯","repo_id":"enceladus"},{"id":"mimas","name":"土卫一","name_en":"Mimas","type":"天然卫星","category":"卫星","alias":"弥玛斯","repo_id":"mimas"},{"id":"tethys","name":"土卫三","name_en":"Tethys","type":"天然卫星","category":"卫星","alias":"忒堤斯","repo_id":"tethys"},{"id":"dione","name":"土卫四","name_en":"Dione","type":"天然卫星","category":"卫星","alias":"狄俄涅","repo_id":"dione"},{"id":"rhea","name":"土卫五","name_en":"Rhea","type":"天然卫星","category":"卫星","alias":"瑞亚","repo_id":"rhea"},{"id":"iapetus","name":"土卫八","name_en":"Iapetus","type":"天然卫星","category":"卫星","alias":"伊阿珀托斯","repo_id":"iapetus"},{"id":"phoebe","name":"土卫九","name_en":"Phoebe","type":"天然卫星","category":"卫星","alias":"菲比","repo_id":"phoebe"},{"id":"hyperion","name":"土卫七","name_en":"Hyperion","type":"天然卫星","category":"卫星","repo_id":"hyperion"}],"repo_id":"saturn"},{"id":"uranus","name":"天王星","name_en":"Uranus","type":"冰巨行星","category":"行星","children":[{"id":"ariel","name":"天卫一","name_en":"Ariel","type":"天然卫星","category":"卫星","alias":"艾瑞尔","repo_id":"ariel"},{"id":"umbriel","name":"天卫二","name_en":"Umbriel","type":"天然卫星","category":"卫星","alias":"乌姆布里尔","repo_id":"umbriel"},{"id":"titania","name":"天卫三","name_en":"Titania","type":"天然卫星","category":"卫星","alias":"泰坦妮亚","repo_id":"titania"},{"id":"oberon","name":"天卫四","name_en":"Oberon","type":"天然卫星","category":"卫星","alias":"奥伯龙","repo_id":"oberon"},{"id":"miranda","name":"天卫五","name_en":"Miranda","type":"天然卫星","category":"卫星","alias":"米兰达","repo_id":"miranda"}],"repo_id":"uranus"},{"id":"neptune","name":"海王星","name_en":"Neptune","type":"冰巨行星","category":"行星","children":[{"id":"triton","name":"海卫一","name_en":"Triton","type":"天然卫星","category":"卫星","alias":"特里同","repo_id":"triton"},{"id":"nereid","name":"海卫二","name_en":"Nereid","type":"天然卫星","category":"卫星","alias":"涅瑞伊得","repo_id":"nereid"},{"id":"proteus","name":"海卫八","name_en":"Proteus","type":"天然卫星","category":"卫星","alias":"普洛透斯","repo_id":"proteus"}],"repo_id":"neptune"}]},{"id":"c.kuiper-belt","name":"柯伊伯带","name_en":"Kuiper Belt","type":"外海王星天体带","category":"宇宙结构","children":[{"id":"pluto","name":"冥王星","name_en":"Pluto","type":"矮行星","category":"矮行星","children":[{"id":"charon","name":"冥卫一","name_en":"Charon","type":"天然卫星","category":"卫星","alias":"卡戎","repo_id":"charon"},{"id":"nix","name":"冥卫二","name_en":"Nix","type":"天然卫星","category":"卫星","alias":"尼克斯","repo_id":"nix"},{"id":"hydra","name":"冥卫三","name_en":"Hydra","type":"天然卫星","category":"卫星","alias":"许德拉","repo_id":"hydra"}],"repo_id":"pluto"},{"id":"eris","name":"阋神星","name_en":"Eris","type":"矮行星","category":"矮行星","children":[{"id":"disnomia","name":"阋卫一","name_en":"Dysnomia","type":"天然卫星","category":"卫星","repo_id":"disnomia"}],"repo_id":"eris"},{"id":"haumea","name":"妊神星","name_en":"Haumea","type":"矮行星","category":"矮行星","repo_id":"haumea"},{"id":"makemake","name":"鸟神星","name_en":"Makemake","type":"矮行星","category":"矮行星","repo_id":"makemake"},{"id":"orcus","name":"亡神星","name_en":"Orcus","type":"矮行星","category":"矮行星","children":[{"id":"vanth","name":"范斯","name_en":"Vanth","type":"天然卫星","category":"卫星","alias":"亡卫一","repo_id":"vanth"}],"repo_id":"orcus"},{"id":"gonggong_225088","name":"共工星","name_en":"225088 Gonggong","type":"矮行星","category":"矮行星","info":"离散盘天体","repo_id":"gonggong_225088"},{"id":"sedna","name":"赛德娜","name_en":"Sedna","type":"矮行星","category":"矮行星","info":"内奥尔特云／离散盘天体","repo_id":"sedna"},{"id":"quaoar","name":"创神星","name_en":"Quaoar","type":"矮行星","category":"矮行星","info":"经典柯伊伯带天体","repo_id":"quaoar"}]},{"id":"c.oort-cloud","name":"奥尔特云","name_en":"Oort Cloud","type":"彗星储库","category":"宇宙结构","info":"太阳系最外层边界"},{"id":"halley","name":"哈雷彗星","name_en":"1P/Halley","type":"彗星","category":"彗星","info":"周期约 76 年的短周期彗星","repo_id":"halley"},{"id":"chiron","name":"凯龙星","name_en":"Chiron","type":"半人马小行星","category":"小行星","info":"轨道介于土星与天王星之间的半人马天体","repo_id":"chiron"}]},{"id":"c.local-bubble-solar-neighborhood","name":"本地泡（太阳邻域恒星系统）","name_en":"Local Bubble (Solar Neighborhood)","type":"恒星分组","category":"宇宙结构","info":"太阳周边约数百光年内的近邻恒星与恒星系统，均位于本地臂","children":[{"id":"c.alpha-centauri","name":"南门二","name_en":"Alpha Centauri","type":"三合星系统","category":"恒星","alias":"半人马座α","info":"距离太阳约 4.37 光年","source":"ESA","children":[{"id":"alphacen_a","name":"南门二A","name_en":"Alpha Centauri A","type":"G2V 主序星","category":"恒星","repo_id":"alphacen_a"},{"id":"alphacen_b","name":"南门二B","name_en":"Alpha Centauri B","type":"K1V 橙矮星","category":"恒星","repo_id":"alphacen_b"},{"id":"proxima_centauri","name":"比邻星","name_en":"Proxima Centauri","type":"M5.5V 红矮星","category":"恒星","alias":"南门二C","info":"距离太阳约 4.22 光年，离我们最近的恒星","children":[{"id":"proxima_centauri_b","name":"比邻星b","name_en":"Proxima Centauri b","type":"系外行星","category":"行星","info":"位于宜居带的类地行星","repo_id":"proxima_centauri_b"},{"id":"proxima_centauri_c","name":"比邻星c","name_en":"Proxima Centauri c","type":"系外行星","category":"行星","info":"候选超级地球，存在争议","repo_id":"proxima_centauri_c"},{"id":"proxima_centauri_d","name":"比邻星d","name_en":"Proxima Centauri d","type":"系外行星","category":"行星","info":"已确认的极小类地行星","repo_id":"proxima_centauri_d"}],"repo_id":"proxima_centauri"}]},{"id":"barnard_s_star","name":"巴纳德星","name_en":"Barnard's Star","type":"M4V 红矮星","category":"恒星","info":"距离约 5.96 光年，自行极高；巴纳德星 b 已证伪","source":"NASA","repo_id":"barnard_s_star"},{"id":"c.sirius","name":"天狼星","name_en":"Sirius","type":"双星系统","category":"恒星","info":"全天最亮恒星，距离约 8.6 光年","source":"NASA","children":[{"id":"sirius_a","name":"天狼星A","name_en":"Sirius A","type":"A1V 主序星","category":"恒星","repo_id":"sirius_a"},{"id":"sirius_b","name":"天狼星B","name_en":"Sirius B","type":"白矮星","category":"恒星","repo_id":"sirius_b"}]},{"id":"procyon_a","name":"南河三","name_en":"Procyon","type":"双星系统","category":"恒星","info":"距离约 11.4 光年","source":"NASA","children":[{"id":"procyon_b","name":"南河三B","name_en":"Procyon B","type":"白矮星","category":"恒星","repo_id":"procyon_b"}],"repo_id":"procyon_a"},{"id":"vega","name":"织女星","name_en":"Vega","type":"A0V 主序星","category":"恒星","info":"天琴座 α，距离约 25 光年","source":"NASA","repo_id":"vega"},{"id":"arcturus","name":"大角星","name_en":"Arcturus","type":"红巨星","category":"恒星","info":"牧夫座 α，光谱型 K0 III，距离约 37 光年","source":"NASA","repo_id":"arcturus"},{"id":"altair","name":"河鼓二","name_en":"Altair","type":"A7V 主序星","category":"恒星","alias":"牛郎星","info":"天鹰座 α，距离约 16.7 光年","source":"NASA","repo_id":"altair"},{"id":"aldebaran","name":"毕宿五","name_en":"Aldebaran","type":"红巨星","category":"恒星","info":"金牛座 α，光谱型 K5 III","source":"NASA","repo_id":"aldebaran"},{"id":"capella","name":"五车二","name_en":"Capella","type":"四合星系统","category":"恒星","alias":"御夫座α","info":"两对双星互相绕转，距离约 42 光年","source":"NASA","children":[{"id":"capella_aa","name":"五车二Aa","name_en":"Capella Aa","type":"G 型巨星","category":"恒星","repo_id":"capella_aa"},{"id":"capella_ab","name":"五车二Ab","name_en":"Capella Ab","type":"G 型巨星","category":"恒星","repo_id":"capella_ab"},{"id":"capella_ba","name":"五车二Ba","name_en":"Capella Ba","type":"M 型矮星","category":"恒星","repo_id":"capella_ba"},{"id":"capella_bb","name":"五车二Bb","name_en":"Capella Bb","type":"M 型矮星","category":"恒星","repo_id":"capella_bb"}],"repo_id":"capella"},{"id":"castor","name":"北河二","name_en":"Castor","type":"六合星系统","category":"恒星","alias":"双子座α","info":"三组双星构成，距离约 51 光年","source":"NASA","children":[{"id":"castor_a1","name":"北河二A1","name_en":"Castor A1","type":"A 型主序星","category":"恒星","repo_id":"castor_a1"},{"id":"castor_a2","name":"北河二A2","name_en":"Castor A2","type":"A 型主序星","category":"恒星","repo_id":"castor_a2"},{"id":"castor_b1","name":"北河二B1","name_en":"Castor B1","type":"A 型主序星","category":"恒星","repo_id":"castor_b1"},{"id":"castor_b2","name":"北河二B2","name_en":"Castor B2","type":"A 型主序星","category":"恒星","repo_id":"castor_b2"},{"id":"castor_c1","name":"北河二C1","name_en":"Castor C1","type":"M 型矮星","category":"恒星","repo_id":"castor_c1"},{"id":"castor_c2","name":"北河二C2","name_en":"Castor C2","type":"M 型矮星","category":"恒星","repo_id":"castor_c2"}],"repo_id":"castor"},{"id":"pollux","name":"北河三","name_en":"Pollux","type":"红巨星","category":"恒星","alias":"双子座β","info":"光谱型 K0 III；拥有行星北河三b（Thestias）","source":"NASA","children":[{"id":"pollux_b","name":"北河三b","name_en":"Pollux b","type":"系外行星","category":"行星","info":"已确认的气态巨行星","repo_id":"pollux_b"}],"repo_id":"pollux"},{"id":"trappist_1","name":"特拉比斯特 1","name_en":"TRAPPIST-1","type":"恒星系统","category":"恒星","alias":"TRAPPIST-1","info":"M8V 红矮星，距离约 40 光年；7 颗类地行星，多颗位于宜居带","children":[{"id":"trappist_1_b","name":"TRAPPIST-1 b","name_en":"TRAPPIST-1 b","type":"系外行星","category":"行星","repo_id":"trappist_1_b"},{"id":"trappist_1_c","name":"TRAPPIST-1 c","name_en":"TRAPPIST-1 c","type":"系外行星","category":"行星","repo_id":"trappist_1_c"},{"id":"trappist_1_d","name":"TRAPPIST-1 d","name_en":"TRAPPIST-1 d","type":"系外行星","category":"行星","repo_id":"trappist_1_d"},{"id":"trappist_1_e","name":"TRAPPIST-1 e","name_en":"TRAPPIST-1 e","type":"系外行星","category":"行星","info":"位于宜居带","repo_id":"trappist_1_e"},{"id":"trappist_1_f","name":"TRAPPIST-1 f","name_en":"TRAPPIST-1 f","type":"系外行星","category":"行星","info":"位于宜居带","repo_id":"trappist_1_f"},{"id":"trappist_1_g","name":"TRAPPIST-1 g","name_en":"TRAPPIST-1 g","type":"系外行星","category":"行星","info":"位于宜居带","repo_id":"trappist_1_g"},{"id":"trappist_1_h","name":"TRAPPIST-1 h","name_en":"TRAPPIST-1 h","type":"系外行星","category":"行星","repo_id":"trappist_1_h"}],"repo_id":"trappist_1"},{"id":"gliese_581","name":"格利泽581","name_en":"Gliese 581","type":"M 型红矮星","category":"恒星","alias":"Gliese 581","info":"距离约 20 光年；格利泽581g/d 存在争议，未被确认","children":[{"id":"gliese_581_b","name":"格利泽581b","name_en":"Gliese 581 b","type":"系外行星","category":"行星","info":"已确认","repo_id":"gliese_581_b"},{"id":"gliese_581_c","name":"格利泽581c","name_en":"Gliese 581 c","type":"系外行星","category":"行星","info":"已确认","repo_id":"gliese_581_c"},{"id":"gliese_581_e","name":"格利泽581e","name_en":"Gliese 581 e","type":"系外行星","category":"行星","info":"已确认","repo_id":"gliese_581_e"},{"id":"c.gliese-581-g","name":"格利泽581g","name_en":"Gliese 581 g","type":"系外行星","category":"行星","info":"存在争议，未确认"}],"repo_id":"gliese_581"}]}]},{"id":"c.sagittarius-arm","name":"人马臂","name_en":"Sagittarius Arm","type":"主旋臂","category":"宇宙结构","info":"内侧主旋臂"},{"id":"c.outer-arm","name":"外缘臂","name_en":"Outer Arm","type":"旋臂","category":"宇宙结构","info":"银河系最外侧旋臂"},{"id":"c.notable-milky-way-objects-spiral-arm-unspecified","name":"银河系内著名天体（旋臂归属未细化）","name_en":"Notable Milky Way Objects (Spiral Arm Unspecified)","type":"天体分组","category":"宇宙结构","info":"距离较远、缺乏可靠旋臂归属依据的银河系内天体；不臆测具体旋臂","children":[{"id":"c.stars-spiral-arm-unspecified","name":"恒星（旋臂归属未细化）","name_en":"Stars (Spiral Arm Unspecified)","type":"恒星分组","category":"宇宙结构","info":"本站收录但缺乏可靠旋臂归属依据的银河系内恒星","children":[{"id":"pistol_star","name":"手枪星","name_en":"Pistol Star","type":"高光度蓝变星","category":"恒星","info":"位于银河系中心方向","repo_id":"pistol_star"},{"id":"rigel","name":"参宿七","name_en":"Rigel","type":"蓝超巨星","category":"恒星","repo_id":"rigel"},{"id":"betelgeuse","name":"参宿四","name_en":"Betelgeuse","type":"红超巨星","category":"恒星","repo_id":"betelgeuse"},{"id":"eridani_40a","name":"波江座40A","name_en":"40 Eridani A","type":"K1V 橙矮星","category":"恒星","info":"波江座 40 三合星系统主星，距约 16 光年","repo_id":"eridani_40a"},{"id":"eridani_40b","name":"波江座40B","name_en":"40 Eridani B","type":"白矮星","category":"恒星","repo_id":"eridani_40b"},{"id":"vela_pulsar","name":"船帆脉冲星","name_en":"Vela Pulsar","type":"脉冲星","category":"恒星","repo_id":"vela_pulsar"},{"id":"sgr_1806_20","name":"SGR 1806-20","name_en":"SGR 1806-20","type":"磁星","category":"恒星","repo_id":"sgr_1806_20"},{"id":"spica","name":"角宿一","name_en":"Spica","type":"B 型主序星","category":"恒星","repo_id":"spica"},{"id":"regulus","name":"轩辕十四","name_en":"Regulus","type":"B 型主序星","category":"恒星","repo_id":"regulus"},{"id":"formalhaut","name":"北落师门","name_en":"Fomalhaut","type":"A 型主序星","category":"恒星","repo_id":"formalhaut"},{"id":"mirfak","name":"天船三","name_en":"Mirfak","type":"F 型超巨星","category":"恒星","repo_id":"mirfak"},{"id":"hamal","name":"娄宿三","name_en":"Hamal","type":"K 型巨星","category":"恒星","repo_id":"hamal"},{"id":"markab","name":"室宿一","name_en":"Markab","type":"B 型主序星","category":"恒星","repo_id":"markab"},{"id":"alpheratz","name":"壁宿二","name_en":"Alpheratz","type":"B 型主序星","category":"恒星","repo_id":"alpheratz"},{"id":"mirach","name":"奎宿九","name_en":"Mirach","type":"M 型红巨星","category":"恒星","repo_id":"mirach"},{"id":"wezen","name":"弧矢一","name_en":"Wezen","type":"F 型超巨星","category":"恒星","repo_id":"wezen"},{"id":"adhara","name":"弧矢七","name_en":"Adhara","type":"B 型超巨星","category":"恒星","repo_id":"adhara"},{"id":"aludra","name":"弧矢二","name_en":"Aludra","type":"B 型超巨星","category":"恒星","repo_id":"aludra"},{"id":"mu_cephei","name":"造父四","name_en":"Mu Cephei","type":"红超巨星","category":"恒星","repo_id":"mu_cephei"},{"id":"rw_cephei","name":"仙王座 RW","name_en":"RW Cephei","type":"红超巨星","category":"恒星","repo_id":"rw_cephei"},{"id":"s_persei","name":"英仙座 S","name_en":"S Persei","type":"红超巨星","category":"恒星","repo_id":"s_persei"},{"id":"mira","name":"蒭藁增二","name_en":"Mira","type":"米拉变星","category":"恒星","repo_id":"mira"},{"id":"p_cygni","name":"天鹅座 P","name_en":"P Cygni","type":"高光度蓝变星","category":"恒星","repo_id":"p_cygni"},{"id":"naos","name":"弧矢增二十二","name_en":"Zeta Puppis","type":"O 型星","category":"恒星","repo_id":"naos"},{"id":"algol","name":"大陵五","name_en":"Algol","type":"食双星","category":"恒星","repo_id":"algol"},{"id":"sheliak","name":"渐台二","name_en":"Beta Lyrae","type":"食双星","category":"恒星","repo_id":"sheliak"},{"id":"almaaz","name":"御夫座ε","name_en":"Epsilon Aurigae","type":"F 型超巨星","category":"恒星","repo_id":"almaaz"},{"id":"kepler_186","name":"开普勒186","name_en":"Kepler-186","type":"红矮星","category":"恒星","alias":"Kepler-186","repo_id":"kepler_186"},{"id":"cancri_55","name":"巨蟹座55","name_en":"55 Cancri","type":"K 型主序星","category":"恒星","alias":"55 Cancri","children":[{"id":"55_cancri_e","name":"巨蟹座55e","name_en":"55 Cancri e","type":"系外行星","category":"行星","alias":"55 Cancri e","repo_id":"55_cancri_e"}],"repo_id":"cancri_55"},{"id":"pegasi_51","name":"飞马座51","name_en":"51 Pegasi","type":"G 型主序星","category":"恒星","alias":"51 Pegasi","children":[{"id":"51_pegasi_b","name":"飞马座51b","name_en":"51 Pegasi b","type":"系外行星","category":"行星","alias":"51 Pegasi b","info":"1995 年发现，首颗围绕类太阳恒星确认的系外行星","repo_id":"51_pegasi_b"}],"repo_id":"pegasi_51"},{"id":"beta_pictoris","name":"绘架座β","name_en":"Beta Pictoris","type":"A 型主序星","category":"恒星","repo_id":"beta_pictoris"},{"id":"deneb","name":"天津四","name_en":"Deneb","type":"蓝超巨星","category":"恒星","info":"天鹅座 α，光谱型 A2 Ia，距约 2600 光年","repo_id":"deneb"},{"id":"antares","name":"心宿二","name_en":"Antares","type":"红超巨星","category":"恒星","info":"天蝎座 α","repo_id":"antares"},{"id":"uy_scuti","name":"盾牌座UY","name_en":"UY Scuti","type":"红超巨星","category":"恒星","repo_id":"uy_scuti"},{"id":"stephenson_2_18","name":"史蒂文森2-18","name_en":"Stephenson 2-18","type":"红超巨星","category":"恒星","info":"已知体积最大的红超巨星之一","repo_id":"stephenson_2_18"}]},{"id":"c.nebulae-spiral-arm-unspecified","name":"星云（旋臂归属未细化）","name_en":"Nebulae (Spiral Arm Unspecified)","type":"星云分组","category":"宇宙结构","info":"本站收录但缺乏可靠旋臂归属依据的银河系内星云","children":[{"id":"m20","name":"三叶星云","name_en":"Trifid Nebula (M20)","type":"发射星云","category":"星云","alias":"M20","repo_id":"m20"},{"id":"m8","name":"礁湖星云","name_en":"Lagoon Nebula (M8)","type":"发射星云","category":"星云","alias":"M8","repo_id":"m8"},{"id":"ngc7293","name":"螺旋星云","name_en":"Helix Nebula (NGC 7293)","type":"行星状星云","category":"星云","alias":"NGC 7293","repo_id":"ngc7293"},{"id":"m2_9","name":"双喷射星星云","name_en":"M2-9 (Twin Jet Nebula)","type":"行星状星云","category":"星云","alias":"M2-9","repo_id":"m2_9"},{"id":"rosette","name":"玫瑰星云","name_en":"Rosette Nebula","type":"发射星云","category":"星云","repo_id":"rosette"},{"id":"barnards_loop","name":"巴纳德环","name_en":"Barnard's Loop","type":"发射星云","category":"星云","repo_id":"barnards_loop"},{"id":"m17","name":"天鹅星云","name_en":"Omega Nebula","type":"发射星云","category":"星云","alias":"M17","repo_id":"m17"},{"id":"ngc3372","name":"船底座星云","name_en":"Carina Nebula","type":"发射星云","category":"星云","alias":"NGC 3372","repo_id":"ngc3372"},{"id":"ngc7000","name":"北美洲星云","name_en":"North America Nebula","type":"发射星云","category":"星云","alias":"NGC 7000","repo_id":"ngc7000"},{"id":"m42","name":"猎户座大星云","name_en":"Orion Nebula (M42)","type":"发射星云","category":"星云","alias":"M42","info":"恒星形成区","repo_id":"m42"},{"id":"m16","name":"鹰状星云","name_en":"Eagle Nebula (M16)","type":"发射星云","category":"星云","alias":"M16","info":"恒星形成区，含创生之柱","repo_id":"m16"},{"id":"m1","name":"蟹状星云","name_en":"Crab Nebula (M1)","type":"超新星遗迹","category":"星云","alias":"M1","info":"1054 年超新星爆发遗迹","children":[{"id":"crab_pulsar","name":"蟹云脉冲星","name_en":"Crab Pulsar","type":"脉冲星","category":"恒星","info":"超新星遗迹中心的脉冲星","repo_id":"crab_pulsar"}],"repo_id":"m1"},{"id":"c.m78-reflection-nebula","name":"M78（反射星云）","name_en":"M78 (Reflection Nebula)","type":"反射星云","category":"星云","alias":"M78"},{"id":"horsehead","name":"马头星云","name_en":"Horsehead Nebula","type":"暗星云","category":"星云","alias":"巴纳德33","repo_id":"horsehead"},{"id":"m57","name":"环状星云","name_en":"Ring Nebula (M57)","type":"行星状星云","category":"星云","alias":"M57","repo_id":"m57"},{"id":"m27","name":"哑铃星云","name_en":"Dumbbell Nebula","type":"行星状星云","category":"星云","alias":"M27","repo_id":"m27"}]},{"id":"c.exoplanet-systems-host-stars","name":"系外行星系统（宿主恒星）","name_en":"Exoplanet Systems (Host Stars)","type":"恒星系统分组","category":"宇宙结构","info":"系外行星与其宿主恒星的引力从属关系","children":[{"id":"c.k2-18","name":"K2-18","name_en":"K2-18","type":"红矮星","category":"恒星","children":[{"id":"k2-18_b","name":"K2-18 b","name_en":"K2-18 b","type":"系外行星","category":"行星","repo_id":"k2-18_b"}]},{"id":"c.lhs-1140","name":"LHS 1140","name_en":"LHS 1140","type":"红矮星","category":"恒星","children":[{"id":"lhs_1140_b","name":"LHS 1140 b","name_en":"LHS 1140 b","type":"系外行星","category":"行星","repo_id":"lhs_1140_b"}]},{"id":"c.wasp-12","name":"WASP-12","name_en":"WASP-12","type":"G 型主序星","category":"恒星","children":[{"id":"wasp-12_b","name":"WASP-12 b","name_en":"WASP-12 b","type":"系外行星","category":"行星","repo_id":"wasp-12_b"}]},{"id":"c.hd-189733","name":"HD 189733","name_en":"HD 189733","type":"K 型主序星","category":"恒星","children":[{"id":"hd_189733_b","name":"HD 189733 b","name_en":"HD 189733 b","type":"系外行星","category":"行星","repo_id":"hd_189733_b"}]},{"id":"c.wasp-107","name":"WASP-107","name_en":"WASP-107","type":"K 型主序星","category":"恒星","children":[{"id":"wasp_107_b","name":"WASP-107 b","name_en":"WASP-107 b","type":"系外行星","category":"行星","repo_id":"wasp_107_b"}]},{"id":"kepler_452","name":"开普勒452","name_en":"Kepler-452","type":"G 型主序星","category":"恒星","alias":"Kepler-452","children":[{"id":"kepler_452b","name":"开普勒452b","name_en":"Kepler-452b","type":"系外行星","category":"行星","info":"超级地球，候选宜居","repo_id":"kepler_452b"}],"repo_id":"kepler_452"},{"id":"kepler_22","name":"开普勒22","name_en":"Kepler-22","type":"G 型主序星","category":"恒星","alias":"Kepler-22","children":[{"id":"kepler_22b","name":"开普勒22b","name_en":"Kepler-22b","type":"系外行星","category":"行星","info":"超级地球","repo_id":"kepler_22b"}],"repo_id":"kepler_22"},{"id":"c.kepler-16","name":"开普勒16","name_en":"Kepler-16","type":"双星系统","category":"恒星","alias":"Kepler-16","info":"环双星行星系统","children":[{"id":"kepler_16_a","name":"开普勒16A","name_en":"Kepler-16 A","type":"主序星","category":"恒星","repo_id":"kepler_16_a"},{"id":"kepler_16_b","name":"开普勒16B","name_en":"Kepler-16 B","type":"红矮星","category":"恒星","repo_id":"kepler_16_b"},{"id":"kepler_16b","name":"开普勒16b","name_en":"Kepler-16b","type":"系外行星","category":"行星","info":"首个被证实的环双星行星","repo_id":"kepler_16b"}]},{"id":"c.psr-b1257-12","name":"PSR B1257+12","name_en":"PSR B1257+12","type":"脉冲星系统","category":"恒星","info":"人类最早发现系外行星的宿主脉冲星","children":[{"id":"c.psr-b1257-12-b","name":"PSR B1257+12 b","name_en":"PSR B1257+12 b","type":"脉冲星行星","category":"行星"},{"id":"c.psr-b1257-12-c","name":"PSR B1257+12 c","name_en":"PSR B1257+12 c","type":"脉冲星行星","category":"行星"},{"id":"c.psr-b1257-12-d","name":"PSR B1257+12 d","name_en":"PSR B1257+12 d","type":"脉冲星行星","category":"行星"}]}]}]},{"id":"c.open-clusters-galactic-disk","name":"疏散星团（银盘）","name_en":"Open Clusters (Galactic Disk)","type":"星团分组","category":"宇宙结构","info":"疏散星团分布于银盘，与银晕中的球状星团不同","children":[{"id":"m45","name":"昴星团","name_en":"Pleiades (M45)","type":"疏散星团","category":"星团","alias":"M45","repo_id":"m45"},{"id":"m67","name":"梅西耶67","name_en":"Messier 67","type":"疏散星团","category":"星团","alias":"M67","repo_id":"m67"},{"id":"hyades","name":"毕星团","name_en":"Hyades","type":"疏散星团","category":"星团","repo_id":"hyades"},{"id":"m44","name":"蜂巢星团","name_en":"Beehive Cluster (M44)","type":"疏散星团","category":"星团","alias":"M44","repo_id":"m44"},{"id":"m11","name":"野鸭星团","name_en":"Wild Duck Cluster","type":"疏散星团","category":"星团","alias":"M11","repo_id":"m11"},{"id":"m7","name":"托勒密星团","name_en":"Ptolemy Cluster","type":"疏散星团","category":"星团","alias":"M7","repo_id":"m7"},{"id":"ngc4755","name":"珠宝盒星团","name_en":"Jewel Box Cluster","type":"疏散星团","category":"星团","alias":"NGC 4755","repo_id":"ngc4755"}]},{"id":"c.stellar-mass-black-holes-in-the-milky-way","name":"银河系内恒星级黑洞","name_en":"Stellar-Mass Black Holes in the Milky Way","type":"黑洞分组","category":"宇宙结构","info":"银河系内由大质量恒星坍缩形成的恒星级黑洞","children":[{"id":"cyg_x1","name":"天鹅座 X-1","name_en":"Cygnus X-1","type":"恒星级黑洞","category":"黑洞","info":"著名 X 射线双星，人类最早确认的黑洞候选之一","repo_id":"cyg_x1"},{"id":"v404_cyg","name":"V404 天鹅座","name_en":"V404 Cygni","type":"恒星级黑洞","category":"黑洞","alias":"天鹅座V404","info":"低质量 X 射线双星中的黑洞","repo_id":"v404_cyg"},{"id":"gaia_bh1","name":"盖亚BH1","name_en":"Gaia BH1","type":"恒星级黑洞","category":"黑洞","info":"距离地球最近的已知黑洞，约 1560 光年","repo_id":"gaia_bh1"}]}]},{"id":"c.galactic-halo","name":"银晕","name_en":"Galactic Halo","type":"星系晕","category":"宇宙结构","info":"暗物质晕 + 球状星团分布区","source":"ESA","children":[{"id":"c.globular-clusters-galactic-halo","name":"球状星团（银晕）","name_en":"Globular Clusters (Galactic Halo)","type":"星团分组","category":"宇宙结构","children":[{"id":"omega_cen","name":"半人马座ω","name_en":"Omega Centauri","type":"球状星团","category":"星团","alias":"ω星团","repo_id":"omega_cen"},{"id":"c.47-tucanae","name":"杜鹃座47","name_en":"47 Tucanae","type":"球状星团","category":"星团"},{"id":"m13","name":"武仙座球状星团","name_en":"Messier 13","type":"球状星团","category":"星团","alias":"M13","repo_id":"m13"},{"id":"m22","name":"梅西耶22","name_en":"Messier 22","type":"球状星团","category":"星团","alias":"M22","repo_id":"m22"},{"id":"c.m5-globular-cluster","name":"M5（球状星团）","name_en":"M5 (Globular Cluster)","type":"球状星团","category":"星团","alias":"M5"},{"id":"c.m15-globular-cluster","name":"M15（球状星团）","name_en":"M15 (Globular Cluster)","type":"球状星团","category":"星团","alias":"M15"},{"id":"c.m92-globular-cluster","name":"M92（球状星团）","name_en":"M92 (Globular Cluster)","type":"球状星团","category":"星团","alias":"M92"}]}]},{"id":"c.milky-way-satellite-dwarf-galaxies","name":"银河系卫星矮星系","name_en":"Milky Way Satellite Dwarf Galaxies","type":"卫星星系分组","category":"宇宙结构","children":[{"id":"lmc","name":"大麦哲伦云","name_en":"Large Magellanic Cloud","type":"不规则矮星系","category":"星系","children":[{"id":"tarantula","name":"蜘蛛星云","name_en":"Tarantula Nebula (30 Doradus)","type":"发射星云","category":"星云","alias":"NGC 2070","info":"大麦哲伦云内巨大恒星形成区","children":[{"id":"r136","name":"R136 星团","name_en":"R136","type":"疏散星团","category":"星团","info":"蜘蛛星云中心的超大质量星团","children":[{"id":"r136a1","name":"R136a1","name_en":"R136a1","type":"沃尔夫-拉叶星","category":"恒星","info":"已知质量最大的恒星之一","repo_id":"r136a1"}],"repo_id":"r136"}],"repo_id":"tarantula"}],"repo_id":"lmc"},{"id":"smc","name":"小麦哲伦云","name_en":"Small Magellanic Cloud","type":"不规则矮星系","category":"星系","repo_id":"smc"},{"id":"c.sagittarius-dwarf-spheroidal-galaxy","name":"人马座矮椭球星系","name_en":"Sagittarius Dwarf Spheroidal Galaxy","type":"矮椭球星系","category":"星系"},{"id":"c.canis-major-dwarf-galaxy","name":"大犬座矮星系","name_en":"Canis Major Dwarf Galaxy","type":"矮不规则星系","category":"星系"},{"id":"c.ursa-minor-dwarf-galaxy","name":"小熊座矮星系","name_en":"Ursa Minor Dwarf Galaxy","type":"矮椭球星系","category":"星系"},{"id":"c.draco-dwarf-galaxy","name":"天龙座矮星系","name_en":"Draco Dwarf Galaxy","type":"矮椭球星系","category":"星系"}]}],"repo_id":"milky_way"},{"id":"m31","name":"仙女座星系","name_en":"Andromeda Galaxy (M31)","type":"旋涡星系","category":"星系","alias":"M31","info":"本星系群最大星系，未来将与银河系并合","children":[{"id":"c.m32-dwarf-elliptical-galaxy","name":"M32（矮椭圆星系）","name_en":"M32 (Dwarf Elliptical Galaxy)","type":"矮椭圆卫星星系","category":"星系","alias":"M32"},{"id":"c.m110-dwarf-elliptical-galaxy","name":"M110（矮椭圆星系）","name_en":"M110 (Dwarf Elliptical Galaxy)","type":"矮椭圆卫星星系","category":"星系","alias":"M110"},{"id":"c.andromeda-i","name":"仙女座 I","name_en":"Andromeda I","type":"矮椭球卫星星系","category":"星系"},{"id":"c.andromeda-ii","name":"仙女座 II","name_en":"Andromeda II","type":"矮椭球卫星星系","category":"星系"}],"repo_id":"m31"},{"id":"m33","name":"三角座星系","name_en":"Triangulum Galaxy (M33)","type":"旋涡星系","category":"星系","alias":"M33","info":"本星系群第三大星系","repo_id":"m33"},{"id":"c.ic-10","name":"IC 10","name_en":"IC 10","type":"不规则矮星系","category":"星系"},{"id":"c.ngc-147","name":"NGC 147","name_en":"NGC 147","type":"矮椭圆星系","category":"星系"},{"id":"c.ngc-185","name":"NGC 185","name_en":"NGC 185","type":"矮椭圆星系","category":"星系"}],"repo_id":"local_group"},{"id":"virgo_cluster","name":"室女座星系团","name_en":"Virgo Cluster","type":"富星系团","category":"宇宙结构","info":"拉尼亚凯亚内部大型富星系团","children":[{"id":"m87","name":"室女座A","name_en":"Messier 87","type":"巨椭圆星系","category":"星系","alias":"M87","children":[{"id":"m87_star","name":"M87*","name_en":"M87*","type":"超大质量黑洞","category":"黑洞","source":"EHT 2019","repo_id":"m87_star"}],"repo_id":"m87"},{"id":"c.m49-giant-elliptical-galaxy","name":"M49（巨椭圆星系）","name_en":"M49 (Giant Elliptical Galaxy)","type":"巨椭圆星系","category":"星系","alias":"M49"},{"id":"c.m60-giant-elliptical-galaxy","name":"M60（巨椭圆星系）","name_en":"M60 (Giant Elliptical Galaxy)","type":"巨椭圆星系","category":"星系","alias":"M60"},{"id":"m104","name":"草帽星系","name_en":"Sombrero Galaxy (M104)","type":"旋涡星系","category":"星系","alias":"M104","repo_id":"m104"}],"repo_id":"virgo_cluster"},{"id":"c.m81-group","name":"M81星系群","name_en":"M81 Group","type":"星系群","category":"宇宙结构","children":[{"id":"m81","name":"波德星系","name_en":"Messier 81","type":"旋涡星系","category":"星系","alias":"M81","repo_id":"m81"},{"id":"m82","name":"雪茄星系","name_en":"Messier 82 (Cigar Galaxy)","type":"星暴星系","category":"星系","alias":"M82","repo_id":"m82"}]},{"id":"c.centaurus-a-group","name":"半人马座A星系群","name_en":"Centaurus A Group","type":"星系群","category":"宇宙结构","info":"距离约 1200 万光年的近邻星系群","children":[{"id":"ngc5128","name":"半人马 A","name_en":"Centaurus A","type":"透镜状星系","category":"星系","alias":"NGC 5128","repo_id":"ngc5128"},{"id":"m83","name":"南风车星系","name_en":"Southern Pinwheel Galaxy","type":"旋涡星系","category":"星系","alias":"M83","repo_id":"m83"}]},{"id":"great_attractor","name":"巨引源","name_en":"Great Attractor","type":"引力异常区域","category":"宇宙结构","info":"拉尼亚凯亚的引力中心","repo_id":"great_attractor"},{"id":"c.m51-group","name":"M51星系群","name_en":"M51 Group","type":"星系群","category":"宇宙结构","info":"M51涡状星系所属的星系群，位于室女座超星系团外围，属拉尼亚凯亚","source":"NASA/IPAC","children":[{"id":"m51","name":"涡状星系","name_en":"Whirlpool Galaxy (M51)","type":"旋涡星系","category":"星系","alias":"M51","repo_id":"m51"}]},{"id":"c.m101-group","name":"M101星系群","name_en":"M101 Group","type":"星系群","category":"宇宙结构","info":"M101风车星系所属的松散星系群，属大熊座云子结构，归入拉尼亚凯亚","source":"NASA/IPAC","children":[{"id":"m101","name":"风车星系","name_en":"Pinwheel Galaxy","type":"旋涡星系","category":"星系","alias":"M101","repo_id":"m101"}]},{"id":"c.m94-group","name":"M94星系群（猎犬座I）","name_en":"M94 Group (Canes Venatici I)","type":"星系群","category":"宇宙结构","info":"M64黑眼星系所属的星系群（猎犬座I），归入拉尼亚凯亚","source":"NASA/IPAC","children":[{"id":"m64","name":"黑眼星系","name_en":"Black Eye Galaxy","type":"旋涡星系","category":"星系","alias":"M64","repo_id":"m64"}]},{"id":"c.ngc4038-group","name":"NGC 4038星系群","name_en":"NGC 4038 Group","type":"星系群","category":"宇宙结构","info":"天线星系（NGC4038/4039）所属的致密相互作用星系群，归入拉尼亚凯亚","source":"NASA/IPAC","children":[{"id":"ngc4038","name":"天线星系","name_en":"Antennae Galaxies","type":"相互作用星系","category":"星系","alias":"NGC 4038","repo_id":"ngc4038"}]}],"repo_id":"laniakea"}]},{"id":"c.abell-2029-galaxy-cluster","name":"Abell 2029 星系团","name_en":"Abell 2029 Galaxy Cluster","type":"富星系团","category":"宇宙结构","info":"距离约 10 亿光年（红移 z≈0.077），远超拉尼亚凯亚范围","source":"NASA / Wikipedia","children":[{"id":"ic1101","name":"IC 1101","name_en":"IC 1101","type":"超巨椭圆星系","category":"星系","info":"Abell 2029 的中心 cD 星系，已知直径最大的星系之一","children":[{"id":"ic1101_bh","name":"IC 1101 中心黑洞","name_en":"IC 1101 black hole","type":"超大质量黑洞","category":"黑洞","repo_id":"ic1101_bh"}],"repo_id":"ic1101"}]},{"id":"hercules_corona_wall","name":"武仙-北冕座长城","name_en":"Hercules–Corona Borealis Great Wall","type":"巨型宇宙纤维","category":"宇宙结构","info":"已知最大尺度宇宙纤维之一，由伽马射线暴过密区统计发现；非由预知星系团组装，无公认独立成员清单，故无下级节点","source":"NASA","repo_id":"hercules_corona_wall"},{"id":"c.shapley-supercluster","name":"夏普利超星系团","name_en":"Shapley Supercluster","type":"超星系团","category":"宇宙结构","info":"遥远、质量巨大的致密超星系团，不在拉尼亚凯亚内","source":"NASA","children":[{"id":"c.abell-3558","name":"阿贝尔3558","name_en":"Abell 3558","type":"富星系团","category":"宇宙结构","info":"夏普利超星系团核心主导星系团","source":"Abell Catalogue","alias":"A3558"},{"id":"c.abell-3560","name":"阿贝尔3560","name_en":"Abell 3560","type":"富星系团","category":"宇宙结构","info":"夏普利核心区重要伴星系团","source":"Abell Catalogue","alias":"A3560"},{"id":"c.abell-3562","name":"阿贝尔3562","name_en":"Abell 3562","type":"富星系团","category":"宇宙结构","info":"X射线明亮星系团","source":"Abell Catalogue","alias":"A3562"},{"id":"c.abell-3556","name":"阿贝尔3556","name_en":"Abell 3556","type":"富星系团","category":"宇宙结构","info":"与A3558正在并合","source":"Abell Catalogue","alias":"A3556"},{"id":"c.abell-3571","name":"阿贝尔3571","name_en":"Abell 3571","type":"富星系团","category":"宇宙结构","info":"夏普利外围子团","source":"Abell Catalogue","alias":"A3571"}]},{"id":"c.coma-cluster","name":"后发座星系团","name_en":"Coma Cluster","type":"富星系团","category":"宇宙结构","info":"遥远致密的富星系团","children":[{"id":"c.ngc4889","name":"NGC 4889","name_en":"NGC 4889","type":"超巨椭圆星系","category":"星系","info":"后发团中心主导cD星系，拥有超大质量黑洞","source":"NASA/IPAC"},{"id":"c.ngc4874","name":"NGC 4874","name_en":"NGC 4874","type":"超巨椭圆星系","category":"星系","info":"后发团核心另一主导cD星系，富球状星团","source":"NASA/IPAC"},{"id":"c.ngc4921","name":"NGC 4921","name_en":"NGC 4921","type":"旋涡星系","category":"星系","info":"后发团最知名旋涡星系，位于团外围","source":"NASA/IPAC"},{"id":"c.ngc4839","name":"NGC 4839","name_en":"NGC 4839","type":"椭圆星系","category":"星系","info":"属于正在并合的子群","source":"NASA/IPAC"},{"id":"c.ngc4840","name":"NGC 4840","name_en":"NGC 4840","type":"透镜状星系","category":"星系","info":"团内亮透镜星系","source":"NASA/IPAC"},{"id":"c.ngc4816","name":"NGC 4816","name_en":"NGC 4816","type":"椭圆星系","category":"星系","info":"团内亮成员椭圆星系","source":"NASA/IPAC"}]},{"id":"ngc1300","name":"NGC 1300","name_en":"NGC 1300","type":"棒旋星系","category":"星系","info":"棒旋星系，属波江座星系团，经核实不属拉尼亚凯亚超星系团","source":"NASA/IPAC","repo_id":"ngc1300"},{"id":"stephens_quintet","name":"斯蒂芬五重星系","name_en":"Stephan's Quintet","type":"致密星系群","category":"星系","info":"致密相互作用星系群（HCG 92），属飞马座星系团复合体，经核实不属拉尼亚凯亚","source":"NASA/IPAC","repo_id":"stephens_quintet"}],"non_structure":[{"id":"c.distant-quasars-and-agn-cosmological-distances","name":"遥远宇宙类星体与活动星系核（宇宙学距离）","name_en":"Distant Quasars and AGN (Cosmological Distances)","type":"天体分组","category":"宇宙结构","info":"红移较高、距离数亿至百亿光年的活动星系核；不属于本星系群或拉尼亚凯亚","children":[{"id":"ton618","name":"TON 618","name_en":"TON 618","type":"类星体","category":"黑洞","info":"极远类星体，中心为超大质量黑洞，距约 182 亿光年","repo_id":"ton618"},{"id":"oj_287","name":"OJ 287","name_en":"OJ 287","type":"耀变体","category":"黑洞","info":"已知双黑洞候选体，红移约 0.306","repo_id":"oj_287"},{"id":"j2157-3602","name":"J2157-3602","name_en":"J2157-3602","type":"类星体","category":"黑洞","info":"已知增长最快的黑洞之一，宇宙学距离","repo_id":"j2157-3602"},{"id":"phoenix_a","name":"凤凰座A","name_en":"Phoenix A","type":"活动星系核","category":"黑洞","info":"凤凰座星系团中心星系的超大质量黑洞","repo_id":"phoenix_a"}]},{"id":"cmb","name":"宇宙微波背景","name_en":"Cosmic Microwave Background","type":"宇宙背景辐射","category":"宇宙结构","info":"大爆炸后约 38 万年的最后散射面","repo_id":"cmb"}],"repo_id":"observable_universe"}</script>
<script>
document.addEventListener('DOMContentLoaded', function () {
  var DATA = JSON.parse(document.getElementById('uh-data').textContent);
  var TYPE_EN = DATA.type_i18n || {};
  var CAT_EN = DATA.category_i18n || {};
  var CAT_COLOR = {
    '宇宙结构':'#f06292','星系':'#ba68c8','星云':'#4db6ac','恒星':'#ffd54f',
    '行星':'#64b5f6','卫星':'#4dd0e1','星团':'#81c784','矮行星':'#ffb74d',
    '小行星':'#b0bec5','彗星':'#cfd8dc','黑洞':'#e57373','其他':'#90a4ae'
  };
  var CAT_ORDER = ['宇宙结构','星系','星云','恒星','行星','卫星','星团','矮行星','小行星','彗星','黑洞','其他'];
  // 非结构现象（CMB / 类星体-AGN 等）不再单列区块，而是作为主树底部的「暂未分类」容器，
  // 因为它们同样属于宇宙，只是暂无稳定上层结构。
  var NS = DATA.non_structure || [];
  var treeData = DATA;
  if (NS.length){
    treeData = JSON.parse(JSON.stringify(DATA));
    treeData.children = (treeData.children || []).concat([{
      id: 'c.uncategorized',
      name: '暂未分类', name_en: 'Uncategorized',
      type: '未归类现象', category: '其他',
      info: '宇宙微波背景、遥远类星体与活动星系核等并非引力束缚结构、也没有稳定上级结构，暂置于此待后续归类。',
      children: NS
    }]);
  }
  // 默认仅展开「地球」所在层级路径；其余折叠（路径用稳定 id，切换语言不失效）
  var FOCUS_ID = 'earth';
  var focusChain = null;
  (function findChain(n, acc){
    if (focusChain) return;
    var chain = acc.concat([n.id]);
    if (n.id === FOCUS_ID){ focusChain = chain; return; }
    (n.children || []).forEach(function(c){ findChain(c, chain); });
  })(treeData, []);
  focusChain = focusChain || [];
  var I18N = {
    zh: {
      intro: '下面按「引力从属 / 包含关系」组织的天体层级思维导图，从「可观测宇宙」一路下钻到行星、卫星、星团与星云。层级数据由 universe-data.json 提供，天体详情与仓库数据（astro.json）按英文 id 唯一关联；命名遵循统一规范，类型与归属严格按天体真实性质挂接。带「归属未细化」的容器表示现有资料不足以确定更精确的层级，不做臆测归类。名称右侧带 ↗ 的节点可跳转本站详情卡片；搜索支持中文名、英文名与 M/NGC 等规范编号，页面语言请用顶栏的中 / EN 按钮切换。',
      search: '搜索天体名称 / 类型 / 英文名…', expand: '展开全部', collapse: '折叠全部',
      empty: '没有匹配的天体。试试别的名称或清空筛选。', link: '查看本站详情卡片'
    },
    en: {
      intro: 'A hierarchy of celestial objects organized by gravitational affiliation and containment, from the Observable Universe down to planets, moons, clusters and nebulae. Hierarchy comes from universe-data.json; object details in astro.json are linked by a unique English id. Naming follows a strict convention and every affiliation reflects the object real physical nature. Containers marked "Unspecified" mean current sources do not support a finer placement — no guessing. Nodes with ↗ open the object detail card; search supports Chinese names, English names and M/NGC catalog numbers. Use the top-right button in the site header to switch language.',
      search: 'Search name / type / catalog number…', expand: 'Expand all', collapse: 'Collapse all',
      empty: 'No matching objects. Try another name or clear the filters.', link: 'Open object detail card'
    }
  };
  function catOf(t){
    t = t || '';
    if (/黑洞/.test(t)) return '黑洞';
    if (/星云/.test(t)) return '星云';
    if (/(超星系团|复合体|长城|星系团|星系群|纤维|宇宙|结构|边界|晕|星系盘|核心区域|分组|储库)/.test(t)) return '宇宙结构';
    if (/恒星|主序|巨星|矮星|变星/.test(t)) return '恒星';
    if (/行星/.test(t)) return '行星';
    if (/卫星/.test(t)) return '卫星';
    if (/星团/.test(t)) return '星团';
    if (/矮行星/.test(t)) return '矮行星';
    if (/小行星/.test(t)) return '小行星';
    if (/彗星/.test(t)) return '彗星';
    if (/星系/.test(t)) return '星系';
    return '其他';
  }
  // 优先使用节点显式 category（受控词表），缺省时回退 catOf 正则推断
  function nodeCat(n){
    var c = n.category;
    if (c && CAT_COLOR[c]) return c;
    return catOf(n.type || '');
  }
  function colorOf(n){ return CAT_COLOR[nodeCat(n)]; }
  var CAT_SET = new Set();
  (function collect(n){ CAT_SET.add(nodeCat(n)); (n.children||[]).forEach(collect); })(treeData);

  // 语言状态以全站 i18n.js 为准；独立打开本页 / jsdom 单测时退化为页面内切换
  var lang = (window.SITE_LANG === 'en') ? 'en' : 'zh';
  var expanded = new Set();          // 存 id 路径，切换语言不失效
  focusChain.forEach(function(id, i){ expanded.add(focusChain.slice(0, i + 1).join('/')); });
  var activeTypes = new Set();       // 存中文 category key，切换语言不失效
  var query = '';
  var curCrumb = [];
  var treeEl = document.getElementById('uh-tree');
  var crumbEl = document.getElementById('uh-crumb');
  var chipsEl = document.getElementById('uh-chips');
  var legendEl = document.getElementById('uh-legend');

  function T(){ return I18N[lang]; }
  function disp(n){ return lang === 'en' ? (n.name_en || n.name) : n.name; }
  function catLabel(c){ return lang === 'en' ? (CAT_EN[c] || c) : c; }
  function typeLabel(n){
    if (lang !== 'en') return n.type || '';
    return TYPE_EN[n.type] || CAT_EN[nodeCat(n)] || n.type || '';
  }
  function setText(id, txt){ var el = document.getElementById(id); if (el) el.textContent = txt; }
  function applyUI(){
    var t = T();
    setText('uh-intro', t.intro);
    setText('uh-expand', t.expand);
    setText('uh-collapse', t.collapse);
    var q = document.getElementById('uh-q'); if (q) q.placeholder = t.search;
    var sec = document.getElementById('uh'); if (sec) sec.setAttribute('data-lang', lang);
  }
  function setLang(l){
    lang = (l === 'en') ? 'en' : 'zh';
    applyUI(); renderChips(); renderLegend(); renderCrumb(); render();
  }
  // 展开状态与筛选状态用 id / 受控 category，不依赖任何名称
  function pathOf(parent, id){ return parent ? parent + '/' + id : id; }
  function countDesc(n){ var c=0; (n.children||[]).forEach(function(x){ c += 1 + countDesc(x); }); return c; }
  function matches(n){
    if (activeTypes.size && !activeTypes.has(nodeCat(n))) return false;
    if (!query) return true;
    var q = query.toLowerCase();
    return (n.name||'').toLowerCase().indexOf(q) >= 0
        || (n.name_en||'').toLowerCase().indexOf(q) >= 0
        || (n.alias||'').toLowerCase().indexOf(q) >= 0
        || (n.type||'').toLowerCase().indexOf(q) >= 0
        || (TYPE_EN[n.type]||'').toLowerCase().indexOf(q) >= 0
        || nodeCat(n).indexOf(q) >= 0
        || (CAT_EN[nodeCat(n)]||'').toLowerCase().indexOf(q) >= 0
        || (n.id||'').toLowerCase().indexOf(q) >= 0;
  }
  function subHasMatch(n){ if (matches(n)) return true; return (n.children||[]).some(subHasMatch); }
  function esc(s){ return (s||'').replace(/[&<>]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }
  function renderCrumb(){
    crumbEl.innerHTML = curCrumb.map(function(n){
      return '<span class="uh-sep">›</span><b>' + esc(disp(n)) + '</b>';
    }).join(' ');
  }

  function renderNode(n, parentPath, depth, ancestors){
    var path = pathOf(parentPath, n.id);
    var hasKids = (n.children||[]).length > 0;
    var filtering = query || activeTypes.size > 0;
    var isOpen = expanded.has(path) || (filtering && (n.children||[]).some(subHasMatch));
    var node = document.createElement('div'); node.className = 'uh-node';

    var head = document.createElement('div'); head.className = 'uh-head';
    head.setAttribute('data-id', n.id);
    var ar = document.createElement('span');
    ar.className = 'uh-arrow' + (hasKids ? '' : ' leaf') + (isOpen ? ' open' : '');
    ar.innerHTML = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
    var label = disp(n);
    var nm = document.createElement('span'); nm.className = 'uh-nm';
    if (query){
      var idx = label.toLowerCase().indexOf(query.toLowerCase());
      if (~idx){
        nm.innerHTML = esc(label.slice(0,idx)) + '<mark>' + esc(label.slice(idx, idx+query.length)) + '</mark>' + esc(label.slice(idx+query.length));
      } else nm.textContent = label;
    } else nm.textContent = label;
    if (n.alias){
      var al = document.createElement('span'); al.className = 'uh-alias';
      // 纯中文别名是中文习惯名（如「福波斯」），英文语境下 name_en 已是主名，
      // 再显示中文只会重复；编号型别名（M42 / Sgr A*）在两种语言下都保留。
      if (/[一-鿿]/.test(n.alias)) al.setAttribute('data-cn-only', '1');
      al.textContent = n.alias;
      nm.appendChild(al);
    }
    var badge = document.createElement('span'); badge.className = 'uh-badge';
    badge.style.background = colorOf(n); badge.textContent = typeLabel(n);
    head.appendChild(ar); head.appendChild(nm); head.appendChild(badge);
    if (n.repo_id){
      var link = document.createElement('a'); link.className = 'uh-link';
      link.href = '/objects/' + n.repo_id + '/'; link.title = T().link;
      link.textContent = '↗';
      link.addEventListener('click', function(e){ e.stopPropagation(); });
      head.appendChild(link);
    }
    if (hasKids){ var c = document.createElement('span'); c.className = 'uh-cnt'; c.textContent = countDesc(n); head.appendChild(c); }

    head.addEventListener('click', function (){
      if (hasKids){ if (expanded.has(path)) expanded.delete(path); else expanded.add(path); }
      curCrumb = ancestors.concat([n]);
      renderCrumb();
      render();
    });
    node.appendChild(head);

    if (hasKids){
      var kids = document.createElement('div'); kids.className = 'uh-children';
      var list = filtering ? n.children.filter(subHasMatch) : n.children;
      list.forEach(function(c){ kids.appendChild(renderNode(c, path, depth+1, ancestors.concat([n]))); });
      kids.classList.toggle('collapsed', !isOpen);
      node.appendChild(kids);
    }
    return node;
  }

  function render(){
    treeEl.innerHTML = '';
    if (query || activeTypes.size){
      var list = treeData.children.filter(subHasMatch);
      if (!list.length){ treeEl.innerHTML = '<div class="uh-empty">' + esc(T().empty) + '</div>'; }
      else list.forEach(function(c){ treeEl.appendChild(renderNode(c, '', 1, [])); });
    } else {
      treeEl.appendChild(renderNode(treeData, '', 0, []));
    }
  }

  function renderChips(){
    chipsEl.innerHTML = '';
    CAT_ORDER.filter(function(c){ return CAT_SET.has(c); }).forEach(function(t){
      var c = document.createElement('span'); c.className = 'uh-chip' + (activeTypes.has(t) ? ' on' : '');
      c.innerHTML = '<span class="uh-dot" style="background:' + CAT_COLOR[t] + '"></span>' + esc(catLabel(t));
      c.addEventListener('click', function (){
        if (activeTypes.has(t)){ activeTypes.delete(t); c.classList.remove('on'); }
        else { activeTypes.add(t); c.classList.add('on'); }
        render();
      });
      chipsEl.appendChild(c);
    });
  }
  function renderLegend(){
    legendEl.innerHTML = '';
    CAT_ORDER.filter(function(c){ return CAT_SET.has(c); }).forEach(function(t){
      var s = document.createElement('span');
      s.innerHTML = '<i style="background:' + CAT_COLOR[t] + '"></i>' + esc(catLabel(t));
      legendEl.appendChild(s);
    });
  }

  document.getElementById('uh-q').addEventListener('input', function(e){ query = e.target.value.trim(); render(); });
  document.getElementById('uh-expand').addEventListener('click', function (){
    (function walk(n, p){
      var path = pathOf(p, n.id);
      if ((n.children||[]).length){ expanded.add(path); n.children.forEach(function(c){ walk(c, path); }); }
    })(treeData, '');
    render();
  });
  document.getElementById('uh-collapse').addEventListener('click', function (){ expanded.clear(); render(); });
  document.addEventListener('site:langchange', function (e){ setLang(e.detail.lang); });

  applyUI(); renderChips(); renderLegend(); render();
});
</script>

> 本页数据由仓库根目录的 `universe-tree.json` 驱动生成（经 `scripts/universe_merge.py` 按英文 id 唯一关联 `universe-data.json` 与 `docs/data/astro.json`）；数据源改动后随 `mkdocs build` 自动同步，无需手动操作。
