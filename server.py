import json
import os
import webbrowser
from functools import wraps

from flask import Flask, url_for, render_template, jsonify, request, make_response
from flask_socketio import SocketIO, emit
import logging
import webview
import deemix.app.main as app

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

@socketio.on('init')
def handle_init():
	can_start = app.initialize()
	emit('toast', {'msg': "App initialized!", 'icon': 'done'})

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

def run_server():
	socketio.run(server, host='127.0.0.1', port=33333)

if __name__ == '__main__':
	run_server()
