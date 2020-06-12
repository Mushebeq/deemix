# -*- mode: python ; coding: utf-8 -*-
import deemix
import sys
from os.path import dirname

block_cipher = None

sys.modules['FixTk'] = None

a = Analysis(['deemix_gui.py'],
             binaries=[],
             datas=[('webui/public', 'webui/public'), (f'{dirname(deemix.__file__)}/app/default.json','deemix/app')],
             hiddenimports=['engineio.async_drivers.threading', 'pkg_resources.py2_warn'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
if sys.platform.startswith('darwin'):
    exe = EXE(pyz,
              a.scripts,
              a.binaries,
              a.zipfiles,
              a.datas,
              [],
              name='deemix_gui',
              debug=False,
              bootloader_ignore_signals=False,
              strip=False,
              upx=True,
              upx_exclude=[],
              runtime_tmpdir=None,
              console=True,
              icon=f"icon.icns")
    app = BUNDLE(exe,
                 name='deemix_gui.app',
                 icon="icon.icns",
                 bundle_identifier=None)
else:
    exe = EXE(pyz,
              a.scripts,
              [],
              name='deemix_gui',
              debug=False,
              bootloader_ignore_signals=False,
              strip=False,
              upx=True,
              console=True,
              icon=f"icon.ico")
    coll = COLLECT(exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   strip=False,
                   upx=True,
                   upx_exclude=[],
                   name='deemix_gui')
