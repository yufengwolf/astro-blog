#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
universe_hook.py — MkDocs 构建钩子（hooks）

在每次 `mkdocs build` 之前，由 JSON 数据源自动重新生成「宇宙层级」思维导图页：
  1. scripts/universe_merge.py    —— universe-data.json + astro.json -> universe-tree.json（融合数据源）
  2. scripts/build_universe_html.py —— universe-tree.json -> docs/universe-hierarchy.md（Material 主题化页面）

这样 universe-data.json / astro.json 任何改动，只要跑 `mkdocs build` 页面就自动同步，
无需手动执行生成脚本——实现「数据驱动、改动自适应」。
钩子失败只告警、不中断构建（旧产物仍存在，构建仍可过）。
"""
import os
import subprocess
import sys


def on_pre_build(config):
    root = os.path.dirname(os.path.abspath(__file__))
    py = sys.executable
    steps = (
        ("scripts/universe_merge.py", "融合数据源 universe-tree.json"),
        ("scripts/build_universe_html.py", "生成思维导图页 universe-hierarchy.md"),
    )
    for rel, label in steps:
        script = os.path.join(root, rel)
        if not os.path.exists(script):
            print(f"[universe-hook] 跳过：未找到 {rel}")
            continue
        try:
            r = subprocess.run(
                [py, script], cwd=root, capture_output=True, text=True
            )
            if r.returncode != 0:
                print(f"[universe-hook] 警告：{label} 失败（返回 {r.returncode}）")
                if r.stderr.strip():
                    print(r.stderr.strip())
            else:
                # 仅打印最后一行摘要，避免刷屏
                out = [l for l in r.stdout.strip().splitlines() if l.strip()]
                if out:
                    print("[universe-hook]", out[-1])
        except Exception as e:  # 钩子异常绝不中断构建
            print(f"[universe-hook] 警告：执行 {rel} 异常：{e}")
