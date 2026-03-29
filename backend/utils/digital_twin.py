import numpy as np
import cv2

class DigitalTwin:
    """Create a basic digital twin visualization of the crowd"""
    
    def __init__(self, frame_width=640, frame_height=480):
        self.width = frame_width
        self.height = frame_height
        self.person_positions = []
        self.person_velocities = []
        self.trail_history = []  # Movement trails
        self.max_trail_length = 30
        
    def update(self, person_centers, movement_vectors=None):
        """
        Update digital twin state
        
        Args:
            person_centers: List of (x, y) positions
            movement_vectors: Optional movement vectors for each person
        """
        self.person_positions = person_centers
        
        if movement_vectors is not None and len(movement_vectors) > 0:
            self.person_velocities = movement_vectors
        else:
            self.person_velocities = [(0, 0)] * len(person_centers)
        
        # Update movement trails
        self.trail_history.append(person_centers.copy() if person_centers else [])
        if len(self.trail_history) > self.max_trail_length:
            self.trail_history.pop(0)
    
    def render(self, show_trails=True, show_velocities=True):
        """
        Render the digital twin visualization
        
        Returns:
            numpy array: Rendered digital twin image
        """
        # Create blank canvas with dark background
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        canvas.fill(20)  # Dark gray background
        
        # Draw grid
        self._draw_grid(canvas)
        
        # Draw movement trails
        if show_trails and len(self.trail_history) > 1:
            self._draw_trails(canvas)
        
        # Draw people
        for i, (x, y) in enumerate(self.person_positions):
            # Person dot
            cv2.circle(canvas, (int(x), int(y)), 8, (0, 255, 255), -1)
            cv2.circle(canvas, (int(x), int(y)), 10, (255, 255, 255), 1)
            
            # Velocity vector
            if show_velocities and i < len(self.person_velocities):
                vx, vy = self.person_velocities[i]
                end_x = int(x + vx * 20)
                end_y = int(y + vy * 20)
                cv2.arrowedLine(canvas, (int(x), int(y)), (end_x, end_y),
                              (0, 255, 0), 2, tipLength=0.3)
        
        # Draw info overlay
        self._draw_info_overlay(canvas)
        
        return canvas
    
    def _draw_grid(self, canvas):
        """Draw a subtle grid on the canvas"""
        grid_spacing = 50
        grid_color = (40, 40, 40)
        
        # Vertical lines
        for x in range(0, self.width, grid_spacing):
            cv2.line(canvas, (x, 0), (x, self.height), grid_color, 1)
        
        # Horizontal lines
        for y in range(0, self.height, grid_spacing):
            cv2.line(canvas, (0, y), (self.width, y), grid_color, 1)
    
    def _draw_trails(self, canvas):
        """Draw movement trails for each person"""
        num_people = len(self.person_positions)
        
        # Draw trails with fading effect
        for trail_idx, positions in enumerate(self.trail_history):
            alpha = trail_idx / len(self.trail_history)  # Fade based on age
            color_intensity = int(150 * alpha)
            color = (color_intensity, color_intensity, color_intensity)
            
            for x, y in positions:
                cv2.circle(canvas, (int(x), int(y)), 2, color, -1)
    
    def _draw_info_overlay(self, canvas):
        """Draw information overlay"""
        info_text = f'People: {len(self.person_positions)}'
        
        # Semi-transparent overlay
        overlay = canvas.copy()
        cv2.rectangle(overlay, (5, 5), (200, 35), (50, 50, 50), -1)
        cv2.addWeighted(overlay, 0.7, canvas, 0.3, 0, canvas)
        
        # Text
        cv2.putText(canvas, info_text, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    def get_crowd_distribution_map(self):
        """Get 2D distribution map of crowd"""
        distribution = np.zeros((self.height, self.width), dtype=np.float32)
        
        # Create gaussian blobs at each person position
        for x, y in self.person_positions:
            if 0 <= x < self.width and 0 <= y < self.height:
                # Create a gaussian kernel
                size = 30
                sigma = 10
                kernel = self._gaussian_kernel(size, sigma)
                
                # Add to distribution map
                x_start = max(0, int(x) - size // 2)
                x_end = min(self.width, int(x) + size // 2)
                y_start = max(0, int(y) - size // 2)
                y_end = min(self.height, int(y) + size // 2)
                
                k_x_start = size // 2 - (int(x) - x_start)
                k_x_end = k_x_start + (x_end - x_start)
                k_y_start = size // 2 - (int(y) - y_start)
                k_y_end = k_y_start + (y_end - y_start)
                
                distribution[y_start:y_end, x_start:x_end] += kernel[k_y_start:k_y_end, k_x_start:k_x_end]
        
        return distribution
    
    def _gaussian_kernel(self, size, sigma):
        """Create a 2D gaussian kernel"""
        ax = np.arange(-size // 2 + 1., size // 2 + 1.)
        xx, yy = np.meshgrid(ax, ax)
        kernel = np.exp(-(xx**2 + yy**2) / (2. * sigma**2))
        return kernel / kernel.sum()
    
    def export_state(self):
        """Export current state as JSON-serializable dict"""
        # Use len() to check for empty arrays - works with both numpy arrays and lists
        velocities = []
        if len(self.person_velocities) > 0:
            velocities = [[float(vx), float(vy)] for vx, vy in self.person_velocities]
        
        return {
            'positions': [[int(x), int(y)] for x, y in self.person_positions],
            'velocities': velocities,
            'count': len(self.person_positions)
        }
    
    def predict_future_state(self, time_horizon=300, exits=None):
        """
        Predict crowd state in the future using social force model
        
        Args:
            time_horizon: Seconds ahead to predict (default 300 = 5 minutes)
            exits: List of exit positions
            
        Returns:
            dict: Predicted future state
        """
        if not self.person_positions:
            return {'positions': [], 'predicted_density': None}
        
        # Convert to numpy for simulation
        positions = np.array(self.person_positions, dtype=np.float32)
        velocities = np.array(self.person_velocities if self.person_velocities else 
                            [(0, 0)] * len(positions), dtype=np.float32)
        
        # Default exits if not provided
        if exits is None:
            exits = [
                (50, self.height // 2),
                (self.width - 50, self.height // 2)
            ]
        
        # Simulate forward (30 frames per second, time_horizon seconds)
        dt = 1.0 / 30.0  # Time step
        steps = min(time_horizon * 30, 9000)  # Limit to 9000 steps (5 min max)
        
        # Only simulate every 10th step for performance
        for step in range(0, steps, 10):
            positions, velocities = self._apply_social_force_model(
                positions, velocities, exits, dt * 10
            )
        
        # Convert back to list
        future_positions = positions.tolist()
        
        # Calculate predicted density map
        future_dist = self._calculate_density_from_positions(future_positions)
        
        return {
            'positions': [[int(x), int(y)] for x, y in future_positions],
            'predicted_density': future_dist,
            'time_horizon': time_horizon
        }
    
    def _apply_social_force_model(self, positions, velocities, exits, dt):
        """
        Apply social force model for one time step
        
        Args:
            positions: Nx2 array of positions
            velocities: Nx2 array of velocities
            exits: List of exit positions
            dt: Time step
            
        Returns:
            tuple: (new_positions, new_velocities)
        """
        n_people = len(positions)
        forces = np.zeros_like(positions)
        
        # Parameters
        desired_speed = 1.4  # m/s
        relaxation_time = 0.5
        
        # 1. Attractive force towards nearest exit
        for i, pos in enumerate(positions):
            # Find nearest exit
            min_dist = float('inf')
            nearest_exit = exits[0]
            
            for exit_pos in exits:
                dist = np.linalg.norm(pos - np.array(exit_pos))
                if dist < min_dist:
                    min_dist = dist
                    nearest_exit = exit_pos
            
            # Direction to exit
            direction = np.array(nearest_exit) - pos
            dist = np.linalg.norm(direction)
            
            if dist > 1:
                direction = direction / dist
                # Desired velocity
                desired_vel = desired_speed * direction
                # Force to achieve desired velocity
                forces[i] += (desired_vel - velocities[i]) / relaxation_time
        
        # 2. Repulsive force from other people
        for i in range(n_people):
            for j in range(i + 1, n_people):
                diff = positions[i] - positions[j]
                dist = np.linalg.norm(diff)
                
                if dist < 50:  # Interaction range
                    # Exponential repulsion
                    repulsion_strength = 2.0 * np.exp(-dist / 10.0)
                    direction = diff / (dist + 1e-6)
                    forces[i] += repulsion_strength * direction
                    forces[j] -= repulsion_strength * direction
        
        # 3. Repulsive force from walls
        for i, pos in enumerate(positions):
            # Left wall
            if pos[0] < 50:
                forces[i][0] += 5.0 * (50 - pos[0]) / 50.0
            # Right wall
            if pos[0] > self.width - 50:
                forces[i][0] -= 5.0 * (pos[0] - (self.width - 50)) / 50.0
            # Top wall
            if pos[1] < 50:
                forces[i][1] += 5.0 * (50 - pos[1]) / 50.0
            # Bottom wall
            if pos[1] > self.height - 50:
                forces[i][1] -= 5.0 * (pos[1] - (self.height - 50)) / 50.0
        
        # Update velocities and positions
        velocities += forces * dt
        
        # Limit maximum speed
        max_speed = 3.0
        speeds = np.linalg.norm(velocities, axis=1)
        for i in range(n_people):
            if speeds[i] > max_speed:
                velocities[i] = velocities[i] / speeds[i] * max_speed
        
        positions += velocities * dt
        
        # Keep within bounds
        positions[:, 0] = np.clip(positions[:, 0], 0, self.width)
        positions[:, 1] = np.clip(positions[:, 1], 0, self.height)
        
        return positions, velocities
    
    def simulate_scenario(self, action, time_steps=300):
        """
        Simulate "what-if" scenario
        
        Args:
            action: dict describing the action, e.g., {'type': 'close_exit', 'exit_id': 0}
            time_steps: Number of time steps to simulate
            
        Returns:
            dict: Simulation results
        """
        # Start with current state
        positions = np.array(self.person_positions, dtype=np.float32) if self.person_positions else np.array([])
        velocities = np.array(self.person_velocities if self.person_velocities else 
                            [(0, 0)] * len(positions), dtype=np.float32)
        
        if len(positions) == 0:
            return {'impact': 'No crowd to simulate', 'density_change': 0}
        
        # Default exits
        exits = [
            (50, self.height // 2),
            (self.width - 50, self.height // 2),
            (self.width // 2, 50)
        ]
        
        # Modify scenario based on action
        if action.get('type') == 'close_exit':
            exit_id = action.get('exit_id', 0)
            if 0 <= exit_id < len(exits):
                exits.pop(exit_id)
        elif action.get('type') == 'add_exit':
            new_exit = action.get('position', (self.width // 2, self.height - 50))
            exits.append(new_exit)
        
        # Simulate with modified scenario
        dt = 1.0 / 30.0
        density_samples = []
        
        for step in range(0, time_steps, 10):
            positions, velocities = self._apply_social_force_model(
                positions, velocities, exits, dt * 10
            )
            
            # Sample density every 30 steps (1 second)
            if step % 30 == 0:
                density = self._calculate_average_density(positions)
                density_samples.append(density)
        
        # Analyze impact
        initial_density = density_samples[0] if density_samples else 0
        final_density = density_samples[-1] if density_samples else 0
        density_change = final_density - initial_density
        
        # Determine impact
        if density_change > 0.2:
            impact = f"⚠️ Pressure increases significantly (+{density_change*100:.0f}%)"
        elif density_change < -0.2:
            impact = f"✅ Pressure decreases significantly ({density_change*100:.0f}%)"
        else:
            impact = f"➡️ Minimal impact ({density_change*100:+.0f}%)"
        
        return {
            'impact': impact,
            'density_change': float(density_change),
            'final_positions': positions.tolist(),
            'density_over_time': [float(d) for d in density_samples]
        }
    
    def _calculate_density_from_positions(self, positions):
        """Calculate density map from positions"""
        density = np.zeros((self.height, self.width), dtype=np.float32)
        
        for x, y in positions:
            if 0 <= int(x) < self.width and 0 <= int(y) < self.height:
                # Add gaussian blob
                size = 20
                sigma = 5
                kernel = self._gaussian_kernel(size, sigma)
                
                x_start = max(0, int(x) - size // 2)
                x_end = min(self.width, int(x) + size // 2)
                y_start = max(0, int(y) - size // 2)
                y_end = min(self.height, int(y) + size // 2)
                
                k_x_start = size // 2 - (int(x) - x_start)
                k_x_end = k_x_start + (x_end - x_start)
                k_y_start = size // 2 - (int(y) - y_start)
                k_y_end = k_y_start + (y_end - y_start)
                
                density[y_start:y_end, x_start:x_end] += kernel[k_y_start:k_y_end, k_x_start:k_x_end]
        
        return density
    
    def _calculate_average_density(self, positions):
        """Calculate average local density"""
        if len(positions) < 2:
            return 0.0
        
        # Use nearest neighbor distances
        distances = []
        for i, pos in enumerate(positions):
            min_dist = float('inf')
            for j, other_pos in enumerate(positions):
                if i != j:
                    dist = np.linalg.norm(pos - other_pos)
                    if dist < min_dist:
                        min_dist = dist
            distances.append(min_dist)
        
        # Average density (inverse of average spacing)
        avg_spacing = np.mean(distances)
        density = 1.0 / (avg_spacing + 1) if avg_spacing > 0 else 0
        
        return float(density)

