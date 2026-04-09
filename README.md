
## Installation

### Prerequisites
- Python 3.8 or higher
- PyTorch (for the AI LSTM neural network)

### Step 1: Create Virtual Environment

```bash
python -m venv venv
```

### Step 2: Activate Virtual Environment

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Web Dashboard

1. Activate virtual environment (if not already activated)
2. Run the Flask application:

```bash
python -m backend.app
```

3. Open your browser and navigate to `http://localhost:5000`.

The dashboard features a **Dual-Engine Risk Architecture**:
- **Manual Risk Assessment**: Calculates immediate danger frame-by-frame using crowd density, speed, and variance thresholds.
- **AI LSTM Model**: Uses a trained PyTorch Long Short-Term Memory (LSTM) neural network that holds a 20-frame rolling window buffer in its memory to anticipate crowd wave dynamics before they hit critical thresholds.

---

## Model Training & Fine-Tuning

You can train your own custom LSTM model on new video datasets of crowd behavior:

### 1. Feature Extraction
Convert raw `.mp4` video footage into mathematical temporal data using YOLO and optical flow. The script limits parsing to specific segments using `--max_seconds`.

```bash
# Extract 30 seconds of features for safe and unsafe datasets
python -m training.feature_extractor --video path/to/safe_video.mp4 --label 0 --max_seconds 30
python -m training.feature_extractor --video path/to/unsafe_video.mp4 --label 1 --max_seconds 30
```
This generates a combined `training/data/training_data.csv`.

### 2. LSTM Training
Train the recurrent neural network on the extracted sequences. The script automatically divides the time series data into overlapping windows, shuffles them evenly, and optimizes learning weights.

```bash
# Train the model
python -m training.train_lstm
```
The output will save `stampede_lstm.pth` (model weights) and `stampede_lstm_scaler.json` (normalization coefficients). 

### 3. Deployment
To use your newly trained model in the live dashboard, copy the two generated files into the `backend/models/` directory. The AI Predictor class will load them dynamically on server start.

