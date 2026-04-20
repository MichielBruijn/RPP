from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename
import subprocess
import threading
import time
import os
import re

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get-printer-ip', methods=['GET'])
def get_printer_ip():
    try:
        with open('printer_ip.txt', 'r') as file:
            ip = file.read().strip()
            print(f"Printer IP read: {ip}", flush=True)
            return jsonify({'ip': ip})
    except Exception as e:
        print(f"Error reading printer IP: {e}", flush=True)
        return jsonify({'error': str(e)})

def read_printer_ip():
    try:
        with open('printer_ip.txt', 'r') as file:
            return file.read().strip()
    except Exception as e:
        print(f"Error reading printer IP: {e}", flush=True)
        return None

@app.route('/set-printer-ip', methods=['POST'])
def set_printer_ip():
    try:
        new_ip = request.json.get('ip')
        print(f"Updating printer IP to: {new_ip}", flush=True)
        with open('printer_ip.txt', 'w') as file:
            file.write(new_ip)
        print("Printer IP updated successfully.", flush=True)
        return jsonify({'message': 'IP updated'})
    except Exception as e:
        print(f"Error updating printer IP: {e}", flush=True)
        return jsonify({'error': str(e)})

@app.route('/print-status')
def print_status():
    printer_ip = read_printer_ip()
    if printer_ip is None:
        return jsonify({'error': 'Could not read printer IP address.'})

    try:
        cmd = ['./cassini.py', '-p', printer_ip, 'status']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = result.stdout.strip()

        is_online = result.returncode == 0 and bool(output)

        match = re.search(r'Layers: (\d+)/(\d+)', output)
        if match:
            current_layer, total_layers = match.groups()
            if int(total_layers) > 0:
                progress = (int(current_layer) / int(total_layers)) * 100
            else:
                progress = 0
        else:
            current_layer, total_layers, progress = 'N/A', 'N/A', 0

        return jsonify({
            'status': output,
            'current_layer': current_layer,
            'total_layers': total_layers,
            'progress': progress,
            'is_online': is_online
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Printer status request timed out.'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'message': 'File uploaded successfully', 'filename': filename})
    return jsonify({'error': 'No file'})


@app.route('/files')
def list_files():
    files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if not f.startswith('.')]
    files_info = []
    for file in files:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file)
        size = os.path.getsize(filepath) / (1024 * 1024)  # Convert to MB
        files_info.append({'name': file, 'size': round(size, 2)})
    return jsonify(files_info)


progress_status = {}
print_lock = threading.Lock()

def upload_and_print(printer_ip, filepath, filename):
    """Upload file to printer and start printing in one MQTT session."""
    print(f"Starting upload+print for {filename}", flush=True)

    try:
        # Single command: upload AND start printing over one MQTT connection
        cmd = ['./cassini.py', '--printer', printer_ip, 'upload', '--start-printing', filepath]
        print(f"Running: {cmd}", flush=True)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(f"stdout: {result.stdout}", flush=True)
        if result.stderr:
            print(f"stderr: {result.stderr}", flush=True)
        if result.returncode != 0:
            print(f"Exit code: {result.returncode}", flush=True)
        else:
            print(f"Upload+print completed successfully for {filename}", flush=True)

    except subprocess.TimeoutExpired:
        print(f"Command timed out after 120s for {filename}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

    progress_status[filename] = 100
    # Clean up after a delay to avoid memory leak
    def cleanup():
        import time
        time.sleep(10)
        progress_status.pop(filename, None)
    threading.Thread(target=cleanup, daemon=True).start()

def run_print_job(printer_ip, filepath, filename):
    """Wrapper that holds the print lock during the entire job."""
    with print_lock:
        progress_status[filename] = 50
        upload_and_print(printer_ip, filepath, filename)

@app.route('/progress/<filename>')
def get_progress(filename):
    return jsonify({'progress': progress_status.get(filename, 0)})


@app.route('/print-file', methods=['POST'])
def print_file():
    printer_ip = read_printer_ip()
    if printer_ip is None:
        return jsonify({'error': 'Could not read printer IP address.'})

    filename = request.json.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided.'})
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(filepath):
        return jsonify({'error': f'File {filename} not found.'})

    if print_lock.locked():
        return jsonify({'error': 'A print job is already in progress. Please wait.'})

    print(f"Queueing print job for {filename}", flush=True)
    job_thread = threading.Thread(target=run_print_job, args=(printer_ip, filepath, filename))
    job_thread.start()

    return jsonify({'message': f'Uploading and printing {filename}...'})


@app.route('/delete-file', methods=['POST'])
def delete_file():
    filename = request.json.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided.'})
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        os.remove(filepath)
        return jsonify({'message': f'File {filename} deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')