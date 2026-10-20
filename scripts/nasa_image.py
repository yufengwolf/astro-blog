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
  --rings  含环天体保留行星+环整体：全包围盒矩形裁剪 → Otsu 阈值 +
           边缘洪水填充去太空背景 + 小连通域过滤（去星点/卫星/亮星芒）
           → 长边 600 的宽幅透明 webp（不裁成圆，环是行星的标志特征）
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
            "crop", "half", "ellipse")


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
    """按 orig → large → medium → small 优先级下载，返回实际用的档位名。"""
    urls = manifest_urls(nasa_id)
    for tier in ("orig", "large", "medium", "small"):
        for u in urls:
            if f"~{tier}.jpg" in u:
                dest.write_bytes(api_get(u))
                return tier
    raise RuntimeError(f"{nasa_id} 无可下载 jpg（manifest: {urls}）")


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
    if soft and soft >= 15:
        # 亮核+光晕衰减路径（韦布辉光场），不依赖洪水填充
        from PIL import ImageFilter
        core = ((lum > thr + 30) * 255).astype(np.uint8)
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
        rgba = np.dstack([a, alpha])
        return Image.fromarray(rgba, "RGBA"), thr
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
    return Image.fromarray(rgba, "RGBA"), thr


def install(oid: str, nasa_id: str, credit: str, crop=None,
            half: str | None = None, ellipse: bool = False,
            rings: bool = False, focus=None,
            src_url: str | None = None, page_url: str | None = None,
            darkthr=None, soft=None) -> bool:
    """下载并安装一张真实影像。
    默认圆/椭圆盘抠图；rings=True 保留行星+环整体（宽幅透明 webp）。
    focus=(x0,y0,x1,y1) 按比例预裁剪；src_url 直连下载（ESA/韦布图）。
    soft<15 仅 alpha 抗锯齿；soft>=15 启用亮核+光晕衰减（韦布辉光场）。"""
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
    if rings:
        # 行星+环整体：全包围盒矩形裁剪，长边占满 600，不裁成圆
        cx, cy, rx0, ry0 = detect_disk(arr)
        pw, ph = int(rx0 * 1.04), int(ry0 * 1.04)
        x0 = int(max(0, cx - pw)); x1 = int(min(im.width, cx + pw))
        y0 = int(max(0, cy - ph)); y1 = int(min(im.height, cy + ph))
        tex = im.crop((x0, y0, x1, y1))
        scale = 600.0 / max(tex.width, tex.height)
        tex = tex.resize((max(1, round(tex.width * scale)),
                          max(1, round(tex.height * scale))), Image.LANCZOS)
        out, thr = cut_space(tex, darkthr, soft)
        print(f"  [rings] 包围盒 ({x0},{y0})-({x1},{y1})，暗色阈值 thr={thr}"
              + (f"，软边 soft={soft}" if soft else ""))
        dst = PLANET_DIR / f"{oid}.webp"
        out.save(dst, "WEBP", quality=85)
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
    ap.add_argument("--ellipse", action="store_true",
                    help="椭圆抠图（土豆形天体：火卫一/土卫七等）")
    args = ap.parse_args()

    if args.search:
        return do_search(args.search)

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
        reg[oid] = entry
        save_reg(reg)
        print(f"登记表更新：{oid} -> {nasa_id}"
              + ("（含环模式）" if args.rings else ""))
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
