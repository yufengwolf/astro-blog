#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
universe_merge.py — 把仓库 astro.json 的天体按【英文 id 唯一关联】挂接到宇宙层级骨架，
产出融合数据源 universe-tree.json。

设计原则（用户硬约束）：
1. 事实源分工：universe-data.json 是「层级拓扑」事实源（节点位置、容器、归属）；
   astro.json 是「天体名称 / 属性 / 来源」唯一事实源。骨架中的 name / name_en 只是
   供人审阅的镜像，须与 astro.json 字节级一致，绝不作为关联依据。
2. 唯一匹配：只按节点 id 做双向 1:1 精确关联。本站天体节点 id == astro.json.id；
   层级容器与本站未收录天体使用 c. 前缀。禁止 lower / 去空白 / 去括号 / 星尾差异 /
   alias 兜底等任何名称模糊匹配。id 缺失、重复、孤立立即报错，改数据而不放宽匹配。
3. 一致性闸：天体节点的 name / name_en 镜像、category 必须与 astro.json 一致；
   type_i18n / category_i18n 必须覆盖全部节点的 type / category，保证双语可切换。
4. 归属严格：校验仓库 parent 链与骨架祖先链兼容（精确祖先或同容器祖先），
   不按类别一刀切分配，不静默塞进默认容器。
5. 写入前比对磁盘内容：无变化则跳过，避免 mkdocs serve 监听触发重建死循环。

