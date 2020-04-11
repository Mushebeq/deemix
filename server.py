import json
import os
import webbrowser
from functools import wraps

from flask import Flask, url_for, render_template, jsonify, request, make_response
from flask_socketio import SocketIO, emit
import logging
import webview
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

@server.route('/')
def landing():
	return render_template('index.html', token=webview.token)

@server.route('/shutdown')
def closing():
	app.shutdown(socket=socketio)
	func = request.environ.get('werkzeug.server.shutdown')
	func()
	return 'server closed'

@socketio.on('init')
def handle_init():
	result = app.initialize()
	emit('initialization', result)

@socketio.on('login')
def login(arl):
	result = app.login(arl)
	emit('logged_in', {'status': result, 'arl': arl, 'user': app.getUser()})

@socketio.on('loginpage')
def login_app():
	loginWindow = webview.create_window('Login into deezer.com', 'https://www.deezer.com/login', user_agent="Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30")
	while (loginWindow and loginWindow.get_current_url().startswith("https://www.deezer.com")):
		time.sleep(1)
	if loginWindow:
		url = loginWindow.get_current_url()
		loginWindow.destroy()
		arl = url[url.find("arl%3D")+6:]
		arl = arl[:arl.find("&")]
		result = app.login(arl)
		emit('logged_in', {'status': result, 'arl': arl, 'user': app.getUser()})
	else:
		emit('logged_in', {'status': 0})

@socketio.on('mainSearch')
def mainSearch(data):
	emit('mainSearch', app.mainSearch(data['term']))

@socketio.on('search')
def search(data):
	result = app.search(data['term'], data['type'], data['start'], data['nb'])
	result['type'] = data['type']
	emit('search', result)

@socketio.on('addToQueue')
def addToQueue(data):
	app.addToQueue_link(data['url'], socket=socketio)

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

@server.route('/fullscreen', methods=['POST'])
def fullscreen():
	webview.windows[0].toggle_fullscreen()
	return jsonify({})

@server.route('/open-url', methods=['POST'])
def open_url():
	url = request.json['url']
	webbrowser.open_new_tab(url)
	return jsonify({})

@server.route('/do/stuff', methods=['POST'])
def do_stuff():
	result = app.do_stuff()
	if result:
		response = {'status': 'ok', 'result': result}
	else:
		response = {'status': 'error'}
	return jsonify(response)

def run_server(port):
	print("Starting server at http://127.0.0.1:"+str(port))
	socketio.run(server, host='127.0.0.1', port=port)

if __name__ == '__main__':
	run_server(33333)
