import numpy as np
from sklearn.cluster import DBSCAN

class MicroEvacuation:
    """AI-guided targeted evacuation (not mass evacuation)"""
    
    def __init__(self):
        self.evacuation_groups = []
        self.evacuation_progress = {}
        
    def identify_target_groups(self, pressure_map, person_positions, min_group_size=5):
        """
        Identify high-pressure groups that need evacuation
        
        Args:
            pressure_map: 2D pressure map
            person_positions: List of (x, y) positions
            min_group_size: Minimum people in a group
            
        Returns:
            list: Target groups for evacuation
        """
        if not person_positions or len(person_positions) < min_group_size:
            return []
        
        # Convert positions to numpy array
        positions = np.array(person_positions)
        
        # Cluster people using DBSCAN
        clustering = DBSCAN(eps=50, min_samples=min_group_size)
        labels = clustering.fit_predict(positions)
        
        # Get pressure for each person
        h, w = pressure_map.shape if pressure_map is not None else (480, 640)
        person_pressures = []
        
        for x, y in person_positions:
            if pressure_map is not None and 0 <= int(y) < h and 0 <= int(x) < w:
                person_pressures.append(pressure_map[int(y), int(x)])
            else:
                person_pressures.append(0.0)
        
        # Analyze each cluster
        target_groups = []
        unique_labels = set(labels)
        
        for label in unique_labels:
            if label == -1:  # Noise points
                continue
            
            # Get members of this cluster
            mask = labels == label
            group_positions = positions[mask]
            group_pressures = [person_pressures[i] for i, m in enumerate(mask) if m]
            
            # Calculate group statistics
            group_center = np.mean(group_positions, axis=0)
            avg_pressure = np.mean(group_pressures)
            group_size = len(group_positions)
            
            # Identify high-pressure groups
            if avg_pressure > 0.5:  # High pressure threshold
                target_groups.append({
                    'group_id': int(label),
                    'center': tuple(group_center.astype(int)),
                    'size': group_size,
                    'avg_pressure': float(avg_pressure),
                    'positions': group_positions.tolist(),
                    'priority': 'HIGH' if avg_pressure > 0.7 else 'MEDIUM'
                })
        
        # Sort by pressure (highest first)
        target_groups.sort(key=lambda g: g['avg_pressure'], reverse=True)
        
        self.evacuation_groups = target_groups
        return target_groups
    
    def generate_redirection_plan(self, target_groups, safe_zones, exit_locations):
        """
        Generate group-specific redirection plans
        
        Args:
            target_groups: Output from identify_target_groups()
            safe_zones: List of safe zone dicts with 'center' and 'area'
            exit_locations: List of exit dicts with 'position' and 'capacity'
            
        Returns:
            list: Redirection plans for each group
        """
        plans = []
        
        for group in target_groups:
            group_center = group['center']
            
            # Find nearest safe zone
            nearest_safe = self._find_nearest_location(group_center, safe_zones, 'center')
            
            # Find nearest exit
            nearest_exit = self._find_nearest_location(group_center, exit_locations, 'position')
            
            # Determine redirection target (prefer safe zone if close, else exit)
            if nearest_safe:
                safe_dist = self._calculate_distance(group_center, nearest_safe['center'])
                exit_dist = self._calculate_distance(group_center, nearest_exit['position']) if nearest_exit else float('inf')
                
                if safe_dist < exit_dist * 0.7:  # Safe zone is much closer
                    target = nearest_safe['center']
                    target_type = 'safe_zone'
                else:
                    target = nearest_exit['position']
                    target_type = 'exit'
            elif nearest_exit:
                target = nearest_exit['position']
                target_type = 'exit'
            else:
                continue  # No valid target
            
            # Calculate direction vector
            dx = target[0] - group_center[0]
            dy = target[1] - group_center[1]
            dist = np.sqrt(dx**2 + dy**2)
            
            if dist > 0:
                direction = (dx / dist, dy / dist)
            else:
                direction = (0, 0)
            
            # Estimate evacuation time
            avg_walking_speed = 1.4  # m/s, roughly 2.8 pixels/frame at our scale
            estimated_time = int(dist / (avg_walking_speed * 30))  # frames to seconds
            
            plan = {
                'group_id': group['group_id'],
                'group_size': group['size'],
                'current_location': group_center,
                'target_location': target,
                'target_type': target_type,
                'direction': direction,
                'distance': float(dist),
                'estimated_time': estimated_time,
                'priority': group['priority'],
                'instructions': self._generate_instructions(group, target, target_type)
            }
            
            plans.append(plan)
            
            # Track progress
            self.evacuation_progress[group['group_id']] = {
                'started': True,
                'completed': False,
                'progress': 0.0
            }
        
        return plans
    
    def _find_nearest_location(self, point, locations, key):
        """Find nearest location to a point"""
        if not locations:
            return None
        
        min_dist = float('inf')
        nearest = None
        
        for loc in locations:
            loc_point = loc[key]
            dist = self._calculate_distance(point, loc_point)
            if dist < min_dist:
                min_dist = dist
                nearest = loc
        
        return nearest
    
    def _calculate_distance(self, p1, p2):
        """Calculate Euclidean distance"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def _generate_instructions(self, group, target, target_type):
        """Generate human-readable instructions"""
        direction_angle = np.degrees(np.arctan2(
            target[1] - group['center'][1],
            target[0] - group['center'][0]
        ))
        
        # Convert angle to compass direction
        if -22.5 <= direction_angle < 22.5:
            compass = "East"
        elif 22.5 <= direction_angle < 67.5:
            compass = "Southeast"
        elif 67.5 <= direction_angle < 112.5:
            compass = "South"
        elif 112.5 <= direction_angle < 157.5:
            compass = "Southwest"
        elif -157.5 <= direction_angle < -112.5:
            compass = "Northwest"
        elif -112.5 <= direction_angle < -67.5:
            compass = "North"
        elif -67.5 <= direction_angle < -22.5:
            compass = "Northeast"
        else:
            compass = "West"
        
        if target_type == 'safe_zone':
            return f"Redirect {group['size']} people {compass} to safe zone"
        else:
            return f"Evacuate {group['size']} people {compass} to nearest exit"
    
    def calculate_pressure_release(self, plans, current_pressure_map):
        """
        Estimate pressure reduction after micro-evacuation
        
        Args:
            plans: Redirection plans
            current_pressure_map: Current pressure map
            
        Returns:
            dict: Pressure release analysis
        """
        if current_pressure_map is None or not plans:
            return {'estimated_reduction': 0.0, 'time_to_safe': 0}
        
        # Estimate total people being redirected
        total_redirected = sum(p['group_size'] for p in plans)
        
        # Current average pressure
        current_avg_pressure = float(np.mean(current_pressure_map))
        
        # Estimate reduction (simplified model)
        # Assume each person redirected reduces pressure by 1%
        estimated_reduction = min(0.5, total_redirected * 0.01)
        
        # Estimated time to reach safe state
        max_time = max((p['estimated_time'] for p in plans), default=0)
        
        return {
            'estimated_reduction': estimated_reduction,
            'people_redirected': total_redirected,
            'time_to_safe': max_time,
            'current_avg_pressure': current_avg_pressure,
            'predicted_avg_pressure': max(0, current_avg_pressure - estimated_reduction)
        }
    
    def monitor_progress(self, current_positions, plans):
        """
        Monitor evacuation progress for each group
        
        Args:
            current_positions: Current person positions
            plans: Active redirection plans
            
        Returns:
            dict: Progress for each group
        """
        progress_report = {}
        
        for plan in plans:
            group_id = plan['group_id']
            target = plan['target_location']
            initial_dist = plan['distance']
            
            # Find current positions of group members (simplified)
            # In practice, you'd track individual IDs
            group_center = plan['current_location']
            
            # Calculate distance to target
            current_dist = self._calculate_distance(group_center, target)
            
            # Progress percentage
            progress = max(0, min(100, (1 - current_dist / initial_dist) * 100)) if initial_dist > 0 else 100
            
            completed = progress >= 95
            
            progress_report[group_id] = {
                'progress': float(progress),
                'completed': completed,
                'remaining_distance': float(current_dist)
            }
            
            # Update tracking
            if group_id in self.evacuation_progress:
                self.evacuation_progress[group_id]['progress'] = progress
                self.evacuation_progress[group_id]['completed'] = completed
        
        return progress_report
    
    def get_summary(self, plans, pressure_release):
        """
        Generate summary of micro-evacuation plan
        
        Returns:
            str: Summary text
        """
        if not plans:
            return "No micro-evacuation needed at this time."
        
        summary_lines = [
            f"🎯 MICRO-EVACUATION PLAN ({len(plans)} groups)",
            ""
        ]
        
        for i, plan in enumerate(plans, 1):
            summary_lines.append(
                f"{i}. Group {plan['group_id']} ({plan['group_size']} people) - "
                f"{plan['priority']} Priority"
            )
            summary_lines.append(f"   → {plan['instructions']}")
            summary_lines.append(f"   ⏱ ETA: {plan['estimated_time']}s")
            summary_lines.append("")
        
        summary_lines.append(
            f"📊 Expected Outcome:\n"
            f"   • People redirected: {pressure_release['people_redirected']}\n"
            f"   • Pressure reduction: {pressure_release['estimated_reduction']*100:.0f}%\n"
            f"   • Time to safety: {pressure_release['time_to_safe']}s"
        )
        
        return '\n'.join(summary_lines)
