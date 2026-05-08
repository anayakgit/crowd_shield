// =============================================================
// CrowdShield — Area-Based Dashboard JS
// =============================================================

const socket = io('http://localhost:5000');

// ---- State ----
let areas = {};   // area_id → { name, cameras: {camera_id → {...}}, personnel: [...] }
let sessions = {};   // camera_id → live state
let currentLayout = 2;

// Active modal context
let activeCameraAreaId = null;
let activePersonnelAreaId = null;

// ---- DOM ----
const areaList = document.getElementById('areaList');
const areasGrid = document.getElementById('areasGrid');
const emptyState = document.getElementById('emptyState');
const connectionBadge = document.getElementById('connectionBadge');
const connectionText = document.getElementById('connectionText');
const headerTimeEl = document.getElementById('headerTime');
const statAreas = document.getElementById('statAreas');
const statFeeds = document.getElementById('statFeeds');
const statHigh = document.getElementById('statHigh');


// ---- Clock ----
function updateClock() {
    const now = new Date();
    if (headerTimeEl) {
        headerTimeEl.textContent = now.toLocaleTimeString('en-GB', { hour12: false });
    }
}
setInterval(updateClock, 1000);
updateClock();


// ---- Layout ----
function setLayout(cols) {
    currentLayout = cols;
    document.querySelectorAll('.layout-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(`layout${cols}`).classList.add('active');
    // Apply to all grids
    document.querySelectorAll('.camera-grid').forEach(g => {
        g.className = `camera-grid cols-${cols}`;
    });
}

// =============================================================
// Socket Events
// =============================================================

socket.on('connect', () => {
    connectionBadge.className = 'connection-badge connected';
    connectionText.textContent = 'Connected';
    showToast('Connected to server', 'success');
    loadAreas();
});

socket.on('disconnect', () => {
    connectionBadge.className = 'connection-badge offline';
    connectionText.textContent = 'Offline';
    showToast('Disconnected', 'error');
});

socket.on('frame_data', (data) => {
    const { camera_id, area_id } = data;
    if (!sessions[camera_id]) return;

    // Update live state
    sessions[camera_id].risk_level = data.risk_level;
    sessions[camera_id].crowd_count = data.crowd_count;
    sessions[camera_id].lstm_score = data.lstm_score;
    sessions[camera_id].lstm_level = data.lstm_level;
    sessions[camera_id].alerts = data.alerts || [];

    updateCameraCard(camera_id, data);
    updateAreaSidebarItem(area_id);
    updateGlobalStats();
});

socket.on('stream_end', (data) => {
    const id = data.camera_id;
    if (id && sessions[id]) {
        sessions[id].processing = false;
        showToast(`Stream ended: ${sessions[id].name}`, 'info');
        updateGlobalStats();
    }
});

// Rule 1/2 — single camera alert
socket.on('camera_alert', (data) => {
    const { area_id, camera_id, camera_name, camera_type, message, tone } = data;
    const icon = tone === 'warning' ? '⚠️' : '🚨';
    // Show inline banner inside the camera card alerts panel
    const ae = document.getElementById(`alerts-${camera_id}`);
    if (ae) {
        const row = document.createElement('div');
        row.className = 'cam-alert-item alert-flash';
        row.innerHTML = `<span class="cam-alert-badge high">${icon} ${camera_type.toUpperCase()}</span><span>${escHtml(message)}</span>`;
        ae.prepend(row);
        setTimeout(() => row.classList.remove('alert-flash'), 2000);
    }
    showToast(message, tone === 'warning' ? 'warning' : 'error');
});

// Rule 3 — area escalation
socket.on('area_alert', (data) => {
    const { area_id, high_count, message } = data;
    showAreaEscalationBanner(area_id, message, high_count);
    showToast(`🚨 AREA ESCALATION: ${high_count} cameras HIGH`, 'error');
});

socket.on('area_alert_clear', (data) => {
    clearAreaEscalationBanner(data.area_id);
});

// =============================================================
// Load Areas from DB on startup
// =============================================================

async function loadAreas() {
    try {
        const res = await fetch('/api/areas');
        const list = await res.json();
        list.forEach(a => {
            areas[a.id] = { ...a, cameras: {}, personnel: a.personnel || [] };
            renderAreaSection(a.id, a);
            renderAreaSidebarItem(a.id, a);


            // Register cameras that already exist in the DB
            (a.cameras || []).forEach(cam => {
                sessions[cam.session_id] = {
                    name: cam.name,
                    camera_type: cam.camera_type || 'other',
                    description: cam.description || '',
                    area_id: a.id,
                    risk_level: cam.risk_level || 'LOW',
                    crowd_count: cam.crowd_count || 0,
                    processing: cam.processing || false,
                    alerts: [],
                };
                areas[a.id].cameras[cam.session_id] = sessions[cam.session_id];
                addCameraCardToArea(a.id, cam.session_id, cam.name, cam.camera_type || 'other', cam.description || '');
            });
        });
        toggleEmptyState();
        updateGlobalStats();
    } catch (e) {
        console.error('Failed to load areas', e);
    }
}

// =============================================================
// Area CRUD
// =============================================================

function openAreaModal() { document.getElementById('areaModal').classList.add('open'); }
function closeAreaModal() { document.getElementById('areaModal').classList.remove('open'); }

async function createArea() {
    const name = document.getElementById('areaName').value.trim();
    const desc = document.getElementById('areaDesc').value.trim();
    const capacity = parseInt(document.getElementById('areaCapacity').value) || 0;
    if (!name) { showToast('Area name is required', 'error'); return; }

    try {
        const res = await fetch('/api/areas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description: desc, capacity_limit: capacity })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        const area = data.area;
        areas[area.id] = { ...area, cameras: {}, personnel: [] };
        renderAreaSection(area.id, area);
        renderAreaSidebarItem(area.id, area);
        toggleEmptyState();
        updateGlobalStats();
        closeAreaModal();
        showToast(`Area "${area.name}" created`, 'success');

        // Clear inputs
        ['areaName', 'areaDesc', 'areaCapacity'].forEach(id => document.getElementById(id).value = '');
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

async function deleteArea(areaId) {
    if (!confirm('Delete this area and all its cameras?')) return;
    try {
        const res = await fetch(`/api/areas/${areaId}`, { method: 'DELETE' });
        const d = await res.json();
        if (!res.ok) throw new Error(d.error);

        // Remove all camera cards in this area from sessions
        const area = areas[areaId];
        if (area) {
            Object.keys(area.cameras).forEach(cid => delete sessions[cid]);
        }
        delete areas[areaId];
        document.getElementById(`area-section-${areaId}`)?.remove();
        document.getElementById(`sidebar-area-${areaId}`)?.remove();
        toggleEmptyState();
        updateGlobalStats();
        showToast('Area deleted', 'info');
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// =============================================================
// Area Sections (main content)
// =============================================================

function renderAreaSection(areaId, area) {
    // Remove empty state if present separately
    const section = document.createElement('div');
    section.className = 'area-section';
    section.id = `area-section-${areaId}`;
    section.innerHTML = `
        <div class="area-header">
            <div class="area-header-left">
                <span class="area-icon">#</span>
                <div>
                    <h2 class="area-title">${escHtml(area.name)}</h2>

                    <span class="area-meta">
                        ${area.description ? escHtml(area.description) + ' · ' : ''}
                        ${area.capacity_limit ? 'Capacity: ' + area.capacity_limit : 'No capacity set'}
                    </span>
                </div>
            </div>
            <div class="area-header-right">
                <button class="btn-sm" onclick="openPersonnelModal(${areaId}, '${escHtml(area.name)}')">+ Personnel</button>
                <button class="btn-sm primary" onclick="openCameraModal(${areaId}, '${escHtml(area.name)}')">+ Camera</button>
                <button class="btn-sm danger" onclick="deleteArea(${areaId})">Delete Area</button>
            </div>
        </div>
        <div class="area-tabs">
            <button class="tab-btn active" onclick="switchTab(${areaId}, 'cameras')">Cameras</button>
            <button class="tab-btn" onclick="switchTab(${areaId}, 'personnel')">Personnel</button>
        </div>
        <div class="tab-panel" id="tab-cameras-${areaId}">
            <div class="camera-grid cols-${currentLayout}" id="camera-grid-${areaId}">
                <div class="no-cameras-msg" id="no-cams-${areaId}">No cameras added yet. Click "+ Camera" to add one.</div>
            </div>
        </div>

        <div class="tab-panel hidden" id="tab-personnel-${areaId}">
            <div class="personnel-list" id="personnel-list-${areaId}">
                ${renderPersonnelList(area.personnel || [], areaId)}
            </div>
        </div>
    `;
    mainContent.appendChild(section);
}

function switchTab(areaId, tab) {
    const section = document.getElementById(`area-section-${areaId}`);
    section.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    section.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    document.getElementById(`tab-${tab}-${areaId}`).classList.remove('hidden');
    section.querySelector(`[onclick="switchTab(${areaId}, '${tab}')"]`).classList.add('active');
}

// =============================================================
// Camera Modal & Upload
// =============================================================

function openCameraModal(areaId, areaName) {
    activeCameraAreaId = areaId;
    document.getElementById('modalAreaName').textContent = areaName;
    document.getElementById('camName').value = '';
    document.getElementById('camDescription').value = '';
    document.getElementById('camType').value = 'other';
    document.getElementById('camDropText').textContent = 'Click or drag video here';
    document.getElementById('camSubmitBtn').disabled = true;
    document.getElementById('camUploadProgress').style.display = 'none';
    document.getElementById('camFileInput').value = '';
    document.getElementById('cameraModal').classList.add('open');
}
function closeCameraModal() { document.getElementById('cameraModal').classList.remove('open'); }

document.getElementById('camFileInput').addEventListener('change', () => {
    const file = document.getElementById('camFileInput').files[0];
    if (file) {
        document.getElementById('camDropText').textContent = `✅ ${file.name}`;
        if (!document.getElementById('camName').value)
            document.getElementById('camName').value = file.name.replace(/\.[^/.]+$/, '');
        document.getElementById('camSubmitBtn').disabled = false;
    }
});

// Drag & drop on camera modal
const camDrop = document.getElementById('camDropZone');
camDrop.addEventListener('dragover', e => { e.preventDefault(); camDrop.classList.add('dragover'); });
camDrop.addEventListener('dragleave', () => camDrop.classList.remove('dragover'));
camDrop.addEventListener('drop', e => {
    e.preventDefault(); camDrop.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('video/')) {
        const dt = new DataTransfer(); dt.items.add(file);
        document.getElementById('camFileInput').files = dt.files;
        document.getElementById('camDropText').textContent = `✅ ${file.name}`;
        if (!document.getElementById('camName').value)
            document.getElementById('camName').value = file.name.replace(/\.[^/.]+$/, '');
        document.getElementById('camSubmitBtn').disabled = false;
    }
});

async function uploadCamera() {
    const file = document.getElementById('camFileInput').files[0];
    const camName = document.getElementById('camName').value.trim() || file?.name;
    const camType = document.getElementById('camType').value;
    const camDesc = document.getElementById('camDescription').value.trim();
    const areaId = activeCameraAreaId;
    if (!file || !areaId) return;

    document.getElementById('camSubmitBtn').disabled = true;
    document.getElementById('camUploadProgress').style.display = 'block';

    try {
        let prog = 0;
        const fp = setInterval(() => {
            prog = Math.min(prog + Math.random() * 15, 88);
            document.getElementById('camProgressFill').style.width = prog + '%';
        }, 200);

        const form = new FormData();
        form.append('video', file);
        form.append('camera_name', camName);
        form.append('area_id', areaId);
        form.append('camera_type', camType);
        form.append('description', camDesc);

        const res = await fetch('/api/upload_video', { method: 'POST', body: form });
        clearInterval(fp);
        document.getElementById('camProgressFill').style.width = '100%';

        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        const { camera_id, area_name, camera_type, description } = data;

        // Register session
        sessions[camera_id] = {
            name: camName, camera_type: camera_type || camType,
            description: description || camDesc,
            area_id: areaId,
            risk_level: 'LOW', crowd_count: 0,
            processing: true, alerts: []
        };
        areas[areaId].cameras[camera_id] = sessions[camera_id];

        closeCameraModal();
        addCameraCardToArea(areaId, camera_id, camName, camera_type || camType, description || camDesc);
        updateAreaSidebarItem(areaId);
        updateGlobalStats();
        showToast(`Camera "${camName}" added to ${area_name}`, 'success');

        // Start stream
        socket.emit('start_stream', { camera_id });
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
        document.getElementById('camSubmitBtn').disabled = false;
    }
}

// =============================================================
// Camera Cards
// =============================================================

const CAM_TYPE_LABELS = {
    entry: 'Entry',
    exit: 'Exit',
    center: 'Center',
    perimeter: 'Perimeter',
    other: 'Other',
};


function addCameraCardToArea(areaId, cameraId, cameraName, cameraType = 'other', description = '') {
    const grid = document.getElementById(`camera-grid-${areaId}`);
    document.getElementById(`no-cams-${areaId}`)?.remove();

    const typeLabel = CAM_TYPE_LABELS[cameraType] || '📷 Other';
    const descHtml = description ? `<span class="cam-card-desc">${escHtml(description)}</span>` : '';

    const card = document.createElement('div');
    card.className = 'camera-card risk-LOW';
    card.id = `card-${cameraId}`;
    card.innerHTML = `
        <div class="cam-card-header">
            <div class="cam-card-dot LOW" id="dot-${cameraId}"></div>
            <span class="cam-card-name">${escHtml(cameraName)}</span>
            <span class="cam-type-pill">${typeLabel}</span>
            <span class="cam-card-id">${cameraId}</span>
            <button class="cam-card-remove" onclick="removeCamera('${cameraId}', ${areaId})">✕</button>
        </div>
        ${descHtml ? `<div class="cam-card-desc-bar">${descHtml}</div>` : ''}
        <div class="cam-video-wrap">
            <img id="feed-${cameraId}" src="" alt="Live Feed" style="display:none;">
            <div class="cam-placeholder" id="placeholder-${cameraId}">
                <div class="cam-placeholder-icon">...</div>
                <span>Awaiting stream...</span>
            </div>
            <div class="cam-risk-badge LOW" id="badge-${cameraId}">LOW</div>
        </div>

        <div class="cam-stats">
            <div class="cam-stat">
                <div class="cam-stat-label">People</div>
                <div class="cam-stat-value" id="count-${cameraId}">—</div>
            </div>
            <div class="cam-stat">
                <div class="cam-stat-label">LSTM Score</div>
                <div class="cam-stat-value" id="lstm-${cameraId}">—</div>
            </div>
            <div class="cam-stat">
                <div class="cam-stat-label">LSTM Status</div>
                <div class="cam-stat-value" id="lstmStatus-${cameraId}">—</div>
            </div>
        </div>
        <div class="cam-alerts" id="alerts-${cameraId}">
            <span class="cam-no-alerts">No active alerts</span>
        </div>
    `;
    grid.appendChild(card);
}

function updateCameraCard(cameraId, data) {
    const risk = data.risk_level || 'LOW';
    const card = document.getElementById(`card-${cameraId}`);
    if (!card) return;

    card.className = `camera-card risk-${risk}`;
    const dot = document.getElementById(`dot-${cameraId}`);
    if (dot) dot.className = `cam-card-dot ${risk}`;

    const badge = document.getElementById(`badge-${cameraId}`);
    if (badge) { badge.className = `cam-risk-badge ${risk}`; badge.textContent = risk; }

    const img = document.getElementById(`feed-${cameraId}`);
    const ph = document.getElementById(`placeholder-${cameraId}`);
    if (img && data.frame) { img.src = 'data:image/jpeg;base64,' + data.frame; img.style.display = 'block'; if (ph) ph.style.display = 'none'; }

    const ce = document.getElementById(`count-${cameraId}`);
    if (ce) { ce.textContent = data.crowd_count; ce.className = `cam-stat-value v-${risk.toLowerCase()}`; }

    const le = document.getElementById(`lstm-${cameraId}`);
    if (le) le.textContent = `${(data.lstm_score * 100).toFixed(1)}%`;

    const ls = document.getElementById(`lstmStatus-${cameraId}`);
    if (ls) { ls.textContent = data.lstm_level || '—'; ls.className = `cam-stat-value ${data.lstm_level === 'UNSAFE' ? 'v-high' : 'v-low'}`; }

    const ae = document.getElementById(`alerts-${cameraId}`);
    if (ae) {
        if (!data.alerts?.length) {
            ae.innerHTML = '<span class="cam-no-alerts">No active alerts</span>';
        } else {
            ae.innerHTML = data.alerts.map(a => `
                <div class="cam-alert-item">
                    <span class="cam-alert-badge ${a.severity?.toLowerCase()}">${a.severity}</span>
                    <span>${escHtml(a.message)}</span>
                </div>`).join('');
        }
    }
}

async function removeCamera(cameraId, areaId) {
    try {
        await fetch('/api/remove_camera', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ camera_id: cameraId })
        });
        document.getElementById(`card-${cameraId}`)?.remove();
        delete sessions[cameraId];
        if (areas[areaId]) delete areas[areaId].cameras[cameraId];
        updateAreaSidebarItem(areaId);
        updateGlobalStats();
        showToast('Camera removed', 'info');

        // If no cameras left, show placeholder
        const grid = document.getElementById(`camera-grid-${areaId}`);
        if (grid && !grid.querySelector('.camera-card')) {
            const msg = document.createElement('div');
            msg.className = 'no-cameras-msg'; msg.id = `no-cams-${areaId}`;
            msg.textContent = 'No cameras added yet. Click "+ Camera" to add one.';
            grid.appendChild(msg);
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// =============================================================
// Personnel Modal & CRUD
// =============================================================

function openPersonnelModal(areaId, areaName) {
    activePersonnelAreaId = areaId;
    document.getElementById('pModalAreaName').textContent = areaName;
    ['pName', 'pRole', 'pEmail', 'pPhone'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('personnelModal').classList.add('open');
}
function closePersonnelModal() { document.getElementById('personnelModal').classList.remove('open'); }

async function addPersonnel() {
    const name = document.getElementById('pName').value.trim();
    const role = document.getElementById('pRole').value.trim() || 'Security Officer';
    const email = document.getElementById('pEmail').value.trim();
    const phone = document.getElementById('pPhone').value.trim();
    const areaId = activePersonnelAreaId;

    if (!name) { showToast('Name is required', 'error'); return; }

    try {
        // Create personnel record
        const res1 = await fetch('/api/personnel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, role, email, phone })
        });
        const d1 = await res1.json();
        if (!res1.ok) throw new Error(d1.error);

        // Assign to area
        const res2 = await fetch(`/api/areas/${areaId}/personnel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ personnel_id: d1.person.id })
        });
        if (!res2.ok) throw new Error('Assignment failed');

        // Update local state
        areas[areaId]?.personnel.push(d1.person);
        refreshPersonnelPanel(areaId);
        updateAreaSidebarItem(areaId);
        closePersonnelModal();
        showToast(`${name} added`, 'success');
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

async function removePersonnel(personId, areaId) {
    try {
        await fetch(`/api/areas/${areaId}/personnel/${personId}`, { method: 'DELETE' });
        if (areas[areaId]) {
            areas[areaId].personnel = areas[areaId].personnel.filter(p => p.id !== personId);
        }
        refreshPersonnelPanel(areaId);
        updateAreaSidebarItem(areaId);
        showToast('Personnel removed', 'info');
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

function renderPersonnelList(personnel, areaId) {
    if (!personnel.length) return '<div class="no-items">No personnel assigned. Click &ldquo;+ Personnel&rdquo; to add.</div>';
    return personnel.map(p => `
        <div class="personnel-card">
            <div class="personnel-avatar">${p.name.charAt(0).toUpperCase()}</div>
            <div class="personnel-info">
                <div class="personnel-name">${escHtml(p.name)}</div>
                <div class="personnel-role">${escHtml(p.role)}</div>
                ${p.email ? `<div class="personnel-contact">✉ ${escHtml(p.email)}</div>` : ''}
                ${p.phone ? `<div class="personnel-contact">📞 ${escHtml(p.phone)}</div>` : ''}
            </div>
            <button class="btn-sm danger" onclick="removePersonnel(${p.id}, ${areaId})">Remove</button>
        </div>
    `).join('');
}

function refreshPersonnelPanel(areaId) {
    const panel = document.getElementById(`personnel-list-${areaId}`);
    if (panel) panel.innerHTML = renderPersonnelList(areas[areaId]?.personnel || [], areaId);
}

// =============================================================
// Sidebar
// =============================================================

function renderAreaSidebarItem(areaId, area) {
    areaList.querySelector('.no-items')?.remove();
    const item = document.createElement('div');
    item.className = 'sidebar-area-item';
    item.id = `sidebar-area-${areaId}`;
    item.innerHTML = `
        <div class="sidebar-area-name" onclick="scrollToArea(${areaId})"># ${escHtml(area.name)}</div>
        <div class="sidebar-area-meta" id="sidebar-meta-${areaId}">0 cameras · 0 personnel</div>
    `;
    areaList.appendChild(item);
}


function updateAreaSidebarItem(areaId) {
    const meta = document.getElementById(`sidebar-meta-${areaId}`);
    const area = areas[areaId];
    if (!meta || !area) return;
    const camCount = Object.keys(area.cameras || {}).length;
    const perCount = (area.personnel || []).length;
    const highCount = Object.values(area.cameras || {}).filter(c => c.risk_level === 'HIGH').length;
    meta.textContent = `${camCount} cameras · ${perCount} personnel${highCount ? ` · ! ${highCount} HIGH` : ''}`;
}


function scrollToArea(areaId) {
    document.getElementById(`area-section-${areaId}`)?.scrollIntoView({ behavior: 'smooth' });
}

// =============================================================
// Global Stats
// =============================================================

function updateGlobalStats() {
    const allSessions = Object.values(sessions);
    statAreas.textContent = Object.keys(areas).length;
    statFeeds.textContent = allSessions.filter(s => s.processing).length;
    statHigh.textContent = allSessions.filter(s => s.risk_level === 'HIGH').length;
}

// =============================================================
// Empty State
// =============================================================

function toggleEmptyState() {
    const hasAreas = Object.keys(areas).length > 0;
    emptyState.style.display = hasAreas ? 'none' : 'flex';
}

// =============================================================
// Toast
// =============================================================

const TOAST_ICONS = { success: '[S]', error: '[E]', info: '[I]', warning: '[W]' };
function showToast(message, type = 'info') {

    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<span class="toast-icon">${TOAST_ICONS[type] || ''}</span><span>${escHtml(message)}</span>`;
    c.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 3500);
}

// =============================================================
// Utility
// =============================================================

function escHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Close modals on background click
['areaModal', 'cameraModal', 'personnelModal'].forEach(id => {
    document.getElementById(id).addEventListener('click', function (e) {
        if (e.target === this) this.classList.remove('open');
    });
});

// =============================================================
// Area Escalation Banner
// =============================================================

function showAreaEscalationBanner(areaId, message, highCount) {
    const section = document.getElementById(`area-section-${areaId}`);
    if (!section) return;
    // Remove existing banner
    section.querySelector('.area-escalation-banner')?.remove();
    section.classList.add('area-escalated');

    const banner = document.createElement('div');
    banner.className = 'area-escalation-banner';
    banner.innerHTML = `
        <span class="escalation-icon">!</span>
        <span class="escalation-msg">${escHtml(message)}</span>
        <span class="escalation-count">${highCount} cameras HIGH</span>
    `;

    // Insert right after area-header
    const header = section.querySelector('.area-header');
    header.insertAdjacentElement('afterend', banner);
}

function clearAreaEscalationBanner(areaId) {
    const section = document.getElementById(`area-section-${areaId}`);
    if (!section) return;
    section.querySelector('.area-escalation-banner')?.remove();
    section.classList.remove('area-escalated');
}

// ---- Init ----
console.log('CrowdShield dashboard initialised');
