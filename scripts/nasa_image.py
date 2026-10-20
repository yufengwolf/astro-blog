#!/usr/bin/env python3
"""nasa_image.py — 从 NASA 图片库安装天体真实影像（与 AI 贴图流水线互补）。

分工：有真实照片/官方概念图的天体用真图（本脚本）；没有的（如鸟神星，
NASA 库无图）才用 blog-pipeline 的 AI 贴图。脚本只做四件事：
  下载（images-api.nasa.gov，公共领域）
  → 圆盘裁剪 + 透明化 + 缩放到 600px webp 入库 docs/assets/planets/<id>.webp
  → astro.json 登记 image / image_credit / image_url
  → 打 image_locked=true（此后 sync_textures.py 不会用 AI 贴图覆盖它）

用法：
  python scripts/nasa_image.py --search pluto          # 搜 NASA 图片库，列候选
  python scripts/nasa_image.py --set pluto PIA19857 "NASA/New Horizons（JHUAPL·SwRI）"
  python scripts/nasa_image.py pluto                    # 按 docs/data/nasa_images.json 登记表安装
  python scripts/nasa_image.py pluto earth eris         # 一次装多个

登记表 docs/data/nasa_images.json 可手改（id → nasa_id + credit）。
"""
import argparse
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG_PATH = ROOT / "docs" / "data" / "nasa_images.json"
ASTRO = ROOT / "docs" / "data" / "astro.json"
PLANET_DIR = ROOT / "docs" / "assets" / "planets"
API = "https://images-api.nasa.gov"
UA = {"User-Agent": "astro-blog-maintainer/1.0 (personal data site)"}


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


def install(oid: str, nasa_id: str, credit: str, crop=None,
            half: str | None = None, ellipse: bool = False) -> bool:
    """下载并安装一张 NASA 影像。
    crop=(cx,cy,r)：手动圆盘（占宽/高/短边的比例），用于含环/多面板图；
    half：先裁半幅再检测（双球拼图取其一）；ellipse：椭圆抠图（土豆形天体）。"""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None        # 放行超大图（如 PIA00478 的 10240px）
    tmp = PLANET_DIR / f".{oid}_nasa_raw.jpg"
    PLANET_DIR.mkdir(parents=True, exist_ok=True)
    tier = download_best(nasa_id, tmp)
    im = Image.open(tmp).convert("RGB")
    if half:
        w, h = im.size
        box = {"left": (0, 0, w // 2, h), "right": (w // 2, 0, w, h),
               "top": (0, 0, w, h // 2), "bottom": (0, h // 2, w, h)}[half]
        im = im.crop(box)
    arr = np.asarray(im)
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
    target = 600 * 0.70                  # 圆盘长轴缩至 600 画布的 70%，与 AI 贴图一致
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
    o["image_url"] = f"https://images.nasa.gov/details/{nasa_id}"
    o["image_locked"] = True
    ASTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(f"  {oid}: {nasa_id}（{tier} 档，{dst.stat().st_size // 1024}KB）"
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
    ap = argparse.ArgumentParser(description="安装 NASA 真实天体影像（圆盘裁剪+署名+锁定）")
    ap.add_argument("ids", nargs="*", help="按登记表安装（对象 id）")
    ap.add_argument("--search", default="", help="搜 NASA 图片库列候选")
    ap.add_argument("--set", nargs=3, metavar=("ID", "NASA_ID", "CREDIT"),
                    help="登记并安装：--set pluto PIA19857 \"NASA/New Horizons\"")
    ap.add_argument("--crop", nargs=3, type=float, metavar=("CX", "CY", "R"),
                    help="手动圆盘（占宽高比例）：--crop 0.5 0.5 0.45（土星等有环天体）")
    ap.add_argument("--half", choices=["left", "right", "top", "bottom"],
                    help="先裁半幅再检测（双球/双面板拼图取其一）")
    ap.add_argument("--ellipse", action="store_true",
                    help="椭圆抠图（土豆形天体：火卫一/土卫七等）")
    args = ap.parse_args()

    if args.search:
        return do_search(args.search)

    reg = load_reg()
    if args.set:
        oid, nasa_id, credit = args.set
        reg[oid] = {"nasa_id": nasa_id, "credit": credit}
        save_reg(reg)
        print(f"登记表更新：{oid} -> {nasa_id}")
        return 0 if install(oid, nasa_id, credit, crop=args.crop,
                            half=args.half, ellipse=args.ellipse) else 1

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
        if not install(oid, e["nasa_id"], e["credit"]):
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
