"""
Graphify: AST-based codebase analysis for the API Endpoint Scanner.
Builds a dependency + call graph from the project's Python/JSX source files
using networkx. No external 'graphify' package required.

Usage:
    python graphify_scan.py
"""
import ast
import os
import re
import json
import multiprocessing
from pathlib import Path
from collections import defaultdict

import networkx as nx


def extract_python_nodes(filepath: Path):
    """Extract classes, functions, and imports from a Python file."""
    nodes = []
    edges = []
    module_name = str(filepath.stem)

    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, ValueError):
        return nodes, edges

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_id = f"{module_name}::{node.name}"
            nodes.append({
                "id": class_id,
                "label": node.name,
                "type": "class",
                "file": str(filepath),
                "line": node.lineno,
            })
            # Class inherits from bases
            for base in node.bases:
                base_name = ast.dump(base) if not hasattr(base, "id") else base.id
                if hasattr(base, "id"):
                    edges.append({
                        "source": class_id,
                        "target": f"*::{base.id}",
                        "relation": "inherits",
                    })

            # Methods inside the class
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_id = f"{class_id}.{item.name}"
                    nodes.append({
                        "id": method_id,
                        "label": f"{node.name}.{item.name}",
                        "type": "method",
                        "file": str(filepath),
                        "line": item.lineno,
                    })
                    edges.append({
                        "source": class_id,
                        "target": method_id,
                        "relation": "has_method",
                    })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node in tree.body:
            # Only module-level functions are emitted here; class methods are
            # already represented through their owning class above.
            func_id = f"{module_name}::{node.name}"
            nodes.append({
                "id": func_id,
                "label": node.name,
                "type": "function",
                "file": str(filepath),
                "line": node.lineno,
            })

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in (node.names or []):
                    imp_name = alias.name
                    edges.append({
                        "source": module_name,
                        "target": f"{node.module}::{imp_name}",
                        "relation": "imports",
                    })

    return nodes, edges


def extract_jsx_nodes(filepath: Path):
    """Extract React components and hooks from JSX files using regex."""
    nodes = []
    edges = []
    module_name = filepath.stem
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return nodes, edges

    # Find component definitions
    for match in re.finditer(r'(?:export\s+(?:default\s+)?)?function\s+(\w+)', source):
        comp_name = match.group(1)
        line = source[:match.start()].count("\n") + 1
        nodes.append({
            "id": f"{module_name}::{comp_name}",
            "label": comp_name,
            "type": "component",
            "file": str(filepath),
            "line": line,
        })

    # Find imports
    for match in re.finditer(r"import\s+(?:{[^}]+}|\w+)\s+from\s+['\"]([^'\"]+)['\"]", source):
        target_mod = match.group(1).split("/")[-1].replace(".jsx", "").replace(".js", "")
        edges.append({
            "source": module_name,
            "target": target_mod,
            "relation": "imports",
        })

    # Find hook usage
    for match in re.finditer(r'use(\w+)\s*\(', source):
        hook_name = f"use{match.group(1)}"
        edges.append({
            "source": module_name,
            "target": hook_name,
            "relation": "uses_hook",
        })

    return nodes, edges


def build_graph(all_nodes, all_edges):
    """Build a NetworkX directed graph from extracted nodes and edges."""
    G = nx.DiGraph()

    for node in all_nodes:
        G.add_node(node["id"], **node)

    for edge in all_edges:
        src = edge["source"]
        tgt = edge["target"]
        # Resolve wildcard targets (e.g., *::BaseAgent → hive::BaseAgent)
        if tgt.startswith("*::"):
            base_name = tgt[3:]
            resolved = [n for n in G.nodes if n.endswith(f"::{base_name}")]
            if resolved:
                tgt = resolved[0]
        if src in G.nodes or True:  # Allow dangling for analysis
            G.add_edge(src, tgt, relation=edge.get("relation", "unknown"))

    return G


def find_god_nodes(G, top_n=20):
    """Find nodes with highest total degree (in + out connections)."""
    degrees = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:top_n]
    results = []
    for node_id, degree in degrees:
        data = G.nodes.get(node_id, {})
        results.append({
            "label": data.get("label", node_id),
            "id": node_id,
            "degree": degree,
            "type": data.get("type", "unknown"),
            "file": data.get("file", ""),
        })
    return results


