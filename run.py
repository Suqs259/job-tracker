"""日常启动入口：拉起服务并自动打开浏览器。

开发调试请用 `python app.py`（带热重载）；
日常使用运行 `python run.py` 或双击 start.bat（不重载，只开一个进程）。
"""
import threading
import webbrowser

from app import app

HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"


def open_browser():
    webbrowser.open(URL)


if __name__ == "__main__":
    print(f"投递管理台已启动：{URL}")
    print("关闭窗口或按 Ctrl+C 停止服务")
    threading.Timer(1.2, open_browser).start()
    app.run(host=HOST, port=PORT, debug=False)
