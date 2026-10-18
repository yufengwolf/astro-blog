# 星野笔记 · 天体数据库

基于 MkDocs + Material for MkDocs 的**静态天体数据工具站**：32 个天体的结构化数据（质量 / 半径 / 密度 / 温度 / 轨道 / 卫星），当前以太阳系为主，后续向恒星与系外行星扩展；首页支持搜索、分类筛选、按任意数值排序；每个天体有独立详情页（完整数据表 + 科普文章）。

## 目录结构

```text
.
├─ mkdocs.yml            # 站点配置（nav/主题/插件）
├─ requirements.txt      # 锁定 mkdocs-material 版本
├─ articles/             # 科普文章源（不在 docs/ 内，不单独建页，合成进详情页）
├─ scripts/
│  ├─ lint_data.py       # 数据 lint：结构+派生量+已知事实校验（不过则阻断）
│  ├─ gen_pages.py       # 页面生成器：astro.json → 首页/详情页/总表/数据集页/CSV
│  └─ test_compare.js    # 对比功能回归测试（Node + DOM stub，31 项断言）
└─ docs/
   ├─ index.md           # 【生成】天体总览工具页（勿手改）
   ├─ objects/           # 【生成】32 个天体详情页 + index.md 总表（勿手改）
   ├─ data.md            # 【生成】数据集下载页（勿手改；不挂导航，仅 URL/sitemap 可达）
   ├─ data/astro.json    # 天体数据库（唯一事实源，手维护）
   ├─ data/astro_flat.csv# 【生成】扁平 CSV
   ├─ js/astro-explore.js# 首页交互（筛选/排序/搜索）
   ├─ js/astro-compare.js# 详情页多天体对比
   ├─ stylesheets/extra.css
   └─ assets/            # 图片：文章配图 + assets/planets/*.webp 星球贴图
```

## 日常使用

### 更新天体数据

```bash
# 0.（建议，季度节奏）先从 NASA 源拉数据生成核查报告，确认有没有源更新
python scripts/fetch_astro_data.py        # 报告落 reports/astro_fetch_latest.md
# 1. 按报告人工更新 docs/data/astro.json（脚本只读不改，详见下节）
# 2. 数据校验（派生密度/轨道速度/逃逸速度一致性、已知质量顺序等）
python scripts/lint_data.py
# 3. 重新生成页面
python scripts/gen_pages.py
# 4. strict 构建确认零警告
mkdocs build --strict
# 5. 提交推送（CF Pages 自动上线）
```

### 数据源核查（fetch_astro_data.py）

天体物理参数不是行情数据，没有理由无人值守自动合入——脚本永远只产**变更提案**：

```bash
python scripts/fetch_astro_data.py                # 全量：NSSDC fact sheets + JPL SBDB
python scripts/fetch_astro_data.py --source nssdc # 只跑一个源
python scripts/fetch_astro_data.py --offline      # 用缓存离线重放（调试用）
python scripts/test_fetch_astro.py                # 解析器回归测试（19 项断言）
```

- **数据源**：NSSDC Planetary Fact Sheets（nssdc.gsfc.nasa.gov，NASA Goddard，
  覆盖太阳/八大行星/月球/冥王星/火卫一二/四大卫星系统，共 15 页，公共领域）
  + JPL SBDB API（ssd-api.jpl.nasa.gov，免 key，谷神星等小天体，公共领域）
- **产物**：`reports/astro_fetch_<时间戳>.md`（人读；`reports/` 与 `scripts/.cache/`
  已 gitignore，缓存用于复现与离线重放）
- **判定**：相对差异 ≤1% 一致、1–5% 微小、>5% 显著；反照率自动甄别 Bond/Geometric
  双口径，逆行自转自动处理符号约定；退出码 0=无显著差异，1=有，2=抓取失败
- **礼仪**：单并发、1s 间隔、带 UA、失败退避（遵循 JPL Fair Use Policy）；
  报告会记录每个源页面的 Last Updated 日期
- 人审报告 → 手动改 `astro.json`（同步 `sources`/`verified`）→ 回到上面的更新流程

### 发布一篇科普文章

1. 文章写入仓库根 `articles/<slug>.md`（文内 H1 或 frontmatter `title` 会成为详情页「延伸阅读」标题）
2. 在 `docs/data/astro.json` 对应天体的 `article` 字段填 `<slug>`
3. 跑 `python scripts/gen_pages.py`，文章自动合成进该天体详情页，并登记到底部「相关文章」区块
4. 配图放 `docs/assets/`，文中相对路径写 `../assets/xxx.jpg`

### 天体对比（详情页）

每个详情页有「⚖ 与其他天体对比」按钮：搜索数据库内任意天体（可多选，上限 5 列），
逐参数对比（含"质量/半径（地球=1）"派生行）；对比组合同步到 URL hash
（`#compare=earth,moon`），刷新/分享保持。改 `astro-compare.js` 或生成器后跑回归测试：

```bash
node scripts/test_compare.js   # 31 项断言：渲染/增删/hash/上限/格式化一致性
```

### 数据集页策略

`data.md`（数据集下载）**不挂导航、界面无入口**，仅经 URL 直达与 sitemap 收录，
人类访客在界面上看不到下载链接；`astro.json` 同时以精简形式内嵌在每个详情页中
供对比功能使用。

### 本地预览

```bash
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
>（`--check` 会校验产物与 JSON 同步，不同步则构建失败）。

## 数据源与许可

- 数值数据整理自 NASA NSSDC Planetary/Satellite Fact Sheets、NASA/JPL SBDB API（美国政府作品，公共领域）
- 一句话简介为本站原创
- 每个天体详情页标注来源标识与核对日期；数据错误欢迎到 GitHub Issues 反馈

## 待补充

- 鸟神星、妊神星、阋神星：SBDB 有轨道要素与自转周期，缺 GM/直径等实测值（2026-10 核查确认）
- 恒星、系外行星（NASA Exoplanet Archive TAP 已规划）
- 反照率口径统一：当前地球与气态巨行星取 Bond、月球与卫星取 Geometric（核查报告已自动甄别）
