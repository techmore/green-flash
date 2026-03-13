import rumps
import threading
import webbrowser
import time
import sys
import os
import requests
import json

# Add the current directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

class UGreenMenuBarApp(rumps.App):
    def __init__(self):
        super(UGreenMenuBarApp, self).__init__("UGreen", icon=None)  # You can add an icon path here
        self.menu = [
            "Open Web Interface",
            "NAS Status: Checking...",
            None,
            "Refresh NAS Status",
            "Plex Tools",
            "Transcode Tools",
            "Large File Scanner",
            None,
            "Quit"
        ]
        self.server_thread = None
        self.server_running = False
        self.nas_status_thread = None
        self.nas_status_active = False
        self.nas_devices = []
        
    def start_flask_server(self):
        """Start the Flask server in a background thread"""
        if not self.server_running:
            self.server_thread = threading.Thread(target=self.run_flask)
            self.server_thread.daemon = True
            self.server_thread.start()
            self.server_running = True
            # Give the server a moment to start
            time.sleep(1)
    
    def run_flask(self):
        """Run the Flask app"""
        app.run(host='127.0.0.1', port=5555, use_reloader=False)
    
    def start_nas_status_monitor(self):
        """Start monitoring NAS status"""
        if not self.nas_status_active:
            self.nas_status_active = True
            self.nas_status_thread = threading.Thread(target=self.nas_status_worker)
            self.nas_status_thread.daemon = True
            self.nas_status_thread.start()
    
    def nas_status_worker(self):
        """Worker thread to check NAS status"""
        while self.nas_status_active:
            try:
                # Try to get NAS status from our Flask app
                response = requests.get('http://127.0.0.1:5555/api/nas/discover', timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    self.nas_devices = data.get('devices', [])
                    
                    # Update menu item
                    count = len(self.nas_devices)
                    if count > 0:
                        title = f"NAS Status: {count} device{'s' if count != 1 else ''} found"
                    else:
                        title = "NAS Status: None discovered"
                    
                    # Update the menu (this needs to be done on main thread)
                    # Note: rumps doesn't allow direct menu updates from threads easily
                    # We'll use a notification instead
                    rumps.notification("UGreen", "NAS Status Updated", title)
                else:
                    rumps.notification("UGreen", "NAS Status", "Failed to check NAS status")
            except requests.exceptions.RequestException:
                # Flask server might not be running yet
                pass
            except Exception as e:
                print(f"Error checking NAS status: {e}")
            
            # Wait before next check
            time.sleep(10)
    
    def stop_nas_status_monitor(self):
        """Stop monitoring NAS status"""
        self.nas_status_active = False
    
    @rumps.clicked("Open Web Interface")
    def open_web_interface(self, _):
        """Start server (if not running) and open the web interface"""
        self.start_flask_server()
        # Start NAS status monitoring if not already started
        if not self.nas_status_active:
            self.start_nas_status_monitor()
        # Open the default web browser
        webbrowser.open('http://127.0.0.1:5000')
    
    @rumps.clicked("Refresh NAS Status")
    def refresh_nas_status(self, _):
        """Manually refresh NAS status"""
        rumps.notification("UGreen", "Refreshing", "Checking NAS status...")
        # This will be picked up by the worker thread on its next cycle
    
    @rumps.clicked("Plex Tools")
    def plex_tools(self, _):
        """Show Plex tools notification"""
        rumps.notification("UGreen", "Plex Tools", "Plex renaming tools available in web interface")
    
    @rumps.clicked("Transcode Tools")
    def transcode_tools(self, _):
        """Show transcode tools notification"""
        rumps.notification("UGreen", "Transcode Tools", "Transcoding tools available in web interface")
    
    @rumps.clicked("Large File Scanner")
    def large_file_scanner(self, _):
        """Show large file scanner notification"""
        rumps.notification("UGreen", "Large File Scanner", "Large file scanning tools available in web interface")
    
    @rumps.clicked("Quit")
    def quit_app(self, _):
        """Quit the application"""
        self.stop_nas_status_monitor()
        rumps.quit_application()

if __name__ == "__main__":
    app_instance = UGreenMenuBarApp()
    # Start NAS status monitoring when app launches
    app_instance.start_nas_status_monitor()
    app_instance.run()