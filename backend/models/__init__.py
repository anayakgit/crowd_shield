# Models package
# Import existing modules
from .yolo_detector import YOLODetector
from .risk_analyzer import RiskAnalyzer
from .movement_tracker import MovementTracker

# Import new modules (optional - won't break if there are issues)
try:
    from .pose_detector import PoseDetector
    from .pre_panic_detector import PrePanicDetector
    from .adaptive_threshold import AdaptiveThreshold
    _new_modules_available = True
except ImportError as e:
    print(f"Warning: New modules not available: {e}")
    PoseDetector = None
    PrePanicDetector = None
    AdaptiveThreshold = None
    _new_modules_available = False

__all__ = [
    'YOLODetector',
    'RiskAnalyzer',
    'MovementTracker',
    'PoseDetector',
    'PrePanicDetector',
    'AdaptiveThreshold'
]
