import numpy as np
from backend.config import Config

class RiskAnalyzer:
    """Analyze crowd data and calculate risk levels"""
    
    def __init__(self):
        self.risk_history = []
        self.alert_active = False
        self.panic_initiators = []  # Track who started panic
        self.pressure_history = []
        
    def calculate_risk_level(self, crowd_count, frame_area, movement_data, iot_data=None, pressure_map=None):
        """
        Calculate overall risk level
        
        Args:
            crowd_count: Number of people detected
            frame_area: Total frame area (width * height)
            movement_data: Movement analysis results
            iot_data: IoT sensor data (optional)
            pressure_map: Pressure map (optional)
            
        Returns:
            dict: {
                'level': 'LOW' | 'MEDIUM' | 'HIGH',
                'score': float (0-1),
                'factors': dict of contributing factors,
                'alerts': list of alert messages,
                'pressure_map': pressure map if provided
            }
        """
        # Calculate density (people per unit area)
        density_score = self._calculate_density_score(crowd_count, frame_area)
        
        # Calculate movement risk
        movement_score = self._calculate_movement_score(movement_data)
        
        # Calculate IoT sensor risk (if available)
        iot_score = self._calculate_iot_score(iot_data) if iot_data else 0.0
        
        # Weighted combination
        weights = {
            'density': 0.5,
            'movement': 0.3,
            'iot': 0.2
        }
        
        overall_score = float(
            density_score * weights['density'] +
            movement_score * weights['movement'] +
            iot_score * weights['iot']
        )
        
        # Determine risk level
        if overall_score < Config.LOW_RISK_THRESHOLD:
            risk_level = 'LOW'
        elif overall_score < Config.MEDIUM_RISK_THRESHOLD:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'HIGH'
        
        # Generate alerts
        alerts = self._generate_alerts(risk_level, crowd_count, movement_data)
        
        # Store in history
        risk_result = {
            'level': risk_level,
            'score': overall_score,
            'factors': {
                'density': density_score,
                'movement': movement_score,
                'iot': iot_score
            },
            'alerts': alerts,
            'crowd_count': crowd_count
        }
        
        self.risk_history.append(risk_result)
        if len(self.risk_history) > 100:
            self.risk_history.pop(0)
        
        return risk_result
    
    def _calculate_density_score(self, count, area):
        """Calculate density-based risk score"""
        # Normalize by area (assuming 640x480 as reference)
        reference_area = 640 * 480
        normalized_count = count * (reference_area / area)
        
        # Map to 0-1 scale (assume 100 people in reference area is max)
        density_score = min(normalized_count / 100.0, 1.0)
        
        return density_score
    
    def _calculate_movement_score(self, movement_data):
        """Calculate movement-based risk score"""
        if movement_data is None:
            return 0.0
        
        score = 0.0
        
        # Movement magnitude contribution
        mag = movement_data.get('movement_magnitude', 0)
        score += min(mag / 10.0, 0.5)  # Max 0.5 contribution
        
        # Erratic movements contribution
        erratic = movement_data.get('erratic_movements', 0)
        score += min(erratic / 20.0, 0.3)  # Max 0.3 contribution
        
        # Panic indicators contribution
        panic_count = len(movement_data.get('panic_indicators', []))
        score += panic_count * 0.1  # 0.1 per indicator
        
        return min(score, 1.0)
    
    def _calculate_iot_score(self, iot_data):
        """Calculate IoT sensor-based risk score"""
        score = 0.0
        
        # Temperature contribution
        temp = iot_data.get('temperature', 25)
        if temp > 30:
            score += min((temp - 30) / 10.0, 0.3)
        
        # Noise level contribution
        noise = iot_data.get('noise_level', 50)
        if noise > 70:
            score += min((noise - 70) / 30.0, 0.4)
        
        # Humidity contribution (high humidity = discomfort)
        humidity = iot_data.get('humidity', 50)
        if humidity > 70:
            score += min((humidity - 70) / 30.0, 0.3)
        
        return min(score, 1.0)
    
    def _generate_alerts(self, risk_level, crowd_count, movement_data):
        """Generate alert messages based on risk factors"""
        alerts = []
        
        if risk_level == 'HIGH':
            alerts.append({
                'severity': 'HIGH',
                'message': 'CRITICAL: High risk of stampede detected!',
                'action': 'Immediate intervention required'
            })
        
        if risk_level == 'MEDIUM':
            alerts.append({
                'severity': 'MEDIUM',
                'message': 'WARNING: Elevated crowd stress levels',
                'action': 'Monitor closely and prepare evacuation routes'
            })
        
        # Specific alerts
        if crowd_count > 50:
            alerts.append({
                'severity': 'INFO',
                'message': f'High crowd density: {crowd_count} people detected',
                'action': 'Consider crowd control measures'
            })
        
        panic_indicators = movement_data.get('panic_indicators', []) if movement_data else []
        if 'convergent_escape_behavior' in panic_indicators:
            alerts.append({
                'severity': 'HIGH',
                'message': 'ALERT: Escape behavior detected in crowd',
                'action': 'Clear evacuation paths immediately'
            })
        
        if 'sudden_direction_changes' in panic_indicators:
            alerts.append({
                'severity': 'MEDIUM',
                'message': 'WARNING: Erratic crowd movements detected',
                'action': 'Investigate cause of disturbance'
            })
        
        return alerts
    
    def predict_contagion_spread(self, density_grid, initial_panic_locations):
        """
        Rule-based prediction of panic spread through crowd
        
        Args:
            density_grid: 2D array of crowd density
            initial_panic_locations: List of (x, y) grid coordinates with panic
            
        Returns:
            2D array showing predicted panic spread intensity
        """
        spread_map = np.zeros_like(density_grid, dtype=np.float32)
        
        # Set initial panic locations
        for x, y in initial_panic_locations:
            if 0 <= y < density_grid.shape[0] and 0 <= x < density_grid.shape[1]:
                spread_map[y, x] = 1.0
        
        # Simple contagion model: panic spreads to adjacent high-density areas
        for iteration in range(3):  # 3 iterations of spread
            new_spread = spread_map.copy()
            
            for y in range(density_grid.shape[0]):
                for x in range(density_grid.shape[1]):
                    if spread_map[y, x] > 0:
                        # Spread to neighbors based on density
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                ny, nx = y + dy, x + dx
                                if (0 <= ny < density_grid.shape[0] and 
                                    0 <= nx < density_grid.shape[1]):
                                    # Spread intensity based on density
                                    # Check for empty grid or zero max to prevent division errors
                                    if density_grid.size == 0 or density_grid.max() == 0:
                                        spread_intensity = 0
                                    else:
                                        spread_intensity = density_grid[ny, nx] / (density_grid.max() + 1e-6)
                                    new_spread[ny, nx] = max(
                                        new_spread[ny, nx],
                                        spread_map[y, x] * 0.7 * spread_intensity
                                    )
            
            spread_map = new_spread
        
        return spread_map
    
    def get_risk_trend(self):
        """Get risk trend over recent history"""
        if len(self.risk_history) < 5:
            return 'insufficient_data'
        
        recent_scores = [h['score'] for h in self.risk_history[-10:]]
        
        # Calculate trend
        first_half = np.mean(recent_scores[:len(recent_scores)//2])
        second_half = np.mean(recent_scores[len(recent_scores)//2:])
        
        if second_half > first_half * 1.3:
            return 'increasing'
        elif second_half < first_half * 0.7:
            return 'decreasing'
        else:
            return 'stable'
    
    def calculate_pressure_map(self, density_grid, speed_grid, direction_grid):
        """
        Calculate crowd pressure map
        Pressure = Density × Speed × Direction Conflict
        
        Args:
            density_grid: 2D array of crowd density
            speed_grid: 2D array of movement speeds
            direction_grid: 2D array of movement directions (flow field)
            
        Returns:
            2D array: Pressure map
        """
        if density_grid is None or speed_grid is None:
            return None
        
        # Calculate direction conflict
        direction_conflict = self._calculate_direction_conflict(direction_grid)
        
        # Pressure formula
        pressure_map = density_grid * speed_grid * direction_conflict
        
        # Normalize to 0-1
        if pressure_map.max() > 0:
            pressure_map = pressure_map / pressure_map.max()
        
        # Store in history
        self.pressure_history.append(pressure_map)
        if len(self.pressure_history) > 30:
            self.pressure_history.pop(0)
        
        return pressure_map
    
    def _calculate_direction_conflict(self, direction_grid):
        """
        Calculate directional conflict (opposing movements)
        
        Args:
            direction_grid: 2D flow field (dx, dy) at each point
            
        Returns:
            2D array: Conflict intensity (0-2, higher = more conflict)
        """
        if direction_grid is None or direction_grid.size == 0:
            return np.ones_like(direction_grid[:,:,0]) if len(direction_grid.shape) > 2 else np.ones((10, 10))
        
        h, w = direction_grid.shape[:2]
        conflict_map = np.ones((h, w), dtype=np.float32)
        
        # For each cell, compare with neighbors
        for y in range(1, h-1):
            for x in range(1, w-1):
                current_dir = direction_grid[y, x]
                
                # Get neighboring directions
                neighbors = [
                    direction_grid[y-1, x],  # up
                    direction_grid[y+1, x],  # down
                    direction_grid[y, x-1],  # left
                    direction_grid[y, x+1],  # right
                ]
                
                # Calculate angle differences
                conflicts = 0
                for neighbor in neighbors:
                    # Dot product to measure opposition
                    dot = np.dot(current_dir, neighbor)
                    # Negative dot = opposing directions
                    if dot < -0.5:  # More than 120 degrees apart
                        conflicts += 1
                
                # Conflict intensity (0-4 neighbors in conflict)
                conflict_map[y, x] = 1.0 + (conflicts / 4.0)  # Range 1.0-2.0
        
        return conflict_map
    
    def track_panic_initiators(self, person_positions, panic_gestures, timestamps):
        """
        Identify panic initiators (first people showing panic)
        
        Args:
            person_positions: List of (x, y) positions
            panic_gestures: List of panic gesture counts per person
            timestamps: Current timestamp
            
        Returns:
            list: IDs of panic initiators
        """
        # Find people with panic gestures
        current_panic = []
        for i, gestures in enumerate(panic_gestures):
            if gestures and gestures > 0:
                current_panic.append({
                    'id': i,
                    'position': person_positions[i],
                    'timestamp': timestamps,
                    'gesture_count': gestures
                })
        
        # Check if these are new panic cases (not in history)
        new_initiators = []
        existing_ids = [p['id'] for p in self.panic_initiators]
        
        for person in current_panic:
            if person['id'] not in existing_ids:
                new_initiators.append(person)
                self.panic_initiators.append(person)
        
        # Keep only recent initiators (last 60 seconds)
        self.panic_initiators = [
            p for p in self.panic_initiators 
            if timestamps - p['timestamp'] < 60
        ]
        
        return new_initiators
    
    def measure_panic_spread_rate(self):
        """
        Calculate panic propagation velocity
        
        Returns:
            dict: Spread rate metrics
        """
        if len(self.panic_initiators) < 2:
            return {'rate': 0.0, 'spreading': False}
        
        # Sort by timestamp
        sorted_panic = sorted(self.panic_initiators, key=lambda p: p['timestamp'])
        
        # Calculate spread over time
        time_range = sorted_panic[-1]['timestamp'] - sorted_panic[0]['timestamp']
        
        if time_range > 0:
            people_affected = len(sorted_panic)
            rate = people_affected / time_range  # people/second
            
            return {
                'rate': float(rate),
                'spreading': rate > 0.1,  # More than 1 person every 10 seconds
                'total_affected': people_affected,
                'time_span': float(time_range)
            }
        
        return {'rate': 0.0, 'spreading': False}

