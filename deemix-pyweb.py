#!/usr/bin/env python3
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl

from threading import Thread, Lock
import sys
import os.path as path
from os import makedirs
from time import sleep
from server import run_server
from http.client import HTTPConnection
from deemix.utils.localpaths import getConfigFolder

server_lock = Lock()

class MainWindow(QMainWindow):
    def __init__(self, title, url, x=None, y=None, w=800, h=600):
        super().__init__()
        self.resize(w, h)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.webview = QWebEngineView()
        self.webview.page().loadFinished.connect(self.finishLoading)
        self.setCentralWidget(self.webview)
        self.url = url

        if x is not None and y is not None:
            self.move(x, y)
        else:
            center = QApplication.desktop().availableGeometry().center() - self.rect().center()
            self.move(center.x(), center.y())

    def showWindow(self):
        self.webview.setUrl(QUrl(self.url))
        self.show()

    def selectDownloadFolder(self):
        filename = QFileDialog.getExistingDirectory(self, "Select Download Folder", options=QFileDialog.ShowDirsOnly)
        return filename

    def closeEvent(self, event):
        x = int(self.x())
        y = int(self.y())
        w = int(self.width())
        h = int(self.height())
        if x < 0: x = 0
        if y < 0: y = 0
        with open(path.join(configFolder, '.UIposition'), 'w') as f:
            f.write("|".join([str(x),str(y),str(w),str(h)]))
        event.accept()

    def finishLoading(self, ok):
        if ok: self.webview.page().runJavaScript("window.dispatchEvent(new Event('pywebviewready'))")

def url_ok(url, port):
    try:
        conn = HTTPConnection(url, port)
        conn.request('GET', '/')
        r = conn.getresponse()
        return r.status == 200
    except:
        print("Server not started")
        return False

def save_position():
    window = webview.windows[0]
    x = int(window.x)
    y = int(window.y)
    w = int(window.width)
    h = int(window.height)
    if x < 0: x = 0
    if y < 0: y = 0
    with open(path.join(configFolder, '.UIposition'), 'w') as f:
        f.write("|".join([str(x),str(y),str(w),str(h)]))

def get_position():
    if path.isfile(path.join(configFolder, '.UIposition')):
        try:
            with open(path.join(configFolder, '.UIposition'), 'r') as f:
                (x,y,w,h) = f.read().strip().split("|")
            x = int(x)
            y = int(y)
            w = int(w)
            h = int(h)
            if x < 0: x = 0
            if y < 0: y = 0
        except:
            x = None
            y = None
            w = 800
            h = 600
    else:
        x = None
        y = None
        w = 800
        h = 600
    return (x,y,w,h)

if __name__ == '__main__':
    url = "127.0.0.1"
    port = 6595
    if len(sys.argv) >= 2:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    portable = None
    server = False
    if '--portable' in sys.argv:
        portable = path.join(path.dirname(path.realpath(__file__)), 'config')
    if '--server' in sys.argv or '-s' in sys.argv:
        server = True

    if not server:
        configFolder = portable or getConfigFolder()
        x,y,w,h = get_position()
        app = QApplication([])
        window = MainWindow('deemix', 'http://'+url+':'+str(port), x,y,w,h)
        t = Thread(target=run_server, args=(port, url, portable, window))
    else:
        t = Thread(target=run_server, args=(port, url, portable))
    t.daemon = True
    t.start()

    if not server:
        while not url_ok(url, port):
            sleep(1)
        window.showWindow()
        app.exec_()
        conn = HTTPConnection(url, port)
        conn.request('GET', '/shutdown')
    t.join()
