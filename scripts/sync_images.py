#!/usr/bin/env python3
"""sync_images.py — 通用图片编排（AI 编排层的出图入口）。

给定 astro.json，按 category 路由到对应生成器，保证每个对象都有贴图。

出图优先级（2026-10-26 用户拍板）：
  1) image_locked=True 的（NASA 真图手动锁定）→ 不动，绝不覆盖
  2) 否则优先用【豆包 AI 生成】（127.0.0.1:9090, model=doubao-image）
       - 豆包实测只输出 RGB（background:"transparent" 也不支持），无透明通道 → 固态球类抠圆不可省
       - 固态球类(planet/dwarf_planet/moon/asteroid/comet)：生成「干净黑底正圆球」→ 裁圆规整为 r=210
         （2026-10-26 v2 算法：迭代 trim 圆心/半径 + 盘自身 mask 羽化作轮廓，
          杜绝旧版硬几何圆蒙版的「切盘/露缝」瑕疵；出图后自检轮廓，不合格自动回退程序化）
       - 大尺度(nebula/galaxy/cluster/structure)：生成「深空占位图」→ 全幅缩放+边缘渐隐
  3) 豆包不可用/失败 → 回退【程序化兜底】（gen_solid_body / gen_bigscale_image.py）
  4) 恒星：复用 build_star_images.py（按 subtype→9 类套 AI 模板，不走豆包单张生成）

约定（与全站贴图体系一致）：600×600，本体盘占画布 70%（r=210），边缘平滑，圆外全透明，无光晕。

用法：
  python scripts/sync_images.py            # 补齐所有未锁定贴图
  python scripts/sync_images.py --ids a,b  # 只处理指定 id
  python scripts/sync_images.py --force    # 强制重制（含已存在的非锁定图）
  python scripts/sync_images.py --no-gen-star   # 跳过恒星（恒星已齐，省时）
"""
import argparse
import base64
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASTRO = ROOT / "docs" / "data" / "astro.json"
PLANET_DIR = ROOT / "docs" / "assets" / "planets"
SIZE, R_BODY = 600, 210.0
PY = "C:/Users/99432/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

DOUBAO_BASE = "http://127.0.0.1:9090/v1"
# 豆包生图强制约束（复用恒星模板同款规则）：单圆/干净黑底/无轮廓外延
CIRCLE_RULE = (
    "严格要求：画面中只有一个光滑的几何圆形天体，圆盘外边界必须绝对平滑完整，"
    "天体直径约占整个画面的75%，精确位于画面正中央；"
    "禁止任何光晕外溢、辉光、不规则形状或延伸到圆形之外的物体，圆形之外必须是纯黑；"
    "不要文字、不要标签、不要水印、不要任何其他物体。"
)

SOLID_CATS = {"planet", "dwarf_planet", "moon", "asteroid", "comet"}
BIGSCALE_CATS = {"black_hole", "nebula", "galaxy", "cluster", "structure"}

# 固态天体兜底配色（RGB）：按类别给一个朴素但可信的球体色，避免千篇一律
SOLID_TINT = {
    "planet": (120, 160, 220),       # 偏蓝（类地/气态通用底）
    "dwarf_planet": (200, 180, 150),  # 偏暖灰（冥王星/谷神星系）
    "moon": (170, 170, 175),          # 灰白（卫星/月球）
    "asteroid": (150, 130, 110),      # 棕灰（岩石小天体）
    "comet": (180, 200, 210),         # 冷灰蓝（冰核）
}

# 豆包生图提示词的描述段（决定外观，黑底约束由 CIRCLE_RULE 统一追加）
SOLID_DESC = {
    "planet": "a realistic spherical planet with visible surface detail (continents, clouds, or banded atmosphere)",
    "dwarf_planet": "a realistic spherical dwarf planet with neutral icy grayish surface and faint craters",
    "moon": "a realistic spherical moon with gray cratered surface",
    "asteroid": "a roughly round rocky asteroid with crater texture",
    "comet": "a realistic icy comet nucleus with a faint tail glow",
}
BIG_DESC = {
    "nebula": "a colorful cosmic nebula with glowing gas clouds and scattered stars",
    "galaxy": "a spiral galaxy with bright core and faint spiral arms, scattered stars",
    "cluster": "a dense globular star cluster full of stars on black background",
    "structure": "a large-scale cosmic web / filament of galaxies on black background",
    "black_hole": "a black sphere representing an event horizon with a thin glowing accretion ring",
}


