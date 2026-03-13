import os
import sqlite3
import socket
import subprocess
import threading
import time
import re
import json
import shutil
from flask import Flask, render_template, request, jsonify, g
from pathlib import Path

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'files.db')
# Set LOCAL_ROOT to /Users by default as requested
app.config['LOCAL_ROOT'] = os.getenv('LOCAL_ROOT', '/Users')
app.config['NAS_ROOT'] = os.getenv('NAS_ROOT', '/Volumes/NAS')
print(f"LOCAL_ROOT set to: {app.config['LOCAL_ROOT']}")
print(f"NAS_ROOT set to: {app.config['NAS_ROOT']}")

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                size INTEGER,
                is_dir BOOLEAN,
                location TEXT NOT NULL, -- 'local' or 'nas'
                media_type TEXT, -- 'movie', 'tv', 'book', 'other'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/browse')
def browse():
    location = request.args.get('location', 'local')
    subpath = request.args.get('path', '')
    
    if location == 'local':
        root = app.config['LOCAL_ROOT']
    else:
        root = app.config['NAS_ROOT']
    
    full_path = os.path.join(root, subpath)
    
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return jsonify({'error': 'Path not found'}), 404
    
    items = []
    try:
        with os.scandir(full_path) as entries:
            for entry in entries:
                # Skip hidden files and directories (those starting with .)
                if entry.name.startswith('.'):
                    continue
                    
                stat = entry.stat()
                items.append({
                    'name': entry.name,
                    'path': os.path.relpath(entry.path, root),
                    'size': stat.st_size if entry.is_file() else 0,
                    'is_dir': entry.is_dir(),
                    'media_type': get_media_type(entry.name) if entry.is_file() else None
                })
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Sort items: directories first, then files, both alphabetically
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    
    return jsonify({
        'current_path': subpath,
        'parent': os.path.dirname(subpath) if subpath else None,
        'items': items
    })

@app.route('/api/nas/discover')
def discover_nas():
    """Endpoint to get discovered NAS devices"""
    global discovered_nas_devices
    return jsonify({
        'devices': discovered_nas_devices,
        'timestamp': time.time()
    })

@app.route('/api/nas/shares/<nas_ip>')
def get_nas_shares(nas_ip):
    """Get available shares on a specific NAS device"""
    # Validate IP address format
    try:
        socket.inet_aton(nas_ip)
    except socket.error:
        return jsonify({'error': 'Invalid IP address'}), 400
    
    shares = scan_nas_shares(nas_ip)
    return jsonify({
        'nas_ip': nas_ip,
        'shares': shares
    })

@app.route('/api/plex/rename', methods=['POST'])
def plex_rename():
    """Rename a file to be Plex-compliant"""
    data = request.get_json()
    if not data or 'file_path' not in data or 'media_type' not in data:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    file_path = data['file_path']
    media_type = data['media_type']  # 'movie', 'tv', 'book'
    location = data.get('location', 'local')  # 'local' or 'nas'
    
    # Security check: ensure the path is within allowed directories
    if location == 'local':
        root = app.config['LOCAL_ROOT']
    else:
        root = app.config['NAS_ROOT']
    
    if not is_safe_path(root, file_path):
        return jsonify({'error': 'Access denied'}), 403
    
    full_path = os.path.join(root, file_path)
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Generate new name based on media type
    new_name = None
    if media_type == 'movie':
        new_name = get_plex_movie_name(full_path)
    elif media_type == 'tv':
        new_name = get_plex_tv_name(full_path)
    elif media_type == 'book':
        new_name = get_plex_book_name(full_path)
    else:
        return jsonify({'error': 'Invalid media type'}), 400
    
    # Construct the new full path
    dir_path = os.path.dirname(full_path)
    new_path = os.path.join(dir_path, new_name)
    
    # Check if the new path already exists
    if os.path.exists(new_path):
        return jsonify({'error': 'A file with the new name already exists'}), 409
    
    try:
        # Rename the file
        os.rename(full_path, new_path)
        
        # Update the database if we have a record for this file
        db = get_db()
        # Compute the new relative path from the root
        new_relative_path = os.path.relpath(new_path, root)
        # Update the record: note that we store the path relative to the root and the location
        db.execute(
            'UPDATE files SET path = ? WHERE path = ? AND location = ?',
            (new_relative_path, file_path, location)
        )
        db.commit()
        
        return jsonify({
            'original_path': file_path,
            'original_name': os.path.basename(file_path),
            'new_name': new_name,
            'new_path': os.path.relpath(new_path, root),
            'message': 'File renamed successfully'
        })
    except OSError as e:
        return jsonify({'error': f'Failed to rename file: {str(e)}'}), 500

