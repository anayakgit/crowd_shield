/**
 * CrowdShield Planner JS
 * Interactive Safety Layout & AI Audit
 */

const canvas = document.getElementById('auditCanvas');
const ctx = canvas.getContext('2d');
const labels = document.getElementById('labels');

let widthM  = 40;
let heightM = 20;
let scale   = 20; // pixels per meter
let objects = [];
let currentTool = 'select';
let selectedIdx = -1;
let isDragging  = false;
let isDrawingRect = false;
let rectStart = { x: 0, y: 0 };


// Initialize
function init() {
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    
    // Mouse events
    canvas.addEventListener('mousedown', onMouseDown);
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('mouseup',   onMouseUp);
    
    // Input listeners
    document.getElementById('vWidth').addEventListener('change', (e) => { widthM = parseFloat(e.target.value); resizeCanvas(); });
    document.getElementById('vHeight').addEventListener('change', (e) => { heightM = parseFloat(e.target.value); resizeCanvas(); });

    render();
}

function resizeCanvas() {
    const container = canvas.parentElement;
    if (!container) return;
    const maxW = container.clientWidth - 60;
    const maxH = container.clientHeight - 60;
    
    // Calculate scale to fit while preserving aspect ratio
    scale = Math.min(maxW / widthM, maxH / heightM);
    
    // Ensure minimum scale for tiny areas
    if (scale < 0.1) scale = 0.5;

    canvas.width  = widthM * scale;
    canvas.height = heightM * scale;
    render();
}


function setTool(tool) {
    currentTool = tool;
    document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tool' + tool.charAt(0).toUpperCase() + tool.slice(1)).classList.add('active');
}

function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw Grid (every 5m for large areas, 1m for small)
    const gridStep = widthM > 100 ? 10 : (widthM > 50 ? 5 : 1);
    ctx.strokeStyle = '#f0f0f0';
    ctx.lineWidth = 1;
    for(let x=0; x<=widthM; x+=gridStep) {
        ctx.beginPath(); ctx.moveTo(x*scale, 0); ctx.lineTo(x*scale, canvas.height); ctx.stroke();
    }
    for(let y=0; y<=heightM; y+=gridStep) {
        ctx.beginPath(); ctx.moveTo(0, y*scale); ctx.lineTo(canvas.width, y*scale); ctx.stroke();
    }

    // Draw Objects
    objects.forEach((obj, idx) => {
        const x = obj.x * scale;
        const y = obj.y * scale;
        const iconSize = 12;

        ctx.font = '10px Inter';
        ctx.textAlign = 'center';

        if (obj.type === 'exit' || obj.type === 'entry') {
            const isH = obj.orientation !== 'v';
            const barColor = obj.type === 'entry' ? '#28a745' : '#dc3545';
            // size stored in meters, drawn in pixels
            const barPx = (obj.size || 3) * scale;  // default 3m
            const thickness = Math.max(6, scale * 0.4);
            ctx.fillStyle = barColor;
            if (isH) {
                ctx.fillRect(x - barPx/2, y - thickness/2, barPx, thickness);
                // tick marks every ~1m
                ctx.strokeStyle = 'rgba(255,255,255,0.7)'; ctx.lineWidth = 1;
                const segW = scale;
                for (let s = segW; s < barPx; s += segW) {
                    ctx.beginPath(); ctx.moveTo(x - barPx/2 + s, y - thickness/2); ctx.lineTo(x - barPx/2 + s, y + thickness/2); ctx.stroke();
                }
            } else {
                ctx.fillRect(x - thickness/2, y - barPx/2, thickness, barPx);
                ctx.strokeStyle = 'rgba(255,255,255,0.7)'; ctx.lineWidth = 1;
                const segH = scale;
                for (let s = segH; s < barPx; s += segH) {
                    ctx.beginPath(); ctx.moveTo(x - thickness/2, y - barPx/2 + s); ctx.lineTo(x + thickness/2, y - barPx/2 + s); ctx.stroke();
                }
            }
            ctx.fillStyle = '#000';
            ctx.fillText(`${obj.name} (${(obj.size||3).toFixed(1)}m)`, x, y + (isH ? thickness : barPx)/2 + 13);
        } else if (obj.type === 'camera') {
            ctx.fillStyle = '#17a2b8';
            ctx.beginPath(); ctx.arc(x, y, iconSize, 0, Math.PI*2); ctx.fill();
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.stroke();
            ctx.fillStyle = '#000'; ctx.fillText(obj.name, x, y + iconSize + 12);
        } else if (obj.type === 'source') {
            ctx.fillStyle = 'rgba(241, 196, 15, 0.3)';
            ctx.beginPath(); ctx.arc(x, y, 30, 0, Math.PI*2); ctx.fill();
            ctx.strokeStyle = '#f1c40f'; ctx.lineWidth = 2; ctx.stroke();
            ctx.fillStyle = '#f1c40f'; ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI*2); ctx.fill();
            ctx.fillStyle = '#000'; ctx.fillText(obj.name, x, y + 42);
        } else if (obj.type === 'zone') {
            ctx.strokeStyle = '#9b59b6';
            ctx.setLineDash([5, 5]);
            ctx.lineWidth = 2;
            ctx.strokeRect(obj.x * scale, obj.y * scale, obj.w * scale, obj.h * scale);
            ctx.fillStyle = 'rgba(155, 89, 182, 0.1)';
            ctx.fillRect(obj.x * scale, obj.y * scale, obj.w * scale, obj.h * scale);
            ctx.setLineDash([]);
            ctx.fillStyle = '#9b59b6';
            ctx.textAlign = 'left';
            ctx.fillText(obj.name, obj.x * scale + 5, obj.y * scale + 15);
        }
        
        if (selectedIdx === idx && obj.type !== 'zone') {
            ctx.strokeStyle = '#007bff';
            ctx.lineWidth = 2;
            ctx.strokeRect(x - (iconSize + 6), y - (iconSize + 6), (iconSize + 6) * 2, (iconSize + 6) * 2);
        }
    });
}




