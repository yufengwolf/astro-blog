#!/usr/bin/env python3
"""nasa_image.py — 从 NASA/ESA 图片库安装天体真实影像（与 AI 贴图流水线互补）。

分工：有真实照片/官方概念图的天体用真图（本脚本）；没有的（如鸟神星，
NASA 库无图）才用 blog-pipeline 的 AI 贴图。脚本只做四件事：
  下载（images-api.nasa.gov 公共领域；ESA/韦布图走 esawebb.org，CC BY 4.0）
  → 裁剪 + 透明化 + 缩放入库 docs/assets/planets/<id>.webp
  → astro.json 登记 image / image_credit / image_url
  → 打 image_locked=true（此后 sync_textures.py 不会用 AI 贴图覆盖它）

两种抠图模式：
  默认     圆/椭圆盘抠图——适合无环天体（输出 600×600，圆盘占 70%）
  --rings  含环天体保留行星+环整体：以行星本体圆为锚裁剪缩放，球体直径
           统一 420（=600 画布高的 70%，与圆盘图一致、跨天体等大），环
           随本体等比呈现；画布高 600、宽按环伸展，本体恒居中，环出画布
           边缘渐隐。本体圆几何优先用登记表 planet=[cx,cy,r]（分数坐标，
           手动标定；斜环+卫星图自动检测必失准，如土星 PIA00349），无则
           95 分位亮区自动检测（planet_r 可手动覆盖半径）
  --frame  全幅模式——星系/星云/星团等延展天体：不抠圆，整幅缩至最长边
           600px，四边约 5% 渐隐；对比页按「全幅=等效球径」绘制（示意）
其他可选：
  --crop CX CY R      手动圆盘（自动检测不准时，如土星环与行星交织）
  --half L/R/T/B      双球/双面板拼图先取半幅
  --focus X0 Y0 X1 Y1 按比例预裁剪（如韦布海王星图先裁掉左上亮星衍射芒）
  --src-url URL       直接从 URL 下载（ESA/韦布图不在 NASA API），nasa_id 仅作标签
  --page-url URL      astro.json image_url 出处页（默认 images.nasa.gov/details/<id>）
  --darkthr N         跳过 Otsu 手动定暗色阈值（背景有星云辉光时用）

用法：
  python scripts/nasa_image.py --search pluto          # 搜 NASA 图片库，列候选
  python scripts/nasa_image.py --set pluto PIA19857 "NASA/New Horizons（JHUAPL·SwRI）"
  python scripts/nasa_image.py pluto                    # 按登记表安装
  python scripts/nasa_image.py pluto earth eris         # 一次装多个

登记表 docs/data/nasa_images.json 可手改，形如：
  {"saturn": {"nasa_id": "PIA02225", "credit": "…", "rings": true,
              "focus": [0.3, 0.4, 0.8, 0.9], "src_url": "…", "page_url": "…"}}
重跑 `python scripts/nasa_image.py <id>` 会按登记表参数复现，不会丢模式。
"""
import argparse
import json
import sys
import urllib.request
from collections import deque
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG_PATH = ROOT / "docs" / "data" / "nasa_images.json"
ASTRO = ROOT / "docs" / "data" / "astro.json"
PLANET_DIR = ROOT / "docs" / "assets" / "planets"
API = "https://images-api.nasa.gov"
UA = {"User-Agent": "astro-blog-maintainer/1.0 (personal data site)"}
OPT_KEYS = ("rings", "focus", "src_url", "page_url", "darkthr", "soft",
            "crop", "half", "ellipse", "planet_r", "gain", "planet", "frame")


