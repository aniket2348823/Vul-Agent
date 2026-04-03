import json
import os
import asyncio
from typing import List, Dict, Any, Optional

GRAPH_FILE = "graph.json"
TMP_GRAPH_FILE = "graph.json.tmp"

class VulnNode:
    def __init__(self, type: str, endpoint: str, weight: int = 1):
        self.type = type
        self.endpoint = endpoint
        self.weight = weight

    def __eq__(self, other):
        if not isinstance(other, VulnNode):
            return False
        return self.type == other.type and self.endpoint == other.endpoint

    def __hash__(self):
        return hash((self.type, self.endpoint))

    def to_dict(self):
        return {"type": self.type, "endpoint": self.endpoint, "weight": self.weight}

    @classmethod
    def from_dict(cls, data):
        return cls(type=data["type"], endpoint=data["endpoint"], weight=data.get("weight", 1))

class Edge:
    def __init__(self, src: VulnNode, dst: VulnNode, weight: int = 1):
        self.src = src
        self.dst = dst
        self.weight = weight

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return False
        return self.src == other.src and self.dst == other.dst

    def __hash__(self):
        return hash((self.src, self.dst))

    def to_dict(self):
        return {
            "src": self.src.to_dict(),
            "dst": self.dst.to_dict(),
            "weight": self.weight
        }
        
    @classmethod
    def from_dict(cls, data):
        return cls(
            src=VulnNode.from_dict(data["src"]),
            dst=VulnNode.from_dict(data["dst"]),
            weight=data.get("weight", 1)
        )

