import Foundation
import Cocoa

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var pythonProcess: Process?
    
    func applicationDidFinishLaunching(_ aNotification: Notification) {
        // Create the menu bar item
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "network", accessibilityDescription: "UGreen")
            if let image = button.image {
                image.size = NSSize(width: 18, height: 18)
            }
            // Set action to show menu (default behavior when menu is assigned)
        }
        
        // Create the menu
        let menu = NSMenu()
        
        // Open Web Interface
        let openWebItem = NSMenuItem(title: "Open Web Interface", action: #selector(openWebInterface), keyEquivalent: "")
        openWebItem.target = self
        menu.addItem(openWebItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Version
        let versionItem = NSMenuItem(title: "Version 1.0", action: nil, keyEquivalent: "")
        versionItem.isEnabled = false  // just display
        menu.addItem(versionItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Uninstall
        let uninstallItem = NSMenuItem(title: "Uninstall", action: #selector(uninstallApp), keyEquivalent: "")
        uninstallItem.target = self
        menu.addItem(uninstallItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Exit
        let exitItem = NSMenuItem(title: "Exit UGreen File Manager", action: #selector(exitApp), keyEquivalent: "q")
        exitItem.target = self
        menu.addItem(exitItem)
        
        // Assign menu to status item
        statusItem.menu = menu
        
        // Start the Python Flask server
        startPythonServer()
    }
    
    @objc func openWebInterface() {
        if let url = URL(string: "http://127.0.0.1:5555") {
            NSWorkspace.shared.open(url)
        }
    }
    
    @objc func uninstallApp() {
        let alert = NSAlert()
        alert.messageText = "Uninstall UGreen File Manager"
        alert.informativeText = "This will move the application to the Trash. Are you sure?"
        alert.addButton(withTitle: "Move to Trash")
        alert.addButton(withTitle: "Cancel")
        alert.alertStyle = .warning
        
        let response = alert.runModal()
        if response == .alertFirstButtonReturn {
            // Get the app bundle path
            let appPath = Bundle.main.bundleURL
            do {
                try FileManager().trashItem(at: appPath, resultingItemURL: nil)
                NSApplication.shared.terminate(nil)
            } catch {
                let errorAlert = NSAlert()
                errorAlert.messageText = "Error"
                errorAlert.informativeText = "Failed to move app to Trash: \(error.localizedDescription)"
                errorAlert.runModal()
            }
        }
    }
    
    @objc func exitApp() {
        NSApplication.shared.terminate(nil)
    }
    
    func startPythonServer() {
        // Hardcoded paths for now
        let pythonPath = "/Users/techmore/projects/ugreen-flask/venv/bin/python"
        let appPath = "/Users/techmore/projects/ugreen-flask/app.py"
        
        // Check if the files exist
        let fileManager = FileManager.default
        if !fileManager.fileExists(atPath: pythonPath) || !fileManager.fileExists(atPath: appPath) {
            print("Warning: Could not find Python or app.py at expected location.")
            print("Python path: \(pythonPath)")
            print("App path: \(appPath)")
            return
        }
        
        pythonProcess = Process()
        pythonProcess?.executableURL = URL(fileURLWithPath: pythonPath)
        pythonProcess?.arguments = [pythonPath, appPath]
        
        let pipe = Pipe()
        pythonProcess?.standardOutput = pipe
        pythonProcess?.standardError = pipe
        
        do {
            try pythonProcess?.run()
        } catch {
            print("Failed to start Python server: \(error)")
        }
    }
    
    func applicationWillTerminate(_ aNotification: Notification) {
        // Stop the Python server when the app quits
        pythonProcess?.terminate()
    }
}

// Set up the app
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)  // Menu bar app style (no dock icon)
app.run()