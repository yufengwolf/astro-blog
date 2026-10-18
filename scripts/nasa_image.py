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
    """按 orig → large → medium 优先级下载，返回实际用的档位名。"""
    urls = manifest_urls(nasa_id)
    for tier in ("orig", "large", "medium"):
        for u in urls:
            if f"~{tier}.jpg" in u:
                dest.write_bytes(api_get(u))
                return tier
    raise RuntimeError(f"{nasa_id} 无可下载 jpg（manifest: {urls}）")


def detect_disk(arr):
    """星空照里定位主体圆盘：亮度掩码 + 行列剖面 2% 阈值（抗星点离群）。
    返回 (cx, cy, r)——已按内切 0.995 收缩的圆。"""
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
    return (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2, \
        min(xs.max() - xs.min(), ys.max() - ys.min()) / 2 * 0.995


def install(oid: str, nasa_id: str, credit: str) -> bool:
    import numpy as np
    from PIL import Image
    tmp = PLANET_DIR / f".{oid}_nasa_raw.jpg"
    PLANET_DIR.mkdir(parents=True, exist_ok=True)
    tier = download_best(nasa_id, tmp)
    im = Image.open(tmp).convert("RGB")
    arr = np.asarray(im).astype(np.int16)
    cx, cy, r = detect_disk(arr)
    # 以圆盘为中心裁正方形（clamp 到画面内）
    side = int(2 * r)
    x0 = int(max(0, min(cx - r, im.width - side)))
    y0 = int(max(0, min(cy - r, im.height - side)))
    crop = im.crop((x0, y0, x0 + side, y0 + side))
    # 圆内保留、圆外透明；圆外 RGB 填黑（太空色），边缘插值不掺白
    yy, xx = np.mgrid[0:side, 0:side]
    inside = ((xx - side / 2) ** 2 + (yy - side / 2) ** 2) <= (side / 2 * 0.995) ** 2
    rgba = np.dstack([np.asarray(crop).astype(np.uint8),
                      np.where(inside, 255, 0).astype(np.uint8)])
    rgba[~inside, :3] = 0
    tex = Image.fromarray(rgba, "RGBA")
    # 圆盘直径缩至 600 画布的 70%，与 AI 贴图视觉占比一致
    scale = (600 * 0.70) / tex.width
    tex = tex.resize((round(tex.width * scale), round(tex.height * scale)),
                     Image.LANCZOS)
    canvas = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
    canvas.paste(tex, ((600 - tex.width) // 2, (600 - tex.height) // 2), tex)
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
    args = ap.parse_args()

    if args.search:
        return do_search(args.search)

    reg = load_reg()
    if args.set:
        oid, nasa_id, credit = args.set
        reg[oid] = {"nasa_id": nasa_id, "credit": credit}
        save_reg(reg)
        print(f"登记表更新：{oid} -> {nasa_id}")
        return 0 if install(oid, nasa_id, credit) else 1

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
