from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import os
import base64
import uuid
import time
import traceback
from datetime import datetime

from backend.config import Config
from backend.models.yolo_detector import YOLODetector
from backend.models.movement_tracker import MovementTracker
from backend.models.risk_analyzer import RiskAnalyzer
from backend.utils.video_processor import VideoProcessor
from backend.utils.digital_twin import DigitalTwin
from backend.utils.notifier import Notifier
from backend.database.models import init_db, SessionLocal, Area, Personnel, Camera

# --------------------------------------------------------------------------
# Flask + SocketIO
# --------------------------------------------------------------------------
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# --------------------------------------------------------------------------
# Init DB on startup
# --------------------------------------------------------------------------
init_db()

# --------------------------------------------------------------------------
# Shared Resources
# --------------------------------------------------------------------------
yolo_detector = None
notifier = Notifier()

def initialize_yolo():
    global yolo_detector
    if yolo_detector is None:
        print("Initializing YOLO model...")
        yolo_detector = YOLODetector()
        print("YOLO model loaded")

# --------------------------------------------------------------------------
# In-memory Camera Session Store
# (Persisted metadata lives in SQLite; runtime state lives here)
# --------------------------------------------------------------------------
sessions = {}

def create_session(camera_id, camera_name, area_id, camera_type='other', description=''):
    sessions[camera_id] = {
        'camera_name':  camera_name,
        'camera_type':  camera_type,
        'description':  description,
        'area_id':      area_id,
        'state': {
            'processing':        False,
            'source_type':       None,
            'risk_level':        'LOW',
            'crowd_count':       0,
            'alerts':            [],
            'stream_session_id': 0,
        },
        'components': {
            'movement_tracker': MovementTracker(),
            'risk_analyzer':    RiskAnalyzer(),
            'video_processor':  VideoProcessor(),
            'digital_twin':     DigitalTwin(),
        }
    }
    return sessions[camera_id]

def stop_session(camera_id):
    if camera_id not in sessions:
        return
    s = sessions[camera_id]
    s['state']['processing'] = False
    s['state']['stream_session_id'] += 1
    time.sleep(0.1)
    s['components']['video_processor'].release()
    s['state']['source_type'] = None

def delete_session(camera_id):
    stop_session(camera_id)
    sessions.pop(camera_id, None)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Alert Router — runs after each risk evaluation
# --------------------------------------------------------------------------

# Track area alert state to avoid spamming
area_alert_state = {}  # area_id → {'alerted': False, 'high_count': 0}

def run_alert_router(camera_id, risk_level, camera_type, area_id):
    """3-rule alert router called after each frame evaluation."""
    # Count how many cameras in this area are currently HIGH
    area_cameras = {cid: s for cid, s in sessions.items() if s['area_id'] == area_id}
    high_cameras = [cid for cid, s in area_cameras.items() if s['state']['risk_level'] == 'HIGH']
    high_count   = len(high_cameras)

    prev = area_alert_state.get(area_id, {'alerted': False, 'high_count': 0})

    # -- Rule 1: Single camera HIGH (any type) → notify area personnel (in-app)
    if risk_level == 'HIGH':
        if camera_type == 'exit':
            # Rule 2: Exit camera HIGH → softer message
            msg  = f"High traffic detected at EXIT camera '{sessions[camera_id]['camera_name']}'. Monitor outflow pressure."
            tone = 'warning'
        else:
            msg  = f"Camera '{sessions[camera_id]['camera_name']}' ({camera_type}) is HIGH risk. Immediate attention required."
            tone = 'high'

        socketio.emit('camera_alert', {
            'area_id':     area_id,
            'camera_id':   camera_id,
            'camera_name': sessions[camera_id]['camera_name'],
            'camera_type': camera_type,
            'message':     msg,
            'tone':        tone,
        })

    # -- Rule 3: 2+ cameras HIGH in area → full area escalation
    if high_count >= 2 and not prev.get('alerted'):
        area_alert_state[area_id] = {'alerted': True, 'high_count': high_count}
        socketio.emit('area_alert', {
            'area_id':    area_id,
            'high_count': high_count,
            'cameras':    high_cameras,
            'message':    f'AREA ESCALATION: {high_count} cameras are HIGH risk simultaneously.',
        })
        print(f"[ALERT] Area {area_id}: {high_count} cameras HIGH — escalation triggered")
    elif high_count < 2 and prev.get('alerted'):
        # Reset when back to safe
        area_alert_state[area_id] = {'alerted': False, 'high_count': 0}
        socketio.emit('area_alert_clear', {'area_id': area_id})


