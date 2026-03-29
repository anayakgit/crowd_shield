import numpy as np
import cv2

class SilentGuidance:
    """Visual guidance system - alternative to panic-inducing alarms"""
    
    def __init__(self, frame_width=640, frame_height=480):
        self.width = frame_width
        self.height = frame_height
        
        # Define exit locations (will be configured based on venue)
        self.exit_locations = [
            {'name': 'Exit A', 'position': (50, frame_height // 2), 'capacity': 100},
            {'name': 'Exit B', 'position': (frame_width - 50, frame_height // 2), 'capacity': 100},
            {'name': 'Exit C', 'position': (frame_width // 2, 50), 'capacity': 80},
        ]
        
        # Safe zones (low pressure areas)
        self.safe_zones = []
    
    def generate_guidance(self, pressure_map, person_positions):
        """
        Generate visual guidance overlays
        
        Args:
            pressure_map: 2D pressure map
            person_positions: List of (x, y) positions
            
        Returns:
            dict: Guidance data including arrows and exit colors
        """
        # Identify safe zones (low pressure areas)
        self.safe_zones = self._identify_safe_zones(pressure_map)
        
        # Generate directional arrows for each person
        arrows = self._generate_arrows(person_positions, pressure_map)
        
        # Color-code exits based on pressure
        exit_colors = self._color_code_exits(pressure_map)
        
        return {
            'arrows': arrows,
            'exit_colors': exit_colors,
            'safe_zones': self.safe_zones
        }
    
    def _identify_safe_zones(self, pressure_map):
        """Identify low-pressure safe zones"""
        if pressure_map is None or pressure_map.size == 0:
            return []
        
        # Threshold for "safe" pressure
        threshold = np.percentile(pressure_map, 30)  # Bottom 30% is safe
        
        safe_mask = pressure_map < threshold
        
        # Find contours of safe zones
        safe_mask_uint8 = (safe_mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(safe_mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        safe_zones = []
        for contour in contours:
            if cv2.contourArea(contour) > 500:  # Minimum area
                M = cv2.moments(contour)
                if M['m00'] > 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                    safe_zones.append({
                        'center': (cx, cy),
                        'area': cv2.contourArea(contour),
                        'contour': contour
                    })
        
        return safe_zones
    
    def _generate_arrows(self, person_positions, pressure_map):
        """Generate directional guidance arrows"""
        arrows = []
        
        if not self.safe_zones or not person_positions:
            return arrows
        
        for px, py in person_positions:
            # Find nearest safe zone
            nearest_safe = None
            min_dist = float('inf')
            
            for zone in self.safe_zones:
                zx, zy = zone['center']
                dist = np.sqrt((px - zx)**2 + (py - zy)**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_safe = zone
            
            if nearest_safe:
                # Calculate arrow direction
                zx, zy = nearest_safe['center']
                dx = zx - px
                dy = zy - py
                
                # Normalize
                magnitude = np.sqrt(dx**2 + dy**2)
                if magnitude > 0:
                    dx /= magnitude
                    dy /= magnitude
                    
                    # Arrow endpoint (40 pixels in direction of safe zone)
                    end_x = int(px + dx * 40)
                    end_y = int(py + dy * 40)
                    
                    arrows.append({
                        'start': (int(px), int(py)),
                        'end': (end_x, end_y),
                        'safe_zone': nearest_safe['center']
                    })
        
        return arrows
    
    def _color_code_exits(self, pressure_map):
        """Assign colors to exits based on nearby pressure"""
        exit_colors = []
        
        if pressure_map is None or pressure_map.size == 0:
            # Default to green if no pressure data
            return [{'exit': exit, 'color': 'green', 'status': 'safe'} 
                   for exit in self.exit_locations]
        
        h, w = pressure_map.shape
        
        for exit_info in self.exit_locations:
            ex, ey = exit_info['position']
            
            # Get pressure in vicinity of exit (20x20 region)
            x1 = max(0, ex - 10)
            x2 = min(w, ex + 10)
            y1 = max(0, ey - 10)
            y2 = min(h, ey + 10)
            
            if x2 > x1 and y2 > y1:
                exit_pressure = np.mean(pressure_map[y1:y2, x1:x2])
                
                # Determine color based on pressure
                if exit_pressure < 0.3:
                    color = 'green'
                    status = 'safe'
                elif exit_pressure < 0.6:
                    color = 'yellow'
                    status = 'moderate'
                else:
                    color = 'red'
                    status = 'congested'
            else:
                color = 'green'
                status = 'safe'
            
            exit_colors.append({
                'exit': exit_info,
                'color': color,
                'status': status,
                'pressure': float(exit_pressure) if 'exit_pressure' in locals() else 0.0
            })
        
        return exit_colors
    
    def overlay_guidance(self, frame, guidance_data):
        """
        Overlay guidance on video frame
        
        Args:
            frame: Video frame
            guidance_data: Output from generate_guidance()
            
        Returns:
            numpy array: Frame with guidance overlay
        """
        overlay = frame.copy()
        
        # Draw safe zones (green transparent overlay)
        for zone in guidance_data.get('safe_zones', []):
            cv2.drawContours(overlay, [zone['contour']], -1, (0, 255, 0), -1)
        
        # Blend safe zones
        alpha = 0.2
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        
        # Draw directional arrows
        for arrow in guidance_data.get('arrows', []):
            cv2.arrowedLine(
                frame,
                arrow['start'],
                arrow['end'],
                (0, 255, 255),  # Cyan arrows
                3,
                tipLength=0.4
            )
        
        # Draw exits with color coding
        for exit_data in guidance_data.get('exit_colors', []):
            exit_info = exit_data['exit']
            color_name = exit_data['color']
            
            # Color mapping
            colors = {
                'green': (0, 255, 0),
                'yellow': (0, 255, 255),
                'red': (0, 0, 255)
            }
            color = colors.get(color_name, (255, 255, 255))
            
            ex, ey = exit_info['position']
            
            # Draw exit marker
            cv2.circle(frame, (ex, ey), 15, color, -1)
            cv2.circle(frame, (ex, ey), 17, (255, 255, 255), 2)
            
            # Draw exit label
            label = f"{exit_info['name']}"
            cv2.putText(
                frame,
                label,
                (ex - 30, ey - 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
            
            # Status text
            status = exit_data['status'].upper()
            cv2.putText(
                frame,
                status,
                (ex - 30, ey + 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1
            )
        
        return frame
    
    def get_evacuation_instructions(self, guidance_data):
        """
        Generate text evacuation instructions based on guidance
        
        Returns:
            str: Evacuation instructions
        """
        instructions = ["🚶 SILENT EVACUATION GUIDANCE:\n"]
        
        # Recommend best exits
        exit_colors = guidance_data.get('exit_colors', [])
        green_exits = [e for e in exit_colors if e['color'] == 'green']
        yellow_exits = [e for e in exit_colors if e['color'] == 'yellow']
        red_exits = [e for e in exit_colors if e['color'] == 'red']
        
        if green_exits:
            exits_text = ', '.join([e['exit']['name'] for e in green_exits])
            instructions.append(f"✅ USE: {exits_text} (SAFE - Low Pressure)")
        
        if yellow_exits:
            exits_text = ', '.join([e['exit']['name'] for e in yellow_exits])
            instructions.append(f"⚠️ CAUTION: {exits_text} (Moderate Pressure)")
        
        if red_exits:
            exits_text = ', '.join([e['exit']['name'] for e in red_exits])
            instructions.append(f"❌ AVOID: {exits_text} (High Pressure)")
        
        # Safe zones
        if guidance_data.get('safe_zones'):
            instructions.append(f"\n🟢 {len(guidance_data['safe_zones'])} Safe Zones Identified")
            instructions.append("Follow cyan arrows to nearest safe area")
        
        instructions.append("\n💡 Stay calm, follow visual guidance, avoid red zones")
        
        return '\n'.join(instructions)
