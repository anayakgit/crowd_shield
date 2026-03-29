import google.generativeai as genai
from backend.config import Config

class LLMAdvisor:
    """Generate evacuation advice using LLM"""
    
    def __init__(self):
        # Configure Gemini API
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
            self.enabled = True
        else:
            self.enabled = False
            print("Warning: GEMINI_API_KEY not set. LLM advisor disabled.")
    
    def generate_evacuation_advice(self, risk_level, crowd_count, density_map, alerts):
        """
        Generate contextual evacuation advice
        
        Args:
            risk_level: Current risk level (LOW/MEDIUM/HIGH)
            crowd_count: Number of people
            density_map: 2D array of crowd density
            alerts: List of current alerts
            
        Returns:
            str: Evacuation advice
        """
        if not self.enabled:
            return self._get_fallback_advice(risk_level, crowd_count)
        
        try:
            # Analyze density map to find hotspots
            hotspots = self._analyze_density_map(density_map)
            
            # Create context prompt
            prompt = self._create_prompt(risk_level, crowd_count, hotspots, alerts)
            
            # Generate advice
            response = self.model.generate_content(prompt)
            
            return response.text
        
        except Exception as e:
            print(f"LLM generation error ({type(e).__name__}): {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_advice(risk_level, crowd_count)
    
    def _create_prompt(self, risk_level, crowd_count, hotspots, alerts):
        """Create prompt for LLM"""
        alert_descriptions = [a['message'] for a in alerts] if alerts else []
        
        prompt = f"""You are an emergency management AI assistant helping manage a crowd safety situation.

Current Situation:
- Risk Level: {risk_level}
- Crowd Size: {crowd_count} people
- High Density Areas: {len(hotspots)} hotspots detected
- Active Alerts: {', '.join(alert_descriptions) if alert_descriptions else 'None'}

Provide clear, actionable evacuation advice for authorities managing this situation. Include:
1. Immediate actions (2-3 steps)
2. Communication strategy
3. Crowd flow management
4. Safety precautions

Keep the advice concise (150 words max), professional, and action-oriented. Use bullet points.
"""
        
        return prompt
    
    def _analyze_density_map(self, density_map):
        """Find high-density hotspots in the map"""
        if density_map is None or density_map.size == 0:
            return []
        
        # Find areas with density above threshold
        threshold = density_map.mean() + density_map.std()
        hotspots = []
        
        import numpy as np
        high_density_mask = density_map > threshold
        
        # Count hotspots (simplified)
        labeled, num_features = self._label_regions(high_density_mask)
        
        for i in range(1, num_features + 1):
            region = (labeled == i)
            if region.sum() > 0:  # If region exists
                # Get center of mass
                y_indices, x_indices = np.where(region)
                center_y = int(y_indices.mean())
                center_x = int(x_indices.mean())
                hotspots.append({'x': center_x, 'y': center_y, 'size': region.sum()})
        
        return hotspots
    
    def _label_regions(self, binary_mask):
        """Simple region labeling (connected components)"""
        # Simplified version - just count separate regions
        import numpy as np
        
        # Use a simple flood-fill approach
        labeled = np.zeros_like(binary_mask, dtype=np.int32)
        current_label = 0
        
        for y in range(binary_mask.shape[0]):
            for x in range(binary_mask.shape[1]):
                if binary_mask[y, x] and labeled[y, x] == 0:
                    current_label += 1
                    self._flood_fill(binary_mask, labeled, x, y, current_label)
        
        return labeled, current_label
    
    def _flood_fill(self, binary_mask, labeled, x, y, label):
        """Flood fill for region labeling"""
        stack = [(x, y)]
        
        while stack:
            cx, cy = stack.pop()
            
            if (cy < 0 or cy >= binary_mask.shape[0] or 
                cx < 0 or cx >= binary_mask.shape[1]):
                continue
            
            if not binary_mask[cy, cx] or labeled[cy, cx] != 0:
                continue
            
            labeled[cy, cx] = label
            
            # Add neighbors
            stack.extend([
                (cx+1, cy), (cx-1, cy),
                (cx, cy+1), (cx, cy-1)
            ])
    
    def _get_fallback_advice(self, risk_level, crowd_count):
        """Fallback advice when LLM is unavailable"""
        if risk_level == 'HIGH':
            return """🚨 CRITICAL SITUATION - IMMEDIATE ACTION REQUIRED:

• Activate emergency protocols immediately
• Clear primary evacuation routes
• Deploy security personnel to manage crowd flow
• Use PA systems to provide clear, calm directions
• Open all available exits
• Prevent new entries to the area
• Call for emergency services backup

Communication: Use authoritative but calm tone. Avoid creating panic.

Safety: Monitor for injuries, provide first aid stations at exits."""

        elif risk_level == 'MEDIUM':
            return """⚠️ ELEVATED RISK - PREVENTIVE MEASURES:

• Increase monitoring of crowd movements
• Position staff at key choke points
• Prepare evacuation routes for quick activation
• Brief security team on emergency procedures
• Slow or pause entry of new people
• Increase lighting in dense areas

Communication: Inform crowd of temporary measures calmly.

Safety: Maintain clear pathways, remove obstacles."""

        else:  # LOW
            return """✓ NORMAL OPERATIONS - MAINTAIN VIGILANCE:

• Continue routine monitoring
• Ensure all exits remain accessible
• Keep security team alert
• Maintain good communication
• Monitor crowd flow patterns

Communication: Standard announcements as needed.

Safety: Regular checks of emergency equipment."""
    
    def generate_micro_evacuation_plan(self, hotspot_location, safe_zones):
        """Generate targeted advice for specific hotspot"""
        if not self.enabled:
            return f"Redirect crowd from hotspot at position {hotspot_location} to nearest safe zone."
        
        prompt = f"""Generate a micro-evacuation plan for a crowd hotspot.

Hotspot location: Grid position {hotspot_location}
Safe zones available: {len(safe_zones)} alternative areas

Provide:
1. Direction to guide crowd (e.g., "Northwest towards exit A")
2. Estimated time for clearance
3. Personnel deployment suggestion

Keep under 100 words."""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except:
            return self._get_fallback_advice('MEDIUM', 0)
