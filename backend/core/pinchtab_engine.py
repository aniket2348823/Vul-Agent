"""
PinchTabEngine: Fast browser operations using PinchTab.

Provides lightweight capabilities:
- Fast DOM scraping
- Token extraction
- Quick navigation
- Simple injection testing
"""

import asyncio
from typing import Dict, Any, List, Optional
import re

from backend.integrations.pinchtab_client import PinchTabClient


class PinchTabEngine:
    """Fast browser operations using PinchTab"""
    
    def __init__(self):
        self.client = PinchTabClient()
        self.last_tab_id = None
        self.last_url = None
        
    async def initialize(self):
        """Initialize PinchTab client"""
        try:
            await self.client.health()
            print("[PinchTabEngine] PinchTab client initialized")
            return True
        except Exception as e:
            print(f"[PinchTabEngine] Initialization failed: {e}")
            return False
            
    async def navigate(self, url: str):
        """
        Fast navigation to URL.
        
        Args:
            url: Target URL
            
        Returns:
            Navigation result with tab ID
        """
        try:
            result = await self.client.navigate(url)
            self.last_tab_id = result.get("tabId") or result.get("id") or result.get("targetId")
            self.last_url = url
            
            return {
                "tab_id": self.last_tab_id,
                "url": url,
                "success": True
            }
        except Exception as e:
            print(f"[PinchTabEngine] Navigation failed: {e}")
            return {
                "tab_id": None,
                "url": url,
                "success": False,
                "error": str(e)
            }
            
    async def extract_endpoints_fast(self, url: str) -> List[str]:
        """
        Fast endpoint extraction using regex.
        
        Extracts:
        - /api/* patterns
        - /v1/* patterns
        - Common REST endpoints
        """
        await self.navigate(url)
        
        if not self.last_tab_id:
            return []
            
        try:
            text = await self.client.text(self.last_tab_id)
            text_str = str(text)
            
            endpoints = set()
            
            # Extract API endpoints
            api_patterns = [
                r'["\']/(api|v\d+)/[^"\']+["\']',
                r'["\']/(graphql|rest|rpc)[^"\']*["\']',
                r'fetch\(["\']([^"\']+)["\']',
                r'axios\.[a-z]+\(["\']([^"\']+)["\']',
            ]
            
            for pattern in api_patterns:
                matches = re.findall(pattern, text_str, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match else ""
                    if match:
                        endpoints.add(match.strip('\'"'))
                        
            return list(endpoints)
        except Exception as e:
            print(f"[PinchTabEngine] Endpoint extraction failed: {e}")
            return []
            
    async def extract_tokens(self, url: str) -> List[str]:
        """
        Fast token extraction.
        
        Extracts:
        - JWT tokens (eyJ...)
        - Bearer tokens
        - API keys
        """
        await self.navigate(url)
        
        if not self.last_tab_id:
            return []
            
        try:
            text = await self.client.text(self.last_tab_id)
            text_str = str(text)
            
            tokens = set()
            
            # Extract JWT tokens
            jwt_pattern = r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
            jwt_matches = re.findall(jwt_pattern, text_str)
            tokens.update(jwt_matches)
            
            # Extract Bearer tokens
            bearer_pattern = r'Bearer\s+([A-Za-z0-9_-]{20,})'
            bearer_matches = re.findall(bearer_pattern, text_str, re.IGNORECASE)
            tokens.update(bearer_matches)
            
            # Extract API keys
            api_key_pattern = r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']([^"\']{20,})["\']'
            api_key_matches = re.findall(api_key_pattern, text_str, re.IGNORECASE)
            tokens.update(api_key_matches)
            
            return list(tokens)
        except Exception as e:
            print(f"[PinchTabEngine] Token extraction failed: {e}")
            return []
            
    async def test_injection(self, url: str, payload: str, method: str = "GET"):
        """
        Fast injection test.
        
        Tests if payload is reflected in response.
        """
        # Navigate with payload
        test_url = f"{url}{'&' if '?' in url else '?'}test={payload}"
        await self.navigate(test_url)
        
        if not self.last_tab_id:
            return {"reflected": False, "error": "Navigation failed"}
            
        try:
            text = await self.client.text(self.last_tab_id)
            text_str = str(text)
            
            # Check if payload is reflected
            reflected = payload in text_str
            
            return {
                "reflected": reflected,
                "payload": payload,
                "url": test_url
            }
        except Exception as e:
            return {"reflected": False, "error": str(e)}
            
    async def analyze_dom(self, url: str) -> Dict[str, Any]:
        """
        Analyze DOM structure.
        
        Extracts:
        - Forms
        - Input fields
        - Buttons
        - Links
        """
        await self.navigate(url)
        
        if not self.last_tab_id:
            return {}
            
        try:
            text = await self.client.text(self.last_tab_id)
            snapshot = await self.client.snapshot(self.last_tab_id)
            
            # Parse snapshot for forms and inputs
            forms = []
            inputs = []
            buttons = []
            
            # Simple regex-based extraction
            text_str = str(text)
            
            # Extract form actions
            form_pattern = r'<form[^>]*action=["\']([^"\']+)["\']'
            form_matches = re.findall(form_pattern, text_str, re.IGNORECASE)
            forms = [{"action": action} for action in form_matches]
            
            # Extract input fields
            input_pattern = r'<input[^>]*name=["\']([^"\']+)["\'][^>]*type=["\']([^"\']+)["\']'
            input_matches = re.findall(input_pattern, text_str, re.IGNORECASE)
            inputs = [{"name": name, "type": type_} for name, type_ in input_matches]
            
            # Extract buttons
            button_pattern = r'<button[^>]*>([^<]+)</button>'
            button_matches = re.findall(button_pattern, text_str, re.IGNORECASE)
            buttons = [{"text": text} for text in button_matches]
            
            return {
                "forms": forms,
                "inputs": inputs,
                "buttons": buttons,
                "text": text_str[:1000],  # First 1000 chars
                "snapshot": snapshot
            }
        except Exception as e:
            print(f"[PinchTabEngine] DOM analysis failed: {e}")
            return {}
            
    async def get_page_text(self) -> str:
        """Get page text content"""
        if not self.last_tab_id:
            return ""
            
        try:
            text = await self.client.text(self.last_tab_id)
            return str(text)
        except Exception as e:
            print(f"[PinchTabEngine] Get page text failed: {e}")
            return ""
            
    async def close(self):
        """Cleanup"""
        # PinchTab manages its own browser lifecycle
        self.last_tab_id = None
        self.last_url = None
