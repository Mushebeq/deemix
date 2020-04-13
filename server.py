import json
import os
import webbrowser
from functools import wraps

from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit
import logging
import webview
from deemix.api.deezer import Deezer
import deemix.app.main as app
import time

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

serverLog = logging.getLogger('werkzeug')
serverLog.disabled = True
server.logger.disabled = True

app.initialize()

@server.route('/')
def landing():
	return render_template('index.html', token=webview.token)

@server.route('/shutdown')
def closing():
	app.shutdown(socket=socketio)
	func = request.environ.get('werkzeug.server.shutdown')
	func()
	return 'server closed'

@socketio.on('connect')
def on_connect():
	session['dz'] = Deezer()
	emit('init_settings', app.getSettings_link())
	queue, queueList = app.getQueue_link()
	emit('init_downloadQueue', {'queue': queue, 'queueList': queueList})

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

@socketio.on('loginpage')
def login_app():
	emit('toast', {'msg': "Logging in...", 'icon': 'loading', 'dismiss': False, 'id': "login-toast"})
	loginWindow = webview.create_window('Login into deezer.com', 'https://www.deezer.com/login', user_agent="Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30")
	while (loginWindow and loginWindow.get_current_url().startswith("https://www.deezer.com")):
		time.sleep(1)
	if loginWindow:
		url = loginWindow.get_current_url()
		loginWindow.destroy()
		arl = url[url.find("arl%3D")+6:]
		arl = arl[:arl.find("&")]
		# Login function
		if not session['dz'].logged_in:
			result = session['dz'].login_via_arl(arl)
		else:
			result = 2
		emit('logged_in', {'status': result, 'arl': arl, 'user': app.getUser(session['dz'])})
	else:
		emit('logged_in', {'status': 0})

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
	result = app.addToQueue_link(session['dz'], data['url'], socket=socketio)
	if result == "Not logged in":
		emit('toast', {'msg': "You need to log in to download tracks!", 'icon': 'report'})

@socketio.on('removeFromQueue')
def removeFromQueue(uuid):
	app.removeFromQueue_link(uuid, socket=socketio)

# Example code leftover, could be usefull later on
@server.route('/choose/path', methods=['POST'])
def choose_path():
	dirs = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
	if dirs and len(dirs) > 0:
		directory = dirs[0]
		if isinstance(directory, bytes):
			directory = directory.decode('utf-8')
		response = {'status': 'ok', 'directory': directory}
	else:
		response = {'status': 'cancel'}

	return jsonify(response)

def run_server(port):
	print("Starting server at http://0.0.0.0:"+str(port))
	socketio.run(server, host='0.0.0.0', port=port)

if __name__ == '__main__':
	run_server(33333)
