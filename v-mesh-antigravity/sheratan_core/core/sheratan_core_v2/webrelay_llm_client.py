# sheratan_core_v2/webrelay_llm_client.py
"""
WebRelay LLM Client for loop_runner integration.
Implements LLMClient interface using WebRelay HTTP API.
"""

import requests
import json
from typing import Optional


class WebRelayLLMClient:
    """
    LLM Client that calls WebRelay via HTTP.
    Compatible with loop_runner's LLMClient interface.
    """
    
    def __init__(self, base_url: str = "http://localhost:3000", model_config: Optional[dict] = None):
        self.base_url = base_url.rstrip('/')
        self.model_config = model_config or {}
        
    def call(self, prompt: str) -> str:
        """
        Calls WebRelay HTTP API with the prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            Raw LLM response text (should be valid LCP JSON)
            
        Raises:
            Exception: If the HTTP call fails
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/llm/call",
                json={"prompt": prompt},
                timeout=120  # 2 minutes for LLM response
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok"):
                raise Exception(f"WebRelay error: {result.get('error', 'Unknown error')}")
            
            # Extract the actual LLM response
            # WebRelay returns parsed data, we need to reconstruct the JSON for loop_runner
            if result.get("type") == "lcp":
                # LCP response - convert back to JSON string
                lcp_response = {
                    "ok": True,
                    "action": result.get("action"),
                    "commentary": result.get("commentary"),
                    "new_jobs": result.get("new_jobs", [])
                }
                return json.dumps(lcp_response)
            else:
                # Plain response - wrap in basic structure
                return json.dumps({
                    "summary": result.get("summary", ""),
                    "ok": True
                })
                
        except requests.exceptions.Timeout:
            raise Exception("WebRelay request timeout")
        except requests.exceptions.RequestException as e:
            raise Exception(f"WebRelay request failed: {str(e)}")
    
    def health_check(self) -> bool:
        """Check if WebRelay is available."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
