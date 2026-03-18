document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const modelSelect = document.getElementById('model-select');
    const fileInfo = document.getElementById('selected-file-info');
    const tasksContainer = document.getElementById('tasks-container');
    
    // Stats elements
    const statTotal = document.getElementById('stat-total');
    const statActive = document.getElementById('stat-active');
    const statCompleted = document.getElementById('stat-completed');
    
    let currentFile = null;

    // --- Drag and Drop Logic ---
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    ['dragleave', 'dragend'].forEach(type => {
        dropZone.addEventListener(type, () => {
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        currentFile = file;
        const fileSize = (file.size / (1024 * 1024)).toFixed(2);
        
        fileInfo.innerHTML = `
            <div>
                <strong>${file.name}</strong> 
                <span style="color: var(--text-muted); font-size: 0.8rem; margin-left: 0.5rem">${fileSize} MB</span>
            </div>
            <button class="remove-file" id="remove-file" title="Remove file">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;
        fileInfo.className = 'selected-file-info';
        uploadBtn.disabled = false;

        document.getElementById('remove-file').addEventListener('click', clearFile);
    }

    function clearFile(e) {
        if(e) e.stopPropagation();
        currentFile = null;
        fileInput.value = '';
        fileInfo.className = 'selected-file-hidden';
        uploadBtn.disabled = true;
    }

    // --- Upload Logic ---
    uploadBtn.addEventListener('click', async () => {
        if (!currentFile) return;

        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('model', modelSelect.value);

        const originalText = uploadBtn.textContent;
        uploadBtn.textContent = 'Uploading...';
        uploadBtn.disabled = true;

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                clearFile(); // Reset UI
                pollStatus(); // Immediately poll after upload
            } else {
                const data = await response.json();
                alert(`Upload failed: ${data.error || 'Server error'}`);
            }
        } catch (error) {
            alert('Upload failed: ' + error.message);
        } finally {
            uploadBtn.textContent = originalText;
            uploadBtn.disabled = !!currentFile ? false : true;
        }
    });

    // --- Queue Pooling Logic ---
    function createTaskCard(task) {
        let actionHTML = '';
        if (task.status === 'completed' && task.result_file) {
            actionHTML = `
                <a href="/download/${task.id}" class="task-action" download>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Download .SRT
                </a>
            `;
        } else if (task.status === 'error') {
            actionHTML = `<span style="color: var(--error); font-size: 0.85rem">Failed</span>`;
        }

        return `
            <div class="task-card" id="task-${task.id}">
                <div class="task-header">
                    <div>
                        <div class="task-title">${task.filename}</div>
                        <div class="task-model">Model: ${task.model}</div>
                    </div>
                    <span class="task-status-badge status-${task.status}">${task.status}</span>
                </div>
                <div class="task-body">
                    <div class="task-progress">${task.progress || ''}</div>
                    ${actionHTML}
                </div>
            </div>
        `;
    }

    async function pollStatus() {
        try {
            const response = await fetch('/status');
            const data = await response.json();
            const tasks = data.tasks || [];

            // Update stats
            statTotal.textContent = tasks.length;
            statActive.textContent = tasks.filter(t => t.status === 'pending' || t.status === 'processing').length;
            statCompleted.textContent = tasks.filter(t => t.status === 'completed').length;

            if (tasks.length === 0) {
                tasksContainer.innerHTML = '<div class="empty-state">No transcriptions in the queue.</div>';
                return;
            }

            // Reverse to show latest first
            const html = tasks.reverse().map(task => createTaskCard(task)).join('');
            
            // Only update DOM if HTML changed to prevent flickering
            if (tasksContainer.dataset.last_html !== html) {
                tasksContainer.innerHTML = html;
                tasksContainer.dataset.last_html = html;
            }

        } catch (error) {
            console.error('Failed to poll status:', error);
        }
    }

    // Start polling every 2 seconds
    pollStatus();
    setInterval(pollStatus, 2000);
});
