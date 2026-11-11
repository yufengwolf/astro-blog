/**
 * compare.js — 天体对比工具页（原生 JS，无依赖，无后台）
 *
 * 默认两个选择框（A / B，可先按类型筛选，默认 月球 / 地球）。选择后：
 *   1) 按**真实直径比例**用 HTML 双列（始终横排，移动端亦然）绘制两个天体：贴图
 *      先经 canvas 测量本体球半径占比，把「本体球体」（而非贴图画布）映射到真实
 *      比例——含环图环自然外伸，不叠加基准圈；悬殊比例下较小的一方如实缩为一个
 *      「点」（配实际倍数文字），不做放大处理，大球 CSS 尺寸依容器宽自适应不溢出；
 *   2) 核心倍数卡：直径 / 体积 / 质量的直观倍数（体积 ∝ 半径³）；
 *   3) 详细数据表：直径、体积、质量、密度、表面重力、逃逸速度、温度、自转、类型，逐行 A÷B 倍数。
 * 状态同步到 location.hash（#cmp=a,b），刷新/分享保持对比组合。
 *
 * 数据来自页面内嵌的 #astro-sizecompare-data（gen_pages 注入，含相对图片路径）。
 * v1.8 起直径/质量/光度/温度的单位字符串也在 payload 里预生成（*_text），
 * 本文件不再自带第二套单位实现，改单位规则只需改 gen_pages.py 的 fmt_*。
 */
