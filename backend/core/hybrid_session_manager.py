"""
Hybrid Session Manager for OpenClaw + PinchTab Integration
Handles session persistence, restoration, and sharing between both browser engines.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
import asyncio


class HybridSessionManager:
    """
    Manages browser sessions across OpenClaw and PinchTab engines.
    Supports session save/restore, cross-engine session sharing, and cleanup.
    """
    
    def __init__(self, storage_dir: str = "scan_states/sessions"):
        """
        Initialize the session manager.
        
        Args:
            storage_dir: Directory to store session files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
    async def save_session(
        self,
        session_id: str,
        engine: str,
        session_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a browser session to disk.
        
        Args:
            session_id: Unique identifier for the session
            engine: Engine type ("openclaw" or "pinchtab")
            session_data: Session data to save (cookies, storage, etc.)
            metadata: Optional metadata (scan_id, target_url, etc.)
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            session_file = self.storage_dir / f"{session_id}_{engine}.json"
            
            session_bundle = {
                "session_id": session_id,
                "engine": engine,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
                "data": session_data
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_bundle, f, indent=2)
            
            # Cache in memory
            self.sessions[f"{session_id}_{engine}"] = session_bundle
            
            return True
            
        except Exception as e:
            print(f"[HybridSessionManager] Failed to save session {session_id}: {e}")
            return False
    
    async def restore_session(
        self,
        session_id: str,
        engine: str
    ) -> Optional[Dict[str, Any]]:
        """
        Restore a browser session from disk.
        
        Args:
            session_id: Unique identifier for the session
            engine: Engine type ("openclaw" or "pinchtab")
            
        Returns:
            Session data if found, None otherwise
        """
        try:
            cache_key = f"{session_id}_{engine}"
            
            # Check memory cache first
            if cache_key in self.sessions:
                return self.sessions[cache_key]["data"]
            
            # Load from disk
            session_file = self.storage_dir / f"{session_id}_{engine}.json"
            
            if not session_file.exists():
                return None
            
            with open(session_file, 'r') as f:
                session_bundle = json.load(f)
            
            # Cache in memory
            self.sessions[cache_key] = session_bundle
            
            return session_bundle["data"]
            
        except Exception as e:
            print(f"[HybridSessionManager] Failed to restore session {session_id}: {e}")
            return None
    
    async def _export_openclaw_session(self, context) -> Dict[str, Any]:
        """
        Export OpenClaw session data (cookies, localStorage, sessionStorage).
        
        Args:
            context: OpenClaw browser context
            
        Returns:
            Dictionary containing session data
        """
        try:
            # Get cookies
            cookies = await context.cookies()
            
            # Get storage state (includes localStorage and sessionStorage)
            storage_state = await context.storage_state()
            
            return {
                "cookies": cookies,
                "storage_state": storage_state,
                "type": "openclaw"
            }
            
        except Exception as e:
            print(f"[HybridSessionManager] Failed to export OpenClaw session: {e}")
            return {}
    
    async def _import_openclaw_session(self, context, session_data: Dict[str, Any]) -> bool:
        """
        Import session data into OpenClaw context.
        
        Args:
            context: OpenClaw browser context
            session_data: Session data to import
            
        Returns:
            True if import successful, False otherwise
        """
        try:
            # Restore storage state (includes cookies, localStorage, sessionStorage)
            if "storage_state" in session_data:
                await context.add_init_script(f"""
                    const storageState = {json.dumps(session_data['storage_state'])};
                    if (storageState.origins) {{
                        storageState.origins.forEach(origin => {{
                            if (origin.localStorage) {{
                                origin.localStorage.forEach(item => {{
                                    localStorage.setItem(item.name, item.value);
                                }});
                            }}
                            if (origin.sessionStorage) {{
                                origin.sessionStorage.forEach(item => {{
                                    sessionStorage.setItem(item.name, item.value);
                                }});
                            }}
                        }});
                    }}
                """)
            
            # Add cookies
            if "cookies" in session_data:
                await context.add_cookies(session_data["cookies"])
            
            return True
            
        except Exception as e:
            print(f"[HybridSessionManager] Failed to import OpenClaw session: {e}")
            return False
    
    async def _export_pinchtab_session(self, pinchtab_client) -> Dict[str, Any]:
        """
        Export PinchTab session data.
        
        Args:
            pinchtab_client: PinchTab client instance
            
        Returns:
            Dictionary containing session data
        """
        try:
            # PinchTab session export (cookies, localStorage)
            # This is a placeholder - actual implementation depends on PinchTab API
            session_data = {
                "cookies": [],  # Would call pinchtab_client.get_cookies()
                "localStorage": {},  # Would call pinchtab_client.get_local_storage()
                "type": "pinchtab"
            }
            
            return session_data
            
        except Exception as e:
            print(f"[HybridSessionManager] Failed to export PinchTab session: {e}")
            return {}
    
    async def _import_pinchtab_session(self, pinchtab_client, session_data: Dict[str, Any]) -> bool:
        """
        Import session data into PinchTab.
        
        Args:
            pinchtab_client: PinchTab client instance
            session_data: Session data to import
            
        Returns:
            True if import successful, False otherwise
        """
        try:
            # PinchTab session import
            # This is a placeholder - actual implementation depends on PinchTab API
            
            if "cookies" in session_data:
                pass  # Would call pinchtab_client.set_cookies(session_data["cookies"])
            
            if "localStorage" in session_data:
                pass  # Would call pinchtab_client.set_local_storage(session_data["localStorage"])
            
            return True
            
        except Exception as e:
            print(f"[HybridSessionManager] Failed to import PinchTab session: {e}")
            return False
    
    async def share_session(
        self,
        session_id: str,
        from_engine: str,
        to_engine: str
    ) -> bool:
        """
        Share a session between engines (e.g., OpenClaw -> PinchTab).
        
        Args:
            session_id: Session identifier
            from_engine: Source engine ("openclaw" or "pinchtab")
            to_engine: Target engine ("openclaw" or "pinchtab")
            
        Returns:
            True if sharing successful, False otherwise
        """
        try:
            # Load source session
            source_session = await self.restore_session(session_id, from_engine)
            
            if not source_session:
                return False
            
            # Convert session format if needed
            converted_session = self._convert_session_format(source_session, from_engine, to_engine)
            
            # Save to target engine
            return await self.save_session(session_id, to_engine, converted_session)
            
        except Exception as e:
            print(f"[HybridSessionManager] Failed to share session: {e}")
            return False
    
    def _convert_session_format(
        self,
        session_data: Dict[str, Any],
        from_engine: str,
        to_engine: str
    ) -> Dict[str, Any]:
        """
        Convert session data between engine formats.
        
        Args:
            session_data: Source session data
            from_engine: Source engine type
            to_engine: Target engine type
            
        Returns:
            Converted session data
        """
        # Basic conversion - both engines use similar cookie/storage formats
        # More sophisticated conversion can be added as needed
        return {
            "cookies": session_data.get("cookies", []),
            "localStorage": session_data.get("localStorage", {}),
            "sessionStorage": session_data.get("sessionStorage", {}),
            "type": to_engine
        }
    
    async def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove expired session files.
        
        Args:
            max_age_hours: Maximum age of sessions in hours
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cleaned = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            for session_file in self.storage_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        session_bundle = json.load(f)
                    
                    timestamp = datetime.fromisoformat(session_bundle["timestamp"])
                    
                    if timestamp < cutoff_time:
                        session_file.unlink()
                        cleaned += 1
                        
                        # Remove from memory cache
                        cache_key = f"{session_bundle['session_id']}_{session_bundle['engine']}"
                        self.sessions.pop(cache_key, None)
                        
                except Exception as e:
                    print(f"[HybridSessionManager] Error cleaning {session_file}: {e}")
                    continue
            
            return cleaned
            
        except Exception as e:
            print(f"[HybridSessionManager] Cleanup failed: {e}")
            return 0
    
    def list_sessions(self, engine: Optional[str] = None) -> list:
        """
        List all stored sessions.
        
        Args:
            engine: Optional filter by engine type
            
        Returns:
            List of session metadata
        """
        sessions = []
        
        for session_file in self.storage_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_bundle = json.load(f)
                
                if engine and session_bundle["engine"] != engine:
                    continue
                
                sessions.append({
                    "session_id": session_bundle["session_id"],
                    "engine": session_bundle["engine"],
                    "timestamp": session_bundle["timestamp"],
                    "metadata": session_bundle.get("metadata", {})
                })
                
            except Exception:
                continue
        
        return sessions
