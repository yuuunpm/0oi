"""墨魂·江湖 — 纯静态文件服务器（仅用于本地预览）"""
import http.server
import socketserver
import os

PORT = int(os.environ.get("PORT", 8080))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


if __name__ == "__main__":
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"墨魂·江湖运行在 http://localhost:{PORT}/")
        httpd.serve_forever()