# ---------------------------------------------------------------- 工具
def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def body_alpha():
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    rr = np.sqrt((xx - SIZE / 2 + 0.5) ** 2 + (yy - SIZE / 2 + 0.5) ** 2)
    return 255.0 * smoothstep(216.0 - rr, -2.0, 6.0)


def set_image_meta(oid, source, credit):
    """回写 astro.json 的 image_source / image_credit（供 query.py 筛 + 网页说明）。"""
    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    for o in data["objects"]:
        if o["id"] == oid:
            o["image_source"] = source
            o["image_credit"] = credit
            break
    ASTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 豆包生图
def doubao_generate_image(prompt, timeout=180):
    """调豆包 doubao-image 生成一张图，返回下载到本地的临时路径；任何失败返回 None。"""
    body = {"model": "doubao-image", "prompt": prompt, "size": "1024x1024",
            "n": 1, "response_format": "url"}
    try:
        req = urllib.request.Request(
            DOUBAO_BASE + "/images/generations",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode())
        item = (resp.get("data") or [{}])[0]
        if item.get("url"):
            with urllib.request.urlopen(item["url"], timeout=timeout) as ir:
                data = ir.read()
        elif item.get("b64_json"):
            data = base64.b64decode(item["b64_json"])
        else:
            print("    [doubao] 返回无图像数据，回退程序化")
            return None
    except Exception as e:
        print(f"    [doubao] 调用/下载失败：{type(e).__name__}: {e} → 回退程序化兜底")
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=str(PLANET_DIR))
    tmp.write(data)
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------- 裁剪：固态圆
def _otsu(lum):
    """对 luminance 数组做 Otsu 二值化，返回分割阈值（把「亮盘」与「暗背景」分开）。"""
    hist, _ = np.histogram(lum, bins=256, range=(0, 256))
    total = lum.size
    sum_total = np.dot(np.arange(256), hist)
    sum_bg = 0.0
    w_bg = 0.0
    maxvar = 0.0
    thr = 127
    for t in range(256):
        w_bg += hist[t]
        if w_bg == 0:
            continue
        w_fg = total - w_bg
        if w_fg == 0:
            break
        sum_bg += t * hist[t]
        m_bg = sum_bg / w_bg
        m_fg = (sum_total - sum_bg) / w_fg
        var = w_bg * w_fg * (m_bg - m_fg) ** 2
        if var > maxvar:
            maxvar = var
            thr = t
    return thr


def _disk_estimate(xs, ys):
    """迭代 trim 估计圆盘的圆心与两轴半径（抗星点/辉光离群污染）。

    每轮：剔除距当前圆心 >1.15r 的离群亮像素 → 用剩余像素的
    bbox 中心作圆心（圆盘的 bbox 中心=圆心，比质心抗明暗偏斜）、
    面积法半径 sqrt(area/π) 与 bbox 平均半径取均值作新半径。
    收敛或 3 轮后，再按 trim 后像素的 bbox 给出两轴半径 (rx, ry)。
    返回 (cx, cy, rx, ry)；像素太少/盘不规整（椭圆度>15%）返回 None。
    """
    if len(xs) < 200:
        return None
    cx, cy = float(xs.mean()), float(ys.mean())
    r = float(np.percentile(np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2), 97)) or 1.0
    for _ in range(3):
        d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        keep = d <= 1.15 * r
        if int(keep.sum()) < 200:
            return None
        xk, yk = xs[keep], ys[keep]
        cx_n = (xk.min() + xk.max()) / 2.0
        cy_n = (yk.min() + yk.max()) / 2.0
        r_n = (float(np.sqrt(len(xk) / np.pi)) +
               float((xk.max() - xk.min() + yk.max() - yk.min() + 2) / 4.0)) / 2.0
        done = (abs(r_n - r) < 0.01 * r and
                abs(cx_n - cx) < 1.0 and abs(cy_n - cy) < 1.0)
        cx, cy, r = cx_n, cy_n, r_n
        if done:
            break
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    keep = d <= 1.15 * r
    if int(keep.sum()) < 200:
        return None
    xk, yk = xs[keep], ys[keep]
    rx = (xk.max() - xk.min() + 1) / 2.0
    ry = (yk.max() - yk.min() + 1) / 2.0
    if rx < 30 or ry < 30:
        return None
    if max(rx, ry) / min(rx, ry) > 1.15:      # 不是规整圆盘（污染/严重椭圆），交给兜底
        return None
    return cx, cy, rx, ry