class GraphEngine:
    """
    Self-Learning Intelligence Graph.
    Turns static API findings into predictive attack chains based on historical weights.
    """
    def __init__(self):
        self.nodes: set[VulnNode] = set()
        self.edges: set[Edge] = set()
        self._lock = asyncio.Lock()
        self.load_graph()

    def load_graph(self):
        if os.path.exists(GRAPH_FILE):
            try:
                with open(GRAPH_FILE, "r") as f:
                    data = json.load(f)
                    for n_data in data.get("nodes", []):
                        self._add_or_update_node(n_data["type"], n_data["endpoint"], n_data.get("weight", 1))
                    for e_data in data.get("edges", []):
                        src = VulnNode.from_dict(e_data["src"])
                        dst = VulnNode.from_dict(e_data["dst"])
                        self._add_or_update_edge(src, dst, e_data.get("weight", 1))
            except Exception as e:
                print(f"[GraphEngine] Failed to load intelligence graph: {e}")

    async def save_graph(self):
        """Persist graph state asynchronously with lock protection."""
        async with self._lock:
            # Auto-prune before saving
            self._prune(max_nodes=500, max_edges=2500)

            data = {
                "nodes": [n.to_dict() for n in self.nodes],
                "edges": [e.to_dict() for e in self.edges]
            }
            try:
                def _write():
                    with open(TMP_GRAPH_FILE, "w") as f:
                        json.dump(data, f, indent=4)
                    os.replace(TMP_GRAPH_FILE, GRAPH_FILE)
                
                await asyncio.get_event_loop().run_in_executor(None, _write)
            except Exception as e:
                print(f"[GraphEngine] Failed to persist intelligence graph: {e}")

    def _prune(self, max_nodes: int = 500, max_edges: int = 2500):
        """
        Weight-based pruning to prevent unbounded graph growth.
        Removes lowest-confidence nodes and their orphaned edges.
        """
        if len(self.nodes) > max_nodes:
            sorted_nodes = sorted(list(self.nodes), key=lambda x: x.weight, reverse=True)
            survivors = set(sorted_nodes[:max_nodes])
            pruned_count = len(self.nodes) - max_nodes
            self.nodes = survivors
            # Remove edges referencing pruned nodes
            self.edges = {e for e in self.edges if e.src in survivors and e.dst in survivors}
            print(f"[GraphEngine] 🌿 Pruned {pruned_count} low-confidence nodes. Graph: {len(self.nodes)} nodes, {len(self.edges)} edges.")
            
        if len(self.edges) > max_edges:
            sorted_edges = sorted(list(self.edges), key=lambda x: x.weight, reverse=True)
            pruned_count = len(self.edges) - max_edges
            self.edges = set(sorted_edges[:max_edges])
            print(f"[GraphEngine] 🌿 Pruned {pruned_count} low-weight edges. Edges remaining: {len(self.edges)}.")

    def _add_or_update_node(self, type: str, endpoint: str, weight: int = 1, source: str = "UNKNOWN") -> VulnNode:
        
        # Enforce Source Tracing (Master Prompt Requirement)
        # We classify origin context for strict generation rules
        if "delta" in type.lower() or "dom" in source.lower():
             verified_source = "PINCHTAB_DOM"
        elif "heuristic" not in source.lower():
             verified_source = "REAL_API_TRACE"
        else:
             verified_source = "UNVERIFIED_HEURISTIC" # Will be penalized
             
        dummy = VulnNode(type, endpoint)
        for n in self.nodes:
            if n == dummy:
                n.weight += weight
                # Add source trace to existing dict
                n.__dict__["verified_source"] = verified_source 
                return n
                
        new_node = VulnNode(type, endpoint, weight)
        new_node.__dict__["verified_source"] = verified_source
        self.nodes.add(new_node)
        return new_node

    def _add_or_update_edge(self, src: VulnNode, dst: VulnNode, weight: int = 1) -> Edge:
        # Ensure nodes exist
        real_src = self._add_or_update_node(src.type, src.endpoint, 0)
        real_dst = self._add_or_update_node(dst.type, dst.endpoint, 0)
        
        dummy_edge = Edge(real_src, real_dst)
        for e in self.edges:
            if e == dummy_edge:
                e.weight += weight
                return e
                
        new_edge = Edge(real_src, real_dst, weight)
        self.edges.add(new_edge)
        return new_edge

    async def learn_from_chain(self, chain: List[Dict[str, Any]]):
        """
        Extracts validated chains from Omega/Reporting and updates historical weights.
        chain: list of finding dicts ordered functionally.
        """
        if len(chain) < 2:
            return
            
        nodes_in_chain = []
        for finding in chain:
            payload = finding.get('payload', {})
            vt = str(payload.get('type', 'UNKNOWN')).upper()
            vu = str(payload.get('url', '')).split('?')[0].lower() # Strip params for graph grouping
            nodes_in_chain.append(VulnNode(vt, vu))

        async with self._lock:
            for i in range(len(nodes_in_chain) - 1):
                src = nodes_in_chain[i]
                dst = nodes_in_chain[i+1]
                self._add_or_update_edge(src, dst, weight=1)
            
        await self.save_graph()

    def predict_next(self, current_type: str, current_endpoint: str) -> List[Dict[str, Any]]:
        """
        Used by Sigma to prioritize modules based on high-weight historical paths.
        Returns a sorted list of most probable next steps.
        """
        current_endpoint = current_endpoint.split('?')[0].lower()
        dummy = VulnNode(current_type.upper(), current_endpoint)
        
        candidates = []
        total_weight = sum([e.weight for e in self.edges if e.src == dummy])
        
        for e in self.edges:
            if e.src == dummy:
                confidence = round((e.weight / total_weight) * 100, 2) if total_weight > 0 else 0
                candidates.append({
                    "suggestion": e.dst.type,
                    "target_path": e.dst.endpoint,
                    "weight": e.weight,
                    "confidence": confidence
                })
                
        return sorted(candidates, key=lambda x: x["weight"], reverse=True)

    # ─── PHASE 3 UPGRADE: Chain Discovery Engine ──────────────────────────

    CHAIN_RULES = {
        "SQL_INJECTION":       ["BROKEN_AUTH", "UNAUTHORIZED_ACCESS", "IDOR", "DATA_LEAK"],
        "COMMAND_INJECTION":   ["BROKEN_AUTH", "UNAUTHORIZED_ACCESS", "RCE"],
        "SSRF":                ["BROKEN_AUTH", "UNAUTHORIZED_ACCESS", "IDOR", "INTERNAL_ACCESS"],
        "IDOR":                ["UNAUTHORIZED_ACCESS", "BROKEN_AUTH", "LOGIC_ESCALATION", "DATA_LEAK"],
        "XSS":                 ["CSRF", "PROMPT_INJECTION", "SESSION_HIJACK"],
        "CROSS_SITE_SCRIPTING":["CSRF", "PROMPT_INJECTION", "SESSION_HIJACK"],
        "BROKEN_AUTH":         ["LOGIC_ESCALATION", "DATA_LEAK", "ADMIN_TAKEOVER"],
        "JWT_BYPASS":          ["BROKEN_AUTH", "UNAUTHORIZED_ACCESS", "ADMIN_TAKEOVER"],
        "PATH_TRAVERSAL":      ["DATA_LEAK", "RCE", "CONFIG_EXPOSURE"],
        "RACE_CONDITION":      ["LOGIC_ESCALATION", "FINANCIAL_MANIPULATION"],
    }

    def can_chain(self, src_type: str, dst_type: str) -> bool:
        """Determine if vulnerability type A can logically chain into type B."""
        src_upper = src_type.upper()
        dst_upper = dst_type.upper()
        allowed = self.CHAIN_RULES.get(src_upper, [])
        return dst_upper in allowed

    def find_chains(self, max_depth: int = 5) -> List[List[Dict[str, Any]]]:
        """
        DFS traversal to discover all multi-step attack paths in the graph.
        Returns sorted list of chains (longest/highest-weight first).
        """
        # Build adjacency list from edges
        adj: Dict[VulnNode, List[VulnNode]] = {}
        edge_weights: Dict[tuple, int] = {}
        for e in self.edges:
            adj.setdefault(e.src, []).append(e.dst)
            edge_weights[(e.src, e.dst)] = e.weight

        chains = []

        def dfs(node: VulnNode, path: List[VulnNode], visited: set):
            if len(path) >= max_depth:
                if len(path) > 1:
                    chains.append(path.copy())
                return
            
            neighbors = adj.get(node, [])
            has_valid_next = False
            for nxt in neighbors:
                if nxt not in visited and self.can_chain(node.type, nxt.type):
                    has_valid_next = True
                    visited.add(nxt)
                    path.append(nxt)
                    dfs(nxt, path, visited)
                    path.pop()
                    visited.discard(nxt)
            
            if not has_valid_next and len(path) > 1:
                chains.append(path.copy())

        for start_node in self.nodes:
            dfs(start_node, [start_node], {start_node})

        # Score & deduplicate
        seen = set()
        unique_chains = []
        for chain in chains:
            sig = "->".join(f"{n.type}@{n.endpoint}" for n in chain)
            if sig not in seen:
                seen.add(sig)
                # Calculate chain weight
                total_weight = sum(
                    edge_weights.get((chain[i], chain[i+1]), 1)
                    for i in range(len(chain) - 1)
                )
                unique_chains.append({
                    "chain": [n.to_dict() for n in chain],
                    "depth": len(chain),
                    "total_weight": total_weight,
                    "confidence": min(100, total_weight * 10 + len(chain) * 15),
                })

        return sorted(unique_chains, key=lambda x: (x["depth"], x["total_weight"]), reverse=True)

# Global Graph Singleton
graph_engine = GraphEngine()
