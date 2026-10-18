/**
 * astro-explore.js — 天体总览页交互（原生 JS，无依赖）
 * 只对服务端预渲染的卡片 DOM 做筛选/排序/搜索，不请求任何数据接口。
 */
(function () {
  var grid = document.querySelector('.astro-grid');
  if (!grid) return;

  var cards = Array.prototype.slice.call(grid.querySelectorAll('.astro-card'));
  var chips = Array.prototype.slice.call(document.querySelectorAll('.astro-chips .chip'));
  var sortSel = document.getElementById('astro-sort');
  var search = document.getElementById('astro-search');
  var countEl = document.getElementById('astro-count');
  var emptyEl = document.getElementById('astro-empty');
  var state = { cat: 'all', sort: 'name', q: '' };

  function num(el, key) {
    var v = el.getAttribute('data-' + key);
    if (v === null || v === '') return null;
    var n = parseFloat(v);
    return isNaN(n) ? null : n;
  }

  function apply() {
    var q = state.q.trim().toLowerCase();
    var shown = cards.filter(function (c) {
      if (state.cat !== 'all' && c.getAttribute('data-category') !== state.cat) return false;
      if (q) {
        var name = (c.getAttribute('data-name') || '').toLowerCase();
        if (name.indexOf(q) === -1) return false;
      }
      return true;
    });

    if (state.sort === 'name') {
      shown.sort(function (a, b) {
        return (a.getAttribute('data-name') || '').localeCompare(b.getAttribute('data-name') || '', 'zh');
      });
    } else {
      shown.sort(function (a, b) {
        var va = num(a, state.sort);
        var vb = num(b, state.sort);
        if (va === null && vb === null) return 0;
        if (va === null) return 1;   // 无数据的排最后
        if (vb === null) return -1;
        return vb - va;              // 降序：大的在前
      });
    }

    var inShown = {};
    shown.forEach(function (c) { inShown[c.getAttribute('data-name')] = true; });
    shown.forEach(function (c) { grid.appendChild(c); c.hidden = false; });
    cards.forEach(function (c) {
      if (!inShown[c.getAttribute('data-name')]) c.hidden = true;
    });

    if (countEl) countEl.textContent = '显示 ' + shown.length + ' / ' + cards.length + ' 个天体';
    if (emptyEl) emptyEl.hidden = shown.length > 0;
  }

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      chips.forEach(function (c) { c.classList.remove('active'); });
      chip.classList.add('active');
      state.cat = chip.getAttribute('data-filter');
      apply();
    });
  });
  if (sortSel) sortSel.addEventListener('change', function () { state.sort = sortSel.value; apply(); });
  if (search) search.addEventListener('input', function () { state.q = search.value; apply(); });

  apply();
})();
