#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
universe_merge.py — 把仓库 astro.json 中"缺失且能明确归属"的天体并入
外部提供的 universe-data.json 层级树，产出融合后的完整数据源 universe-tree.json。

设计原则（用户硬约束：层级/所属必须严格，天体自身数据准确性次要）：
1. universe-data.json 的层级为权威骨架，不重构、不挪动既有节点（仅追加）。
2. 仓库 astro.json 的**全部 178 个天体**都接入：按各对象的 parent 关系沿仓库父链
   找到树上已有节点挂接；仓库 parent=None 的天体按类别归入合适的宇宙结构节点
   （恒星→猎户臂、星云/银河星团→银盘、星系→拉尼亚凯亚、黑洞→拉尼亚凯亚、
    星团→银河系、矮行星/小行星/彗星→太阳系统/柯伊伯带、结构→可观测宇宙）。
3. 名称匹配做健壮归一化：小写 + 去全部空白（含全角）+ 去括号；并额外支持
   「星」尾差异（"天狼星A" 与 "天狼星 A"、"天狼 B" 与 "天狼星B" 视为同一天体），
   避免重复节点、保证详情卡片链接 (repo_id) 正确命中。
4. 同名（归一化后）不重复追加；孤儿天体仍可按类别归入，不再整棵跳过。

