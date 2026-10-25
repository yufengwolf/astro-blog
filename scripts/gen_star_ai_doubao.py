import base64, json, os, sys, urllib.request

BASE = "http://127.0.0.1:9090/v1"
OUT = "C:/Users/99432/code/WorkBuddy_workspace/generated-images"

CIRCLE_RULE = (
    "严格要求：画面中只有一个光滑的几何圆形圆盘，圆盘外边界必须绝对平滑完整，"
    "圆盘直径约占整个画面的75%，精确位于画面正中央；"
    "禁止任何火焰、日珥、耀斑、弧线、光晕外溢或任何延伸到圆形之外的不规则形状，圆形之外必须是纯黑；"
    "不要文字、不要标签、不要水印、不要任何其他物体。"
)

STARS = {
    "betelgeuse": "一张天文摄影风格的正方形图像：红超巨星参宿四，呈现为一个完美的正圆形，"
                  "表面为温暖的橙红色，带细微暗色斑驳纹理，像真实巨星光球。",
    "vega": "一张天文摄影风格的正方形图像：蓝白色主序星织女星，呈现为一个完美的正圆形，"
            "表面为明亮的白蓝色，带细腻光斑纹理。",
    "rigel": "一张天文摄影风格的正方形图像：蓝超巨星参宿七，呈现为一个完美的正圆形，"
             "表面为明亮的冰蓝色，带细腻颗粒感纹理。",
}


def gen(sid, prompt):
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
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read().decode())
    print(json.dumps(resp, ensure_ascii=False)[:400])
    item = resp["data"][0]
    out_path = os.path.join(OUT, "doubao_%s.png" % sid)
    if item.get("b64_json"):
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=120) as ir, open(out_path, "wb") as f:
            f.write(ir.read())
    else:
        raise ValueError("no image data in response: " + json.dumps(item)[:200])
    print(sid, "saved ->", out_path, os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    for sid in (sys.argv[1:] or ["betelgeuse"]):
        gen(sid, STARS[sid])
