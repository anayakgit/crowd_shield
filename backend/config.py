import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'True') == 'True'
    
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Risk level thresholds
    LOW_RISK_THRESHOLD = float(os.getenv('LOW_RISK_THRESHOLD', '0.25'))
    MEDIUM_RISK_THRESHOLD = float(os.getenv('MEDIUM_RISK_THRESHOLD', '0.55'))
    
    # YOLO configuration
    YOLO_MODEL = os.getenv('YOLO_MODEL', 'yolov8s.pt')
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.25'))
    
    # Video processing settings
    FRAME_SKIP = int(os.getenv('FRAME_SKIP', '2'))
    MAX_FRAME_WIDTH = int(os.getenv('MAX_FRAME_WIDTH', '1280'))
    
    # File paths
    UPLOAD_FOLDER = 'static/uploads'
    DATASET_FOLDER = 'datasets'
    MODEL_FOLDER = 'backend/models/weights'
    
    # Risk level colors
    RISK_COLORS = {
        'LOW': (0, 255, 0),      # Green
        'MEDIUM': (255, 165, 0),  # Orange
        'HIGH': (255, 0, 0)       # Red
    }
    
    # Crowd density thresholds (people per square meter equivalent)
    DENSITY_LOW = 0.5
    DENSITY_MEDIUM = 1.0
    DENSITY_HIGH = 2.0
    
    # IoT Sensor simulation parameters
    TEMP_BASE = 25.0  # Base temperature in Celsius
    TEMP_CROWD_FACTOR = 0.5  # Temperature increase per person
    NOISE_BASE = 50.0  # Base noise level in dB
    NOISE_CROWD_FACTOR = 2.0  # Noise increase per person

    # Email Notification Settings
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL', '')
