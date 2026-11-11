#!/usr/bin/env python3
"""translate_fields.py — 把 astro.json 的中文自由文本字段译成英文（可复跑维护工具）。

产物：docs/data/i18n_fields.json（按 id + 字段索引，进 git，可人工审阅）
用法：
    python scripts/translate_fields.py              # 增量：只译缺失项
    python scripts/translate_fields.py --dry-run    # 仅列出待译条数，不调模型、不写盘
    python scripts/translate_fields.py --refresh    # 全量重译（忽略断点缓存）

依赖本地 LLM：优先豆包 http://127.0.0.1:9090/v1（并发快），失败回退 llama-server :8080。
断点缓存写入 scripts/.cache/i18n_fields_flat.json（已在 .gitignore），
最终结构化产物只在收尾写一次 —— 中途中断不会把 __flat__ 中间态写进正式数据文件。

数据契约：译稿 key 是 astro.json 里的「中文原文整串」，gen_pages.py 按 id + 字段
精确构造 i18n-data.js 的 fields 表。源中文一改动，整串匹配立即失效，
check_i18n_coverage.js 的漂移检测会报警，此时必须重跑本脚本。
"""
import argparse
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs/data/astro.json"
OUT = ROOT / "docs/data/i18n_fields.json"
CACHE = ROOT / "scripts/.cache/i18n_fields_flat.json"

DOUBAO = "http://127.0.0.1:9090/v1/chat/completions"
LOCAL = "http://127.0.0.1:8080/v1/chat/completions"
LOCAL_MODEL = "Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ3_M.gguf"

# tagline 已有 tagline_en，不再重复翻译
FIELDS = ["subtype", "note", "atmosphere", "spectral_type", "constellation",
          "image_credit", "members", "host_star"]

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true", help="只统计待译条数，不调模型、不写盘")
ap.add_argument("--refresh", action="store_true", help="忽略断点缓存，全量重译")
a = ap.parse_args()

d = json.loads(SRC.read_text(encoding="utf-8"))
by_id = {o["id"]: o for o in d["objects"]}
has_cn = lambda s: isinstance(s, str) and bool(re.search(r"[\u4e00-\u9fff]", s))

items, seen = [], set()
for o in d["objects"]:
    for f in FIELDS:
        v = o.get(f)
        if has_cn(v) and (f, v) not in seen:
            seen.add((f, v))
            items.append((f, v))
for s in d["meta"].get("primary_sources", []):
    if has_cn(s) and ("source", s) not in seen:
        seen.add(("source", s))
        items.append(("source", s))
pending = d["meta"].get("pending")
if has_cn(pending):
    items.append(("pending", pending))

print(f"待译去重文案 {len(items)} 条", flush=True)

SYS = ("You are a professional astronomy translator for a bilingual data website. "
       "Translate each Chinese string into concise, accurate English. "
       "Rules: keep all numbers, units, catalog IDs, Latin/Greek letters, URLs and "
       "bracketed machine annotations (e.g. 【AI复校 2026-10-27：填充:distance_ly】) "
       "intact — inside such annotations translate only the Chinese words. "
       "Use standard astronomical terms (constellation names -> standard English names; "
       "黄矮星 -> yellow dwarf; 光球层 -> photosphere). "
       "Do NOT add explanations. Output ONLY a JSON array of strings with exactly the "
       "same number of items in the same order. No markdown, no code fence.")


def chat(url, model, messages, timeout=90):
    payload = {"model": model, "messages": messages, "temperature": 0.15,
               "max_tokens": 2600}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer local"})
    r = json.load(urllib.request.urlopen(req, timeout=timeout))
    c = r["choices"][0]["message"]["content"]
    c = re.sub(r"^```(?:json)?\s*|\s*```$", "", c.strip())
    if "</think>" in c:
        c = c.split("</think>")[-1].strip()
    return json.loads(c)


def clean_arr(a, n):
    return (isinstance(a, list) and len(a) == n and
            all(isinstance(x, str) and x.strip() and not re.search(r"[\u4e00-\u9fff]", x)
                for x in a))


