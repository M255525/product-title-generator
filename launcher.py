# -*- coding: utf-8 -*-
"""跨境商品標題產生器 — 桌面啟動器（備用，本次未打包 exe）

執行時在本機 127.0.0.1:8791 啟動靜態伺服器並開啟預設瀏覽器。
固定使用 8791 埠，讓瀏覽器 localStorage（已產生的標題、API 設定、序號）跨次啟動保留。
"""
import http.server
import os
import socket
import sys
import threading
import webbrowser

PORT = 8791
HOST = "127.0.0.1"


def resource_dir() -> str:
    """PyInstaller onefile 解壓目錄；直接執行 .py 時為腳本所在目錄。"""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def port_in_use() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, PORT)) == 0


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=resource_dir(), **kwargs)

    def log_message(self, fmt, *args):  # 不在主控台洗 log
        pass


def main() -> None:
    url = f"http://{HOST}:{PORT}/index.html"

    if port_in_use():
        print("偵測到跨境商品標題產生器已在執行中，開啟瀏覽器頁面…")
        webbrowser.open(url)
        return

    server = http.server.ThreadingHTTPServer((HOST, PORT), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print("=" * 46)
    print("  跨境商品標題產生器")
    print("=" * 46)
    print()
    print(f"  已啟動：{url}")
    print("  瀏覽器將自動開啟；若沒有，請手動貼上上方網址。")
    print()
    print("  ※ 使用期間請保持此視窗開啟；")
    print("    關閉此視窗即結束程式（已填資料存於瀏覽器，不會遺失）。")
    print()
    print("  本工具僅供教學、課程及個人使用，")
    print("  禁止未經授權公開發布、販售或商業化使用。  製作：Mark Tsai")
    print()

    webbrowser.open(url)

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
