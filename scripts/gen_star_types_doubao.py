# 按恒星类型生成代表图（豆包 OpenAI 兼容接口，model=doubao-image）
# 每个类型 1 张 → generated-images/type_<tid>.png；后续由 build_star_images.py
# 做居中切圆（70% 本体盘）+ 同型恒星共用 + 个体色相微调。
# 已存在的类型图默认跳过；--force 强制重新生成。
import base64
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from star_types import TYPE_DEFS, SUN_PROMPT

BASE = "http://127.0.0.1:9090/v1"
OUT = r"C:/Users/99432/code/WorkBuddy_workspace/generated-images"

CIRCLE_RULE = (
    "严格要求：画面中只有一个光滑的几何圆形圆盘，圆盘外边界必须绝对平滑完整，"
    "圆盘直径约占整个画面的75%，精确位于画面正中央；"
    "禁止任何火焰、日珥、耀斑、弧线、光晕外溢或任何延伸到圆形之外的不规则形状，圆形之外必须是纯黑；"
    "不要文字、不要标签、不要水印、不要任何其他物体。"
)


def gen(tid, prompt, force=False):
    path = os.path.join(OUT, "type_%s.png" % tid)
    if os.path.exists(path) and not force:
        print(tid, "exists, skip ->", path)
        return
    body = {
        "model": "doubao-image",
        "prompt": prompt + CIRCLE_RULE,
        "size": "1024x1024",
        "n": 1,
        "response_format": "url",
    }
    req = urllib.request.Request(
        BASE + "/images/generations",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read().decode())
    item = resp["data"][0]
    if item.get("b64_json"):
        with open(path, "wb") as f:
            f.write(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=180) as ir, open(path, "wb") as f:
            f.write(ir.read())
    else:
        raise ValueError("no image data: " + json.dumps(item)[:200])
    print(tid, "saved ->", path, os.path.getsize(path), "bytes")


if __name__ == "__main__":
    args = sys.argv[1:]
    force = "--force" in args
    if "--sun" in args:
        gen("sun", SUN_PROMPT, force)  # 太阳独立底图
        sys.exit(0)
    ids = [a for a in args if not a.startswith("--")] or list(TYPE_DEFS)
    for tid in ids:
        if tid not in TYPE_DEFS:
            raise SystemExit("unknown type id: " + tid)
        gen(tid, TYPE_DEFS[tid]["prompt"], force)
    print("done")
