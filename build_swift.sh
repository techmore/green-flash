#!/bin/bash

# Build script for UGreen File Manager Swift app

echo "Building UGreen File Manager Swift app..."

# Kill any existing processes
pkill -f "python.*app.py" || true
pkill -f "UGreenFileManager" || true

# Compile the Swift app
echo "Compiling Swift app..."
swiftc -sdk $(xcrun --show-sdk-path) -target arm64-apple-macosx13.0 -framework Cocoa -framework WebKit UGreenFileManagerApp/Sources/main.swift -o UGreenFileManager

# Create app bundle directory structure
echo "Creating app bundle..."
mkdir -p UGreenFileManagerApp.app/Contents/MacOS
mkdir -p UGreenFileManagerApp.app/Contents/Resources

# Copy the binary
cp UGreenFileManager UGreenFileManagerApp.app/Contents/MacOS/

# Create Info.plist
cat > UGreenFileManagerApp.app/Contents/Info.plist << 'EOF'
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
</EOF>

# Create a simple run script
cat > run.sh << 'EOF'
#!/bin/bash
# Start the Flask server in background
source venv/bin/activate
python app.py &
FLASK_PID=$!

# Launch the Swift app
./UGreenFileManager &
SWIFT_PID=$!

echo "Flask server started (PID: $FLASK_PID)"
echo "Swift app started (PID: $SWIFT_PID)"
echo "Web interface available at http://127.0.0.1:5555"
echo ""
echo "To stop all processes:"
echo "kill $FLASK_PID $SWIFT_PID"
EOF

chmod +x run.sh

echo ""
echo "Build complete!"
echo ""
echo "To run the app:"
echo "  ./run.sh"
echo ""
echo "Or to run just the Swift app (if Flask is already running):"
echo "  ./UGreenFileManager"
echo ""
echo "The app will appear in your menu bar and open the web interface at http://127.0.0.1:5555"