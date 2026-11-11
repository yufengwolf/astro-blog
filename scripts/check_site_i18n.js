// 全站中英双语 jsdom 回归校验（常驻维护工具）
// 用法：仓库根目录执行 `node scripts/check_site_i18n.js`（需先 mkdocs build）
// 直接加载 site/ 构建产物并手动 eval i18n 运行时，覆盖：
//   顶栏按钮位置 / 语言持久化 / 中文↔英文可逆 / 导航 / 卡片名主次互换 /
//   分类徽章 / 英文简介 / 筛选 chips / 计数文案 / 详情页表头 / 对比页表格。
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const I18N_DATA = fs.readFileSync('site/js/i18n-data.js', 'utf8');
const I18N = fs.readFileSync('site/js/i18n.js', 'utf8');
const EXPLORE = fs.readFileSync('site/js/astro-explore.js', 'utf8');
const COMPARE = fs.readFileSync('site/js/compare.js', 'utf8');

const fail = [];
const ok = (cond, label, extra = '') => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${label}${extra ? '  ' + extra : ''}`);
  if (!cond) fail.push(label);
};
const CJK = /[\u4e00-\u9fff]/;

function boot(htmlFile, extraScripts = []) {
  const html = fs.readFileSync(htmlFile, 'utf8');
  const dom = new JSDOM(html, { runScripts: 'outside-only', url: 'https://example.test/' });
  const { window } = dom;
  const errors = [];
  window.addEventListener('error', e => errors.push(String(e.error || e.message)));
  try {
    window.eval(I18N_DATA);
    window.eval(I18N);
    window.eval(EXPLORE);
    extraScripts.forEach(s => window.eval(s));
    window.document.dispatchEvent(new window.Event('DOMContentLoaded'));
  } catch (e) {
    errors.push('EVAL: ' + e.stack);
  }
  return { window, doc: window.document, errors, $: s => window.document.querySelector(s), $$: s => [...window.document.querySelectorAll(s)] };
}

// ---------------------------------------------------------------- 首页
console.log('--- 首页 index.html ---');
const A = boot('site/index.html');
ok(A.errors.length === 0, '首页无 JS 运行时错误', A.errors.join(' | ').slice(0, 240));
ok(A.window.SITE_LANG === 'zh', '默认语言为中文');
ok(A.doc.documentElement.getAttribute('data-lang') === 'zh', 'html[data-lang=zh]');

const palette = A.$('form[data-md-component="palette"]');
const langBtn = A.$('#site-lang-btn');
ok(!!palette && !!langBtn, '顶栏语言按钮已注入');
ok(!!langBtn && !!palette && langBtn.parentNode.nextElementSibling === palette,
   '语言按钮紧邻明暗模式切换（在其前一位）');
ok(A.$('.astro-hero h1').textContent.trim() === '天体数据库', '中文首页标题');
// 用固定 id 的卡片，避免 astro-explore.js 排序后「第一张卡片」漂移
const sunCard = A.$('a.astro-card-link[href="objects/sun/"]');
const firstTitle = sunCard.querySelector('.astro-card-title');
const firstTag = sunCard.querySelector('.astro-card-tagline');
const firstBadge = sunCard.querySelector('.astro-badge');
ok(firstTitle.firstChild.nodeValue.trim() === '太阳', '中文卡片主名为中文名');
ok(firstTitle.querySelector('.en').textContent === 'Sun', '中文卡片副名为英文名');
ok(firstBadge.textContent === '恒星', '中文分类徽章');
ok(CJK.test(firstTag.textContent), '中文简介为中文');
ok(A.$('.astro-chips .chip').textContent.trim() === '全部 179', '中文筛选 chips');

// 切到英文
langBtn.dispatchEvent(new A.window.Event('click'));
ok(A.window.SITE_LANG === 'en', '点击按钮切换为英文');
ok(A.doc.documentElement.getAttribute('data-lang') === 'en', 'html[data-lang=en]');
ok(A.doc.documentElement.getAttribute('lang') === 'en', 'html[lang=en]');
ok(A.window.localStorage.getItem('astro-site-lang') === 'en', '语言写入 localStorage');
ok(A.$('.astro-hero h1').textContent.trim() === 'Celestial Object Database', '首页标题转英文');
ok(A.$('.md-header__title .md-ellipsis').textContent.trim() === 'Starfield Notes', '顶栏站点名转英文');
ok(A.doc.body.textContent.includes('Object Explorer'), '侧栏导航转英文');
ok(firstTitle.firstChild.nodeValue.trim() === 'Sun', '英文模式卡片主名为英文名');
ok(firstTitle.querySelector('.en').textContent === '太阳', '英文模式副名为中文名');
ok(firstBadge.textContent === 'Star', '英文分类徽章');
ok(!CJK.test(firstTag.textContent), '英文简介不含中文', firstTag.textContent.slice(0, 60));
ok(A.$('.astro-chips .chip').textContent.trim() === 'All 179', '英文筛选 chips');
ok(A.$('#astro-search').getAttribute('placeholder') === 'Search objects…', '搜索框占位符转英文');
ok(/Showing \d+ of \d+ objects/.test(A.$('#astro-count').textContent), '计数文案转英文',
   A.$('#astro-count').textContent);
ok(A.$('.astro-hero-links a').textContent.trim() === 'Featured Articles', '文章链接转英文');

// 切回中文：可逆性
langBtn.dispatchEvent(new A.window.Event('click'));
ok(A.window.SITE_LANG === 'zh', '再次点击切回中文');
ok(A.$('.astro-hero h1').textContent.trim() === '天体数据库', '标题恢复中文');
ok(firstTitle.firstChild.nodeValue.trim() === '太阳', '卡片主名恢复中文');
ok(firstTitle.querySelector('.en').textContent === 'Sun', '卡片副名恢复英文');
ok(firstBadge.textContent === '恒星', '徽章恢复中文');
ok(CJK.test(firstTag.textContent), '简介恢复中文');
ok(A.$('.astro-chips .chip').textContent.trim() === '全部 179', 'chips 恢复中文');
ok(/显示 \d+ \/ \d+ 个天体/.test(A.$('#astro-count').textContent), '计数恢复中文');

// 重新加载时读取持久化偏好
const B = boot('site/index.html');
B.window.localStorage.setItem('astro-site-lang', 'en');
B.window.setSiteLang('en');
ok(B.$('.astro-hero h1').textContent.trim() === 'Celestial Object Database', 'setSiteLang 可程序化切换');

// ---------------------------------------------------------------- 详情页
console.log('--- 详情页 objects/sun ---');
const detail = 'site/objects/sun/index.html';
if (fs.existsSync(detail)) {
  const C = boot(detail);
  ok(C.errors.length === 0, '详情页无 JS 运行时错误', C.errors.join(' | ').slice(0, 240));
  ok(C.$('.obj-hero h1') && C.$('.obj-hero h1').firstChild.textContent.trim() === '太阳', '详情页中文主名');
  C.window.setSiteLang('en');
  ok(C.$('.obj-hero h1').firstChild.textContent.trim() === 'Sun', '详情页英文主名');
  ok(C.$('.obj-hero h1 small').textContent.trim() === '太阳', '详情页小字换为中文名');
  const heads = [...C.$$('.obj-data-block h2')].map(h => h.textContent.trim());
  ok(heads.includes('Physical Properties'), '详情页段落标题转英文', heads.join(' / '));
  const ths = [...C.$$('.obj-data-block th')].map(h => h.textContent.trim());
  ok(ths.includes('Mass') && ths.includes('Parameter'), '详情页表头转英文', ths.slice(0, 6).join(' / '));
  ok(!CJK.test(C.$('.obj-tagline').textContent), '详情页简介转英文');
  // 影像署名由 data-en-html 整块替换：必须保留 <a> 来源链接，且中英可逆
  const credit = C.$('.astro-img-credit');
  ok(!!credit && !!credit.querySelector('a'), '英文模式影像署名保留来源链接');
  ok(!!credit && !CJK.test(credit.textContent), '英文模式影像署名不含中文',
     credit && credit.textContent.slice(0, 80));
  C.window.setSiteLang('zh');
  ok(C.$('.obj-hero h1').firstChild.textContent.trim() === '太阳', '详情页可逆恢复');
  ok(!!credit && !!credit.querySelector('a') && CJK.test(credit.textContent),
     '切回中文影像署名与来源链接恢复');
} else {
  ok(false, '详情页构建产物存在');
}

// ---------------------------------------------------------------- 对比页
console.log('--- 对比页 compare ---');
const cmp = 'site/compare/index.html';
if (fs.existsSync(cmp)) {
  const D = boot(cmp, [COMPARE]);
  ok(D.errors.length === 0, '对比页无 JS 运行时错误', D.errors.join(' | ').slice(0, 240));
  ok(D.$('#sizecmp-a option') && CJK.test(D.$('#sizecmp-a option').textContent), '对比页下拉为中文名');
  D.window.setSiteLang('en');
  ok(D.$('h1') && /Size Comparison/.test(D.$('h1').textContent), '对比页标题转英文');
  const opt = D.$('#sizecmp-a option');
  ok(opt && !CJK.test(opt.textContent), '对比页下拉转英文名', opt && opt.textContent);
  const catOpt = D.$('#sizecmp-cat-a option');
  ok(catOpt && catOpt.textContent === 'All types', '分类下拉转英文', catOpt && catOpt.textContent);
  const cmpTh = [...D.$$('.sizecmp-table th')].map(h => h.textContent.trim());
  ok(cmpTh.includes('Parameter'), '对比表表头转英文', cmpTh.slice(0, 5).join(' / '));
  ok(/Drawn at true diameter ratio|logarithmic/.test(D.$('#sizecmp-viz-note').textContent),
     '对比说明转英文', D.$('#sizecmp-viz-note').textContent.slice(0, 70));
  D.window.setSiteLang('zh');
  ok(CJK.test(D.$('#sizecmp-a option').textContent), '对比页可逆恢复');
} else {
  ok(false, '对比页构建产物存在');
}

console.log(fail.length ? `\nFAILED: ${fail.length}\n - ${fail.join('\n - ')}` : '\nALL PASS');
process.exit(fail.length ? 1 : 0);
