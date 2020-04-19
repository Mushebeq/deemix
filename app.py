import deemix.utils.localpaths as localpaths
from deemix.app.queuemanager import addToQueue, removeFromQueue, getQueue, cancelAllDownloads, removeFinishedDownloads
from deemix.app.settings import initSettings, getSettings, saveSettings
from deemix.app.spotify import SpotifyHelper
from os import system as execute

settings = {}
spotifyHelper = None

def getUser(dz):
	return dz.user

def initialize():
	global settings
	global spotifyHelper
	settings = initSettings()
	spotifyHelper = SpotifyHelper()

def shutdown(interface=None):
	getQueue()
	cancelAllDownloads(interface)
	if interface:
		interface.send("toast", {'msg': "Server is closed."})

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

# Settings functions
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
