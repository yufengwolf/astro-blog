# 恒星按光谱类型统一外观（2026-10-26 用户拍板）：每种类型一张豆包 AI 代表图，
# 同类型恒星共用同一外观，仅做个体色相微调（±12°，如黑洞先例——一个类型一个外观）。
# 太阳除外：保留独立处理（真实日面纹理，不做类型模板）。
# AI 源图缺失时由 build_star_images.py 降级为程序化着色（fallback 字段）。
import hashlib

# type_id → 展示标签 / 豆包生图提示词 / 程序化兜底基色 RGB
TYPE_DEFS = {
    "blue": {
        "label": "蓝（超）巨星（O/B/LBV/WR/食双星主星）",
        "prompt": "一张天文摄影风格的正方形图像：一颗炽热的蓝超巨星，呈现为一个完美的正圆形，"
                  "表面为明亮的冰蓝色，带细腻的高对比颗粒与斑驳纹理，像真实巨星光球。",
        "fallback": (158, 192, 255),
    },
    "white": {
        "label": "蓝白主序星（A 型）",
        "prompt": "一张天文摄影风格的正方形图像：一颗蓝白色主序星（如织女星），呈现为一个完美的正圆形，"
                  "表面为明亮的蓝白色，带细腻光斑与微弱对流纹理。",
        "fallback": (202, 222, 255),
    },
    "yellow_white": {
        "label": "黄白星（F 型）",
        "prompt": "一张天文摄影风格的正方形图像：一颗黄白色恒星（F 型），呈现为一个完美的正圆形，"
                  "表面为温暖的黄白色，带柔和的对流颗粒纹理。",
        "fallback": (255, 244, 220),
    },
    "yellow": {
        "label": "黄矮星（G 型，太阳除外）",
        "prompt": "一张天文摄影风格的正方形图像：一颗类太阳的黄矮星（G 型），呈现为一个完美的正圆形，"
                  "表面为温暖的金黄色，带明显的米粒组织与零星暗色星斑。",
        "fallback": (255, 236, 185),
    },
    "orange": {
        "label": "橙巨星 / 橙矮星（K 型）",
        "prompt": "一张天文摄影风格的正方形图像：一颗橙色巨星（K 型），呈现为一个完美的正圆形，"
                  "表面为温暖的橙色，带大尺度对流斑块与较暗的边缘（临边昏暗）。",
        "fallback": (255, 198, 140),
    },
    "red_giant": {
        "label": "红（超）巨星（M 型巨星）",
        "prompt": "一张天文摄影风格的正方形图像：一颗红超巨星（M 型），呈现为一个完美的正圆形，"
                  "表面为深橙红色，带巨大暗色对流斑块与脉动纹理，像参宿四或心宿二。",
        "fallback": (235, 118, 72),
    },
    "red_dwarf": {
        "label": "红矮星（M 型主序）",
        "prompt": "一张天文摄影风格的正方形图像：一颗红矮星（M 型主序星），呈现为一个完美的正圆形，"
                  "表面为暗红色，带细微而均匀的颗粒纹理。",
        "fallback": (255, 152, 98),
    },
    "white_dwarf": {
        "label": "白矮星",
        "prompt": "一张天文摄影风格的正方形图像：一颗白矮星，呈现为一个完美的正圆形，"
                  "表面为炽热的蓝白色，极高亮度、几乎无纹理、边缘锐利。",
        "fallback": (228, 238, 255),
    },
    "neutron": {
        "label": "中子星 / 脉冲星 / 磁星",
        "prompt": "一张天文摄影风格的正方形图像：一颗中子星，呈现为一个完美的正圆形，"
                  "表面为冷白色带蓝色调，极高亮度、边缘锐利、带细微的磁场纹理感。",
        "fallback": (205, 225, 255),
    },
}


def map_subtype(sub):
    """subtype 文本 → type_id。先查光谱字母+数字（如 F0Iab），再查特殊类别关键词。"""
    s = sub or ""
    if "白矮星" in s:
        return "white_dwarf"
    if "中子星" in s or "脉冲星" in s or "磁星" in s:
        return "neutron"
    for ch in ("O", "B", "A", "F", "G", "K", "M"):
        idx = s.find(ch)
        if idx >= 0 and idx + 1 < len(s) and s[idx + 1].isdigit():
            if ch == "M":
                giant = any(k in s for k in ("巨星", "超巨星", "特超巨星"))
                return "red_giant" if giant else "red_dwarf"
            if ch in ("B", "O"):
                return "blue"
            if ch == "A":
                return "white"
            if ch == "F":
                return "yellow_white"
            if ch == "G":
                return "yellow"
            if ch == "K":
                return "orange"
    if "沃尔夫-拉叶" in s or "WN" in s:
        return "blue"
    if "蓝变星" in s or "LBV" in s:
        return "blue"
    if "食" in s:  # 大陵五/天琴 β 均为 B 型蓝白主星
        return "blue"
    return "yellow"


def hue_offset(star_id):
    """个体色相微调：由 id 确定性生成 -12..+12 度（同类型内微妙区分，整体外观统一）。"""
    h = int(hashlib.md5(star_id.encode("utf-8")).hexdigest()[:8], 16)
    return h % 25 - 12


# 太阳独立底图（用户要求：一律用豆包接口生图，不用其他模型）
SUN_PROMPT = ("一张天文摄影风格的正方形图像：太阳，呈现为一个完美的正圆形，"
              "表面为明亮的橙黄色，带真实的米粒组织纹理和少量暗色太阳黑子。")
