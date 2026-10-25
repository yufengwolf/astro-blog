/**
 * astro-explore.js — 天体总览页交互（原生 JS，无依赖）
 * 只对服务端预渲染的卡片 DOM 做筛选/排序/搜索，不请求任何数据接口。
 * 另含两段全局增强（每页注入，先于页面逻辑执行）：
 *   1) Markdown 表格包进横向滚动容器（移动端多列表格必需，附首列固定）
 *   2) 按 .md-header 实际高度写 --astro-sticky-top（工具栏 sticky 不被吸顶 header 遮住）
 */
(function () {
  "use strict";

  // ---- 全局增强 1：表格横向滚动包裹 ----
  // MkDocs 渲染的 Markdown 表格是裸 <table>（自身无法 overflow），移动端
  // 10 列总表会被挤压变形。包一层 .table-scroll（overflow-x:auto + 首列 sticky），
  // 桌面端不设 min-width 不触发滚动，无副作用。可横滚时加 .is-scrollable 显示右缘渐隐提示。
  document.querySelectorAll(".md-typeset table").forEach(function (t) {
    if (t.parentElement && t.parentElement.classList.contains("table-scroll")) return;
    var wrap = document.createElement("div");
    wrap.className = "table-scroll";
    t.parentNode.insertBefore(wrap, t);
    wrap.appendChild(t);
    var check = function () {
      wrap.classList.toggle("is-scrollable", wrap.scrollWidth > wrap.clientWidth + 1);
    };
    check();
    wrap.addEventListener("scroll", check, { passive: true });
    window.addEventListener("resize", check);
  });

  // ---- 全局增强 2：sticky 工具栏的 top 偏移（避开吸顶 header）----
  var header = document.querySelector(".md-header");
  function setStickyTop() {
    var h = header ? header.offsetHeight : 0;
    document.documentElement.style.setProperty("--astro-sticky-top", h + "px");
  }
  setStickyTop();
  window.addEventListener("resize", setStickyTop);

  // ---- 天体总览页：筛选 / 排序 / 搜索 ----
  var grid = document.querySelector(".astro-grid");
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
