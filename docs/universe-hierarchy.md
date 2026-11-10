---
hide:
  - toc
---

# 宇宙天体层级思维导图

下面是通过 `iframe` 嵌入的**宇宙天体层级思维导图**——按「引力从属 / 包含关系」组织的可折叠树，从「可观测宇宙」一路下钻到行星、卫星、星团与星云。数据由外部层级文档与「星野笔记」天体库（`astro.json`）融合而成，**天体本体数值准确性要求不高，层级所属严格**。

<div class="solar-embed" id="universe-embed">
  <div class="solar-frame">
    <iframe src="/universe-hierarchy.html" title="宇宙天体层级思维导图" loading="lazy" allowfullscreen style="height:82vh"></iframe>
  </div>
</div>

- 顶部搜索框可按**名称或类型**实时过滤；下方色块为**大类筛选**（宇宙结构 / 星系 / 星云 / 恒星 / 行星 / 卫星 / 星团 / 矮行星 / 小行星 / 彗星 / 黑洞），可多选。
- 点击任一节点可展开 / 折叠其下级，同时顶部显示当前的**层级路径（面包屑）**；「展开全部 / 折叠全部」一键切换。
- 每个节点标注**类型**与（若有）**简介、来源**；颜色仅代表大类，便于在长树中快速定位。
- 想要更大视野？点右上角「全屏」，或[在新标签页打开完整独立版 ↗](/universe-hierarchy.html)。

> 本页思维导图的数据源是仓库根目录的 `universe-tree.json`（由 `universe-data.json` 与 `docs/data/astro.json` 经 `scripts/universe_merge.py` 融合生成）。修改数据后运行 `python scripts/build_universe_html.py` 即可重新生成下方的独立 HTML。
