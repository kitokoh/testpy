# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files

# Collect qtwebengine locale files
qtwebengine_locales = collect_data_files(
    'PyQt5',
    subdir='Qt5/translations/qtwebengine_locales',
    include_py_files=False
)

a = Analysis(
    ['main.py'],
    pathex=['.'],  # Chemin relatif corrigé (il manquait les guillemets)
    
    binaries=[
        (os.path.join('dlls', 'liblzma.dll'), '.'),
        (os.path.join('dlls', 'libssl-3-x64.dll'), '.'),
        (os.path.join('dlls', 'libcrypto-3-x64.dll'), '.')
    ],
    datas=[
        (os.path.join('resources', 'icons', '*.ico'), os.path.join('resources', 'icons')),
        (os.path.join('resources', 'icons', '*.png'), os.path.join('resources', 'icons')),
        (os.path.join('resources', 'data', '*.json'), os.path.join('resources', 'data')),
        (os.path.join('resources', 'images', '*'), os.path.join('resources', 'images')),
        (os.path.join('resources', 'videos', '*'), os.path.join('resources', 'videos')),
        (os.path.join('lesClesNova360', 'icons', 'exeCle', '*'), os.path.join('resources', 'tools')),
        (os.path.join('resources', 'sounds', '*'), os.path.join('resources', 'sounds')),
        (os.path.join('resources', 'gifs', '*'), os.path.join('resources', 'gifs')),
        (os.path.join('resources', '*.key'), 'resources'),
        (os.path.join('resources', 'lang', '*'), os.path.join('resources', 'lang'))
    ],
    hiddenimports=[
        'sip', 'pymysql', 'pysqlite2', 'MySQLdb', 'psycopg2',
        'ssl', 'PyQt5.QtWebEngineWidgets', 'cryptography',
        'smtplib', 'email.mime.multipart', 'email.mime.text',
        'email.mime.base', 'email.encoders'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='nova360.ico',
    distpath='dist',
    workpath='build',
    onefile=True
)