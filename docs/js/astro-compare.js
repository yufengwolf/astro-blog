/**
 * astro-compare.js — 天体详情页「多天体对比」（原生 JS，无依赖）
 * 数据来自页面内嵌的 #astro-compare-data（全量天体精简数值），本地渲染，无网络请求。
 * 状态同步到 location.hash（#compare=earth,moon），刷新/分享保持对比组合。
 */
(function () {
  var dataEl = document.getElementById('astro-compare-data');
  var panel = document.getElementById('astro-compare');
  if (!dataEl || !panel) return;

  var data;
  try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
  var rows = data.rows || [];
  var byId = {};
  rows.forEach(function (r) { byId[r.id] = r; });
  var EARTH = data.earth_id;

  var current = panel.getAttribute('data-current') || (rows[0] && rows[0].id);
  var MAX_COLS = 5;
  var selected = [current];

  var toggleBtn = document.getElementById('astro-compare-toggle');
  var search = document.getElementById('cmp-search');
  var results = document.getElementById('cmp-results');
  var table = document.getElementById('cmp-table');

  var SUP = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '-': '⁻' };
  function sup(s) { return String(s).replace(/[0-9-]/g, function (c) { return SUP[c]; }); }
  function sig3(x) {
    if (x === 0) return '0';
    var e = Math.floor(Math.log10(Math.abs(x)));
    var m = x / Math.pow(10, e);
    var s = m.toPrecision(3);
    if (s.indexOf('.') !== -1) s = s.replace(/0+$/, '').replace(/\.$/, '');
    return s + '×10' + sup(e);
  }
  function fmtMass(kg) {
    if (kg === null || kg === undefined) return '—';
    return sig3(kg) + ' kg';
  }
  function fmtRadius(r) {
    if (r === null || r === undefined) return '—';
    return (r < 1000 ? r.toFixed(1) : r.toFixed(0)).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + ' km';
  }
  function fmtTemp(t) { return (t === null || t === undefined) ? '—' : t + ' °C'; }
  function fmtPeriod(d) {
    if (d === null || d === undefined) return '—';
    if (d < 2) return d.toFixed(2) + ' 天';
    if (d < 1000) return d.toFixed(1) + ' 天';
    return (d / 365.25).toFixed(1) + ' 年（' + Math.round(d).toLocaleString('en-US') + ' 天）';
  }
  function fmtRotation(h) {
    if (h === null || h === undefined) return '—';
    var retro = h < 0, s;
    h = Math.abs(h);
    s = h >= 48 ? (h / 24).toFixed(2) + ' 天' : h.toFixed(2) + ' 小时';
    return (retro ? '逆行自转 · ' : '') + s;
  }
  function fmtPressure(p) {
    if (p === null || p === undefined) return '—';
    if (p === 0) return '≈ 0（可忽略）';
    if (p < 0.001) { var e = Math.floor(Math.log10(p)); return sig3(p / Math.pow(10, e)) + '×10' + sup(e) + ' bar'; }
    return String(p) + ' bar';
  }
  function fmtVelocity(v) {
    if (v === null || v === undefined) return '—';
    return (v < 1 ? v.toFixed(3) : v.toFixed(2)) + ' km/s';
  }
  function fmtGravity(g) { return (g === null || g === undefined) ? '—' : g.toFixed(2) + ' m/s²'; }
  function fmtKm(a) {
    if (a === null || a === undefined) return '—';
    return Math.round(a).toLocaleString('en-US') + ' km';
  }
  function fmtRatio(x, base) {
    if (x === null || x === undefined || !base) return '—';
    var s = (x / base).toPrecision(3);
    if (s.indexOf('.') !== -1) s = s.replace(/0+$/, '').replace(/\.$/, '');
    return s;
  }
  function fmtLum(l) {
    if (l === null || l === undefined) return '—';
    return sig3(l / 3.828e26) + ' L☉';
  }
  function fmtDist(ly) {
    if (ly === null || ly === undefined) return '—';
    if (ly < 10) return ly.toFixed(2) + ' 光年';
    if (ly < 1000) return ly.toFixed(1) + ' 光年';
    return Math.round(ly).toLocaleString('en-US') + ' 光年';
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // 参数行定义：key → [显示名, 取值函数]
  var earthRow = byId[EARTH] || {};
  var PARAM_ROWS = [
    ['分类', function (r) { return esc(r.cat); }],
    ['母天体', function (r) { return r.parent && byId[r.parent] ? esc(byId[r.parent].name) : '—'; }],
    ['质量', function (r) { return fmtMass(r.mass); }],
    ['质量（地球 = 1）', function (r) { return fmtRatio(r.mass, earthRow.mass); }],
    ['平均半径', function (r) { return fmtRadius(r.radius); }],
    ['半径（地球 = 1）', function (r) { return fmtRatio(r.radius, earthRow.radius); }],
    ['平均密度', function (r) { return (r.density === null || r.density === undefined) ? '—' : r.density + ' g/cm³'; }],
    ['表面重力', function (r) { return fmtGravity(r.gravity); }],
    ['逃逸速度', function (r) { return fmtVelocity(r.escape); }],
    ['平均表面温度', function (r) { return fmtTemp(r.temp); }],
    ['表面气压', function (r) { return fmtPressure(r.pressure); }],
    ['自转周期', function (r) { return fmtRotation(r.rotation); }],
    ['轨道半长轴', function (r) { return fmtKm(r.axis); }],
    ['轨道周期', function (r) { return fmtPeriod(r.period); }],
    ['平均轨道速度', function (r) { return fmtVelocity(r.velocity); }],
    ['已确认卫星数', function (r) { return (r.moons === null || r.moons === undefined) ? '—' : r.moons + ' 颗'; }],
    ['光度（L☉）', function (r) { return fmtLum(r.lum); }],
    ['距离', function (r) { return fmtDist(r.distance); }],
    ['星座', function (r) { return (r.constellation === null || r.constellation === undefined) ? '—' : esc(r.constellation); }],
    ['光谱型', function (r) { return (r.spectral === null || r.spectral === undefined) ? '—' : esc(r.spectral); }]
  ];

  function syncHash() {
    if (history.replaceState) {
      history.replaceState(null, '', location.pathname + location.search + '#compare=' + selected.join(','));
    } else {
      location.hash = 'compare=' + selected.join(',');
    }
  }

  function renderTable() {
    var html = ['<thead><tr><th class="cmp-param">参数</th>'];
    selected.forEach(function (id, i) {
      var r = byId[id];
      if (!r) return;
      var close = (i === 0) ? '' : '<button type="button" class="cmp-remove" data-id="' + id + '" title="移除对比" aria-label="移除 ' + esc(r.name) + '">×</button>';
      html.push('<th class="cmp-col' + (i === 0 ? ' cmp-current' : '') + '" data-id="' + id + '">'
        + '<a href="../' + id + '/">' + esc(r.name) + '</a><span class="cmp-en">' + esc(r.en) + '</span>' + close + '</th>');
    });
    html.push('</tr></thead><tbody>');
    PARAM_ROWS.forEach(function (row) {
      html.push('<tr><th class="cmp-param">' + esc(row[0]) + '</th>');
      selected.forEach(function (id, i) {
        var r = byId[id];
        if (!r) return;
        html.push('<td class="' + (i === 0 ? 'cmp-current' : '') + '">' + row[1](r) + '</td>');
      });
      html.push('</tr>');
    });
    html.push('</tbody>');
    table.innerHTML = html.join('');
  }

  function renderResults(q) {
    q = q.trim().toLowerCase();
    if (!q) { results.hidden = true; results.innerHTML = ''; return; }
    var hits = rows.filter(function (r) {
      if (selected.indexOf(r.id) !== -1) return false;
      return r.name.toLowerCase().indexOf(q) !== -1 || r.en.toLowerCase().indexOf(q) !== -1;
    }).slice(0, 10);
    if (!hits.length) {
      results.innerHTML = '<li class="cmp-none">没有匹配的天体</li>';
    } else {
      results.innerHTML = hits.map(function (r) {
        return '<li><button type="button" data-id="' + r.id + '">'
          + '<b>' + esc(r.name) + '</b><span class="cmp-en">' + esc(r.en) + ' · ' + esc(r.cat) + '</span></button></li>';
      }).join('');
    }
    results.hidden = false;
  }

  function add(id) {
    if (selected.indexOf(id) !== -1 || selected.length >= MAX_COLS) return;
    selected.push(id);
    search.value = '';
    results.hidden = true;
    renderTable();
    syncHash();
    setPanel(true);   // 添加即确保面板展开
  }

  function remove(id) {
    var i = selected.indexOf(id);
    if (i <= 0) return;               // 第一列（当前天体）不可移除
    selected.splice(i, 1);
    renderTable();
    syncHash();
  }

  function setPanel(open) {
    panel.hidden = !open;
    toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  // ---- 事件 ----
  toggleBtn.addEventListener('click', function () { setPanel(panel.hidden); });
  search.addEventListener('input', function () { renderResults(search.value); });
  search.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { search.value = ''; results.hidden = true; }
  });
  results.addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-id]');
    if (btn) add(btn.getAttribute('data-id'));
  });
  table.addEventListener('click', function (e) {
    var btn = e.target.closest('.cmp-remove');
    if (btn) remove(btn.getAttribute('data-id'));
  });
  document.addEventListener('click', function (e) {
    if (!results.hidden && !results.contains(e.target) && e.target !== search) results.hidden = true;
  });

  // ---- 初始化：读 hash 恢复对比组合 ----
  var m = location.hash.match(/compare=([\w,]+)/);
  if (m) {
    m[1].split(',').forEach(function (id) {
      if (byId[id] && selected.indexOf(id) === -1 && selected.length < MAX_COLS) selected.push(id);
    });
  }
  renderTable();
  syncHash();
  if (selected.length > 1) setPanel(true);   // 带对比参数进入时自动展开
})();
