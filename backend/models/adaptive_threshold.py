import numpy as np
import pickle
import os
from collections import defaultdict

class AdaptiveThreshold:
    """Self-learning stress thresholds using Q-learning"""
    
    def __init__(self, model_path='backend/models/weights/adaptive_thresholds.pkl'):
        self.model_path = model_path
        
        # Q-learning parameters
        self.alpha = 0.1  # Learning rate
        self.gamma = 0.9  # Discount factor
        self.epsilon = 0.1  # Exploration rate
        
        # State space: discretized (density, movement, iot_score)
        # Action space: (increase_threshold, decrease_threshold, no_change)
        self.q_table = defaultdict(lambda: [0.0, 0.0, 0.0])
        
        # Current thresholds (will adapt over time)
        self.low_threshold = 0.3
        self.medium_threshold = 0.6
        
        # Context awareness
        self.context = {
            'location_type': 'unknown',  # indoor/outdoor/religious/stadium
            'event_type': 'unknown',  # concert/religious/sports/general
            'crowd_pattern': 'normal'
        }
        
        # History for learning
        self.episode_history = []
        self.false_alarm_count = 0
        self.correct_warning_count = 0
        
        # Load existing model if available
        self.load_model()
    
    def get_thresholds(self, context=None):
        """
        Get adaptive thresholds for current context
        
        Args:
            context: Optional context dict
            
        Returns:
            tuple: (low_threshold, medium_threshold)
        """
        if context:
            self.context.update(context)
        
        # Context-specific adjustments
        adjustments = self._get_context_adjustments()
        
        low = max(0.1, min(0.5, self.low_threshold + adjustments['low']))
        medium = max(0.4, min(0.8, self.medium_threshold + adjustments['medium']))
        
        return (low, medium)
    
    def _get_context_adjustments(self):
        """Get threshold adjustments based on context"""
        adjustments = {'low': 0.0, 'medium': 0.0}
        
        # Religious places: lower thresholds (more sensitive)
        if self.context.get('location_type') == 'religious':
            adjustments['low'] -= 0.05
            adjustments['medium'] -= 0.05
        
        # Outdoor: higher thresholds (more tolerance)
        if self.context.get('location_type') == 'outdoor':
            adjustments['low'] += 0.05
            adjustments['medium'] += 0.05
        
        # Concert/sports: higher thresholds (expected high energy)
        if self.context.get('event_type') in ['concert', 'sports']:
            adjustments['low'] += 0.1
            adjustments['medium'] += 0.1
        
        return adjustments
    
    def discretize_state(self, density_score, movement_score, iot_score):
        """
        Convert continuous state to discrete bins
        
        Returns:
            tuple: Discrete state representation
        """
        # Bin into 5 levels each (0-4)
        density_bin = min(4, int(density_score * 5))
        movement_bin = min(4, int(movement_score * 5))
        iot_bin = min(4, int(iot_score * 5))
        
        return (density_bin, movement_bin, iot_bin)
    
    def choose_action(self, state):
        """
        Choose action using epsilon-greedy policy
        
        Args:
            state: Discrete state tuple
            
        Returns:
            int: Action index (0=increase, 1=decrease, 2=no_change)
        """
        # Epsilon-greedy
        if np.random.random() < self.epsilon:
            return np.random.randint(0, 3)  # Explore
        else:
            return int(np.argmax(self.q_table[state]))  # Exploit
    
    def update(self, state, action, reward, next_state):
        """
        Update Q-table based on experience
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
        """
        current_q = self.q_table[state][action]
        max_next_q = max(self.q_table[next_state])
        
        # Q-learning update
        new_q = current_q + self.alpha * (reward + self.gamma * max_next_q - current_q)
        self.q_table[state][action] = new_q
    
    def learn_from_outcome(self, risk_assessment, incident_occurred, false_alarm):
        """
        Learn from incident outcome
        
        Args:
            risk_assessment: The risk assessment that was made
            incident_occurred: True if actual incident happened
            false_alarm: True if warning was given but no incident
        """
        # Extract state
        factors = risk_assessment.get('factors', {})
        state = self.discretize_state(
            factors.get('density', 0),
            factors.get('movement', 0),
            factors.get('iot', 0)
        )
        
        # Determine reward
        reward = 0
        if incident_occurred and risk_assessment['level'] == 'HIGH':
            # Correct high warning
            reward = 10
            self.correct_warning_count += 1
        elif not incident_occurred and risk_assessment['level'] == 'LOW':
            # Correct low assessment
            reward = 5
        elif false_alarm and risk_assessment['level'] == 'HIGH':
            # False alarm penalty
            reward = -15
            self.false_alarm_count += 1
        elif incident_occurred and risk_assessment['level'] != 'HIGH':
            # Missed incident penalty
            reward = -20
        
        # Choose action for threshold adjustment
        action = self.choose_action(state)
        
        # Apply action
        if action == 0:  # Increase threshold (less sensitive)
            self.low_threshold = min(0.5, self.low_threshold + 0.02)
            self.medium_threshold = min(0.8, self.medium_threshold + 0.02)
        elif action == 1:  # Decrease threshold (more sensitive)
            self.low_threshold = max(0.1, self.low_threshold - 0.02)
            self.medium_threshold = max(0.4, self.medium_threshold - 0.02)
        # action == 2: no change
        
        # Update Q-table
        # Next state (same for simplicity in this episodic learning)
        self.update(state, action, reward, state)
        
        # Save periodically
        if (self.correct_warning_count + self.false_alarm_count) % 10 == 0:
            self.save_model()
    
    def auto_calibrate(self, historical_data):
        """
        Auto-calibrate based on historical data
        
        Args:
            historical_data: List of {risk_score, incident_occurred}
        """
        if len(historical_data) < 10:
            return  # Need sufficient data
        
        # Find optimal thresholds that minimize false alarms
        # while maximizing incident detection
        
        scores = [d['risk_score'] for d in historical_data]
        incidents = [d['incident_occurred'] for d in historical_data]
        
        # Try different threshold combinations
        best_f1 = 0
        best_low = 0.3
        best_medium = 0.6
        
        for low in np.arange(0.1, 0.5, 0.05):
            for medium in np.arange(0.4, 0.8, 0.05):
                if medium <= low:
                    continue
                
                # Calculate F1 score for this threshold
                predictions = []
                for score in scores:
                    if score < low:
                        predictions.append('LOW')
                    elif score < medium:
                        predictions.append('MEDIUM')
                    else:
                        predictions.append('HIGH')
                
                # Count true positives, false positives, false negatives
                tp = sum(1 for p, i in zip(predictions, incidents) 
                        if p == 'HIGH' and i)
                fp = sum(1 for p, i in zip(predictions, incidents) 
                        if p == 'HIGH' and not i)
                fn = sum(1 for p, i in zip(predictions, incidents) 
                        if p != 'HIGH' and i)
                
                # Calculate F1
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                if f1 > best_f1:
                    best_f1 = f1
                    best_low = low
                    best_medium = medium
        
        # Update thresholds
        self.low_threshold = best_low
        self.medium_threshold = best_medium
        
        print(f"Auto-calibrated thresholds: LOW={best_low:.2f}, MEDIUM={best_medium:.2f}, F1={best_f1:.2f}")
    
    def save_model(self):
        """Save Q-table and thresholds"""
        model_data = {
            'q_table': dict(self.q_table),
            'low_threshold': self.low_threshold,
            'medium_threshold': self.medium_threshold,
            'correct_warning_count': self.correct_warning_count,
            'false_alarm_count': self.false_alarm_count,
            'context': self.context
        }
        
        # Create directory if needed
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self):
        """Load Q-table and thresholds"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.q_table = defaultdict(lambda: [0.0, 0.0, 0.0], model_data.get('q_table', {}))
                self.low_threshold = model_data.get('low_threshold', 0.3)
                self.medium_threshold = model_data.get('medium_threshold', 0.6)
                self.correct_warning_count = model_data.get('correct_warning_count', 0)
                self.false_alarm_count = model_data.get('false_alarm_count', 0)
                self.context = model_data.get('context', self.context)
                
                print(f"Loaded adaptive thresholds: LOW={self.low_threshold:.2f}, MEDIUM={self.medium_threshold:.2f}")
            except Exception as e:
                print(f"Error loading adaptive thresholds: {e}")
    
    def get_stats(self):
        """Get learning statistics"""
        total = self.correct_warning_count + self.false_alarm_count
        accuracy = self.correct_warning_count / total if total > 0 else 0
        
        return {
            'correct_warnings': self.correct_warning_count,
            'false_alarms': self.false_alarm_count,
            'accuracy': accuracy,
            'current_low_threshold': self.low_threshold,
            'current_medium_threshold': self.medium_threshold,
            'q_table_size': len(self.q_table)
        }
