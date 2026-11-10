#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_universe_html.py — 由 universe-tree.json 生成自包含静态 HTML 思维导图。

产出 docs/universe-hierarchy.html：
  - JSON 内嵌（<script type="application/json">），可离线/直接打开，无需 fetch。
  - 贴合「星野笔记」Material 深色风格（indigo/slate 配色）。
  - 交互：折叠树、搜索(名称+类型)、类型筛选 chips、展开/折叠全部、面包屑路径。
universe-tree.json 为唯一事实源；改 JSON 后重跑本脚本即可刷新 HTML。
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREE = os.path.join(ROOT, "universe-tree.json")
OUT  = os.path.join(ROOT, "docs", "universe-hierarchy.html")

with open(TREE, encoding="utf-8") as f:
    data = json.load(f)
tree_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>宇宙天体层级思维导图 ｜ 星野笔记</title>
<style>
  :root{
    --bg:#0b0e1a; --panel:#11152a; --panel2:#161b34;
    --line:rgba(255,255,255,.10); --line2:rgba(255,255,255,.06);
    --txt:#e6edf6; --muted:#9aa6c4; --accent:#7c8cff; --accent2:#5c6bc0;
    --hi:#ffd54f;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{background:var(--bg);color:var(--txt);
    font-family:system-ui,-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
    font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
  .wrap{max-width:1100px;margin:0 auto;padding:18px 16px 60px}
  .topbar{position:sticky;top:0;z-index:20;background:linear-gradient(180deg,var(--bg) 70%,rgba(11,14,26,.85));
    padding:6px 0 12px;backdrop-filter:blur(6px)}
  h1{font-size:19px;font-weight:700;letter-spacing:.5px}
  h1 .em{color:var(--accent)}
  .back{display:inline-flex;align-items:center;gap:4px;margin-left:10px;font-size:12px;
    color:var(--muted);text-decoration:none;border:1px solid var(--line);border-radius:999px;
    padding:3px 10px;vertical-align:middle;transition:.15s}
  .back:hover{color:var(--txt);border-color:var(--accent2);background:var(--panel)}
  .sub{color:var(--muted);font-size:12px;margin-top:2px}
  .toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
  .search{flex:1 1 220px;min-width:180px;display:flex;align-items:center;gap:6px;
    background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:7px 10px}
  .search input{flex:1;background:transparent;border:0;outline:0;color:var(--txt);font-size:14px}
  .search svg{width:15px;height:15px;fill:var(--muted);flex:none}
  .btn{background:var(--panel);border:1px solid var(--line);color:var(--txt);
    border-radius:8px;padding:7px 11px;cursor:pointer;font-size:13px;transition:.15s}
  .btn:hover{background:var(--panel2);border-color:var(--accent2)}
  .chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
  .chip{font-size:12px;padding:4px 10px;border-radius:999px;border:1px solid var(--line);
    background:var(--panel);color:var(--muted);cursor:pointer;user-select:none;transition:.15s;display:flex;align-items:center;gap:5px}
  .chip .dot{width:8px;height:8px;border-radius:50%;background:var(--c,#888)}
  .chip.on{color:var(--txt);border-color:var(--accent2);background:var(--panel2)}
  .crumb{margin:14px 0 6px;font-size:12px;color:var(--muted);min-height:18px;
    display:flex;flex-wrap:wrap;gap:4px;align-items:center}
  .crumb b{color:var(--accent)}
  .crumb .sep{opacity:.5}
  .tree{margin-top:6px}
  .node{position:relative}
  .node-children{margin-left:14px;padding-left:12px;border-left:1px solid var(--line2)}
  .node-children.collapsed{display:none}
  .head{display:flex;align-items:center;gap:7px;padding:5px 8px;border-radius:7px;cursor:pointer;transition:.12s}
  .head:hover{background:var(--panel)}
  .arrow{width:14px;height:14px;flex:none;fill:var(--muted);transition:transform .15s}
  .arrow.leaf{opacity:0}
  .arrow.open{transform:rotate(90deg)}
  .nm{font-weight:600}
  .badge{font-size:11px;padding:1px 8px;border-radius:999px;color:#0b0e1a;font-weight:700;white-space:nowrap}
  .cnt{font-size:11px;color:var(--muted);margin-left:auto;flex:none}
  .meta{padding:0 8px 6px 29px;color:var(--muted);font-size:12px;line-height:1.55}
  .meta .src{color:#7f8bb0}
  .meta .src::before{content:"📚 "}
  mark{background:var(--hi);color:#1a1300;border-radius:3px;padding:0 1px}
  .empty{color:var(--muted);text-align:center;padding:30px;font-size:13px}
  .legend{margin-top:22px;border-top:1px solid var(--line2);padding-top:12px;
    display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:var(--muted)}
  .legend span{display:flex;align-items:center;gap:5px}
  .legend i{width:9px;height:9px;border-radius:50%;display:inline-block}
  @media (max-width:560px){
    .wrap{padding:12px 10px 50px}
    h1{font-size:17px}
    .node-children{margin-left:9px;padding-left:9px}
    .meta{padding-left:23px}
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <h1>🌌 宇宙天体<span class="em">层级思维导图</span><a class="back" href="/">← 返回星野笔记</a></h1>
    <div class="sub">按「引力从属 / 包含关系」组织的天体层级 · 数据来源：外部层级文档 + 星野笔记天体库（astro.json）融合</div>
    <div class="toolbar">
      <label class="search">
        <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>
        <input id="q" type="text" placeholder="搜索天体名称 / 类型…" autocomplete="off">
      </label>
      <button class="btn" id="expandAll">展开全部</button>
      <button class="btn" id="collapseAll">折叠全部</button>
    </div>
    <div class="chips" id="chips"></div>
  </div>
  <div class="crumb" id="crumb"></div>
  <div class="tree" id="tree"></div>
  <div class="legend" id="legend"></div>
</div>

<script id="tree-data" type="application/json">__TREE__</script>
<script>
const DATA = JSON.parse(document.getElementById('tree-data').textContent);
const CAT_COLOR={
  '宇宙结构':'#f783ac','星系':'#b388ff','星云':'#4dd0c4','恒星':'#ffd166',
  '行星':'#5b9bff','卫星':'#56c5e8','星团':'#69db7c','矮行星':'#ffa94d',
  '小行星':'#adb5bd','彗星':'#ced4da','黑洞':'#ff6b6b','其他':'#90a4ae'
};
const CAT_ORDER=['宇宙结构','星系','星云','恒星','行星','卫星','星团','矮行星','小行星','彗星','黑洞','其他'];
// 把自由文本 type 归并到受控粗分类（层级思维导图按大类着色/筛选）
function catOf(t){
  t=t||'';
  if(/黑洞/.test(t)) return '黑洞';
  if(/星云/.test(t)) return '星云';
  if(/(超星系团|复合体|长城|星系团|星系群|纤维|宇宙|结构|边界|晕|星系盘|核心区域|分组|储库|系统)/.test(t)) return '宇宙结构';
  if(/恒星|主序|巨星|矮星|变星/.test(t)) return '恒星';
  if(/行星/.test(t)) return '行星';
  if(/卫星/.test(t)) return '卫星';
  if(/星团/.test(t)) return '星团';
  if(/矮行星/.test(t)) return '矮行星';
  if(/小行星/.test(t)) return '小行星';
  if(/彗星/.test(t)) return '彗星';
  if(/星系/.test(t)) return '星系';
  return '其他';
}
function colorOf(t){ return CAT_COLOR[catOf(t)]; }
// 收集出现的粗分类
const CAT_SET=new Set();
(function collect(n){ CAT_SET.add(catOf(n.type)); (n.children||[]).forEach(collect); })(DATA);

const expanded = new Set();          // 已展开节点的 path 集合
const activeTypes = new Set();       // 类型筛选（空=全部）
let query='';
const treeEl=document.getElementById('tree');
const crumbEl=document.getElementById('crumb');

function pathOf(parent, name){ return parent ? parent+'/'+name : name; }

function countDesc(n){ let c=0; (n.children||[]).forEach(x=>{c+=1+countDesc(x);}); return c; }

function matches(n){
  if(activeTypes.size && !activeTypes.has(catOf(n.type))) return false;
  if(!query) return true;
  const q=query.toLowerCase();
  return (n.name||'').toLowerCase().includes(q) || (n.type||'').toLowerCase().includes(q);
}
// 子树是否存在匹配（自身或后代）
function subHasMatch(n){
  if(matches(n)) return true;
  return (n.children||[]).some(subHasMatch);
}

function renderNode(n, parentPath, depth, ancestors){
  const path=pathOf(parentPath, n.name);
  const hasKids=(n.children||[]).length>0;
  const filtering = query || activeTypes.size>0;
  const isOpen = expanded.has(path) || (!filtering && depth<2) || (filtering && (n.children||[]).some(subHasMatch));
  const node=document.createElement('div'); node.className='node';

  const head=document.createElement('div'); head.className='head';
  const ar=document.createElement('span');
  ar.className='arrow'+(hasKids?'':' leaf')+(isOpen?' open':'');
  ar.innerHTML='<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
  const nm=document.createElement('span'); nm.className='nm';
  if(query){ const idx=(n.name||'').toLowerCase().indexOf(query.toLowerCase());
    if(~idx && query){ nm.innerHTML=esc(n.name.slice(0,idx))+'<mark>'+esc(n.name.slice(idx,idx+query.length))+'</mark>'+esc(n.name.slice(idx+query.length)); }
    else nm.textContent=n.name;
  } else nm.textContent=n.name;
  const badge=document.createElement('span'); badge.className='badge';
  const col=colorOf(n.type); badge.style.background=col; badge.textContent=n.type||'';
  head.appendChild(ar); head.appendChild(nm); head.appendChild(badge);
  if(hasKids){ const c=document.createElement('span'); c.className='cnt'; c.textContent=countDesc(n); head.appendChild(c); }

  head.addEventListener('click',()=>{
    if(hasKids){ if(expanded.has(path)) expanded.delete(path); else expanded.add(path); }
    crumbEl.innerHTML = ancestors.concat([n.name]).map((a,i,arr)=>
      (i?'<span class="sep">›</span>':'')+'<b>'+esc(a)+'</b>').join(' ');
    render();
  });
  node.appendChild(head);

  if(n.info || n.source){
    const meta=document.createElement('div'); meta.className='meta';
    if(n.info) meta.appendChild(document.createTextNode(n.info+' '));
    if(n.source){ const s=document.createElement('span'); s.className='src'; s.textContent=n.source; meta.appendChild(s); }
    node.appendChild(meta);
  }

  if(hasKids){
    const kids=document.createElement('div'); kids.className='node-children';
    // 筛选时仅渲染有匹配的后代（父级已用 subHasMatch 过滤，无需再判空）
    const list = filtering ? n.children.filter(subHasMatch) : n.children;
    list.forEach(c=>kids.appendChild(renderNode(c, path, depth+1, ancestors.concat([n.name]))));
    kids.classList.toggle('collapsed', !isOpen);
    node.appendChild(kids);
  }
  return node;
}

function esc(s){ return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

function render(){
  treeEl.innerHTML='';
  if(query || activeTypes.size){
    const list=DATA.children.filter(subHasMatch);
    if(!list.length){ treeEl.innerHTML='<div class="empty">没有匹配的天体。试试别的名称或清空筛选。</div>'; return; }
    list.forEach(c=>treeEl.appendChild(renderNode(c,'',1,[])));
  } else {
    treeEl.appendChild(renderNode(DATA,'',0,[]));
  }
}

// chips（粗分类筛选）
const chipsEl=document.getElementById('chips');
CAT_ORDER.filter(c=>CAT_SET.has(c)).forEach(t=>{
  const c=document.createElement('span'); c.className='chip';
  c.innerHTML='<span class="dot" style="background:'+CAT_COLOR[t]+'"></span>'+t;
  c.addEventListener('click',()=>{ if(activeTypes.has(t)){activeTypes.delete(t);c.classList.remove('on');}
    else{activeTypes.add(t);c.classList.add('on');} render(); });
  chipsEl.appendChild(c);
});
// legend
const legendEl=document.getElementById('legend');
CAT_ORDER.filter(c=>CAT_SET.has(c)).forEach(t=>{ const s=document.createElement('span');
  s.innerHTML='<i style="background:'+CAT_COLOR[t]+'"></i>'+t; legendEl.appendChild(s); });

document.getElementById('q').addEventListener('input',e=>{ query=e.target.value.trim(); render(); });
document.getElementById('expandAll').addEventListener('click',()=>{
  (function walk(n,p){ const path=pathOf(p, n.name); if((n.children||[]).length){expanded.add(path);n.children.forEach(c=>walk(c,path));} }) (DATA,'');
  render();
});
document.getElementById('collapseAll').addEventListener('click',()=>{ expanded.clear(); render(); });

render();
</script>
</body>
</html>
"""

html = HTML.replace("__TREE__", tree_json)
def iter_nodes(n):
    yield n
    for c in n.get("children", []):
        yield from iter_nodes(c)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", os.path.relpath(OUT, ROOT), "size", len(html), "bytes; embedded nodes:",
      sum(1 for _ in iter_nodes(data)))
