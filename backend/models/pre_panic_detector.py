import numpy as np
from sklearn.cluster import DBSCAN

class PrePanicDetector:
    """Detect pre-panic signatures before visible panic starts"""
    
    def __init__(self):
        self.speed_history = []
        self.orientation_history = []
        self.max_history = 150  # 5 seconds at 30fps
        self.pre_panic_warnings = []
        
    def detect_signatures(self, movement_data, poses, crowd_count):
        """
        Detect pre-panic signatures
        
        Args:
            movement_data: Movement analysis from MovementTracker
            poses: Pose data from PoseDetector
            crowd_count: Number of people
            
        Returns:
            dict: Pre-panic detection results
        """
        signatures = {
            'detected': False,
            'indicators': [],
            'confidence': 0.0,
            'estimated_time_to_panic': None
        }
        
        # 1. Micro speed fluctuation analysis
        speed_fluctuation = self._analyze_speed_fluctuations(movement_data)
        if speed_fluctuation['high_variance']:
            signatures['indicators'].append('speed_fluctuation')
            signatures['confidence'] += 0.3
        
        # 2. Body orientation randomness
        if poses:
            orientation_random = self._analyze_orientation_randomness(poses)
            if orientation_random['high_randomness']:
                signatures['indicators'].append('orientation_randomness')
                signatures['confidence'] += 0.25
        
        # 3. Crowd hesitation patterns
        hesitation = self._detect_hesitation_patterns()
        if hesitation['detected']:
            signatures['indicators'].append('hesitation_pattern')
            signatures['confidence'] += 0.25
        
        # 4. Clustering behavior changes
        clustering = self._detect_clustering_changes(crowd_count)
        if clustering['abnormal']:
            signatures['indicators'].append('clustering_change')
            signatures['confidence'] += 0.2
        
        # Determine if pre-panic is detected
        if signatures['confidence'] >= 0.5:
            signatures['detected'] = True
            # Estimate time to panic based on trend
            signatures['estimated_time_to_panic'] = self._estimate_panic_onset()
        
        return signatures
    
    def _analyze_speed_fluctuations(self, movement_data):
        """
        Analyze micro speed fluctuations
        
        Returns:
            dict: Fluctuation analysis
        """
        if not movement_data or 'movement_magnitude' not in movement_data:
            return {'high_variance': False, 'variance': 0.0}
        
        # Add to history
        speed = movement_data['movement_magnitude']
        self.speed_history.append(speed)
        
        # Keep only recent data (5 seconds)
        if len(self.speed_history) > self.max_history:
            self.speed_history.pop(0)
        
        if len(self.speed_history) < 30:  # Need at least 1 second of data
            return {'high_variance': False, 'variance': 0.0}
        
        # Calculate short-term variance (last 2 seconds)
        recent_speeds = self.speed_history[-60:] if len(self.speed_history) >= 60 else self.speed_history
        variance = float(np.var(recent_speeds))
        
        # High variance indicates indecision/anxiety
        threshold = 2.0
        
        return {
            'high_variance': variance > threshold,
            'variance': variance
        }
    
    def _analyze_orientation_randomness(self, poses):
        """
        Analyze body orientation randomness
        
        Returns:
            dict: Orientation analysis
        """
        # Extract orientations from poses
        orientations = []
        for pose in poses:
            if pose is not None and 'orientation' in pose:
                orientations.append(pose['orientation'])
        
        if len(orientations) < 5:
            return {'high_randomness': False, 'randomness': 0.0}
        
        # Add to history
        self.orientation_history.append(orientations)
        if len(self.orientation_history) > 30:
            self.orientation_history.pop(0)
        
        # Calculate randomness over time
        if len(self.orientation_history) < 10:
            return {'high_randomness': False, 'randomness': 0.0}
        
        # Flatten all recent orientations
        all_orientations = []
        for frame_orientations in self.orientation_history:
            all_orientations.extend(frame_orientations)
        
        # Calculate circular standard deviation
        angles_rad = np.radians(all_orientations)
        mean_sin = np.mean(np.sin(angles_rad))
        mean_cos = np.mean(np.cos(angles_rad))
        r = np.sqrt(mean_sin**2 + mean_cos**2)
        randomness = float(1 - r)
        
        # High randomness indicates confusion/anxiety
        threshold = 0.6
        
        return {
            'high_randomness': randomness > threshold,
            'randomness': randomness
        }
    
    def _detect_hesitation_patterns(self):
        """
        Detect stop-go-stop hesitation behavior
        
        Returns:
            dict: Hesitation detection
        """
        if len(self.speed_history) < 60:
            return {'detected': False, 'pattern': None}
        
        # Look for stop-go-stop pattern in last 2 seconds
        recent_speeds = self.speed_history[-60:]
        
        # Threshold for "stopped" vs "moving"
        stop_threshold = 1.0
        
        # Convert to binary (stopped/moving)
        binary_movement = [1 if s > stop_threshold else 0 for s in recent_speeds]
        
        # Detect transitions
        transitions = 0
        for i in range(1, len(binary_movement)):
            if binary_movement[i] != binary_movement[i-1]:
                transitions += 1
        
        # High transition count indicates hesitation
        hesitation_detected = transitions > 6  # More than 3 stop-go cycles in 2s
        
        return {
            'detected': hesitation_detected,
            'pattern': 'stop_go_stop' if hesitation_detected else None,
            'transitions': transitions
        }
    
    def _detect_clustering_changes(self, crowd_count):
        """
        Detect abnormal clustering behavior
        
        Returns:
            dict: Clustering analysis
        """
        # Simple heuristic: sudden crowd count changes
        # More sophisticated version would use spatial clustering
        
        # Track crowd count over time
        if not hasattr(self, 'crowd_count_history'):
            self.crowd_count_history = []
        
        self.crowd_count_history.append(crowd_count)
        if len(self.crowd_count_history) > 30:
            self.crowd_count_history.pop(0)
        
        if len(self.crowd_count_history) < 10:
            return {'abnormal': False}
        
        # Check for sudden changes
        recent_variance = np.var(self.crowd_count_history[-10:])
        
        return {
            'abnormal': recent_variance > 20.0,  # High variance in count
            'variance': float(recent_variance)
        }
    
    def _estimate_panic_onset(self):
        """
        Estimate time to panic based on trend
        
        Returns:
            int: Estimated seconds until panic (20-30s range)
        """
        if len(self.speed_history) < 60:
            return 25  # Default estimate
        
        # Analyze acceleration of movement
        recent = self.speed_history[-60:]
        first_half = np.mean(recent[:30])
        second_half = np.mean(recent[30:])
        
        if second_half > first_half:
            acceleration_rate = (second_half - first_half) / first_half if first_half > 0 else 0
            
            # Higher acceleration = sooner panic
            if acceleration_rate > 0.5:
                return 20
            elif acceleration_rate > 0.3:
                return 25
            else:
                return 30
        
        return 25  # Default middle estimate
    
    def get_warning_summary(self, signatures):
        """
        Generate human-readable warning summary
        
        Args:
            signatures: Pre-panic signature dict
            
        Returns:
            str: Warning message
        """
        if not signatures['detected']:
            return None
        
        time_est = signatures['estimated_time_to_panic']
        confidence = int(signatures['confidence'] * 100)
        
        indicators_text = ', '.join([
            i.replace('_', ' ').title() 
            for i in signatures['indicators']
        ])
        
        warning = (
            f"⚠️ PRE-PANIC SIGNATURES DETECTED ({confidence}% confidence)\n"
            f"Estimated time to panic onset: {time_est} seconds\n"
            f"Indicators: {indicators_text}\n"
            f"Recommendation: Implement preventive measures immediately"
        )
        
        return warning
