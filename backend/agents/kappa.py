import asyncio
import json
import os
import math
import aiohttp
import time as _time
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID

class KappaAgent(BaseAgent):
    """
    AGENT KAPPA: THE LIBRARIAN
    Role: Knowledge & Memory.
    Capabilities:
    - Persistent Vector Memory for exploit history.
    - AI-Driven Semantic Similarity Search.
    - Anomaly suppression via truth kernel.
    """
    def __init__(self, bus):
        super().__init__("agent_kappa", bus)
        base_dir = os.getcwd()
        self.memory_file = os.path.join(base_dir, "brain", "exploit_vectors.json")
        
        # Initialize Cortex AI (Local Ollama)
        try:
            from backend.ai.cortex import CortexEngine, get_cortex_engine
            self.truth_kernel = get_cortex_engine()
        except Exception:
            self.truth_kernel = None
            
        self._embeddings_disabled = False
        self._ensure_memory()

    def _ensure_memory(self):
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, "w") as f:
                json.dump([], f)

    async def setup(self):
        self.bus.subscribe(EventType.VULN_CONFIRMED, self.archive_victory)

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate vector embedding using Ollama."""
        if self._embeddings_disabled: return []
        ollama_url = getattr(self.truth_kernel, 'ollama_url', "http://localhost:11434")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{ollama_url}/api/embeddings", json={
                    "model": "nomic-embed-text", 
                    "prompt": text
                }, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("embedding", [])
                    elif resp.status == 404:
                        self._embeddings_disabled = True
                        return []
                    else:
                        print(f"[{self.name}] Embedding status error: {resp.status}")
        except Exception as e:
            self._embeddings_disabled = True
        return []

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2): return 0.0
        dot = sum(a*b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a*a for a in vec1))
        norm2 = math.sqrt(sum(b*b for b in vec2))
        if norm1 == 0 or norm2 == 0: return 0.0
        return dot / (norm1 * norm2)

    async def archive_victory(self, event: HiveEvent):
        payload = event.payload
        print(f"[{self.name}] [ARCHIVE] Verified Vulnerability Exploit Captured. Embedding...")
        
        # RICHER SCHEMA (V6 Enhancement)
        archive_data = {
            "type": payload.get("type", "unknown"),
            "url": payload.get("url", ""),
            "payload": payload.get("payload", ""),
            "confidence": payload.get("confidence", 0.0),
            "audit_reasoning": payload.get("audit_reasoning", ""),
            "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Generate Vector Representation
        text_rep = f"TYPE: {archive_data['type']} | URL: {archive_data['url']} | PAYLOAD: {archive_data['payload']}"
        embedding = await self._get_embedding(text_rep)
        archive_data["vector"] = embedding
        
        self._save_record(archive_data)
        
        await self.bus.publish(HiveEvent(
            type=EventType.LOG,
            source=self.name,
            payload={"message": f"Vector Memory {archive_data['type']} stored with {len(embedding)}-dim embedding."}
        ))

    def _save_record(self, record):
        try:
            with open(self.memory_file, "r+") as f:
                data = json.load(f)
                data.append(record)
                f.seek(0)
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[{self.name}] Memory Write Error: {e}")

    async def recall_tactics(self, query: str, top_k: int = 3):
        """Vector memory Semantic Search."""
        print(f"[{self.name}] Semantic search for: {query}")
        query_vec = await self._get_embedding(query)
        if not query_vec: return []

        with open(self.memory_file, "r") as f:
            data = json.load(f)

        scored_records = []
        for rec in data:
            rec_vec = rec.get("vector", [])
            if rec_vec:
                sim = self._cosine_similarity(query_vec, rec_vec)
                scored_records.append((sim, rec))

        scored_records.sort(key=lambda x: x[0], reverse=True)
        return [r for sim, r in scored_records[:top_k] if sim > 0.3]
