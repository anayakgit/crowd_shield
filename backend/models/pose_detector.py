import cv2
import numpy as np

# Try different MediaPipe import methods
try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    MEDIAPIPE_AVAILABLE = True
except (ImportError, AttributeError):
    try:
        # Alternative import for older versions
        from mediapipe.python.solutions import pose as mp_pose
        from mediapipe.python.solutions import drawing_utils as mp_drawing
        MEDIAPIPE_AVAILABLE = True
    except ImportError:
        mp_pose = None
        mp_drawing = None
        MEDIAPIPE_AVAILABLE = False
        print("⚠️ MediaPipe not available - pose detection disabled")

class PoseDetector:
    """Detect body poses and panic gestures using MediaPipe"""
    
    def __init__(self):
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("MediaPipe not available")
        
        self.mp_pose = mp_pose
        self.mp_drawing = mp_drawing
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.pose_history = []
        
    def detect_poses(self, frame, person_boxes):
        """
        Extract poses from detected person bounding boxes
        
        Args:
            frame: Current frame
            person_boxes: List of (x1, y1, x2, y2) bounding boxes
            
        Returns:
            list: Pose data for each person
        """
        poses = []
        
        for box in person_boxes:
            x1, y1, x2, y2 = box
            
            # Ensure box is within frame bounds
            h, w = frame.shape[:2]
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w, int(x2)), min(h, int(y2))
            
            if x2 <= x1 or y2 <= y1:
                poses.append(None)
                continue
            
            # Extract person region
            person_roi = frame[y1:y2, x1:x2]
            
            # Detect pose
            rgb_roi = cv2.cvtColor(person_roi, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb_roi)
            
            if results.pose_landmarks:
                pose_data = {
                    'landmarks': results.pose_landmarks,
                    'box': (x1, y1, x2, y2),
                    'orientation': self.calculate_orientation(results.pose_landmarks),
                    'panic_gestures': self.detect_panic_gestures(results.pose_landmarks),
                    'pose_type': self.classify_pose(results.pose_landmarks)
                }
                poses.append(pose_data)
            else:
                poses.append(None)
        
        return poses
    
    def calculate_orientation(self, landmarks):
        """
        Calculate body orientation angle
        
        Args:
            landmarks: MediaPipe pose landmarks
            
        Returns:
            float: Orientation angle in degrees (0-360)
        """
        # Get shoulder positions
        left_shoulder = landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        
        # Calculate angle
        dx = right_shoulder.x - left_shoulder.x
        dy = right_shoulder.y - left_shoulder.y
        angle = np.degrees(np.arctan2(dy, dx))
        
        # Normalize to 0-360
        angle = (angle + 360) % 360
        
        return float(angle)
    
    def detect_panic_gestures(self, landmarks):
        """
        Detect panic-related gestures
        
        Args:
            landmarks: MediaPipe pose landmarks
            
        Returns:
            list: Detected panic gestures
        """
        gestures = []
        
        # Extract key landmarks
        left_wrist = landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        left_shoulder = landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        nose = landmarks.landmark[self.mp_pose.PoseLandmark.NOSE]
        left_hip = landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_HIP]
        
        # 1. Arms raised (distress signal)
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        if left_wrist.y < shoulder_y - 0.1 or right_wrist.y < shoulder_y - 0.1:
            gestures.append('arms_raised')
        
        # 2. Crouching (trampling risk or fear)
        hip_y = (left_hip.y + right_hip.y) / 2
        if nose.y > hip_y - 0.15:  # Head close to hips
            gestures.append('crouching')
        
        # 3. Arms protecting head
        if (left_wrist.y < nose.y and right_wrist.y < nose.y and
            abs(left_wrist.x - nose.x) < 0.15 and abs(right_wrist.x - nose.x) < 0.15):
            gestures.append('protective_stance')
        
        return gestures
    
    def classify_pose(self, landmarks):
        """
        Classify overall pose type
        
        Args:
            landmarks: MediaPipe pose landmarks
            
        Returns:
            str: Pose classification
        """
        left_hip = landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_HIP]
        left_knee = landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_KNEE]
        right_knee = landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_KNEE]
        nose = landmarks.landmark[self.mp_pose.PoseLandmark.NOSE]
        
        hip_y = (left_hip.y + right_hip.y) / 2
        knee_y = (left_knee.y + right_knee.y) / 2
        
        # Running pose (legs bent, dynamic)
        leg_bend = abs(hip_y - knee_y)
        if leg_bend < 0.25:
            return 'running'
        
        # Standing
        if nose.y < hip_y - 0.3:
            return 'standing'
        
        # Crouching/sitting
        if nose.y > hip_y - 0.15:
            return 'crouching'
        
        return 'unknown'
    
    def get_orientation_randomness(self, poses):
        """
        Calculate orientation randomness (panic indicator)
        
        Args:
            poses: List of pose data
            
        Returns:
            float: Randomness score (0-1)
        """
        if not poses:
            return 0.0
        
        orientations = [p['orientation'] for p in poses if p is not None]
        
        if len(orientations) < 3:
            return 0.0
        
        # Calculate circular standard deviation
        angles_rad = np.radians(orientations)
        mean_sin = np.mean(np.sin(angles_rad))
        mean_cos = np.mean(np.cos(angles_rad))
        r = np.sqrt(mean_sin**2 + mean_cos**2)
        
        # Randomness: 1 - concentration
        randomness = 1 - r
        
        return float(randomness)
    
    def count_panic_gestures(self, poses):
        """
        Count total panic gestures detected
        
        Args:
            poses: List of pose data
            
        Returns:
            dict: Gesture counts
        """
        gesture_counts = {
            'arms_raised': 0,
            'crouching': 0,
            'protective_stance': 0,
            'total': 0
        }
        
        for pose in poses:
            if pose is not None and 'panic_gestures' in pose:
                for gesture in pose['panic_gestures']:
                    if gesture in gesture_counts:
                        gesture_counts[gesture] += 1
                        gesture_counts['total'] += 1
        
        return gesture_counts
    
    def release(self):
        """Release resources"""
        if hasattr(self, 'pose'):
            self.pose.close()
