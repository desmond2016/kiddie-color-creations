#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端静态文件服务器
解决CORS问题，让前端通过HTTP协议访问
"""
import http.server
import socketserver
import os
import webbrowser
import threading
import time

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="frontend", **kwargs)
    
    def end_headers(self):
        # 添加CORS头
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Admin-Key')
        super().end_headers()

def start_server():
    PORT = 8080
    
    # 检查端口是否可用
    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print(f"前端服务器启动在 http://localhost:{PORT}")
            print(f"主页面: http://localhost:{PORT}/index.html")
            print(f"管理员后台: http://localhost:{PORT}/admin.html")
            print("按 Ctrl+C 停止服务器")
            
            # 延迟打开浏览器
            def open_browser():
                time.sleep(2)
                webbrowser.open(f'http://localhost:{PORT}/index.html')
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            httpd.serve_forever()
            
    except OSError as e:
        if e.errno == 10048:  # Windows: 端口已被占用
            print(f"端口 {PORT} 已被占用，请关闭占用该端口的程序或使用其他端口")
        else:
            print(f"启动服务器失败: {e}")
    except KeyboardInterrupt:
        print("\n服务器已停止")

if __name__ == '__main__':
    # 确保在正确的目录
    if not os.path.exists('frontend'):
        print("错误：找不到 frontend 目录")
        print("请确保在项目根目录运行此脚本")
        exit(1)
    
    start_server()
