#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
query_doubao.py — 通过本地豆包 OpenAI 兼容端点查询天体物理数据。

用途：批量补全卡片时，向豆包请求权威天体属性（质量/半径/距离/光谱型/光度/温度等）。
原则：只取数据，不直接写库；结果由调用方人工/脚本校验后落地（准确性优先）。

用法：
  echo "<prompt>" | python scripts/query_doubao.py
  python scripts/query_doubao.py "请给出老人星 Canopus 的 ..."
可选环境变量：
  DOUBAO_URL  默认 http://127.0.0.1:9090/v1/chat/completions
  DOUBAO_MODEL 默认 doubao-2.1
"""
import os, sys, json, urllib.request

URL = os.environ.get("DOUBAO_URL", "http://127.0.0.1:9090/v1/chat/completions")
MODEL = os.environ.get("DOUBAO_MODEL", "doubao-2.1")


def query(prompt, temperature=0.2, timeout=60):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]


def main():
    if not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    else:
        prompt = " ".join(sys.argv[1:])
    if not prompt:
        print("用法: echo '<prompt>' | python scripts/query_doubao.py", file=sys.stderr)
        sys.exit(2)
    print(query(prompt))


if __name__ == "__main__":
    main()
