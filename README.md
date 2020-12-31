# deemix-pyweb
This is a pywebview wrapper for deemix-webui

## Installing the app
NOTES:
- Python 3 is required for this app. Make sure you tick the option to add Python to PATH when installing.
- If `python3` is "not a recognized command" try using `python` instead.
- If you're having issues with the package `wheel` missing use: `python3 -m pip install setuptools wheel --user`
- Python 3.9 may not work, Python 3.8 is recommended

After installing Python open a terminal/command prompt in the app folder and install the dependencies using `python3 -m pip install -U -r requirements.txt --user`

If you're using git to get this repo you should use `git submodule update --init --recursive` as well. If you're just downloading the archive.zip, make sure you download and extract deemix-webui into the webui folder.

## Using the app
### GUI
If you want to use the app with a GUI you can start it by using `python3 deemix-pyweb.py`.<br>
You can change the port of the server by starting the app with `python3 deemix-pyweb.py [PORT]`.<br>
If you want to change the host IP (If you want to access the app from outside of your pc) you can use the `--host custom.host.ip.here` parameter.<br>
The `--portable` flags creates a local folder for the configs allowing to start the app without creating permanent folders on the host machine.

### Server
You can run `python3 server.py`, `python3 deemix-pyweb.py --server` or `python3 deemix-pyweb.py -s` to start the server.<br>
The default host and port combination used by the server is `127.0.0.1:6595`.<br>
You can change the port of the server by starting the app with `python3 server.py [PORT]`.<br>
Same thing with the host using the `--host custom.host.ip.here` parameter.<br>
If you want to set a default arl for all connecting clients you can use the `--serverwide-arl` flag. It will use the same arl used by the cli app, that is located inside a file named `.arl` in the config folder.<br>
The `--portable` flags creates a local folder for the configs allowing to start the app without creating permanent folders on the host machine.

## Feature requests
Before asking for a feature make sure it isn't an already open issue on the repo

# License
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
