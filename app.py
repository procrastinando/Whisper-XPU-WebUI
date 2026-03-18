import os
import time
import uuid
import queue
import threading
import subprocess
import re
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1GB limit

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Global queue and task state
task_queue = queue.Queue()
tasks_state = {}

# Available models
WHISPER_MODELS = [
    "tiny.en", "tiny", "base.en", "base", "small.en", "small", 
    "medium.en", "medium", "large-v1", "large-v2", "large-v3", "large"
]

def worker():
    while True:
        task_id = task_queue.get()
        task = tasks_state.get(task_id)
        if not task:
            task_queue.task_done()
            continue
            
        task['status'] = 'processing'
        task['progress'] = 'Starting transcription...'
        
        filepath = task['filepath']
        model = task['model']
        filename = task['filename']
        name_only = os.path.splitext(filename)[0]
        output_srt = os.path.join(app.config['OUTPUT_FOLDER'], f"{task_id}_{name_only}.srt")
        
        # Command syntax from documentation:
        # whisper <file> --device xpu --model <model> --task transcribe
        # Note: Depending on whisper version `--output_format srt --output_dir XXX` is supported.
        # But per the requirement, we will capture stdout manually to create the SRT file to be safe.
        
        cmd = [
            "whisper", filepath,
            "--device", "xpu",
            "--model", model,
            "--task", "transcribe"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            srt_lines = []
            srt_index = 1
            
            # regex to capture standard whisper output: [00:00.000 --> 00:08.000]  Some text
            time_regex = re.compile(r'\[(\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}\.\d{3})\]\s*(.*)')
            
            # regex for download progress handling: e.g. 10%|████▍ | 20M/200M
            download_regex = re.compile(r'(\d+)%\|')
            
            for line in process.stdout:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                # Check for download progress
                dl_match = download_regex.search(line_stripped)
                if dl_match:
                    task['progress'] = f"Downloading model: {dl_match.group(1)}%"
                    continue
                elif "Downloading" in line_stripped and "model" in line_stripped.lower():
                    task['progress'] = "Downloading model..."
                    continue
                    
                # Parsing the actual transcription block
                match = time_regex.search(line_stripped)
                if match:
                    task['progress'] = f"Transcribing at {match.group(1)}"
                    start_time = match.group(1).replace('.', ',')
                    end_time = match.group(2).replace('.', ',')
                    text = match.group(3)
                    
                    # Convert [00:00.000] format to proper SRT format: 00:00:00,000
                    def format_time(t_str):
                        # Add hours if missing
                        parts = t_str.split(':')
                        if len(parts) == 2:
                            return f"00:{parts[0]}:{parts[1]}"
                        return t_str
                        
                    srt_lines.append(str(srt_index))
                    srt_lines.append(f"{format_time(start_time)} --> {format_time(end_time)}")
                    srt_lines.append(text)
                    srt_lines.append("") # Empty line denotes end of block
                    srt_index += 1
            
            process.wait()
            
            if process.returncode == 0:
                with open(output_srt, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(srt_lines))
                task['status'] = 'completed'
                task['result_file'] = f"{task_id}_{name_only}.srt"
                task['progress'] = "Done"
            else:
                task['status'] = 'error'
                task['progress'] = f"Whisper exited with code {process.returncode}"
                
        except Exception as e:
            task['status'] = 'error'
            task['progress'] = str(e)
            
        task_queue.task_done()

# Start background worker thread
threading.Thread(target=worker, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html', models=WHISPER_MODELS)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    model = request.form.get('model', 'base')
    if model not in WHISPER_MODELS:
        model = 'base'
        
    filename = secure_filename(file.filename)
    task_id = str(uuid.uuid4())
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
    file.save(filepath)
    
    task = {
        'id': task_id,
        'filename': filename,
        'filepath': filepath,
        'model': model,
        'status': 'pending',
        'progress': 'Added to queue',
        'created_at': time.time()
    }
    
    tasks_state[task_id] = task
    task_queue.put(task_id)
    
    return jsonify({'message': 'File queued', 'task_id': task_id})

@app.route('/status', methods=['GET'])
def status():
    # Return all tasks sorted by creation time
    sorted_tasks = sorted(tasks_state.values(), key=lambda x: x['created_at'])
    
    # We strip filepath before sending
    safe_tasks = []
    for t in sorted_tasks:
        safe_copy = t.copy()
        safe_copy.pop('filepath', None)
        safe_tasks.append(safe_copy)
        
    return jsonify({'tasks': safe_tasks})

@app.route('/download/<task_id>', methods=['GET'])
def download(task_id):
    task = tasks_state.get(task_id)
    if not task or task['status'] != 'completed':
        return "File not found or not ready", 404
        
    srt_file = os.path.join(app.config['OUTPUT_FOLDER'], task['result_file'])
    if not os.path.exists(srt_file):
         return "File missing on disk", 404
         
    return send_file(
        srt_file, 
        as_attachment=True, 
        download_name=f"{os.path.splitext(task['filename'])[0]}.srt"
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