# --------------------------------------------------------------------------
# DB helper
# --------------------------------------------------------------------------
def db_session():
    return SessionLocal()

# ============================================================
# ROUTES — Static
# ============================================================

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# ============================================================
# ROUTES — Areas
# ============================================================

@app.route('/api/areas', methods=['GET'])
def list_areas():
    db = db_session()
    try:
        areas = db.query(Area).all()
        result = []
        for a in areas:
            d = a.to_dict()
            # Attach live risk for each camera in that area
            cam_statuses = []
            for cam in a.cameras:
                live = sessions.get(cam.session_id)
                cam_statuses.append({
                    **cam.to_dict(),
                    'risk_level':  live['state']['risk_level']  if live else 'OFFLINE',
                    'crowd_count': live['state']['crowd_count'] if live else 0,
                    'processing':  live['state']['processing']  if live else False,
                })
            d['cameras']   = cam_statuses
            d['personnel'] = [p.to_dict() for p in a.personnel]
            result.append(d)
        return jsonify(result)
    finally:
        db.close()


@app.route('/api/areas', methods=['POST'])
def create_area():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Area name is required'}), 400

    db = db_session()
    try:
        area = Area(
            name           = name,
            description    = data.get('description', ''),
            capacity_limit = int(data.get('capacity_limit', 0)),
        )
        db.add(area)
        db.commit()
        db.refresh(area)
        return jsonify({'message': 'Area created', 'area': area.to_dict()}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/areas/<int:area_id>', methods=['PUT'])
def update_area(area_id):
    data = request.get_json(silent=True) or {}
    db = db_session()
    try:
        area = db.get(Area, area_id)
        if not area:

            return jsonify({'error': 'Area not found'}), 404
        if 'name'           in data: area.name           = data['name']
        if 'description'    in data: area.description    = data['description']
        if 'capacity_limit' in data: area.capacity_limit = int(data['capacity_limit'])
        db.commit()
        return jsonify({'message': 'Area updated', 'area': area.to_dict()})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/areas/<int:area_id>', methods=['DELETE'])
def delete_area(area_id):
    db = db_session()
    try:
        area = db.get(Area, area_id)
        if not area:

            return jsonify({'error': 'Area not found'}), 404
        # Stop all running sessions for cameras in this area
        for cam in area.cameras:
            delete_session(cam.session_id)
        db.delete(area)
        db.commit()
        return jsonify({'message': f'Area {area_id} deleted'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ============================================================
# ROUTES — Personnel
# ============================================================

@app.route('/api/personnel', methods=['GET'])
def list_personnel():
    db = db_session()
    try:
        people = db.query(Personnel).all()
        return jsonify([p.to_dict() for p in people])
    finally:
        db.close()


@app.route('/api/personnel', methods=['POST'])
def create_personnel():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Personnel name is required'}), 400
    db = db_session()
    try:
        person = Personnel(
            name  = name,
            email = data.get('email', ''),
            phone = data.get('phone', ''),
            role  = data.get('role', 'Security Officer'),
        )
        db.add(person)
        db.commit()
        db.refresh(person)
        return jsonify({'message': 'Personnel created', 'person': person.to_dict()}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/personnel/<int:person_id>', methods=['DELETE'])
def delete_personnel(person_id):
    db = db_session()
    try:
        person = db.get(Personnel, person_id)
        if not person:

            return jsonify({'error': 'Personnel not found'}), 404
        db.delete(person)
        db.commit()
        return jsonify({'message': f'Personnel {person_id} deleted'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/areas/<int:area_id>/personnel', methods=['POST'])
def assign_personnel(area_id):
    """Assign an existing personnel member to an area."""
    data = request.get_json(silent=True) or {}
    person_id = data.get('personnel_id')
    db = db_session()
    try:
        area   = db.get(Area, area_id)
        person = db.get(Personnel, person_id)
        if not area:

            return jsonify({'error': 'Area not found'}), 404
        if not person:
            return jsonify({'error': 'Personnel not found'}), 404
        if person not in area.personnel:
            area.personnel.append(person)
            db.commit()
        return jsonify({'message': f'{person.name} assigned to {area.name}'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/areas/<int:area_id>/personnel/<int:person_id>', methods=['DELETE'])
def unassign_personnel(area_id, person_id):
    """Remove a personnel member from an area."""
    db = db_session()
    try:
        area   = db.get(Area, area_id)
        person = db.get(Personnel, person_id)
        if not area or not person:

            return jsonify({'error': 'Not found'}), 404
        if person in area.personnel:
            area.personnel.remove(person)
            db.commit()
        return jsonify({'message': f'{person.name} removed from {area.name}'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ============================================================
# ROUTES — Cameras (now area-aware)
# ============================================================

@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    """Upload a video and link it to an area."""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    area_id     = request.form.get('area_id', type=int)
    camera_name = request.form.get('camera_name', file.filename).strip()
    camera_type = request.form.get('camera_type', 'other')
    description = request.form.get('description', '')

    if not area_id:
        return jsonify({'error': 'area_id is required'}), 400

    db = db_session()
    try:
        area = db.get(Area, area_id)
        if not area:

            return jsonify({'error': 'Area not found'}), 404

        # Generate unique session ID
        camera_id = f"cam_{str(uuid.uuid4())[:8]}"

        # Save file
        timestamp     = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{camera_id}_{timestamp}_{file.filename}"
        filepath      = os.path.join(Config.UPLOAD_FOLDER, safe_filename)
        file.save(filepath)

        # Persist to DB
        cam_record = Camera(
            area_id     = area_id,
            session_id  = camera_id,
            name        = camera_name,
            camera_type = camera_type,
            description = description,
            filepath    = filepath,
        )
        db.add(cam_record)
        db.commit()

        # Create in-memory session
        session    = create_session(camera_id, camera_name, area_id, camera_type, description)
        video_info = session['components']['video_processor'].open_video_file(filepath)
        session['state']['source_type'] = 'video'
        session['state']['processing']  = True

        print(f"Video uploaded → [{area.name}] {camera_id} ({camera_name}, type={camera_type})")
        return jsonify({
            'message':     'Video uploaded successfully',
            'camera_id':   camera_id,
            'camera_name': camera_name,
            'camera_type': camera_type,
            'description': description,
            'area_id':     area_id,
            'area_name':   area.name,
            'video_info':  video_info,
        })
    except Exception as e:
        db.rollback()
        delete_session(camera_id) if 'camera_id' in locals() else None
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/remove_camera', methods=['POST'])
def remove_camera():
    data      = request.get_json(silent=True) or {}
    camera_id = data.get('camera_id')
    if not camera_id:
        return jsonify({'error': 'camera_id required'}), 400

    delete_session(camera_id)

    db = db_session()
    try:
        cam = db.query(Camera).filter_by(session_id=camera_id).first()
        if cam:
            db.delete(cam)
            db.commit()
        return jsonify({'message': f'Camera {camera_id} removed'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/get_status', methods=['GET'])
def get_status():
    result = {}
    for cam_id, session in sessions.items():
        st = session['state']
        result[cam_id] = {
            'camera_name': session['camera_name'],
            'area_id':     session['area_id'],
            'processing':  st['processing'],
            'risk_level':  st['risk_level'],
            'crowd_count': st['crowd_count'],
        }
    return jsonify(result)

# ============================================================
# ROUTES — Planner
# ============================================================

@app.route('/api/planner/audit', methods=['POST'])
def planner_audit():
    data = request.get_json(silent=True) or {}
    dimensions = data.get('dimensions', {'width': 40, 'height': 20})
    exits      = data.get('exits', [])
    cameras    = data.get('cameras', [])
    
    # Initialize advisor if not already
    global notifier # unrelated but using global pattern
    from backend.utils.llm_advisor import LLMAdvisor
    advisor = LLMAdvisor()
    
    report = advisor.run_safety_audit(dimensions, exits, cameras)
    return jsonify({'report': report})


# ============================================================
# SocketIO
# ============================================================

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected — stopping all sessions')
    for cam_id in list(sessions.keys()):
        stop_session(cam_id)

@socketio.on('start_stream')
def handle_start_stream(data):
    camera_id = data.get('camera_id') if isinstance(data, dict) else None
    if not camera_id or camera_id not in sessions:
        return
    socketio.start_background_task(stream_video, camera_id)
    print(f"Streaming task launched for {camera_id}")

# ============================================================
# Per-Camera Streaming Worker
# ============================================================

def stream_video(camera_id):
    session = sessions.get(camera_id)
    if not session:
        return
    state = session['state']
    comp  = session['components']
    try:
        initialize_yolo()
        my_session_id = state['stream_session_id']
        print(f"[{camera_id}] Stream started (session_id={my_session_id})")
        while state['processing'] and state['stream_session_id'] == my_session_id:
            try:
                frame, success = comp['video_processor'].read_frame()
                if not success:
                    if state['source_type'] == 'video':
                        socketio.emit('stream_end', {'camera_id': camera_id, 'message': 'Video ended'})
                        state['processing'] = False
                    break

                frame        = comp['video_processor'].resize_frame(frame, Config.MAX_FRAME_WIDTH)
                detections   = yolo_detector.detect_people(frame)
                state['crowd_count'] = detections['count']

                movement_data = comp['movement_tracker'].detect_movements(frame, detections['centers'])
                frame_area    = frame.shape[0] * frame.shape[1]
                risk_result   = comp['risk_analyzer'].calculate_risk_level(
                    detections['count'], frame_area, movement_data, {}, None
                )
                state['risk_level'] = risk_result['level']
                state['alerts']     = risk_result['alerts']

                # Run alert router after every frame
                run_alert_router(
                    camera_id,
                    risk_result['level'],
                    session['camera_type'],
                    session['area_id']
                )

                movement_vectors = movement_data.get('person_vectors', [])
                comp['digital_twin'].update(detections['centers'], movement_vectors)

                # Visualisations
                annotated    = yolo_detector.draw_detections(frame, detections)
                density_grid = yolo_detector.calculate_density_grid(frame.shape, detections['centers'])
                heatmap      = comp['video_processor'].create_heatmap_overlay(annotated, density_grid, alpha=0.4)
                final_frame  = comp['video_processor'].draw_directional_arrows(heatmap, density_grid)

                risk_color = Config.RISK_COLORS[risk_result['level']]
                cv2.rectangle(final_frame, (8, 8), (340, 54), (0,0,0), -1)
                cv2.rectangle(final_frame, (8, 8), (340, 54), risk_color, 2)
                label = f"{session['camera_name']}  |  {risk_result['level']}"
                cv2.putText(final_frame, label, (14, 38),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255,255,255), 2)

                _, buf = cv2.imencode('.jpg', final_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buf).decode('utf-8')

                twin_img = comp['digital_twin'].render()
                _, twin_buf = cv2.imencode('.jpg', twin_img, [cv2.IMWRITE_JPEG_QUALITY, 60])
                twin_b64 = base64.b64encode(twin_buf).decode('utf-8')

                socketio.emit('frame_data', {
                    'camera_id':   camera_id,
                    'area_id':     session['area_id'],
                    'camera_name': session['camera_name'],
                    'frame':       frame_b64,
                    'digital_twin': twin_b64,
                    'risk_level':  risk_result['level'],
                    'crowd_count': detections['count'],
                    'alerts':      risk_result['alerts'],
                    'lstm_score':  risk_result.get('lstm_score', 0.0),
                    'lstm_level':  risk_result.get('lstm_level', 'SAFE'),
                })
                socketio.sleep(0.03)
            except Exception as fe:
                print(f"[{camera_id}] Frame error: {fe}")
                continue
    except Exception as e:
        print(f"[{camera_id}] Fatal: {e}")
        traceback.print_exc()
        socketio.emit('stream_end', {'camera_id': camera_id, 'message': str(e)})
    finally:
        print(f"[{camera_id}] Stream ended")

# ============================================================
# Entry Point
# ============================================================

if __name__ == '__main__':
    print("=" * 55)
    print("  CrowdShield — Multi-Camera AI Safety System")
    print("=" * 55)
    print(f"  Dashboard → http://localhost:5000")
    print("=" * 55)
    socketio.run(app, host='0.0.0.0', port=5000, debug=Config.DEBUG)