用法：python scripts/universe_merge.py
"""
import json, re, copy, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "universe-data.json")
REPO = os.path.join(ROOT, "docs", "data", "astro.json")
OUT  = os.path.join(ROOT, "universe-tree.json")

def norm(name):
    """小写 + 去括号内容 + 去全部空白（含全角），用于健壮同名判定。"""
    n = re.split(r"[（(]", name)[0]
    n = n.strip().lower()
    n = re.sub(r"\s+", "", n)
    n = n.replace("　", "")
    return n

def norm_star(name):
    """在 norm 基础上，去掉「星 + 字母/数字后缀」这类内部差异，用于
    "天狼星B"(天狼星+b) 与 "天狼 B"(天狼+b) 视作同一天体；
    不影响"疏散星团"等词（其"星"后接的是汉字，不去掉）。"""
    k = norm(name)
    k = re.sub(r"星(?=[a-z0-9])", "", k)
    return k

# ---------- 读入 ----------
base = json.load(open(BASE, encoding="utf-8"))
repo = json.load(open(REPO, encoding="utf-8"))
repo_objs = {o["id"]: o for o in repo["objects"]}

# ---------- 审计：索引 + 统计 ----------
index = {}          # norm_name -> 节点（首次出现）
dupes = []
depths = {}
branch_leaves = {}

def walk(n, path, depth):
    key = norm(n["name"])
    if key in index:
        dupes.append((key, " > ".join(path)))
    else:
        index[key] = n
    depths[key] = depth
    for c in n.get("children", []):
        walk(c, path + [n["name"]], depth + 1)

walk(base, [], 0)

root = base
for child in root.get("children", []):
    name = child["name"]
    cnt = sum(1 for _ in child.get("children", []))
    branch_leaves[name] = cnt

total = len(index)
maxdepth = max(depths.values())

print("=" * 60)
print("【审计】universe-data.json 结构统计")
print("=" * 60)
print(f"骨架节点总数(去重后): {total}")
print(f"最大层级深度(根=0): {maxdepth}")
print(f"重复归一化名: {dupes if dupes else '无'}")
print("\n可观测宇宙直接子分支(展开度):")
for k, v in branch_leaves.items():
    print(f"  - {k}: 直接子节点 {v} 个"
          + ("  [几乎为空，仅叶子]" if v <= 1 else ""))

# ---------- 名称索引（含去星尾） ----------
tree_index = {}
tree_index_star = {}
def index_node(n):
    tree_index.setdefault(norm(n["name"]), n)
    tree_index_star.setdefault(norm_star(n["name"]), n)
    for c in n.get("children", []):
        index_node(c)
index_node(base)

TYPE_MAP = {
    "star": "恒星", "planet": "行星", "moon": "天然卫星",
    "galaxy": "星系", "nebula": "星云", "black_hole": "黑洞",
    "cluster": "星团", "dwarf_planet": "矮行星", "asteroid": "小行星",
    "comet": "彗星", "structure": "宇宙结构",
}
# parent=None 的仓库天体按类别归入的骨架节点
CATEGORY_DEFAULT = {
    "star": "猎户臂（本地臂）", "nebula": "银盘", "galaxy": "拉尼亚凯亚超星系团",
    "black_hole": "拉尼亚凯亚超星系团", "cluster": "银河系", "dwarf_planet": "柯伊伯带",
    "asteroid": "太阳系统", "comet": "太阳系统", "structure": "可观测宇宙",
    "planet": "太阳系统", "moon": "太阳系统",
}
# 仓库 parent id -> 期望挂接的骨架节点（修正 milky_way→银盘 等）
PARENT_OVERRIDE = {
    "milky_way": "银盘", "local_group": "本星系群",
    "virgo_cluster": "室女座星系团", "laniakea": "拉尼亚凯亚超星系团",
}

placed_ids = set()
placed_cache = {}
created, tagged, fuzzy, defaulted = [], [], [], []

def resolve_tree_parent(name):
    k = norm(name)
    if k in tree_index:
        return tree_index[k]
    ks = norm_star(name)
    if ks in tree_index_star:
        return tree_index_star[ks]
    return None

def default_parent_node(cat):
    tgt = CATEGORY_DEFAULT.get(cat, "可观测宇宙")
    node = resolve_tree_parent(tgt)
    return node or tree_index.get(norm("可观测宇宙")) or base

def ensure_in_tree(rid, visiting=None):
    if rid in placed_ids:
        return placed_cache.get(rid)
    po = repo_objs.get(rid)
    if po is None:
        return None
    visiting = visiting or set()
    if rid in visiting:
        return None
    visiting.add(rid)

    # 特判：仓库的 sun 在骨架里没有独立节点（骨架用"太阳系统"承载），
    # 把 sun 直接对应到"太阳系统"，避免凭空生成空节点 / 把太阳系错挂到猎户臂。
    if rid == "sun":
        node = resolve_tree_parent("太阳系统")
        if node is not None:
            if "repo_id" not in node:
                node["repo_id"] = "sun"
                tagged.append(("太阳(sun)", node["name"]))
            placed_ids.add(rid); placed_cache[rid] = node
            return node

    # 1) 自身已存在于树（健壮/去星匹配）→ 仅补 repo_id，不新建
    ke = norm(po["name"]); ks = norm_star(po["name"])
    existing = tree_index.get(ke) or tree_index_star.get(ks)
    if existing is not None:
        if "repo_id" not in existing:
            existing["repo_id"] = rid
            (tagged if ke in tree_index else fuzzy).append((po["name"], existing["name"]))
        placed_ids.add(rid); placed_cache[rid] = existing
        return existing

    # 2) 解析父节点
    prid = po.get("parent")
    parent_node = None
    if prid:
        if prid in PARENT_OVERRIDE:
            parent_node = resolve_tree_parent(PARENT_OVERRIDE[prid])
        if parent_node is None and prid in repo_objs:
            parent_node = ensure_in_tree(prid, visiting)
        if parent_node is None:
            parent_node = resolve_tree_parent(prid) if prid in repo_objs else None
    if parent_node is None:
        parent_node = default_parent_node(po.get("category"))
        defaulted.append((po["name"], parent_node["name"], po.get("category")))

    # 3) 父节点下去重创建
    t = TYPE_MAP.get(po.get("category"), po.get("subtype") or po.get("category"))
    newnode = {"name": po["name"], "type": t}
    tag = po.get("tagline")
    if tag:
        newnode["info"] = tag
    newnode["repo_id"] = rid
    for c in parent_node.get("children", []):
        if norm(c["name"]) == ke or norm_star(c["name"]) == ks:
            if "repo_id" not in c:
                c["repo_id"] = rid
                (tagged if norm(c["name"]) == ke else fuzzy).append((po["name"], c["name"]))
            placed_ids.add(rid); placed_cache[rid] = c
            return c
    parent_node.setdefault("children", []).append(newnode)
    index_node(newnode)
    created.append((po["name"], parent_node["name"], t))
    placed_ids.add(rid); placed_cache[rid] = newnode
    return newnode

for o in repo["objects"]:
    ensure_in_tree(o["id"])

print("\n" + "=" * 60)
print("【融合】astro.json(全部) -> universe-tree.json")
print("=" * 60)
print(f"库内天体总数(astro.json): {len(repo_objs)}")
print(f"命中已有节点(补 repo_id): {len(tagged)}")
print(f"去星尾模糊命中(避免重复): {len(fuzzy)}")
for nm, tn in fuzzy:
    print(f"  ~ {nm}  ->  命中「{tn}」(星尾差异)")
print(f"新建节点: {len(created)}")
for nm, par, tp in created:
    print(f"  + {nm}  [{tp}]  -> 挂到「{par}」")
print(f"按类别默认归入(仓库 parent=None): {len(defaulted)}")
from collections import Counter
dc = Counter(d[2] for d in defaulted)
for cat, c in dc.items():
    print(f"  · {cat}: {c} 个")
print(f"未归类(仓库中找不到且类别无默认): {sum(1 for o in repo['objects'] if o['id'] not in placed_ids)}")

# 写出融合结果（写入前比对：内容无变化则跳过，避免 mkdocs serve 监听触发重建死循环）
new_text = json.dumps(base, ensure_ascii=False, indent=2)
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as f:
        if f.read() == new_text:
            print(f"\n融合数据源无变化，跳过写出: {os.path.relpath(OUT, ROOT)}  (节点去重后 {len(index)})")
            raise SystemExit(0)
open(OUT, "w", encoding="utf-8").write(new_text)
print(f"\n已写出融合数据源: {os.path.relpath(OUT, ROOT)}  (节点去重后 {len(index)})")
