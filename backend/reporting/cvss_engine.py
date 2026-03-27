# Hybrid AI Engine
from backend.ai.cortex import CortexEngine

cortex = CortexEngine()

class CVSSCalculator:
    def __init__(self, success_count: int, body_content: str = "", target_url: str = "", vuln_type: str = ""):
        self.success_count = success_count
        self.body_content = body_content.lower()
        self.target_url = target_url
        self.vuln_type = vuln_type

    def calculate(self):
        # Base Metrics
        av = "N" # Network
        ac = "H" # High (Race Condition complexity)
        pr = "L" # Low (Usually requires basic auth)
        ui = "N" # None
        s = "U"  # Unchanged
        
        # Dynamic Impacts
        c = "N" # Confidentiality
        i = "N" # Integrity
        a = "N" # Availability

        # Logic for Integrity (Double Spend / Logic Bypass)
        if self.success_count >= 1:
            i = "H"
        
        # Logic for Confidentiality (Data Leak)
        sensitive_keywords = ["token", "key", "password", "secret", "admin"]
        if any(k in self.body_content for k in sensitive_keywords):
            c = "H"

        # Construct Vector String
        vector = f"CVSS:3.1/AV:{av}/AC:{ac}/PR:{pr}/UI:{ui}/S:{s}/C:{c}/I:{i}/A:{a}"
        
        # Calculate Logic (Simplified lookup or formula)
        # For Race Conditions (AC:H):
        # I:H, C:N -> ~5.3 - 7.5
        
        score = 0.0
        if i == "H" or c == "H":
            score = 7.5 # High
            if i == "H" and c == "H":
                score = 8.1 # High
        elif self.success_count > 0:
            score = 3.7 # Low (Single success, no race but maybe unintended access)
        else:
            score = 0.0 # None
            
        return score, vector

    async def calculate_hybrid(self):
        """Calculate CVSS with AI-powered contextual adjustment."""
        base_score, vector = self.calculate()
        if self.target_url and self.vuln_type:
            adjusted = await cortex.adjust_cvss_score(base_score, self.vuln_type, self.target_url)
            return adjusted, vector
        return base_score, vector
