"""
API Key Compatibility Layer
Provides drop-in replacement for API_CONFIG_PATH pattern.
All modules using the old `open(API_CONFIG_PATH)` pattern can import this.
"""

from typing import Dict, Any
import json
from pathlib import Path

try:
    from core.secure_keys import get_api_key, load_api_keys, save_api_keys
    _SECURE_KEYS_AVAILABLE = True
except ImportError:
    _SECURE_KEYS_AVAILABLE = False
    def get_api_key(key_name: str) -> str:
        return ""
    def load_api_keys() -> Dict[str, Any]:
        return {}
    def save_api_keys(keys: Dict[str, Any]) -> bool:
        return False


# Backward compatibility: API_CONFIG_PATH as a Path-like object
class _APIConfigPath:
    """Path-like object that reads/writes from secure key manager."""
    
    def __init__(self):
        self._path = Path()
    
    def exists(self) -> bool:
        if _SECURE_KEYS_AVAILABLE:
            return bool(load_api_keys())
        return False
    
    def read_text(self, encoding: str = "utf-8") -> str:
        if _SECURE_KEYS_AVAILABLE:
            keys = load_api_keys()
            return json.dumps(keys, indent=2)
        return "{}"
    
    def write_text(self, data: str, encoding: str = "utf-8") -> None:
        if _SECURE_KEYS_AVAILABLE:
            try:
                keys = json.loads(data)
                save_api_keys(keys)
            except Exception:
                pass
    
    def __str__(self) -> str:
        return str(self._path)
    
    def __truediv__(self, other):
        return self._path / other


# Global instance for backward compatibility
API_CONFIG_PATH = _APIConfigPath()


def get_gemini_api_key() -> str:
    """Get Gemini API key from secure storage."""
    return get_api_key("gemini_api_key")


def get_all_api_keys() -> Dict[str, str]:
    """Get all API keys as dict."""
    if _SECURE_KEYS_AVAILABLE:
        return load_api_keys()
    return {}


def set_api_key(key_name: str, value: str) -> bool:
    """Set a single API key."""
    if _SECURE_KEYS_AVAILABLE:
        keys = load_api_keys()
        keys[key_name] = value
        return save_api_keys(keys)
    return False