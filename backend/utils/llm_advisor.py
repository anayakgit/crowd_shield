import google.generativeai as genai
from backend.config import Config

class LLMAdvisor:
    """Generate evacuation advice and architectural audits using Gemini 2.0"""
    
    def __init__(self):
        if Config.GEMINI_API_KEY:
            # Use the default API version which supports the latest models
            self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
            self.model_id = 'gemini-2.5-flash'
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

    def run_safety_audit(self, dimensions, exits, cameras, entries=None, zones=None, sources=None):
        """
        CrowdShield Planner: Run an architectural audit of a proposed layout.
        
        Args:
            dimensions: {width, height} in meters
            exits: List of {x, y, size, orientation}
            cameras: List of {x, y, type}
            entries: List of {x, y, size}
            zones: List of {x, y, w, h, name}
            sources: List of {x, y, name}  (crowd source/ingress points)
        """
        if not self.enabled:
            return "AI Planner is currently offline. Please set GEMINI_API_KEY."

        entries = entries or []
        zones = zones or []
        sources = sources or []

        total_area = dimensions['width'] * dimensions['height']
        
        exit_summary = ', '.join(
            [f"{e.get('name','Exit')} at ({round(e['x'],1)}m, {round(e['y'],1)}m) — {e.get('size', 3)}m wide"
             for e in exits]
        ) or 'None'
        
        entry_summary = ', '.join(
            [f"{e.get('name','Entry')} at ({round(e['x'],1)}m, {round(e['y'],1)}m) — {e.get('size', 3)}m wide"
             for e in entries]
        ) or 'None'

        camera_summary = ', '.join(
            [f"{c.get('name','Cam')} at ({round(c['x'],1)}m, {round(c['y'],1)}m)"
             for c in cameras]
        ) or 'None'
        
        zone_summary = ', '.join(
            [f"{z.get('name','Zone')} covers {round(abs(z.get('w',0)),1)}m x {round(abs(z.get('h',0)),1)}m at ({round(z['x'],1)}m, {round(z['y'],1)}m)"
             for z in zones]
        ) or 'None'

        source_summary = ', '.join(
            [f"{s.get('name','Source')} at ({round(s['x'],1)}m, {round(s['y'],1)}m)"
             for s in sources]
        ) or 'None'

        prompt = f"""You are a Crowd Safety Architect. Perform a full audit of the following venue layout:

VENUE DIMENSIONS: {dimensions['width']}m x {dimensions['height']}m (Total Area: {total_area} sqm)

EXITS ({len(exits)}):  {exit_summary}
ENTRY POINTS ({len(entries)}): {entry_summary}
AI CAMERAS ({len(cameras)}): {camera_summary}
MONITORING ZONES ({len(zones)}): {zone_summary}
CROWD SOURCES/INGRESS NODES ({len(sources)}): {source_summary}

Provide a structured Safety Audit with the following sections:

## 1. Safe Capacity
- Normal Flow (0.7 sqm/person) and High-Stress Event (1.0 sqm/person) maximums.

## 2. Exit & Entry Analysis
- Are exits/entries sufficient and correctly placed per NFPA 101 standards?
- Is the separation between exits adequate?

## 3. Monitoring Coverage
- Given the camera positions and zones, are there blind spots?
- Are crowd source/ingress points monitored?

## 4. Critical Suggestion
- One high-impact change that would most improve safety.

Keep it professional, use bullet points, and be specific using the coordinates provided."""
        
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
