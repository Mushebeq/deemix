import logging
import os
import sys

from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit

import app
from deemix.api.deezer import Deezer
from deemix.app.MessageInterface import MessageInterface


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


gui_dir = os.path.join(os.path.dirname(__file__), 'public')  # development path
if not os.path.exists(gui_dir):  # frozen executable path
    gui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
server = CustomFlask(__name__, static_folder=gui_dir, template_folder=gui_dir)
server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1  # disable caching
socketio = SocketIO(server)


class SocketInterface(MessageInterface):
    def send(self, message, value=None):
        if value:
            socketio.emit(message, value)
        else:
            socketio.emit(message)


socket_interface = SocketInterface()

serverLog = logging.getLogger('werkzeug')
serverLog.disabled = True
server.logger.disabled = True

app.initialize()


@server.route('/')
def landing():
    return render_template('index.html')


@server.route('/shutdown')
def closing():
    app.shutdown(interface=socket_interface)
    func = request.environ.get('werkzeug.server.shutdown')
    func()
    return 'server closed'


@socketio.on('connect')
def on_connect():
    session['dz'] = Deezer()
    settings = app.getSettings_link()
    spotifyCredentials = app.getSpotifyCredentials()
    emit('init_settings', (settings, spotifyCredentials))
    queue, queueComplete, queueList, currentItem = app.getQueue_link()
    emit('init_downloadQueue',
         {'queue': queue, 'queueComplete': queueComplete, 'queueList': queueList, 'currentItem': currentItem})
    emit('init_home', session['dz'].get_charts())


@socketio.on('login')
def login(arl, force=False):
    emit('toast', {'msg': "Logging in...", 'icon': 'loading', 'dismiss': False, 'id': "login-toast"})
    if not session['dz'].logged_in:
        result = session['dz'].login_via_arl(arl)
    else:
        if force:
            session['dz'] = Deezer()
            result = session['dz'].login_via_arl(arl)
            if result == 1:
                result = 3
        else:
            result = 2
    emit('logged_in', {'status': result, 'arl': arl, 'user': app.getUser(session['dz'])})


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
    emit('mainSearch', app.mainSearch(session['dz'], data['term']))


@socketio.on('search')
def search(data):
    result = app.search(session['dz'], data['term'], data['type'], data['start'], data['nb'])
    result['type'] = data['type']
    emit('search', result)


@socketio.on('addToQueue')
def addToQueue(data):
    result = app.addToQueue_link(session['dz'], data['url'], data['bitrate'], interface=socket_interface)
    if result == "Not logged in":
        emit('toast', {'msg': "You need to log in to download tracks!", 'icon': 'report'})


@socketio.on('removeFromQueue')
def removeFromQueue(uuid):
    app.removeFromQueue_link(uuid, interface=socket_interface)


@socketio.on('removeFinishedDownloads')
def removeFinishedDownloads():
    app.removeFinishedDownloads_link(interface=socket_interface)


@socketio.on('cancelAllDownloads')
def cancelAllDownloads():
    app.cancelAllDownloads_link(interface=socket_interface)


@socketio.on('saveSettings')
def saveSettings(settings, spotifyCredentials):
    app.saveSettings_link(settings)
    app.setSpotifyCredentials(spotifyCredentials)
    socketio.emit('updateSettings', (settings, spotifyCredentials))


@socketio.on('getTracklist')
def getTracklist(data):
    if data['type'] == 'artist':
        artistAPI = session['dz'].get_artist(data['id'])
        artistAlbumsAPI = session['dz'].get_artist_albums(data['id'])['data']
        tracksData = {'all': []}
        for release in artistAlbumsAPI:
            if not release['record_type'] in tracksData:
                tracksData[release['record_type']] = []
            tracksData[release['record_type']].append(release)
            tracksData['all'].append(release)
        artistAPI['releases'] = tracksData
        emit('show_artist', artistAPI)
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
    (type, data) = app.analyzeLink(session['dz'], link)
    emit('analyze_'+type, data)

def run_server(port):
    print("Starting server at http://127.0.0.1:" + str(port))
    socketio.run(server, host='0.0.0.0', port=port)


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
    else:
        port = 33333
    run_server(port)
