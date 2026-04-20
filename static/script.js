// script.js - Complete code for printer status management, file display, upload, and deletion

let selectedFile = null;

document.addEventListener('DOMContentLoaded', (event) => {
    fetchPrintStatus();
    fetchFiles();
    loadPrinterIP();
});

function loadPrinterIP() {
    fetch('/get-printer-ip')
        .then(response => response.json())
        .then(data => {
            if (data.ip) {
                document.getElementById('printer-ip').value = data.ip;
            } else {
                console.error('Error loading IP:', data.error);
            }
        });
}

// Save the IP address to the server
function saveIP() {
    let ipField = document.getElementById('printer-ip');
    let saveBtn = document.querySelector('.btn-save');
    let newIP = ipField.value;

    fetch('/set-printer-ip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip: newIP }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                alert('Printer adres opgeslagen!');
                ipField.readOnly = true;
                saveBtn.style.display = 'none';
            } else {
                console.error('Error saving IP:', data.error);
                alert('Fout bij opslaan: ' + data.error);
            }
        });
}

function editIP() {
    let ipField = document.getElementById('printer-ip');
    let saveBtn = document.querySelector('.btn-save');

    ipField.readOnly = false;
    ipField.focus();
    ipField.select();

    saveBtn.style.display = 'inline-block';
}

function uploadFile() {
    let input = document.createElement('input');
    input.type = 'file';
    input.onchange = e => {
        let file = e.target.files[0];
        let formData = new FormData();
        formData.append('file', file);

        showLoadingIndicator('Uploading...');

        let xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);

        xhr.upload.onprogress = function (e) {
            if (e.lengthComputable) {
                let percentComplete = (e.loaded / e.total) * 100;
                updateLoadingPercentage(percentComplete);
            }
        };

        xhr.onloadstart = function (e) {
            updateLoadingPercentage(0); // Initialize progress bar at 0%
        };

        xhr.onload = function () {
            if (xhr.status === 200) {
                updateLoadingPercentage(100); // Complete, set progress to 100%
                hideLoadingIndicator();
                alert('Upload complete!');
                fetchFiles(); // Refresh list after upload
            } else {
                alert('An error occurred during the upload.');
            }
        };

        xhr.onerror = function () {
            hideLoadingIndicator();
            alert('An error occurred during the upload.');
        };

        xhr.send(formData);
    };
    input.click(); // Open file selection dialog
}

function printSelectedFile() {
    if (selectedFile) {
        showLoadingIndicator('Preparing print...');

        fetch('/print-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ filename: selectedFile }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    hideLoadingIndicator();
                } else {
                    checkProgress(selectedFile); // Start polling for progress
                    alert(data.message);
                }
            })
            .catch(error => {
                hideLoadingIndicator();
                console.error('Error:', error);
            });
    } else {
        alert("Please select a file first.");
    }
}

function updatePrintProgress(percent) {
    showLoadingIndicator(`Printing... (${percent}%)`);
    updateLoadingPercentage(percent);

    if (percent >= 100) {
        // Hide the loading indicator after a short delay so the user sees completion
        setTimeout(hideLoadingIndicator, 1000);
    }
}

// Show the loading indicator with message and percentage
function showLoadingIndicator(message) {
    let loadingDiv = document.getElementById('loading-indicator');
    if (!loadingDiv) {
        loadingDiv = document.createElement('div');
        loadingDiv.id = 'loading-indicator';
        loadingDiv.innerHTML = `
            <div class="loading-spinner"></div>
            <p id="loading-msg">${message}</p>
            <p id="loading-percentage">0%</p>`;
        document.body.appendChild(loadingDiv);
    } else {
        document.getElementById('loading-msg').innerText = message;
    }
}

function hideLoadingIndicator() {
    let loadingDiv = document.getElementById('loading-indicator');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

function updateLoadingPercentage(percent) {
    let percentageText = document.getElementById('loading-percentage');
    if (percentageText) {
        percentageText.innerText = `${percent.toFixed(2)}%`;
    }
}

function checkProgress(filename) {
    fetch(`/progress/${filename}`)
        .then(response => response.json())
        .then(data => {
            updatePrintProgress(data.progress);
            if (data.progress < 100) {
                setTimeout(() => checkProgress(filename), 1000); // Poll every second
            }
        })
        .catch(error => console.error('Error:', error));
}

function fetchPrintStatus() {
    fetch('/print-status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('status').innerText = data.status;
            let progressBar = document.getElementById('progress-bar');
            let progressText = document.getElementById('progress-text');

            let progressValue = parseFloat(data.progress).toFixed(2);
            if (progressBar) progressBar.style.width = progressValue + '%';
            if (progressText) progressText.innerText = progressValue + '%';

            // Update ONLINE/OFFLINE capsule
            const onlineStatusElement = document.getElementById('online-status');
            if (onlineStatusElement) {
                if (data.is_online) {
                    onlineStatusElement.className = 'online-status online';
                    onlineStatusElement.textContent = 'ONLINE';
                } else {
                    onlineStatusElement.className = 'online-status offline';
                    onlineStatusElement.textContent = 'OFFLINE';
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('status').innerText = 'Error loading status.';
        });
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function fetchFiles() {
    fetch('/files')
        .then(response => response.json())
        .then(filesInfo => {
            const tbody = document.getElementById('file-list').querySelector('tbody');
            tbody.innerHTML = '';
            filesInfo.forEach(fileInfo => {
                const tr = document.createElement('tr');
                if (selectedFile === fileInfo.name) tr.classList.add('selected');
                tr.addEventListener('click', () => selectFile(fileInfo.name));
                const tdName = document.createElement('td');
                tdName.textContent = fileInfo.name;
                const tdSize = document.createElement('td');
                tdSize.textContent = fileInfo.size + ' MB';
                tr.appendChild(tdName);
                tr.appendChild(tdSize);
                tbody.appendChild(tr);
            });
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('file-list').querySelector('tbody').innerHTML = '<tr><td colspan="2">Error loading files.</td></tr>';
        });
}

function selectFile(filename) {
    selectedFile = filename;
    document.querySelectorAll('.file-list tr').forEach(tr => {
        tr.classList.remove('selected');
    });
    const rows = [...document.querySelectorAll('.file-list tr')];
    const selectedRow = rows.find(tr => tr.cells[0].textContent === filename);
    if (selectedRow) {
        selectedRow.classList.add('selected');
    }
}

function deleteSelectedFile() {
    if (selectedFile) {
        if (!confirm(`Are you sure you want to delete ${selectedFile}?`)) return;

        fetch('/delete-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ filename: selectedFile }),
        })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                selectedFile = null;
                fetchFiles();
            })
            .catch(error => console.error('Error:', error));
    }
}

// Automatically update status every 5 seconds
setInterval(fetchPrintStatus, 5000);