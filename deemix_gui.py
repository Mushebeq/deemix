#!/usr/env/bin python3
import webview

from threading import Thread, Lock
import sys
import os.path as path
from time import sleep
from server import run_server
from http.client import HTTPConnection
from deemix.utils.localpaths import getConfigFolder

server_lock = Lock()

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
    x = window.x
    y = window.y
    w = window.width
    h = window.height
    with open(path.join(configFolder, '.UIposition'), 'w') as f:
        f.write("|".join([str(x),str(y),str(w),str(h)]))

if __name__ == '__main__':
    url = "127.0.0.1"
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
    else:
        port = 9666
    t = Thread(target=run_server, args=(port, ))
    t.daemon = True
    t.start()

    while not url_ok(url, port):
        sleep(1)
    configFolder = getConfigFolder()

    if path.isfile(path.join(configFolder, '.UIposition')):
        try:
            with open(path.join(configFolder, '.UIposition'), 'r') as f:
                (x,y,w,h) = f.read().strip().split("|")
            x = int(x)
            y = int(y)
            w = int(w)
            h = int(h)
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
    window = webview.create_window('deemix', 'http://'+url+':'+str(port),
        confirm_close=True, x=x, y=y, width=w, height=h)
    window.closing += save_position
    if sys.platform == "win32":
        from webview.platforms.cef import settings
        settings.update({
            'persist_session_cookies': True,
            'cache_path': configFolder
        })
        webview.start(gui='cef', debug=True)
    else:
        webview.start(debug=True)
    conn = HTTPConnection(url, port)
    conn.request('GET', '/shutdown')
    t.join()
