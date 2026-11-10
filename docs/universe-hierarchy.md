---
title: 宇宙天体层级
hide:
  - toc
---

下面按「引力从属 / 包含关系」组织的天体层级思维导图，从「可观测宇宙」一路下钻到行星、卫星、星团与星云。数据由外部层级文档与「星野笔记」天体库（`astro.json`）融合而成；**天体本体数值准确性要求不高，层级所属严格**。

<section id="uh" class="uh">
  <div class="uh-bar">
    <label class="uh-search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>
      <input id="uh-q" type="text" placeholder="搜索天体名称 / 类型…" autocomplete="off">
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

<script id="uh-data" type="application/json">{"name":"可观测宇宙","type":"宇宙边界","info":"半径约465亿光年，ΛCDM标准模型","source":"NASA / ΛCDM","children":[{"name":"双鱼-鲸鱼座超星系团复合体","type":"超星系团复合体","info":"拉尼亚凯亚超星系团隶属于该复合体","source":"Tully et al. 2014","children":[{"name":"拉尼亚凯亚超星系团","type":"超星系团","info":"引力中心：巨引源；包含本星系群、室女座星系团、M81星系群","source":"Tully et al. 2014","children":[{"name":"本星系群","type":"星系群","info":"约50余个星系，无中心巨椭圆星系","source":"NASA","children":[{"name":"银河系","type":"棒旋星系","info":"直径约10万光年，包含数千亿恒星","source":"ESA","children":[{"name":"银核","type":"星系核心区域","info":"高密度恒星核心，包含中心黑洞","source":"EHT","children":[{"name":"人马座A* (Sgr A*)","type":"超大质量黑洞","info":"银河系中心黑洞，430万倍太阳质量","source":"EHT 2022"}]},{"name":"银盘","type":"星系盘","info":"银河系恒星、星云主要分布区域，分为多条旋臂","source":"ESA","children":[{"name":"盾牌-半人马臂","type":"主旋臂","info":"银河系内侧主旋臂","children":[{"name":"海山二","type":"高光度蓝变星（双星系统）","info":"质量巨大，不稳定，高光度蓝变星","source":"ESA","repo_id":"eta_carinae"},{"name":"老人星","type":"黄超巨星","info":"全天第二亮恒星","source":"NASA"}]},{"name":"英仙臂","type":"主旋臂","info":"外侧主旋臂，大量亮星云、星团","children":[{"name":"M36 疏散星团","type":"疏散星团","info":"年轻星团"},{"name":"M37 疏散星团","type":"疏散星团","info":"银河系最富疏散星团之一"},{"name":"M38 疏散星团","type":"疏散星团"}]},{"name":"猎户臂（本地臂）","type":"次级旋臂","info":"我们所在的次级旋臂，太阳就在这里","source":"NASA","children":[{"name":"太阳系统","type":"恒星系统","info":"G2V黄矮星，太阳系引力中心","source":"NASA","children":[{"name":"内行星系统","type":"行星分组","children":[{"name":"水星","type":"类地行星","info":"无卫星","repo_id":"mercury"},{"name":"金星","type":"类地行星","info":"无卫星","repo_id":"venus"},{"name":"地球","type":"类地行星","children":[{"name":"月球","type":"天然卫星","repo_id":"moon"}],"repo_id":"earth"},{"name":"火星","type":"类地行星","children":[{"name":"火卫一（福波斯）","type":"天然卫星","repo_id":"phobos"},{"name":"火卫二（德莫斯）","type":"天然卫星","repo_id":"deimos"}],"repo_id":"mars"}]},{"name":"主小行星带","type":"小行星带","children":[{"name":"谷神星","type":"矮行星","repo_id":"ceres"},{"name":"灶神星","type":"原行星","repo_id":"vesta"},{"name":"智神星","type":"小行星","repo_id":"pallas"},{"name":"婚神星","type":"小行星","repo_id":"juno"},{"name":"健神星","type":"小行星","repo_id":"hygiea"}]},{"name":"外行星系统","type":"行星分组","children":[{"name":"木星","type":"气态巨行星","info":"已知卫星极多，这里列出知名大卫星","children":[{"name":"木卫一（伊奥）","type":"天然卫星","repo_id":"io"},{"name":"木卫二（欧罗巴）","type":"天然卫星","repo_id":"europa"},{"name":"木卫三（盖尼米德）","type":"天然卫星","repo_id":"ganymede"},{"name":"木卫四（卡利斯托）","type":"天然卫星","repo_id":"callisto"},{"name":"木卫五（阿马尔忒亚）","type":"天然卫星"},{"name":"木卫六（希玛利亚）","type":"天然卫星"},{"name":"木卫七（伊拉拉）","type":"天然卫星"},{"name":"木卫八（帕西法尔）","type":"天然卫星"}],"repo_id":"jupiter"},{"name":"土星","type":"气态巨行星","info":"行星环系统，卫星数量极多，列出经典知名卫星","children":[{"name":"土卫六（泰坦）","type":"天然卫星","repo_id":"titan"},{"name":"土卫二（恩克拉多斯）","type":"天然卫星","repo_id":"enceladus"},{"name":"土卫一（弥玛斯）","type":"天然卫星","repo_id":"mimas"},{"name":"土卫三（忒堤斯）","type":"天然卫星","repo_id":"tethys"},{"name":"土卫四（狄俄涅）","type":"天然卫星","repo_id":"dione"},{"name":"土卫五（瑞亚）","type":"天然卫星","repo_id":"rhea"},{"name":"土卫八（伊阿珀托斯）","type":"天然卫星","repo_id":"iapetus"},{"name":"土卫九（菲比）","type":"天然卫星"},{"name":"土卫七","type":"天然卫星","info":"形状极不规则的卫星，混沌自转使它的朝向无法预测","repo_id":"hyperion"}],"repo_id":"saturn"},{"name":"天王星","type":"冰巨行星","children":[{"name":"天卫一（艾瑞尔）","type":"天然卫星","repo_id":"ariel"},{"name":"天卫二（乌姆布里尔）","type":"天然卫星","repo_id":"umbriel"},{"name":"天卫三（泰坦妮亚）","type":"天然卫星","repo_id":"titania"},{"name":"天卫四（奥伯龙）","type":"天然卫星","repo_id":"oberon"},{"name":"天卫五（米兰达）","type":"天然卫星","repo_id":"miranda"}],"repo_id":"uranus"},{"name":"海王星","type":"冰巨行星","children":[{"name":"海卫一（特里同）","type":"天然卫星","repo_id":"triton"},{"name":"海卫二（涅瑞伊得）","type":"天然卫星"},{"name":"海卫八（普洛透斯）","type":"天然卫星"}],"repo_id":"neptune"}]},{"name":"柯伊伯带","type":"外海王星天体带","children":[{"name":"冥王星","type":"矮行星","children":[{"name":"冥卫一（卡戎）","type":"天然卫星"},{"name":"冥卫二（尼克斯）","type":"天然卫星"},{"name":"冥卫三（许德拉）","type":"天然卫星"}],"repo_id":"pluto"},{"name":"阋神星","type":"矮行星","repo_id":"eris"},{"name":"妊神星","type":"矮行星","repo_id":"haumea"},{"name":"鸟神星","type":"矮行星","repo_id":"makemake"},{"name":"亡神星","type":"矮行星","repo_id":"orcus"},{"name":"共工星","type":"矮行星","info":"柯伊伯带离散盘冰质矮行星，以中国水神共工命名","repo_id":"gonggong_225088"},{"name":"创神星","type":"矮行星","info":"柯伊伯带矮行星，拥有行星环，位于海王星轨道外侧","repo_id":"quaoar"},{"name":"赛德娜","type":"矮行星","info":"外海王星矮行星，轨道极扁，远日点极其遥远","repo_id":"sedna"}]},{"name":"奥尔特云","type":"彗星储库","info":"太阳系最外层边界"},{"name":"哈雷彗星","type":"彗星","info":"每 76 年回归一次的著名周期彗星，肉眼可见的脏雪球","repo_id":"halley"}]},{"name":"南门二（半人马α）三合星系统","type":"多星系统","info":"距离太阳4.37光年","source":"ESA","children":[{"name":"南门二A","type":"G2V主序星"},{"name":"南门二B","type":"K1V橙色矮星"},{"name":"比邻星（南门二C）","type":"M5.5V红矮星","info":"距离太阳4.22光年，离我们最近恒星","children":[{"name":"比邻星b","type":"系外行星（已确认，宜居带类地）","repo_id":"proxima_centauri_b"},{"name":"比邻星c","type":"系外行星（候选，超级地球）"},{"name":"比邻星d","type":"系外行星（已确认，极小类地）"}],"repo_id":"proxima_centauri"}]},{"name":"巴纳德星","type":"M4V红矮星","info":"距离5.96光年，自行很高；巴纳德星b已证伪","source":"NASA"},{"name":"天狼星双星系统","type":"双星系统","info":"全天最亮恒星，距离8.6光年","source":"NASA","children":[{"name":"天狼星A","type":"A1V主序星"},{"name":"天狼星B","type":"白矮星伴星"}]},{"name":"南河三双星系统","type":"双星系统","info":"距离11.4光年","source":"NASA","children":[{"name":"南河三A","type":"F5IV主序星"},{"name":"南河三B","type":"白矮星伴星"}]},{"name":"织女星","type":"A0V主序星","info":"天琴座α，距离25光年","source":"NASA","repo_id":"vega"},{"name":"大角星","type":"红巨星","info":"牧夫座α，距离37光年","source":"NASA","repo_id":"arcturus"},{"name":"牛郎星（河鼓二）","type":"A7V主序星","info":"天鹰座α，距离16.7光年","source":"NASA"},{"name":"天津四","type":"蓝超巨星","info":"天鹅座α，距离约2600光年","source":"ESA","repo_id":"deneb"},{"name":"心宿二","type":"红超巨星","info":"天蝎座α","source":"NASA","repo_id":"antares"},{"name":"毕宿五","type":"红巨星","info":"金牛座α","source":"NASA","repo_id":"aldebaran"},{"name":"五车二（御夫座α）四星系统","type":"四星系统","info":"两对双星互相绕转","source":"NASA","children":[{"name":"五车二Aa","type":"G型巨星"},{"name":"五车二Ab","type":"G型巨星"},{"name":"五车二Ba","type":"M型矮星"},{"name":"五车二Bb","type":"M型矮星"}],"repo_id":"capella"},{"name":"北河二（双子座α）六合星系统","type":"六合星系统","info":"三组双星构成","source":"NASA","children":[{"name":"北河二A1/A2","type":"双星对子"},{"name":"北河二B1/B2","type":"双星对子"},{"name":"北河二C1/C2","type":"双星对子"}],"repo_id":"castor"},{"name":"北河三（双子座β）","type":"红巨星","info":"拥有行星北河三b（Thestias）","source":"NASA","children":[{"name":"北河三b","type":"系外行星（已确认，气态巨行星）"}],"repo_id":"pollux"},{"name":"盾牌座UY","type":"红超巨星","info":"体积巨大的红超巨星","source":"NASA"},{"name":"史蒂文森2-18","type":"红超巨星","info":"已知体积最大红超巨星之一","source":"NASA"},{"name":"TRAPPIST-1系统","type":"恒星系统","info":"M8V红矮星，7颗类地行星，多颗宜居带","children":[{"name":"TRAPPIST-1 b","type":"系外行星"},{"name":"TRAPPIST-1 c","type":"系外行星"},{"name":"TRAPPIST-1 d","type":"系外行星"},{"name":"TRAPPIST-1 e","type":"系外行星（宜居带）"},{"name":"TRAPPIST-1 f","type":"系外行星（宜居带）"},{"name":"TRAPPIST-1 g","type":"系外行星（宜居带）"},{"name":"TRAPPIST-1 h","type":"系外行星"}]},{"name":"开普勒-452系统","type":"恒星系统","children":[{"name":"开普勒452b","type":"系外行星（超级地球，候选宜居）","repo_id":"kepler_452b"}]},{"name":"开普勒-22系统","type":"恒星系统","children":[{"name":"开普勒22b","type":"系外行星（超级地球）","repo_id":"kepler_22b"}]},{"name":"开普勒-16双星系统","type":"双星系统","children":[{"name":"开普勒16A","type":"主序星"},{"name":"开普勒16B","type":"红矮星"},{"name":"开普勒16b","type":"系外行星（环双星行星）","repo_id":"kepler_16b"}]},{"name":"PSR B1257+12 脉冲星系统","type":"脉冲星系统","info":"人类最早发现的系外行星宿主","children":[{"name":"PSR B1257+12 b","type":"脉冲星行星"},{"name":"PSR B1257+12 c","type":"脉冲星行星"},{"name":"PSR B1257+12 d","type":"脉冲星行星"}]},{"name":"格利泽581","type":"M型红矮星","info":"格利泽581g/d存在争议，未被确认","children":[{"name":"格利泽581b","type":"系外行星（已确认）"},{"name":"格利泽581c","type":"系外行星（已确认）"},{"name":"格利泽581e","type":"系外行星（已确认）"},{"name":"格利泽581g","type":"系外行星（争议）"}]},{"name":"M42 猎户座大星云","type":"发射星云","info":"恒星形成区"},{"name":"M16 鹰星云（创生之柱）","type":"发射星云","info":"恒星形成区"},{"name":"M1 蟹状星云","type":"超新星遗迹","info":"1054年超新星爆发遗迹"},{"name":"M78 星云","type":"反射星云","info":"猎户座反射星云"},{"name":"马头星云","type":"暗星云","info":"巴纳德33","repo_id":"horsehead"},{"name":"M57 环状星云","type":"行星状星云"},{"name":"M27 哑铃星云","type":"行星状星云"}]},{"name":"人马臂","type":"主旋臂","info":"内侧主旋臂"},{"name":"外缘臂","type":"旋臂","info":"银河系最外侧旋臂"},{"name":"天鹅星云","type":"星云","info":"银河系中最亮的发射星云之一，形似一只展翅的天鹅","repo_id":"m17"},{"name":"船底座星云","type":"星云","info":"全天最大最亮的星云之一，藏着最不稳定的巨星海山二","repo_id":"ngc3372"},{"name":"北美洲星云","type":"星云","info":"形状酷似北美洲大陆的发射星云","repo_id":"ngc7000"}]},{"name":"银晕","type":"星系晕","info":"暗物质晕 + 球状星团分布区","source":"ESA","children":[{"name":"球状星团集合","type":"星团分组","children":[{"name":"ω半人马座星团","type":"球状星团"},{"name":"杜鹃座47","type":"球状星团"},{"name":"M13 武仙座球状星团","type":"球状星团"},{"name":"M22","type":"球状星团"},{"name":"M5","type":"球状星团"},{"name":"M15","type":"球状星团"},{"name":"M92","type":"球状星团"}]},{"name":"疏散星团集合","type":"星团分组","children":[{"name":"M45 昴星团","type":"疏散星团"},{"name":"M67","type":"疏散星团"},{"name":"毕星团","type":"星团","info":"金牛座的 V 形头部，离太阳最近的疏散星团之一","repo_id":"hyades"},{"name":"蜂巢星团","type":"星团","info":"巨蟹座腹中的蜂巢，双筒望远镜里的经典星团","repo_id":"m44"},{"name":"野鸭星团","type":"星团","info":"数千颗恒星挤成三角阵，像一群列队飞翔的野鸭","repo_id":"m11"},{"name":"托勒密星团","type":"星团","info":"两千年前就被古人记进星表的疏散星团","repo_id":"m7"}]}]},{"name":"银河系卫星矮星系","type":"卫星星系分组","children":[{"name":"大麦哲伦云","type":"不规则矮星系","children":[{"name":"蜘蛛星云","type":"星云","info":"大麦哲伦云里的巨型恒星工厂，本星系群最活跃的星云","children":[{"name":"R136 星团","type":"星团","info":"蜘蛛星云核心的超级星团，已知最亮恒星的故乡","children":[{"name":"R136a1","type":"恒星","info":"目前已知质量最大的恒星，藏在蜘蛛星云核心","repo_id":"r136a1"}],"repo_id":"r136"}],"repo_id":"tarantula"}],"repo_id":"lmc"},{"name":"小麦哲伦云","type":"不规则矮星系","repo_id":"smc"},{"name":"人马座矮椭球星系","type":"矮椭球星系"},{"name":"大犬座矮星系","type":"矮不规则星系"},{"name":"小熊座矮星系","type":"矮椭球星系"},{"name":"天龙座矮星系","type":"矮椭球星系"}]}],"repo_id":"milky_way"},{"name":"仙女座星系 M31","type":"棒旋星系","info":"本星系群最大星系，未来会和银河系并合","children":[{"name":"M32","type":"矮椭圆卫星星系"},{"name":"M110","type":"矮椭圆卫星星系"},{"name":"仙女座Ⅰ","type":"矮椭球卫星星系"},{"name":"仙女座Ⅱ","type":"矮椭球卫星星系"}]},{"name":"三角座星系 M33","type":"旋涡星系","info":"本星系群第三大星系"},{"name":"IC 10","type":"不规则矮星系"},{"name":"NGC 147","type":"矮椭圆星系"},{"name":"NGC 185","type":"矮椭圆星系"}],"repo_id":"local_group"},{"name":"室女座星系团","type":"富星系团","info":"拉尼亚凯亚内部大型富星系团","children":[{"name":"M87星系","type":"巨椭圆星系","children":[{"name":"M87*","type":"超大质量黑洞","source":"EHT 2019","repo_id":"m87_star"}]},{"name":"M49","type":"巨椭圆星系"},{"name":"M60","type":"巨椭圆星系"},{"name":"M104 草帽星系","type":"旋涡星系"}],"repo_id":"virgo_cluster"},{"name":"M81星系群","type":"星系群","children":[{"name":"M81","type":"旋涡星系"},{"name":"M82","type":"星暴星系"}]},{"name":"巨引源","type":"宇宙结构","info":"隐匿在银河盘面背后的引力深渊，牵引着本超星系团","repo_id":"great_attractor"}],"repo_id":"laniakea"}]},{"name":"武仙-北冕座长城","type":"巨型宇宙纤维","info":"已知超大尺度宇宙结构","source":"NASA","repo_id":"hercules_corona_wall"},{"name":"夏普利超星系团","type":"超星系团","info":"遥远、质量巨大的致密超星系团，不在拉尼亚凯亚内","source":"NASA"},{"name":"后发座星系团","type":"富星系团","info":"遥远致密富星系团"},{"name":"宇宙微波背景","type":"宇宙结构","info":"大爆炸的余晖，宇宙最古老的光（最后散射面）","repo_id":"cmb"}],"repo_id":"observable_universe"}</script>
<script>
document.addEventListener('DOMContentLoaded', function () {
  var DATA = JSON.parse(document.getElementById('uh-data').textContent);
  var CAT_COLOR = {
    '宇宙结构':'#f06292','星系':'#ba68c8','星云':'#4db6ac','恒星':'#ffd54f',
    '行星':'#64b5f6','卫星':'#4dd0e1','星团':'#81c784','矮行星':'#ffb74d',
    '小行星':'#b0bec5','彗星':'#cfd8dc','黑洞':'#e57373','其他':'#90a4ae'
  };
  var CAT_ORDER = ['宇宙结构','星系','星云','恒星','行星','卫星','星团','矮行星','小行星','彗星','黑洞','其他'];
  function catOf(t){
    t = t || '';
    if (/黑洞/.test(t)) return '黑洞';
    if (/星云/.test(t)) return '星云';
    if (/(超星系团|复合体|长城|星系团|星系群|纤维|宇宙|结构|边界|晕|星系盘|核心区域|分组|储库|系统)/.test(t)) return '宇宙结构';
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
  function colorOf(t){ return CAT_COLOR[catOf(t)]; }
  var CAT_SET = new Set();
  (function collect(n){ CAT_SET.add(catOf(n.type)); (n.children||[]).forEach(collect); })(DATA);

  var expanded = new Set();
  var activeTypes = new Set();
  var query = '';
  var treeEl = document.getElementById('uh-tree');
  var crumbEl = document.getElementById('uh-crumb');

  function pathOf(parent, name){ return parent ? parent + '/' + name : name; }
  function countDesc(n){ var c=0; (n.children||[]).forEach(function(x){ c += 1 + countDesc(x); }); return c; }
  function matches(n){
    if (activeTypes.size && !activeTypes.has(catOf(n.type))) return false;
    if (!query) return true;
    var q = query.toLowerCase();
    return (n.name||'').toLowerCase().indexOf(q) >= 0 || (n.type||'').toLowerCase().indexOf(q) >= 0;
  }
  function subHasMatch(n){ if (matches(n)) return true; return (n.children||[]).some(subHasMatch); }

  function renderNode(n, parentPath, depth, ancestors){
    var path = pathOf(parentPath, n.name);
    var hasKids = (n.children||[]).length > 0;
    var filtering = query || activeTypes.size > 0;
    var isOpen = expanded.has(path) || (!filtering && depth < 2) || (filtering && (n.children||[]).some(subHasMatch));
    var node = document.createElement('div'); node.className = 'uh-node';

    var head = document.createElement('div'); head.className = 'uh-head';
    var ar = document.createElement('span');
    ar.className = 'uh-arrow' + (hasKids ? '' : ' leaf') + (isOpen ? ' open' : '');
    ar.innerHTML = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
    var nm = document.createElement('span'); nm.className = 'uh-nm';
    if (query){
      var idx = (n.name||'').toLowerCase().indexOf(query.toLowerCase());
      if (~idx && query){
        nm.innerHTML = esc(n.name.slice(0,idx)) + '<mark>' + esc(n.name.slice(idx, idx+query.length)) + '</mark>' + esc(n.name.slice(idx+query.length));
      } else nm.textContent = n.name;
    } else nm.textContent = n.name;
    var badge = document.createElement('span'); badge.className = 'uh-badge';
    badge.style.background = colorOf(n.type); badge.textContent = n.type || '';
    head.appendChild(ar); head.appendChild(nm); head.appendChild(badge);
    if (n.repo_id){
      var link = document.createElement('a'); link.className = 'uh-link';
      link.href = '/objects/' + n.repo_id + '/'; link.title = '查看本站详情卡片';
      link.textContent = '↗';
      link.addEventListener('click', function(e){ e.stopPropagation(); });
      head.appendChild(link);
    }
    if (hasKids){ var c = document.createElement('span'); c.className = 'uh-cnt'; c.textContent = countDesc(n); head.appendChild(c); }

    head.addEventListener('click', function (){
      if (hasKids){ if (expanded.has(path)) expanded.delete(path); else expanded.add(path); }
      crumbEl.innerHTML = ancestors.concat([n.name]).map(function(a){
        return '<span class="uh-sep">›</span><b>' + esc(a) + '</b>';
      }).join(' ');
      render();
    });
    node.appendChild(head);

    if (hasKids){
      var kids = document.createElement('div'); kids.className = 'uh-children';
      var list = filtering ? n.children.filter(subHasMatch) : n.children;
      list.forEach(function(c){ kids.appendChild(renderNode(c, path, depth+1, ancestors.concat([n.name]))); });
      kids.classList.toggle('collapsed', !isOpen);
      node.appendChild(kids);
    }
    return node;
  }

  function esc(s){ return (s||'').replace(/[&<>]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }

  function render(){
    treeEl.innerHTML = '';
    if (query || activeTypes.size){
      var list = DATA.children.filter(subHasMatch);
      if (!list.length){ treeEl.innerHTML = '<div class="uh-empty">没有匹配的天体。试试别的名称或清空筛选。</div>'; return; }
      list.forEach(function(c){ treeEl.appendChild(renderNode(c, '', 1, [])); });
    } else {
      treeEl.appendChild(renderNode(DATA, '', 0, []));
    }
  }

  var chipsEl = document.getElementById('uh-chips');
  CAT_ORDER.filter(function(c){ return CAT_SET.has(c); }).forEach(function(t){
    var c = document.createElement('span'); c.className = 'uh-chip';
    c.innerHTML = '<span class="uh-dot" style="background:' + CAT_COLOR[t] + '"></span>' + t;
    c.addEventListener('click', function (){
      if (activeTypes.has(t)){ activeTypes.delete(t); c.classList.remove('on'); }
      else { activeTypes.add(t); c.classList.add('on'); }
      render();
    });
    chipsEl.appendChild(c);
  });
  var legendEl = document.getElementById('uh-legend');
  CAT_ORDER.filter(function(c){ return CAT_SET.has(c); }).forEach(function(t){
    var s = document.createElement('span');
    s.innerHTML = '<i style="background:' + CAT_COLOR[t] + '"></i>' + t;
    legendEl.appendChild(s);
  });

  document.getElementById('uh-q').addEventListener('input', function(e){ query = e.target.value.trim(); render(); });
  document.getElementById('uh-expand').addEventListener('click', function (){
    (function walk(n, p){
      var path = pathOf(p, n.name);
      if ((n.children||[]).length){ expanded.add(path); n.children.forEach(function(c){ walk(c, path); }); }
    })(DATA, '');
    render();
  });
  document.getElementById('uh-collapse').addEventListener('click', function (){ expanded.clear(); render(); });

  render();
});
</script>

> 本页数据由仓库根目录的 `universe-tree.json` 驱动生成（经 `scripts/universe_merge.py` 融合 `universe-data.json` 与 `docs/data/astro.json`）；数据源改动后随 `mkdocs build` 自动同步，无需手动操作。