def find_communities(G):
    """Detect communities using connected components on undirected projection."""
    UG = G.to_undirected()
    communities = {}
    for i, component in enumerate(nx.connected_components(UG)):
        communities[i] = list(component)
    return communities


def find_surprising_connections(G, communities, top_n=10):
    """Find edges that connect different communities (cross-cutting concerns)."""
    node_to_comm = {}
    for cid, nodes in communities.items():
        for n in nodes:
            node_to_comm[n] = cid

    surprises = []
    for src, tgt, data in G.edges(data=True):
        src_comm = node_to_comm.get(src, -1)
        tgt_comm = node_to_comm.get(tgt, -1)
        if src_comm != tgt_comm and src_comm >= 0 and tgt_comm >= 0:
            surprises.append({
                "source": src,
                "target": tgt,
                "relation": data.get("relation", ""),
                "source_community": src_comm,
                "target_community": tgt_comm,
            })

    # Sort by how large the source community is (bigger = more surprising)
    comm_sizes = {cid: len(nodes) for cid, nodes in communities.items()}
    surprises.sort(key=lambda s: comm_sizes.get(s["source_community"], 0), reverse=True)
    return surprises[:top_n]


def main():
    root = Path(r"d:\Antigravity 2\API Endpoint Scanner")

    # Collect files
    import glob
    py_files = [Path(f) for f in glob.glob(str(root / "backend" / "**" / "*.py"), recursive=True)]
    jsx_files = [Path(f) for f in glob.glob(str(root / "src" / "**" / "*.jsx"), recursive=True)]
    js_files = [Path(f) for f in glob.glob(str(root / "src" / "**" / "*.js"), recursive=True)]
    all_files = py_files + jsx_files + js_files
    print(f"Scanning {len(all_files)} project files for AST extraction...")

    all_nodes = []
    all_edges = []

    for filepath in all_files:
        if filepath.suffix == ".py":
            nodes, edges = extract_python_nodes(filepath)
        else:
            nodes, edges = extract_jsx_nodes(filepath)
        all_nodes.extend(nodes)
        all_edges.extend(edges)

    print(f"Extraction complete: {len(all_nodes)} nodes, {len(all_edges)} edges")

    if not all_nodes:
        print("No nodes extracted!")
        return

    G = build_graph(all_nodes, all_edges)
    communities = find_communities(G)

    # Tag community membership
    for cid, nodes in communities.items():
        for n in nodes:
            if n in G.nodes:
                G.nodes[n]["community"] = cid

    gods = find_god_nodes(G, top_n=20)
    surprises = find_surprising_connections(G, communities, top_n=10)

    print(f"\n=== GRAPH BUILT ===")
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    print(f"Communities: {len(communities)}")

    print(f"\n=== GOD NODES (most connected) ===")
    for i, g in enumerate(gods, 1):
        print(f"  {i}. {g['label']} ({g['type']}): {g['degree']} connections")
        if g.get("file"):
            print(f"     -> {g['file']}")

    print(f"\n=== SURPRISING CONNECTIONS (cross-community) ===")
    for s in surprises:
        print(f"  {s['source']} <-> {s['target']}")
        print(f"    relation: {s['relation']}, communities: {s['source_community']} -> {s['target_community']}")

    # Save outputs
    from networkx.readwrite import json_graph
    out = root / "graphify-out"
    out.mkdir(exist_ok=True)

    data = json_graph.node_link_data(G)
    (out / "graph.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nSaved graph to {out / 'graph.json'}")

    comm_summary = {}
    for cid, nodes in sorted(communities.items()):
        labels = [G.nodes[n].get("label", n) for n in nodes[:10] if n in G.nodes]
        comm_summary[str(cid)] = {"size": len(nodes), "sample": labels}
    (out / "communities.json").write_text(json.dumps(comm_summary, indent=2), encoding="utf-8")
    print(f"Saved communities to {out / 'communities.json'}")

    # Save god nodes report
    (out / "god_nodes.json").write_text(json.dumps(gods, indent=2), encoding="utf-8")
    print(f"Saved god nodes to {out / 'god_nodes.json'}")

    # Save surprising connections
    (out / "surprises.json").write_text(json.dumps(surprises, indent=2), encoding="utf-8")
    print(f"Saved surprising connections to {out / 'surprises.json'}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