(function () {
  "use strict";
  var dataEl = document.getElementById("astro-sizecompare-data");
  if (!dataEl) return;
  var vizEl = document.getElementById("sizecmp-viz-canvas");
  var selA = document.getElementById("sizecmp-a");
  var selB = document.getElementById("sizecmp-b");
  var catSelA = document.getElementById("sizecmp-cat-a");
  var catSelB = document.getElementById("sizecmp-cat-b");
  var ratiosEl = document.getElementById("sizecmp-ratios");
  var detailEl = document.getElementById("sizecmp-detail");
  var noteEl = document.getElementById("sizecmp-viz-note");
  var shareEl = document.getElementById("sizecmp-share");
  var toggleEl = document.getElementById("sizecmp-scale");
  var scaleMode = "linear";        // 当前刻度：linear / log
  var userChoseScale = false;      // 用户是否手动选过刻度
  if (!vizEl || !selA || !selB || !catSelA || !catSelB) return;
  var data;
  try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
  var rows = data.rows || [];
  var byId = {};
  rows.forEach(function (r) { byId[r.id] = r; });

  // ---- 全站双语：文案取 i18n.js 词表，天体名取 payload 的 en 字段 ----
  function isEn() { return window.SITE_LANG === 'en'; }
  function T(key, zh) { return window.siteT ? window.siteT(key) : zh; }
  function disp(r) { return isEn() ? (r.en || r.name) : r.name; }

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

  // ---- 格式化 ----
  // num3 / sig3 只服务前端实时计算的量（体积、倍数、密度、重力、速度）。
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
  // ---- 单位字符串：统一读 payload 的预生成字段 ----
  // v1.8 起 gen_pages.py 是唯一实现（fmt_diameter / fmt_mass / fmt_lum / fmt_temp），
  // 这里只做读取，避免详情页与对比页出现两套单位口径。入参一律是行对象。
  // 英文模式仅替换括号与中文基准单位词，数值与 SI 单位一律保持原样。
  function L(s) {
    if (!isEn() || typeof s !== 'string') return s;
    return s.replace(/（/g, ' (').replace(/）/g, ')')
            .replace(/× 太阳直径/g, '× solar diameter')
            .replace(/× 地球直径/g, '× Earth diameter')
            .replace(/太阳质量/g, 'solar mass')
            .replace(/太阳半径/g, 'solar radius')
            .replace(/光年/g, 'ly');
  }
  function textOf(field) {
    return function (r) { return L((r && r[field]) || "—"); };
  }
  var fmtDiameter = textOf("diameter_text");
  var fmtMass = textOf("mass_text");
  var fmtLum = textOf("lum_text");
  var fmtTemp = textOf("temp_text");
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
  function fmtRotation(x) {
    var h = (x && typeof x === "object" && "rotation" in x) ? x.rotation : x;
    if (h == null) return "—";
    var retro = h < 0, s; h = Math.abs(h);
    s = h >= 48 ? (h / 24).toFixed(2) + " " + T("unitDays", "天")
                : h.toFixed(2) + " " + T("unitHours", "小时");
    return (retro ? T("retrograde", "逆行 · ") : "") + s;
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


  function renderViz(a, b) {
    vizEl.innerHTML = "";
    if (a.radius == null || b.radius == null) {
      noteEl.textContent = T("noRadius", "所选天体缺少半径数据，无法绘制大小对比。");
      if (toggleEl) toggleEl.hidden = true;
      return;
    }
    var ratio = Math.max(a.radius, b.radius) / Math.min(a.radius, b.radius);
    var overThreshold = ratio > 1000;
    if (toggleEl) toggleEl.hidden = !overThreshold;
    // 默认始终按真实直径比例：悬殊比例下较小的一方如实缩为点（配文字说明），
    // 不偷换对数刻度造成「看起来差不多大」的错觉；对数刻度仅作可选项保留
    if (!userChoseScale) scaleMode = "linear";
    var useLog = overThreshold && scaleMode === "log";
    // 大球 CSS 半径基准：依容器宽度自适应（手机更小、桌面更大），两球横排不溢出
    var maxCss = 240;
    if (vizEl.clientWidth) maxCss = Math.max(120, Math.min(240, vizEl.clientWidth * 0.42));
    var DOT = Math.max(3, maxCss * 0.02);   // 绘为「点」的本体直径阈值（px）
    function pxOf(r) {
      if (useLog) {
        // 对数刻度：log10(半径) 线性映射到 [DOT, maxCss]——非真实比例，仅让悬殊尺寸都可见
        var rMin = Math.min(a.radius, b.radius), rMax = Math.max(a.radius, b.radius);
        if (rMax === rMin) return maxCss;
        var lMin = Math.log10(rMin), lMax = Math.log10(rMax);
        return DOT + (Math.log10(r.radius) - lMin) / (lMax - lMin) * (maxCss - DOT);
      }
      return r.radius / Math.max(a.radius, b.radius) * maxCss;
    }
    var pa = pxOf(a), pb = pxOf(b);
    // 真实比例下本体直径小于阈值的：不放大、不贴图，绘为点（配实际倍数文字）
    var dotA = !useLog && (2 * pa) < DOT, dotB = !useLog && (2 * pb) < DOT;

    // 每侧贴图按「本体球直径 = 2*px」定高；再由 总宽/总高 共同约束取统一缩放 S，
    // 保证两图都装得下、严格保持宽高比（不变形）、且真实比例不变（两侧同一 S 缩放）
    var availH = Math.min(maxCss * 3.2, (window.innerHeight || 700) * 0.72);
    var gap = 24;  // .sizecmp-viz-inner 的 gap 估算
    function target(r, px) {
      if (r.image) {
        var sf = r._sf || 0.5, ar = r._aspect || 1;
        var h = px / sf;            // 本体球直径 = 2*px（sf=本体球半径/图高）
        return { w: h * ar, h: h }; // 按真实宽高比推导宽度，杜绝变形
      }
      var d = 2 * px;               // 纯色实心球：直径 = 2*px
      return { w: d, h: d };
    }
    var tA = target(a, pa), tB = target(b, pb);
    var sW = (vizEl.clientWidth - gap) / (tA.w + tB.w);   // 两图并排不超出容器
    var sH = Math.min(availH / tA.h, availH / tB.h);       // 任一侧不超出可用高
    var S = Math.max(0.01, Math.min(sW, sH, 1));           // 同一缩放 → 真实比例不变

    function side(r, px, isDot) {
      var col = colorFor(r)[0];
      if (isDot) {
        var big = (r === a) ? b : a;
        return '<div class="sizecmp-side">' +
          '<div class="sizecmp-ball-wrap"><span class="sizecmp-dot" style="background:' + col + '"></span></div>' +
          '<div class="sizecmp-name sizecmp-name-dot">' + esc(disp(r)) + '</div>' +
          '<div class="sizecmp-sub">' + fmtDiameter(r) + '</div>' +
          '<div class="sizecmp-dot-note">' + T('cmpDotOnly', '按真实比例仅 ') +
            (px < 0.1 ? T('cmpDotUnder', '不足 0.1') : px.toFixed(1)) +
            T('cmpDotPx', ' 像素：仅为') +
            (isEn() ? '1/' + fmtRatio(ratio) + ' of ' + esc(disp(big))
                    : esc(disp(big)) + ' 的 1/' + fmtRatio(ratio)) + '</div>' +
          '</div>';
      }
      var ball;
      if (r.image) {
        // width/height 同时按 _aspect（图片真实宽高比，onload 时测得）推导并统一缩放 S，
        // dw/dh = _aspect，严格保持宽高比（不变形）；S 两侧同一值 → 真实比例不变
        var t = (r === a) ? tA : tB;
        var dw = (t.w * S).toFixed(1), dh = (t.h * S).toFixed(1);
        ball = '<img class="sizecmp-img" src="' + esc(r.image) + '" alt="' + esc(disp(r)) +
          '" style="width:' + dw + 'px;height:' + dh + 'px">';
      } else {
        var d = (2 * px * S).toFixed(1);   // 纯色实心球同样按 S 缩放，保持真实比例
        ball = '<span class="sizecmp-solid" style="width:' + d + 'px;height:' + d +
          'px;background:' + col + '">' + esc((disp(r) || '?').charAt(0)) + '</span>';
      }
      return '<div class="sizecmp-side">' +
        '<div class="sizecmp-ball-wrap">' + ball + '</div>' +
        '<div class="sizecmp-name">' + esc(disp(r)) + '</div>' +
        '<div class="sizecmp-sub">' + fmtDiameter(r) + '</div>' +
        '</div>';
    }
    vizEl.innerHTML = '<div class="sizecmp-viz-inner">' + side(a, pa, dotA) + side(b, pb, dotB) + '</div>';
    var extInvolved = a.ext || b.ext;
    var dotNames = [];
    if (dotA) dotNames.push(disp(a));
    if (dotB) dotNames.push(disp(b));
    var parts = [];
    if (extInvolved) parts.push(T('cmpExtNote', '星系/星云等延展天体以等效球径示意（非真实形状），具体尺度以数字为准'));
    if (dotNames.length) parts.push(dotNames.join(isEn() ? ', ' : '、') +
      T('cmpDotNote', ' 在真实比例下已缩为一个点（旁标实际倍数），未作放大'));
    var tail = parts.length ? (isEn() ? '. ' + parts.join('. ') + '.' : '；' + parts.join('；') + '。')
                            : (isEn() ? '.' : '。');
    noteEl.textContent =
      T(extInvolved ? 'cmpObject' : 'cmpSphere', extInvolved ? '天体' : '球体') +
      (isEn() ? ' ' : '') +
      T(useLog ? 'cmpLogNote' : 'cmpLinearNote',
        useLog ? '按对数刻度绘制（非真实比例，仅让悬殊尺寸都可见）' : '按真实直径比例绘制') +
      (isEn() ? ' (' : '（') + disp(a) + ' ' + fmtDiameter(a) + ' : ' + disp(b) + ' ' + fmtDiameter(b) +
      ' ≈ ' + fmtRatio(ratio) + ' : 1' + (isEn() ? ')' : '）') + tail;
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
      '<div class="sizecmp-ratio-sub">' + (isEn()
        ? esc(disp(big)) + ' is ' + mult.toPrecision(3) + '× ' + esc(disp(small))
        : esc(disp(big)) + ' 是 ' + esc(disp(small)) + ' 的 ' + mult.toPrecision(3) + ' 倍') + '</div>' +
      '<div class="sizecmp-ratio-rows">' +
        '<div><span class="dot" style="background:' + cBig + '"></span>' +
          esc(disp(big)) + " <b>1.00×</b> <i>" + (fmt ? fmt(big) : bv) + "</i></div>" +
        '<div><span class="dot" style="background:' + cSmall + '"></span>' +
          esc(disp(small)) + " <b>" + relSmall.toPrecision(3) + "×</b> <i>" +
          (fmt ? fmt(small) : sv) + "</i></div>" +
      "</div></div>";
  }

  // ---- 详细数据表 ----（fmt 接收行对象）
  function renderDetail(a, b) {
    var defs = [
      [T('rDiameter', '直径'), fmtDiameter, function (r) { return r.radius; }],
      [T('rVolumeEq', '体积（等效球）'), fmtKm3, function (r) { return volume(r); }],
      [T('rMass', '质量'), fmtMass, function (r) { return r.mass; }],
      [T('fLum', '光度'), fmtLum, function (r) { return r.lum; }],
      [T('fDensity', '平均密度'), fmtDensity, function (r) { return r.density; }],
      [T('rGravity', '表面重力'), fmtGravity, function (r) { return r.gravity; }],
      [T('fEscape', '逃逸速度'), fmtVelocity, function (r) { return r.escape; }],
      [T('rTemp', '平均温度'), fmtTemp, function (r) { return r.temp; }],
      [T('fRotation', '自转周期'), fmtRotation, function (r) { return r.rotation; }],
      // 类型细分为字符串（恒星类型/星云类型/星系类型等），无倍数概念，仅展示
      [T('rType', '类型'), function (r) { return r.subtype || "—"; }, function (r) { return r.subtype; }]
    ];
    var html = '<table class="sizecmp-table"><thead><tr>' +
      '<th>' + T('cmpParam', '参数') + '</th><th>' + esc(disp(a)) + '</th><th>' + esc(disp(b)) +
      "</th><th>A ÷ B</th></tr></thead><tbody>";
    defs.forEach(function (d) {
      var va = d[2](a), vb = d[2](b);
      var ratio = (typeof va === "number" && typeof vb === "number" && vb) ? (va / vb) : null;
      html += "<tr><th>" + d[0] + "</th><td>" + d[1](a) + "</td><td>" + d[1](b) +
        "</td><td>" + (ratio == null ? "—" : ratio.toPrecision(3) + "×") + "</td></tr>";
    });
    html += "</tbody></table>";
    // 移动端 4 列数值易折行：包一层横向滚动（≥600px 时 CSS 取消 min-width 不滚动）
    detailEl.innerHTML = '<div class="sizecmp-detail-scroll">' + html + "</div>";
  }

  function render() {
    var a = byId[selA.value], b = byId[selB.value];
    if (!a || !b) return;
    renderViz(a, b);
    // 倍数一律用底层 radius/mass 原始数值算：半径比 === 直径比，缩放与口径都不受影响；
    // 展示文本则由 fmtDiameter/fmtMass 读 payload 的预生成字符串（v1.8 起统一）。
    ratiosEl.innerHTML =
      ratioCard(T('rDiameter', '直径'), a.radius, b.radius, a, b, fmtDiameter) +
      ratioCard(T('rVolume', '体积'), volume(a), volume(b), a, b, fmtKm3) +
      ratioCard(T('rMass', '质量'), a.mass, b.mass, a, b, fmtMass);
    renderDetail(a, b);
    syncHash(a.id, b.id);
  }

  function syncHash(a, b) {
    var url = location.pathname + location.search + "#cmp=" + a + "," + b;
    if (history.replaceState) history.replaceState(null, "", url);
    else location.hash = "cmp=" + a + "," + b;
    if (shareEl) shareEl.textContent = T('shareHint', '分享链接已更新：复制当前地址即可还原此对比组合。');
  }

  // ---- 选择框填充（支持按类型筛选）----
  // 选项标签跟随全站语言切换：中文模式中文名、英文模式英文名；数据侧 r.en 已在 payload 内
  function optionHTML(r, sel) {
    return '<option value="' + r.id + '"' + (sel ? " selected" : "") + ">" +
      esc(disp(r)) + "</option>";
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
    var html = '<option value="">' + T('allTypes', '全部类型') + '</option>' + catOrder.map(function (c) {
      var label = window.siteCat ? window.siteCat(c[1]) : c[0];
      return '<option value="' + c[1] + '">' + esc(label) + "</option>";
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
  // 窗口缩放 / 旋屏：容器宽度跨越 600px 断点时重排（横排 ↔ 纵堆叠）
  var resizeTimer = null;
  window.addEventListener("resize", function () {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      var a = byId[selA.value], b = byId[selB.value];
      if (a && b) render();
    }, 150);
  });
  // 顶栏切换语言：重建下拉选项与表格文案，保持当前对比组合不丢失
  if (window.onSiteLang) window.onSiteLang(function () {
    var a = selA.value, b = selB.value;
    fillCatSelects();
    fillSelects(a, b);
    render();
  });
  maybeRender();   // 无图片时 pending 已为 0，立即渲染；有图片等 onload
})();
