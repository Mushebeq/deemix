#!/usr/bin/env python3
import logging
import sys
import subprocess
from os import path
import json
import requests
from urllib.request import urlopen

from flask import Flask, render_template, request, session, redirect, copy_current_request_context
from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix

from deemix import __version__ as deemixVersion
from app import deemix
from deemix.api.deezer import Deezer
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

app = None
gui = None
arl = None

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

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.dirname(path.abspath(path.realpath(__file__)))

    return path.join(base_path, relative_path)

gui_dir = resource_path(path.join('webui', 'public'))
if not path.exists(gui_dir):
    gui_dir = resource_path('webui')
if not path.isfile(path.join(gui_dir, 'index.html')):
    sys.exit("WebUI not found, please download and add a WebUI")
server = CustomFlask(__name__, static_folder=gui_dir, template_folder=gui_dir, static_url_path="")
server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1  # disable caching
socketio = SocketIO(server, async_mode='threading')
server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1)

class SocketInterface(MessageInterface):
    def send(self, message, value=None):
        if value:
            socketio.emit(message, value)
        else:
            socketio.emit(message)


socket_interface = SocketInterface()
loginWindow = False

serverLog = logging.getLogger('werkzeug')
serverLog.disabled = True
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)
#server.logger.disabled = True

firstConnection = True
appDir = path.dirname(path.realpath(__file__))

currentCommit = None
latestCommit = None
updateAvailable = False

def check_for_updates():
    global currentCommit, latestCommit, updateAvailable
    if path.isfile(path.join(appDir, 'commit.txt')):
        print("Checking for updates...")
        with open(path.join(appDir, 'commit.txt'), 'r') as f:
            currentCommit = f.read().strip()
        latestCommit = requests.get("https://deemix.app/pyweb/latest").text.strip()
        updateAvailable = currentCommit != latestCommit
        if updateAvailable:
            print("Update available! Commit: "+latestCommit)
        else:
            print("You're running the latest version")

@server.route('/')
def landing():
    return render_template('index.html')

@server.errorhandler(404)
def not_found_handler(e):
    return redirect("/")

@server.route('/shutdown')
def closing():
    app.shutdown(interface=socket_interface)
    socketio.stop()
    return 'Server Closed'

serverwide_arl = "--serverwide-arl" in sys.argv
if serverwide_arl:
    print("Server-wide ARL enabled.")

@socketio.on('connect')
def on_connect():
    session['dz'] = Deezer()
    settings = app.getSettings()
    spotifyCredentials = app.getSpotifyCredentials()
    defaultSettings = app.getDefaultSettings()
    emit('init_settings', (settings, spotifyCredentials, defaultSettings))
    emit('init_update',
        {'currentCommit': currentCommit,
        'latestCommit': latestCommit,
        'updateAvailable': updateAvailable,
        'deemixVersion': deemixVersion}
    )

    if serverwide_arl:
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
    emit('init_home', session['dz'].get_charts())
    emit('init_charts', app.get_charts(session['dz']))

@socketio.on('get_home_data')
def get_home_data():
    emit('init_home', app.get_home(session['dz']))

@socketio.on('get_charts_data')
def get_charts_data():
    emit('init_charts', app.get_charts(session['dz']))

@socketio.on('login')
def login(arl, force=False, child=0):
    global firstConnection
    if child == None:
        child = 0
    arl = arl.strip()
    emit('logging_in')
    if not session['dz'].logged_in:
        result = session['dz'].login_via_arl(arl, int(child))
    else:
        if force:
            session['dz'] = Deezer()
            result = session['dz'].login_via_arl(arl, int(child))
            if result == 1:
                result = 3
        else:
            result = 2
    emit('logged_in', {'status': result, 'arl': arl, 'user': session['dz'].user})
    if firstConnection and result in [1, 3]:
        firstConnection = False
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
    status = 0
    if session['dz'].logged_in:
        session['dz'] = Deezer()
        status = 0
    else:
        status = 1
    emit('logged_out', status)


@socketio.on('mainSearch')
def mainSearch(data):
    if data['term'].strip() != "":
        emit('mainSearch', app.mainSearch(session['dz'], data['term']))


