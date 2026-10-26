#!/usr/bin/env python3
"""sync_images.py — 通用图片编排（AI 编排层的出图入口）。

给定 astro.json，按 category 路由到对应生成器，保证每个对象都有贴图。

出图优先级（2026-10-26 用户拍板）：
  1) image_locked=True 的（NASA 真图手动锁定）→ 不动，绝不覆盖
  2) 否则优先用【豆包 AI 生成】（127.0.0.1:9090, model=doubao-image）
       - 豆包实测只输出 RGB（background:"transparent" 也不支持），无透明通道 → 固态球类抠圆不可省
       - 固态球类(planet/dwarf_planet/moon/asteroid/comet)：生成「干净黑底居中正圆球」→ 以球体中心切几何正圆规整为 r=210
         （2026-10-26 默认裁法：提示词已约束正方形+球体居中，故默认中心切、不做迭代 trim/椭圆归一；
          出图后自检轮廓，不合格自动回退程序化）；不规则真实天体走 nasa_image 的 irregular 轮廓模式
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
def doubao_generate_image(prompt, timeout=300):
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
def _bg_level(lum):
    """背景亮度估计：四角 10% 区域中位数（豆包水印固定在右下一角，中位数稳健）。"""
    H, W = lum.shape
    k = max(8, min(H, W) // 10)
    corners = np.concatenate([lum[:k, :k].ravel(), lum[:k, -k:].ravel(),
                              lum[-k:, :k].ravel(), lum[-k:, -k:].ravel()])
    return float(np.median(corners))


def _ray_circle_fit(lum, n_rays=360, r_min_frac=0.12, r_max_frac=0.46):
    """从图心向外射 n_rays 条射线，沿每条找【最外侧陡峭负梯度】作为球缘点，
    以边缘点到图心的距离的稳健统计给出球半径 R，返回 (R, n_used)。

    【圆心 = 图心】是设计决策而非偷懒：提示词合同保证「球体居中」，豆包实测
    也确实基本居中（智神星图真球心距图心仅 ~2%）；而暗面与背景亮度无法区分
    （智神星实测：背景 4~7、球暗面 12~27），边缘点只能覆盖亮侧约半圈弧段，
    对这段弧做自由圆拟合存在经典的部分圆弧退化（半径换圆心沿弧平分线滑动，
    实测拟出 R=602/球心偏 8% 的错误圆），不可用。故圆心信图心，射线只用于：
      a) 估计半径 R（边缘点到图心距离的中位数，对弧段覆盖不全稳健）；
      b) 验证图上确实存在一个边缘一致的球（点数/离散度门槛），否则回退。

    为什么用「陡峭负梯度」而非「亮过再落入背景」：亮侧球缘外常有【辉光】
    （缓变、可延伸数十~上百 px），「落入背景」会落到辉光尽头，把边缘点推到
    球外。真实临边是【锐利过渡】，故以「8px 窗口负梯度超过陡降阈值 + 内侧
    显著亮于外侧」判定球缘；从外向内取第一条陡降，球内纹理在其内侧不会被
    误取。暗面缓变无陡降 → 该侧无边缘点、被自然跳过。
    边缘点太少 / 离散度过大（不是居中球）返回 None。
    """
    H, W = lum.shape
    bg = _bg_level(lum)
    hi = float(np.percentile(lum, 99.5))
    g_thresh = -max(8.0, 0.10 * (hi - bg))          # 陡降阈值（8px 窗口）
    d_thresh = max(10.0, 0.15 * (hi - bg))          # 内侧须比外侧亮至少这么多
    r_min, r_max = r_min_frac * min(W, H), r_max_frac * min(W, H)
    half = 4                                        # 梯度半窗
    ds = []                                         # 边缘点到图心的距离
    for th in np.linspace(0, 2 * np.pi, n_rays, endpoint=False):
        ux, uy = float(np.cos(th)), float(np.sin(th))
        rs = np.arange(r_min, r_max, 1.0)
        xs = np.clip(np.round(W / 2 - 0.5 + rs * ux).astype(int), 0, W - 1)
        ys = np.clip(np.round(H / 2 - 0.5 + rs * uy).astype(int), 0, H - 1)
        vals = lum[ys, xs]
        if len(vals) < 4 * half + 2:
            continue
        edge = None
        # 从外向内扫：第一条满足「陡降 + 内亮外暗」的位置即球缘
        for i in range(len(vals) - 1, 2 * half, -1):
            g = vals[i] - vals[i - 2 * half]
            if g > g_thresh:
                continue
            inner = vals[max(0, i - 2 * half):i - half].mean()
            outer = vals[i + half:i + 2 * half].mean()
            if inner - outer > d_thresh:
                edge = i - half
                break
        if edge is not None:
            ds.append(float(rs[edge]))
    if len(ds) < 50:                                # 边缘点太少（球太暗/太怪）
        return None
    d = np.asarray(ds)
    med = float(np.median(d))
    # 一轮离群剔除（水印残边/偶发噪点），再检验离散度：真实居中球的
    # 边缘距离应集中在 ±6% 内（覆盖弧段上 c·u 投影的变化远小于此）
    keep = np.abs(d - med) <= 0.06 * med
    if int(keep.sum()) < 50:
        return None
    d = d[keep]
    med = float(np.median(d))
    if float(np.abs(d - med).max()) > 0.10 * med:   # 离散度过大：非居中规整球
        return None
    return med, int(len(d))


def crop_to_circle(src_path, out_path, target_r=R_BODY):
    """AI 球体默认裁圆：图心为球心（提示词合同）+ 射线陡降临边估半径，切几何正圆。

    这是固态球类（planet/dwarf_planet/moon/asteroid/comet）豆包图的【默认】裁法。
    提示词已约束「正方形 + 球体居中」，圆心直接取图心；半径用 _ray_circle_fit
    （陡降临边点到图心距离的中位数，对强明暗/辉光/水印免疫，智神星实例）：
      1) 抑噪平滑；置零右下角固定水印区（「豆包AI生成」，位置固定）；
      2) 从图心射 360 条射线找陡降边缘点 → 中位数距离为半径 R；
      3) 裁以图心为中心的 2R 方块 → 缩放到 420（r=210）→ 贴入 600 画布中心；
      4) 几何正圆 alpha（抗锯齿）输出，盘内纹理保留，圆外全透明，必过自检。
    失败（无边缘点/边缘离散度过大/半径越界）返回 False，由调用方回退
    程序化兜底。不规则真实天体（小行星/彗星土豆形）不走此函数，
    走 nasa_image 的 irregular 轮廓模式。
    """
    im = Image.open(src_path).convert("RGBA")
    W, H = im.size
    m = min(W, H)
    # 轻度平滑抑 JPEG 噪声，让背景噪声梯度远低于陡降阈值
    blur_r = max(2.0, m / 400.0)
    g_im = im.convert("L").filter(ImageFilter.GaussianBlur(blur_r))
    lum_s = np.asarray(g_im).astype(np.float32)
    # 豆包水印固定在右下角：预先置零，防止其锐利文字边缘被当成球缘
    wm = lum_s[int(H * 0.92):, int(W * 0.70):]
    wm[:] = 0.0
    fit = _ray_circle_fit(lum_s)
    if fit is None:
        return False
    R, n_used = fit
    if not (0.15 * m <= R <= 0.42 * m):             # 盘太小/太大都异常（太大可能伸入水印区）
        return False
    # 以图心为球心裁 2R 方块 → 缩放到 420（r=210）→ 贴上 600 画布中心
    cx, cy = W / 2.0, H / 2.0
    left = int(round(cx - R))
    top = int(round(cy - R))
    side = int(round(2 * R))
    sq = im.crop((left, top, left + side, top + side)).resize(
        (int(2 * target_r), int(2 * target_r)), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(sq, (int(SIZE / 2 - target_r), int(SIZE / 2 - target_r)))
    arr = np.asarray(canvas).astype(np.float32)
    # 几何正圆 alpha（抗锯齿边 ~4px），强制干净圆形轮廓，必过自检
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    r2 = np.sqrt((xx - SIZE / 2 + 0.5) ** 2 + (yy - SIZE / 2 + 0.5) ** 2)
    alpha = 255.0 * smoothstep(target_r + 2.0 - r2, -2.0, 4.0)
    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(arr[..., :3], 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    out[alpha < 1, :3] = 0
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
def gen_solid(oid, cat, obj, max_attempts=2):
    """优先豆包（不合格最多重试 max_attempts-1 次），仍失败回退程序化；返回来源标签。
    max_attempts=2 =「初始 1 次 + 重试 1 次」（默认，与原行为一致）；
    AI 重生成命令可传更大值（如 4 = 重试 3 次）。"""
    for attempt in range(max_attempts):
        if gen_solid_doubao(oid, cat, obj):
            return "doubao"
        if attempt < max_attempts - 1:
            print(f"    [doubao] 第 {attempt+1} 次出图不合格/失败，再试一次"
                  f"（豆包随机波动较大 / 网络问题）")
    gen_solid_body(oid, cat)
    set_image_meta(oid, "programmatic", "程序化示意图")
    return "programmatic"


def gen_bigscale(oid, cat, obj, force, max_attempts=2):
    """优先豆包占位，失败最多重试 max_attempts-1 次，仍失败回退程序化。黑洞恒程序化。"""
    if cat != "black_hole":
        for attempt in range(max_attempts):
            if gen_bigscale_doubao(oid, cat, obj):
                return "doubao"
            if attempt < max_attempts - 1:
                print(f"    [doubao] 大尺度第 {attempt+1} 次出图失败，再试一次"
                      f"（网络问题 / 豆包随机波动）")
    cmd = [PY, "scripts/gen_bigscale_image.py"] + (["--force"] if force else []) + ["--ids", oid]
    subprocess.run(cmd, cwd=str(ROOT), check=False)
    set_image_meta(oid, "programmatic", "程序化示意图")
    return "programmatic"


# ---------------------------------------------------------------- AI 重生成入口
def regenerate_ai(oid, max_attempts=4, force=True):
    """重新生成某对象的 AI 图（手动重试入口，供 nasa_image.py ai 子命令调用）。

    豆包优先，最多 max_attempts 次尝试（含重试）；全失败回退程序化。
      - image_locked 的 NASA 真图：不覆盖，返回 ("locked", 说明)
      - 恒星 / sun：走 build_star_images 模板重建（不走豆包单张）
      - 大尺度 / 固态：分别走 gen_bigscale / gen_solid（带重试）
    返回 (source_label, note)。
    """
    data = json.loads(ASTRO.read_text(encoding="utf-8"))
    hit = [o for o in data["objects"] if o["id"] == oid]
    if not hit:
        return None, "未收录"
    o = hit[0]
    if o.get("image_locked") and o.get("image_source") == "nasa":
        return "locked", "NASA 真图已锁定，不覆盖（如需替换请先改 image_locked=false）"
    cat = o["category"]
    if cat in ("star", "sun"):
        subprocess.run([PY, "scripts/build_star_images.py"], cwd=str(ROOT), check=False)
        set_image_meta(oid, "doubao_template", "AI 生成")
        return "doubao_template", "恒星模板重建"
    if cat in BIGSCALE_CATS:
        lbl = gen_bigscale(oid, cat, o, force, max_attempts=max_attempts)
        return lbl, "大尺度 AI/程序化"
    if cat in SOLID_CATS:
        lbl = gen_solid(oid, cat, o, max_attempts=max_attempts)
        return lbl, "固态 AI/程序化"
    return None, f"类别 {cat} 无生成器"


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
