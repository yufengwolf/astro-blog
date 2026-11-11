// 全站双语覆盖率回归（常驻维护工具）
// 用法：先 `mkdocs build --strict`，再执行 `node scripts/check_i18n_coverage.js`
//
// 按真实浏览器顺序加载 js/i18n-data.js -> js/i18n.js -> 业务脚本，切到英文，
// 逐页统计「可见文本节点」里的中文字符残留，并列出具体残留元素。
// 排除项均为设计上刻意保留或不可见的内容，不算漏译：
//   script/style/noscript/button  —— 逻辑数据与功能性按钮文案（如「中文」切回按钮）
//   [data-cn-only]                —— 英文模式下由 CSS 隐藏的中文别名
//   .astro-card-title .en         —— 英文模式副名（中文名刻意并排保留）
//   .obj-hero small               —— 详情页副名
// 覆盖率低于 THRESHOLDS 的页面直接 FAIL，避免新增静态文案漏译悄悄上线。
const fs = require('fs');
const { JSDOM } = require('jsdom');

const ROOT = 'site/';
const DATA = fs.readFileSync(ROOT + 'js/i18n-data.js', 'utf8');
const I18N = fs.readFileSync(ROOT + 'js/i18n.js', 'utf8');
const EXTRA = ['js/astro-explore.js', 'js/compare.js', 'js/solar-embed.js'];

const PAGES = [
  'index.html', 'objects/index.html', 'data/index.html', 'compare/index.html',
  'solar-demo/index.html', 'universe-hierarchy/index.html', 'objects/sun/index.html'
];
// 各页最低覆盖率（%）。新增页面必须登记；调低阈值需说明原因。
const THRESHOLDS = {
  'index.html': 99,
  'objects/index.html': 99,
  'data/index.html': 99,
  'compare/index.html': 99,
  'solar-demo/index.html': 99,
  'universe-hierarchy/index.html': 99,
  'objects/sun/index.html': 99
};
const EXCLUDE = 'script,style,noscript,button,[data-cn-only],' +
                '.astro-card-title .en,.obj-hero small';
const VERBOSE = process.env.I18N_COV_VERBOSE === '1';

const cn = s => (String(s).match(/[\u4e00-\u9fff]/g) || []).length;

// 返回 { total, items: [{where, text, n}] }，按文本节点计数，父子元素不重复累计。
function scan(doc) {
  const clone = doc.body.cloneNode(true);
  clone.querySelectorAll(EXCLUDE).forEach(x => x.remove());
  const walker = clone.ownerDocument.createTreeWalker(clone, 4 /* SHOW_TEXT */, null);
  let total = 0;
  const items = [];
  let n;
  while ((n = walker.nextNode())) {
    const k = cn(n.nodeValue);
    if (!k) continue;
    total += k;
    const p = n.parentElement;
    const where = p ? p.tagName.toLowerCase() + (p.className ? '.' + String(p.className).trim().split(/\s+/).join('.') : '') : '#text';
    items.push({ where, text: n.nodeValue.trim().slice(0, 90), n: k });
  }
  return { total, items };
}

const fail = [];
for (const p of PAGES) {
  const f = ROOT + p;
  if (!fs.existsSync(f)) { console.log('MISS ' + f); fail.push(p + ' (产物缺失)'); continue; }
  const html = fs.readFileSync(f, 'utf8');
  const dom = new JSDOM(html, {
    runScripts: 'outside-only',
    url: 'https://example.test/' + p.replace(/index\.html$/, '')
  });
  const w = dom.window, doc = w.document;
  const errs = [];
  // 页面内嵌逻辑脚本（排除 type=application/json 的数据块）
  const inline = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)]
    .filter(m => !/application\/json/.test(m[1]) && m[2].trim())
    .map(m => m[2]);
  for (const s of inline) { try { w.eval(s); } catch (e) { errs.push('inline:' + e.message); } }
  // 严格按 mkdocs.yml 声明顺序：数据 -> 运行时 -> 业务脚本
  try { w.eval(DATA); } catch (e) { errs.push('data:' + e.message); }
  try { w.eval(I18N); } catch (e) { errs.push('i18n:' + e.message); }
  for (const x of EXTRA) {
    const fp = ROOT + x;
    if (!fs.existsSync(fp)) continue;
    try { w.eval(fs.readFileSync(fp, 'utf8')); } catch (e) { errs.push(x + ':' + e.message); }
  }
  try {
    doc.dispatchEvent(new w.Event('DOMContentLoaded'));
    w.setSiteLang('en');
  } catch (e) { errs.push('apply:' + e.message); }

  // 中文态基线：在同一份 DOM 上切回中文再扫描
  w.setSiteLang('zh');
  const before = scan(doc);
  w.setSiteLang('en');
  const after = scan(doc);
  const rate = before.total ? 100 * (1 - after.total / before.total) : 100;
  const min = THRESHOLDS[p] != null ? THRESHOLDS[p] : 99;
  // 译表漂移：含中文的静态段落既没登记 BLOCKS，也没有数据层整串译稿
  const drift = w.SITE_I18N_UNMATCHED || [];
  const good = errs.length === 0 && rate >= min && drift.length === 0;
  console.log(`${good ? 'PASS' : 'FAIL'}  ${p.padEnd(34)} ${String(before.total).padStart(5)} -> ${String(after.total).padStart(4)}  ${rate.toFixed(1)}%  (min ${min}%)  漂移 ${drift.length}` +
              (errs.length ? '  [ERR ' + errs.join(' | ') + ']' : ''));
  if (drift.length) {
    fail.push(p + ' 译表漂移 ' + drift.length + ' 处');
    drift.slice(0, 8).forEach(s => console.log('      [漂移] ' + s));
  }
  if (rate < min) fail.push(p + ' 覆盖率 ' + rate.toFixed(1) + '%');
  if (errs.length) fail.push(p + ' JS 错误');
  if (!good || (VERBOSE && after.items.length)) {
    after.items.slice(0, 14).forEach(it => console.log(`      ${String(it.n).padStart(4)}字  ${it.where}  ${it.text}`));
    if (after.items.length > 14) console.log(`      ... 另有 ${after.items.length - 14} 个文本节点`);
  }
}
console.log(fail.length ? `\nFAILED: ${fail.length}\n - ${fail.join('\n - ')}` : '\nALL PASS');
process.exit(fail.length ? 1 : 0);
