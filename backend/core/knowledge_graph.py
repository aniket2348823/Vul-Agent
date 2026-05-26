from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional, Dict, List


class NodeKind(str, Enum):
    TARGET = "target"
    DOMAIN = "domain"
    HOST = "host"
    SERVICE = "service"
    URL = "url"
    ENDPOINT = "endpoint"
    PARAMETER = "parameter"
    AUTH_SCHEME = "auth_scheme"
    TOKEN = "token"
    COOKIE = "cookie"
    SESSION = "session"
    CREDENTIAL = "credential"
    SECRET = "secret"
    VULNERABILITY = "vulnerability"
    CVE = "cve"
    WEAKNESS = "weakness"
    FINDING = "finding"
    EVIDENCE = "evidence"
    OBJECTIVE = "objective"
    ATTACK_PATH = "attack_path"
    TECHNIQUE = "technique"
    # Browser-specific node types
    BROWSER_ENDPOINT = "browser_endpoint"
    JAVASCRIPT_ROUTE = "javascript_route"
    WEBSOCKET_CONNECTION = "websocket_connection"


class EdgeKind(str, Enum):
    RESOLVES_TO = "resolves_to"
    EXPOSES = "exposes"
    CONTAINS_ENDPOINT = "contains_endpoint"
    ACCEPTS_PARAMETER = "accepts_parameter"
    AUTHENTICATED_BY = "authenticated_by"
    HAS_SESSION = "has_session"
    LEAKS_SECRET = "leaks_secret"
    HAS_VULN = "has_vuln"
    VALIDATES = "validates"
    EXPLOITS = "exploits"
    LEADS_TO = "leads_to"
    PIVOTS_TO = "pivots_to"
    ESCALATES_TO = "escalates_to"
    REACHES = "reaches"
    SUPPORTS = "supports"
    # Browser-specific edge types
    HTTP_EQUIVALENT = "http_equivalent"
    DISCOVERED_BY_BROWSER = "discovered_by_browser"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class KGNode:
    kind: NodeKind
    label: str
    props: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = stable_id(self.kind.value, self.label)


@dataclass
class KGEdge:
    src_id: str
    dst_id: str
    kind: EdgeKind
    weight: float = 1.0
    props: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = stable_id(self.src_id, self.kind.value, self.dst_id)


