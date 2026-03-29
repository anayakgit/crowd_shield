from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import os
import base64
from datetime import datetime
import json

from backend.config import Config
from backend.models.yolo_detector import YOLODetector
from backend.models.movement_tracker import MovementTracker
from backend.models.risk_analyzer import RiskAnalyzer
from backend.utils.video_processor import VideoProcessor
from backend.utils.iot_simulator import IoTSimulator
from backend.utils.digital_twin import DigitalTwin
from backend.utils.llm_advisor import LLMAdvisor
from backend.utils.notifier import Notifier

# NEW: Import advanced feature modules
try:
    from backend.models.pose_detector import PoseDetector
    from backend.models.pre_panic_detector import PrePanicDetector
    from backend.models.adaptive_threshold import AdaptiveThreshold
    from backend.utils.silent_guidance import SilentGuidance
    from backend.utils.micro_evacuation import MicroEvacuation
    NEW_FEATURES_AVAILABLE = True
    print("Advanced features loaded successfully")
except ImportError as e:
    print(f"Advanced features not available: {e}")
    PoseDetector = None
    PrePanicDetector = None
    AdaptiveThreshold = None
    SilentGuidance = None
    MicroEvacuation = None
    NEW_FEATURES_AVAILABLE = False

import time  # For timestamps

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create upload directory
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# Initialize components
yolo_detector = None
movement_tracker = MovementTracker()
risk_analyzer = RiskAnalyzer()
video_processor = VideoProcessor()
iot_simulator = IoTSimulator()
digital_twin = DigitalTwin()
llm_advisor = LLMAdvisor()
notifier = Notifier()

# NEW: Initialize advanced feature components
# DISABLED FOR PERFORMANCE - Set to False to keep it simple
ENABLE_ADVANCED_FEATURES = False  # Change to True to enable advanced features

if NEW_FEATURES_AVAILABLE and ENABLE_ADVANCED_FEATURES:
    pose_detector = PoseDetector()
    pre_panic_detector = PrePanicDetector()
    adaptive_threshold = AdaptiveThreshold()
    silent_guidance = SilentGuidance(frame_width=1280, frame_height=720)
    micro_evacuation = MicroEvacuation()
    print("✅ Advanced feature modules initialized")
else:
    pose_detector = None
    pre_panic_detector = None
    adaptive_threshold = None
    silent_guidance = None
    micro_evacuation = None
    if not ENABLE_ADVANCED_FEATURES:
        print("Advanced features disabled for better performance")

# Global state
current_state = {
    'processing': False,
    'source_type': None,  # 'video' or 'webcam'
    'risk_level': 'LOW',
    'crowd_count': 0,
    'alerts': [],
    'iot_data': {},
    'digital_twin_state': {},
    'stream_session_id': 0  # Track stream sessions to handle race conditions
}

def reset_all_state():
    """Reset all component state for new video processing"""
    global movement_tracker, risk_analyzer, digital_twin
    
    print("Resetting all component state...")
    
    # Reset movement tracker state (clears prev_gray and history)
    movement_tracker.prev_gray = None
    movement_tracker.movement_history = []
    
    # Reset risk analyzer history
    risk_analyzer.risk_history = []
    risk_analyzer.alert_active = False
    
    # Reset digital twin
    digital_twin.nodes = []
    digital_twin.node_history = []
    
    # Reset current state metrics
    current_state['risk_level'] = 'LOW'
    current_state['crowd_count'] = 0
    current_state['alerts'] = []
    current_state['iot_data'] = {}
    current_state['digital_twin_state'] = {}
    
    print("All component state reset complete")


def initialize_yolo():
    """Lazy initialization of YOLO model"""
    global yolo_detector
    if yolo_detector is None:
        print("Initializing YOLO model...")
        yolo_detector = YOLODetector()
        print("YOLO model loaded successfully")


