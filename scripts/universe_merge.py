#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
universe_merge.py — 把仓库 astro.json 的天体精确挂接到宇宙层级骨架，
产出融合数据源 universe-tree.json。

设计原则（用户硬约束）：
1. universe-data.json 是「宇宙层级」章节的层级事实源，其 _convention 字段定义命名与分类规范。
   骨架已为全部仓库天体建好精确节点；归属不靠猜，改 JSON 即改层级。
2. 名称严格对齐：name 与骨架节点**字节级精确一致**（大小写、空格都有语义），
   norm() 为恒等函数，不做 lower、不去空白、不去括号、不做星尾差异等模糊匹配。
   仅额外支持骨架显式声明的 alias 精确匹配。对不上就报错，改数据而不放宽匹配。
3. 归属严格：每个节点带受控 category；融合时校验
   (a) 节点 category 与仓库 category 一致；
   (b) 仓库 parent 链与骨架祖先链兼容。
   任一不一致都作为「归属冲突」输出，绝不静默塞进默认容器。
4. parent=None 的天体不按类别一刀切分配；骨架里已给出其精确位置，
   查不到位置的明确报错而不是臆测。
5. 写入前比对磁盘内容：无变化则跳过，避免 mkdocs serve 监听触发重建死循环。

用法：python scripts/universe_merge.py
"""
import json, os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "universe-data.json")
REPO = os.path.join(ROOT, "docs", "data", "astro.json")
OUT  = os.path.join(ROOT, "universe-tree.json")

CATS = {"宇宙结构", "星系", "星云", "恒星", "行星", "卫星", "星团",
        "矮行星", "小行星", "彗星", "黑洞", "其他"}

# 仓库 category(英文) -> 受控中文 category
TYPE_MAP = {
    "star": "恒星", "planet": "行星", "moon": "卫星",
    "galaxy": "星系", "nebula": "星云", "black_hole": "黑洞",
    "cluster": "星团", "dwarf_planet": "矮行星", "asteroid": "小行星",
    "comet": "彗星", "structure": "宇宙结构",
}


def norm(name):
    """字节级精确匹配：不做任何归一化。大小写与空白都有语义，
    防止靠容错掩盖 astro.json 与骨架之间的命名漂移。"""
    return name


base = json.load(open(BASE, encoding="utf-8"))
repo = json.load(open(REPO, encoding="utf-8"))
repo_objs = {o["id"]: o for o in repo["objects"]}

# ---------- 骨架索引（name 优先，alias 补充） ----------
by_name, by_alias, parents = {}, {}, {}
dupes = []

def walk(n, parent=None):
    if "name" not in n:
        return
    k = norm(n["name"])
    if k in by_name:
        dupes.append(k)
    else:
        by_name[k] = n
    parents[id(n)] = parent
    if n.get("category") not in CATS:
        raise SystemExit(f"骨架节点「{n['name']}」category 越界: {n.get('category')}")
    if n.get("alias"):
        by_alias.setdefault(norm(n["alias"]), n)
    for c in n.get("children", []):
        walk(c, n)

walk(base)
if dupes:
    raise SystemExit(f"骨架存在重复名称（归一化后）: {dupes}")

# ---------- 精确挂接 ----------
tagged, mismatches, unmatched = [], [], []

for o in repo["objects"]:
    k = norm(o["name"])
    target = by_name.get(k) or by_alias.get(k)
    if target is None:
        unmatched.append((o["id"], o["name"]))
        continue
    want = TYPE_MAP.get(o["category"])
    if want and target["category"] != want:
        mismatches.append((o["id"], o["name"], want, target["category"]))
    if not target.get("repo_id"):
        target["repo_id"] = o["id"]
    tagged.append((o["name"], target["name"]))

# ---------- 归属校验：仓库 parent 链 vs 骨架祖先链 ----------
# 仓库 parent 表示「物理母天体」（如行星绕太阳、卫星绕行星），
# 骨架则按「引力从属 / 包含关系」组织（如行星归入内/外行星系统分组）。
# 两者都是合法语义，因此判定为「容器兼容」：
#   (1) 母天体本身就是骨架祖先 —— 精确层级父；
#   (2) 母天体与子天体同属一个容器（母天体的父节点是子天体的祖先）—— 分组式层级。
# 若母天体落在完全无关的大类（如把类星体挂进银河系），两条都不成立，会被检出。
def ancestor_names(n):
    out = []
    p = parents.get(id(n))
    while p is not None:
        out.append(norm(p["name"]))
        p = parents.get(id(p))
    return out

def skeleton_node(rid):
    o = repo_objs.get(rid)
    return by_name.get(norm(o["name"])) if o else None

conflicts = []
for o in repo["objects"]:
    prid = o.get("parent")
    if not prid or prid not in repo_objs:
        continue
    child, parent = skeleton_node(o["id"]), skeleton_node(prid)
    if child is None or parent is None:
        continue
    chain = ancestor_names(child)
    exact = norm(parent["name"]) in chain
    pp = parents.get(id(parent))
    same_container = pp is not None and norm(pp["name"]) in chain
    if not (exact or same_container):
        conflicts.append((o["id"], o["name"], repo_objs[prid]["name"],
                          " > ".join(chain[:3]) or "（根节点下）"))

# ---------- 摘要 ----------
print("=" * 64)
print("【融合】astro.json 精确挂接 -> universe-tree.json")
print("=" * 64)
print(f"骨架节点: {len(by_name)}   仓库天体: {len(repo_objs)}   精确命中: {len(tagged)}")
print(f"category 类型不一致: {len(mismatches)}")
for m in mismatches:
    print(f"  ! {m[0]:20s} {m[1]:16s} 应为「{m[2]}」但骨架为「{m[3]}」")
print(f"归属冲突(parent 链与骨架不一致): {len(conflicts)}")
for c in conflicts:
    print(f"  ! {c[0]:20s} {c[1]:16s} 仓库父={c[2]:14s} 骨架祖先={c[3]}")
print(f"未匹配(骨架缺节点): {len(unmatched)}")
for u in unmatched:
    print(f"  ! {u[0]:20s} {u[1]}")
print("\n按 category 分布(骨架):", dict(Counter(
    n.get("category") for n in by_name.values())))

# ---------- 写出（写前比对防 serve 死循环） ----------
new_text = json.dumps(base, ensure_ascii=False, indent=2) + "\n"
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as f:
        if f.read() == new_text:
            print(f"\n融合数据源无变化，跳过写出: {os.path.relpath(OUT, ROOT)}")
            raise SystemExit(0)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(new_text)
print(f"\n已写出融合数据源: {os.path.relpath(OUT, ROOT)}")

if mismatches or conflicts or unmatched:
    print("\n[警告] 存在待修正的归属/类型问题，详见上方清单")
