# deemix-pyweb
This is a pywebview wrapper for deemix-webui

## How to use this
NOTE: Python 3 is required for this app. Make sure you tick the option to add Python to PATH when installing.<br>
NOTE: If `python3` is "not a recognized command" try using `python` instead.<br>
NOTE: If you're on windows you'll need to install cefpython and pythonnet as well: `python3 -m pip install cefpython pythonnet`<br>
After installing Python open a terminal/command prompt and install the dependencies using `python3 -m pip install -r requirements.txt --user`<br>
Run `python3 server.py` to start the server and then connect to `127.0.0.1:9666`. The GUI should show up.<br>
If you don't want to use your browser you can start the GUI by using `python3 deemix_gui.py`<br>

Having an hard time following these steps? You could try these [tools](https://notabug.org/RemixDev/deemix-tools)

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
