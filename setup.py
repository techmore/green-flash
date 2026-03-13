from setuptools import setup

APP = ['run_menu_bar.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,  # Make it a menu bar app (no dock icon)
        'CFBundleName': 'UGreen File Manager',
        'CFBundleDisplayName': 'UGreen File Manager',
        'CFBundleGetInfoString': "File Manager for UGreen NAS",
        'CFBundleIdentifier': 'com.techmore.ugreenfilemanager',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
    },
    'packages': ['flask', 'rumps', 'requests'],
    'includes': ['charset_normalizer', 'charset_normalizer.api', 'charset_normalizer.cd', 'charset_normalizer.charset_templates', 'idna', 'idna.idnadata'],
    'excludes': ['_mypy_cache__', '_builtins', 'charset_normalizer._mypy_cache', 'charset_normalizer.tests'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)