#!/usr/bin/env python3
"""本地预览服务器：在 python -m http.server 基础上给所有响应加 Cache-Control: no-cache。
原因：MkDocs 自定义 JS/CSS 不带内容 hash、URL 固定，浏览器/代理会长期缓存，
导致「改了代码却显示旧版」。加 no-cache 让浏览器每次加载都向源站校验，内容变更即生效。
用法: python scripts/serve_nocache.py [port] [directory]
"""
import http.server
import socketserver
import os
import sys


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 强制 revalidate：浏览器每次加载都校验，内容变了就拉新
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *args):  # 静默
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    directory = sys.argv[2] if len(sys.argv) > 2 else "site"
    os.chdir(directory)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", port), NoCacheHandler) as httpd:
        print(f"no-cache preview server on http://0.0.0.0:{port}/  (serving ./{directory})")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
