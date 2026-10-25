/**
 * astro-size-compare.js — 天体对比工具页（原生 JS，无依赖，无后台）
 *
 * 默认两个选择框（A / B，可先按类型筛选，默认 月球 / 地球）。选择后：
 *   1) 按**真实直径比例**用 SVG 绘制两个球体：贴图先经 canvas 测量本体球半径
 *      占比，把「本体球体」（而非贴图画布）映射到真实比例——含环图环自然外伸，
 *      不叠加基准圈；悬殊比例下较小的一方如实缩为一个「点」（配实际倍数文字），
 *      不做放大处理，图幅超宽时整体等比缩小自适应页面；
 *   2) 核心倍数卡：直径 / 体积 / 质量的直观倍数（体积 ∝ 半径³）；
 *   3) 详细数据表：半径、体积、质量、密度、表面重力、逃逸速度、温度、自转、类型，逐行 A÷B 倍数。
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
  var catSelA = document.getElementById("sizecmp-cat-a");
  var catSelB = document.getElementById("sizecmp-cat-b");
  var swapBtn = document.getElementById("sizecmp-swap");
  var ratiosEl = document.getElementById("sizecmp-ratios");
  var detailEl = document.getElementById("sizecmp-detail");
  var noteEl = document.getElementById("sizecmp-viz-note");
  var shareEl = document.getElementById("sizecmp-share");
  var toggleEl = document.getElementById("sizecmp-scale");
  var scaleMode = "linear";        // 当前刻度：linear / log
  var userChoseScale = false;      // 用户是否手动选过刻度
  if (!svg || !selA || !selB || !catSelA || !catSelB) return;
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
    exoplanet: ["#2a8a78", "#1c5e52"],
    black_hole: ["#7a7ab8", "#2a2a4a"],
    nebula: ["#e06ac8", "#8a2f6e"],
    galaxy: ["#f2c94c", "#8a5a00"],
    cluster: ["#d9a5ff", "#6a3a8a"],
    structure: ["#7fd4ff", "#2a6a8a"],
    comet: ["#7fe0d0", "#1f7a6a"]
  };
  function colorFor(r) { return CAT_COLOR[r.cat_key] || ["#888888", "#555555"]; }

  var LY_KM = 9.4607e12;
  var EXT_CATS = { nebula: 1, galaxy: 1, cluster: 1, structure: 1 };

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
  // 中段值（1e-3 ~ 1e3）普通计数法，极端值科学计数法（与 gen_pages.py 的 num3 一致）
  function num3(x) {
    if (x === 0) return "0";
    var a = Math.abs(x);
    if (a >= 1e-3 && a < 1e3) {
      var s = x.toPrecision(3);
      if (s.indexOf(".") !== -1) s = s.replace(/0+$/, "").replace(/\.$/, "");
      return s;
    }
    return sig3(x);
  }
  function fmtLum(x) {
    var w = (x && typeof x === "object" && "lum" in x) ? x.lum : x;
    return (w == null) ? "—" : num3(w / 3.828e26) + " L☉";
  }
  // 按天体类型格式化半径（入参可以是行对象或纯数值）
  function fmtRadius(x) {
    var r = (x && typeof x === "object" && "radius" in x) ? x : null;
    var v = r ? r.radius : x;
    if (v == null) return "—";
    var ck = r ? r.cat_key : null;
    if (ck === "star") {
      var rs = v / 695700;
      if (rs < 0.001) return sig3(rs) + " R☉";                       // 脉冲星/白矮星
      if (rs >= 1000) return Math.round(rs).toLocaleString("en-US") + " R☉";  // 红超巨星
      return num3(rs) + " R☉";
    }
    if (ck === "black_hole") return v >= 1e8 ? sig3(v / 1.496e8) + " AU" : sig3(v) + " km";
    if (ck && EXT_CATS[ck]) {
      var ly = v / LY_KM;
      if (ly < 0.001) return sig3(ly) + " 光年";
      if (ly >= 1000) return Math.round(ly).toLocaleString("en-US") + " 光年";
      return num3(ly) + " 光年";
    }
    return (v < 1000 ? v.toFixed(1) : v.toFixed(0)).replace(/\B(?=(\d{3})+(?!\d))/g, ",") + " km";
  }
  // 质量：恒星/黑洞/星系/星团/大尺度结构用 M☉，行星用 kg
  var MASS_SUN_CATS = { star: 1, black_hole: 1, galaxy: 1, cluster: 1, structure: 1, nebula: 1 };
  function fmtMassCat(x) {
    var r = (x && typeof x === "object" && "mass" in x) ? x : null;
    var v = r ? r.mass : x;
    if (v == null) return "—";
    return (r && MASS_SUN_CATS[r.cat_key]) ? num3(v / 1.9884e30) + " M☉" : sig3(v) + " kg";
  }
  function fmtKm3(x) {
    var v = (x && typeof x === "object") ? volume(x) : x;
    return (v == null) ? "—" : sig3(v) + " km³";
  }
  function fmtDensity(x) {
    var d = (x && typeof x === "object" && "density" in x) ? x.density : x;
    if (d == null) return "—";
    // 中子星密度可达 10¹⁴ g/cm³、红超巨星低至 10⁻⁹，用科学计数法
    return num3(d) + " g/cm³";
  }
  function fmtGravity(x) {
    var g = (x && typeof x === "object" && "gravity" in x) ? x.gravity : x;
    if (g == null) return "—";
    if (g >= 1e4 || (g > 0 && g < 0.01)) return sig3(g) + " m/s²";   // 白矮星/中子星/超巨星
    return g.toFixed(2) + " m/s²";
  }
  function fmtVelocity(x) {
    var v = (x && typeof x === "object" && "escape" in x) ? x.escape : x;
    if (v == null) return "—";
    if (v >= 1e5) return sig3(v) + " km/s";                          // 中子星逃逸速度
    return (v < 1 ? v.toFixed(3) : v.toFixed(2)) + " km/s";
  }
  // 恒星/星云/大尺度结构的 mean_temp_c 为「开尔文-273.15」等效值，展示 K（与详情页一致）
  function fmtTemp(x) {
    var r = (x && typeof x === "object" && "temp" in x) ? x : null;
    var t = r ? r.temp : x;
    if (t == null) return "—";
    var ck = r ? r.cat_key : null;
    if (ck === "star" || ck === "nebula" || ck === "structure") {
      var k = t + 273.15;
      if (k >= 1e6) return sig3(k) + " K";
      return Math.round(k).toLocaleString("en-US") + " K";
    }
    return t + " °C";
  }
  function fmtRotation(x) {
    var h = (x && typeof x === "object" && "rotation" in x) ? x.rotation : x;
    if (h == null) return "—";
    var retro = h < 0, s; h = Math.abs(h);
    s = h >= 48 ? (h / 24).toFixed(2) + " 天" : h.toFixed(2) + " 小时";
    return (retro ? "逆行 · " : "") + s;
  }
  // 倍数的人类可读格式：≥100 千分位整数（33,600 而非 3.36e+4），中段 3 位有效数字
  function fmtRatio(x) {
    if (x >= 100) return Math.round(x).toLocaleString("en-US");
    if (x >= 10) return x.toFixed(1);
    return x.toPrecision(3);
  }
  function volume(r) {
    return (r.radius == null) ? null : (4 / 3) * Math.PI * Math.pow(r.radius, 3);
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c];
    });
  }

  // ---- 预加载图片：测真实宽高比 + 本体球半径占比 ----
  // 贴图按「本体居中」构建：圆盘图本体占画布高 70%，含环图环向外伸展。
  // 对比图需按「本体球体」（而非整个画布）映射真实比例——否则球体比真实
  // 比例小 30%，且基准圆会悬浮在球体外（用户看到的"外面一圈"）。
  // 测量方法：在缩小的 canvas 上二分查找「以图中心为圆心、圆内不透明像素
  // 占比 ≥ 92% 的最大圆」——该圆恰好止步于本体边缘（环/光晕在四周留透明，
  // 占比下降即被截住），椭球天体（妊神星）止步于赤道半径，形变如实呈现。
  var pending = rows.length;
  function maybeRender() { if (pending === 0) render(); }
  function measureSphere(im) {
    try {
      var S = 128, ar = im.naturalWidth / im.naturalHeight;
      var w = ar >= 1 ? S : Math.max(8, Math.round(S * ar));
      var h = ar >= 1 ? Math.max(8, Math.round(S / ar)) : S;
      var cv = document.createElement("canvas");
      cv.width = w; cv.height = h;
      var ctx = cv.getContext("2d");
      if (!ctx) return null;
      ctx.drawImage(im, 0, 0, w, h);
      var d = ctx.getImageData(0, 0, w, h).data;
      var cx = w / 2, cy = h / 2, hi = Math.min(cx, cy);
      function cover(R) {
        var n = 0, op = 0, R2 = R * R;
        for (var y = 0; y < h; y++) for (var x = 0; x < w; x++) {
          var dx = x + 0.5 - cx, dy = y + 0.5 - cy;
          if (dx * dx + dy * dy <= R2) { n++; if (d[(y * w + x) * 4 + 3] >= 40) op++; }
        }
        return n ? op / n : 0;
      }
      var lo = 0;
      if (cover(hi) >= 0.92) { lo = hi; }
      else for (var i = 0; i < 8; i++) {
        var mid = (lo + hi) / 2;
        if (cover(mid) >= 0.92) lo = mid; else hi = mid;
      }
      return lo > 0 ? lo / h : null;   // 本体球半径 / 图高
    } catch (e) { return null; }
  }
  rows.forEach(function (r) {
    if (!r.image) { pending--; return; }
    var im = new Image();
    im.onload = function () {
      r._aspect = im.naturalWidth / im.naturalHeight;
      r._sf = measureSphere(im);
      if (--pending === 0) render();
    };
    im.onerror = function () { r._aspect = 1; r._sf = null; if (--pending === 0) render(); };
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

  function drawBody(g, cx, cy, rPx, r, asDot) {
    if (asDot) {
      // 真实比例下本体半径已不足挂载贴图：绘为分类色「点」，边界即球体本身，
      // 名称下方附实际比例说明——宁可小而真实，不放大到与更大天体视觉混淆
      var c = colorFor(r);
      var rr = Math.max(1.2, rPx);
      g.appendChild(el("circle", { "cx": cx, "cy": cy, "r": rr, "fill": c[0] }));
      g.appendChild(el("circle", {
        "cx": cx, "cy": cy, "r": rr, "fill": "none", "class": "sizecmp-stroke"
      }));
      return;
    }
    if (r.image) {
      if (r.ext) {
        // 延展天体（星云/星系/星团/大尺度结构）：贴图全幅≈天体本身，
        // 按「全幅=等效直径（2×rPx）」绘制——较长边映射直径，保留真实宽高比，
        // 属等效球径示意（非真实形状），具体尺度以数字为准
        var ar = r._aspect || 1;
        var W2, H2;
        if (ar >= 1) { W2 = 2 * rPx; H2 = W2 / ar; } else { H2 = 2 * rPx; W2 = H2 * ar; }
        var img2 = el("image", {
          "x": cx - W2 / 2, "y": cy - H2 / 2,
          "width": W2, "height": H2, "preserveAspectRatio": "xMidYMid meet"
        });
        setHref(img2, r.image);
        g.appendChild(img2);
        return;
      }
      // 图内本体球半径映射为 rPx：图高 H = rPx / sf（sf 为测得的本体球半径
      // 占图高比例；测量失败按本站贴图构建约定 0.35 兜底）。含环图环自然
      // 超出球体范围向外伸展，不再叠加描边基准圆。
      var sf = r._sf || 0.35;
      var H = rPx / sf, W = H * (r._aspect || 1);
      var img = el("image", {
        "x": cx - W / 2, "y": cy - H / 2,
        "width": W, "height": H, "preserveAspectRatio": "xMidYMid meet"
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
      // 仅无贴图的纯色圆保留描边（即球体边界本身，非悬浮基准圈）
      g.appendChild(el("circle", {
        "cx": cx, "cy": cy, "r": rPx, "fill": "none", "class": "sizecmp-stroke"
      }));
    }
  }

  function renderViz(a, b) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    if (a.radius == null || b.radius == null) {
      noteEl.textContent = "所选天体缺少半径数据，无法绘制大小对比。";
      if (toggleEl) toggleEl.hidden = true;
      return;
    }
    var VW = 1000, VH = 760, MARGIN = 30, GAP = 90;
    var MAX_PX = 240, DOT_PX = 4;            // 大球半径上限 / 绘为「点」的本体半径阈值
    var ratio = Math.max(a.radius, b.radius) / Math.min(a.radius, b.radius);
    var overThreshold = ratio > 1000;
    if (toggleEl) toggleEl.hidden = !overThreshold;
    // 默认始终按真实直径比例：悬殊比例下较小的一方如实缩为点（配文字说明），
    // 不偷换对数刻度造成「看起来差不多大」的错觉；对数刻度仅作可选项保留
    if (!userChoseScale) scaleMode = "linear";
    var useLog = overThreshold && scaleMode === "log";
    function drawn(r, rPx) {
      if (r.ext && r.image) {
        // 延展天体：全幅=等效直径（与 drawBody 的 ext 分支一致）
        var ar2 = r._aspect || 1;
        return ar2 >= 1 ? { w: 2 * rPx, h: 2 * rPx / ar2 } : { w: 2 * rPx * ar2, h: 2 * rPx };
      }
      if (!r.image) return { w: 2 * rPx, h: 2 * rPx };
      var h = rPx / (r._sf || 0.35);
      return { w: h * (r._aspect || 1), h: h };
    }
    var pa, pb;
    if (useLog) {
      // 对数刻度：把 log10(半径) 线性映射到 [MIN_PX, MAX_PX]——非真实比例，仅让悬殊尺寸都可见
      var rMin = Math.min(a.radius, b.radius), rMax = Math.max(a.radius, b.radius);
      var lMin = Math.log10(rMin), lMax = Math.log10(rMax);
      function logPx(r) {
        if (lMax === lMin) return MAX_PX;
        return DOT_PX + (Math.log10(r) - lMin) / (lMax - lMin) * (MAX_PX - DOT_PX);
      }
      pa = logPx(a.radius); pb = logPx(b.radius);
    } else {
      var scale = MAX_PX / Math.max(a.radius, b.radius);
      pa = a.radius * scale;
      pb = b.radius * scale;
    }
    // 真实比例下本体半径小于阈值的：不放大、不贴图，绘为点（布局占位同点尺寸）
    var dotA = !useLog && pa < DOT_PX, dotB = !useLog && pb < DOT_PX;
    function layout(r, rPx, isDot) {
      return isDot ? { w: 2 * DOT_PX, h: 2 * DOT_PX } : drawn(r, rPx);
    }
    // 自适应页面：贴图外沿总宽超出画布时整体等比缩小（真实比例不变），
    // 窄屏下 SVG 随容器宽度等比缩放，同一套比例适配任意屏宽
    var totalW = layout(a, pa, dotA).w + layout(b, pb, dotB).w + GAP;
    var fit = Math.min(1, (VW - 2 * MARGIN) / totalW);
    pa *= fit; pb *= fit;
    var da = layout(a, pa, dotA), db = layout(b, pb, dotB);
    var baseY = 650;                          // 球体底边基线（下有名称标注）
    var startX = (VW - (da.w + db.w + GAP)) / 2;
    var cxA = startX + da.w / 2, cxB = startX + da.w + GAP + db.w / 2;
    var g = el("g", {});
    drawBody(g, cxA, baseY - (dotA ? DOT_PX * fit : pa), dotA ? DOT_PX * fit : pa, a, dotA);
    drawBody(g, cxB, baseY - (dotB ? DOT_PX * fit : pb), dotB ? DOT_PX * fit : pb, b, dotB);
    svg.appendChild(g);
    function label(cx, r, isDot, realPx) {
      var t1 = el("text", {
        "x": cx, "y": baseY + 26, "text-anchor": "middle",
        "class": "sizecmp-name" + (isDot ? " sizecmp-name-dot" : "")
      });
      t1.textContent = r.name;
      var t2 = el("text", { "x": cx, "y": baseY + 48, "text-anchor": "middle", "class": "sizecmp-sub" });
      t2.textContent = fmtRadius(r);
      svg.appendChild(t1); svg.appendChild(t2);
      if (isDot) {
        // 点模式：加一行醒目的实际比例说明（大字名称 + 小字倍数，数字为准）
        var big = (r === a) ? b : a;
        var t3 = el("text", {
          "x": cx, "y": baseY + 70, "text-anchor": "middle", "class": "sizecmp-dot-note"
        });
        t3.textContent = "按真实比例仅 " + (realPx < 0.1 ? "不足 0.1" : realPx.toFixed(1)) +
          " 像素：仅为" + big.name + "的 1/" + fmtRatio(ratio);
        svg.appendChild(t3);
      }
    }
    label(cxA, a, dotA, dotA ? a.radius * (MAX_PX / Math.max(a.radius, b.radius)) : pa);
    label(cxB, b, dotB, dotB ? b.radius * (MAX_PX / Math.max(a.radius, b.radius)) : pb);
    var extInvolved = a.ext || b.ext;
    var dotNames = [];
    if (dotA) dotNames.push(a.name);
    if (dotB) dotNames.push(b.name);
    // 补充说明句：延展天体口径 + 点模式说明，按有无拼接到基数句之后
    var parts = [];
    if (extInvolved) parts.push("星系/星云等延展天体以等效球径示意（非真实形状），具体尺度以数字为准");
    if (dotNames.length) parts.push(dotNames.join("、") + " 在真实比例下已缩为一个点（旁边标注实际倍数），未作放大处理");
    var tail = parts.length ? "；" + parts.join("；") + "。" : "。";
    noteEl.textContent =
      (extInvolved ? "天体" : "球体") + (useLog ? "按对数刻度绘制（非真实比例，仅让悬殊尺寸都可见）" : "按真实直径比例绘制") +
      "（" + a.name + " " + fmtRadius(a) + " : " + b.name + " " + fmtRadius(b) +
      " ≈ " + fmtRatio(ratio) + " : 1）" + tail;
    updateToggleUI();
  }

  function updateToggleUI() {
    if (!toggleEl) return;
    var btns = toggleEl.querySelectorAll("button");
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle("active", btns[i].getAttribute("data-mode") === scaleMode);
    }
  }

  // ---- 核心倍数卡 ----（fmt 接收行对象，按类型取合适单位）
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
          esc(big.name) + " <b>1.00×</b> <i>" + (fmt ? fmt(big) : bv) + "</i></div>" +
        '<div><span class="dot" style="background:' + cSmall + '"></span>' +
          esc(small.name) + " <b>" + relSmall.toPrecision(3) + "×</b> <i>" +
          (fmt ? fmt(small) : sv) + "</i></div>" +
      "</div></div>";
  }

  // ---- 详细数据表 ----（fmt 接收行对象）
  function renderDetail(a, b) {
    var defs = [
      ["半径 / 大小", fmtRadius, function (r) { return r.radius; }],
      ["体积（等效球）", fmtKm3, function (r) { return volume(r); }],
      ["质量", fmtMassCat, function (r) { return r.mass; }],
      ["光度", fmtLum, function (r) { return r.lum; }],
      ["平均密度", fmtDensity, function (r) { return r.density; }],
      ["表面重力", fmtGravity, function (r) { return r.gravity; }],
      ["逃逸速度", fmtVelocity, function (r) { return r.escape; }],
      ["平均温度", fmtTemp, function (r) { return r.temp; }],
      ["自转周期", fmtRotation, function (r) { return r.rotation; }],
      // 类型细分为字符串（恒星类型/星云类型/星系类型等），无倍数概念，仅展示
      ["类型", function (r) { return r.subtype || "—"; }, function (r) { return r.subtype; }]
    ];
    var html = '<table class="sizecmp-table"><thead><tr>' +
      "<th>参数</th><th>" + esc(a.name) + "</th><th>" + esc(b.name) +
      "</th><th>A ÷ B</th></tr></thead><tbody>";
    defs.forEach(function (d) {
      var va = d[2](a), vb = d[2](b);
      var ratio = (typeof va === "number" && typeof vb === "number" && vb) ? (va / vb) : null;
      html += "<tr><th>" + d[0] + "</th><td>" + d[1](a) + "</td><td>" + d[1](b) +
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
      ratioCard("质量", a.mass, b.mass, a, b, fmtMassCat);
    renderDetail(a, b);
    syncHash(a.id, b.id);
  }

  function syncHash(a, b) {
    var url = location.pathname + location.search + "#cmp=" + a + "," + b;
    if (history.replaceState) history.replaceState(null, "", url);
    else location.hash = "cmp=" + a + "," + b;
    if (shareEl) shareEl.textContent = "分享链接已更新：复制当前地址即可还原此对比组合。";
  }

  // ---- 选择框填充（支持按类型筛选）----
  function optionHTML(r, sel) {
    return '<option value="' + r.id + '"' + (sel ? " selected" : "") + ">" +
      esc(r.name) + "（" + esc(r.en) + "）</option>";
  }
  // 分类集合：按 rows 出现顺序去重（数据侧已按分类排序，天然稳定）
  var catOrder = [], catSeen = {};
  rows.forEach(function (r) {
    if (!catSeen[r.cat]) { catSeen[r.cat] = 1; catOrder.push([r.cat, r.cat_key]); }
  });
  function visibleRows(catKey) {
    return catKey ? rows.filter(function (r) { return r.cat_key === catKey; }) : rows;
  }
  // 当前选中若已被筛选出列表，回退到该列表首项（保证 select.value 始终有效）
  function pickFallback(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return id;
    return list.length ? list[0].id : "";
  }
  function fillCatSelects() {
    var html = '<option value="">全部类型</option>' + catOrder.map(function (c) {
      return '<option value="' + c[1] + '">' + esc(c[0]) + "</option>";
    }).join("");
    catSelA.innerHTML = html; catSelB.innerHTML = html;
  }
  function fillSelects(aId, bId) {
    var ra = visibleRows(catSelA.value), rb = visibleRows(catSelB.value);
    aId = pickFallback(ra, aId); bId = pickFallback(rb, bId);
    selA.innerHTML = ra.map(function (r) { return optionHTML(r, r.id === aId); }).join("");
    selB.innerHTML = rb.map(function (r) { return optionHTML(r, r.id === bId); }).join("");
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
  fillCatSelects();
  fillSelects(initA, initB);
  selA.addEventListener("change", render);
  selB.addEventListener("change", render);
  catSelA.addEventListener("change", function () { fillSelects(selA.value, selB.value); render(); });
  catSelB.addEventListener("change", function () { fillSelects(selA.value, selB.value); render(); });
  swapBtn.addEventListener("click", function () {
    // 分类随天体一起交换，保证两侧 option 必然存在
    var t = catSelA.value; catSelA.value = catSelB.value; catSelB.value = t;
    fillSelects(selB.value, selA.value);
    render();
  });
  if (toggleEl) {
    toggleEl.querySelectorAll("button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        scaleMode = btn.getAttribute("data-mode");
        userChoseScale = true;
        updateToggleUI();
        var a = byId[selA.value], b = byId[selB.value];
        if (a && b) render();
      });
    });
  }
  maybeRender();   // 无图片时 pending 已为 0，立即渲染；有图片等 onload
})();
