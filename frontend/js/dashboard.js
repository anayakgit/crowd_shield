// Socket.IO Connection
const socket = io('http://localhost:5000');

// DOM Elements
// const webcamBtn = document.getElementById('webcamBtn');
const uploadBtn = document.getElementById('uploadBtn');
const stopBtn = document.getElementById('stopBtn');
const videoInput = document.getElementById('videoInput');
const videoFeed = document.getElementById('videoFeed');
const videoPlaceholder = document.getElementById('videoPlaceholder');
// const digitalTwinFeed = document.getElementById('digitalTwinFeed');
// const twinPlaceholder = document.getElementById('twinPlaceholder');
const crowdCount = document.querySelector('.count-value');
const riskLevel = document.getElementById('riskLevel');
const trendValue = document.getElementById('trendValue');
const alertsList = document.getElementById('alertsList');
const alertCount = document.getElementById('alertCount');
// const tempValue = document.getElementById('tempValue');
// const noiseValue = document.getElementById('noiseValue');
// const humidityValue = document.getElementById('humidityValue');
// const aqiValue = document.getElementById('aqiValue');
// const adviceContent = document.getElementById('adviceContent');
// const refreshAdvice = document.getElementById('refreshAdvice');
// const notifyBtn = document.getElementById('notifyBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const systemStatus = document.getElementById('systemStatus');

// State
let isProcessing = false;
let currentRiskLevel = 'LOW';

// Event Listeners
// webcamBtn.addEventListener('click', startWebcam);
uploadBtn.addEventListener('click', () => videoInput.click());
videoInput.addEventListener('change', uploadVideo);
stopBtn.addEventListener('click', stopProcessing);
// refreshAdvice.addEventListener('click', fetchEvacuationAdvice);
// notifyBtn.addEventListener('click', notifyAuthorities);

// Socket.IO Events
socket.on('connect', () => {
    console.log('Connected to server');
    updateSystemStatus(true);
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateSystemStatus(false);
});

socket.on('frame_data', (data) => {
    // Update video feed
    videoFeed.src = 'data:image/jpeg;base64,' + data.frame;
    videoFeed.classList.add('active');
    videoPlaceholder.classList.add('hidden');

    // Update digital twin
    // digitalTwinFeed.src = 'data:image/jpeg;base64,' + data.digital_twin;
    // digitalTwinFeed.classList.add('active');
    // twinPlaceholder.classList.add('hidden');

    // Update crowd count
    crowdCount.textContent = data.crowd_count;

    // Update risk level
    updateRiskLevel(data.risk_level);

    // Update alerts
    updateAlerts(data.alerts);

    // Update IoT data
    // updateIoTData(data.iot_data);
});

socket.on('stream_end', (data) => {
    console.log('Stream ended:', data.message);
    showNotification('Video ended', 'info');
});