function onMouseDown(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / scale;
    const my = (e.clientY - rect.top) / scale;
    const hitRadius = 15 / scale;

    if (currentTool === 'select') {
        selectedIdx = objects.findIndex(o => {
            if (o.type === 'zone') {
               return mx >= o.x && mx <= o.x+o.w && my >= o.y && my <= o.y+o.h;
            }
            return Math.hypot(o.x - mx, o.y - my) < hitRadius;
        });
        
        if (selectedIdx !== -1) {
            isDragging = true;
            showInspector(objects[selectedIdx]);
        } else {
            hideInspector();
        }
        render();
    } else if (currentTool === 'zone') {
        isDrawingRect = true;
        rectStart = { x: mx, y: my };
        const name = 'Zone ' + (objects.filter(o=>o.type==='zone').length + 1);
        objects.push({ type: 'zone', x: mx, y: my, w: 0.1, h: 0.1, name: name });
        selectedIdx = objects.length - 1;
    } else {
        const typeLabel = currentTool.charAt(0).toUpperCase() + currentTool.slice(1);
        const name = typeLabel + ' ' + (objects.filter(o=>o.type===currentTool).length + 1);
        objects.push({ type: currentTool, x: mx, y: my, name: name });
        selectedIdx = objects.length - 1;
        render();
    }
}

function showInspector(obj) {
    const inspector = document.getElementById('inspector');
    inspector.style.display = 'block';
    document.getElementById('objName').value = obj.name || '';
    const orientRow = document.getElementById('orientRow');
    const sizeRow   = document.getElementById('sizeRow');
    const isGate = obj.type === 'entry' || obj.type === 'exit';
    if (orientRow) orientRow.style.display = isGate ? 'block' : 'none';
    if (sizeRow)   sizeRow.style.display   = isGate ? 'block' : 'none';
    if (isGate) {
        document.getElementById('objOrient').value = obj.orientation || 'h';
        document.getElementById('objSize').value   = obj.size != null ? obj.size : 3;
    }
}

