#!/usr/bin/env python3
from deemix.api.deezer import Deezer
from deemix.app.settings import Settings
from deemix.app.queuemanager import QueueManager
from deemix.app.spotifyhelper import SpotifyHelper, emptyPlaylist as emptySpotifyPlaylist

from deemix.utils.misc import getTypeFromLink, getIDFromLink
from deemix.utils.localpaths import getConfigFolder

#from deemix.app.queuemanager import addToQueue, removeFromQueue, getQueue, cancelAllDownloads, removeFinishedDownloads, restoreQueue, slimQueueItems, resetQueueItems
#
#from deemix.app.settings import initSettings, getSettings, getDefaultSettings, saveSettings
#from deemix.app.spotify import SpotifyHelper
#

import os.path as path
import json


class deemix:
    def __init__(self, portable):
        self.configFolder = portable or getConfigFolder()
        self.set = Settings(self.configFolder)
        self.sp = SpotifyHelper(self.configFolder)
        self.qm = QueueManager()

        self.chartsList = []

    def shutdown(self, interface=None):
        if self.set.settings['saveDownloadQueue']:
            self.qm.saveQueue(self.configFolder)
        self.qm.cancelAllDownloads(interface)
        if interface:
            interface.send("toast", {'msg': "Server is closed."})

    def restoreDownloadQueue(self, dz, interface=None):
        self.qm.loadQueue(self.configFolder, self.set.settings, interface)

    def queueRestored(self, dz, interface=None):
        self.qm.nextItem(dz, self.sp, interface)

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

    def getDownloadFolder(self):
        return self.set.settings['downloadLocation']

    def getUserFavorites(self, dz):
        user_id = dz.user['id']
        result = {}
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

    # Queue functions
    def addToQueue(self, dz, url, bitrate=None, interface=None):
        if ';' in url:
            url = url.split(";")
        self.qm.addToQueue(dz, self.sp, url, self.set.settings, bitrate, interface)


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
        type = getTypeFromLink(link)
        relID = getIDFromLink(link, type)
        if type in ["track", "album"]:
            data = getattr(dz, 'get_' + type)(relID)
        else:
            data = {}
        return (type, data)

    # Settings functions
    def getDefaultSettings(self):
        return self.set.defaultSettings

    def getSettings(self):
        return self.set.settings

    def saveSettings(self, newSettings):
        return self.set.saveSettings(newSettings)

    def getSpotifyCredentials(self):
        return self.sp.getCredentials()

    def setSpotifyCredentials(self, newCredentials):
        return self.sp.setCredentials(newCredentials)
