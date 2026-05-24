import asyncio
import json
from backend.core.content_boundary import content_boundary
import os
import math
import re
import aiohttp
import time as _time
from backend.core.hive import BaseAgent, EventType, HiveEvent
from backend.core.protocol import JobPacket, ResultPacket, AgentID
from backend.core.memory import memory_store, cosine_similarity
from backend.core.sandbox import TempWorkspace
from backend.core.queue import command_lane

class KappaAgent(BaseAgent):
    """
    AGENT KAPPA: THE LIBRARIAN
    Role: Knowledge & Memory.
    Capabilities:
    - Persistent Vector Memory for exploit history.
    - AI-Driven Semantic Similarity Search (via Gemini text-embedding-004).
    - Anomaly suppression via truth kernel.
    """
    def __init__(self, bus):
        super().__init__("agent_kappa", bus)
        base_dir = os.getcwd()
        self.memory_file = os.path.join(base_dir, "brain", "exploit_vectors.json")
        
        # Initialize Cortex AI
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
        """Generate vector embedding using Gemini text-embedding-004."""
        if self._embeddings_disabled: return []
        try:
            from backend.ai.gemini import gemini_client
            if not gemini_client.is_available:
                self._embeddings_disabled = True
                return []
            embedding = await gemini_client.generate_embedding(text)
            if not embedding:
                self._embeddings_disabled = True
            return embedding
        except Exception as e:
            self._embeddings_disabled = True
        return []

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        return cosine_similarity(vec1, vec2)

    async def archive_victory(self, event: HiveEvent):
        payload = event.payload
        # ScanContext: record event for transcript causality
        if hasattr(self.bus, "get_or_create_context"):
            _ctx = self.bus.get_or_create_context(getattr(event, "scan_id", "GLOBAL"))
            _ctx.append_event(event)
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
        memory_store.remember_episode(event.scan_id, {"type": "vulnerability", "payload": archive_data})
        if embedding:
            memory_store.remember_semantic(archive_data)
        
        await self.bus.publish(HiveEvent(
            type=EventType.LOG,
            source=self.name,
            payload={"message": f"Vector Memory {archive_data['type']} stored with {len(embedding)}-dim embedding."}
        ))

        # PROBLEM 6 FIX: Feed intelligence back to Omega for adaptive replanning
        confidence = payload.get("confidence", 0.0)
        vuln_type = payload.get("type", "")
        url = payload.get("url", "")
        if confidence > 0.7 and vuln_type:
            pattern = {
                "vuln_type": vuln_type,
                "endpoint_pattern": self._extract_pattern(url),
                "confidence": confidence,
                "timestamp": _time.time()
            }
            await self.bus.publish(HiveEvent(
                type=EventType.PATTERN_LEARNED,
                source=self.name,
                scan_id=event.scan_id,
                payload={"pattern": pattern}
            ))
            print(f"[{self.name}] [PATTERN] Fed pattern '{vuln_type}' back to Omega for adaptive replanning.")

    def _extract_pattern(self, url: str) -> str:
        """Convert specific URL to a reusable pattern for cross-scan intelligence."""
        pattern = re.sub(r'/\d+', '/{id}', url)
        pattern = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', pattern)
        return pattern

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

        semantic_hits = memory_store.recall_semantic(query_vec, top_k=top_k)
        if semantic_hits:
            sanitized_hits = []
        for hit in semantic_hits:
            if isinstance(hit, dict) and "payload" in hit:
                hit["payload"] = content_boundary.sanitize_control_tokens(str(hit["payload"]))
            sanitized_hits.append(hit)
        return sanitized_hits

        async with TempWorkspace(prefix="kappa-recall") as workspace:
            workspace.write_file("query.txt", query)
            with open(self.memory_file, "r") as f:
                data = json.load(f)
            workspace.write_file("memory_record_count.txt", str(len(data)))

            scored_records = []
            for rec in data:
                rec_vec = rec.get("vector", [])
                if rec_vec:
                    sim = self._cosine_similarity(query_vec, rec_vec)
                    scored_records.append((sim, rec))

        scored_records.sort(key=lambda x: x[0], reverse=True)
        return [r for sim, r in scored_records[:top_k] if sim > 0.3]