def stable_id(*parts: str) -> str:
    raw = "|".join(part.lower().strip() for part in parts)
    return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, KGNode] = {}
        self.edges: dict[str, KGEdge] = {}

    def upsert_node(self, node: KGNode) -> KGNode:
        existing = self.nodes.get(node.id)
        if existing:
            existing.props.update(node.props)
            return existing
        self.nodes[node.id] = node
        return node

    def upsert_edge(self, edge: KGEdge) -> KGEdge:
        existing = self.edges.get(edge.id)
        if existing:
            existing.weight = max(existing.weight, edge.weight)
            existing.props.update(edge.props)
            return existing
        self.edges[edge.id] = edge
        return edge

    def link(self, src: KGNode, dst: KGNode, kind: EdgeKind, *, weight: float = 1.0, props: dict[str, Any] | None = None) -> KGEdge:
        src = self.upsert_node(src)
        dst = self.upsert_node(dst)
        return self.upsert_edge(KGEdge(src.id, dst.id, kind, weight, props or {}))

    def by_kind(self, kind: NodeKind) -> list[KGNode]:
        return [node for node in self.nodes.values() if node.kind == kind]

    def neighbors(self, node_id: str, *, direction: str = "out", edge_kind: EdgeKind | None = None) -> list[KGNode]:
        found: list[KGNode] = []
        for edge in self.edges.values():
            if edge_kind and edge.kind != edge_kind:
                continue
            if direction in {"out", "both"} and edge.src_id == node_id and edge.dst_id in self.nodes:
                found.append(self.nodes[edge.dst_id])
            if direction in {"in", "both"} and edge.dst_id == node_id and edge.src_id in self.nodes:
                found.append(self.nodes[edge.src_id])
        return found

    def ingest_finding(self, finding: dict[str, Any], *, scan_id: str = "GLOBAL") -> KGNode:
        endpoint = str(finding.get("endpoint") or finding.get("url") or finding.get("affected_target") or "unknown")
        vuln_type = str(finding.get("vuln_type") or finding.get("type") or finding.get("title") or "vulnerability")
        severity = str(finding.get("severity") or "info").lower()
        endpoint_node = KGNode(NodeKind.ENDPOINT, endpoint, {"scan_id": scan_id})
        vuln_node = KGNode(NodeKind.VULNERABILITY, vuln_type, {"scan_id": scan_id, "severity": severity})
        finding_node = KGNode(NodeKind.FINDING, str(finding.get("id") or stable_id(scan_id, endpoint, vuln_type)), {"scan_id": scan_id, **finding})
        self.link(endpoint_node, vuln_node, EdgeKind.HAS_VULN, weight=_severity_weight(severity))
        self.link(vuln_node, finding_node, EdgeKind.VALIDATES, weight=_severity_weight(severity))
        return finding_node

    def ingest_http_record(self, record: Any, *, scan_id: str = "GLOBAL") -> None:
        url = getattr(record, "url", "") or record.get("url", "")
        status = getattr(record, "status", 0) if not isinstance(record, dict) else record.get("status", 0)
        method = getattr(record, "method", "") if not isinstance(record, dict) else record.get("method", "")
        endpoint = KGNode(NodeKind.ENDPOINT, str(url), {"scan_id": scan_id, "method": method, "status": status})
        self.upsert_node(endpoint)
        if status in {401, 403}:
            self.link(endpoint, KGNode(NodeKind.AUTH_SCHEME, "auth_required", {"scan_id": scan_id}), EdgeKind.AUTHENTICATED_BY)

    def plan_attack_paths(self, *, max_depth: int = 5) -> list[list[KGNode]]:
        paths: list[list[KGNode]] = []
        starts = [node for node in self.nodes.values() if node.kind in {NodeKind.VULNERABILITY, NodeKind.FINDING}]
        adjacency: dict[str, list[str]] = {}
        for edge in self.edges.values():
            if edge.kind in {EdgeKind.LEADS_TO, EdgeKind.PIVOTS_TO, EdgeKind.ESCALATES_TO, EdgeKind.EXPLOITS, EdgeKind.HAS_VULN}:
                adjacency.setdefault(edge.src_id, []).append(edge.dst_id)

        def walk(node_id: str, path: list[str]) -> None:
            if len(path) >= max_depth or node_id not in adjacency:
                if len(path) > 1:
                    paths.append([self.nodes[item] for item in path if item in self.nodes])
                return
            for nxt in adjacency.get(node_id, []):
                if nxt not in path:
                    walk(nxt, [*path, nxt])

        for start in starts:
            walk(start.id, [start.id])
        return sorted(paths, key=len, reverse=True)

    def bulk_upsert(self, nodes: Iterable[KGNode], edges: Iterable[KGEdge]) -> None:
        for node in nodes:
            self.upsert_node(node)
        for edge in edges:
            self.upsert_edge(edge)

    def stats(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for node in self.nodes.values():
            counts[node.kind.value] = counts.get(node.kind.value, 0) + 1
        return {"nodes": len(self.nodes), "edges": len(self.edges), "by_kind": counts}


def _severity_weight(severity: str) -> float:
    return {
        "critical": 10.0,
        "high": 7.5,
        "medium": 5.0,
        "low": 2.5,
        "informational": 1.0,
        "info": 1.0,
    }.get(severity.lower(), 1.0)


knowledge_graph = KnowledgeGraph()


# ============================================================================
# BROWSER KNOWLEDGE GRAPH EXTENSION
# ============================================================================

class BrowserKnowledgeGraphExtension:
    """Extension for browser discovery and HTTP-browser linking"""
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.graph = knowledge_graph
    
    def add_browser_discovery(
        self,
        discovery_data: Dict[str, Any],
        scan_id: str = "GLOBAL"
    ) -> KGNode:
        """
        Add browser discovery to knowledge graph with source tagging.
        Returns the created discovery node.
        """
        discovery_type = discovery_data.get("type", "browser_endpoint")
        url = discovery_data.get("url", "")
        
        # Create appropriate node type
        if discovery_type == "javascript_route":
            node = KGNode(
                NodeKind.JAVASCRIPT_ROUTE,
                url,
                {
                    "scan_id": scan_id,
                    "source": "browser_recon",
                    "framework": discovery_data.get("framework"),
                    "route_pattern": discovery_data.get("route_pattern"),
                    **discovery_data
                }
            )
        elif discovery_type == "websocket":
            node = KGNode(
                NodeKind.WEBSOCKET_CONNECTION,
                url,
                {
                    "scan_id": scan_id,
                    "source": "browser_recon",
                    "protocol": discovery_data.get("protocol", "ws"),
                    **discovery_data
                }
            )
        else:
            node = KGNode(
                NodeKind.BROWSER_ENDPOINT,
                url,
                {
                    "scan_id": scan_id,
                    "source": "browser_recon",
                    **discovery_data
                }
            )
        
        # Add to graph
        self.graph.upsert_node(node)
        
        # Link to HTTP equivalent if exists
        http_equivalent = self._find_http_equivalent(url)
        if http_equivalent:
            self.link_http_browser_endpoints(http_equivalent, node)
        
        return node
    
    def _find_http_equivalent(self, browser_url: str) -> Optional[KGNode]:
        """Find HTTP endpoint that matches browser URL."""
        # Normalize URL
        normalized = browser_url.split("?")[0].split("#")[0]
        
        # Search for matching HTTP endpoint
        for node in self.graph.nodes.values():
            if node.kind == NodeKind.ENDPOINT:
                node_url = node.label.split("?")[0].split("#")[0]
                if node_url == normalized:
                    return node
        
        return None
    
    def link_http_browser_endpoints(
        self,
        http_node: KGNode,
        browser_node: KGNode
    ) -> KGEdge:
        """
        Create HTTP_EQUIVALENT relationship between HTTP and browser endpoints.
        Merges metadata and deduplicates discoveries.
        """
        # Merge metadata
        merged_props = {
            **http_node.props,
            "browser_discovered": True,
            "browser_url": browser_node.label,
            "discovery_sources": ["http", "browser"]
        }
        
        # Update HTTP node with merged metadata
        http_node.props.update(merged_props)
        
        # Create bidirectional link
        edge = self.graph.link(
            http_node,
            browser_node,
            EdgeKind.HTTP_EQUIVALENT,
            weight=1.0,
            props={"linked_at": time.time()}
        )
        
        return edge
    
    def get_endpoint_context(
        self,
        endpoint_url: str
    ) -> Dict[str, Any]:
        """
        Get unified context for an endpoint (HTTP + browser data).
        Returns both HTTP and browser discovery data.
        """
        context = {
            "url": endpoint_url,
            "http_data": None,
            "browser_data": None,
            "linked_endpoints": [],
            "discovery_sources": []
        }
        
        # Find endpoint node
        endpoint_node = None
        for node in self.graph.nodes.values():
            if node.label == endpoint_url or node.label.startswith(endpoint_url):
                endpoint_node = node
                break
        
        if not endpoint_node:
            return context
        
        # Get HTTP data
        if endpoint_node.kind == NodeKind.ENDPOINT:
            context["http_data"] = endpoint_node.props
            context["discovery_sources"].append("http")
        
        # Get browser data
        if endpoint_node.kind in [NodeKind.BROWSER_ENDPOINT, NodeKind.JAVASCRIPT_ROUTE]:
            context["browser_data"] = endpoint_node.props
            context["discovery_sources"].append("browser")
        
        # Get linked endpoints
        linked = self.graph.neighbors(
            endpoint_node.id,
            direction="both",
            edge_kind=EdgeKind.HTTP_EQUIVALENT
        )
        
        for linked_node in linked:
            context["linked_endpoints"].append({
                "url": linked_node.label,
                "kind": linked_node.kind.value,
                "props": linked_node.props
            })
            
            # Add discovery source
            source = linked_node.props.get("source")
            if source and source not in context["discovery_sources"]:
                context["discovery_sources"].append(source)
        
        return context
    
    def get_browser_discoveries(
        self,
        scan_id: Optional[str] = None
    ) -> List[KGNode]:
        """Get all browser discoveries, optionally filtered by scan_id."""
        discoveries = []
        
        for node in self.graph.nodes.values():
            if node.kind in [NodeKind.BROWSER_ENDPOINT, NodeKind.JAVASCRIPT_ROUTE, NodeKind.WEBSOCKET_CONNECTION]:
                if scan_id is None or node.props.get("scan_id") == scan_id:
                    discoveries.append(node)
        
        return discoveries
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get statistics about browser discoveries."""
        browser_endpoints = len(self.graph.by_kind(NodeKind.BROWSER_ENDPOINT))
        js_routes = len(self.graph.by_kind(NodeKind.JAVASCRIPT_ROUTE))
        websockets = len(self.graph.by_kind(NodeKind.WEBSOCKET_CONNECTION))
        
        # Count linked endpoints
        linked_count = 0
        for edge in self.graph.edges.values():
            if edge.kind == EdgeKind.HTTP_EQUIVALENT:
                linked_count += 1
        
        return {
            "browser_endpoints": browser_endpoints,
            "javascript_routes": js_routes,
            "websocket_connections": websockets,
            "total_browser_discoveries": browser_endpoints + js_routes + websockets,
            "http_browser_links": linked_count,
            "timestamp": time.time()
        }


# Create global browser knowledge graph extension
browser_knowledge_graph = BrowserKnowledgeGraphExtension(knowledge_graph)