function hideInspector() {
    document.getElementById('inspector').style.display = 'none';
}

function updateSelectedName() {
    if (selectedIdx === -1) return;
    objects[selectedIdx].name = document.getElementById('objName').value;
    updateInventory();
    render();
}

function updateSelectedOrient() {
    if (selectedIdx === -1) return;
    objects[selectedIdx].orientation = document.getElementById('objOrient').value;
    render();
}

function updateSelectedSize() {
    if (selectedIdx === -1) return;
    const v = parseFloat(document.getElementById('objSize').value);
    if (!isNaN(v) && v > 0) objects[selectedIdx].size = v;
    render();
}

function deleteSelected() {
    if (selectedIdx === -1) return;
    objects.splice(selectedIdx, 1);
    selectedIdx = -1;
    hideInspector();
    updateInventory();
    render();
}

function isInZone(obj, z) {
    // Works for point objects; zone needs normalised coords
    const zx1 = Math.min(z.x, z.x + z.w), zx2 = Math.max(z.x, z.x + z.w);
    const zy1 = Math.min(z.y, z.y + z.h), zy2 = Math.max(z.y, z.y + z.h);
    return obj.x >= zx1 && obj.x <= zx2 && obj.y >= zy1 && obj.y <= zy2;
}

function updateInventory() {
    const list = document.getElementById('inventoryList');
    if (objects.length === 0) {
        list.innerHTML = '<div class="no-items">Empty layout</div>';
        return;
    }

    const zones   = objects.filter(o => o.type === 'zone');
    const cameras = objects.filter(o => o.type === 'camera');
    const entries = objects.filter(o => o.type === 'entry');
    const exits   = objects.filter(o => o.type === 'exit');
    const sources = objects.filter(o => o.type === 'source');

    let html = '';

    if (zones.length === 0 && objects.length > 0) {
        // No zones — flat list
        objects.forEach(o => {
            const icon = {exit:'🔴', entry:'🟢', camera:'🔵', source:'🟡', zone:'🟣'}[o.type] || '•';
            html += `<div>${icon} ${o.name}</div>`;
        });
        list.innerHTML = html;
        return;
    }

    // Zone sections
    zones.forEach(z => {
        const inCams   = cameras.filter(c => isInZone(c, z));
        const inEntry  = entries.filter(c => isInZone(c, z));
        const inExits  = exits.filter(c => isInZone(c, z));
        const allItems = [...inEntry.map(o=>`🟢 ${o.name}`), ...inExits.map(o=>`🔴 ${o.name}`), ...inCams.map(o=>`🔵 ${o.name}`)];
        html += `<div style="margin-bottom:10px;">
            <strong style="color:#9b59b6;">▤ ${z.name}</strong>
            <div style="padding-left:12px;margin-top:3px;">
                ${allItems.length ? allItems.map(t=>`<div>${t}</div>`).join('') : '<div style="color:#aaa;font-style:italic;">Nothing inside</div>'}
            </div>
        </div>`;
    });

    // Unassigned items (not in any zone)
    const unassignedItems = [...cameras, ...entries, ...exits, ...sources].filter(o =>
        !zones.some(z => isInZone(o, z))
    );
    if (unassignedItems.length) {
        html += `<div style="margin-top:8px;border-top:1px dotted #ddd;padding-top:8px;">
            <strong style="color:#888;">Unassigned</strong>
            <div style="padding-left:12px;margin-top:3px;">
                ${unassignedItems.map(o => {
                    const icon = {exit:'🔴', entry:'🟢', camera:'🔵', source:'🟡'}[o.type]||'•';
                    return `<div>${icon} ${o.name}</div>`;
                }).join('')}
            </div>
        </div>`;
    }

    list.innerHTML = html;
}





function onMouseMove(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / scale;
    const my = (e.clientY - rect.top) / scale;

    if (isDrawingRect) {
        const obj = objects[selectedIdx];
        obj.w = mx - rectStart.x;
        obj.h = my - rectStart.y;
        updateInventory();
        render();
    } else if (isDragging && selectedIdx !== -1) {
        const obj = objects[selectedIdx];
        if (obj.type === 'zone') {
            obj.x = mx - obj.w/2;
            obj.y = my - obj.h/2;
        } else {
            obj.x = mx;
            obj.y = my;
        }
        updateInventory();
        render();
    }
}