@app.route('/')
def index():
    """Serve the main dashboard"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    """Upload and start processing a video file"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Stop any previous processing and increment session ID
    if current_state['processing']:
        print("Stopping previous processing before new upload...")
        current_state['processing'] = False  # Signal current stream to stop
        current_state['stream_session_id'] += 1  # Increment session to invalidate old streams
        import time
        time.sleep(0.2)  # Brief wait for old stream to exit
    
    # Release old video and reset all state
    video_processor.release()
    reset_all_state()
    current_state['source_type'] = None
    
    # Save uploaded file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'video_{timestamp}_{file.filename}'
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Open video file
    try:
        video_info = video_processor.open_video_file(filepath)
        current_state['source_type'] = 'video'
        current_state['processing'] = True
        # Note: session_id was already incremented when stopping old stream (if any)
        # For first video, session_id stays at 0 which is fine
        
        print(f"Video uploaded successfully: {filename}, session_id: {current_state['stream_session_id']}")
        
        return jsonify({
            'message': 'Video uploaded successfully',
            'video_info': video_info,
            'filepath': filepath,
            'session_id': current_state['stream_session_id']
        })
    except Exception as e:
        print(f"Error opening video: {str(e)}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/start_webcam', methods=['POST'])
def start_webcam():
    """Start webcam processing (Disabled)"""
    return jsonify({'error': 'Webcam feature is disabled'}), 403



@app.route('/api/stop_processing', methods=['POST'])
def stop_processing():
    """Stop current video/webcam processing"""
    current_state['processing'] = False
    current_state['stream_session_id'] += 1  # Invalidate current stream
    import time
    time.sleep(0.1)  # Brief wait for stream to exit
    video_processor.release()
    current_state['source_type'] = None
    
    return jsonify({'message': 'Processing stopped'})


@app.route('/api/get_status', methods=['GET'])
def get_status():
    """Get current system status"""
    return jsonify({
        'processing': current_state['processing'],
        'source_type': current_state['source_type'],
        'risk_level': current_state['risk_level'],
        'crowd_count': current_state['crowd_count']
    })


@app.route('/api/get_risk_data', methods=['GET'])
def get_risk_data():
    """Get detailed risk assessment data"""
    return jsonify({
        'risk_level': current_state['risk_level'],
        'alerts': current_state['alerts'],
        'trend': risk_analyzer.get_risk_trend()
    })


@app.route('/api/get_iot_data', methods=['GET'])
def get_iot_data():
    """Get IoT sensor data (Disabled)"""
    return jsonify({'error': 'IoT feature is disabled'}), 403


@app.route('/api/get_digital_twin', methods=['GET'])
def get_digital_twin_data():
    """Get digital twin state"""
    return jsonify(current_state['digital_twin_state'])


@app.route('/api/get_evacuation_advice', methods=['GET'])
def get_evacuation_advice():
    """Get LLM-generated evacuation advice (Disabled)"""
    return jsonify({'error': 'Advice feature is disabled'}), 403


@app.route('/api/notify_authorities', methods=['POST'])
def notify_authorities():
    """Manual notification to authorities (Disabled)"""
    return jsonify({'error': 'Notification feature is disabled'}), 403


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connection_response', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')
    # Stop processing and release camera when client disconnects
    global current_state
    if current_state['processing']:
        print("Stopping processing and releasing camera due to client disconnect")
        current_state['processing'] = False
        current_state['stream_session_id'] += 1
        video_processor.release()
        current_state['source_type'] = None


@socketio.on('start_stream')
def handle_start_stream():
    """Start video streaming to client (non-blocking)"""
    # Start streaming in background task to avoid blocking
    socketio.start_background_task(stream_video)
    print('Video streaming task started in background')


