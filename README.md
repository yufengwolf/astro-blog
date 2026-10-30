# 星野笔记 · 天体数据库

基于 MkDocs + Material for MkDocs 的**静态天体数据工具站**：**152 个天体、11 类**（恒星 56 / 卫星 21 / 星系 18 / 星云 16 / 星团 11 / 行星 8 / 黑洞 8 / 大尺度结构 7 / 矮行星 5 / 小行星 1 / 彗星 1）的结构化数据（质量 / 半径 / 密度 / 温度 / 轨道 / 卫星 / 光谱型等），覆盖太阳系天体到恒星、星云、星系、黑洞；首页支持搜索、分类筛选、按任意数值排序；每个天体有独立详情页（完整数据表 + 可选科普文章）；另有独立 `/compare/` 对比页做多天体尺寸/参数对比。

> **维护者看这里**：[维护指南.md](维护指南.md) —— 自助维护全流程（AI 录入 / 图片编排 / NASA 真图 / 数据校验 / 收尾构建），含端到端流程图与命令速查，每条都是可直接复制的命令。**任何代码改动都必须同步更新该指南与本文档**（见文末「文档维护约定」）。

---

## 一、它是什么

- **数据站为主、文章附属**：以 `docs/data/astro.json` 为唯一事实源，所有页面/CSV/贴图从它生成。
- **可追溯**：每个对象带 `data_source` / `data_verified` / `image_source` / `image_locked`，可一条命令筛出"AI 吐的数据""未校验的数据""程序化占位图""真实照片"。
- **AI 编排录入**：只给一个名字，`add_object.py` 让豆包自动定位类型、抽数据、写库，并**自动出图 + 自动生成页面/构建**。

---

## 二、目录结构

```text
.
├─ mkdocs.yml            # 站点配置（nav/主题/插件）
├─ 维护指南.md           # 自助维护全流程（命令速查 + 踩坑 + 流程图）
├─ requirements.txt      # 锁定 mkdocs-material==9.7.7
├─ articles/             # 科普文章源（合成进详情页，不在 docs/ 内）
├─ scripts/
│  ├─ add_object.py      # 【AI 编排层】只给名字 → 自动分类/抽数据/写库 + 自动出图
│  ├─ sync_images.py     # 【图片编排】按类别路由 + 豆包AI优先/程序化兜底
│  ├─ query.py           # 来源/校验筛选器（人工校验用: --unverified/--data-source/--image-source/--missing）
│  ├─ migrate_provenance.py # 一次性回填 provenance 字段（已跑过, 日常不用）
│  ├─ fetch_astro_data.py# 太阳系权威核查: status/--propose/--apply
│  ├─ nasa_image.py      # NASA 真实影像: <id> <url> 手动安装 / --search / --auto-batch
│  ├─ lint_data.py       # 数据 lint: 结构+派生量校验（不过则阻断）
│  ├─ gen_pages.py       # 页面生成器 v1.6（--check 校验同步）
│  ├─ star_types.py      # 恒星 9 光谱型定义 + 映射 + 色相偏移
│  ├─ gen_star_types_doubao.py # 每型 1 张豆包 AI 代表图（--sun 生成太阳底图）
│  ├─ build_star_images.py# 恒星套模板 + limb 圆拟合 + 色相微调
│  ├─ gen_bigscale_image.py   # 黑洞/星云/星系/星团/结构 程序化生成
│  ├─ venus_circle.py    # 金星特例：NASA 雷达图内切圆
│  ├─ cdp_shot.js        # 移动端真机布局验证（CDP 设备模拟）
│  ├─ serve_nocache.py   # 本地预览（带 Cache-Control:no-cache 头）
│  ├─ test_fetch_astro.py# 解析器+合库回归测试
│  └─ insert_*.py        # 历史一次性批录入（insert_stars/insert_bigscale/insert_bigscale2，已不再日常使用）
└─ docs/
   ├─ index.md           # 【生成】天体总览工具页（勿手改）
   ├─ objects/           # 【生成】152 个天体详情页 + index.md 总表（勿手改）
   ├─ data.md            # 【生成】数据集下载页（不挂导航，仅 URL/sitemap 可达）
   ├─ data/astro.json    # 天体数据库（唯一事实源）
   ├─ data/nasa_images.json # NASA 真实影像登记表
   ├─ data/astro_flat.csv# 【生成】扁平 CSV
   ├─ js/astro-explore.js# 首页交互（筛选/排序/搜索）
   ├─ js/compare.js      # 独立对比页 /compare/ 逻辑
   ├─ js/solar-embed.js  # 3D 嵌入页：全屏切换 + 移动端横屏提示
   ├─ stylesheets/site.css   # 含 .solar-embed 嵌入块样式
   ├─ solar-demo.md      # 【手写】太阳系 3D 交互站主页（导航卡片 iframe）
   └─ assets/planets/*.webp  # 星球贴图（152/152，透明背景 600px）
```

