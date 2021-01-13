# -*- mode: python ; coding: utf-8 -*-
import sys
from datetime import date
import subprocess

today = date.today().strftime("%Y.%m.%d")
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'])[:10].decode("utf-8")
version = f"{today}-{commit}"
with open('version.txt', 'w') as f:
    f.write(version)

block_cipher = None

sys.modules['FixTk'] = None

a = Analysis(['server.py'],
             binaries=[],
             datas=[('webui/public', 'webui'), ('icon.ico', '.'), ('version.txt', '.')],
             hiddenimports=['engineio.async_drivers.eventlet', 'pkg_resources.py2_warn', 'eventlet.hubs.epolls', 'eventlet.hubs.kqueue', 'eventlet.hubs.selects', 'dns', 'dns.dnssec', 'dns.e164', 'dns.hash', 'dns.namedict', 'dns.tsigkeyring', 'dns.update', 'dns.version', 'dns.zone'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
if '--onefile' in sys.argv or '-F' in sys.argv:
    exe = EXE(pyz,
              a.scripts,
              a.binaries,
              a.zipfiles,
              a.datas,
              [],
              name='deemix-server',
              debug=False,
              bootloader_ignore_signals=False,
              strip=False,
              upx=True,
              upx_exclude=[],
              runtime_tmpdir=None,
              console=True , icon='icon.ico')
else:
    exe = EXE(pyz,
              a.scripts,
              [],
              exclude_binaries=True,
              name='deemix-server',
              debug=False,
              bootloader_ignore_signals=False,
              strip=False,
              upx=True,
              console=True,
              icon="icon.ico")
    coll = COLLECT(exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   strip=False,
                   upx=True,
                   upx_exclude=[],
                   name='deemix-server')