def stream_video():
    """Background task for streaming video frames"""
    try:
        initialize_yolo()
        
        # Capture the session ID when this stream starts
        my_session_id = current_state['stream_session_id']
        
        print(f'Starting video stream... (session_id: {my_session_id})')
        print(f'  processing={current_state["processing"]}, source_type={current_state["source_type"]}')
        
        frame_num = 0
        while current_state['processing'] and current_state['stream_session_id'] == my_session_id:
            try:
                # Double-check session is still valid
                if current_state['stream_session_id'] != my_session_id:
                    print(f'Session {my_session_id} superseded by {current_state["stream_session_id"]}, exiting...')
                    break
                    
                frame, success = video_processor.read_frame()
                frame_num += 1
                
                if frame_num % 30 == 1:  # Log every 30 frames
                    print(f'  Frame {frame_num}: success={success}, processing={current_state["processing"]}')
                
                if not success:
                    print(f'  Frame {frame_num}: read failed, source_type={current_state["source_type"]}')
                    if current_state['source_type'] == 'video':
                        # Video ended, loop or stop
                        socketio.emit('stream_end', {'message': 'Video ended'})
                        break
                    else:
                        continue
                
                # Resize frame
                frame = video_processor.resize_frame(frame, Config.MAX_FRAME_WIDTH)
                
                # Detect people
                detections = yolo_detector.detect_people(frame)
                current_state['crowd_count'] = detections['count']
                
                # NEW: Pose detection (if available)
                poses = None
                if ENABLE_ADVANCED_FEATURES and NEW_FEATURES_AVAILABLE and pose_detector and detections['boxes']:
                    try:
                        poses = pose_detector.detect_poses(frame, detections['boxes'])
                    except Exception as pose_error:
                        # Silently fail - pose detection is optional
                        poses = None
                
                # Track movements
                movement_data = movement_tracker.detect_movements(frame, detections['centers'])
                
                # NEW: Pre-panic signature detection
                pre_panic_warnings = None
                if ENABLE_ADVANCED_FEATURES and NEW_FEATURES_AVAILABLE and pre_panic_detector:
                    try:
                        pre_panic_sigs = pre_panic_detector.detect_signatures(
                            movement_data, poses, detections['count']
                        )
                        if pre_panic_sigs['detected']:
                            pre_panic_warnings = pre_panic_detector.get_warning_summary(pre_panic_sigs)
                            print(f"PRE-PANIC WARNING: {pre_panic_warnings}")
                    except Exception as pre_panic_error:
                        # Don't crash on pre-panic detection errors
                        pre_panic_warnings = None
                
                # Generate IoT data
                # iot_data = iot_simulator.generate_sensor_data(
                #     detections['count'],
                #     movement_data.get('movement_magnitude', 0)
                # )
                # current_state['iot_data'] = iot_data
                iot_data = {}
                
                # NEW: Get adaptive thresholds (if available)
                if ENABLE_ADVANCED_FEATURES and NEW_FEATURES_AVAILABLE and adaptive_threshold:
                    try:
                        thresholds = adaptive_threshold.get_thresholds()
                        Config.LOW_RISK_THRESHOLD = thresholds[0]
                        Config.MEDIUM_RISK_THRESHOLD = thresholds[1]
                    except Exception:
                        pass  # Use default thresholds
                
                # Calculate pressure map
                pressure_map = None
                if ENABLE_ADVANCED_FEATURES and NEW_FEATURES_AVAILABLE and detections['count'] > 0:
                    try:
                        # Create grids for pressure calculation
                        h, w = frame.shape[:2]
                        density_grid = yolo_detector.calculate_density_grid(frame.shape, detections['centers'])
                        
                        # Create speed grid from movement magnitude
                        speed_grid = np.ones((h, w), dtype=np.float32) * movement_data.get('movement_magnitude', 0)
                        
                        # Get optical flow as direction grid
                        direction_grid = movement_data.get('optical_flow')
                        if direction_grid is not None and direction_grid.shape[:2] == (h, w):
                            pressure_map = risk_analyzer.calculate_pressure_map(
                                density_grid, speed_grid, direction_grid
                            )
                    except Exception as pressure_error:
                        # Pressure map calculation failed - continue without it
                        pressure_map = None
                
                # Calculate risk
                frame_area = frame.shape[0] * frame.shape[1]
                risk_result = risk_analyzer.calculate_risk_level(
                    detections['count'],
                    frame_area,
                    movement_data,
                    iot_data,
                    pressure_map
                )
                current_state['risk_level'] = risk_result['level']
                current_state['alerts'] = risk_result['alerts']
                
                # NEW: Track panic initiators
                if ENABLE_ADVANCED_FEATURES and NEW_FEATURES_AVAILABLE and poses:
                    try:
                        # Count panic gestures from poses
                        panic_gesture_counts = []
                        for pose in poses:
                            if pose:
                                panic_gesture_counts.append(len(pose.get('panic_gestures', [])))
                            else:
                                panic_gesture_counts.append(0)
                        
                        if any(panic_gesture_counts):
                            timestamp = time.time()
                            new_initiators = risk_analyzer.track_panic_initiators(
                                detections['centers'], panic_gesture_counts, timestamp
                            )
                            if new_initiators:
                                print(f"{len(new_initiators)} new panic initiators detected!")
                    except Exception:
                        pass  # Don't crash on panic tracking errors
                
                # Automatic external notification for HIGH risk
                # if risk_result['level'] == 'HIGH':
                #     notifier.send_email_alert(
                #         risk_level=risk_result['level'],
                #         crowd_count=detections['count'],
                #         alerts=risk_result['alerts'],
                #         manual=False
                #     )
                
                # Update digital twin
                movement_vectors = movement_data.get('person_vectors', [])
                digital_twin.update(detections['centers'], movement_vectors)
                current_state['digital_twin_state'] = digital_twin.export_state()
                
                # Create visualizations
                annotated_frame = yolo_detector.draw_detections(frame, detections)
                
                # Add density heatmap
                density_grid = yolo_detector.calculate_density_grid(frame.shape, detections['centers'])
                heatmap_frame = video_processor.create_heatmap_overlay(annotated_frame, density_grid, alpha=0.4)
                
                # NEW: Add silent guidance overlays (if available and high risk)
                if ENABLE_ADVANCED_FEATURES and NEW_FEATURES_AVAILABLE and silent_guidance and pressure_map is not None:
                    guidance_data = silent_guidance.generate_guidance(pressure_map, detections['centers'])
                    heatmap_frame = silent_guidance.overlay_guidance(heatmap_frame, guidance_data)
                    
                    # Micro-evacuation planning for HIGH risk
                    if risk_result['level'] == 'HIGH' and detections['count'] > 5:
                        target_groups = micro_evacuation.identify_target_groups(
                            pressure_map, detections['centers'], min_group_size=3
                        )
                        if target_groups:
                            evacuation_plans = micro_evacuation.generate_redirection_plan(
                                target_groups,
                                guidance_data.get('safe_zones', []),
                                silent_guidance.exit_locations
                            )
                            pressure_release = micro_evacuation.calculate_pressure_release(
                                evacuation_plans, pressure_map
                            )
                            print(f"Micro-evacuation: {len(target_groups)} groups, "
                                  f"{pressure_release['people_redirected']} people, "
                                  f"{pressure_release['estimated_reduction']*100:.1f}% reduction")
                
                # Add directional arrows
                final_frame = video_processor.draw_directional_arrows(heatmap_frame, density_grid)
                
                # Add risk level indicator
                risk_color = Config.RISK_COLORS[risk_result['level']]
                cv2.rectangle(final_frame, (10, 50), (250, 100), risk_color, -1)
                cv2.putText(final_frame, f'Risk: {risk_result["level"]}', (20, 85),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
                
                # NEW: Add pre-panic warning banner
                if pre_panic_warnings:
                    cv2.rectangle(final_frame, (10, 110), (600, 160), (0, 165, 255), -1)
                    cv2.putText(final_frame, 'PRE-PANIC WARNING', (20, 145),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                
                # Encode frame to base64
                _, buffer = cv2.imencode('.jpg', final_frame)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Render digital twin
                twin_visual = digital_twin.render()
                _, twin_buffer = cv2.imencode('.jpg', twin_visual)
                twin_base64 = base64.b64encode(twin_buffer).decode('utf-8')
                
                # Send to client
                socketio.emit('frame_data', {
                    'frame': frame_base64,
                    'digital_twin': twin_base64,
                    'risk_level': risk_result['level'],
                    'crowd_count': detections['count'],
                    'alerts': risk_result['alerts'],
                    # 'iot_data': iot_data
                })
                
                socketio.sleep(0.03)  # ~30 FPS
                
            except Exception as frame_error:
                # Log error but continue processing
                print(f"Error processing frame: {str(frame_error)}")
                import traceback
                traceback.print_exc()
                # Continue to next frame instead of crashing
                continue
                
    except Exception as stream_error:
        print(f"Fatal error in video stream: {str(stream_error)}")
        import traceback
        traceback.print_exc()
        socketio.emit('stream_end', {'message': f'Error: {str(stream_error)}'})
    finally:
        print(f'Video streaming task ended (was session_id: {my_session_id}, current: {current_state["stream_session_id"]})')



if __name__ == '__main__':
    print("="*50)
    print("AI-Driven Crowd Stress Detection System")
    print("="*50)
    print(f"Server starting on http://localhost:5000")
    print("Open your browser and navigate to http://localhost:5000")
    print("="*50)
    
    # Debug: Print all registered routes
    print("\nRegistered API routes:")
    for rule in app.url_map.iter_rules():
        if '/api/' in str(rule):
            print(f"  {rule} -> {rule.endpoint}")
    print("="*50)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=Config.DEBUG)
