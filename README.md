# 🛡️ Crowd Shield: AI-Driven Stampede Detection System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-ultralytics-red)](https://github.com/ultralytics/ultralytics)

**Crowd Shield** is a state-of-the-art real-time monitoring and predictive analytics system designed to identify, analyze, and prevent crowd stampedes. By combining spatial computer vision (YOLO) with temporal neural networks (LSTM), the system provides early warning signals before density levels reach critical thresholds.

---

## 🚀 System Architecture: The Dual-Engine Approach

The core of Crowd Shield is its unique **Dual-Engine Risk Architecture**, ensuring high reliability by combining deterministic physics with predictive AI.

### 1. The Manual Physics Engine (Spatial/Kinetic)
*   **Crowd Density**: Calculates "People per Square Meter" using YOLOv8 person detection.
*   **Optical Flow**: Measures pixel-level displacement between frames to determine the average velocity (m/s) of the crowd.
*   **Erratic Movement**: Tracks direction variance to detect "turbulent" flow—a key precursor to panic.

### 2. The AI LSTM Engine (Temporal)
*   **RNN Architecture**: Uses a Long Short-Term Memory (LSTM) network to remember the last 20 frames of crowd dynamics.
*   **Wave Detection**: Identifies rhythmic "waves" and pressure builds that are invisible to frame-by-frame math.
*   **Predictive Labeling**: Classifies behavior as `SAFE` or `UNSAFE` based on trained video datasets.

---

## 🛠️ Tech Stack

-   **Deep Learning**: YOLOv8 (Object Detection), PyTorch (LSTM Neural Network)
-   **Computer Vision**: OpenCV (Optical Flow, Heatmap Generation, Visualization)
-   **Backend**: Flask (REST API), Flask-SocketIO (Real-time WebSocket streaming)
-   **Frontend**: Vanilla HTML5/CSS3, JavaScript (Digital Twin rendering)
-   **Data Science**: NumPy, Scikit-Learn (Feature Scaling), Pandas

---

## 📂 Project Structure

```bash
crowd-stampede-detection/
├── backend/
│   ├── app.py             # Main Flask server & WebSocket orchestrator
│   ├── config.py          # System constants & risk thresholds
│   ├── models/
│   │   ├── yolo_detector.py # Person detection logic (YOLOv8)
│   │   ├── movement_tracker.py # Kinetic analysis (Optical Flow)
│   │   ├── risk_analyzer.py   # Decision engine (Dual-Engine Logic)
│   │   └── lstm_predictor.py  # LSTM inference class
│   └── utils/
│       ├── video_processor.py # Image processing & Visual overlays
│       └── digital_twin.py    # Crowd state abstraction
├── frontend/
│   ├── index.html         # Dashboard UI
│   ├── css/style.css      # Monochrome styling
│   └── js/dashboard.js    # WebSocket client & Render logic
├── training/
│   ├── feature_extractor.py # Video-to-CSV translation script
│   ├── train_lstm.py       # PyTorch training routine
│   └── data/               # Training datasets (CSV)
├── yolov8n.pt             # Pre-trained YOLO weights
└── requirements.txt       # Dependency list
```

---

## 🔄 Data Assembly Line

1.  **Ingestion**: `app.py` pulls a frame from the video source.
2.  **Detection**: `yolo_detector.py` identifies bounding boxes and center-points for every person.
3.  **Kinematics**: `movement_tracker.py` calculates the speed and direction vectors.
4.  **Prediction**: `risk_analyzer.py` feeds density + speed + variance into the LSTM model.
5.  **Visualization**: `video_processor.py` draws a **Heatmap**, **Directional Arrows**, and **Bounding Boxes**.
6.  **Broadcast**: The processed frame and risk metrics are sent via WebSockets to the frontend.
7.  **Rendering**: `dashboard.js` updates the live dashboard at 30 FPS.

---

## 🔬 Scientific Methodology

Crowd Shield quantifies human behavior into mathematical signals using the following logic:

### 1. Spatial Density Normalization
To maintain consistency across different camera resolutions, density is normalized against a reference area ($640 \times 480$ pixels):
$$\text{Density Score} = \min\left(\frac{N \times (\frac{A_{ref}}{A_{actual}})}{100}, 1.0\right)$$
*Where $N$ is detections and $A$ is pixel area.*

