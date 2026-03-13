#!/bin/bash

# UGreen File Manager Build Script
# Creates a standalone macOS application bundle using py2app

echo "Building UGreen File Manager application..."

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install py2app if not already installed
pip install py2app

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the application
echo "Building application bundle..."
python setup.py py2app

# Check if build was successful
if [ -d "dist/UGreen File Manager.app" ]; then
    echo ""
    echo "Build successful! Application bundle created at:"
    echo "  dist/UGreen File Manager.app"
    echo ""
    echo "To install, drag the .app bundle to your Applications folder."
    echo "To run, double-click the .app bundle or open from Applications."
else
    echo ""
    echo "Build failed. Check the output above for errors."
    exit 1
fi