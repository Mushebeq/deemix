#!/usr/bin/env python3
import eventlet
requests = eventlet.import_patched('requests')

from deezer import Deezer
from deezer.utils import clean_search_query
from deemix.app.settings import Settings, DEFAULT_SETTINGS
from deemix.app.queuemanager import QueueManager
from deemix.app.spotifyhelper import SpotifyHelper, emptyPlaylist as emptySpotifyPlaylist

from deemix.utils import getTypeFromLink, getIDFromLink
from deemix.utils.localpaths import getConfigFolder

from pathlib import Path
import json
import re

from datetime import datetime, timedelta

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).resolve().parent

    return Path(base_path) / relative_path

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
        if commitFile.is_file():
            with open(commitFile, 'r') as f:
                self.currentVersion = f.read().strip()
            #print("Checking for updates...")
            #try:
            #    latestVersion = requests.get("https://deemix.app/pyweb/latest")
            #    latestVersion.raise_for_status()
            #    self.latestVersion = latestVersion.text.strip()
            #except:
            #    self.latestVersion = None
            #self.updateAvailable = self.compareVersions()
            #if self.updateAvailable:
            #    print("Update available! Commit: "+self.latestVersion)
            #else:
            #    print("You're running the latest version")

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
        print("Pinging deezer.com...")
        try:
            body = requests.get("https://www.deezer.com/", headers={'Cookie': 'dz_lang=en; Domain=deezer.com; Path=/; Secure; hostOnly=false;'}).text
        except Exception as e:
            self.isDeezerAvailable = False
            print(f"deezer.com not reached! {str(e)}")
        title = body[body.find('<title>')+7:body.find('</title>')]
        self.isDeezerAvailable = title.strip() != "Deezer will soon be available in your country."
        print(f"deezer.com reached: {'Available' if self.isDeezerAvailable else 'Not Available'}")

    def shutdown(self, interface=None):
        if self.set.settings['saveDownloadQueue']:
            self.qm.saveQueue(self.configFolder)
        self.qm.cancelAllDownloads(interface)
        if interface:
            interface.send("toast", {'msg': "Server is closed."})

    def getArl(self, tempDz):
        while True:
            arl = input("Paste here your arl: ")
            if not tempDz.login_via_arl(arl):
                print("ARL doesnt work. Mistyped or expired?")
            else:
                break
        with open(self.configFolder / '.arl', 'w') as f:
            f.write(arl)
        return arl

    def getConfigArl(self):
        tempDz = Deezer()
        arl = None
        if (self.configFolder / '.arl').is_file():
            with open(self.configFolder / '.arl', 'r') as f:
                arl = f.readline().rstrip("\n")
            if not tempDz.login_via_arl(arl):
                print("Saved ARL mistyped or expired, please enter a new one")
                return self.getArl(tempDz)
        else:
            return self.getArl(tempDz)
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
            temp = dz.api.get_countries_charts()
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
            self.homeCache = dz.api.get_chart(limit=30)
        return self.homeCache

    def getDownloadFolder(self):
        return self.set.settings['downloadLocation']

    def getTracklist(self, dz, data):
        if data['type'] == 'artist':
            artistAPI = dz.api.get_artist(data['id'])
            artistAPI['releases'] = dz.gw.get_artist_discography_tabs(data['id'], 100)
            return artistAPI
        elif data['type'] == 'spotifyplaylist':
            playlistAPI = self.getSpotifyPlaylistTracklist(data['id'])
            for i in range(len(playlistAPI['tracks'])):
                playlistAPI['tracks'][i] = playlistAPI['tracks'][i]['track']
                playlistAPI['tracks'][i]['selected'] = False
            return playlistAPI
        else:
            releaseAPI = getattr(dz.api, 'get_' + data['type'])(data['id'])
            releaseTracksAPI = getattr(dz.api, 'get_' + data['type'] + '_tracks')(data['id'])['data']
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
            user_id = dz.current_user['id']
            try:
                result['playlists'] = dz.api.get_user_playlists(user_id, limit=-1)['data']
                result['albums'] = dz.api.get_user_albums(user_id, limit=-1)['data']
                result['artists'] = dz.api.get_user_artists(user_id, limit=-1)['data']
                result['tracks'] = dz.api.get_user_tracks(user_id, limit=-1)['data']
            except:
                result['playlists'] = dz.gw.get_user_playlists(user_id, limit=-1)
                result['albums'] = dz.gw.get_user_albums(user_id, limit=-1)
                result['artists'] = dz.gw.get_user_artists(user_id, limit=-1)
                result['tracks'] = dz.gw.get_user_tracks(user_id, limit=-1)
        return result

    def updateUserSpotifyPlaylists(self, user):
        if user == "" or not self.sp.spotifyEnabled:
            return []
        try:
            return self.sp.get_user_playlists(user)
        except:
            return []

    def updateUserPlaylists(self, dz):
        user_id = dz.current_user['id']
        try:
            return dz.api.get_user_playlists(user_id, limit=-1)['data']
        except:
            return dz.gw.get_user_playlists(user_id, limit=-1)

    def updateUserAlbums(self, dz):
        user_id = dz.current_user['id']
        try:
            return dz.api.get_user_albums(user_id, limit=-1)['data']
        except:
            return dz.gw.get_user_albums(user_id, limit=-1)

    def updateUserArtists(self, dz):
        user_id = dz.current_user['id']
        try:
            return dz.api.get_user_artists(user_id, limit=-1)['data']
        except:
            return dz.gw.get_user_artists(user_id, limit=-1)

    def updateUserTracks(self, dz):
        user_id = dz.current_user['id']
        try:
            return dz.api.get_user_tracks(user_id, limit=-1)['data']
        except:
            return dz.gw.get_user_tracks(user_id, limit=-1)

    def getSpotifyPlaylistTracklist(self, id):
        if id == "" or not self.sp.spotifyEnabled:
            return emptySpotifyPlaylist
        return self.sp.get_playlist_tracklist(id)

    # Search functions
    def mainSearch(self, dz, term):
        results = dz.gw.search(clean_search_query(term))
        order = []
        for x in results['ORDER']:
            if x in ['TOP_RESULT', 'TRACK', 'ALBUM', 'ARTIST', 'PLAYLIST']:
                order.append(x)
        if 'TOP_RESULT' in results and len(results['TOP_RESULT']):
            orig_top_result = results['TOP_RESULT'][0]
            top_result = {}
            top_result['type'] = orig_top_result['__TYPE__']
            if top_result['type'] == 'artist':
                top_result['id'] = orig_top_result['ART_ID']
                top_result['picture'] = 'https://e-cdns-images.dzcdn.net/images/artist/' + orig_top_result['ART_PICTURE']
                top_result['title'] = orig_top_result['ART_NAME']
                top_result['nb_fan'] = orig_top_result['NB_FAN']
            elif top_result['type'] == 'album':
                top_result['id'] = orig_top_result['ALB_ID']
                top_result['picture'] = 'https://e-cdns-images.dzcdn.net/images/cover/' + orig_top_result['ALB_PICTURE']
                top_result['title'] = orig_top_result['ALB_TITLE']
                top_result['artist'] = orig_top_result['ART_NAME']
                top_result['nb_song'] = orig_top_result['NUMBER_TRACK']
            elif top_result['type'] == 'playlist':
                top_result['id'] = orig_top_result['PLAYLIST_ID']
                top_result['picture'] = 'https://e-cdns-images.dzcdn.net/images/' + orig_top_result['PICTURE_TYPE'] + '/' + orig_top_result['PLAYLIST_PICTURE']
                top_result['title'] = orig_top_result['TITLE']
                top_result['artist'] = orig_top_result['PARENT_USERNAME']
                top_result['nb_song'] = orig_top_result['NB_SONG']
            else:
                top_result['id'] = "0"
                top_result['picture'] = 'https://e-cdns-images.dzcdn.net/images/cover'
            top_result['picture'] += '/156x156-000000-80-0-0.jpg'
            top_result['link'] = 'https://deezer.com/'+top_result['type']+'/'+str(top_result['id'])
            results['TOP_RESULT'][0] = top_result
        results['ORDER'] = order
        return results

    def search(self, dz, term, type, start, nb):
        if type == "album":
            return dz.api.search_album(clean_search_query(term), limit=nb, index=start)
        if type == "artist":
            return dz.api.search_artist(clean_search_query(term), limit=nb, index=start)
        if type == "playlist":
            return dz.api.search_playlist(clean_search_query(term), limit=nb, index=start)
        if type == "radio":
            return dz.api.search_radio(clean_search_query(term), limit=nb, index=start)
        if type == "track":
            return dz.api.search_track(clean_search_query(term), limit=nb, index=start)
        if type == "user":
            return dz.api.search_user(clean_search_query(term), limit=nb, index=start)
        return dz.api.search(clean_search_query(term), limit=nb, index=start)

    def getAlbumDetails(self, dz, album_id):
        result = dz.gw.get_album_page(album_id)
        output = result['DATA']

        duration = 0
        for x in result['SONGS']['data']:
            try:
                duration += int(x['DURATION'])
            except:
                pass

        output['DURATION'] = duration
        output['NUMBER_TRACK'] = result['SONGS']['total']
        output['LINK'] = f"https://deezer.com/album/{str(output['ALB_ID'])}"

        return output

    def searchAlbum(self, dz, term, start, nb):
        results = dz.gw.search_music(clean_search_query(term), "ALBUM", start, nb)['data']

        ids = [x['ALB_ID'] for x in results]

        def albumDetailsWorker(album_id):
            return self.getAlbumDetails(dz, album_id)
        pool = eventlet.GreenPool(100)
        albums = [a for a in pool.imap(albumDetailsWorker, ids)]

        return albums

    def channelNewReleases(self, dz, channel_name):
        channel_data = dz.gw.get_page(channel_name)
        pattern = '^New.*releases$'
        new_releases = next((x for x in channel_data['sections'] if re.match(pattern, x['title'])), None)

        try:
            if new_releases is None:
                return []
            elif 'target' in new_releases:
                show_all = dz.gw.get_page(new_releases['target'])
                return [x['data'] for x in show_all['sections'][0]['items']]
            elif 'items' in new_releases:
                return [x['data'] for x in new_releases['items']]
            else:
                return []
        except Exception:
            return []

    def newReleases(self, dz):
        explore = dz.gw.get_page('channels/explore')
        music_section = next((x for x in explore['sections'] if x['title'] == 'Music'), None)
        channels = [x['target'] for x in music_section['items']]

        def channelWorker(channel):
            return self.channelNewReleases(dz, channel)
        pool = eventlet.GreenPool(100)
        new_releases_lists = [x for x in pool.imap(channelWorker, channels[1:10])]

        seen = set()
        new_releases = [seen.add(x['ALB_ID']) or x for list in new_releases_lists for x in list if x['ALB_ID'] not in seen]
        new_releases.sort(key=lambda x: x['DIGITAL_RELEASE_DATE'], reverse=True)

        now = datetime.now()
        delta = timedelta(days=8)
        recent_releases = [x for x in new_releases if now - datetime.strptime(x['DIGITAL_RELEASE_DATE'], "%Y-%m-%d") < delta]
        recent_releases.sort(key=lambda x: x['ALB_ID'], reverse=True)

        def albumDetailsWorker(album_id):
            return self.getAlbumDetails(dz, album_id)
        albums = [a for a in pool.imap(albumDetailsWorker, [x['ALB_ID'] for x in recent_releases])]

        return albums

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
            data = getattr(dz.api, 'get_' + type)(relID)
        else:
            data = {}
        return (type, data)

    # Settings functions
    def getAllSettings(self):
        return (self.set.settings, self.sp.getCredentials(), DEFAULT_SETTINGS)

    def getDefaultSettings(self):
        return DEFAULT_SETTINGS

    def getSettings(self):
        return self.set.settings

    def saveSettings(self, newSettings, dz=None):
        return self.set.saveSettings(newSettings, dz)

    def getSpotifyCredentials(self):
        return self.sp.getCredentials()

    def setSpotifyCredentials(self, newCredentials):
        return self.sp.setCredentials(newCredentials)