### 2. Kinetic Stress Calculation
Risk is not just density, but the **energy** within the crowd. The movement score is a summation of:
- **Velocity Stress**: Linear speed of crowd flow.
- **Turbulence**: Standard deviation of movement directions.
- **Discontinuity**: Sudden stops or starts found via frame-differencing.

### 3. Pressure Mapping
The system generates a spatial pressure map using:
$$\text{Pressure} = \text{Density} \times \text{Speed} \times \text{Conflict Intensity}$$
*Conflict intensity is calculated by measuring the dot product of movement vectors between neighboring nodes. Opposing vectors (collisions) yield higher conflict.*

### 4. Neural Network (LSTM) Feature Set
The LSTM does not look at the image; it looks at a sequence of 4-dimensional vectors:
`[person_count, density_percentage, average_velocity, directional_variance]`
By analyzing the **gradient** of these values over 20 frames, it can predict a stampede even if current thresholds are "LOW".

---

## ⚡ Key Features

-   **Real-time Dashboard**: No-latency streaming of processed footage.
-   **Digital Twin Visualization**: A simplified 2D map showing crowd "nodes" and their energy levels.
-   **Pressure Mapping**: Calculates Pressure ($P = Density \times Velocity \times Conflict$) to identify high-compression zones.
-   **Dynamic Alerts**: Provides action-oriented advice (e.g., "Clear evacuation paths") based on risk level.
-   **Pre-Panic Signature Detection**: Identifies gesture-based distress signals (Advanced/Dev mode).

---

## ⚙️ Installation & Setup

### 1. Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd crowd-stampede-detection

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Application
```bash
# Start the Flask server
python -m backend.app
```
Then navigate to `http://localhost:5000` in your web browser.

---

## 🧠 The AI Training Pipeline

To make Crowd Shield smarter, you must "teach" the LSTM brain using raw video footage. Think of this as a three-stage assembly line:

### Stage 1: Data Sourcing
You provide two sets of `.mp4` videos representing the two states of existence the AI needs to differentiate:
-   **Class 0 (Safe)**: Normal walking, standing, or organized crowd movement.
-   **Class 1 (Unsafe)**: Footage of running, stampedes, panic, or "crowd crush" events.

### Stage 2: Feature Extraction (`feature_extractor.py`)
The system converts raw pixels into mathematical signals. Instead of "watching" colors, the AI is trained on 4 key indicators per frame:
1.  **Crowd Count**: Raw number of people (via YOLOv8).
2.  **Density %**: Horizontal area coverage of the crowd.
3.  **Avg Speed**: Mean kinetic displacement (pixels/frame) via Optical Flow.
4.  **Direction Variance**: Measures the "chaos" of flow—orderly movement has low variance; panic has high variance.

**Example Command:**
```bash
python -m training.feature_extractor --video paths/to/panic_video.mp4 --label 1
```
This appends the frame-by-frame math to `training/data/training_data.csv`.

### Stage 3: LSTM Learning Logic (`train_lstm.py`)
The training script performs several critical "data cleaning" steps to ensure the brain learns correctly:
-   **Sliding Windows**: LSTMs require a "memory span." We group the CSV data into sequences of **30 frames** (~1 second) so the model can learn *acceleration* and *trends* over time, not just snapshots.
-   **Shuffling**: We mix up the "Safe" and "Unsafe" sequences. This prevents the model from "memorizing" the order of the videos and forces it to learn the actual visual patterns.
-   **Normalization**: All numbers (Count, Speed, etc.) are squashed into a similar scale (Mean=0, Std=1). Without this, the AI might think a high crowd count is more "important" than a high speed just because the number is larger.

**Run Training:**
```bash
python -m training.train_lstm
```
The result is `stampede_lstm.pth` (the brain weights) and `stampede_lstm_scaler.json` (the normalization rules). Copy these to `backend/models/` to deploy.

---

## ⚠️ Requirements
-   **Python 3.8+**
-   **Web Camera or MP4 Video Source**
-   **Modern Web Browser** (Chrome/Edge/Safari)

---
*Note: This project was developed as a college project to showcase the integration of Computer Vision and Recurrent Neural Networks in public safety applications.*
