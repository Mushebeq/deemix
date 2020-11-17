#!/usr/bin/env python3
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
from PyQt5.QtCore import QUrl, pyqtSignal
from PyQt5.QtGui import QIcon

import json
import webbrowser

from threading import Thread, Semaphore
import signal
import sys
from pathlib import Path
from os.path import sep as pathSep
from os import makedirs
from time import sleep
from server import run_server
from http.client import HTTPConnection
from deemix.utils.localpaths import getConfigFolder

if sys.platform == "win32":
    import ctypes
    myappid = 'RemixDev.deemix'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

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
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        profile.setPersistentStoragePath(str(configFolder / "QtWebEngine" / "Storage" / "OffTheRecord"))
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

class MainWindow(QMainWindow):
    selectDownloadFolder_trigger = pyqtSignal()
    appLogin_trigger = pyqtSignal()

    class MainWebpage(QWebEnginePage):
        def __init__(self, profile, parent):
            super().__init__(profile, parent)
            actions = [
                QWebEnginePage.Stop,
                QWebEnginePage.Reload,
                QWebEnginePage.ReloadAndBypassCache,
                QWebEnginePage.PasteAndMatchStyle,
                QWebEnginePage.OpenLinkInThisWindow,
                QWebEnginePage.OpenLinkInNewWindow,
                QWebEnginePage.OpenLinkInNewTab,
                QWebEnginePage.OpenLinkInNewBackgroundTab,
                QWebEnginePage.DownloadLinkToDisk,
                QWebEnginePage.DownloadImageToDisk,
                QWebEnginePage.DownloadMediaToDisk,
                QWebEnginePage.InspectElement,
                QWebEnginePage.RequestClose,
                QWebEnginePage.SavePage,
                QWebEnginePage.ViewSource
            ]
            for a in actions:
                self.action(a).setVisible(False)

        class ExternalWebpage(QWebEnginePage):
            def __init__(self, parent):
                super().__init__(parent)
                self.urlChanged.connect(self.open_browser)

            def open_browser(self, url):
                page = self.sender()
                webbrowser.open(url.toString(), 2, True)
                page.deleteLater()

        def createWindow(self, _type):
            page = None
            if _type == QWebEnginePage.WebBrowserTab:
                page = self.ExternalWebpage(self)
            return page

    def __init__(self, title, url, x=None, y=None, w=800, h=600):
        super().__init__()
        startMaximized = False
        if w == -1 or h == -1:
            self.resize(800, 600)
            startMaximized = True
        else:
            self.resize(w, h)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(str(appDir / 'icon.ico')))
        self.setMinimumSize(800, 600)
        self.webview = QWebEngineView()
        self.profile = QWebEngineProfile("Default", self.webview)
        self.profile.setCachePath(str(configFolder / "QtWebEngine" / "Cache" / "Default"))
        self.profile.setPersistentStoragePath(str(configFolder / "QtWebEngine" / "Storage" / "Default"))
        self.page = self.MainWebpage(self.profile, self.webview)
        self.page.loadFinished.connect(self.finishLoading)
        self.webview.setPage(self.page)
        self.setCentralWidget(self.webview)
        self.url = url

        if dev:
            self.dev_tools = QWebEngineView()
            self.webview.page().setDevToolsPage(self.dev_tools.page())
            self.dev_tools.show()

        self.downloadFolder = None
        self.selectDownloadFolder_trigger.connect(self.selectDownloadFolder)
        self._selectDownloadFolder_semaphore = Semaphore(0)

        self.arl = None
        self.appLogin_trigger.connect(self.appLogin)
        self._appLogin_semaphore = Semaphore(0)

        if x is None or y is None or startMaximized:
            center = QApplication.desktop().availableGeometry().center() - self.rect().center()
            self.move(center.x(), center.y())
        else:
            self.move(x, y)

        if startMaximized: self.showMaximized()

    def showWindow(self):
        self.webview.setUrl(QUrl(self.url))
        self.show()

    def selectDownloadFolder(self):
        filename = QFileDialog.getExistingDirectory(self, "Select Download Folder", options=QFileDialog.ShowDirsOnly)
        self.downloadFolder = filename.replace('/', pathSep)
        self._selectDownloadFolder_semaphore.release()

    def appLogin(self):
        self.arl = None
        loginWindow = LoginWindow(self)
        self.arl = loginWindow.arl
        self._appLogin_semaphore.release()
        loginWindow.page.deleteLater()
        loginWindow.webview.deleteLater()
        loginWindow.deleteLater()

    def closeEvent(self, event):
        x = int(self.x())
        y = int(self.y())
        w = int(self.width())
        h = int(self.height())
        if x < 0: x = 0
        if y < 0: y = 0
        if self.isMaximized():
            w = -1
            h = -1
        with open(configFolder / '.UIposition', 'w') as f:
            f.write("|".join([str(x),str(y),str(w),str(h)]))
        self.page.deleteLater()
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

def get_position():
    if (configFolder / '.UIposition').is_file():
        try:
            with open(configFolder / '.UIposition', 'r') as f:
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

url = "127.0.0.1"
port = 6595

def server_shutdown_handler(signalnum, frame):
    conn = HTTPConnection(url, port)
    conn.request('GET', '/shutdown')

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    portable = None
    appDir = Path(__file__).parent
    if '--portable' in sys.argv:
        portable = appDir / 'config'
    server = '--server' in sys.argv or '-s' in sys.argv
    dev = '--dev' in sys.argv

    if not server:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        app = QApplication([])
        configFolder = portable or getConfigFolder()
        x,y,w,h = get_position()
        makedirs(configFolder / "QtWebEngine", exist_ok=True)
        window = MainWindow('deemix', 'http://localhost:'+str(port), x,y,w,h)
        t = Thread(target=run_server, args=(url, port, portable, window))
    else:
        signal.signal(signal.SIGINT, server_shutdown_handler)
        signal.signal(signal.SIGTERM, server_shutdown_handler)
        t = Thread(target=run_server, args=(url, port, portable))
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