function onMouseUp() {
    // After finishing a zone draw, open its inspector
    if (isDrawingRect && selectedIdx !== -1) {
        showInspector(objects[selectedIdx]);
        updateInventory();
    }
    isDragging = false;
    isDrawingRect = false;
    render();
}


async function runAiAudit() {
    const auditBox = document.getElementById('auditBox');
    const auditText = document.getElementById('auditText');
    auditBox.style.display = 'block';
    auditText.innerHTML = '<i>AI Analyst is reviewing your layout...</i>';

    const payload = {
        dimensions: { width: widthM, height: heightM },
        exits: objects.filter(o => o.type === 'exit'),
        entries: objects.filter(o => o.type === 'entry'),
        cameras: objects.filter(o => o.type === 'camera'),
        zones: objects.filter(o => o.type === 'zone'),
        sources: objects.filter(o => o.type === 'source')
    };


    try {
        const res = await fetch('/api/planner/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        auditText.innerHTML = data.report.replace(/\n/g, '<br>');
    } catch (e) {
        auditText.innerHTML = 'Error communicating with AI Advisor.';
    }
}

function closeAudit() {
    document.getElementById('auditBox').style.display = 'none';
}

function startSimulation() {
    let people = [];
    const sources = objects.filter(o => o.type === 'source');
    
    function spawn(count) {
        for(let i=0; i<count; i++) {
            if (sources.length > 0) {
                const s = sources[Math.floor(Math.random() * sources.length)];
                const angle = Math.random() * Math.PI * 2;
                const radius = Math.random() * 40 / scale;
                people.push({ 
                    x: s.x + Math.cos(angle) * radius, 
                    y: s.y + Math.sin(angle) * radius,
                    vx: 0, vy: 0
                });
            } else {
                people.push({ x: Math.random() * widthM, y: Math.random() * heightM, vx: 0, vy: 0 });
            }
        }
    }

    // Start with a large group
    spawn(150);

    // Continue spawning more and more people every 600ms
    const spawnInt = setInterval(() => spawn(20), 600);

    const simInt = setInterval(() => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        render(); 
        
        const targets = objects.filter(o => o.type === 'exit' || o.type === 'entry');
        if (targets.length === 0) { clearInterval(simInt); clearInterval(spawnInt); return; }

        ctx.fillStyle = 'rgba(0,0,0,0.7)';
        people.forEach(p => {
            const target = targets.reduce((prev, curr) => 
                Math.hypot(curr.x - p.x, curr.y - p.y) < Math.hypot(prev.x - p.x, prev.y - p.y) ? curr : prev
            );
            
            const dx = target.x - p.x;
            const dy = target.y - p.y;
            const dist = Math.hypot(dx, dy);
            
            if (dist > 0.4) {
                // Directional move + jitter for "crowd swarm" effect
                const jitter = (Math.random() - 0.5) * 0.1;
                p.x += (dx/dist) * 0.15 + jitter;
                p.y += (dy/dist) * 0.15 + jitter;
            } else {
                // Delete people when they "exit" to keep performance stable
                p.escaped = true;
            }
            
            ctx.beginPath();
            ctx.arc(p.x * scale, p.y * scale, 3, 0, Math.PI*2);
            ctx.fill();
        });
        
        people = people.filter(p => !p.escaped);
    }, 40);

    setTimeout(() => {
        clearInterval(simInt);
        clearInterval(spawnInt);
        render(); // final clean
    }, 20000);
}


// Delete selected with Delete/Backspace key
window.addEventListener('keydown', (e) => {
    if ((e.key === 'Delete' || e.key === 'Backspace') && selectedIdx !== -1) {
        objects.splice(selectedIdx, 1);
        selectedIdx = -1;
        render();
    }
});

init();

