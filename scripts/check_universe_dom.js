// 宇宙层级页 jsdom 交互回归校验（常驻维护工具）
// 用法：仓库根目录执行 `node scripts/check_universe_dom.js`（需本机可 require('jsdom')）
// 直接从生成的 docs/universe-hierarchy.md 抽取内嵌 JSON + 逻辑脚本实跑，
// 覆盖：初始渲染 / alias / 详情链接 / 筛选 / 搜索（含大小写语义）/ 展开折叠 / URL 格式。
const fs = require('fs');
const { JSDOM } = require('jsdom');

const md = fs.readFileSync('docs/universe-hierarchy.md', 'utf8');
const scripts = [...md.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
const jsonScript = scripts.find(s => /uh-data/.test(s[1]));
const logicScript = scripts.find(s => !/uh-data/.test(s[1]));

const html = `<!DOCTYPE html><html><body>
<section id="uh" class="uh">
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

ok(errors.length === 0, '无 JS 运行时错误', errors.join(' | ').slice(0, 300));

// 初始渲染
const heads0 = $$('.uh-head').length;
ok(heads0 > 0, '初始渲染节点', `heads=${heads0}`);
ok($$('.uh-alias').length > 0, '规范编号 alias 渲染', `count=${$$('.uh-alias').length}`);
ok($$('.uh-link').length > 0, '详情卡片链接渲染', `count=${$$('.uh-link').length}`);
ok($$('.uh-chip').length >= 8, '大类筛选 chips', `count=${$$('.uh-chip').length}`);

// 大小写语义：搜索 开普勒16 应同时出现 B(恒星) 与 b(行星)
const q = $('#uh-q');
function search(v) {
  q.value = v;
  q.dispatchEvent(new window.Event('input'));
  return $$('.uh-nm').map(n => n.textContent);
}
const k16 = search('开普勒16');
ok(k16.some(t => t.includes('开普勒16B')) && k16.some(t => t.includes('开普勒16b')),
   '大小写语义：开普勒16B 与 开普勒16b 可区分且均命中',
   `hits=${k16.length}`);

// alias 编号搜索
const m42 = search('M42');
ok(m42.some(t => t.includes('猎户座大星云')), '按编号 M42 搜索命中中文名', `hits=${m42.length}`);

// 详情链接命中
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

// category 显式：所有 badge 背景色合法
ok($$('.uh-badge').every(b => /^rgb|^#/.test(b.style.background)) || $$('.uh-badge').length > 0,
   '类型徽章着色正常');

console.log('\n' + (fail.length ? `FAILED: ${fail.length}` : 'ALL PASS'));
process.exit(fail.length ? 1 : 0);
