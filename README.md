# 站点名称

基于 [MkDocs](https://www.mkdocs.org/) + [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) 的静态博客骨架，可一键部署到 Cloudflare Pages。

## 目录结构

```text
.
├─ mkdocs.yml        # 站点配置
├─ README.md
└─ docs/
   ├─ index.md       # 首页
   ├─ topic1/        # 专题一
   │  └─ index.md
   ├─ topic2/        # 专题二
   │  └─ index.md
   └─ assets/        # 图片资源（文章配图放这里）
```

## ① 本地安装依赖

```bash
pip install mkdocs-material
```

## ② 本地预览

```bash
mkdocs serve
```

> 若 8000 端口已被占用（如本机御风 Home 服务），换端口启动：
>
> ```bash
> mkdocs serve -a 127.0.0.1:8001
> ```

## ③ 访问预览

浏览器打开对应地址（默认 <http://127.0.0.1:8000> ），编辑 `docs/` 下的 Markdown 文件后保存，页面自动热更新。

## 发布一篇文章

1. 在 `docs/<专题目录>/` 下新建 `xxx.md`
2. 配图放入 `docs/assets/`，文中用相对路径引用：首页写 `assets/xxx.jpg`，专题页写 `../assets/xxx.jpg`
3. 在 `mkdocs.yml` 的 `nav` 中登记新页面
4. `mkdocs serve` 本地确认无误后，提交并推送

## 部署到 Cloudflare Pages

1. 代码推送到 GitHub 仓库
2. Cloudflare 控制台 → Workers & Pages → Create → Pages → Connect to Git，选中仓库
3. 构建设置：
   - Framework preset：`None`
   - Build command：`pip install mkdocs-material && mkdocs build`
   - Build output directory：`site`
4. 保存并部署，之后每次 push 自动构建上线

> 也可以本地执行 `mkdocs build` 生成 `site/` 目录，在 Pages 控制台用「直接上传」拖拽部署。

## 套用为一个新站点

复制本仓库，修改 `mkdocs.yml` 中的 `site_name` / `site_description` / `site_author` / `site_url` 和 `nav` 栏目名即可。
