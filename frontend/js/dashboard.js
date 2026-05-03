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
const lstmLevel = document.getElementById('lstmLevel');
const lstmScore = document.getElementById('lstmScore');
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
const alertEmailInput = document.getElementById('alertEmailInput');
const enableEmailAlerts = document.getElementById('enableEmailAlerts');
const saveEmailAlertBtn = document.getElementById('saveEmailAlertBtn');
const testEmailAlertBtn = document.getElementById('testEmailAlertBtn');
const emailAlertStatus = document.getElementById('emailAlertStatus');
const emailAlertEvents = document.getElementById('emailAlertEvents');

// State
let isProcessing = false;
let currentRiskLevel = 'LOW';

// Event Listeners
// webcamBtn.addEventListener('click', startWebcam);
uploadBtn.addEventListener('click', () => videoInput.click());
videoInput.addEventListener('change', uploadVideo);
stopBtn.addEventListener('click', stopProcessing);
saveEmailAlertBtn.addEventListener('click', saveEmailAlertConfig);
testEmailAlertBtn.addEventListener('click', sendTestEmailAlert);
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

    // Update AI risk level
    updateLSTMRisk(data.lstm_level, data.lstm_score);

    // Update alerts
    updateAlerts(data.alerts);

    // Update IoT data
    // updateIoTData(data.iot_data);
});

socket.on('stream_end', (data) => {
    console.log('Stream ended:', data.message);
    showNotification('Video ended', 'info');
});

socket.on('email_alert', (data) => {
    renderEmailAlertEvents([data]);
    showNotification(`Email alert: ${data.reason}`, data.sent ? 'success' : 'error');
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
    // Basic color fallback
    if (level === 'HIGH') riskLevel.style.color = '#ff4c4c';
    else if (level === 'MEDIUM') riskLevel.style.color = '#ffa500';
    else riskLevel.style.color = '#4caf50';
}

function updateLSTMRisk(level, score) {
    if (!lstmLevel) return;
    lstmLevel.textContent = level;
    if (level === 'UNSAFE' || level === 'HIGH') {
        lstmLevel.style.color = '#ff4c4c';
        if (lstmScore) lstmScore.style.color = '#ff4c4c';
    } else {
        lstmLevel.style.color = '#4caf50';
        if (lstmScore) lstmScore.style.color = '#888';
    }
    if (lstmScore) {
        lstmScore.textContent = `Probability: ${(score * 100).toFixed(1)}%`;
    }
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

async function loadEmailAlertConfig() {
    try {
        const response = await fetch('/api/email_alert_config');
        const result = await response.json();
        if (!response.ok) return;
        alertEmailInput.value = result.email || '';
        enableEmailAlerts.checked = !!result.enabled;
        updateEmailAlertStatus(result);
    } catch (error) {
        console.error('Error loading email alert config:', error);
    }
}

async function saveEmailAlertConfig() {
    const payload = {
        email: alertEmailInput.value.trim(),
        enabled: enableEmailAlerts.checked
    };

    try {
        const response = await fetch('/api/email_alert_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        if (response.ok) {
            const config = result.config || {};
            alertEmailInput.value = config.email || '';
            enableEmailAlerts.checked = !!config.enabled;
            updateEmailAlertStatus(config);
            showNotification('Email alert settings saved', 'success');
        } else {
            showNotification(result.error || 'Failed to save email alert settings', 'error');
        }
    } catch (error) {
        console.error('Error saving email alert config:', error);
        showNotification('Error saving email alert settings', 'error');
    }
}

async function sendTestEmailAlert() {
    try {
        const response = await fetch('/api/test_email_alert', {
            method: 'POST'
        });
        const result = await response.json();
        if (response.ok) {
            if (result.alert) {
                renderEmailAlertEvents([result.alert]);
            }
            showNotification('Test email alert sent', 'success');
        } else {
            showNotification(result.error || 'Failed to send test email alert', 'error');
        }
    } catch (error) {
        console.error('Error sending test email alert:', error);
        showNotification('Error sending test email alert', 'error');
    }
}

function updateEmailAlertStatus(config) {
    if (!config.email) {
        emailAlertStatus.textContent = 'No email configured';
        return;
    }
    emailAlertStatus.textContent = config.enabled
        ? `Alerts active for ${config.email}`
        : `Email saved (${config.email}), alerts disabled`;
}

async function loadEmailAlertEvents() {
    try {
        const response = await fetch('/api/email_alerts');
        const result = await response.json();
        if (!response.ok) return;
        renderEmailAlertEvents(result.alerts || [], true);
    } catch (error) {
        console.error('Error loading email alerts:', error);
    }
}

function renderEmailAlertEvents(alerts, replace = false) {
    if (!emailAlertEvents) return;
    const existing = emailAlertEvents.querySelectorAll('.alert-item.mobile');
    if (replace) {
        existing.forEach(el => el.remove());
    }

    const list = replace ? alerts.slice().reverse() : alerts;
    if (replace && list.length === 0) {
        emailAlertEvents.innerHTML = `
            <h3>Recent Email Alerts</h3>
            <div class="no-alerts">No email alerts sent yet</div>
        `;
        return;
    }

    if (emailAlertEvents.querySelector('.no-alerts')) {
        emailAlertEvents.querySelector('.no-alerts').remove();
    }

    list.forEach(alert => {
        const item = document.createElement('div');
        item.className = 'alert-item mobile';
        item.innerHTML = `
            <div class="alert-severity">${alert.sent ? 'sent' : 'failed'} - ${alert.reason}</div>
            <div class="alert-message">${alert.timestamp} -> ${alert.email}</div>
        `;
        emailAlertEvents.appendChild(item);
    });

    const maxVisible = 8;
    const all = emailAlertEvents.querySelectorAll('.alert-item.mobile');
    if (all.length > maxVisible) {
        for (let i = 0; i < all.length - maxVisible; i += 1) {
            all[i].remove();
        }
    }
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
loadEmailAlertConfig();
loadEmailAlertEvents();
console.log('Dashboard initialized');
