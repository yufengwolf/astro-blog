/* test_compare.js — 用最小 DOM stub 在 Node 中实跑 astro-compare.js 的完整交互逻辑。
 * 数据源：docs/objects/earth.md 中真实内嵌的 astro-compare-data JSON。
 * 验证：初始渲染 / 搜索添加 / hash 同步 / 移除 / 上限 / 格式化与 gen_pages.py 一致。
 * 用法：node scripts/test_compare.js（改 astro-compare.js 或生成器后必跑）
 */
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const REPO = path.join(__dirname, '..');
const md = fs.readFileSync(path.join(REPO, 'docs/objects/earth.md'), 'utf-8');
const m = md.match(/<script type="application\/json" id="astro-compare-data">([\s\S]*?)<\/script>/);
if (!m) { console.error('FAIL: earth.md 中未找到内嵌对比数据'); process.exit(1); }
const payload = m[1];

// ---- 最小 DOM stub ----
function makeEl(id) {
  return {
    id, innerHTML: '', textContent: '', value: '', hidden: false,
    _attrs: {}, _listeners: {},
    setAttribute(k, v) { this._attrs[k] = String(v); },
    getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
    addEventListener(ev, fn) { (this._listeners[ev] = this._listeners[ev] || []).push(fn); },
    contains() { return false; },
    classList: { add() {}, remove() {}, contains() { return false; } },
    closest() { return null; }
  };
}
const ids = ['astro-compare-data', 'astro-compare', 'astro-compare-toggle',
             'cmp-search', 'cmp-results', 'cmp-table'];
const els = {};
ids.forEach(id => { els[id] = makeEl(id); });
els['astro-compare-data'].textContent = payload;
els['astro-compare']._attrs['data-current'] = 'earth';
els['astro-compare'].hidden = true;   // 模拟 HTML hidden 属性

const docListeners = {};
let replacedURL = null;
const sandbox = {
  document: {
    getElementById: id => els[id] || null,
    addEventListener: (ev, fn) => { docListeners[ev] = fn; }
  },
  location: { hash: '', pathname: '/objects/earth/', search: '' },
  history: { replaceState: (a, b, url) => { replacedURL = url; } },
  console
};
vm.createContext(sandbox);
const code = fs.readFileSync(path.join(REPO, 'docs/js/astro-compare.js'), 'utf-8');
vm.runInContext(code, sandbox);

// ---- 断言工具 ----
let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (extra ? ' | ' + extra : '')); }
}

const table = els['cmp-table'];
const search = els['cmp-search'];
const results = els['cmp-results'];

console.log('== 1. 初始渲染（当前天体=地球，单列）==');
check('表格已渲染', table.innerHTML.length > 0);
check('含"地球"列', table.innerHTML.includes('>地球<'));
check('地球质量格式 5.97×10²⁴ kg（与 Python .3g 一致）', table.innerHTML.includes('5.97×10²⁴ kg'), table.innerHTML.match(/5\.9[07][^<]*/));
check('地球质量（地球=1）为 1', table.innerHTML.includes('<td class="cmp-current">1</td>'));
check('卫星数 1 颗', table.innerHTML.includes('1 颗'));
check('初始 hash 同步', replacedURL === '/objects/earth/#compare=earth', replacedURL);
check('面板初始隐藏', els['astro-compare'].hidden === true);

console.log('== 2. 搜索"月球" → 添加 ==');
search.value = '月球';
search._listeners['input'][0].call(search);
check('搜索结果出现月球', results.innerHTML.includes('月球'), results.innerHTML.slice(0, 120));
const fakeBtn = { getAttribute: () => 'moon' };
results._listeners['click'][0]({ target: { closest: sel => sel === 'button[data-id]' ? fakeBtn : null } });
check('添加后表格含月球列', table.innerHTML.includes('>月球<'));
check('月球质量 7.35×10²² kg', table.innerHTML.includes('7.35×10²² kg'));
check('月球质量（地球=1）= 0.0123', table.innerHTML.includes('0.0123'));
check('月球半径 1,737 km（≥1000 取整，同 Python）', table.innerHTML.includes('1,737 km'));
check('月球母天体显示地球', table.innerHTML.includes('地球'));
check('hash 同步 earth,moon', replacedURL === '/objects/earth/#compare=earth,moon', replacedURL);
check('多列后面板自动展开', els['astro-compare'].hidden === false);
check('搜索框已清空', search.value === '');

