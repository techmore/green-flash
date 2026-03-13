# UGreen File Manager

A macOS menu bar application that provides a web interface for managing files on your local machine and UGreen NAS, with features for organizing media files.

## Features

- **Menu Bar Icon**: Click to open the web interface in your default browser
- **File Browser**: Navigate folders on local machine and NAS
- **Media Type Detection**: Automatically identifies movies, TV shows, books, and other files
- **File Information**: Shows file sizes and types
- **Auto-discovery**: Automatically discovers UGreen NAS devices on the network
- **NAS Status Monitoring**: Menu bar shows NAS discovery status
- **Placeholder Functions**: Buttons for Plex-compliant renaming, transcoding, and NAS sync (to be implemented)
- **Filesystem Tree View**: Future enhancement for visualizing NAS and local files
- **Plex Search and Sync**: Future enhancement for searching and syncing with Plex folder structure

## Setup

### Running from Source

1. **Install Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Paths** (optional):
   Set environment variables to override default paths:
   ```bash
   export LOCAL_ROOT="/path/to/your/local/files"
   export NAS_ROOT="/Volumes/your-nas-share"
   ```

3. **Run the Application**:
   ```bash
   source venv/bin/activate
   python run_menu_bar.py
   ```
   
   This will:
   - Start a Flask web server on http://127.0.0.1:5000
   - Add a menu bar icon (click to open the web interface)
   - Automatically start discovering UGreen NAS devices on the network
   - Open your default browser to the file manager

### Building a Standalone Application

You can build a double-clickable macOS application bundle using the provided build script:

```bash
chmod +x build.sh
./build.sh
```

This will create `dist/UGreen File Manager.app` which you can drag to your Applications folder.

## Current Implementation

- **app.py**: Flask backend with file browsing API and NAS discovery
- **templates/index.html**: Web interface with file table, navigation, and NAS device listing
- **menu_bar_app.py**: rumps-based menu bar application with NAS status monitoring
- **run_menu_bar.py**: Entry point script
- **build.sh**: Script to build a standalone macOS app bundle
- **setup.py**: Configuration for py2app

## Next Steps / Planned Features

1. **Plex-Compliant Renaming**:
   - Implement proper movie/TV show naming conventions
   - Integration with file metadata APIs (IMDb, TMDB, etc.)

2. **Transcoding**:
   - FFmpeg integration for video conversion
   - Format selection (H.264, H.265, etc.)

3. **NAS Sync**:
   - Copy files to/from UGreen NAS
   - Progress tracking and conflict resolution

4. **Large File Analyzer** (NCDU-like):
   - Visualize disk usage by directory
   - Identify space-consuming files

5. **Enhanced Media Management**:
   - Metadata extraction (duration, resolution, etc.)
   - Library organization tools

6. **Filesystem Tree View**:
   - Display local and NAS files in a tree structure
   - Easy drag-and-drop between locations

7. **Plex Search and Sync Mode**:
   - Search across entire user space for media files
   - Identify and sync with Plex folder structure on UGreen NAS
   - Options to break out menus and actions from search results

## Environment Variables

- `LOCAL_ROOT`: Root directory for local file browsing (default: user home)
- `NAS_ROOT`: Root directory for NAS file browsing (default: /Volumes/NAS)
- `FLASK_PORT`: Port for the Flask server (default: 5000)

## Notes

- The menu bar app starts the Flask server in a background thread
- Clicking "Open Web Interface" launches your default browser
- File browsing respects permissions - inaccessible directories show errors
- Media type detection is based on file extensions
- NAS discovery happens automatically in the background
- LSP errors in the editor about missing imports (flask, rumps, requests) are expected if the editor is not using the virtual environment. The application runs correctly when executed within the virtual environment.