// Functions
async function startWebcam() {
    try {
        showLoading(true);

        const response = await fetch('/api/start_webcam', {
            method: 'POST'
        });

        const result = await response.json();

        if (response.ok) {
            isProcessing = true;
            updateControlButtons();
            socket.emit('start_stream');
            showNotification('Webcam started successfully', 'success');
        } else {
            showNotification('Failed to start webcam: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error starting webcam:', error);
        showNotification('Error starting webcam', 'error');
    } finally {
        showLoading(false);
    }
}

async function uploadVideo() {
    const file = videoInput.files[0];
    if (!file) return;

    try {
        showLoading(true);

        const formData = new FormData();
        formData.append('video', file);

        const response = await fetch('/api/upload_video', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            isProcessing = true;
            updateControlButtons();
            socket.emit('start_stream');
            showNotification('Video uploaded successfully', 'success');
        } else {
            showNotification('Failed to upload video: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error uploading video:', error);
        showNotification('Error uploading video', 'error');
    } finally {
        showLoading(false);
    }
}

async function stopProcessing() {
    try {
        const response = await fetch('/api/stop_processing', {
            method: 'POST'
        });

        if (response.ok) {
            isProcessing = false;
            updateControlButtons();

            // Reset UI
            videoFeed.classList.remove('active');
            videoPlaceholder.classList.remove('hidden');
            // digitalTwinFeed.classList.remove('active');
            // twinPlaceholder.classList.remove('hidden');

            showNotification('Processing stopped', 'info');
        }
    } catch (error) {
        console.error('Error stopping processing:', error);
        showNotification('Error stopping processing', 'error');
    }
}

async function fetchEvacuationAdvice() {
    try {
        refreshAdvice.style.transform = 'rotate(360deg)';

        const response = await fetch('/api/get_evacuation_advice');
        const result = await response.json();

        if (response.ok) {
            adviceContent.innerHTML = formatAdvice(result.advice);
        } else {
            adviceContent.innerHTML = '<p class="advice-loading">Failed to generate advice</p>';
        }
    } catch (error) {
        console.error('Error fetching advice:', error);
        adviceContent.innerHTML = '<p class="advice-loading">Error fetching advice</p>';
    } finally {
        setTimeout(() => {
            refreshAdvice.style.transform = 'rotate(0deg)';
        }, 600);
    }
}

function formatAdvice(text) {
    // Convert markdown-style formatting to HTML
    let formatted = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    return '<p>' + formatted + '</p>';
}

function updateRiskLevel(level) {
    currentRiskLevel = level;
    riskLevel.textContent = level;
}

function updateAlerts(alerts) {
    alertCount.textContent = alerts.length;

    if (alerts.length === 0) {
        alertsList.innerHTML = '<div class="no-alerts">No active alerts</div>';
        return;
    }

    let html = '';
    alerts.forEach(alert => {
        const severityClass = alert.severity.toLowerCase();
        html += `
            <div class="alert-item ${severityClass}">
                <div class="alert-severity">${alert.severity}</div>
                <div class="alert-message">${alert.message}</div>
            </div>
        `;
    });

    alertsList.innerHTML = html;
}

function updateIoTData(data) {
    if (!data) return;

    tempValue.textContent = data.temperature + '°C';
    noiseValue.textContent = data.noise_level + ' dB';
    humidityValue.textContent = data.humidity + '%';
    aqiValue.textContent = 'AQI ' + data.air_quality_index;

    // Color code based on values
    updateSensorColor(tempValue, data.temperature, [28, 32]);
    updateSensorColor(noiseValue, data.noise_level, [70, 85]);
    updateSensorColor(humidityValue, data.humidity, [70, 80]);
}

function updateSensorColor(element, value, thresholds) {
    if (value > thresholds[1]) {
        element.style.color = 'var(--accent-danger)';
    } else if (value > thresholds[0]) {
        element.style.color = 'var(--accent-warning)';
    } else {
        element.style.color = 'var(--accent-success)';
    }
}

function updateControlButtons() {
    // webcamBtn.disabled = isProcessing;
    uploadBtn.disabled = isProcessing;
    stopBtn.disabled = !isProcessing;
}

function updateSystemStatus(connected) {
    if (connected) {
        systemStatus.textContent = 'STATUS: Connected';
    } else {
        systemStatus.textContent = 'STATUS: Offline';
    }
}

function showLoading(show) {
    if (show) {
        loadingOverlay.classList.add('active');
    } else {
        loadingOverlay.classList.remove('active');
    }
}

function showNotification(message, type) {
    console.log(`Notification [${type}]: ${message}`);
}

async function notifyAuthorities() {
    try {
        const response = await fetch('/api/notify_authorities', {
            method: 'POST'
        });

        const result = await response.json();

        if (response.ok) {
            showNotification(result.message, 'success');
            // Flash the button
            notifyBtn.style.animation = 'pulse 0.5s ease 3';
        } else {
            showNotification('Failed to notify: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error notifying authorities:', error);
        showNotification('Error sending notification', 'error');
    }
}

// Auto-fetch risk trend
setInterval(async () => {
    if (!isProcessing) return;

    try {
        const response = await fetch('/api/get_risk_data');
        const data = await response.json();

        if (data.trend) {
            trendValue.textContent = capitalizeFirst(data.trend);
        }
    } catch (error) {
        console.error('Error fetching risk trend:', error);
    }
}, 5000);

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// Initialize
updateControlButtons();
console.log('Dashboard initialized');
