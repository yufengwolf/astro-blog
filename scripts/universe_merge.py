#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
universe_merge.py — 把仓库 astro.json 中"缺失且能明确归属"的天体并入
外部提供的 universe-data.json 层级树，产出融合后的完整数据源 universe-tree.json。

设计原则（用户硬约束：层级/所属必须严格，天体自身数据准确性次要）：
1. universe-data.json 的层级为权威骨架，不重构、不挪动既有节点。
2. 仅追加 astro.json 中存在、但树中缺失、且能明确映射到某个树节点的天体。
3. 每个追加项的目标父节点由 astro.json 的 parent 关系推导，人工校订到
   最贴合的现有树节点（如银河系的星云并入"银盘"、疏散星团并入"疏散星团集合"、
   TNO 矮行星并入"柯伊伯带"），保证所属正确。
4. 同名（归一化后）不重复追加。

用法：python scripts/universe_merge.py
"""
import json, re, copy, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "universe-data.json")
REPO = os.path.join(ROOT, "docs", "data", "astro.json")
OUT  = os.path.join(ROOT, "universe-tree.json")

def norm(name):
    """取（前的中文/ASCII 名，去括号，去空格）做归一并去重判定。"""
    n = re.split(r"[（(]", name)[0]
    return n.strip()

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

# 可观测宇宙各直接子分支的"展开度"
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
print(f"节点总数(去重后): {total}")
print(f"最大层级深度(根=0): {maxdepth}")
print(f"重复归一化名: {dupes if dupes else '无'}")
print("\n可观测宇宙直接子分支(展开度):")
for k, v in branch_leaves.items():
    print(f"  - {k}: 直接子节点 {v} 个"
          + ("  [几乎为空，仅叶子]" if v <= 1 else ""))

# ---------- 融合映射 ----------
TYPE_MAP = {
    "star": "恒星", "planet": "行星", "moon": "天然卫星",
    "galaxy": "星系", "nebula": "星云", "black_hole": "黑洞",
    "cluster": "星团", "dwarf_planet": "矮行星", "asteroid": "小行星",
    "comet": "彗星", "structure": "宇宙结构",
}

# 需要追加的 repo 天体 -> 目标父节点(树的现有节点名)
# 仅列"缺失且能明确归属"的项；target 必须是树中已存在的节点名。
ADDITIONS = [
    ("m17",            "银盘"),          # 天鹅星云
    ("ngc3372",        "银盘"),          # 船底座星云
    ("ngc7000",        "银盘"),          # 北美洲星云
    ("hyades",         "疏散星团集合"),   # 毕星团
    ("m44",            "疏散星团集合"),   # 蜂巢星团
    ("m11",            "疏散星团集合"),   # 野鸭星团
    ("m7",             "疏散星团集合"),   # 托勒密星团
    ("halley",         "太阳系统"),       # 哈雷彗星
    ("gonggong_225088","柯伊伯带"),       # 共工星
    ("quaoar",         "柯伊伯带"),       # 创神星
    ("sedna",          "柯伊伯带"),       # 赛德娜
    ("hyperion",       "土星"),           # 土卫七
    ("tarantula",      "大麦哲伦云"),     # 蜘蛛星云(+其下 R136→R136a1 链)
    ("great_attractor","拉尼亚凯亚超星系团"),  # 巨引源
    ("cmb",            "可观测宇宙"),     # 宇宙微波背景
]

# repo 中已被树覆盖(或无法明确归属)而跳过的 id（用于报告）
SKIP_IDS = {
    "ic1101", "ic1101_bh",  # 孤儿巨星系，无干净父节点（不在拉尼亚凯亚内）
    # 以下在树中已存在同名节点，靠下方"已存在"检测跳过，无需列此
}

def find_node(name):
    return index.get(norm(name))

added, skipped_exist, skipped_no_target, skipped_unknown = [], [], [], []
placed_ids = set()

def build_node(o):
    """由 repo 对象构造树节点。"""
    t = TYPE_MAP.get(o.get("category"), o.get("subtype") or o.get("category"))
    node = {"name": o["name"], "type": t}
    tag = o.get("tagline")
    if tag:
        node["info"] = tag
    return node

def attach_chain(repo_id, target_node, depth_limit=4):
    """把 repo 对象及其全部后代递归挂到 target_node 下（用于蜘蛛星云链）。"""
    if repo_id in placed_ids:
        return
    o = repo_objs[repo_id]
    # 避免重复
    for c in target_node.get("children", []):
        if norm(c["name"]) == norm(o["name"]):
            # 已存在：仍尝试挂它的后代到该已存在节点
            existing = c
            placed_ids.add(repo_id)
            for kid in repo["objects"]:
                if kid.get("parent") == repo_id:
                    attach_chain(kid["id"], existing)
            return
    node = build_node(o)
    kids = [k for k in repo["objects"] if k.get("parent") == repo_id]
    if kids:
        node["children"] = []
        for kid in kids:
            attach_chain(kid["id"], node)
    target_node.setdefault("children", []).append(node)
    placed_ids.add(repo_id)
    added.append((o["name"], target_node.get("name") or "根", node["type"]))

# 普通叶子/已知目标追加
for rid, target_name in ADDITIONS:
    if rid in placed_ids:
        continue
    if rid not in repo_objs:
        skipped_unknown.append(rid)
        continue
    tgt = find_node(target_name)
    if not tgt:
        skipped_no_target.append((rid, target_name))
        continue
    o = repo_objs[rid]
    # 同名检测
    exists = any(norm(c["name"]) == norm(o["name"]) for c in tgt.get("children", []))
    if exists:
        skipped_exist.append((o["name"], target_name))
        placed_ids.add(rid)
        continue
    # 蜘蛛星云需要递归挂后代
    if rid == "tarantula":
        attach_chain("tarantula", tgt)
        continue
    node = build_node(o)
    tgt.setdefault("children", []).append(node)
    placed_ids.add(rid)
    added.append((o["name"], target_name, node["type"]))

# 额外扫描：报告 repo 中"天体本身已在树里、无需追加"的覆盖情况（抽样）
covered = 0
for o in repo["objects"]:
    if norm(o["name"]) in index and o["id"] not in placed_ids:
        covered += 1

print("\n" + "=" * 60)
print("【融合】astro.json -> universe-tree.json")
print("=" * 60)
print(f"库内天体总数(astro.json): {len(repo_objs)}")
print(f"树中已存在(同名覆盖，未改动): {covered}")
print(f"本次新增节点: {len(added)}")
for nm, par, tp in added:
    print(f"  + {nm}  [{tp}]  -> 挂到「{par}」")
print(f"\n跳过(树中已存在同名): {len(skipped_exist)}")
for nm, par in skipped_exist:
    print(f"  = {nm}  (「{par}」下已有)")
print(f"跳过(无目标父节点/孤儿): {len(skipped_no_target)}")
for rid, t in skipped_no_target:
    print(f"  ! {rid} -> {t}")
print(f"跳过(不在 repo 中): {skipped_unknown}")

# 写出融合结果
json.dump(base, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n已写出融合数据源: {os.path.relpath(OUT, ROOT)}  (节点去重后 {len(index)})")