def translate_batch(batch):
    """batch: [(field, zh)] -> {中文原文: 英文译稿}"""
    prompt = ("Translate every string in this JSON array to English. "
              "Return a JSON array of the same length, same order.\n\n" +
              json.dumps([x[1] for x in batch], ensure_ascii=False))
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": prompt}]
    for url, model, tmo in ((DOUBAO, "doubao-2.1-turbo", 75),
                            (LOCAL, LOCAL_MODEL, 150)):
        try:
            a = chat(url, model, msgs, tmo)
            if clean_arr(a, len(batch)):
                return {zh: en.strip() for (_, zh), en in zip(batch, a)}
        except Exception as e:
            print(f"    {url.split(':')[-1][:4]} {type(e).__name__} {str(e)[:70]}", flush=True)
    # 整批失败：拆成单条兜底，避免一条坏数据拖垮整批
    out = {}
    for f, zh in batch:
        hint = ("constellation name -> standard English name" if f == "constellation" else
                "bibliographic citation, keep URL" if f == "source" else
                "short factual note about a celestial object")
        try:
            a = chat(DOUBAO, "doubao-2.1-turbo",
                     [{"role": "system", "content": SYS},
                      {"role": "user", "content": hint +
                       "\nReply with a JSON array containing exactly one English string:\n" +
                       json.dumps(zh, ensure_ascii=False)}], 45)
            if clean_arr(a, 1):
                out[zh] = a[0].strip()
        except Exception:
            pass
    return out


def load_cache():
    """断点缓存优先；没有缓存时从已提交的结构化译稿按 id + 字段反推，保证可重复运行。"""
    if a.refresh:
        return {}
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    flat = {}
    if not OUT.exists():
        return flat
    prev = json.loads(OUT.read_text(encoding="utf-8"))
    for oid, fmap in prev.get("objects", {}).items():
        src = by_id.get(oid, {})
        for f, en in fmap.items():
            zh = src.get(f)
            if isinstance(zh, str) and isinstance(en, str) and en:
                flat[zh] = en
    srcs = prev.get("meta", {}).get("primary_sources", [])
    for zh, en in zip(d["meta"].get("primary_sources", []), srcs):
        if isinstance(en, str) and en:
            flat[zh] = en
    pen = prev.get("meta", {}).get("pending")
    if pending and isinstance(pen, str) and pen:
        flat[pending] = pen
    return flat


cache = load_cache()
print(f"已有译稿 {len(cache)} 条", flush=True)
todo = [x for x in items if x[1] not in cache]
print(f"本轮需译 {len(todo)} 条", flush=True)
if a.dry_run:
    print("dry-run：不调模型、不写盘")
    raise SystemExit(0)

BATCH, WORKERS = 10, 5
batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
done_batches = 0
CACHE.parent.mkdir(parents=True, exist_ok=True)
with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    futs = {pool.submit(translate_batch, b): b for b in batches}
    for fu in as_completed(futs):
        try:
            got = fu.result()
        except Exception as e:
            print(f"    批次异常 {type(e).__name__} {str(e)[:70]}", flush=True)
            got = {}
        cache.update(got)
        done_batches += 1
        if done_batches % 5 == 0 or done_batches == len(batches):
            print(f"  {done_batches}/{len(batches)} 批  累计 "
                  f"{sum(1 for _, z in items if z in cache)}/{len(items)}", flush=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")

# 只在收尾写正式产物：即使上面崩了，OUT 仍是上一版完整结构化译稿
result = {"_meta": {"generator": "scripts/translate_fields.py",
                    "rule": "按 id + 字段关联；值为英文译稿，源文案改动需重新生成",
                    "fields": FIELDS},
          "objects": {}, "meta": {}}
missing = 0
for o in d["objects"]:
    en = {}
    for f in FIELDS:
        v = o.get(f)
        if has_cn(v):
            if v in cache:
                en[f] = cache[v]
            else:
                missing += 1
    if en:
        result["objects"][o["id"]] = en
srcs = [cache.get(s) for s in d["meta"].get("primary_sources", [])]
if any(srcs):
    result["meta"]["primary_sources"] = srcs
if pending and pending in cache:
    result["meta"]["pending"] = cache[pending]

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"完成：{len(result['objects'])} 个天体，缺失 {missing} 条，输出 {OUT}", flush=True)
