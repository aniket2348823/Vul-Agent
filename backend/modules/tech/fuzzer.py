from backend.core.base import BaseArsenalModule
from backend.core.protocol import JobPacket, Vulnerability, TaskTarget
from backend.ai.cortex import CortexEngine, get_cortex_engine

class APIFuzzer(BaseArsenalModule):
    def __init__(self):
        super().__init__()
        self.name = "API Fuzzer"
        # CORTEX AI for intelligent vector generation
        try:
            self.ai = get_cortex_engine()
        except Exception:self.ai = None

    async def generate_payloads(self, packet: JobPacket) -> list[TaskTarget]:
        targets = []
        fuzz_vectors = [
            "<script>alert('Antigravity')</script>", # XSS
            "A" * 10000, # Buffer Overflow attempt
            "%00",       # Null Byte
            "{{7*7}}",   # SSTI
            "../" * 10   # Path Traversal
        ]
        
        if self.ai and self.ai.enabled:
            try:
                ai_vectors = await self.ai.generate_fuzz_vectors(
                    target_url=packet.target.url,
                    content_type=packet.config.params.get("content_type", "") if hasattr(packet.config, 'params') else "",
                    tech_stack=packet.config.params.get("tech_stack", "") if hasattr(packet.config, 'params') else ""
                )
                if ai_vectors:
                    fuzz_vectors.extend(ai_vectors)
            except Exception:pass
                
        for vector in fuzz_vectors:
            fuzzed_url = f"{packet.target.url}?fuzz={vector}"
            targets.append(TaskTarget(
                url=fuzzed_url,
                method="GET",
                headers=packet.target.headers,
                payload=packet.target.payload
            ))
        return targets

    async def analyze_responses(self, interactions: list[tuple[TaskTarget, str]], packet: JobPacket) -> list[Vulnerability]:
        vulnerabilities = []
        for target, text in interactions:
            if not text or not isinstance(text, str): continue
            
            vector = ""
            if "?fuzz=" in target.url:
                vector = target.url.split("?fuzz=")[1]
                
            if vector and vector in text and "<script>" in vector:
                vulnerabilities.append(Vulnerability(
                    name="Cross-Site Scripting (XSS)",
                    severity="HIGH",
                    description="Reflection of unsterilized input detected in page content.",
                    evidence=f"Payload: {vector} reflected in response.",
                    remediation="Sanitize all user inputs and use Content Security Policy (CSP)."
                ))
                
            if "root:" in text or "boot.ini" in text:
                 vulnerabilities.append(Vulnerability(
                    name="Path Traversal",
                    severity="CRITICAL",
                    description="Access to sensitive system files detected.",
                    evidence="Leakage of 'root:' or OS identifiers in response.",
                    remediation="Restrict file access and validate input paths."
                ))
        return vulnerabilities
