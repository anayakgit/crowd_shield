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

        if (obj.type === 'exit') {
            ctx.fillStyle = '#dc3545';
            ctx.fillRect(x - iconSize, y - iconSize, iconSize*2, iconSize*2);
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.strokeRect(x - iconSize, y - iconSize, iconSize*2, iconSize*2);
        } else if (obj.type === 'entry') {
            ctx.fillStyle = '#28a745';
            ctx.fillRect(x - iconSize, y - iconSize, iconSize*2, iconSize*2);
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.strokeRect(x - iconSize, y - iconSize, iconSize*2, iconSize*2);
        } else if (obj.type === 'camera') {
            ctx.fillStyle = '#17a2b8';
            ctx.beginPath(); ctx.arc(x, y, iconSize, 0, Math.PI*2); ctx.fill();
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.stroke();
        } else if (obj.type === 'source') {
            ctx.fillStyle = 'rgba(241, 196, 15, 0.3)';
            ctx.beginPath(); ctx.arc(x, y, 30, 0, Math.PI*2); ctx.fill();
            ctx.strokeStyle = '#f1c40f'; ctx.lineWidth = 2; ctx.stroke();
            ctx.fillStyle = '#f1c40f'; ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI*2); ctx.fill();
        } else if (obj.type === 'zone') {
            ctx.strokeStyle = '#9b59b6';
            ctx.setLineDash([5, 5]);
            ctx.lineWidth = 2;
            ctx.strokeRect(obj.x * scale, obj.y * scale, obj.w * scale, obj.h * scale);
            ctx.fillStyle = 'rgba(155, 89, 182, 0.1)';
            ctx.fillRect(obj.x * scale, obj.y * scale, obj.w * scale, obj.h * scale);
            ctx.setLineDash([]);
        }
        
        if (selectedIdx === idx) {
            ctx.strokeStyle = '#007bff';
            ctx.lineWidth = 2;
            const size = obj.type === 'zone' ? 0 : 5;
            if (obj.type !== 'zone') {
                ctx.strokeRect(x - (iconSize+size), y - (iconSize+size), (iconSize+size)*2, (iconSize+size)*2);
            }
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
        if (selectedIdx !== -1) isDragging = true;
        render();
    } else if (currentTool === 'zone') {
        isDrawingRect = true;
        rectStart = { x: mx, y: my };
        objects.push({ type: 'zone', x: mx, y: my, w: 0.1, h: 0.1 });
        selectedIdx = objects.length - 1;
    } else {
        objects.push({ type: currentTool, x: mx, y: my });
        selectedIdx = objects.length - 1;
        render();
    }
}




function onMouseMove(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / scale;
    const my = (e.clientY - rect.top) / scale;

    if (isDrawingRect) {
        const obj = objects[selectedIdx];
        obj.w = mx - rectStart.x;
        obj.h = my - rectStart.y;
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
        render();
    }
}


function onMouseUp() {
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

function startSimulation() {
    const people = [];
    const sources = objects.filter(o => o.type === 'source');
    
    // Spawn from sources if they exist, otherwise random
    for(let i=0; i<50; i++) {
        if (sources.length > 0) {
            const s = sources[Math.floor(Math.random() * sources.length)];
            const angle = Math.random() * Math.PI * 2;
            const radius = Math.random() * 30 / scale;
            people.push({ 
                x: s.x + Math.cos(angle) * radius, 
                y: s.y + Math.sin(angle) * radius,
                vx: 0, vy: 0
            });
        } else {
            people.push({ x: Math.random() * widthM, y: Math.random() * heightM, vx: 0, vy: 0 });
        }
    }

    const simInt = setInterval(() => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        render(); 
        
        const targets = objects.filter(o => o.type === 'exit' || o.type === 'entry');
        if (targets.length === 0) { clearInterval(simInt); return; }

        ctx.fillStyle = 'rgba(0,0,0,0.6)';
        people.forEach(p => {
            const target = targets.reduce((prev, curr) => 
                Math.hypot(curr.x - p.x, curr.y - p.y) < Math.hypot(prev.x - p.x, prev.y - p.y) ? curr : prev
            );

            
            const dx = target.x - p.x;
            const dy = target.y - p.y;
            const dist = Math.hypot(dx, dy);
            
            if (dist > 0.5) {
                p.x += (dx/dist) * 0.2;
                p.y += (dy/dist) * 0.2;
            }
            
            ctx.beginPath();
            ctx.arc(p.x * scale, p.y * scale, 3, 0, Math.PI*2);
            ctx.fill();
        });
    }, 50);

    setTimeout(() => clearInterval(simInt), 5000);
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

