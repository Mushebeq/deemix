#!/usr/env/bin python3
import logging
import os
import sys
from os import path

from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit

import app
from deemix.api.deezer import Deezer
from deemix.app.MessageInterface import MessageInterface
from deemix.utils import localpaths

# Workaround for MIME type error in certain Windows installs
# https://github.com/pallets/flask/issues/1045#issuecomment-42202749
import mimetypes
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/javascript', '.js')

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

serverwide_arl = "--serverwide-arl" in sys.argv
if serverwide_arl:
    print("Server-wide ARL enabled.")

@socketio.on('connect')
def on_connect():
    session['dz'] = Deezer()
    settings = app.getSettings_link()
    spotifyCredentials = app.getSpotifyCredentials()
    defaultSettings = app.getDefaultSettings_link()
    emit('init_settings', (settings, spotifyCredentials, defaultSettings))

    arl_file_path = path.join(localpaths.getConfigFolder(), '.arl')
    if serverwide_arl and path.isfile(arl_file_path):
        with open(arl_file_path, 'r') as file:
            arl = file.read()
            login(arl)

    queue, queueComplete, queueList, currentItem = app.getQueue_link()
    emit('init_downloadQueue',
         {'queue': queue, 'queueComplete': queueComplete, 'queueList': queueList, 'currentItem': currentItem})
    emit('init_home', session['dz'].get_charts())
    emit('init_charts', app.get_charts(session['dz']))


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
def saveSettings(settings, spotifyCredentials, spotifyUser):
    app.saveSettings_link(settings)
    app.setSpotifyCredentials(spotifyCredentials)
    socketio.emit('updateSettings', (settings, spotifyCredentials))
    if spotifyUser != False:
        emit('updated_userSpotifyPlaylists', app.updateUserSpotifyPlaylists(spotifyUser))


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
    (type, data) = app.analyzeLink(session['dz'], link)
    emit('analyze_'+type, data)

@socketio.on('getChartTracks')
def getChartTracks(id):
    emit('setChartTracks', session['dz'].get_playlist_tracks(id)['data'])

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

def run_server(port):
    print("Starting server at http://127.0.0.1:" + str(port))
    socketio.run(server, host='0.0.0.0', port=port)


if __name__ == '__main__':
    port = 33333
    if len(sys.argv) >= 2:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
