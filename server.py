#!/usr/bin/env python3
import logging
import signal
import sys
from pathlib import Path
from os.path import sep as pathSep
import json

# Import needed to set all sequential requests import eventlet compatible
import eventlet
requests = eventlet.import_patched('requests')

from eventlet import tpool
from eventlet.green import subprocess

from flask import Flask, render_template, request, session, redirect, copy_current_request_context
from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix

from deezer import Deezer
from deemix import __version__ as deemix_version
from app import deemix, LoginStatus, resource_path
from deemix.app.messageinterface import MessageInterface

# Workaround for MIME type error in certain Windows installs
# https://github.com/pallets/flask/issues/1045#issuecomment-42202749
import mimetypes
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/javascript', '.js')

# Makes engineio accept more packets from client, needed for long URL lists in addToQueue requests
# https://github.com/miguelgrinberg/python-engineio/issues/142#issuecomment-545807047
from engineio.payload import Payload
Payload.max_decode_packets = 500

# Disable logging
serverLog = logging.getLogger('werkzeug')
serverLog.disabled = True
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)
#server.logger.disabled = True

class SocketInterface(MessageInterface):
    def send(self, message, value=None):
        if value:
            socketio.emit(message, value)
        else:
            socketio.emit(message)

# This allows the frontend to use vue.js
class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        block_start_string='$$',
        block_end_string='$$',
        variable_start_string='$',
        variable_end_string='$',
        comment_start_string='$#',
        comment_end_string='#$',
    ))

# Retrocompatibility with old versions of the app
# Check for public folder and fallback to webui
GUI_DIR = resource_path(f'webui{pathSep}public')
if not GUI_DIR.exists():
    GUI_DIR = resource_path('webui')
if not (GUI_DIR / 'index.html').is_file():
    sys.exit("WebUI not found, please download and add a WebUI")

server = CustomFlask(__name__, static_folder=str(GUI_DIR), template_folder=str(GUI_DIR), static_url_path="")
server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1  # disable caching
socketio = SocketIO(server)
server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1)

app = None
gui = None
arl = None

socket_interface = SocketInterface()
first_connection = True

def shutdown():
    print("Shutting down server")
    if app is not None:
        app.shutdown(socket_interface)
    socketio.stop()

@server.route('/')
def landing():
    return render_template('index.html')

@server.errorhandler(404)
def not_found_handler(e):
    return redirect("/")

@server.route('/shutdown')
def closing():
    shutdown()
    return 'Server Closed'

@socketio.on('connect')
def on_connect():
    session['dz'] = Deezer()
    (settings, spotifyCredentials, defaultSettings) = app.getAllSettings()
    session['dz'].set_accept_language(settings.get('tagsLanguage'))
    emit('init_settings', (settings, spotifyCredentials, defaultSettings))

    if first_connection:
        app.checkForUpdates()
        app.checkDeezerAvailability()

    emit('init_update',{
            'currentCommit': app.currentVersion,
            'latestCommit': app.latestVersion,
            'updateAvailable': app.updateAvailable,
            'deemixVersion': deemix_version
        }
    )

    if arl:
        login(arl)
    else:
        emit('init_autologin')

    queue, queueComplete, queueList, currentItem = app.initDownloadQueue()
    if len(queueList.keys()):
        emit('init_downloadQueue',{
            'queue': queue,
            'queueComplete': queueComplete,
            'queueList': queueList,
            'currentItem': currentItem
        })

    #emit('init_home', app.get_home(session['dz']))
    #emit('init_charts', app.get_charts(session['dz']))

    if app.updateAvailable: emit('updateAvailable')
    if not app.isDeezerAvailable: emit('deezerNotAvailable')

@socketio.on('get_home_data')
def get_home_data():
    emit('init_home', app.get_home(session['dz']))

@socketio.on('get_charts_data')
def get_charts_data():
    emit('init_charts', app.get_charts(session['dz']))

@socketio.on('get_favorites_data')
def get_favorites_data():
    emit('init_favorites', app.getUserFavorites(session['dz']))

@socketio.on('get_settings_data')
def get_settings_data():
    emit('init_settings', app.getAllSettings())

@socketio.on('login')
def login(arl, force=False, child=0):
    global first_connection

    if not app.isDeezerAvailable:
        emit('logged_in', {'status': LoginStatus.NOT_AVAILABLE, 'arl': arl, 'user': session['dz'].current_user})
        return

    if child == None: child = 0
    arl = arl.strip()
    emit('logging_in')

    if force: session['dz'] = Deezer()
    result = app.login(session['dz'], arl, int(child))
    if force and result == LoginStatus.SUCCESS: result = LoginStatus.FORCED_SUCCESS

    emit('logged_in', {'status': result, 'arl': arl, 'user': session['dz'].current_user})
    if first_connection and result in [LoginStatus.SUCCESS, LoginStatus.FORCED_SUCCESS]:
        first_connection = False
        app.restoreDownloadQueue(session['dz'], socket_interface)
    if result != 0:
        emit('familyAccounts', session['dz'].childs)
        emit('init_favorites', app.getUserFavorites(session['dz']))

@socketio.on('changeAccount')
def changeAccount(child):
    emit('accountChanged', session['dz'].change_account(int(child)))
    emit('init_favorites', app.getUserFavorites(session['dz']))

@socketio.on('logout')
def logout():
    if session['dz'].logged_in:
        session['dz'] = Deezer()
    emit('logged_out')

@socketio.on('mainSearch')
def mainSearch(data):
    if data['term'].strip() != "":
        result = app.mainSearch(session['dz'], data['term'])
        result['ack'] = data.get('ack')
        emit('mainSearch', result)

