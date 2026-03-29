import cv2
import numpy as np

class MovementTracker:
    """Track micro-movements using optical flow and motion analysis"""
    
    def __init__(self):
        self.prev_gray = None
        self.movement_history = []
        self.max_history = 30  # Keep last 30 frames
        
    def detect_movements(self, frame, person_centers):
        """
        Detect micro-movements in the crowd
        
        Args:
            frame: Current frame
            person_centers: List of detected person centers
            
        Returns:
            dict: Movement analysis results
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        movement_data = {
            'optical_flow': None,
            'movement_magnitude': 0.0,
            'erratic_movements': 0,
            'panic_indicators': [],
            'person_vectors': []
        }
        
        if self.prev_gray is not None:
            # Calculate dense optical flow
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray, gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2,
                flags=0
            )
            
            # Calculate movement magnitude
            mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            movement_data['optical_flow'] = flow
            # Explicitly convert to native Python float for JSON serialization
            movement_data['movement_magnitude'] = float(np.mean(mag))
            
            # Detect erratic movements (high variance in direction)
            if len(person_centers) > 0:
                movement_vectors = self._get_movement_vectors(flow, person_centers)
                movement_data['erratic_movements'] = self._count_erratic_movements(movement_vectors)
                movement_data['panic_indicators'] = self._detect_panic_patterns(movement_vectors, mag)
                movement_data['person_vectors'] = movement_vectors
        
        self.prev_gray = gray
        self.movement_history.append(movement_data)
        
        # Keep only recent history
        if len(self.movement_history) > self.max_history:
            self.movement_history.pop(0)
        
        return movement_data
    
    def _get_movement_vectors(self, flow, centers):
        """Get movement vectors at person centers"""
        vectors = []
        h, w = flow.shape[:2]
        
        for cx, cy in centers:
            if 0 <= cy < h and 0 <= cx < w:
                vector = flow[cy, cx]
                vectors.append(vector)
        
        return np.array(vectors) if len(vectors) > 0 else np.array([])
    
    def _count_erratic_movements(self, vectors, threshold=2.0):
        """Count people with erratic movements"""
        if len(vectors) == 0:
            return 0
        
        # Calculate standard deviation of movement direction
        angles = np.arctan2(vectors[:, 1], vectors[:, 0])
        
        # Circular standard deviation
        mean_angle = np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))
        angular_diff = np.abs(angles - mean_angle)
        
        # Count movements that deviate significantly
        erratic_count = np.sum(angular_diff > threshold)
        
        return int(erratic_count)
    
    def _detect_panic_patterns(self, vectors, magnitude):
        """Detect panic patterns in movement"""
        indicators = []
        
        if len(vectors) == 0:
            return indicators
        
        # High velocity movements
        speeds = np.linalg.norm(vectors, axis=1)
        high_speed_ratio = np.sum(speeds > np.percentile(speeds, 75)) / len(speeds)
        
        if high_speed_ratio > 0.3:
            indicators.append('high_velocity_movements')
        
        # Sudden direction changes
        if len(self.movement_history) > 5:
            recent_mags = [h['movement_magnitude'] for h in self.movement_history[-5:]]
            if np.std(recent_mags) > 1.5:
                indicators.append('sudden_direction_changes')
        
        # Convergent movements (everyone moving to same direction - escape behavior)
        if len(vectors) > 5:
            angles = np.arctan2(vectors[:, 1], vectors[:, 0])
            mean_angle = np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))
            angular_concentration = np.sum(np.abs(angles - mean_angle) < 0.5) / len(angles)
            
            if angular_concentration > 0.7:
                indicators.append('convergent_escape_behavior')
        
        return indicators
    
    def draw_optical_flow(self, frame, flow, step=16):
        """Draw optical flow vectors on frame"""
        if flow is None:
            return frame
        
        h, w = frame.shape[:2]
        y, x = np.mgrid[step/2:h:step, step/2:w:step].reshape(2, -1).astype(int)
        fx, fy = flow[y, x].T
        
        # Create lines
        lines = np.vstack([x, y, x+fx, y+fy]).T.reshape(-1, 2, 2)
        lines = np.int32(lines + 0.5)
        
        # Draw flow vectors
        vis = frame.copy()
        for (x1, y1), (x2, y2) in lines:
            cv2.arrowedLine(vis, (x1, y1), (x2, y2), (0, 255, 0), 1, tipLength=0.3)
        
        return vis
    
    def get_movement_trends(self):
        """Get movement trends over time"""
        if len(self.movement_history) < 5:
            return {'trend': 'stable', 'risk_increasing': False}
        
        recent_mags = [h['movement_magnitude'] for h in self.movement_history[-10:]]
        
        # Check if movement is increasing
        if len(recent_mags) >= 5:
            first_half = np.mean(recent_mags[:len(recent_mags)//2])
            second_half = np.mean(recent_mags[len(recent_mags)//2:])
            
            if second_half > first_half * 1.5:
                return {'trend': 'increasing', 'risk_increasing': True}
            elif second_half < first_half * 0.7:
                return {'trend': 'decreasing', 'risk_increasing': False}
        
        return {'trend': 'stable', 'risk_increasing': False}
