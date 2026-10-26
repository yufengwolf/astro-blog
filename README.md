# 星野笔记 · 天体数据库

基于 MkDocs + Material for MkDocs 的**静态天体数据工具站**：**152 个天体、11 类**（恒星 56 / 卫星 21 / 星系 18 / 星云 16 / 星团 11 / 行星 8 / 黑洞 8 / 大尺度结构 7 / 矮行星 5 / 小行星 1 / 彗星 1）的结构化数据（质量 / 半径 / 密度 / 温度 / 轨道 / 卫星 / 光谱型等），覆盖太阳系天体到恒星、星云、星系、黑洞；首页支持搜索、分类筛选、按任意数值排序；每个天体有独立详情页（完整数据表 + 可选科普文章）；另有独立 `/compare/` 对比页做多天体尺寸/参数对比。

> **维护者看这里**：[维护指南.md](维护指南.md) —— 自助维护全流程（AI 录入 / 太阳系核查 / 图片编排 / NASA 真图 / 校验构建），每条都是可直接复制的命令，无隐藏操作。

## 目录结构

```text
.
├─ mkdocs.yml            # 站点配置（nav/主题/插件）
├─ 维护指南.md           # 自助维护全流程（命令速查 + 踩坑记录）
├─ requirements.txt      # 锁定 mkdocs-material 版本
├─ articles/             # 科普文章源（不在 docs/ 内，不单独建页，合成进详情页）
├─ scripts/
│  ├─ add_object.py      # 【AI 编排层】只给名字 → 自动分类/抓数据/写库
│  ├─ sync_images.py     # 【图片编排】按类别路由 + 固态球体程序化兜底
│  ├─ fetch_astro_data.py# 太阳系核查：status/--objects/--propose/--apply
│  ├─ lint_data.py       # 数据 lint：结构+派生量+已知事实校验（不过则阻断）
│  ├─ gen_pages.py       # 页面生成器：astro.json → 首页/详情页/总表/数据集页/CSV（v1.6）
│  ├─ nasa_image.py      # NASA 真实影像：--search 找图 / --set 安装（自动署名+锁定）
│  ├─ star_types.py      # 恒星 9 光谱型定义 + 映射 + 色相偏移
│  ├─ gen_star_types_doubao.py # 每型 1 张豆包 AI 代表图（--sun 生成太阳底图）
│  ├─ build_star_images.py# 代表图 limb 圆拟合居中切圆 → 54 星共用 + 色相微调
│  ├─ gen_bigscale_image.py   # 黑洞/星云/星系/星团/结构 程序化生成
│  ├─ venus_circle.py    # 金星特例：NASA 雷达图内切圆
│  ├─ cdp_shot.js        # 移动端真机布局验证（CDP 设备模拟）
│  ├─ serve_nocache.py   # 本地预览（带 Cache-Control:no-cache 头）
│  └─ test_fetch_astro.py# 解析器+合库回归测试
└─ docs/
   ├─ index.md           # 【生成】天体总览工具页（勿手改）
   ├─ objects/           # 【生成】152 个天体详情页 + index.md 总表（勿手改）
   ├─ data.md            # 【生成】数据集下载页（不挂导航，仅 URL/sitemap 可达）
   ├─ data/astro.json    # 天体数据库（唯一事实源，脚本合入/手维护）
   ├─ data/nasa_images.json # NASA 真实影像登记表
   ├─ data/astro_flat.csv# 【生成】扁平 CSV
   ├─ js/astro-explore.js# 首页交互（筛选/排序/搜索）
   ├─ js/compare.js      # 独立对比页 /compare/ 逻辑
   ├─ stylesheets/extra.css
   └─ assets/            # 文章配图 + assets/planets/*.webp 星球贴图（152/152）
```

## 日常使用

### 新增天体（两条路径）

**路径 A · AI 编排层（任意类型，推荐）**——只给名字，LLM 自动定位类型、拉数据特征、写库：

```bash
python scripts/add_object.py --name "南河三"     # 只给名字
python scripts/add_object.py --name "参宿四" --dry-run  # 先看草稿不落盘
```

写入后跑 `python scripts/sync_images.py` 自动按类别出图（恒星/黑洞套模板不审核，其余需人工审核真图）。详见 [维护指南.md](维护指南.md) 第二节。

**路径 B · 太阳系权威核查**——行星/卫星/矮行星/TNO 用 NSSDC + SBDB 对照：

```bash
python scripts/fetch_astro_data.py status              # 零网络本地体检（建议先跑）
python scripts/fetch_astro_data.py --propose quaoar    # 生成候选骨架（无值填 null 不编造）
# 人工补 tagline（lint 门禁）→
python scripts/fetch_astro_data.py --apply quaoar      # 合库（唯一写库入口）
```

### 更新天体数据

```bash
python scripts/fetch_astro_data.py status              # 对象/字段矩阵/新鲜度/缺口
python scripts/fetch_astro_data.py --objects mars,moon # 只核查关注的对象（不传则全量）
# 审 reports/ 报告（只提案，永不自动改库）→ 手动改 docs/data/astro.json
python scripts/lint_data.py          # 派生量一致性等校验
python scripts/gen_pages.py          # 重新生成页面
mkdocs build --strict                # 零警告才算过
```

### 数据源核查（fetch_astro_data.py）

天体物理参数不是行情数据，没有理由无人值守自动合入——自动拉取永远只产**变更提案**，写库只有 `--apply` 一个显式入口：