@socketio.on('search')
def search(data):
    if data['term'].strip() != "":
        result = app.search(session['dz'], data['term'], data['type'], data['start'], data['nb'])
        result['type'] = data['type']
        result['ack'] = data.get('ack')
        emit('search', result)

@socketio.on('albumSearch')
def albumSearch(data):
    if data['term'].strip() != "":
        albums = app.searchAlbum(session['dz'], data['term'], data['start'], data['nb'])
        output = {
            'data': albums,
            'total': len(albums),
            'ack': data.get('ack')
        };
        emit('albumSearch', output)

@socketio.on('newReleases')
def newReleases(data):
    result = app.newReleases(session['dz'])
    output = {
        'data': result,
        'total': len(result),
        'ack': data.get('ack')
    };
    emit('newReleases', output)

@socketio.on('queueRestored')
def queueRestored():
    app.queueRestored(session['dz'], socket_interface)

@socketio.on('addToQueue')
def addToQueue(data):
    result = app.addToQueue(session['dz'], data['url'], data['bitrate'], interface=socket_interface, ack=data.get('ack'))

@socketio.on('removeFromQueue')
def removeFromQueue(uuid):
    app.removeFromQueue(uuid, interface=socket_interface)

@socketio.on('removeFinishedDownloads')
def removeFinishedDownloads():
    app.removeFinishedDownloads(interface=socket_interface)

@socketio.on('cancelAllDownloads')
def cancelAllDownloads():
    app.cancelAllDownloads(interface=socket_interface)

@socketio.on('saveSettings')
def saveSettings(settings, spotifyCredentials, spotifyUser):
    app.saveSettings(settings, session['dz'])
    app.setSpotifyCredentials(spotifyCredentials)
    socketio.emit('updateSettings', (settings, spotifyCredentials))
    if spotifyUser != False:
        emit('updated_userSpotifyPlaylists', app.updateUserSpotifyPlaylists(spotifyUser))

@socketio.on('getTracklist')
def getTracklist(data):
    emit('show_'+data['type'], app.getTracklist(session['dz'], data))

@socketio.on('analyzeLink')
def analyzeLink(link):
    (type, data) = app.analyzeLink(session['dz'], link)
    if len(data):
        emit('analyze_'+type, data)
    else:
        emit('analyze_notSupported')

@socketio.on('getChartTracks')
def getChartTracks(id):
    emit('setChartTracks', session['dz'].api.get_playlist_tracks(id)['data'])

@socketio.on('update_userFavorites')
def update_userFavorites():
    emit('updated_userFavorites', app.getUserFavorites(session['dz']))

@socketio.on('update_userSpotifyPlaylists')
def update_userSpotifyPlaylists(spotifyUser):
    if spotifyUser != False:
        emit('updated_userSpotifyPlaylists', app.updateUserSpotifyPlaylists(spotifyUser))

@socketio.on('update_userPlaylists')
def update_userPlaylists():
    emit('updated_userPlaylists', app.updateUserPlaylists(session['dz']))

@socketio.on('update_userAlbums')
def update_userAlbums():
    emit('updated_userAlbums', app.updateUserAlbums(session['dz']))

@socketio.on('update_userArtists')
def update_userArtists():
    emit('updated_userArtists', app.updateUserArtists(session['dz']))

@socketio.on('update_userTracks')
def update_userTracks():
    emit('updated_userTracks', app.updateUserTracks(session['dz']))

@socketio.on('openDownloadsFolder')
def openDownloadsFolder():
    folder = app.getDownloadFolder()
    if sys.platform == 'darwin':
        subprocess.check_call(['open', folder])
    elif sys.platform == 'linux':
        subprocess.check_call(['xdg-open', folder])
    elif sys.platform == 'win32':
        subprocess.check_call(['explorer', folder])

@socketio.on('selectDownloadFolder')
def selectDownloadFolder():
    if gui:
        # Must be done with tpool to avoid blocking the greenthread
        result = tpool.execute(doSelectDowloadFolder)
        if result:
            emit('downloadFolderSelected', result)
    else:
        print("Can't open folder selection, you're not running the gui")

def doSelectDowloadFolder():
    gui.selectDownloadFolder_trigger.emit()
    gui._selectDownloadFolder_semaphore.acquire()
    return gui.downloadFolder

@socketio.on('applogin')
def applogin():
    if gui:
        if not session['dz'].logged_in:
            # Must be done with tpool to avoid blocking the greenthread
            arl = tpool.execute(dologin)
            if arl:
                emit('applogin_arl', arl)
        else:
            emit('logged_in', {'status': 2, 'user': session['dz'].current_user})
    else:
        print("Can't open login page, you're not running the gui")

def dologin():
    gui.appLogin_trigger.emit()
    gui._appLogin_semaphore.acquire()
    return gui.arl

def run_server(host="127.0.0.1", port=6595, portable=None, guiWindow=None, server_arl=False):
    global app, gui, arl
    app = deemix(portable)
    gui = guiWindow
    if server_arl:
        print("Server-wide ARL enabled.")
        arl = app.getConfigArl()
    print("Starting server at http://" + host + ":" + str(port))
    try:
        socketio.run(server, host=host, port=port)
    except UnicodeDecodeError as e:
        print(str(e))
        print("A workaround for this issue is to remove all non roman characters from the computer name")
        print("More info here: https://bugs.python.org/issue26227")

def shutdown_handler(signalnum, frame):
    shutdown()

if __name__ == '__main__':
    host = "127.0.0.1"
    port = 6595
    if len(sys.argv) >= 2:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    portable = None
    if '--portable' in sys.argv:
        portable = Path(__file__).parent / 'config'
    if '--host' in sys.argv:
        host = str(sys.argv[sys.argv.index("--host")+1])
    serverwide_arl = "--serverwide-arl" in sys.argv

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    run_server(host, port, portable, server_arl=serverwide_arl)