---

## 三、完整工作流（新增一个天体）

```mermaid
flowchart TD
    U["add_object.py --name 名字"] --> P{"已收录?"}
    P -->|是| S["跳过"]
    P -->|否| L["豆包 :9090 默认<br/>本地 :8080 兜底<br/>分类+抽数据"]
    L --> W["写入 astro.json (幂等)<br/>+ provenance 字段"]
    W --> Y["自动 sync_images --ids"]
    Y --> R{"类别路由 (豆包优先)"}
    R -->|恒星/太阳| E["套豆包模板 (不审核)"]
    R -->|黑洞| F0["程序化 (不审核)"]
    R -->|星云/星系/星团/结构| F["豆包AI占位→回退程序化 (全幅)"]
    R -->|行星/卫星/矮行星/小行星/彗星| G["豆包AI生成→回退程序化 (裁圆)"]
    E --> V["自动 gen_pages + mkdocs build"]
    F0 --> V
    F --> V
    G --> V
```

**最简用法**：

```bash
python scripts/add_object.py --name "南河三"     # 只给名字，自动分类/抽数据/写库/出图/生成页面/构建
python scripts/add_object.py --name "参宿四" --dry-run  # 先看草稿不落盘、不出图
python scripts/add_object.py --batch names.txt  # 批量录入：names.txt 每行一个名字，豆包两发一致性对拍
python scripts/add_object.py --batch names.txt --dry-run  # 先预览将写入的对象，不落盘
python scripts/add_object.py --recheck --category all    # AI 复校：全量重新抽数，争议字段置空、空缺补填
python scripts/add_object.py --recheck --category star   # 只复校恒星（也支持 planet / 具体名 --name / 名单 --batch）
python scripts/add_object.py --recheck --dry-run         # 先预览将置空/填充的字段，不落盘
```
> 默认一条命令搞定「数据→出图→页面→构建」；`--no-sync` 关闭出图、`--no-pages` 关闭页面/构建（关闭后需手动 `gen_pages + mkdocs build` 才能在网页看到）。批量模式三阶段解耦（并发抽数→写盘一次→统一出图+build），豆包 `:9090` 两发对拍筛掉随机幻觉；**两发不一致时逐字段合并——一致字段保留、争议字段置 null 不误填**。复校模式（`--recheck`）对已有对象重新抽数做数据清洗：相同字段级规则（争议置空、空缺补填），可按 `--category/--name/--batch` 筛选，官方 API 来源（`data_source=official_api`）默认跳过、`--force` 强制，整批可反复重跑（幂等）。

写入后如需把程序化占位换成 NASA 真图（尤其行星/卫星）：

```bash
python scripts/nasa_image.py <id> <NASA图片URL>   # 你给地址 → 下载+校验标题+自适应裁图+锁定
python scripts/nasa_image.py 智神星 ai             # 豆包图不满意/失败时，按名重试豆包出图(默认重试3次)
python scripts/nasa_image.py 共工星 ai --retries 5  # 改重试次数；--no-pages 可不自动重建站点
```

收尾校验与构建（每次维护必跑）：

```bash
python scripts/lint_data.py && python scripts/gen_pages.py --check && mkdocs build --strict
```

---

## 四、快速开始（本地）

```bash
pip install -r requirements.txt
python scripts/serve_nocache.py 8001 site   # 带 no-cache 头，避免本地缓存旧资源
# 或
mkdocs serve -a 127.0.0.1:8001              # 8000 端口被御风 Home 占用时换端口
```

---

## 五、数据源与许可

