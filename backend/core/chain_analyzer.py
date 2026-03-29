from typing import List, Dict, Any

class ChainAnalyzer:
    """
    RESEARCH-GRADE ATTACK CHAIN CORRELATOR
    Transcribes atomic vulnerabilities into multi-step execution graphs mapping the lateral movement path of an attacker.
    """
    def __init__(self, findings: List[Dict[str, Any]]):
        self.raw_findings = findings
        self.nodes = []
        self._build_nodes()

    def _build_nodes(self):
        # We assume `findings` is a deduplicated list from reporting.py
        for f in self.raw_findings:
            payload = f.get('payload', {})
            vid = payload.get('id', str(hash(payload.get('url', ''))))
            vtype = str(payload.get('type', 'Unknown')).upper()
            vurl = str(payload.get('url', 'Target')).split('?')[0].lower()
            vimpact = payload.get('severity', 'LOW').upper()
            self.nodes.append({"id": vid, "type": vtype, "endpoint": vurl, "impact": vimpact, "raw": f})

    def can_chain(self, src: Dict[str, Any], dst: Dict[str, Any]) -> bool:
        """
        Determines if an offensive step logically proceeds into another.
        """
        stype = src['type']
        dtype = dst['type']
        
        # SQLi / Injection usually leads to Auth bypass or Data Leak
        if stype in ["SQL_INJECTION", "COMMAND_INJECTION", "SSRF"] and dtype in ["BROKEN_AUTH", "UNAUTHORIZED_ACCESS", "IDOR"]:
            return True
            
        # UI Flow: IDOR leading to Privilege Escalation
        if stype == "IDOR" and dtype in ["UNAUTHORIZED_ACCESS", "BROKEN_AUTH", "LOGIC_ESCALATION"]:
            return True
            
        # XSS leading to API Action
        if stype in ["XSS", "CROSS_SITE_SCRIPTING"] and dtype in ["CSRF", "PROMPT_INJECTION"]:
            return True
            
        # Target Proximity: Same Endpoint (Chain of bugs on one parameter)
        if src['endpoint'] == dst['endpoint'] and src['id'] != dst['id']:
            if stype != dtype:
                return True
                
        return False

    def build_chains(self) -> List[List[Dict[str, Any]]]:
        """
        Uses DFS to extract full attack paths.
        """
        for a in self.nodes:
            a["edges"] = []
            for b in self.nodes:
                if a["id"] != b["id"] and self.can_chain(a, b):
                    a["edges"].append(b)

        chains = []
        
        def dfs(node, path):
            path.append(node)
            # If leaf node or max depth 4 (to prevent infinite looping with circular logic)
            if not node.get('edges') or len(path) >= 4:
                if len(path) > 1: # Only track multi-step chains
                    chains.append(path.copy())
            else:
                for n in node['edges']:
                    if n not in path: # Avoid circular reference
                        dfs(n, path)
            path.pop()

        for n in self.nodes:
            dfs(n, [])
            
        # Optional: Dereplicate exact sub-chains
        unique_chains = []
        seen = set()
        for c in chains:
            sig = "->".join([x['id'] for x in c])
            if sig not in seen:
                seen.add(sig)
                unique_chains.append(c)

        return sorted(unique_chains, key=lambda x: len(x), reverse=True)

    def score_chain(self, chain: List[Dict[str, Any]]) -> int:
        score = 0
        impact_weights = {"CRITICAL": 30, "HIGH": 20, "MEDIUM": 10, "LOW": 5, "INFO": 1}
        
        for node in chain:
            score += impact_weights.get(node["impact"], 0)
            
        score += len(chain) * 15 # Depth multiplier bonuses
        return min(score, 100)
