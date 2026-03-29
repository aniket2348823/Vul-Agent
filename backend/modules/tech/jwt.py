from backend.core.base import BaseArsenalModule
from backend.core.protocol import JobPacket, ResultPacket, Vulnerability, TaskTarget
import time
# Hybrid AI Engine
from backend.ai.cortex import CortexEngine, get_cortex_engine

cortex = get_cortex_engine()

class JWTTokenCracker(BaseArsenalModule):
    def __init__(self):
        super().__init__()
        self.name = "JWT Token Cracker"

    async def generate_payloads(self, packet: JobPacket) -> list[TaskTarget]:
        return [packet.target]

    async def analyze_responses(self, interactions: list[tuple[TaskTarget, str]], packet: JobPacket) -> list[Vulnerability]:
        vulnerabilities = []
        
        for target, text in interactions:
            if "token=" in target.url:
                vulnerabilities.append(Vulnerability(
                     name="Weak JWT Implementation",
                     severity="HIGH",
                     description="JWT found in URL parameters.",
                     evidence=f"Token exposed in URL: {target.url}",
                     remediation="Place JWTs in Authorization header or HttpOnly cookies."
                ))
            
            token = ""
            if "token=" in target.url:
                token = target.url.split("token=")[-1].split("&")[0]
                
            jwt_analysis = await cortex.analyze_jwt_weakness(token=token, url=target.url)
            
            if jwt_analysis and jwt_analysis.get("weaknesses"):
                for weakness in jwt_analysis["weaknesses"]:
                    vulnerabilities.append(Vulnerability(
                        name=f"JWT Weakness: {weakness.replace('_', ' ').title()}",
                        severity="HIGH" if jwt_analysis.get("risk_score", 0) > 60 else "MEDIUM",
                        description=f"AI detected JWT weakness: {weakness}. Risk: {jwt_analysis.get('risk_score', 0)}",
                        evidence=f"Weaknesses: {jwt_analysis['weaknesses']}",
                        remediation=jwt_analysis.get("recommendations", ["Implement RS256 JWT validation."])[0] if jwt_analysis.get("recommendations") else "Implement RS256 JWT validation."
                    ))

        return vulnerabilities
