#!/usr/bin/env python3
from deemix.app.queuemanager import addToQueue, removeFromQueue, getQueue, cancelAllDownloads, removeFinishedDownloads
from deemix.utils.misc import getTypeFromLink, getIDFromLink
from deemix.app.settings import initSettings, getSettings, getDefaultSettings, saveSettings
from deemix.app.spotify import SpotifyHelper

settings = {}
spotifyHelper = None
chartsList = []


def getUser(dz):
    return dz.user


def initialize():
    global settings
    global spotifyHelper
    global defaultSettings
    settings = initSettings()
    defaultSettings = getDefaultSettings()
    spotifyHelper = SpotifyHelper()


def shutdown(interface=None):
    getQueue()
    cancelAllDownloads(interface)
    if interface:
        interface.send("toast", {'msg': "Server is closed."})

def get_charts(dz):
    global chartsList
    if len(chartsList) == 0:
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
        chartsList = countries
    return chartsList

def getUserFavorites(dz):
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

def updateUserSpotifyPlaylists(user):
    if user == "" or not spotifyHelper.spotifyEnabled:
        return []
    return spotifyHelper.get_user_playlists(user)


def updateUserPlaylists(dz):
    user_id = dz.user['id']
    try:
        return dz.get_user_playlists(user_id)['data']
    except:
        return dz.get_user_playlists_gw(user_id)

def updateUserAlbums(dz):
    user_id = dz.user['id']
    try:
        return dz.get_user_albums(user_id)['data']
    except:
        return dz.get_user_albums_gw(user_id)

def updateUserArtists(dz):
    user_id = dz.user['id']
    try:
        return dz.get_user_artists(user_id)['data']
    except:
        return dz.get_user_artists_gw(user_id)

def updateUserTracks(dz):
    user_id = dz.user['id']
    try:
        return dz.get_user_tracks(user_id)['data']
    except:
        return dz.get_user_tracks_gw(user_id)

def getSpotifyPlaylistTracklist(id):
    if id == "" or not spotifyHelper.spotifyEnabled:
        return spotifyHelper.emptyPlaylist
    return spotifyHelper.get_playlist_tracklist(id)

# Search functions
def mainSearch(dz, term):
    return dz.search_main_gw(term)


def search(dz, term, type, start, nb):
    return dz.search(term, type, nb, start)


# Queue functions
def addToQueue_link(dz, url, bitrate=None, interface=None):
    return addToQueue(dz, spotifyHelper, url, settings, bitrate, interface)


def removeFromQueue_link(uuid, interface=None):
    removeFromQueue(uuid, interface)


def cancelAllDownloads_link(interface=None):
    cancelAllDownloads(interface)


def removeFinishedDownloads_link(interface=None):
    removeFinishedDownloads(interface)


def getQueue_link():
    return getQueue()

def analyzeLink(dz, link):
    type = getTypeFromLink(link)
    relID = getIDFromLink(link, type)
    if type in ["track", "album"]:
        data = getattr(dz, 'get_' + type)(relID)
    else:
        data = {}
    return (type, data)

# Settings functions
def getDefaultSettings_link():
    return defaultSettings


def getSettings_link():
    return getSettings()


def saveSettings_link(newSettings):
    global settings
    settings = newSettings
    return saveSettings(newSettings)


def getSpotifyCredentials():
    return spotifyHelper.getCredentials()


def setSpotifyCredentials(newCredentials):
    return spotifyHelper.setCredentials(newCredentials)
