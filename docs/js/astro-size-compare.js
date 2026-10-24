/**
 * astro-size-compare.js — 天体对比工具页（原生 JS，无依赖，无后台）
 *
 * 默认两个选择框（A / B，默认 月球 / 地球）。选择后：
 *   1) 按**真实直径比例**用 SVG 绘制两个球体（含真实贴图；小球放大到最小可见尺寸时
 *      在说明里标注真实倍数，以数字为准）——解决「AI 画图把 95% 画成更大」的视觉事实错误；
 *   2) 核心倍数卡：直径 / 体积 / 质量的直观倍数（体积 ∝ 半径³）；
 *   3) 详细数据表：半径、体积、质量、密度、表面重力、逃逸速度、温度、自转，逐行 A÷B 倍数。
 * 状态同步到 location.hash（#cmp=a,b），刷新/分享保持对比组合。
 *
 * 数据来自页面内嵌的 #astro-sizecompare-data（gen_pages 注入，含相对图片路径）。
 */
(function () {
  "use strict";
  var dataEl = document.getElementById("astro-sizecompare-data");
  if (!dataEl) return;
  var svg = document.getElementById("sizecmp-svg");
  var selA = document.getElementById("sizecmp-a");
  var selB = document.getElementById("sizecmp-b");
  var swapBtn = document.getElementById("sizecmp-swap");
  var ratiosEl = document.getElementById("sizecmp-ratios");
  var detailEl = document.getElementById("sizecmp-detail");
  var noteEl = document.getElementById("sizecmp-viz-note");
  var shareEl = document.getElementById("sizecmp-share");
  if (!svg || !selA || !selB) return;

  var data;
  try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
  var rows = data.rows || [];
  var byId = {};
  rows.forEach(function (r) { byId[r.id] = r; });

  // ---- 分类配色（用于无贴图天体纯色圆 + 倍数卡圆点）----
  var CAT_COLOR = {
    star: ["#f5a623", "#e06c00"],
    planet: ["#4a90d9", "#2b5f9e"],
    dwarf_planet: ["#9b7fc4", "#6a4fa0"],
    moon: ["#8d99ae", "#5c6773"],
    asteroid: ["#b08a4a", "#7a5e2e"],
    exoplanet: ["#2a8a78", "#1c5e52"]
  };
  function colorFor(r) { return CAT_COLOR[r.cat_key] || ["#888888", "#555555"]; }

  // ---- 格式化 ----
  var SUP = { "0":"⁰","1":"¹","2":"²","3":"³","4":"⁴","5":"⁵","6":"⁶","7":"⁷","8":"⁸","9":"⁹","-":"⁻" };
  function sup(s) { return String(s).replace(/[0-9-]/g, function (c) { return SUP[c]; }); }
  function sig3(x) {
    if (x === 0) return "0";
    var e = Math.floor(Math.log10(Math.abs(x)));
    var m = x / Math.pow(10, e);
    var s = m.toPrecision(3);
    if (s.indexOf(".") !== -1) s = s.replace(/0+$/, "").replace(/\.$/, "");
    return s + "×10" + sup(e);
  }
  function fmtMass(kg) { return (kg == null) ? "—" : sig3(kg) + " kg"; }
  function fmtRadius(r) {
    if (r == null) return "—";
    return (r < 1000 ? r.toFixed(1) : r.toFixed(0)).replace(/\B(?=(\d{3})+(?!\d))/g, ",") + " km";
  }
  function fmtKm3(v) { return (v == null) ? "—" : sig3(v) + " km³"; }
  function fmtDensity(d) { return (d == null) ? "—" : d + " g/cm³"; }
  function fmtGravity(g) { return (g == null) ? "—" : g.toFixed(2) + " m/s²"; }
  function fmtVelocity(v) { return (v == null) ? "—" : (v < 1 ? v.toFixed(3) : v.toFixed(2)) + " km/s"; }
  function fmtTemp(t) { return (t == null) ? "—" : t + " °C"; }
  function fmtRotation(h) {
    if (h == null) return "—";
    var retro = h < 0, s; h = Math.abs(h);
    s = h >= 48 ? (h / 24).toFixed(2) + " 天" : h.toFixed(2) + " 小时";
    return (retro ? "逆行 · " : "") + s;
  }
  function volume(r) {
    return (r.radius == null) ? null : (4 / 3) * Math.PI * Math.pow(r.radius, 3);
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c];
    });
  }

  // ---- 预加载图片尺寸：按真实宽高比缩放贴图（保留含环天体环系）----
  var pending = rows.length;
  function maybeRender() { if (pending === 0) render(); }
  rows.forEach(function (r) {
    if (!r.image) { pending--; return; }
    var im = new Image();
    im.onload = function () { r._aspect = im.naturalWidth / im.naturalHeight; if (--pending === 0) render(); };
    im.onerror = function () { r._aspect = 1; if (--pending === 0) render(); };
    im.src = r.image;
  });

  // ---- SVG 工具 ----
  var SVGNS = "http://www.w3.org/2000/svg";
  function el(name, attrs) {
    var e = document.createElementNS(SVGNS, name);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }
  function setHref(e, val) {
    e.setAttribute("href", val);
    e.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", val);
  }

  function drawBody(g, cx, cy, rPx, r) {
    var aspect = r._aspect || 1.0;
    var h = 2 * rPx, w = h * aspect;
    if (r.image) {
      var img = el("image", {
        "x": cx - w / 2, "y": cy - h / 2,
        "width": w, "height": h, "preserveAspectRatio": "xMidYMid meet"
      });
      setHref(img, r.image);
      g.appendChild(img);
    } else {
      var c = colorFor(r);
      g.appendChild(el("circle", { "cx": cx, "cy": cy, "r": rPx, "fill": c[0] }));
      var t = el("text", {
        "x": cx, "y": cy, "text-anchor": "middle", "dominant-baseline": "central",
        "class": "sizecmp-initial", "fill": "#fff"
      });
      t.textContent = r.name.charAt(0);
      g.appendChild(t);
    }
    // 球体描边：圆盘天体正好圆边；含环图环自然露出圆外
    g.appendChild(el("circle", {
      "cx": cx, "cy": cy, "r": rPx, "fill": "none", "class": "sizecmp-stroke"
    }));
  }

  function renderViz(a, b) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    if (a.radius == null || b.radius == null) {
      noteEl.textContent = "所选天体缺少半径数据，无法绘制大小对比。";
      return;
    }
    var MAX_PX = 150, MIN_PX = 7;            // 大球半径上限 / 小球半径下限（保可见）
    var scale = MAX_PX / Math.max(a.radius, b.radius);
    var pa = Math.max(a.radius * scale, MIN_PX);
    var pb = Math.max(b.radius * scale, MIN_PX);
    var baseY = 350, gap = 70;
    var totalW = 2 * pa + gap + 2 * pb;
    var startX = (800 - totalW) / 2;
    var cxA = startX + pa, cxB = startX + 2 * pa + gap + pb;
    var g = el("g", {});
    drawBody(g, cxA, baseY - pa, pa, a);
    drawBody(g, cxB, baseY - pb, pb, b);
    svg.appendChild(g);
    function label(cx, r) {
      var t1 = el("text", { "x": cx, "y": baseY + 24, "text-anchor": "middle", "class": "sizecmp-name" });
      t1.textContent = r.name;
      var t2 = el("text", { "x": cx, "y": baseY + 46, "text-anchor": "middle", "class": "sizecmp-sub" });
      t2.textContent = fmtRadius(r.radius);
      svg.appendChild(t1); svg.appendChild(t2);
    }
    label(cxA, a); label(cxB, b);
    var ratio = Math.max(a.radius, b.radius) / Math.min(a.radius, b.radius);
    var clamped = (pa === MIN_PX && a.radius < b.radius) || (pb === MIN_PX && b.radius < a.radius);
    noteEl.textContent =
      "球体按真实直径比例绘制（" + a.name + " " + fmtRadius(a.radius) + " : " +
      b.name + " " + fmtRadius(b.radius) + " ≈ " + ratio.toFixed(1) + " : 1）" +
      (clamped ? "；较小的天体已放大到最小可见尺寸以便观察，倍数以数字为准。" : "。");
  }

  // ---- 核心倍数卡 ----
  function ratioCard(title, va, vb, a, b, fmt) {
    if (va == null || vb == null) return "";
    var big = (va >= vb) ? a : b, small = (va >= vb) ? b : a;
    var bv = (va >= vb) ? va : vb, sv = (va >= vb) ? vb : va;
    var mult = bv / sv, relSmall = sv / bv;
    var cBig = colorFor(big)[0], cSmall = colorFor(small)[0];
    return '<div class="sizecmp-ratio-card">' +
      '<div class="sizecmp-ratio-title">' + title + "</div>" +
      '<div class="sizecmp-ratio-big">' + mult.toPrecision(3) + "×</div>" +
      '<div class="sizecmp-ratio-sub">' + esc(big.name) + " 是 " + esc(small.name) +
        " 的 " + mult.toPrecision(3) + " 倍</div>" +
      '<div class="sizecmp-ratio-rows">' +
        '<div><span class="dot" style="background:' + cBig + '"></span>' +
          esc(big.name) + " <b>1.00×</b> <i>" + (fmt ? fmt(bv) : bv) + "</i></div>" +
        '<div><span class="dot" style="background:' + cSmall + '"></span>' +
          esc(small.name) + " <b>" + relSmall.toPrecision(3) + "×</b> <i>" +
          (fmt ? fmt(sv) : sv) + "</i></div>" +
      "</div></div>";
  }

  // ---- 详细数据表 ----
  function renderDetail(a, b) {
    var defs = [
      ["平均半径", fmtRadius, function (r) { return r.radius; }],
      ["体积", fmtKm3, function (r) { return volume(r); }],
      ["质量", fmtMass, function (r) { return r.mass; }],
      ["平均密度", fmtDensity, function (r) { return r.density; }],
      ["表面重力", fmtGravity, function (r) { return r.gravity; }],
      ["逃逸速度", fmtVelocity, function (r) { return r.escape; }],
      ["平均温度", fmtTemp, function (r) { return r.temp; }],
      ["自转周期", fmtRotation, function (r) { return r.rotation; }]
    ];
    var html = '<table class="sizecmp-table"><thead><tr>' +
      "<th>参数</th><th>" + esc(a.name) + "</th><th>" + esc(b.name) +
      "</th><th>A ÷ B</th></tr></thead><tbody>";
    defs.forEach(function (d) {
      var va = d[2](a), vb = d[2](b);
      var ratio = (va != null && vb) ? (va / vb) : null;
      html += "<tr><th>" + d[0] + "</th><td>" + d[1](va) + "</td><td>" + d[1](vb) +
        "</td><td>" + (ratio == null ? "—" : ratio.toPrecision(3) + "×") + "</td></tr>";
    });
    html += "</tbody></table>";
    detailEl.innerHTML = html;
  }

  function render() {
    var a = byId[selA.value], b = byId[selB.value];
    if (!a || !b) return;
    renderViz(a, b);
    ratiosEl.innerHTML =
      ratioCard("直径", a.radius, b.radius, a, b, fmtRadius) +
      ratioCard("体积", volume(a), volume(b), a, b, fmtKm3) +
      ratioCard("质量", a.mass, b.mass, a, b, fmtMass);
    renderDetail(a, b);
    syncHash(a.id, b.id);
  }

  function syncHash(a, b) {
    var url = location.pathname + location.search + "#cmp=" + a + "," + b;
    if (history.replaceState) history.replaceState(null, "", url);
    else location.hash = "cmp=" + a + "," + b;
    if (shareEl) shareEl.textContent = "分享链接已更新：复制当前地址即可还原此对比组合。";
  }

  // ---- 选择框填充 ----
  function optionHTML(r, sel) {
    return '<option value="' + r.id + '"' + (sel ? " selected" : "") + ">" +
      esc(r.name) + "（" + esc(r.en) + "）</option>";
  }
  function fillSelects(aId, bId) {
    selA.innerHTML = rows.map(function (r) { return optionHTML(r, r.id === aId); }).join("");
    selB.innerHTML = rows.map(function (r) { return optionHTML(r, r.id === bId); }).join("");
    selA.value = aId; selB.value = bId;
  }

  // ---- 初始化 ----
  var m = location.hash.match(/cmp=([\w,]+)/);
  var initA = "moon", initB = "earth";
  if (m) {
    var ids = m[1].split(",");
    if (byId[ids[0]]) initA = ids[0];
    if (byId[ids[1]]) initB = ids[1];
  }
  fillSelects(initA, initB);
  selA.addEventListener("change", render);
  selB.addEventListener("change", render);
  swapBtn.addEventListener("click", function () {
    var t = selA.value; selA.value = selB.value; selB.value = t; render();
  });
  maybeRender();   // 无图片时 pending 已为 0，立即渲染；有图片等 onload
})();
