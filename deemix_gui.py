#!/usr/env/bin python3
import webview

from threading import Thread, Lock
import sys
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

    window = webview.create_window('deemix', 'http://'+url+':'+str(port))
    if sys.platform == "win32":
        from webview.platforms.cef import settings
        settings.update({
            'persist_session_cookies': True,
            'cache_path': getConfigFolder()
        })
        webview.start(gui='cef', debug=True)
    else:
        webview.start(debug=True)
    conn = HTTPConnection(url, port)
    conn.request('GET', '/shutdown')
    t.join()
