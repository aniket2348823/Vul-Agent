import asyncio
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import networkx as nx
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Xytherion.GraphAI")

class GraphIntelligence:
    """
    XYTHERION GLOBAL BRAIN (GRAPH AI)
    Role: Predictive attack path modeling and cross-node swarm intelligence.
    """
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.attack_graph = nx.DiGraph()
        self.vulnerability_clusters = {}
        self.attack_patterns = {}
        self.learning_rate = 0.1
        
    async def build_graph_from_data(self):
        """Builds a directed attack graph from all cluster findings."""
        try:
            # Atomic fetch from global persistence
            nodes_data = self.supabase.table("attack_graph").select("*").execute()
            
            self.attack_graph.clear()
            for node in nodes_data.data:
                self.attack_graph.add_node(
                    node["id"],
                    type=node["node_type"],
                    target=node["target"],
                    score=node["vulnerability_score"],
                    timestamp=node["timestamp"]
                )
                
                # Link related targets (Lateral Movement mapping)
                if node.get("connections"):
                    for connection in node["connections"]:
                        if self.attack_graph.has_node(connection):
                            self.attack_graph.add_edge(node["id"], connection)
                            
            logger.info(f"🧠 Built Xytherion Graph: {len(self.attack_graph)} nodes.")
        except Exception as e:
            logger.error(f"❌ Graph Build FAIL: {e}")

    async def analyze_attack_paths(self) -> List[Dict]:
        """Identifies optimal exploitation chains using shortest-path logic."""
        paths = []
        try:
            # Find high-value targets (Score > 7)
            targets = [n for n, d in self.attack_graph.nodes(data=True) if d.get("score", 0) > 7]
            
            for target in targets:
                for source in self.attack_graph.nodes():
                    if source == target: continue
                    try:
                        # Dijkstra-style pathfinding
                        path = nx.shortest_path(self.attack_graph, source, target)
                        if len(path) > 1:
                            paths.append({
                                "source": source,
                                "target": target,
                                "steps": path,
                                "length": len(path),
                                "cumulative_risk": sum(self.attack_graph.nodes[n].get("score", 0) for n in path)
                            })
                    except nx.NetworkXNoPath:
                        continue
            paths.sort(key=lambda x: x["cumulative_risk"], reverse=True)
            return paths[:10]
        except Exception as e:
            logger.error(f"❌ Path Analysis FAIL: {e}")
            return []

    async def identify_vulnerability_clusters(self) -> Dict:
        """Clusters related vectors using DBSCAN for mass-exploit identification."""
        try:
            features = []
            node_ids = []
            for nid, data in self.attack_graph.nodes(data=True):
                # Vectorize finding
                vector = [
                    data.get("score", 0),
                    len(list(self.attack_graph.predecessors(nid))),
                    len(list(self.attack_graph.successors(nid)))
                ]
                features.append(vector)
                node_ids.append(nid)
            
            if len(features) < 2: return {}
            
            # Density-Based Clustering
            scaler = StandardScaler()
            scaled = scaler.fit_transform(features)
            clustering = DBSCAN(eps=0.5, min_samples=2).fit(scaled)
            
            clusters = {}
            for i, label in enumerate(clustering.labels_):
                if label != -1: # Noise removal
                    if label not in clusters: clusters[label] = []
                    clusters[label].append(node_ids[i])
            return clusters
        except Exception as e:
            logger.error(f"❌ Clustering FAIL: {e}")
            return {}

    async def predict_next_targets(self) -> List[Dict]:
        """Uses PageRank/Centrality to predict the next logical node to pivot to."""
        try:
            pagerank = nx.pagerank(self.attack_graph)
            centrality = nx.betweenness_centrality(self.attack_graph)
            
            predictions = []
            for nid in self.attack_graph.nodes():
                data = self.attack_graph.nodes[nid]
                if data.get("score", 0) > 8: continue # Already hit
                
                # Predictive score formula
                pred_score = (pagerank.get(nid, 0) * 0.4 + centrality.get(nid, 0) * 0.4 + data.get("score", 0) * 0.2)
                predictions.append({"target": data.get("target"), "confidence": pred_score})
            
            predictions.sort(key=lambda x: x["confidence"], reverse=True)
            return predictions[:15]
        except Exception as e:
            logger.error(f"❌ Prediction FAIL: {e}")
            return []

if __name__ == "__main__":
    # Brain Bootstrap
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if supabase_url:
        brain = GraphIntelligence(supabase_url, supabase_key)
        asyncio.run(brain.build_graph_from_data())
        print("Brain Test Complete.")
