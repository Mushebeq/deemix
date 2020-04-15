import deemix.utils.localpaths as localpaths
from deemix.app.queuemanager import addToQueue, removeFromQueue, getQueue, cancelAllDownloads, removeFinishedDownloads
from deemix.app.settings import initSettings, getSettings, saveSettings
from os import system as execute

settings = {}

def getUser(dz):
	return dz.user

def initialize():
	global settings
	settings = initSettings()

def shutdown(interface=None):
	getQueue()
	cancelAllDownloads(interface)
	if interface:
		interface.send("toast", {'msg': "Server is closed."})

def mainSearch(dz, term):
	return dz.search_main_gw(term)

def search(dz, term, type, start, nb):
	return dz.search_gw(term, type, start, nb)

def addToQueue_link(dz, url, bitrate=None, interface=None):
	return addToQueue(dz, url, settings, bitrate, interface)

def removeFromQueue_link(uuid, interface=None):
	removeFromQueue(uuid, interface)

def cancelAllDownloads_link(interface=None):
	cancelAllDownloads(interface)

def removeFinishedDownloads_link(interface=None):
	removeFinishedDownloads(interface)

def getSettings_link():
	return getSettings()

def getSettings_link():
	return getSettings()

def getQueue_link():
	return getQueue()

def saveSettings_link(newSettings):
	global settings
	settings = newSettings
	return saveSettings(newSettings)
