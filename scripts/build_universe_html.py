#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_universe_html.py — 由 universe-tree.json 生成【主题化】的 MkDocs 页面
docs/universe-hierarchy.md。

要点（对齐用户要求）：
  - 页面是 Material 主题内的普通 .md 页：自动带左侧导航、顶部栏、站内搜索、仓库字体/配色。
  - 思维导图内容（树 / 搜索 / 大类筛选 / 折叠 / 面包屑）由 JSON 驱动生成，内嵌在页面里，
    不依赖 iframe、不依赖外部 a.html。
  - 数据按英文 id 关联；中文 / EN 切换只读取 name / name_en 与顶层 type_i18n /
    category_i18n 词表，不做任何名称匹配。展开状态路径用稳定 id，切换语言不丢失。
  - 样式全部使用 Material 主题 CSS 变量（--md-*），随浅/深色切换自动适配，视觉与全站一致。
  - universe-tree.json 为唯一事实源；改 JSON 后随 `mkdocs build` 自动重生（见 universe_hook.py）。
  - 写入前比对磁盘已有内容：内容无变化则跳过写入，避免 mkdocs serve 监听 docs/ 触发重建死循环。
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREE = os.path.join(ROOT, "universe-tree.json")
OUT  = os.path.join(ROOT, "docs", "universe-hierarchy.md")

with open(TREE, encoding="utf-8") as f:
    data = json.load(f)

# —— 节点级 3D 外链（cosmic-web）——
# 主站层级节点 id 与 3D 仓 nodes[] id 命名空间不同（c.kebab vs camelCase），
# 用显式 alias 关联（稳定英文 id，禁止模糊名称匹配）。给匹配节点附加 cosmos3d 外链。
SOLAR3D_BASE = "https://astro-solar-3d.pages.dev"
SOLAR3D_LINKS = os.path.join(ROOT, "scripts", "solar3d_links.json")
NODE3D_ALIASES = {
    # 宇宙结构 / 超星系团 / 星系团 / 星系群
    "observable_universe": "universe",
    "laniakea": "laniakea",
    "c.perseuspisces": "perseuspisces",
    "c.coma-cluster": "coma",
    "c.shapley-supercluster": "shapley",
    "c.hercules": "hercules",
    "c.sculptorsc": "sculptorsc",
    "c.horologium": "horologium",
    "c.pisces-cetus-supercluster-complex": "piscescetus",
    "hercules_corona_wall": "hcbg",
    "c.virgo-supercluster": "virgo",
    "c.hydra-centaurus-sc": "hydra",
    "c.norma": "norma",
    "c.pavoindus": "pavoindus",
    "c.a1367": "a1367",
    "c.a262": "a262",
    "local_group": "localgroup",
    "virgo_cluster": "virgocluster",
    "c.fornax": "fornax",
    "c.eridanus": "eridanus",
    "c.ursamajor": "ursamajor",
    "c.antlia": "antlia",
    "c.centauruscluster": "centauruscluster",
    "c.pegasuscluster": "pegasuscluster",
    "c.m81-group": "m81group",
    "c.centaurus-a-group": "cenagroup",
    "c.sculptorgroup": "sculptorgroup",
    "c.leo1group": "leo1group",
    # 本星系群成员星系
    "milky_way": "milkyway",
    "m31": "andromeda",
    "m33": "triangulum",
    "lmc": "lmc",
    "smc": "smc",
    # 太阳系 / 行星系统
    "c.solar-system": "solar",
    "earth": "earth-moon",
    "mars": "mars",
    "jupiter": "jupiter",
    "saturn": "saturn",
    "uranus": "uranus",
    "neptune": "neptune",
    "pluto": "pluto",
    # 聚星系统（多星系统）
    "sirius": "sys_sirius",
    "alpha_centauri": "sys_alphacen",
    "procyon_a": "sys_procyon",
    "eridani_40": "sys_eridani40",
    "capella": "sys_capella",
    "castor": "sys_castor",
    "kepler_16": "sys_kepler16",
    "epsilon_lyrae": "sys_epsilonlyr",
    "algol": "sys_algol",
    "cyg_x1": "sys_cygx1",
}

def _load_node3d():
    node3d = {}
    try:
        with open(SOLAR3D_LINKS, encoding="utf-8") as f:
            links = json.load(f)
        for n in links.get("nodes", []):
            node3d[n["id"]] = n
    except (OSError, ValueError):
        pass
    return node3d

