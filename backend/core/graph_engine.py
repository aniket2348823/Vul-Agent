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

    def save_graph(self):
        data = {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges]
        }
        try:
            with open(TMP_GRAPH_FILE, "w") as f:
                json.dump(data, f, indent=4)
            os.replace(TMP_GRAPH_FILE, GRAPH_FILE)
        except Exception as e:
            print(f"[GraphEngine] Failed to persist intelligence graph: {e}")

    def _add_or_update_node(self, type: str, endpoint: str, weight: int = 1) -> VulnNode:
        dummy = VulnNode(type, endpoint)
        for n in self.nodes:
            if n == dummy:
                n.weight += weight
                return n
        new_node = VulnNode(type, endpoint, weight)
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

    def learn_from_chain(self, chain: List[Dict[str, Any]]):
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

        for i in range(len(nodes_in_chain) - 1):
            src = nodes_in_chain[i]
            dst = nodes_in_chain[i+1]
            self._add_or_update_edge(src, dst, weight=1)
            
        self.save_graph()

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

# Global Graph Singleton
graph_engine = GraphEngine()
