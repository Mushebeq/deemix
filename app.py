#!/usr/bin/env python3
import eventlet
requests = eventlet.import_patched('requests')

from deemix.api.deezer import Deezer
from deemix.app.settings import Settings
from deemix.app.queuemanager import QueueManager
from deemix.app.spotifyhelper import SpotifyHelper, emptyPlaylist as emptySpotifyPlaylist

from deemix.utils import getTypeFromLink, getIDFromLink
from deemix.utils.localpaths import getConfigFolder

import os.path as path
import json

from datetime import datetime

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.dirname(path.abspath(path.realpath(__file__)))

    return path.join(base_path, relative_path)

class LoginStatus():
    """Login status codes"""

    NOT_AVAILABLE = -1
    """Deezer is not Available in your country"""

    FAILED = 0
    """Login Failed"""

    SUCCESS = 1
    """Login Successfull"""

    ALREADY_LOGGED = 2
    """Already logged in"""

    FORCED_SUCCESS = 3
    """Forced Login Successfull"""

class deemix:
    def __init__(self, portable):
        self.configFolder = portable or getConfigFolder()
        self.set = Settings(self.configFolder)
        self.sp = SpotifyHelper(self.configFolder)
        self.qm = QueueManager(self.sp)

        self.chartsList = []
        self.homeCache = None

        self.currentVersion = None
        self.latestVersion = None
        self.updateAvailable = False
        self.isDeezerAvailable = True

    def checkForUpdates(self):
        commitFile = resource_path('version.txt')
        if path.isfile(commitFile):
            print("Checking for updates...")
            with open(commitFile, 'r') as f:
                self.currentVersion = f.read().strip()
            try:
                latestVersion = requests.get("https://deemix.app/pyweb/latest")
                latestVersion.raise_for_status()
                self.latestVersion = latestVersion.text.strip()
            except:
                self.latestVersion = None
            self.updateAvailable = self.compareVersions()
            if self.updateAvailable:
                print("Update available! Commit: "+self.latestVersion)
            else:
                print("You're running the latest version")

    def compareVersions(self):
        if not self.latestVersion or not self.currentVersion:
            return False
        (currentDate, currentCommit) = tuple(self.currentVersion.split('-'))
        (latestDate, latestCommit) = tuple(self.latestVersion.split('-'))
        currentDate = currentDate.split('.')
        latestDate = latestDate.split('.')
        current = datetime(int(currentDate[0]), int(currentDate[1]), int(currentDate[2]))
        latest = datetime(int(latestDate[0]), int(latestDate[1]), int(latestDate[2]))
        if latest > current:
            return True
        elif latest == current:
            return latestCommit != currentCommit
        else:
             return False

    def checkDeezerAvailability(self):
        body = requests.get("https://www.deezer.com/", headers={'Cookie': 'dz_lang=en; Domain=deezer.com; Path=/; Secure; hostOnly=false;'}).text
        title = body[body.find('<title>')+7:body.find('</title>')]
        self.isDeezerAvailable = title.strip() != "Deezer will soon be available in your country."

    def shutdown(self, interface=None):
        if self.set.settings['saveDownloadQueue']:
            self.qm.saveQueue(self.configFolder)
        self.qm.cancelAllDownloads(interface)
        if interface:
            interface.send("toast", {'msg': "Server is closed."})

    def getConfigArl(self):
        tempDeezer = Deezer()
        arl = None
        if path.isfile(path.join(self.configFolder, '.arl')):
            with open(path.join(self.configFolder, '.arl'), 'r') as f:
                arl = f.readline().rstrip("\n")
        if not arl or not tempDeezer.login_via_arl(arl):
            while True:
                arl = input("Paste here your arl:")
                if tempDeezer.login_via_arl(arl):
                    break
            with open(path.join(self.configFolder, '.arl'), 'w') as f:
                f.write(arl)
        return arl

    def login(self, dz, arl, child):
        if not dz.logged_in:
            return int(dz.login_via_arl(arl, child))
        else:
            return LoginStatus.ALREADY_LOGGED

    def restoreDownloadQueue(self, dz, interface=None):
        self.qm.loadQueue(self.configFolder, self.set.settings, interface)

    def queueRestored(self, dz, interface=None):
        self.qm.nextItem(dz, interface)

    def get_charts(self, dz):
        if len(self.chartsList) == 0:
            temp = dz.get_charts_countries()
            countries = []
            for i in range(len(temp)):
                countries.append({
                    'title': temp[i]['title'].replace("Top ", ""),
                    'id': temp[i]['id'],
                    'picture_small': temp[i]['picture_small'],
                    'picture_medium': temp[i]['picture_medium'],
                    'picture_big': temp[i]['picture_big']
                })
            self.chartsList = countries
        return self.chartsList

    def get_home(self, dz):
        if not self.homeCache:
            self.homeCache = dz.get_charts()
        return self.homeCache

    def getDownloadFolder(self):
        return self.set.settings['downloadLocation']

    def getTracklist(self, dz, data):
        if data['type'] == 'artist':
            artistAPI = dz.get_artist(data['id'])
            artistAPI['releases'] = dz.get_artist_discography_gw(data['id'], 100)
            return artistAPI
        elif data['type'] == 'spotifyplaylist':
            playlistAPI = self.getSpotifyPlaylistTracklist(data['id'])
            for i in range(len(playlistAPI['tracks'])):
                playlistAPI['tracks'][i] = playlistAPI['tracks'][i]['track']
                playlistAPI['tracks'][i]['selected'] = False
            return playlistAPI
        else:
            releaseAPI = getattr(dz, 'get_' + data['type'])(data['id'])
            releaseTracksAPI = getattr(dz, 'get_' + data['type'] + '_tracks')(data['id'])['data']
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
            return releaseAPI

    def getUserFavorites(self, dz):
        result = {}
        if dz.logged_in:
            user_id = dz.user['id']
            try:
                result['playlists'] = dz.get_user_playlists(user_id)['data']
                result['albums'] = dz.get_user_albums(user_id)['data']
                result['artists'] = dz.get_user_artists(user_id)['data']
                result['tracks'] = dz.get_user_tracks(user_id)['data']
            except:
                result['playlists'] = dz.get_user_playlists_gw(user_id)
                result['albums'] = dz.get_user_albums_gw(user_id)
                result['artists'] = dz.get_user_artists_gw(user_id)
                result['tracks'] = dz.get_user_tracks_gw(user_id)
        return result

    def updateUserSpotifyPlaylists(self, user):
        if user == "" or not self.sp.spotifyEnabled:
            return []
        try:
            return self.sp.get_user_playlists(user)
        except:
            return []

    def updateUserPlaylists(self, dz):
        user_id = dz.user['id']
        try:
            return dz.get_user_playlists(user_id)['data']
        except:
            return dz.get_user_playlists_gw(user_id)

    def updateUserAlbums(self, dz):
        user_id = dz.user['id']
        try:
            return dz.get_user_albums(user_id)['data']
        except:
            return dz.get_user_albums_gw(user_id)

    def updateUserArtists(self, dz):
        user_id = dz.user['id']
        try:
            return dz.get_user_artists(user_id)['data']
        except:
            return dz.get_user_artists_gw(user_id)

    def updateUserTracks(self, dz):
        user_id = dz.user['id']
        try:
            return dz.get_user_tracks(user_id)['data']
        except:
            return dz.get_user_tracks_gw(user_id)

    def getSpotifyPlaylistTracklist(self, id):
        if id == "" or not self.sp.spotifyEnabled:
            return emptySpotifyPlaylist
        return self.sp.get_playlist_tracklist(id)

    # Search functions
    def mainSearch(self, dz, term):
        return dz.search_main_gw(term)

    def search(self, dz, term, type, start, nb):
        return dz.search(term, type, nb, start)

    def searchAlbum(self, dz, term, start, nb):
        return dz.search_album_gw(term, start, nb)

    def newReleases(self, dz):
        return dz.get_new_releases()

    # Queue functions
    def addToQueue(self, dz, url, bitrate=None, interface=None, ack=None):
        if ';' in url:
            url = url.split(";")
        self.qm.addToQueue(dz, url, self.set.settings, bitrate, interface, ack)

    def removeFromQueue(self, uuid, interface=None):
        self.qm.removeFromQueue(uuid, interface)

    def cancelAllDownloads(self, interface=None):
        self.qm.cancelAllDownloads(interface)

    def removeFinishedDownloads(self, interface=None):
        self.qm.removeFinishedDownloads(interface)

    def initDownloadQueue(self):
        (queue, queueComplete, queueList, currentItem) = self.qm.getQueue()
        return (queue, queueComplete, queueList, currentItem)

    def analyzeLink(self, dz, link):
        if 'deezer.page.link' in link:
            link = requests.get(link).url
        type = getTypeFromLink(link)
        relID = getIDFromLink(link, type)
        if type in ["track", "album"]:
            data = getattr(dz, 'get_' + type)(relID)
        else:
            data = {}
        return (type, data)

    # Settings functions
    def getAllSettings(self):
        return (self.set.settings, self.sp.getCredentials(), self.set.defaultSettings)

    def getDefaultSettings(self):
        return self.set.defaultSettings

    def getSettings(self):
        return self.set.settings

    def saveSettings(self, newSettings, dz=None):
        return self.set.saveSettings(newSettings, dz)

    def getSpotifyCredentials(self):
        return self.sp.getCredentials()

    def setSpotifyCredentials(self, newCredentials):
        return self.sp.setCredentials(newCredentials)