def api_get(url: str, timeout: int = 90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def api_json(url: str, timeout: int = 30):
    return json.loads(api_get(url, timeout).decode())


def load_reg() -> dict:
    if REG_PATH.exists():
        return json.loads(REG_PATH.read_text(encoding="utf-8"))
    return {}


def save_reg(reg: dict):
    REG_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")


def manifest_urls(nasa_id: str) -> list:
    d = api_json(f"{API}/asset/{nasa_id}")
    return [i["href"] for i in d.get("collection", {}).get("items", [])
            if i["href"].endswith(".jpg")]


def download_best(nasa_id: str, dest: Path) -> str:
    """下载所有可用档位，取字节最大者（分辨率最高）。
    不能只信 orig：部分图的 orig 是几十 KB 的缩略图（如 PIA03158）。"""
    urls = manifest_urls(nasa_id)
    best_tier, best_data = None, b""
    for tier in ("orig", "large", "medium", "small"):
        for u in urls:
            if f"~{tier}.jpg" in u:
                try:
                    data = api_get(u)
                except Exception:
                    continue
                if len(data) > len(best_data):
                    best_tier, best_data = tier, data
    if best_tier is None:
        raise RuntimeError(f"{nasa_id} 无可下载 jpg（manifest: {urls}）")
    dest.write_bytes(best_data)
    return best_tier


def detect_disk(arr):
    """星空照里定位主体：亮度掩码 + 行列剖面 2% 阈值（抗星点离群）。
    返回 (cx, cy, rx, ry)——主体 bbox 的中心与半宽/半高（已按 0.995 收缩）。"""
    import numpy as np
    h, w, _ = arr.shape
    mask = arr.max(axis=2) > 16          # 太空近黑，主体亮
    colc = mask.sum(axis=0)
    rowc = mask.sum(axis=1)
    thr = max(colc.max(), rowc.max()) * 0.02
    xs = np.where(colc > thr)[0]
    ys = np.where(rowc > thr)[0]
    if len(xs) < 2 or len(ys) < 2:
        raise RuntimeError("未检测到主体圆盘")
    cx = (xs.min() + xs.max()) / 2
    cy = (ys.min() + ys.max()) / 2
    rx = (xs.max() - xs.min()) / 2 * 0.995
    ry = (ys.max() - ys.min()) / 2 * 0.995
    return cx, cy, rx, ry


def otsu_threshold(lum) -> int:
    """Otsu 自动阈值：太空(暗)与主体(亮)双峰直方图的最佳分割点。"""
    import numpy as np
    hist = np.bincount(lum.ravel(), minlength=256).astype(np.float64)
    total = lum.size
    sum_all = float(np.dot(np.arange(256), hist))
    sum_b = w_b = 0.0
    best = 0.0
    thr = 24
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        v = w_b * w_f * (m_b - m_f) ** 2
        if v > best:
            best = v
            thr = t
    return thr


def cut_space(tex, darkthr=None, soft=None):
    """含环天体去太空背景。两档算法（按 soft 大小自动选择）：
    soft < 15  二值抠图 + 模糊羽化——Otsu/手动阈值 + 边缘洪水填充 +
               小连通域过滤（删星点/卫星），最后 alpha 高斯模糊抗锯齿。
               只有从画面边缘可达的暗区才算太空（环缝等被环包住的暗区
               保留为不透明，免得浅色背景透白缝）。适合背景干净的图。
    soft >= 15 亮核 + 光晕衰减——韦布图的辉光场比环还亮且一直延伸，
               洪水填充边界会变成阶梯状脏边；改用亮核（lum>thr+30）
               高斯模糊向外平滑衰减到 0，暗区 RGB 同时用模糊版替换
               （去噪点纹理），边缘 12% 羽化兜底。
    返回 RGBA（透明背景，行星+环整体保留）。"""
    import numpy as np
    from PIL import Image
    h, w = tex.height, tex.width
    a = np.asarray(tex.convert("RGB"))
    lum = a.astype(np.int16).max(axis=2)
    if darkthr is not None:
        thr = int(darkthr)
    else:
        thr = max(10, int(otsu_threshold(lum) * 0.75))
    # 行星本体半径（用于统一各天体显示尺寸）：取最亮 5%（95 分位）像素的
    # 包围盒半宽/半高较大者。自适应阈值——土星环暗、行星最亮；韦布行星
    # 过曝，其亮核即行星。比固定 +60 更能避免环亮纹污染行星半径。
    Tc = float(np.percentile(lum, 95))
    bright = lum > Tc
    _cols = np.where(bright.any(axis=0))[0]
    _rows = np.where(bright.any(axis=1))[0]
    if len(_cols) >= 2 and len(_rows) >= 2:
        # 行星近似圆形：环只沿水平拉长，取 X/Y 半宽较小者作行星半径，
        # 避免把环的横向跨度误算进行星直径（土星环极宽时尤甚）。
        planet_r = float(min((_cols.max() - _cols.min()) / 2,
                             (_rows.max() - _rows.min()) / 2))
    else:
        planet_r = float(max(h, w))
    if soft and soft >= 15:
        # 亮核+光晕衰减路径（韦布辉光场），不依赖洪水填充
        from PIL import ImageFilter
        # 亮核阈值自适应：取 90 分位——韦布图行星盘常只占画面 ~10%，
        # 固定 thr+30 会卡在盘面亮度以下、alpha 掉到几十（海王星实测）
        core_thr = max(float(np.percentile(lum, 90)), thr + 10)
        core = ((lum > core_thr) * 255).astype(np.uint8)
        halo = np.asarray(Image.fromarray(core, "L").filter(
            ImageFilter.GaussianBlur(float(soft) * 2))).astype(np.float32) / 255.0
        alpha = (np.clip(halo * 1.15, 0, 1) * 255).astype(np.uint8)
        # RGB 降噪：暗区（辉光/噪点）用模糊版替换，亮区保持锐利
        blur_rgb = Image.fromarray(a, "RGB").filter(
            ImageFilter.GaussianBlur(float(soft) / 2))
        wgt = np.clip((lum - thr) / 80.0, 0, 1)[:, :, None]
        a = (a * wgt + np.asarray(blur_rgb) * (1 - wgt)).astype(np.uint8)
        # 边缘羽化：辉光被 focus 裁剪边界硬切时兜底
        feather = max(10, int(min(h, w) * 0.12))
        yy2, xx2 = np.mgrid[0:h, 0:w]
        edge = np.minimum.reduce([xx2, yy2, w - 1 - xx2, h - 1 - yy2]).astype(np.float32)
        alpha = (alpha * np.clip(edge / feather, 0, 1)).astype(np.uint8)
        alpha = np.asarray(Image.fromarray(alpha, "L")
                           .filter(ImageFilter.GaussianBlur(float(soft))))
        # 归一化：两级高斯模糊会稀释峰值（实测海王星盘面中心 alpha 仅 ~100），
        # 按最大值归一到 255，保证行星本体完全不透明、光晕按比例渐隐
        if alpha.max() > 0:
            alpha = (alpha.astype(np.float32) * (255.0 / float(alpha.max()))
                     ).clip(0, 255).astype(np.uint8)
        rgba = np.dstack([a, alpha])
        return Image.fromarray(rgba, "RGBA"), thr, planet_r
    dark = lum <= thr
    # 从画面四边洪水填充：连通暗区 = 太空背景
    bg = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if dark[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if dark[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        if y > 0 and dark[y - 1, x] and not bg[y - 1, x]:
            bg[y - 1, x] = True; dq.append((y - 1, x))
        if y < h - 1 and dark[y + 1, x] and not bg[y + 1, x]:
            bg[y + 1, x] = True; dq.append((y + 1, x))
        if x > 0 and dark[y, x - 1] and not bg[y, x - 1]:
            bg[y, x - 1] = True; dq.append((y, x - 1))
        if x < w - 1 and dark[y, x + 1] and not bg[y, x + 1]:
            bg[y, x + 1] = True; dq.append((y, x + 1))
    fg = ~bg
    # 连通域过滤：删卫星/星点等小组件（行星与环都是大连通域，保留）
    min_area = max(40, h * w // 600)
    keep = np.zeros((h, w), bool)
    seen = np.zeros((h, w), bool)
    for yy in range(h):
        row_fg = fg[yy]
        row_seen = seen[yy]
        for xx in range(w):
            if not row_fg[xx] or row_seen[xx]:
                continue
            comp = [(yy, xx)]
            seen[yy, xx] = True
            q = deque([(yy, xx)])
            while q:
                cy_, cx_ = q.popleft()
                if cy_ > 0 and fg[cy_ - 1, cx_] and not seen[cy_ - 1, cx_]:
                    seen[cy_ - 1, cx_] = True; comp.append((cy_ - 1, cx_)); q.append((cy_ - 1, cx_))
                if cy_ < h - 1 and fg[cy_ + 1, cx_] and not seen[cy_ + 1, cx_]:
                    seen[cy_ + 1, cx_] = True; comp.append((cy_ + 1, cx_)); q.append((cy_ + 1, cx_))
                if cx_ > 0 and fg[cy_, cx_ - 1] and not seen[cy_, cx_ - 1]:
                    seen[cy_, cx_ - 1] = True; comp.append((cy_, cx_ - 1)); q.append((cy_, cx_ - 1))
                if cx_ < w - 1 and fg[cy_, cx_ + 1] and not seen[cy_, cx_ + 1]:
                    seen[cy_, cx_ + 1] = True; comp.append((cy_, cx_ + 1)); q.append((cy_, cx_ + 1))
            if len(comp) >= min_area:
                for py, px in comp:
                    keep[py, px] = True
    if not keep.any():
        raise RuntimeError(f"cut_space: 全图被判为背景（thr={thr}），用 --darkthr 调整")
    alpha = np.where(keep, 255, 0).astype(np.uint8)
    if soft:
        # 小半径软边：纯抗锯齿（羽化硬二值边缘）
        from PIL import ImageFilter
        alpha = np.asarray(Image.fromarray(alpha, "L")
                           .filter(ImageFilter.GaussianBlur(float(soft))))
    rgba = np.dstack([a, alpha])
    return Image.fromarray(rgba, "RGBA"), thr, planet_r


def install(oid: str, nasa_id: str, credit: str, crop=None,
            half: str | None = None, ellipse: bool = False,
            rings: bool = False, focus=None,
            src_url: str | None = None, page_url: str | None = None,
            darkthr=None, soft=None, planet_r=None, gain=None,
            planet=None, frame: bool = False) -> bool:
    """下载并安装一张真实影像。
    默认圆/椭圆盘抠图；rings=True 保留行星+环整体（宽幅透明 webp）。
    frame=True 全幅模式（星系/星云/星团等延展天体）：不抠圆形，整幅缩至
    最长边 600px，四边约 5% 透明渐隐融入星空底；对比页按「全幅=等效球径」绘制。
    focus=(x0,y0,x1,y1) 按比例预裁剪；src_url 直连下载（ESA/韦布图）。
    soft<15 仅 alpha 抗锯齿；soft>=15 启用亮核+光晕衰减（韦布辉光场）。
    planet_r 手动指定行星本体半径 px（裁剪后坐标系，自动检测不准时用）。
    planet=[cx,cy,r] 手动标定行星本体圆（分数坐标：cx/cy 相对裁剪后图幅
    宽/高，r 相对高）——斜环+卫星场景自动检测必失准（如 PIA00349 土星），
    用 limb 扫描+最小二乘圆拟合一次性标定后写入登记表永久复现。"""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None        # 放行超大图（如 PIA00478 的 10240px）
    tmp = PLANET_DIR / f".{oid}_nasa_raw.jpg"
    PLANET_DIR.mkdir(parents=True, exist_ok=True)
    if src_url:
        tmp.write_bytes(api_get(src_url))
        tier = "direct"
    else:
        tier = download_best(nasa_id, tmp)
    im = Image.open(tmp).convert("RGB")
    if gain and gain != 1.0:
        # 亮度增益：提亮暗淡源图（如韦布海王星红外片）。必须在 cut_space
        # 之前做——亮核 alpha 掩码依赖亮度，后补提亮救不了 alpha。
        from PIL import ImageEnhance
        im = ImageEnhance.Brightness(im).enhance(float(gain))
    if half:
        w, h = im.size
        box = {"left": (0, 0, w // 2, h), "right": (w // 2, 0, w, h),
               "top": (0, 0, w, h // 2), "bottom": (0, h // 2, w, h)}[half]
        im = im.crop(box)
    if focus:
        fw, fh = im.size
        im = im.crop((int(focus[0] * fw), int(focus[1] * fh),
                      int(focus[2] * fw), int(focus[3] * fh)))
    b = 3                                # 去边缘装饰白框（如有）
    im = im.crop((b, b, im.width - b, im.height - b))
    arr = np.asarray(im)
    if frame:
        # 全幅模式（延展天体）：整幅缩至最长边 600px，四边约 5% 渐隐融入星空底。
        # 不做圆形抠图——星系旋臂/星云形态/星团成员都应完整保留。
        scale = 600.0 / max(im.width, im.height)
        new_w = max(1, round(im.width * scale))
        new_h = max(1, round(im.height * scale))
        tex = im.resize((new_w, new_h), Image.LANCZOS)
        feather = max(8, int(min(new_w, new_h) * 0.05))
        yy, xx = np.mgrid[0:new_h, 0:new_w]
        edge = np.minimum.reduce([xx, yy, new_w - 1 - xx, new_h - 1 - yy]).astype(np.float32)
        fade = np.clip(edge / feather, 0, 1)
        rgba = np.dstack([np.asarray(tex).astype(np.uint8),
                          (fade * 255).astype(np.uint8)])
        canvas = Image.fromarray(rgba, "RGBA")
        dst = PLANET_DIR / f"{oid}.webp"
        canvas.save(dst, "WEBP", quality=85)
        print(f"  [frame] 全幅 {new_w}×{new_h}px（源 {im.width}×{im.height}），"
              f"四边渐隐 {feather}px")
    elif rings:
        # 行星+环整体。本体圆来源：登记表 planet=[cx,cy,r]（分数坐标）优先，
        # 否则 95 分位亮区自动检测（斜环+卫星图会失准，见 install docstring）。
        # 缩放只以本体为准：球体直径=600 画布高的 70%（=420，与圆盘图一致，
        # 跨天体等大），环随本体等比呈现；画布高固定 600、宽按环伸展。
        if planet:
            pcx = float(planet[0]) * im.width
            pcy = float(planet[1]) * im.height
            prad = float(planet[2]) * im.height
            print(f"  [rings] 手动本体圆 ({pcx:.0f},{pcy:.0f}) r={prad:.0f}px")
        else:
            lum = arr.max(axis=2)
            Tc = float(np.percentile(lum, 95))
            bright = lum > Tc
            _c = np.where(bright.any(axis=0))[0]
            _r = np.where(bright.any(axis=1))[0]
            if len(_c) >= 2 and len(_r) >= 2:
                pcx = float((_c.min() + _c.max()) / 2)
                pcy = float((_r.min() + _r.max()) / 2)
                # 取 X/Y 半宽较小者作行星半径：环横向拉长不会污染行星半径
                prad = float(min((_c.max() - _c.min()) / 2, (_r.max() - _r.min()) / 2))
            else:
                pcx, pcy, prad = im.width / 2, im.height / 2, max(im.width, im.height) / 2
            if planet_r:                       # 手动覆盖半径（自动检测失准时）
                prad = float(planet_r)
        # 环伸展：低亮阈抓环，相对本体有界增长（防远处卫星/背景撑爆画布；
        # 环斜置时纵向伸展大，上限放宽到 2.6 倍半径）
        lum = arr.max(axis=2)
        Tring = max(12.0, float(np.percentile(lum, 95)) * 0.35)
        rmask = lum > Tring
        rc = np.where(rmask.any(axis=0))[0]
        rr = np.where(rmask.any(axis=1))[0]
        if len(rc) >= 2 and len(rr) >= 2:
            hw = float((rc.max() - rc.min()) / 2)
            hh = float((rr.max() - rr.min()) / 2)
        else:
            hw, hh = prad * 2.3, prad * 1.6
        hw = min(max(hw, prad * 1.3), prad * 4.0)
        hh = min(max(hh, prad * 1.1), prad * 2.6)
        # 低亮阈会漏掉环的最外圈暗部（测出的 bbox 偏紧，环带在画布内被硬切），
        # 在 clamp 上限内四周加 6% 余量，能用足画幅就用足
        hw = min(hw + 0.06 * im.width, prad * 4.0)
        hh = min(hh + 0.06 * im.height, prad * 2.6)
        x0 = int(max(0, round(pcx - hw))); x1 = int(min(im.width, round(pcx + hw)))
        y0 = int(max(0, round(pcy - hh))); y1 = int(min(im.height, round(pcy + hh)))
        tex = im.crop((x0, y0, x1, y1))
        if darkthr is not None and gain:
            darkthr = darkthr * gain    # 阈值坐标系随提亮同步放大
        out, thr, auto_r = cut_space(tex, darkthr, soft)
        target_d = 420.0                      # 球体直径 = 600 画布高的 70%
        scale = target_d / (2 * prad) if prad > 0 else 420.0 / max(tex.width, tex.height)
        new_w = max(1, round(tex.width * scale))
        new_h = max(1, round(tex.height * scale))
        print(f"  [rings] 环伸展 {hw:.0f}×{hh:.0f}px，裁剪 ({x0},{y0})-({x1},{y1})，"
              f"缩放 {scale:.3f}，thr={thr}"
              + (f"，soft={soft}" if soft else ""))
        tex = out.resize((new_w, new_h), Image.LANCZOS)   # out 已是去背景 RGBA
        # 画布高固定 600、球体直径固定 420（占 70%，与圆盘图一致）。
        # 贴图按「本体圆心」对齐画布中心——裁剪框被图像边界截成不对称时，
        # 按纹理中心贴会让本体偏移甚至出画布（上一版土星本体被截的根因）。
        # 环超出画布边缘的部分由四边 24px alpha 渐隐平滑淡出（星空底不突兀）。
        canvas_h = 600
        canvas_w = min(max(new_w, 600), 2000)
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        paste_x = int(round(canvas_w / 2 - (pcx - x0) * scale))
        paste_y = int(round(canvas_h / 2 - (pcy - y0) * scale))
        canvas.paste(tex, (paste_x, paste_y), tex)
        ca = np.asarray(canvas).astype(np.float32)
        ch2, cw2 = ca.shape[:2]
        fade = 36.0
        yy2, xx2 = np.mgrid[0:ch2, 0:cw2]
        edge = np.minimum.reduce([xx2, yy2, cw2 - 1 - xx2, ch2 - 1 - yy2]).astype(np.float32)
        ca[:, :, 3] = ca[:, :, 3] * np.clip(edge / fade, 0, 1)
        canvas = Image.fromarray(ca.astype(np.uint8), "RGBA")
        dst = PLANET_DIR / f"{oid}.webp"
        canvas.save(dst, "WEBP", quality=85)
    else:
        if crop:  # 手动圆盘
            cx = crop[0] * im.width
            cy = crop[1] * im.height
            rx = ry = crop[2] * min(im.width, im.height)
        else:
            cx, cy, rx0, ry0 = detect_disk(arr)
            if ellipse:
                rx, ry = rx0, ry0
            else:
                rx = ry = min(rx0, ry0)
        # 裁正方形（包住整个 bbox）→ 先缩放再抠 alpha（大图内存友好）
        side = int(2 * max(rx, ry))
        x0 = int(max(0, min(cx - max(rx, ry), im.width - side)))
        y0 = int(max(0, min(cy - max(rx, ry), im.height - side)))
        tex = im.crop((x0, y0, x0 + side, y0 + side))
        target = 600 * 0.70              # 圆盘长轴缩至 600 画布的 70%，与 AI 贴图一致
        scale = target / max(tex.width, tex.height)
        tex = tex.resize((max(1, round(tex.width * scale)),
                          max(1, round(tex.height * scale))), Image.LANCZOS)
        w2, h2 = tex.size
        yy, xx = np.mgrid[0:h2, 0:w2]
        # 半径换算到缩放后坐标系（掩码在缩放图上计算）
        nx = (xx - w2 / 2) / (rx * scale)
        ny = (yy - h2 / 2) / (ry * scale)
        inside = (nx ** 2 + ny ** 2) <= 0.995 ** 2
        rgba = np.dstack([np.asarray(tex).astype(np.uint8),
                          np.where(inside, 255, 0).astype(np.uint8)])
        rgba[~inside, :3] = 0
        out = Image.fromarray(rgba, "RGBA")
        canvas = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
        canvas.paste(out, ((600 - w2) // 2, (600 - h2) // 2), out)
        dst = PLANET_DIR / f"{oid}.webp"
        canvas.save(dst, "WEBP", quality=85)
    tmp.unlink(missing_ok=True)

    # 登记进 astro.json：影像路径 + 署名 + 锁定
    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    hit = [o for o in data["objects"] if o["id"] == oid]
    if not hit:
        print(f"[error] astro.json 无对象 {oid}")
        return False
    o = hit[0]
    o["image"] = f"assets/planets/{oid}.webp"
    o["image_credit"] = credit
    o["image_url"] = page_url or f"https://images.nasa.gov/details/{nasa_id}"
    o["image_locked"] = True
    ASTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(f"  {oid}: {nasa_id}（{tier}，{dst.stat().st_size // 1024}KB）"
          f" -> {dst.relative_to(ROOT)}，astro.json 已登记并锁定")
    return True


def do_search(q: str, n: int = 8):
    import urllib.parse
    d = api_json(f"{API}/search?q={urllib.parse.quote(q)}&media_type=image")
    items = d.get("collection", {}).get("items", [])
    print(f"== NASA 图片库搜索「{q}」（{len(items)} 命中，列前 {n}）==")
    for it in items[:n]:
        dd = it["data"][0]
        print(f"  {dd.get('nasa_id'):22s} {(dd.get('date_created') or '')[:10]} "
              f"{(dd.get('title') or '')[:60]}")
        desc = (dd.get("description") or "").replace("\n", " ")[:110]
        if desc:
            print(f"      {desc}")
    print("\n选定后：python scripts/nasa_image.py --set <对象id> <nasa_id> \"<署名>\"")
    return 0


def auto_pick(query: str, title_kw=()):
    """搜索 NASA 图片库并挑最佳候选：标题命中关键词加分，取分数最高者。
    返回 (nasa_id, title, credit) 或 None。"""
    import urllib.parse
    d = api_json(f"{API}/search?q={urllib.parse.quote(query)}&media_type=image")
    items = d.get("collection", {}).get("items", [])
    best = None
    for it in items[:25]:
        dd = it["data"][0]
        nid = dd.get("nasa_id")
        title = dd.get("title") or ""
        if not nid:
            continue
        tl = title.lower()
        score = 0
        for kw in title_kw:
            if kw.lower() in tl:
                score += 3
        for w in query.lower().split():
            if len(w) > 2 and w in tl:
                score += 1
        if best is None or score > best[0]:
            best = (score, nid, title, dd)
    if not best:
        return None
    _, nid, title, dd = best
    center = (dd.get("center") or "").strip()
    credit = f"NASA/{center} · {title[:40]}" if center else f"NASA · {title[:40]}"
    return nid, title, credit


def do_auto_batch(pairs, frame: bool):
    """pairs: [(oid, query, [title_kw...]), ...] 逐个人搜图→装图（frame 模式）。
    单个失败只记录不影响其余；返回失败数。"""
    fails = 0
    for item in pairs:
        oid, query = item[0], item[1]
        kws = item[2] if len(item) > 2 else ()
        try:
            pick = auto_pick(query, kws)
        except Exception as e:
            print(f"[fail] {oid}：搜索出错 {e}")
            fails += 1
            continue
        if not pick:
            print(f"[fail] {oid}：NASA 库无「{query}」可用结果（保留程序化贴图）")
            fails += 1
            continue
        nid, title, credit = pick
        print(f"[auto] {oid} → {nid}《{title[:50]}》")
        try:
            if not install(oid, nid, credit, frame=frame):
                fails += 1
        except Exception as e:
            print(f"[fail] {oid}：安装出错 {e}")
            fails += 1
    return fails


def main() -> int:
    ap = argparse.ArgumentParser(description="安装真实天体影像（圆盘裁剪或含环宽幅 + 署名 + 锁定）")
    ap.add_argument("ids", nargs="*", help="按登记表安装（对象 id）")
    ap.add_argument("--search", default="", help="搜 NASA 图片库列候选")
    ap.add_argument("--set", nargs=3, metavar=("ID", "NASA_ID", "CREDIT"),
                    help="登记并安装：--set pluto PIA19857 \"NASA/New Horizons\"")
    ap.add_argument("--rings", action="store_true",
                    help="含环天体：保留行星+环整体（宽幅透明 webp，不裁成圆）")
    ap.add_argument("--crop", nargs=3, type=float, metavar=("CX", "CY", "R"),
                    help="手动圆盘（占宽高比例）：--crop 0.5 0.5 0.45")
    ap.add_argument("--half", choices=["left", "right", "top", "bottom"],
                    help="先裁半幅再检测（双球/双面板拼图取其一）")
    ap.add_argument("--focus", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"),
                    help="按比例预裁剪：--focus 0.35 0.45 0.75 0.9（韦布海王星裁亮星）")
    ap.add_argument("--src-url", help="直接从 URL 下载（ESA/韦布图不在 NASA API）")
    ap.add_argument("--page-url", help="astro.json image_url 出处页")
    ap.add_argument("--darkthr", type=float, help="手动暗色阈值（跳过 Otsu）")
    ap.add_argument("--soft", type=float, metavar="R",
                    help="软边：<15 仅抗锯齿（如 3）；>=15 亮核+光晕衰减，韦布辉光场用（如 20/25）")
    ap.add_argument("--planet-r", type=float, metavar="PX",
                    help="手动行星本体半径 px（裁剪后坐标系；自动检测不准时，如韦布海王星）")
    ap.add_argument("--gain", type=float, metavar="F",
                    help="亮度增益（提亮暗淡源图，如韦布海王星 1.35）")
    ap.add_argument("--ellipse", action="store_true",
                    help="椭圆抠图（土豆形天体：火卫一/土卫七等）")
    ap.add_argument("--frame", action="store_true",
                    help="全幅模式（星系/星云/星团等延展天体）：不抠圆，整幅缩放+边缘渐隐")
    ap.add_argument("--auto-batch", nargs="+", metavar="ID:QUERY",
                    help="批量自动模式：'对象id:搜索词[:标题关键词]'，自动挑图并安装")
    args = ap.parse_args()

    if args.search:
        return do_search(args.search)

    if args.auto_batch:
        pairs = []
        for tok in args.auto_batch:
            parts = tok.split(":")
            if len(parts) < 2:
                print(f"[skip] 格式应为 对象id:搜索词[:关键词]，得到 {tok!r}")
                continue
            pairs.append((parts[0], parts[1], parts[2:]))
        fails = do_auto_batch(pairs, frame=args.frame)
        print(f"批量完成：{len(pairs) - fails}/{len(pairs)} 成功")
        return 1 if fails else 0

    reg = load_reg()
    if args.set:
        oid, nasa_id, credit = args.set
        entry = {"nasa_id": nasa_id, "credit": credit}
        if args.rings:
            entry["rings"] = True
        if args.focus:
            entry["focus"] = args.focus
        if args.src_url:
            entry["src_url"] = args.src_url
        if args.page_url:
            entry["page_url"] = args.page_url
        if args.darkthr is not None:
            entry["darkthr"] = args.darkthr
        if args.soft is not None:
            entry["soft"] = args.soft
        if args.planet_r is not None:
            entry["planet_r"] = args.planet_r
        if args.gain is not None:
            entry["gain"] = args.gain
        if args.frame:
            entry["frame"] = True
        reg[oid] = entry
        save_reg(reg)
        print(f"登记表更新：{oid} -> {nasa_id}"
              + ("（含环模式）" if args.rings else "")
              + ("（全幅模式）" if args.frame else ""))
        opts = {k: entry[k] for k in OPT_KEYS if k in entry}
        return 0 if install(oid, nasa_id, credit, **opts) else 1

    if not args.ids:
        ap.print_help()
        return 1
    rc = 0
    for oid in args.ids:
        if oid not in reg:
            print(f"[skip] {oid} 未登记；先 --search 找图再 --set，或手改 "
                  f"{REG_PATH.relative_to(ROOT)}")
            rc = 1
            continue
        e = reg[oid]
        if not install(oid, e["nasa_id"], e["credit"],
                       **{k: e[k] for k in OPT_KEYS if k in e}):
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