- **数值数据**：太阳系天体整理自 NASA NSSDC Planetary/Satellite Fact Sheets、NASA/JPL SBDB API（美国政府作品，公共领域）；恒星/星系/星云/黑洞等经 `add_object.py`（AI 编排层）录入——`--name` 模式把名字发给豆包/本地模型，**由 LLM 凭训练记忆给出知名天体的最佳近似真值**（`llm_doubao` / `llm_local` 来源，**不查权威 API、无对拍闸，建议人工校验**）；`--facts` 可喂检索文本、`--json` 可直接录入权威值。
- **星球影像**：行星/卫星多为 NASA 真实影像（公共领域，详情页署名可溯源 PIA 编号，`image_source=nasa`）；恒星为豆包 AI 模板（`doubao_template`）；黑洞为程序化示意图（`programmatic`）；星云/星系/星团/结构及行星/矮行星/卫星/小行星/彗星默认由**豆包 AI 生成**（`doubao`，失败回退程序化 `programmatic`）。网页署名面向访客只显示短文案：「AI 生成」/「程序化示意图」。
- **一句话简介**为本站原创。
- 每个天体详情页标注来源标识与核对日期；数据错误欢迎到 GitHub Issues 反馈。

---

## 六、部署到 Cloudflare Pages

1. 代码推送到 GitHub 仓库
2. Cloudflare Pages → Connect to Git，选中仓库
3. 构建设置：Framework preset `MkDocs`；Build command `pip install -r requirements.txt && mkdocs build`；output `site`
4. 保存后每次 push 自动构建上线

> 页面是构建前生成并提交的，CF 端只跑 `mkdocs build`。如需 CF 构建时生成，把 build command 换成
> `pip install -r requirements.txt && python scripts/gen_pages.py --check && mkdocs build`（`--check` 会校验产物与 JSON 同步）。

> **太阳系 3D 页面不在本仓库**：它们是另一个 Cloudflare Pages 站点，以 iframe 形式嵌进来，详见下一章。

---

## 七、太阳系 3D 交互站（外站 iframe）

本站只有 **1 个** 3D 导航页（`/solar-demo/`，左侧导航叫「太阳系3D模型」），但**3D 工程本身不在本仓库**——它是独立仓库 + 独立 Cloudflare Pages 站点。
该页用 `iframe` 嵌入 3D 站点的**导航主页**（卡片式，列出全部 8 个系统），在 iframe 内点任意卡片即可直接打开对应系统；顶部「↺ 重新选择」按钮可一键退回主页换看别的系统。

| 项 | 值 |
|---|---|
| 3D 工程仓库 | https://github.com/yufengwolf/astro-solar-3d |
| 3D 导航主页（iframe 源） | https://astro-solar-3d.pages.dev |
| 部署方式 | CF Pages 连 GitHub；`npm ci && npm run build`，输出 `dist`，环境变量 `NODE_VERSION=20` |

**URL 说明**（CF Pages 会把 `/xxx.html` 308 重定向到 `/xxx`，所以统一用无扩展名写法）：

- 3D 站根路径 `https://astro-solar-3d.pages.dev/` 是导航主页（卡片，列出全部系统）
- 各系统：`/overview`（太阳系总览）、`/earth-moon`、`/mars`、`/jupiter`、`/saturn`、`/uranus`、`/neptune`、`/pluto`

**改哪里**：

- 改 3D 内容（天体、轨道、贴图）→ 去 3D 仓库改并 push，CF 自动部署，**本站无需任何改动**
- 改嵌入样式 / 全屏 / 横屏提示 / 重新选择按钮 → 本仓库的 `docs/js/solar-embed.js` 与 `site.css` 的 `.solar-embed`
- 改页面上下说明文字 → 本仓库 `docs/solar-demo.md`
- 改导航显示名 → 本仓库 `mkdocs.yml` 的 `nav`

**为什么不放本站目录**：产物约 20MB / 57 个文件。塞进本仓库会让每次 push 都带上这些静态文件，
并连带触发 mkdocs 全量重建。拆开后两边构建彻底解耦，各自独立缓存。

**全屏实现**：按钮在本站页面上，调的是本站元素的 `requestFullscreen()`（同源，无需授权）；
iframe 上的 `allow="fullscreen"` 只是兜底。移动端全屏会尝试锁定横屏，仍竖屏则显示旋转提示；
iOS Safari 不支持元素全屏时回退为新标签打开独立页。

---

## 八、文档维护约定

**硬规则**：本站任何脚本或工作流变更（新增/修改/删除脚本、增删命令参数、改图片路由、改数据字段、改 LLM 路由），都**必须在同一轮改动中同步更新 [维护指南.md](维护指南.md) 与本文档**（对应章节 + 流程图），并随代码一起提交。**不依赖任何人提醒。** 详细清单见维护指南第十一章。