@socketio.on('search')
def search(data):
    if data['term'].strip() != "":
        result = app.search(session['dz'], data['term'], data['type'], data['start'], data['nb'])
        result['type'] = data['type']
        emit('search', result)


@socketio.on('queueRestored')
def queueRestored():
    app.queueRestored(session['dz'], socket_interface)


@socketio.on('addToQueue')
def addToQueue(data):
    result = app.addToQueue(session['dz'], data['url'], data['bitrate'], interface=socket_interface)
    if result == "Not logged in":
        emit('loginNeededToDownload')


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
    app.saveSettings(settings)
    app.setSpotifyCredentials(spotifyCredentials)
    socketio.emit('updateSettings', (settings, spotifyCredentials))
    if spotifyUser != False:
        emit('updated_userSpotifyPlaylists', app.updateUserSpotifyPlaylists(spotifyUser))


@socketio.on('getTracklist')
def getTracklist(data):
    if data['type'] == 'artist':
        artistAPI = session['dz'].get_artist(data['id'])
        artistAPI['releases'] = session['dz'].get_artist_discography_gw(data['id'], 100)
        emit('show_artist', artistAPI)
    elif data['type'] == 'spotifyplaylist':
        playlistAPI = app.getSpotifyPlaylistTracklist(data['id'])
        for i in range(len(playlistAPI['tracks'])):
            playlistAPI['tracks'][i] = playlistAPI['tracks'][i]['track']
            playlistAPI['tracks'][i]['selected'] = False
        emit('show_spotifyplaylist', playlistAPI)
    else:
        releaseAPI = getattr(session['dz'], 'get_' + data['type'])(data['id'])
        releaseTracksAPI = getattr(session['dz'], 'get_' + data['type'] + '_tracks')(data['id'])['data']
        tracks = []
        showdiscs = False
        if data['type'] == 'album' and len(releaseTracksAPI) and releaseTracksAPI[-1]['disk_number'] != 1:
            current_disk = 0
            showdiscs = True
        for track in releaseTracksAPI:
            if showdiscs and int(track['disk_number']) != current_disk:
                current_disk = int(track['disk_number'])
                tracks.append({'type': 'disc_separator', 'number': current_disk})
            track['selected'] = False
            tracks.append(track)
        releaseAPI['tracks'] = tracks
        emit('show_' + data['type'], releaseAPI)

@socketio.on('analyzeLink')
def analyzeLink(link):
    if 'deezer.page.link' in link:
        link = urlopen(link).url
    (type, data) = app.analyzeLink(session['dz'], link)
    if len(data):
        emit('analyze_'+type, data)
    else:
        emit('analyze_notSupported')

@socketio.on('getChartTracks')
def getChartTracks(id):
    emit('setChartTracks', session['dz'].get_playlist_tracks(id)['data'])

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
        gui.selectDownloadFolder_trigger.emit()
        gui._selectDownloadFolder_semaphore.acquire()
        result = gui.downloadFolder
        if result:
            emit('downloadFolderSelected', result)
    else:
        print("Can't open folder selection, you're not running the gui")

@socketio.on('applogin')
def applogin():
    if gui:
        if not session['dz'].logged_in:
            gui.appLogin_trigger.emit()
            gui._appLogin_semaphore.acquire()
            if gui.arl:
                emit('applogin_arl', gui.arl)
                gui.arl = None
        else:
            emit('logged_in', {'status': 2, 'user': session['dz'].user})
    else:
        print("Can't open login page, you're not running the gui")

def run_server(port, host="127.0.0.1", portable=None, mainWindow=None):
    global app, gui, arl
    app = deemix(portable)
    gui = mainWindow
    if serverwide_arl:
        arl = app.getConfigArl()
    check_for_updates()
    print("Starting server at http://" + host + ":" + str(port))
    socketio.run(server, host=host, port=port)


if __name__ == '__main__':
    port = 6595
    host = "127.0.0.1"
    portable = None
    if len(sys.argv) >= 2:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    if '--portable' in sys.argv:
        portable = path.join(path.dirname(path.realpath(__file__)), 'config')
    if '--host' in sys.argv:
        host = str(sys.argv[sys.argv.index("--host")+1])
    run_server(port, host, portable)
