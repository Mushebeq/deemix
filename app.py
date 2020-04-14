import deemix.utils.localpaths as localpaths
from deemix.app.queuemanager import addToQueue, removeFromQueue, getQueue, cancelAllDownloads
from deemix.app.settings import initSettings, getSettings, saveSettings
from os import system as execute

settings = {}

def getUser(dz):
	return dz.user

def initialize():
	global settings
	settings = initSettings()

def shutdown(socket=None):
	print(getQueue())
	cancelAllDownloads(socket)
	if socket:
		socket.emit("toast", {'msg': "Server is closed."})

def mainSearch(dz, term):
	return dz.search_main_gw(term)

def search(dz, term, type, start, nb):
	return dz.search_gw(term, type, start, nb)

def addToQueue_link(dz, url, bitrate=None, socket=None):
	return addToQueue(dz, url, settings, bitrate, socket)

def removeFromQueue_link(uuid, socket=None):
	removeFromQueue(uuid, socket)

def getSettings_link():
	return getSettings()

def getSettings_link():
	return getSettings()

def getQueue_link():
	return getQueue()

def saveSettings_link(newSettings):
	return saveSettings(newSettings)
