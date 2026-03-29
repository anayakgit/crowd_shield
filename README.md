# AI-Driven Crowd Stress Detection and Stampede Prevention System

An intelligent real-time crowd monitoring system using YOLOv8, OpenCV, and AI-driven risk assessment to prevent stampede incidents. The system provides live video analysis, crowd density mapping, risk level detection, and LLM-powered evacuation guidance.

![System Status](https://img.shields.io/badge/status-active-success)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

### Core Capabilities
- **Real-time Crowd Detection**: YOLOv8-based people detection and counting
- **Risk Assessment**: Multi-factor risk analysis (Low/Medium/High)
- **Micro-Movement Tracking**: Optical flow analysis to detect panic behaviors
- **Dynamic Crowd Pressure Map**: Visual heatmap overlay showing density hotspots
- **Directional Guidance**: UI-based arrows to guide crowd to less dense areas
- **Digital Twin Visualization**: Real-time 2D representation of crowd positions
- **AI Evacuation Advice**: LLM-generated context-aware evacuation strategies
- **IoT Sensor Simulation**: Hardcoded environmental data (temp, noise, humidity, air quality)
- **Alert System**: Real-time warnings and authority notifications

### Technical Features
- Webcam and video file support
- WebSocket-based real-time streaming
- Rule-based panic contagion prediction
- Premium dark-themed responsive UI
- REST API for data access

## Tech Stack

### Backend
- **Python 3.8+**
- **Flask** - Web framework
- **Flask-SocketIO** - Real-time communication
- **YOLOv8 (Ultralytics)** - Crowd detection
- **OpenCV** - Video processing and optical flow
- **Google Gemini API** - LLM evacuation advice
- **NumPy** - Numerical computations

### Frontend
- **HTML5** - Structure
- **CSS3** - Styling with glassmorphism effects
- **JavaScript** - Interactivity
- **Socket.IO Client** - Real-time updates

## Project Structure

```
crowd_detection/
├── backend/
│   ├── app.py                      # Main Flask application
│   ├── config.py                   # Configuration settings
│   ├── models/
│   │   ├── yolo_detector.py        # YOLOv8 crowd detection
│   │   ├── risk_analyzer.py        # Risk level calculation
│   │   └── movement_tracker.py     # Micro-movement detection
│   └── utils/
│       ├── video_processor.py      # Video/webcam handling
│       ├── iot_simulator.py        # IoT sensor simulation
│       ├── digital_twin.py         # Digital twin visualization
│       └── llm_advisor.py          # LLM evacuation advice
├── frontend/
│   ├── index.html                  # Main dashboard
│   ├── css/
│   │   └── style.css               # Premium styling
│   └── js/
│       └── dashboard.js            # Frontend logic
├── datasets/                        # Kaggle datasets (to be downloaded)
├── static/
│   └── uploads/                    # Uploaded videos
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
└── README.md                       # This file
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Webcam (for live detection)
- Google Gemini API key (free tier available)

### Step 1: Clone or Navigate to Project

```bash
cd "c:\Users\Mohit Sharma\Desktop\crowd_detection"
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
```

### Step 3: Activate Virtual Environment

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and add your Google Gemini API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

   Get a free API key at: https://makersuite.google.com/app/apikey

### Step 6: Download YOLOv8 Model (Optional)

The YOLOv8n model will be downloaded automatically on first run. To use a different model:

```bash
# Download YOLOv8 medium model (more accurate but slower)
pip install ultralytics
python -c "from ultralytics import YOLO; YOLO('yolov8m.pt')"
```

Then update `.env`:
```
YOLO_MODEL=yolov8m.pt
```

## Usage

### Starting the Application

1. Activate virtual environment (if not already activated)
2. Run the Flask application:

```bash
python -m backend.app
```

3. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

### Using the Dashboard

#### Option 1: Webcam Mode
1. Click **"Start Webcam"** button
2. Allow browser webcam access if prompted
3. Live detection will begin automatically

#### Option 2: Video Upload Mode
1. Click **"Upload Video"** button
2. Select a crowd video file (MP4, AVI, etc.)
3. Processing will start automatically

#### Dashboard Features

- **Live Feed**: Shows processed video with bounding boxes and heatmap overlay
- **Risk Assessment**: Displays current risk level (LOW/MEDIUM/HIGH)
- **Active Alerts**: Lists all current warnings and their severity
- **IoT Sensors**: Shows simulated environmental data
- **Digital Twin**: 2D visualization of crowd positions
- **AI Evacuation Advice**: Click refresh to get LLM-generated guidance
- **Notify Authorities**: Send emergency alert

### Stopping Processing

Click the **"Stop"** button to end video/webcam processing.

## Datasets

This project uses public crowd datasets from Kaggle:

1. **Abnormal High-Density Crowds Dataset**
   - URL: https://www.kaggle.com/datasets/angelchi56/abnormal-highdensity-crowds
   - Contains high-density crowd videos

2. **Crowd Panic Dataset**
   - URL: https://www.kaggle.com/datasets/aj1714/crowd-panic-dataset
   - Contains crowd panic scenarios

### Downloading Datasets (Optional)

To download datasets for testing:

1. Install Kaggle CLI:
   ```bash
   pip install kaggle
   ```

2. Set up Kaggle API credentials (follow: https://www.kaggle.com/docs/api)

3. Download datasets:
   ```bash
   mkdir datasets
   cd datasets
   kaggle datasets download -d angelchi56/abnormal-highdensity-crowds
   kaggle datasets download -d aj1714/crowd-panic-dataset
   ```

4. Extract the downloaded files

## Risk Level Calculation

The system uses a multi-factor approach:

### Factors
1. **Crowd Density** (50% weight)
   - People per unit area
   - Normalized against frame size

2. **Movement Analysis** (30% weight)
   - Optical flow magnitude
   - Erratic movement count
   - Panic pattern indicators

3. **IoT Sensors** (20% weight)
   - Temperature
   - Noise level
   - Humidity
   - Air quality

### Risk Levels
- **LOW**: < 30% risk score, normal operations
- **MEDIUM**: 30-60% risk score, elevated monitoring
- **HIGH**: > 60% risk score, critical intervention needed

## Panic Detection Indicators

The system detects:
- **High Velocity Movements**: Sudden fast movements
- **Sudden Direction Changes**: Erratic behavior
- **Convergent Escape Behavior**: Everyone moving same direction
- **Density Hotspots**: Areas with excessive crowding

## API Endpoints

### REST API

- `GET /` - Main dashboard
- `POST /api/upload_video` - Upload video file
- `POST /api/start_webcam` - Start webcam processing
- `POST /api/stop_processing` - Stop current processing
- `GET /api/get_status` - Get system status
- `GET /api/get_risk_data` - Get risk assessment data
- `GET /api/get_iot_data` - Get IoT sensor readings
- `GET /api/get_digital_twin` - Get digital twin state
- `GET /api/get_evacuation_advice` - Get LLM evacuation advice
- `POST /api/notify_authorities` - Manual notification to authorities via email

### WebSocket Events

- `connect` - Client connected
- `start_stream` - Begin video streaming
- `frame_data` - Receive processed frame and analytics
- `stream_end` - Video processing completed

## Configuration

Edit `backend/config.py` or `.env` to customize:

- Risk thresholds
- YOLO confidence threshold
- Frame processing rate
- Video dimensions
- IoT simulation parameters
- SMTP and Email settings

## Troubleshooting

### Webcam Not Working
- Ensure webcam is not in use by another application
- Check browser permissions for camera access
- Try a different browser (Chrome recommended)

### YOLO Model Download Fails
```bash
# Manually download
pip install ultralytics
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### LLM Advice Not Generating
- Verify GEMINI_API_KEY in `.env`
- Check API key is valid
- System will fallback to hardcoded advice if API fails

### High CPU Usage
- Reduce `MAX_FRAME_WIDTH` in `.env`
- Increase `FRAME_SKIP` value
- Use `yolov8n.pt` instead of larger models

## Performance Optimization

For better performance:

1. **Use lighter YOLO model**: `yolov8n.pt` (fastest)
2. **Reduce frame resolution**: Set `MAX_FRAME_WIDTH=640`
3. **Skip frames**: Set `FRAME_SKIP=3` or higher
4. **Close other applications**: Free up system resources

## Limitations

- Pre-panic gesture detection is approximate (rule-based, not ML)
- No physical IoT devices (simulated data only)
- Digital twin is 2D representation (not 3D)
- Requires good lighting for accurate detection
- Performance depends on hardware

## Future Enhancements

- 3D digital twin visualization
- ML-based panic gesture recognition
- Real IoT sensor integration
- Multi-camera support
- Crowd flow prediction
- Historical analytics dashboard


