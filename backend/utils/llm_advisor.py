from google import genai
from backend.config import Config

class LLMAdvisor:
    """Generate evacuation advice and architectural audits using Gemini 2.0"""
    
    def __init__(self):
        if Config.GEMINI_API_KEY:
            # Using the new google-genai SDK
            # Explicitly use v1 API version to avoid v1beta 404 issues
            self.client = genai.Client(api_key=Config.GEMINI_API_KEY, http_options={'api_version': 'v1'})
            self.model_id = 'gemini-1.5-flash'
            self.enabled = True
        else:
            self.enabled = False
            print("Warning: GEMINI_API_KEY not set. LLM advisor disabled.")
    
    def generate_evacuation_advice(self, risk_level, crowd_count, density_map, alerts):
        """Standard monitoring advice"""
        if not self.enabled:
            return self._get_fallback_advice(risk_level, crowd_count)
        
        try:
            prompt = self._create_monitoring_prompt(risk_level, crowd_count, alerts)
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return self._get_fallback_advice(risk_level, crowd_count)

    def run_safety_audit(self, dimensions, exits, cameras):
        """
        CrowdShield Planner: Run an architectural audit of a proposed layout.
        
        Args:
            dimensions: {width, height} in meters
            exits: List of {x, y, width}
            cameras: List of {x, y, type}
        """
        if not self.enabled:
            return "AI Planner is currently offline. Please set GEMINI_API_KEY."

        prompt = f"""You are a Crowd Safety Architect. Audit the following venue layout:
        
        VENUE DIMENSIONS: {dimensions['width']}m x {dimensions['height']}m (Total: {dimensions['width']*dimensions['height']} sqm)
        EXITS: {len(exits)} exits located at {[ (e['x'], e['y']) for e in exits ]}
        CAMERAS: {len(cameras)} cameras located at {[ (c['x'], c['y']) for c in cameras ]}

        Provide a structured Safety Audit:
        1. SAFE CAPACITY: Suggest max people for (a) Normal Flow and (b) High-Stress Event.
        2. EXIT ANALYSIS: Are exits placed optimally? Are more needed based on NFPA standards?
        3. MONITORING GAPS: Do the cameras cover all corners and exit routes?
        4. CRITICAL SUGGESTION: One high-impact change to improve safety.

        Keep it professional, bulleted, and under 200 words.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error analyzing layout: {str(e)}"

    def _create_monitoring_prompt(self, risk_level, crowd_count, alerts):
        alert_text = ", ".join([a['message'] for a in alerts]) if alerts else "None"
        return f"""Emergency AI Assistant context:
        - Risk Level: {risk_level}
        - People Count: {crowd_count}
        - Active Alerts: {alert_text}
        
        Provide 3-4 bullet points of immediate actionable evacuation or crowd-control advice."""

    def _get_fallback_advice(self, risk_level, crowd_count):
        if risk_level == 'HIGH':
            return "🚨 HIGH RISK: Clear exits immediately. Deploy all security personnel."
        return "System monitoring. No immediate critical actions required."

    def generate_micro_evacuation_plan(self, hotspot_location, safe_zones):
        # ... simplified for now
        return f"Redirect crowd from hotspot at {hotspot_location} to nearest safe zone."
