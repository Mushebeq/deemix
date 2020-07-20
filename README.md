# deemix-pyweb
This is a pywebview wrapper for deemix-webui

## How to use this
NOTES:
- Python 3 is required for this app. Make sure you tick the option to add Python to PATH when installing.
- If `python3` is "not a recognized command" try using `python` instead.
- If you're having issues with the package `wheel` missing use: `python3 -m pip install setuptools wheel --user`
- If you're on Windows:
	- Python 3.8 is not supported, you'll need to use Python 3.7 or 3.6
	- You'll need to install cefpython as well: `python3 -m pip install cefpython3 --user`
	- You also might need [.NET 4.0](https://www.microsoft.com/en-us/download/details.aspx?id=17718) installed

After installing Python open a terminal/command prompt and install the dependencies using `python3 -m pip install -U -r requirements.txt --user`<br>
If you're using git to get this repo you should use `git submodule update --init --recursive` as well. If you're just downloading the archive.zip, make sure you download and extract [deemix-webui](https://codeberg.org/RemixDev/deemix-webui) into the webui folder.<br>
Run `python3 server.py` to start the server and then connect to `127.0.0.1:6595`. The GUI should show up.<br>
If you don't want to use your browser you can start the GUI by using `python3 deemix_gui.py`<br>

Having an hard time following these steps? You could try these [tools](https://codeberg.org/RemixDev/deemix-tools)

## Feature requests
Before asking for a feature [check this out](https://codeberg.org/RemixDev/deemix-pyweb/src/master/FEATURES.md)

## What's left to do?
- Add an auto updater
- Add installer for windows
- AppImage builds

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
