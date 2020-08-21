#!/usr/bin/env python3
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
from PyQt5.QtCore import QUrl, pyqtSignal

import json

from threading import Thread, Lock, Semaphore
import sys
import os.path as path
from os import makedirs
from time import sleep
from server import run_server
from http.client import HTTPConnection
from deemix.utils.localpaths import getConfigFolder

server_lock = Lock()

class LoginWindow(QDialog):

    class CustomPage(QWebEnginePage):

        def acceptNavigationRequest(self, url, type, main):
            if url.toString() == "https://www.deezer.com/":
                url = QUrl('https://www.deezer.com/ajax/gw-light.php?method=user.getArl&input=3&api_version=1.0&api_token=null')
                self.setUrl(url)
                return False
            return super().acceptNavigationRequest(url, type, main)


    def __init__(self, parent):
        super().__init__(parent)
        self.webview = QWebEngineView()
        profile = QWebEngineProfile(self.webview)
        profile.clearHttpCache()
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.NoCache)
        self.page = self.CustomPage(profile, self.webview)
        self.page.loadFinished.connect(self.checkURL)
        self.webview.setPage(self.page)
        self.webview.setUrl(QUrl("https://deezer.com/login"))
        layout = QVBoxLayout()
        layout.addWidget(self.webview)
        self.setLayout(layout)
        self.arl = None
        self.exec_()

    def checkURL(self, ok):
        url = self.webview.url().toString()
        if 'user.getArl' in url:
            sleep(1)
            self.webview.page().toPlainText(self.saveARL)

    def saveARL(self, body):
        if body.startswith("{"):
            self.arl = json.loads(body)['results']
            self.accept()
            self.page = None
            self.webview = None

class MainWindow(QMainWindow):
    selectDownloadFolder_trigger = pyqtSignal()
    appLogin_trigger = pyqtSignal()

    def __init__(self, title, url, x=None, y=None, w=800, h=600):
        super().__init__()
        self.resize(w, h)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.webview = QWebEngineView()
        self.webview.page().loadFinished.connect(self.finishLoading)
        self.setCentralWidget(self.webview)
        self.url = url

        self.downloadFolder = None
        self.selectDownloadFolder_trigger.connect(self.selectDownloadFolder)
        self._selectDownloadFolder_semaphore = Semaphore(0)

        self.arl = None
        self.appLogin_trigger.connect(self.appLogin)
        self._appLogin_semaphore = Semaphore(0)

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
        self.downloadFolder = filename
        self._selectDownloadFolder_semaphore.release()

    def appLogin(self):
        loginWindow = LoginWindow(self)
        self.arl = loginWindow.arl
        self._appLogin_semaphore.release()
        loginWindow.deleteLater()

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