node3d = _load_node3d()

def _enrich_node(node):
    nid = node.get("id")
    if nid in NODE3D_ALIASES:
        t = node3d.get(NODE3D_ALIASES[nid])
        if t:
            node["cosmos3d"] = SOLAR3D_BASE + "/" + t.get("url", "cosmos.html?node=" + NODE3D_ALIASES[nid])
    for c in node.get("children", []) or []:
        _enrich_node(c)

for _root in [data] + (data.get("non_structure", []) or []):
    _enrich_node(_root)

# 安全嵌入：避免数据里的 "</script" 提前闭合脚本块
tree_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace(
    "</script", "<\\/script"
)

MD = """---
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
.uh-3d{flex:none;margin-left:6px;color:var(--md-accent-fg-color,#7c4dff);font-size:.7rem;font-weight:700;
  text-decoration:none;background:color-mix(in srgb,var(--md-accent-fg-color,#7c4dff) 16%,transparent);
  border:1px solid var(--md-accent-fg-color,#7c4dff);border-radius:6px;padding:1px 6px;transition:.15s}
.uh-3d:hover{opacity:1;text-decoration:none;background:color-mix(in srgb,var(--md-accent-fg-color,#7c4dff) 30%,transparent)}
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

<script id="uh-data" type="application/json">__TREE__</script>
<script>
document.addEventListener('DOMContentLoaded', function () {
  var DATA = JSON.parse(document.getElementById('uh-data').textContent);
  var TYPE_EN = DATA.type_i18n || {};
  var CAT_EN = DATA.category_i18n || {};
  var CAT_COLOR = {
    '宇宙结构':'#f06292','星系':'#ba68c8','星云':'#4db6ac','恒星':'#ffd54f',
    '聚星系统':'#ffa726','行星':'#64b5f6','卫星':'#4dd0e1','星团':'#81c784','矮行星':'#ffb74d',
    '小行星':'#b0bec5','彗星':'#cfd8dc','黑洞':'#e57373','其他':'#90a4ae'
  };
  var CAT_ORDER = ['宇宙结构','星系','星云','恒星','聚星系统','行星','卫星','星团','矮行星','小行星','彗星','黑洞','其他'];
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
      empty: '没有匹配的天体。试试别的名称或清空筛选。', link: '查看本站详情卡片',
      cosmos3d: '在 3D 宇宙网中查看'
    },
    en: {
      intro: 'A hierarchy of celestial objects organized by gravitational affiliation and containment, from the Observable Universe down to planets, moons, clusters and nebulae. Hierarchy comes from universe-data.json; object details in astro.json are linked by a unique English id. Naming follows a strict convention and every affiliation reflects the object real physical nature. Containers marked "Unspecified" mean current sources do not support a finer placement — no guessing. Nodes with ↗ open the object detail card; search supports Chinese names, English names and M/NGC catalog numbers. Use the top-right button in the site header to switch language.',
      search: 'Search name / type / catalog number…', expand: 'Expand all', collapse: 'Collapse all',
      empty: 'No matching objects. Try another name or clear the filters.', link: 'Open object detail card',
      cosmos3d: 'View in 3D cosmic web'
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
      if (/[\u4e00-\u9fff]/.test(n.alias)) al.setAttribute('data-cn-only', '1');
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
    if (n.cosmos3d){
      var l3 = document.createElement('a'); l3.className = 'uh-3d';
      l3.href = n.cosmos3d; l3.target = '_blank'; l3.rel = 'noopener';
      l3.title = T().cosmos3d; l3.textContent = '3D';
      l3.addEventListener('click', function(e){ e.stopPropagation(); });
      head.appendChild(l3);
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
"""

new_html = MD.replace("__TREE__", tree_json)

def iter_nodes(n):
    yield n
    for c in n.get("children", []):
        yield from iter_nodes(c)

os.makedirs(os.path.dirname(OUT), exist_ok=True)

# 写入前比对：内容无变化则跳过，避免 mkdocs serve 监听 docs/ 触发「重写→重建」死循环
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as f:
        old = f.read()
    if old == new_html:
        print("universe-hierarchy.md 内容无变化，跳过写入（避免 mkdocs serve 循环刷新）")
        raise SystemExit(0)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(new_html)
print("wrote", os.path.relpath(OUT, ROOT), "size", len(new_html), "bytes; embedded nodes:",
      sum(1 for _ in iter_nodes(data)))
