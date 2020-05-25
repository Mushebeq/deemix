# -*- mode: python ; coding: utf-8 -*-
import deemix
from os.path import dirname

block_cipher = None

a = Analysis(['server.py'],
             binaries=[],
             datas=[('webui/public', 'webui/public'), (f'{dirname(deemix.__file__)}/app/default.json','deemix/app')],
             hiddenimports=['engineio.async_drivers.threading', 'pkg_resources.py2_warn'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='deemix_webui',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='server')