用法：python scripts/universe_merge.py
"""
import json, os, re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "universe-data.json")
REPO = os.path.join(ROOT, "docs", "data", "astro.json")
OUT  = os.path.join(ROOT, "universe-tree.json")

CATS = {"宇宙结构", "星系", "星云", "恒星", "聚星系统", "行星", "卫星", "星团",
        "矮行星", "小行星", "彗星", "黑洞", "其他"}

# 仓库 category(英文) -> 受控中文 category
TYPE_MAP = {
    "star": "恒星", "star_system": "聚星系统", "planet": "行星", "moon": "卫星",
    "galaxy": "星系", "nebula": "星云", "black_hole": "黑洞",
    "cluster": "星团", "dwarf_planet": "矮行星", "asteroid": "小行星",
    "comet": "彗星", "structure": "宇宙结构",
}

ID_RE = re.compile(r"[a-z0-9._-]+")
CONTAINER_PREFIX = "c."


base = json.load(open(BASE, encoding="utf-8"))
repo = json.load(open(REPO, encoding="utf-8"))
repo_objs = {o["id"]: o for o in repo["objects"]}

type_i18n = base.get("type_i18n", {})
cat_i18n = base.get("category_i18n", {})

# ---------- 骨架索引：只按 id，不做任何名称匹配 ----------
by_id, parents = {}, {}
dupes, invalid_ids = [], []

def walk(n, parent=None):
    nid = n.get("id")
    if not nid:
        raise SystemExit("骨架节点缺少 id：「%s」" % n.get("name", "?"))
    if not ID_RE.fullmatch(nid):
        invalid_ids.append(nid)
    if nid in by_id:
        dupes.append(nid)
    else:
        by_id[nid] = n
    parents[id(n)] = parent
    if n.get("category") not in CATS:
        raise SystemExit("骨架节点「%s」category 越界: %s" % (nid, n.get("category")))
    for c in n.get("children", []):
        walk(c, n)

walk(base)

# ---------- 非结构·宇宙学现象 ----------
# 这些节点不属于引力束缚结构，单独存放于 non_structure 数组。
# 仍参与 id / category / i18n / repo_id 校验，但不参与 parent 链归属冲突检查
# （它们被刻意移出层级树，astro.json 中的 parent 不再对应层级祖先）。
ns_ids = set()
for ns in base.get("non_structure", []):
    walk(ns, None)
    def _collect_ns(n):
        ns_ids.add(n["id"])
        for c in n.get("children", []):
            _collect_ns(c)
    _collect_ns(ns)

body_ids = {i for i in by_id if not i.startswith(CONTAINER_PREFIX)}
container_ids = set(by_id) - body_ids
orphans = sorted(body_ids - set(repo_objs))       # 骨架有、astro 无
uncovered = sorted(set(repo_objs) - body_ids)      # astro 有、骨架无

# ---------- 按 id 唯一关联 + 镜像/类型一致性闸 ----------
tagged, name_bad, cat_bad, i18n_bad = [], [], [], []

for rid, o in repo_objs.items():
    target = by_id.get(rid)
    if target is None:
        continue                                   # 已在 uncovered 中报错
    if target.get("name") != o["name"]:
        name_bad.append((rid, "name", target.get("name"), o["name"]))
    if target.get("name_en") != o.get("name_en"):
        name_bad.append((rid, "name_en", target.get("name_en"), o.get("name_en")))
    want = TYPE_MAP.get(o["category"])
    if want and target.get("category") != want:
        cat_bad.append((rid, o["name"], want, target.get("category")))
    target["repo_id"] = rid
    tagged.append(rid)

for nid, n in by_id.items():
    if n.get("type") not in type_i18n:
        i18n_bad.append((nid, "type", n.get("type")))
    if n.get("category") not in cat_i18n:
        i18n_bad.append((nid, "category", n.get("category")))

# ---------- 归属校验：仓库 parent 链 vs 骨架祖先链（按 id） ----------
# 仓库 parent 表示「物理母天体」（如行星绕太阳、卫星绕行星），
# 骨架则按「引力从属 / 包含关系」组织（如行星归入内/外行星系统分组）。
# 两者都是合法语义，因此判定为「容器兼容」：
#   (1) 母天体本身就是骨架祖先 —— 精确层级父；
#   (2) 母天体与子天体同属一个容器（母天体的父节点是子天体的祖先）—— 分组式层级。
def ancestor_ids(n):
    out = []
    p = parents.get(id(n))
    while p is not None:
        out.append(p["id"])
        p = parents.get(id(p))
    return out

conflicts = []
for o in repo["objects"]:
    if o["id"] in ns_ids:
        continue                                     # 非结构节点不参与归属冲突检查
    prid = o.get("parent")
    if not prid or prid not in repo_objs:
        continue
    child, parent = by_id.get(o["id"]), by_id.get(prid)
    if child is None or parent is None:
        continue
    chain = ancestor_ids(child)
    exact = prid in chain
    pp = parents.get(id(parent))
    same_container = pp is not None and pp["id"] in chain
    if not (exact or same_container):
        conflicts.append((o["id"], repo_objs[prid]["id"], " > ".join(chain[:3]) or "（根节点下）"))

# ---------- 摘要 ----------
print("=" * 64)
print("【融合】astro.json 按英文 id 唯一关联 -> universe-tree.json")
print("=" * 64)
print("骨架节点: %d  (本站天体 %d / 容器+未收录 %d)   仓库天体: %d   id 精确命中: %d"
      % (len(by_id), len(body_ids), len(container_ids), len(repo_objs), len(tagged)))
print("id 重复: %d   非法 id: %d   容器 id 与 astro 冲突: %d"
      % (len(dupes), len(invalid_ids), len(container_ids & set(repo_objs))))
for d in dupes:
    print("  ! 重复 id: %s" % d)
for d in invalid_ids:
    print("  ! 非法 id: %s" % d)
print("孤立节点(骨架有 / astro 无): %d   未覆盖(astro 有 / 骨架无): %d"
      % (len(orphans), len(uncovered)))
for u in orphans:
    print("  ! 孤立: %s" % u)
for u in uncovered:
    print("  ! 未覆盖: %s  %s" % (u, repo_objs[u]["name"]))
print("名称镜像不一致(name / name_en): %d" % len(name_bad))
for m in name_bad:
    print("  ! %s 的 %s 镜像为「%s」，astro.json 为「%s」" % m)
print("category 类型不一致: %d" % len(cat_bad))
for m in cat_bad:
    print("  ! %s %s 应为「%s」但骨架为「%s」" % m)
print("词表缺项(type_i18n / category_i18n): %d   (type %d 条 / category %d 条)"
      % (len(i18n_bad), len(type_i18n), len(cat_i18n)))
for m in i18n_bad:
    print("  ! %s 的 %s「%s」缺英文词表" % m)
print("归属冲突(parent 链与骨架不一致): %d" % len(conflicts))
for c in conflicts:
    print("  ! %s 仓库父=%s 骨架祖先=%s" % c)
print("\n按 category 分布(骨架):", dict(Counter(n.get("category") for n in by_id.values())))
print("非结构·宇宙学现象节点: %d 个 (已跳过归属冲突检查)" % len(ns_ids))

problems = sum(len(x) for x in (dupes, invalid_ids, orphans, uncovered,
                                name_bad, cat_bad, i18n_bad, conflicts))
if problems:
    print("\n[错误] 共 %d 处不一致，请改数据（不要放宽匹配）" % problems)

# ---------- 写出（写前比对防 serve 死循环） ----------
new_text = json.dumps(base, ensure_ascii=False, indent=2) + "\n"
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as f:
        if f.read() == new_text:
            print("\n融合数据源无变化，跳过写出: %s" % os.path.relpath(OUT, ROOT))
            raise SystemExit(1 if problems else 0)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(new_text)
print("\n已写出融合数据源: %s" % os.path.relpath(OUT, ROOT))
if problems:
    raise SystemExit(1)
