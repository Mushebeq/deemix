# deemix-pyweb
This is a pywebview wrapper for deemix-webui

## Installing the app
NOTES:
- Python 3 is required for this app. Make sure you tick the option to add Python to PATH when installing.
- If `python3` is "not a recognized command" try using `python` instead.
- If you're having issues with the package `wheel` missing use: `python3 -m pip install setuptools wheel --user`
- If you're on Windows:
	- Python 3.8 is not supported, you'll need to use Python 3.7 or 3.6
	- You'll need to install cefpython as well: `python3 -m pip install cefpython3 --user`
	- You also might need [.NET 4.0](https://www.microsoft.com/en-us/download/details.aspx?id=17718) installed

After installing Python open a terminal/command prompt in the app folder and install the dependencies using `python3 -m pip install -U -r requirements.txt --user`<br>
If you're on linux you can choose if you want to use GTK or QT (GTK is the primary choice, QT is the fallback). Instead of the plain requirements.txt you should use the respective requirements file for the Toolkit you want to use.

If you're using git to get this repo you should use `git submodule update --init --recursive` as well. If you're just downloading the archive.zip, make sure you download and extract [deemix-webui](https://codeberg.org/RemixDev/deemix-webui) into the webui folder.

Having an hard time following these steps? You could try these [tools](https://codeberg.org/RemixDev/deemix-tools)

## Using the app
### GUI
If you want to use the app with a GUI you can start it by using `python3 deemix_gui.py`.<br>
You can change the port of the server by starting the app with `python3 deemix_gui.py [PORT]`.<br>
If you want to change the host IP (If you want to access the app from outside of your pc) you can use the `--host custom.host.ip.here` parameter.<br>
The `--portable` flags creates a local folder for the configs allowing to start the app without creating permanent folders on the host machine.

### Server
You can run `python3 server.py` or `python3 deemix_gui.py --server` or `python3 deemix_gui.py -s` to start the server.<br>
The default host and port combination used by the server is `127.0.0.1:6595`.<br>
You can change the port of the server by starting the app with `python3 server.py [PORT]`.<br>
Same thing with the host using the `--host custom.host.ip.here` parameter.<br>
If you want to set a default arl for all connecting clients you can use the `--serverwide-arl` flag. It will use the same arl used by the cli app, that is located inside a file name `.arl` in the config folder.<br>
The `--portable` flags creates a local folder for the configs allowing to start the app without creating permanent folders on the host machine.

## Feature requests
Before asking for a feature [check this out](https://codeberg.org/RemixDev/deemix-pyweb/src/branch/main/FEATURES.md)

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