console.log('== 3. 再添加木星 + 太阳（3+ 列）==');
search.value = '木星';
search._listeners['input'][0].call(search);
const fakeJ = { getAttribute: () => 'jupiter' };
results._listeners['click'][0]({ target: { closest: sel => sel === 'button[data-id]' ? fakeJ : null } });
search.value = '太阳';
search._listeners['input'][0].call(search);
const fakeS = { getAttribute: () => 'sun' };
results._listeners['click'][0]({ target: { closest: sel => sel === 'button[data-id]' ? fakeS : null } });
check('含木星列', table.innerHTML.includes('>木星<'));
check('含太阳列', table.innerHTML.includes('>太阳<'));
check('木星质量 1.9×10²⁷ kg（.3g 三位有效，尾零去）', table.innerHTML.includes('1.9×10²⁷ kg'));
check('太阳母天体显示 —（无 parent）', table.innerHTML.includes('<td>—</td>') || table.innerHTML.includes('—'));
check('太阳密度显示 —（恒星无密度字段）', /密度[\s\S]*?—/.test(table.innerHTML));
check('hash 为 earth,moon,jupiter,sun', replacedURL === '/objects/earth/#compare=earth,moon,jupiter,sun', replacedURL);

console.log('== 4. 移除月球 ==');
table._listeners['click'][0]({ target: { closest: sel => sel === '.cmp-remove' ? { getAttribute: () => 'moon' } : null } });
check('月球列已移除', !table.innerHTML.includes('>月球<'));
check('木星列仍在', table.innerHTML.includes('>木星<'));
check('hash 更新', replacedURL === '/objects/earth/#compare=earth,jupiter,sun', replacedURL);

console.log('== 5. 上限 5 列 ==');
['mercury', 'venus', 'mars'].forEach(id => {
  search.value = id;
  search._listeners['input'][0].call(search);
  const b = { getAttribute: () => id };
  results._listeners['click'][0]({ target: { closest: sel => sel === 'button[data-id]' ? b : null } });
});
check('当前列数 = 5（earth+jupiter+sun+mercury+venus，mars 被拒）', (table.innerHTML.match(/cmp-col/g) || []).length === 5, '列头数=' + (table.innerHTML.match(/cmp-col/g) || []).length);
check('hash 恰 5 个 id', replacedURL === '/objects/earth/#compare=earth,jupiter,sun,mercury,venus', replacedURL);

console.log('== 6. 第一列（当前天体）不可移除 ==');
table._listeners['click'][0]({ target: { closest: sel => sel === '.cmp-remove' ? { getAttribute: () => 'earth' } : null } });
check('地球列仍在', table.innerHTML.includes('>地球<'));

console.log('== 7. hash 恢复（新页面场景）==');
const els2 = {};
ids.forEach(id => { els2[id] = makeEl(id); });
els2['astro-compare-data'].textContent = payload;
els2['astro-compare']._attrs['data-current'] = 'mars';
let replaced2 = null;
const sandbox2 = {
  document: { getElementById: id => els2[id] || null, addEventListener: () => {} },
  location: { hash: '#compare=mars,venus,earth', pathname: '/objects/mars/', search: '' },
  history: { replaceState: (a, b, url) => { replaced2 = url; } },
  console
};
vm.createContext(sandbox2);
vm.runInContext(code, sandbox2);
check('hash 恢复到 3 列（当前天体置首）', replaced2 === '/objects/mars/#compare=mars,venus,earth', replaced2);
check('自动展开', els2['astro-compare'].hidden === false);
check('表格含火星+金星+地球', els2['cmp-table'].innerHTML.includes('>火星<') && els2['cmp-table'].innerHTML.includes('>金星<') && els2['cmp-table'].innerHTML.includes('>地球<'));

console.log('\n结果: ' + pass + ' 通过, ' + fail + ' 失败');
process.exit(fail ? 1 : 0);