```bash
python scripts/fetch_astro_data.py status              # 零网络本地体检
python scripts/fetch_astro_data.py                     # 全量：NSSDC fact sheets + JPL SBDB
python scripts/fetch_astro_data.py --objects mars,moon # 针对性拉取
python scripts/fetch_astro_data.py --propose quaoar    # 库外对象候选骨架
python scripts/fetch_astro_data.py --apply quaoar      # 人审后合入（唯一写库入口）
python scripts/test_fetch_astro.py                     # 解析器+合库回归测试
```

- **数据源**：NSSDC Planetary Fact Sheets（NASA Goddard，覆盖太阳/八大行星/月球/冥王星/主要卫星）+ JPL SBDB API（小天体/矮行星/TNO）。恒星/星系/星云/黑洞等数据由 `add_object.py` 经 LLM 检索权威源（如 SIMBAD、NASA Exoplanet Archive、各型恒星文献）后录入，字段缺失一律 `null`。
- **产物**：`reports/astro_fetch_<时间戳>.md`（人读；`reports/` 与 `scripts/.cache/` 已 gitignore）；`reports/propose_<id>.json`（候选骨架）
- **判定**：相对差异 ≤1% 一致、1–5% 微小、>5% 显著；退出码 0=无显著差异，1=有，2=抓取失败
- **新鲜度**：每个对象带 `verified`（本站核对日）与 `source_dates`，`status` 据此输出新鲜度面板

### 星球贴图（152/152 已全覆盖）

详细命令与踩坑记录见 [维护指南.md](维护指南.md) 第二节：

1. **AI 编排自动出图**（默认）：`python scripts/sync_images.py` 按类别路由——
   - 恒星/太阳 → `build_star_images.py`（9 光谱型豆包 AI 代表图 + limb 圆拟合 + 色相微调）
   - 黑洞/星云/星系/星团/结构 → `gen_bigscale_image.py` 程序化
   - 行星/卫星/矮行星/小行星/彗星 → `gen_solid_body` 程序化兜底（临边昏暗+高光、圆外透明）
2. **NASA 真实影像**（有真图首选，尤其行星/卫星）：`python scripts/nasa_image.py --search <关键词>` 找图 → `--set <id> <PIA号> "<署名>"` 安装（自动圆盘裁剪/透明化/600px/登记署名/`image_locked` 锁定）
3. **手动放置**：图存 `docs/assets/planets/<id>.webp`，astro.json 填 `image` + `image_credit` + `image_locked: true`

### 发布一篇科普文章

1. 文章写入仓库根 `articles/<slug>.md`（文内 H1 或 frontmatter `title` 会成为详情页「延伸阅读」标题）
2. 在 `docs/data/astro.json` 对应天体的 `article` 字段填 `<slug>`
3. 跑 `python scripts/gen_pages.py`，文章自动合成进该天体详情页

### 天体对比（独立 /compare/ 页）

导航进入 `/compare/`，搜索数据库内任意天体（可多选）加入 A/B 两侧，逐参数对比（含"质量/半径（地球=1）"派生行）。球体贴图按真实比例渲染，悬殊比例默认真实比例（小方缩为「点」+ 大字标倍数）。对比逻辑在 `docs/js/compare.js`。

### 数据集页策略

`data.md`（数据集下载）**不挂导航、界面无入口**，仅经 URL 直达与 sitemap 收录；`astro.json` 同时以精简形式内嵌在每个详情页中供对比功能使用。

### 本地预览

```bash
python scripts/serve_nocache.py 8001 site   # 带 no-cache 头，避免本地缓存旧资源
# 或
mkdocs serve -a 127.0.0.1:8001   # 8000 端口被御风 Home 占用时换端口
```

## 部署到 Cloudflare Pages

1. 代码推送到 GitHub 仓库
2. Cloudflare Pages → Connect to Git，选中仓库
3. 构建设置：
   - Framework preset：`MkDocs`
   - Build command：`pip install -r requirements.txt && mkdocs build`
   - Build output directory：`site`
4. 保存后每次 push 自动构建上线

> 页面是构建前生成并提交的，CF 端只跑 `mkdocs build`。
> 如希望改为 CF 构建时生成，把 build command 换成
> `pip install -r requirements.txt && python scripts/gen_pages.py --check && mkdocs build`
> （`--check` 会校验产物与 JSON 同步，不同步则构建失败）。

## 数据源与许可

- 数值数据整理自 NASA NSSDC Planetary/Satellite Fact Sheets、NASA/JPL SBDB API（美国政府作品，公共领域）；恒星/星系/星云/黑洞等经 `add_object.py` 检索 SIMBAD、NASA Exoplanet Archive 及各权威文献后录入
- 星球影像：行星/卫星多为 NASA 真实影像（公共领域，详情页署名可溯源 PIA 编号）；恒星/黑洞/星云/星系为程序化或 AI 生成示意图（表面特征据科学结论绘制）
- 一句话简介为本站原创
- 每个天体详情页标注来源标识与核对日期；数据错误欢迎到 GitHub Issues 反馈

## 待补充

- 反照率口径统一：当前地球与气态巨行星取 Bond、月球与卫星取 Geometric（核查报告已自动甄别），逐步统一
- 系外行星（NASA Exoplanet Archive TAP）可经 `add_object.py` 持续扩收，维持精选不盲目扩
- 部分罕见类型（如小行星/彗星目前各 1 个）可随资料完善增补
