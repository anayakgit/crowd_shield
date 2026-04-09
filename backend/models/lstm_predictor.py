"""
LSTM Stampede Predictor
========================
Loads the trained stampede_lstm.pth model and applies it in real-time
to a sliding window of crowd features extracted per frame.

The predictor is stateful: it maintains a rolling buffer of the last
WINDOW_SIZE feature vectors. Once the buffer is full, it returns a
probability score (0.0 = safe, 1.0 = stampede) on every call.
"""

import os
import json
import numpy as np

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Must match the architecture used in train_lstm.py
WINDOW_SIZE  = 20
HIDDEN_SIZE  = 64
NUM_LAYERS   = 2
FEATURES     = ["crowd_count", "density_pct", "avg_speed", "direction_variance"]

_MODEL_DIR   = os.path.dirname(__file__)
_MODEL_PATH  = os.path.join(_MODEL_DIR, "stampede_lstm.pth")
_SCALER_PATH = os.path.join(_MODEL_DIR, "stampede_lstm_scaler.json")


# ── Same architecture as train_lstm.py ──────────────────────────────────────

class _StampedeDetectorLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=len(FEATURES),
            hidden_size=HIDDEN_SIZE,
            num_layers=NUM_LAYERS,
            batch_first=True,
            dropout=0.2
        )
        self.classifier = nn.Sequential(
            nn.Linear(HIDDEN_SIZE, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_step = lstm_out[:, -1, :]
        return self.classifier(last_step).squeeze(1)


# ── Public predictor class ───────────────────────────────────────────────────

class LSTMPredictor:
    """
    Real-time sliding-window LSTM inference.

    Usage:
        predictor = LSTMPredictor()
        # each frame:
        result = predictor.update(crowd_count, density_pct, avg_speed, direction_variance)
        print(result['probability'], result['label'])
    """

    def __init__(self):
        self.loaded   = False
        self.model    = None
        self.device   = None
        self.mean_    = None
        self.scale_   = None
        self._buffer  = []   # rolling list of raw feature vectors

        if not TORCH_AVAILABLE:
            print("⚠️  LSTMPredictor: PyTorch not found — LSTM disabled.")
            return

        if not os.path.exists(_MODEL_PATH):
            print(f"⚠️  LSTMPredictor: model file not found at {_MODEL_PATH}")
            return

        if not os.path.exists(_SCALER_PATH):
            print(f"⚠️  LSTMPredictor: scaler file not found at {_SCALER_PATH}")
            return

        try:
            # Load scaler
            with open(_SCALER_PATH) as f:
                scaler_data = json.load(f)
            self.mean_  = np.array(scaler_data["mean"],  dtype=np.float32)
            self.scale_ = np.array(scaler_data["scale"], dtype=np.float32)

            # Select device
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")

            # Load model
            self.model = _StampedeDetectorLSTM().to(self.device)
            self.model.load_state_dict(
                torch.load(_MODEL_PATH, map_location=self.device)
            )
            self.model.eval()

            self.loaded = True
            print(f"✅ LSTMPredictor loaded — device={self.device}, window={WINDOW_SIZE}")

        except Exception as e:
            print(f"❌ LSTMPredictor failed to load: {e}")
            self.loaded = False

    # ── Core method ─────────────────────────────────────────────────────────

    def update(self, crowd_count: float, density_pct: float,
               avg_speed: float, direction_variance: float) -> dict:
        """
        Feed one frame's features, get back an inference result.

        Returns:
            {
                'probability': float,   # 0.0–1.0 (stampede likelihood)
                'label':       str,     # 'SAFE' | 'UNSAFE' | 'BUFFERING'
                'ready':       bool,    # True once window is full
            }
        """
        raw = np.array([crowd_count, density_pct, avg_speed, direction_variance],
                       dtype=np.float32)
        self._buffer.append(raw)

        # Keep only last WINDOW_SIZE frames
        if len(self._buffer) > WINDOW_SIZE:
            self._buffer.pop(0)

        # Not enough frames yet
        if len(self._buffer) < WINDOW_SIZE:
            return {'probability': 0.0, 'label': 'BUFFERING', 'ready': False}

        if not self.loaded:
            return {'probability': 0.0, 'label': 'SAFE', 'ready': True}

        try:
            # Normalise
            window = np.stack(self._buffer, axis=0)                 # [W, 4]
            window = (window - self.mean_) / (self.scale_ + 1e-8)  # z-score

            # Run inference
            with torch.no_grad():
                tensor = torch.tensor(window, dtype=torch.float32)  # [W, 4]
                tensor = tensor.unsqueeze(0).to(self.device)        # [1, W, 4]
                prob = float(self.model(tensor).item())

            label = 'UNSAFE' if prob >= 0.5 else 'SAFE'
            return {'probability': round(prob, 4), 'label': label, 'ready': True}

        except Exception as e:
            print(f"LSTMPredictor inference error: {e}")
            return {'probability': 0.0, 'label': 'SAFE', 'ready': True}

    def reset(self):
        """Clear the frame buffer (call when starting a new video)."""
        self._buffer = []
