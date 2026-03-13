#!/bin/bash
# Build and run script for UGreen File Manager Swift app
# This script:
#   1. Kills any existing Flask / Swift processes from this project
#   2. Compiles the Swift app and copies binary into the .app bundle
#   3. Starts the Flask web server (app.py) in the background
#   4. Launches the Swift menu‑bar app
#   5. Prints instructions for stopping the processes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_BUNDLE="$SCRIPT_DIR/UGreenFileManagerApp.app"
SWIFT_BIN="$SCRIPT_DIR/UGreenFileManager"
SWIFT_SRC="$SCRIPT_DIR/UGreenFileManagerApp/Sources/main.swift"
FLASK_APP="$SCRIPT_DIR/app.py"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"

echo "=== UGreen File Manager - Build and Run ==="

# 1. Kill existing processes
echo "[1/5] Stopping existing processes..."
pkill -f "python.*$FLASK_APP" || true
pkill -f "UGreenFileManager" || true
sleep 1

# 2. Compile Swift app
echo "[2/5] Compiling Swift app..."
swiftc -sdk "$(xcrun --show-sdk-path)" -target arm64-apple-macosx13.0 -framework Cocoa "$SWIFT_SRC" -o "$SWIFT_BIN"

# 3. Create/append app bundle
echo "[3/5] Creating app bundle..."
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Copy the binary
cp "$SWIFT_BIN" "$APP_BUNDLE/Contents/MacOS/"

# Create Info.plist
cat > "$APP_BUNDLE/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>UGreenFileManager</string>
    <key>CFBundleIdentifier</key>
    <string>com.techmore.ugreenfilemanager</string>
    <key>CFBundleName</key>
    <string>UGreen File Manager</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
EOF

# 4. Start Flask server in background
echo "[4/5] Starting Flask server..."
source "$SCRIPT_DIR/venv/bin/activate"
"$VENV_PYTHON" "$FLASK_APP" &
FLASK_PID=$!
# Give Flask a moment to start
sleep 2

# 5. Launch the Swift app (menu bar)
echo "[5/5] Launching UGreen File Manager..."
open "$APP_BUNDLE"
# Alternatively, launch the binary directly:
# "$SWIFT_BIN" &

echo ""
echo "=== UGreen File Manager is running ==="
echo "Flask server PID: $FLASK_PID"
echo "Web interface: http://127.0.0.1:5555"
echo "Menu-bar app:  $APP_BUNDLE"
echo ""
echo "To stop all processes:"
echo "  kill $FLASK_PID"
echo "  # The menu‑bar app can be quit from its menu → Exit"
echo ""
echo "Tip: You can also stop everything with:"
echo "  pkill -f \"python.*$FLASK_APP\""
echo "  pkill -f \"UGreenFileManager\""
echo ""