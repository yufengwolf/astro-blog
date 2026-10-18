# 星野笔记 · 太阳系天体数据库

基于 MkDocs + Material for MkDocs 的**静态天体数据工具站**：32 个太阳系天体的结构化数据（质量 / 半径 / 密度 / 温度 / 轨道 / 卫星），首页支持搜索、分类筛选、按任意数值排序；每个天体有独立详情页（完整数据表 + 科普文章）。

## 目录结构

```text
.
├─ mkdocs.yml            # 站点配置（nav/主题/插件）
├─ requirements.txt      # 锁定 mkdocs-material 版本
├─ articles/             # 科普文章源（不在 docs/ 内，不单独建页，合成进详情页）
├─ scripts/
│  ├─ lint_data.py       # 数据 lint：结构+派生量+已知事实校验（不过则阻断）
│  └─ gen_pages.py       # 页面生成器：astro.json → 首页/详情页/总表/数据集页/CSV
└─ docs/
   ├─ index.md           # 【生成】天体总览工具页（勿手改）
   ├─ objects/           # 【生成】32 个天体详情页 + index.md 总表（勿手改）
   ├─ data.md            # 【生成】数据集下载页（勿手改）
   ├─ data/astro.json    # 天体数据库（唯一事实源，手维护）
   ├─ data/astro_flat.csv# 【生成】扁平 CSV
   ├─ js/astro-explore.js# 首页交互（筛选/排序/搜索）
   ├─ stylesheets/extra.css
   └─ assets/            # 图片：文章配图 + assets/planets/*.webp 星球贴图
```

## 日常使用

### 更新天体数据

```bash
# 1. 编辑 docs/data/astro.json
# 2. 数据校验（派生密度/轨道速度/逃逸速度一致性、已知质量顺序等）
python scripts/lint_data.py
# 3. 重新生成页面
python scripts/gen_pages.py
# 4. strict 构建确认零警告
mkdocs build --strict
# 5. 提交推送（CF Pages 自动上线）
```

### 发布一篇科普文章

1. 文章写入仓库根 `articles/<slug>.md`（frontmatter 的 `title` 会成为详情页"延伸阅读"标题）
2. 在 `docs/data/astro.json` 对应天体的 `article` 字段填 `<slug>`
3. 跑 `python scripts/gen_pages.py`，文章自动合成进该天体详情页
4. 配图放 `docs/assets/`，文中相对路径写 `../assets/xxx.jpg`

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

- 鸟神星、妊神星、阋神星（权威源暂无完整实测值）
- 恒星、系外行星（NASA Exoplanet Archive TAP 已规划）
- 太阳贴图（抠图校验暂未通过，现用占位图形）