def crop_to_circle(src_path, out_path, target_r=R_BODY):
    """把豆包生成的「行星图」规整为 600×600、盘半径≈210、圆外透明。

    豆包实测只输出 RGB（background:"transparent" 也不支持），抠圆不可省：
      1) Otsu 自适应分离亮盘与暗背景；
      2) 迭代 trim 估计圆心/半径（面积法+bbox，抗星点污染）；
      3) 各向微缩放归一：盘的 x/y 直径分别映射为 420（r=210）并居中
         （消除豆包「正圆」实测 ±6% 的椭圆度，形变不可见）；
      4) 轮廓 alpha 用【盘自身 mask 高斯羽化】——贴合内容边缘，
         机制上杜绝旧版硬几何圆蒙版的「切盘/露缝」瑕疵；
         另乘 r=216 渐隐几何圆兜底（guard），防极端溢出/远处星点。
    失败（检测不到规整圆盘）返回 False，由调用方回退程序化兜底。
    """
    im = Image.open(src_path).convert("RGBA")
    a = np.asarray(im).astype(np.float32)
    lum = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    mask = lum > _otsu(lum)
    ys, xs = np.where(mask)
    frac = len(xs) / (a.shape[0] * a.shape[1])
    if len(xs) < 200 or frac > 0.7:          # 阈值失效（整幅都亮）或没有盘
        return False
    est = _disk_estimate(xs, ys)
    if est is None:
        return False
    cx, cy, rx, ry = est
    if max(rx, ry) > 0.49 * min(a.shape[0], a.shape[1]):
        return False
    # 各向微缩放归一：盘的 x/y 直径分别映射为 420（r=210）。
    # 豆包「正圆」实测有 ±6% 左右椭圆度/不规则，旧版硬几何圆蒙版因此切盘/露缝；
    # 直接把两轴归一到标准圆（形变仅几个百分点，肉眼不可见），换取完美圆形轮廓。
    hx = rx * SIZE / (2 * target_r)
    hy = ry * SIZE / (2 * target_r)
    left, top = int(round(cx - hx)), int(round(cy - hy))
    sq = im.crop((left, top, left + int(round(2 * hx)), top + int(round(2 * hy))))
    sq = sq.resize((SIZE, SIZE), Image.LANCZOS)
    arr = np.asarray(sq).astype(np.float32)
    lum2 = arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114
    body = (lum2 > _otsu(lum2)).astype(np.uint8) * 255
    body = np.asarray(Image.fromarray(body, "L")
                      .filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    rr = np.sqrt((xx - SIZE / 2 + 0.5) ** 2 + (yy - SIZE / 2 + 0.5) ** 2)
    guard = 255.0 * smoothstep(216.0 - rr, -2.0, 6.0)   # r=222 外归零，兜底防溢出
    out = arr.copy()
    out[..., 3] = np.clip(body, 0, 255) * (guard / 255.0) * (arr[..., 3] / 255.0)
    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(out_path, "WEBP", quality=90)
    return True


def _silhouette_check(path, target_r=R_BODY):
    """自检：按角度扫描 alpha 轮廓半径，盘应规整地贴近 target_r。
    不合格（碎盘/污染/缩放异常）返回 False，调用方回退程序化。"""
    a = np.asarray(Image.open(path).convert("RGBA"))[..., 3].astype(np.float32)
    H, W = a.shape
    rs = np.zeros(360)
    for i, th in enumerate(np.linspace(0, 2 * np.pi, 360, endpoint=False)):
        rads = np.arange(0, int(SIZE * 0.55), 1.0)
        xs = np.clip((W / 2 - 0.5 + rads * np.cos(th)).astype(int), 0, W - 1)
        ys = np.clip((H / 2 - 0.5 + rads * np.sin(th)).astype(int), 0, H - 1)
        solid = np.where(a[ys, xs] > 128)[0]
        rs[i] = solid.max() if len(solid) else 0
    med = float(np.median(rs))
    return bool(rs.min() >= target_r - 20 and rs.max() <= target_r + 12
                and 200 <= med <= target_r + 8)


# ---------------------------------------------------------------- 裁剪：大尺度全幅
def frame_resize(src_path, out_path):
    """大尺度占位：整幅缩至最长边 600，四边渐隐，圆外透明。"""
    im = Image.open(src_path).convert("RGBA")
    w, h = im.size
    scale = 600.0 / max(w, h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    im = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(im, ((SIZE - nw) // 2, (SIZE - nh) // 2))
    arr = np.asarray(canvas).astype(np.float32)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    fx = np.minimum(xx, SIZE - 1 - xx) / (SIZE * 0.06)
    fy = np.minimum(yy, SIZE - 1 - yy) / (SIZE * 0.06)
    fade = np.clip(np.minimum(fx, fy), 0, 1)
    arr[..., 3] = arr[..., 3] * fade
    Image.fromarray(arr.astype(np.uint8), "RGBA").save(out_path, "WEBP", quality=90)
    return True


# ---------------------------------------------------------------- 程序化兜底
def gen_solid_body(oid, cat):
    """程序化固态球体兜底：带临边昏暗 + 左上高光的简单球面，圆外全透明，无光晕。"""
    rgba = body_alpha()
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    nx = (xx - SIZE / 2) / R_BODY
    ny = (yy - SIZE / 2) / R_BODY
    rr = np.sqrt(nx ** 2 + ny ** 2)
    inside = rr <= 1.0
    z = np.sqrt(np.clip(1.0 - rr ** 2, 0, 1))
    lx, ly, lz = -0.5, -0.5, 0.707
    diff = np.clip(-(nx * lx + ny * ly) + z * lz, 0, 1)
    base = np.array(SOLID_TINT.get(cat, (160, 160, 170)), dtype=np.float32)
    shade = np.clip(0.55 + 0.65 * diff, 0.35, 1.25)
    rgb = base[None, None, :] * shade[..., None]
    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = rgba.astype(np.uint8)
    out[~inside] = 0
    img = Image.fromarray(out, "RGBA")
    dst = PLANET_DIR / f"{oid}.webp"
    img.save(dst, "WEBP", quality=88)
    return dst


# ---------------------------------------------------------------- 豆包优先生成
def gen_solid_doubao(oid, cat, obj):
    """优先豆包 AI 生成固态球；成功返回 True，失败返回 False（交由程序化兜底）。"""
    name = obj.get("name") or obj.get("name_en") or oid
    desc = SOLID_DESC.get(cat, "a realistic spherical celestial body")
    prompt = (f"Photorealistic image of {desc} (this is {name}), fully illuminated, "
              f"perfect sphere centered, isolated on pure black background, "
              f"no stars, no glow, no ring, no text, no watermark. " + CIRCLE_RULE)
    tmp = doubao_generate_image(prompt)
    if not tmp:
        return False
    dst = PLANET_DIR / f"{oid}.webp"
    ok = crop_to_circle(tmp, dst)
    Path(tmp).unlink(missing_ok=True)
    if not ok:
        print("    [doubao] 裁圆检测失败（背景/圆盘不符），回退程序化")
        return False
    if not _silhouette_check(dst):
        dst.unlink(missing_ok=True)
        print("    [doubao] 轮廓自检不合格（盘不规整），回退程序化")
        return False
    set_image_meta(oid, "doubao", "AI 生成")
    return True


def gen_bigscale_doubao(oid, cat, obj):
    """优先豆包 AI 生成大尺度占位（全幅）；成功 True，失败 False。"""
    name = obj.get("name") or obj.get("name_en") or oid
    desc = BIG_DESC.get(cat, "a deep space astronomical object")
    prompt = (f"Astronomy photograph style image of {desc} (this is {name}), "
              f"on pure black background, high detail, no text, no watermark.")
    tmp = doubao_generate_image(prompt)
    if not tmp:
        return False
    dst = PLANET_DIR / f"{oid}.webp"
    ok = frame_resize(tmp, dst)
    Path(tmp).unlink(missing_ok=True)
    if not ok:
        return False
    set_image_meta(oid, "doubao", "AI 生成")
    return True


# ---------------------------------------------------------------- 路由
def gen_solid(oid, cat, obj):
    """优先豆包（不合格自动重试 1 次），仍失败回退程序化；返回来源标签。"""
    for attempt in range(2):
        if gen_solid_doubao(oid, cat, obj):
            return "doubao"
        if attempt == 0:
            print("    [doubao] 第 1 次出图不合格，再试一次（豆包随机波动较大）")
    gen_solid_body(oid, cat)
    set_image_meta(oid, "programmatic", "程序化示意图")
    return "programmatic"


def gen_bigscale(oid, cat, obj, force):
    """优先豆包占位，失败回退程序化（gen_bigscale_image.py）。黑洞恒程序化（无需 AI）。"""
    if cat != "black_hole" and gen_bigscale_doubao(oid, cat, obj):
        return "doubao"
    cmd = [PY, "scripts/gen_bigscale_image.py"] + (["--force"] if force else []) + ["--ids", oid]
    subprocess.run(cmd, cwd=str(ROOT), check=False)
    set_image_meta(oid, "programmatic", "程序化示意图")
    return "programmatic"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="", help="只处理这些 id（逗号分隔）")
    ap.add_argument("--force", action="store_true", help="强制重制已存在的非锁定图")
    ap.add_argument("--no-gen-star", action="store_true", help="跳过恒星（恒星已齐，省时）")
    args = ap.parse_args()

    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    objs = data["objects"]
    by_id = {o["id"]: o for o in objs}
    only = set(args.ids.split(",")) if args.ids else None

    stars, bigscale, solid = [], [], []
    for o in objs:
        oid, cat = o["id"], o["category"]
        if only and oid not in only:
            continue
        locked = o.get("image_locked")
        dst = PLANET_DIR / f"{oid}.webp"
        exists = dst.exists()
        if cat == "star" or oid == "sun":
            if args.no_gen_star:
                continue
            stars.append(oid)
        elif cat in BIGSCALE_CATS:
            if locked and exists:
                continue  # NASA 真图锁定，不覆盖
            bigscale.append(oid)
        elif cat in SOLID_CATS:
            if locked and exists:
                continue  # NASA 真图锁定，不覆盖
            if exists and not args.force:
                continue
            solid.append(oid)
        else:
            print(f"  [skip] {oid}: 类别 {cat} 无生成器")

    made = []          # (oid, source_label)
    if stars:
        print(f"恒星（{len(stars)} 颗）→ build_star_images.py ...")
        subprocess.run([PY, "scripts/build_star_images.py"], cwd=str(ROOT), check=False)
    if bigscale:
        print(f"大尺度（{len(bigscale)}）→ 优先豆包占位，失败回退程序化 ...")
        for oid in bigscale:
            lbl = gen_bigscale(oid, by_id[oid]["category"], by_id[oid], args.force)
            made.append((oid, lbl))
    for oid in solid:
        cat = by_id[oid]["category"]
        lbl = gen_solid(oid, cat, by_id[oid])
        made.append((oid, lbl))

    if made:
        print("本次出图（豆包优先 / 程序化兜底）：")
        for oid, lbl in made:
            tag = "豆包AI" if lbl == "doubao" else "程序化"
            print(f"  - {oid}: {tag}")
    else:
        print("本次无新出图（均已锁定或已存在）")
    print("sync_images 完成。恒星/大尺度由对应脚本输出，固态见上行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
