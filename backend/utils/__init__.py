# Utils package
# Import existing modules
from .video_processor import VideoProcessor
from .iot_simulator import IoTSimulator
from .digital_twin import DigitalTwin
from .llm_advisor import LLMAdvisor
from .notifier import Notifier

# Import new modules (optional - won't break if there are issues)
try:
    from .silent_guidance import SilentGuidance
    from .micro_evacuation import MicroEvacuation
    _new_modules_available = True
except ImportError as e:
    print(f"Warning: New utility modules not available: {e}")
    SilentGuidance = None
    MicroEvacuation = None
    _new_modules_available = False

__all__ = [
    'VideoProcessor',
    'IoTSimulator',
    'DigitalTwin',
    'LLMAdvisor',
    'Notifier',
    'SilentGuidance',
    'MicroEvacuation'
]