@app.route('/api/transcode', methods=['POST'])
def transcode_file():
    """Transcode a media file using FFmpeg"""
    data = request.get_json()
    if not data or 'file_path' not in data:
        return jsonify({'error': 'Missing file_path parameter'}), 400
    
    file_path = data['file_path']
    location = data.get('location', 'local')
    target_format = data.get('format', 'mp4').lower()  # Default to MP4
    quality = data.get('quality', 'medium')  # high, medium, low
    
    # Map quality to ffmpeg preset (simplified)
    quality_map = {
        'high': 'slow',
        'medium': 'medium',
        'low': 'fast'
    }
    preset = quality_map.get(quality, 'medium')
    
    # Security check
    if location == 'local':
        root = app.config['LOCAL_ROOT']
    else:
        root = app.config['NAS_ROOT']
    
    if not is_safe_path(root, file_path):
        return jsonify({'error': 'Access denied'}), 403
    
    full_path = os.path.join(root, file_path)
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return jsonify({'error': 'FFmpeg is not installed or not accessible'}), 500
    
    # Construct output file path: same directory, same basename, new extension
    # We'll add _transcoded before extension to avoid overwriting
    base, ext = os.path.splitext(full_path)
    # Remove any existing _transcoded suffix to avoid duplication
    if base.endswith('_transcoded'):
        base = base[:-len('_transcoded')]
    output_path = f"{base}_transcoded.{target_format}"
    
    # Build ffmpeg command
    # Use libx264 for video, copy audio if possible; simple approach: re-encode video and audio
    # For simplicity, we'll use preset and target format; note: target format must be supported by ffmpeg
    cmd = [
        'ffmpeg',
        '-i', full_path,
        '-c:v', 'libx264',
        '-preset', preset,
        '-c:a', 'aac',
        '-b:a', '128k',
        output_path
    ]
    
    try:
        # Run ffmpeg
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        if result.returncode != 0:
            return jsonify({'error': f'FFmpeg failed: {result.stderr}'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Transcoding timed out'}), 500
    except Exception as e:
        return jsonify({'error': f'Transcoding error: {str(e)}'}), 500
    
    # Verify output file exists
    if not os.path.exists(output_path):
        return jsonify({'error': 'Transcoding completed but output file not found'}), 500
    
    # Compute relative paths for response
    rel_input = os.path.relpath(full_path, root)
    rel_output = os.path.relpath(output_path, root)
    
    return jsonify({
        'original_path': rel_input,
        'original_name': os.path.basename(full_path),
        'transcoded_path': rel_output,
        'transcoded_name': os.path.basename(output_path),
        'target_format': target_format,
        'message': 'Transcoding completed successfully'
    })

@app.route('/api/scan/large-files')
def scan_large_files():
    """Scan for large files (NCDU-like functionality)"""
    location = request.args.get('location', 'local')
    path = request.args.get('path', '')
    min_size = int(request.args.get('min_size', 100 * 1024 * 1024))  # Default 100MB
    
    if location == 'local':
        root = app.config['LOCAL_ROOT']
    else:
        root = app.config['NAS_ROOT']
    
    full_path = os.path.join(root, path)
    
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return jsonify({'error': 'Path not found'}), 404
    
    large_files = []
    
    try:
        for root_dir, dirs, files in os.walk(full_path):
            # Security check: ensure we're still within allowed directory
            if not is_safe_path(root, os.path.relpath(root_dir, root)):
                continue
                
            for file in files:
                file_path = os.path.join(root_dir, file)
                try:
                    size = os.path.getsize(file_path)
                    if size >= min_size:
                        rel_path = os.path.relpath(file_path, root)
                        large_files.append({
                            'name': file,
                            'path': rel_path,
                            'size': size,
                            'size_formatted': format_file_size(size),
                            'media_type': get_media_type(file) if '.' in file else 'other',
                            'is_dir': False
                        })
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue
    except Exception as e:
        return jsonify({'error': f'Error scanning directory: {str(e)}'}), 500
    
    # Sort by size descending
    large_files.sort(key=lambda x: x['size'], reverse=True)
    
    return jsonify({
        'scan_path': path or '/',
        'location': location,
        'min_size': min_size,
        'min_size_formatted': format_file_size(min_size),
        'large_files': large_files,
        'count': len(large_files)
    })

@app.route('/api/tree')
def get_tree():
    """Get directory tree structure for a given location and path"""
    location = request.args.get('location', 'local')
    path = request.args.get('path', '')
    
    if location == 'local':
        root = app.config['LOCAL_ROOT']
    else:
        root = app.config['NAS_ROOT']
    
    full_path = os.path.join(root, path)
    
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return jsonify({'error': 'Path not found'}), 404
    
    # Security check
    if not is_safe_path(root, path):
        return jsonify({'error': 'Access denied'}), 403
    
    items = []
    try:
        with os.scandir(full_path) as entries:
            for entry in entries:
                # Skip hidden files and directories (those starting with .)
                if entry.name.startswith('.'):
                    continue
                    
                stat = entry.stat()
                items.append({
                    'name': entry.name,
                    'path': os.path.relpath(entry.path, root),
                    'size': stat.st_size if entry.is_file() else 0,
                    'is_dir': entry.is_dir(),
                    'media_type': get_media_type(entry.name) if entry.is_file() else None
                })
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Sort items: directories first, then files, both alphabetically
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    
    return jsonify({
        'current_path': path,
        'items': items
    })

@app.route('/api/config')
def get_config():
    """Return current configuration"""
    return jsonify({
        'LOCAL_ROOT': app.config['LOCAL_ROOT'],
        'NAS_ROOT': app.config['NAS_ROOT']
    })

@app.route('/api/diskusage')
def get_disk_usage():
    """Get disk usage for LOCAL_ROOT and NAS_ROOT"""
    usage = {}
    for name, root in [('LOCAL', app.config['LOCAL_ROOT']), ('NAS', app.config['NAS_ROOT'])]:
        try:
            total, used, free = shutil.disk_usage(root)
            usage[name.lower()] = {
                'total': total,
                'used': used,
                'free': free,
                'total_str': format_file_size(total),
                'used_str': format_file_size(used),
                'free_str': format_file_size(free),
                'percent_used': round(used / total * 100, 1) if total > 0 else 0
            }
        except Exception as e:
            # If path doesn't exist or no permission, mark error
            usage[name.lower()] = {'error': str(e)}
    return jsonify(usage)

def format_file_size(bytes):
    if bytes == 0:
        return '0 Bytes'
    k = 1024
    sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while bytes >= k and i < len(sizes) - 1:
        bytes /= k
        i += 1
    return f"{bytes:.1f} {sizes[i]}"

def get_media_type(filename):
    ext = Path(filename).suffix.lower()
    if ext in ['.mkv', '.mp4', '.avi', '.mov']:
        return 'movie'
    elif ext in ['.m4v']:  # TV shows often use m4v
        return 'tv'
    elif ext in ['.epub', '.pdf', '.mobi']:
        return 'book'
    else:
        return 'other'

def discover_ugreen_nas():
    """Discover UGreen NAS devices on the local network"""
    nas_devices = []
    
    # Get local network info
    try:
        # Get local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Extract network prefix (assuming /24 network)
        network_prefix = '.'.join(local_ip.split('.')[:-1]) + '.'
        
        # Common UGreen NAS ports to check
        ports = [80, 443, 8080, 8081]  # HTTP, HTTPS, and common alternative ports
        
        # Scan a limited range for responsiveness (in practice, you might want to be more selective)
        for i in range(1, 255):
            target_ip = network_prefix + str(i)
            
            # Skip if it's our own IP
            if target_ip == local_ip:
                continue
                
            # Quick check if host is reachable (ping-like)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)  # Very short timeout
                result = sock.connect_ex((target_ip, 80))  # Try HTTP port first
                sock.close()
                
                if result == 0:  # Port is open
                    # Try to get more info about the device
                    try:
                        # Attempt to get hostname
                        hostname = socket.gethostbyaddr(target_ip)[0]
                    except:
                        hostname = target_ip
                    
                    # Check if it might be a UGreen device (simple heuristic)
                    # In a real implementation, you'd check for specific UGreen signatures
                    nas_devices.append({
                        'ip': target_ip,
                        'hostname': hostname,
                        'type': 'potential_nas'
                    })
            except:
                pass  # Ignore errors and continue
                
    except Exception as e:
        print(f"Error during NAS discovery: {e}")
    
    return nas_devices

def scan_nas_shares(nas_ip):
    """Scan for available shares on a discovered NAS"""
    shares = []
    
    # Common NAS share paths to check
    common_paths = [
        '/volume1/',
        '/volume2/',
        '/share/',
        '/public/',
        '/homes/',
        '/usb/',
        '/external/'
    ]
    
    # In a real implementation, you would use proper NAS API calls
    # or SMB/NFS probing to detect actual shares
    # For now, we'll return a placeholder
    
    return shares

# Background thread for NAS discovery
nas_discovery_thread = None
discovered_nas_devices = []
discovery_active = False

def nas_discovery_worker():
    """Background worker for NAS discovery"""
    global discovered_nas_devices, discovery_active
    
    while discovery_active:
        try:
            # Perform discovery
            devices = discover_ugreen_nas()
            discovered_nas_devices = devices
            
            # Wait before next discovery cycle
            time.sleep(30)  # Discover every 30 seconds
        except Exception as e:
            print(f"Error in NAS discovery worker: {e}")
            time.sleep(5)

def start_nas_discovery():
    """Start the NAS discovery background thread"""
    global nas_discovery_thread, discovery_active
    
    if not discovery_active:
        discovery_active = True
        nas_discovery_thread = threading.Thread(target=nas_discovery_worker)
        nas_discovery_thread.daemon = True
        nas_discovery_thread.start()

def stop_nas_discovery():
    """Stop the NAS discovery background thread"""
    global discovery_active
    discovery_active = False

def is_safe_path(root, path):
    """Check if the path is within the root directory"""
    # Resolve relative paths and symlinks
    real_root = os.path.realpath(root)
    real_path = os.path.realpath(os.path.join(root, path))
    return os.path.commonpath([real_root, real_path]) == real_root

def get_plex_movie_name(filepath):
    """Generate a Plex-compliant movie name"""
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    
    # Clean up the name: remove common unwanted patterns
    cleaned_name = re.sub(r'[._\-]', ' ', name)
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    
    # Try to extract year if present (e.g., "Movie Name (2023)")
    year_match = re.search(r'\((\d{4})\)', cleaned_name)
    year = year_match.group(1) if year_match else ""
    
    # Remove year from name if found
    if year_match:
        cleaned_name = re.sub(r'\s*\(\d{4}\)\s*', ' ', cleaned_name).strip()
    
    # Format according to Plex standards: "Movie Name (Year)[ext]"
    if year:
        return f"{cleaned_name} ({year}){ext}"
    else:
        return f"{cleaned_name}{ext}"

def get_plex_tv_name(filepath):
    """Generate a Plex-compliant TV show name"""
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    
    # Clean up the name
    cleaned_name = re.sub(r'[._\-]', ' ', name)
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    
    # Try to extract season and episode info (e.g., "S01E02", "1x02", "Season 1 Episode 2")
    se_patterns = [
        r'[._\-]?[Ss](\d+)[._\-]?[Ee](\d+)',  # S01E02
        r'[._\-]?(\d+)[xX](\d+)',              # 1x02
        r'[._\-]?[Ss]eason[._\-]?(\d+)[._\-]?[Ee]pisode[._\-]?(\d+)'  # Season 1 Episode 2
    ]
    
    season = ""
    episode = ""
    
    for pattern in se_patterns:
        match = re.search(pattern, cleaned_name)
        if match:
            season = match.group(1).zfill(2)  # Pad with zero
            episode = match.group(2).zfill(2)
            # Remove the matched part from the name
            cleaned_name = re.sub(pattern, '', cleaned_name).strip()
            break
    
    # Clean up any remaining separators
    cleaned_name = re.sub(r'[._\-]+$', '', cleaned_name)  # Remove trailing separators
    cleaned_name = re.sub(r'^[._\-]+', '', cleaned_name)  # Remove leading separators
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    
    # Format according to Plex standards: "Show Name - S01E02 - Episode Title.ext"
    # Since we don't have episode title info, we'll just use: "Show Name - S01E02.ext"
    if season and episode:
        return f"{cleaned_name} - S{season}E{episode}{ext}"
    else:
        # If we can't find season/episode, just clean up the name
        return f"{cleaned_name}{ext}"

def get_plex_book_name(filepath):
    """Generate a Plex-compliant book name"""
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    
    # Clean up the name: remove common unwanted patterns
    cleaned_name = re.sub(r'[._\-]', ' ', name)
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    
    # Try to extract author if present in format "Author - Title" or "Title - Author"
    parts = re.split(r'\s[\-–]\s', cleaned_name, 1)
    if len(parts) == 2:
        # Assume first part is author, second is title (common format)
        # For books, Plex prefers "Title (Author).ext" or just clean title
        # We'll keep it simple and just clean the title part
        cleaned_name = parts[1] if len(parts[1]) > len(parts[0]) else parts[0]
    
    return f"{cleaned_name}{ext}"

if __name__ == '__main__':
    init_db()
    # Start NAS discovery in background
    start_nas_discovery()
    app.run(debug=True, host='127.0.0.1', port=5555)