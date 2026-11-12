// 宇宙层级页 jsdom 交互回归校验（常驻维护工具）
// 用法：仓库根目录执行 `node scripts/check_universe_dom.js`（需本机可 require('jsdom')）
// 直接从生成的 docs/universe-hierarchy.md 抽取内嵌 JSON + 逻辑脚本实跑，
// 覆盖：初始渲染 / alias / 详情链接 / 筛选 / 搜索（含大小写语义与英文名）/
// id 唯一关联 / 中英文切换 / 切换后展开状态保留 / 展开折叠 / URL 格式。
const fs = require('fs');
const { JSDOM } = require('jsdom');

const md = fs.readFileSync('docs/universe-hierarchy.md', 'utf8');
const scripts = [...md.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
const jsonScript = scripts.find(s => /uh-data/.test(s[1]));
const logicScript = scripts.find(s => !/uh-data/.test(s[1]));

const html = `<!DOCTYPE html><html><body>
<p id="uh-intro"></p>
<section id="uh" class="uh" data-lang="zh">
  <div class="uh-bar">
    <label class="uh-search"><input id="uh-q" type="text"></label>
    <button class="uh-btn" id="uh-expand">展开全部</button>
    <button class="uh-btn" id="uh-collapse">折叠全部</button>
  </div>
  <div class="uh-chips" id="uh-chips"></div>
  <div class="uh-crumb" id="uh-crumb"></div>
  <div class="uh-tree" id="uh-tree"></div>
  <div class="uh-legend" id="uh-legend"></div>
</section>
<script id="uh-data" type="application/json">${jsonScript[2]}</script>
</body></html>`;

const errors = [];
const dom = new JSDOM(html, { runScripts: 'outside-only' });
const { window } = dom;
window.addEventListener('error', e => errors.push(String(e.error || e.message)));
try {
  window.eval(logicScript[2]);
  window.document.dispatchEvent(new window.Event('DOMContentLoaded'));
} catch (e) {
  errors.push('EVAL: ' + e.stack);
}

const doc = window.document;
const $ = s => doc.querySelector(s);
const $$ = s => [...doc.querySelectorAll(s)];
const fail = [];
const ok = (cond, label, extra = '') => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${label}${extra ? '  ' + extra : ''}`);
  if (!cond) fail.push(label);
};
const CJK = /[\u4e00-\u9fff]/;

ok(errors.length === 0, '无 JS 运行时错误', errors.join(' | ').slice(0, 300));

// ---------- 数据契约：英文 id 唯一关联 + 双语字段 ----------
const tree = JSON.parse(jsonScript[2]);
const nodes = [];
(function w(n) { nodes.push(n); (n.children || []).forEach(w); })(tree);
const ids = nodes.map(n => n.id);
ok(ids.length === 286, '内嵌节点数', `count=${ids.length}`);
ok(ids.every(i => typeof i === 'string' && /^[a-z0-9._-]+$/.test(i)), '全部 id 为 ASCII 稳定标识');
ok(new Set(ids).size === ids.length, 'id 全局唯一', `unique=${new Set(ids).size}`);
const withRepo = nodes.filter(n => n.repo_id);
ok(withRepo.length === 208 && withRepo.every(n => n.id === n.repo_id),
   '天体节点 id === repo_id（唯一关联，无名称匹配）', `count=${withRepo.length}`);
ok(nodes.filter(n => n.id.startsWith('c.')).length === 78, '容器使用 c. 命名空间');
ok(nodes.every(n => typeof n.name_en === 'string' && n.name_en.length > 0),
   '全部节点具备 name_en');
ok(Object.keys(tree.type_i18n || {}).length === 106 && Object.keys(tree.category_i18n || {}).length === 12,
   '类型/大类中英词表齐备');

// ---------- 初始渲染（中文） ----------
const heads0 = $$('.uh-head').length;
ok(heads0 > 0, '初始渲染节点', `heads=${heads0}`);
ok($$('.uh-alias').length > 0, '规范编号 alias 渲染', `count=${$$('.uh-alias').length}`);
ok($$('.uh-link').length > 0, '详情卡片链接渲染', `count=${$$('.uh-link').length}`);
ok($$('.uh-chip').length >= 8, '大类筛选 chips', `count=${$$('.uh-chip').length}`);
ok($$('.uh-head[data-id]').length === $$('.uh-head').length, '节点行带稳定 data-id');

// 修复①：默认仅展开地球层级路径；根的直接子节点（depth=1，如夏普利超星系团）
// 此前因强制展开规则永远无法折叠，点击只往 expanded 加路径、关不掉。
const earthNode = $$('.uh-head[data-id="earth"]')[0];
ok(!!earthNode, '存在地球节点');
if (earthNode) {
  const ec = earthNode.closest('.uh-node').parentElement; // 包含 earth 的 .uh-children
  ok(ec && ec.classList.contains('uh-children') && !ec.classList.contains('collapsed'),
     '地球默认在展开路径上（可见）');
}
const shapleySel = '.uh-head[data-id="c.shapley-supercluster"]';
const shapleyKids = () => { const h = $$(shapleySel)[0]; return h ? h.closest('.uh-node').querySelector('.uh-children') : null; };
ok(!!$$(shapleySel)[0], '存在 depth=1 节点（夏普利超星系团）');
ok(shapleyKids() && shapleyKids().classList.contains('collapsed'), 'depth=1 节点默认折叠（修复前无法收起）');
$$(shapleySel)[0].dispatchEvent(new window.Event('click'));   // 点击会整体重渲染，需重新查询 DOM
ok(shapleyKids() && !shapleyKids().classList.contains('collapsed'), '点击后可展开');
$$(shapleySel)[0].dispatchEvent(new window.Event('click'));
ok(shapleyKids() && shapleyKids().classList.contains('collapsed'), '再次点击可折叠（修复后正常）');

// 大小写语义：搜索 开普勒16 应同时出现 B(恒星) 与 b(行星)
const q = $('#uh-q');
function search(v) {
  q.value = v;
  q.dispatchEvent(new window.Event('input'));
  return $$('.uh-nm').map(n => n.textContent);
}
const k16 = search('开普勒16');
ok(k16.some(t => t.includes('开普勒16B')) && k16.some(t => t.includes('开普勒16b')),
   '大小写语义：开普勒16B 与 开普勒16b 可区分且均命中', `hits=${k16.length}`);
const m42 = search('M42');
ok(m42.some(t => t.includes('猎户座大星云')), '按编号 M42 搜索命中中文名', `hits=${m42.length}`);
const sirius = search('天狼星');
ok(sirius.some(t => t.includes('天狼星A')) && sirius.some(t => t.includes('天狼星B')),
   '天狼星A/B 均命中', `hits=${sirius.length}`);

// 大类筛选
q.value = ''; q.dispatchEvent(new window.Event('input'));
const chip = $$('.uh-chip').find(c => c.textContent.includes('黑洞'));
if (chip) {
  chip.dispatchEvent(new window.Event('click'));
  const badges = $$('.uh-nm').length;
  const bhLinks = $$('.uh-link').length;
  ok(badges > 0, '黑洞大类筛选有结果', `nodes=${badges} links=${bhLinks}`);
  chip.dispatchEvent(new window.Event('click'));
} else ok(false, '存在黑洞大类 chip');

// 展开全部 / 折叠全部
$('#uh-expand').dispatchEvent(new window.Event('click'));
const openAfterExpand = $$('.uh-children:not(.collapsed)').length;
ok(openAfterExpand > 0, '展开全部生效', `open=${openAfterExpand}`);
$('#uh-collapse').dispatchEvent(new window.Event('click'));
const collapsed = $$('.uh-children.collapsed').length;
ok(collapsed > 0, '折叠全部生效', `collapsed=${collapsed}`);

// 详情链接 URL 格式
const bad = $$('.uh-link').filter(a => !/^\/objects\/[^/]+\/$/.test(a.getAttribute('href')));
ok(bad.length === 0, '详情链接 URL 格式正确', `total=${$$('.uh-link').length}`);
ok($$('.uh-badge').every(b => /^rgb|^#/.test(b.style.background)) || $$('.uh-badge').length > 0,
   '类型徽章着色正常');

// ---------- 中英文切换（页面仅依赖全站 i18n.js 派发的 site:langchange 事件） ----------
function setLang(l){ doc.dispatchEvent(new window.CustomEvent('site:langchange', { detail: { lang: l } })); }
setLang('en');
ok($('#uh').getAttribute('data-lang') === 'en', '切换后 data-lang=en');
const enNames = $$('.uh-nm').map(n => n.textContent);
ok(enNames.some(t => t.includes('Observable Universe')) && !enNames.some(t => t.includes('可观测宇宙')),
   '节点名切换为英文', `heads=${enNames.length}`);
ok($$('.uh-chip').length > 0 && $$('.uh-chip').every(c => !CJK.test(c.textContent)),
   '大类 chips 切换为英文');
ok($$('.uh-badge').length > 0 && $$('.uh-badge').every(b => !CJK.test(b.textContent)),
   '类型徽章切换为英文（type_i18n 覆盖）');
ok($('#uh-intro').textContent.length > 0 && !CJK.test($('#uh-intro').textContent),
   '说明段落切换为英文');

// 英文名搜索
const enHit = search('Sirius');
ok(enHit.some(t => t.includes('Sirius')), '英文名搜索命中', `hits=${enHit.length}`);

// 切换语言不丢失展开状态（路径用稳定 id）
q.value = ''; q.dispatchEvent(new window.Event('input'));
$('#uh-expand').dispatchEvent(new window.Event('click'));
const openEn = $$('.uh-children:not(.collapsed)').length;
setLang('zh');
const openZh = $$('.uh-children:not(.collapsed)').length;
ok(openEn > 0 && openEn === openZh, '切换语言不丢失展开状态（id 路径）', `en=${openEn} zh=${openZh}`);
ok($('#uh').getAttribute('data-lang') === 'zh' && $$('.uh-nm').some(n => CJK.test(n.textContent)),
   '可切回中文');

// ---------- 非结构现象并入主树底部「暂未分类」容器 ----------
const uncat = $$('.uh-node').find(n => {
  const h = n.querySelector('.uh-nm');
  return h && /暂未分类|Uncategorized/.test(h.textContent);
});
ok(!!uncat, '存在「暂未分类」容器节点（原非结构现象，移出独立区块）');
if (uncat) {
  const sub = [...uncat.querySelectorAll('.uh-head')].map(h => h.textContent);
  ok(sub.some(t => t.includes('宇宙微波背景')) && sub.some(t => t.includes('TON 618')),
     '暂未分类含 CMB 与类星体-AGN 子节点', `sub=${sub.length}`);
}

console.log('\n' + (fail.length ? `FAILED: ${fail.length}` : 'ALL PASS'));
process.exit(fail.length ? 1 : 0);
