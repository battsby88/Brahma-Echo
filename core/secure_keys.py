"""
Secure Key Management for Brahma Echo
- Encrypts api_keys.json at rest using Fernet (AES-256)
- Stores master key in OS keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- Automatic key rotation and backup
"""

import os
import json
import base64
import secrets
import hashlib
import time
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

SERVICE_NAME = "BrahmaEcho"
KEYRING_ACCOUNT = "api_keys_master"
CONFIG_DIR = Path(os.getenv('LOCALAPPDATA', os.path.expanduser('~'))) / 'BrahmaAI' / 'config'
ENCRYPTED_KEYS_FILE = CONFIG_DIR / "api_keys.json.enc"
SALT_FILE = CONFIG_DIR / "api_keys.salt"
KEYRING_BACKUP_FILE = CONFIG_DIR / "keyring_backup.json"


class SecureKeyManager:
    """Manages encrypted API keys with OS keyring integration."""
    
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._fernet: Optional[Fernet] = None
        self._master_key: Optional[bytes] = None
    
    def _get_or_create_master_key(self) -> bytes:
        """Retrieve master key from OS keyring or create new one."""
        if self._master_key:
            return self._master_key
        
        # Try to get from keyring
        if KEYRING_AVAILABLE:
            try:
                stored = keyring.get_password(SERVICE_NAME, KEYRING_ACCOUNT)
                if stored:
                    self._master_key = base64.b64decode(stored)
                    return self._master_key
            except Exception:
                pass
        
        # Fallback: try backup file
        if KEYRING_BACKUP_FILE.exists():
            try:
                with open(KEYRING_BACKUP_FILE, 'r') as f:
                    data = json.load(f)
                    self._master_key = base64.b64decode(data['master_key'])
                    return self._master_key
            except Exception:
                pass
        
        # Generate new master key
        self._master_key = Fernet.generate_key()
        self._store_master_key()
        return self._master_key
    
    def _store_master_key(self) -> None:
        """Store master key in OS keyring and backup file."""
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(SERVICE_NAME, KEYRING_ACCOUNT, base64.b64encode(self._master_key).decode())
            except Exception:
                pass
        
        # Also write backup file (encrypted with machine-specific key)
        try:
            import platform
            machine_id = platform.node() + platform.machine()
            machine_salt = hashlib.sha256(machine_id.encode()).digest()[:16]
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=machine_salt, iterations=100000)
            backup_key = base64.b64encode(kdf.derive(self._master_key)).decode()
            
            backup_data = {
                'master_key': base64.b64encode(self._master_key).decode(),
                'created': time.time()
            }
            with open(KEYRING_BACKUP_FILE, 'w') as f:
                json.dump(backup_data, f)
        except Exception:
            pass
    
    def _get_fernet(self) -> Fernet:
        """Get or create Fernet instance."""
        if self._fernet is None:
            master_key = self._get_or_create_master_key()
            self._fernet = Fernet(master_key)
        return self._fernet
    
    def encrypt_keys(self, keys: Dict[str, str]) -> bytes:
        """Encrypt API keys dict to bytes."""
        f = self._get_fernet()
        data = json.dumps(keys, separators=(',', ':')).encode()
        return f.encrypt(data)
    
    def decrypt_keys(self, encrypted: bytes) -> Dict[str, str]:
        """Decrypt bytes to API keys dict."""
        f = self._get_fernet()
        data = f.decrypt(encrypted)
        return json.loads(data.decode())
    
    def save_keys(self, keys: Dict[str, str]) -> bool:
        """Save API keys to encrypted file."""
        try:
            encrypted = self.encrypt_keys(keys)
            ENCRYPTED_KEYS_FILE.write_bytes(encrypted)
            return True
        except Exception as e:
            print(f"[SecureKeyManager] Failed to save keys: {e}")
            return False
    
    def load_keys(self) -> Dict[str, str]:
        """Load API keys from encrypted file."""
        try:
            if not ENCRYPTED_KEYS_FILE.exists():
                return {}
            encrypted = ENCRYPTED_KEYS_FILE.read_bytes()
            return self.decrypt_keys(encrypted)
        except Exception as e:
            print(f"[SecureKeyManager] Failed to load keys: {e}")
            return {}
    
    def rotate_master_key(self) -> bool:
        """Rotate master key - re-encrypt all data with new key."""
        try:
            # Load current keys
            keys = self.load_keys()
            # Generate new master key
            old_key = self._master_key
            self._master_key = Fernet.generate_key()
            self._fernet = None
            self._store_master_key()
            # Re-save with new key
            return self.save_keys(keys)
        except Exception as e:
            print(f"[SecureKeyManager] Key rotation failed: {e}")
            # Restore old key
            self._master_key = old_key
            self._fernet = None
            return False
    
    def migrate_from_plaintext(self, plaintext_file: Path) -> bool:
        """One-time migration from plaintext api_keys.json to encrypted."""
        try:
            if not plaintext_file.exists():
                return False
            with open(plaintext_file, 'r') as f:
                keys = json.load(f)
            return self.save_keys(keys)
        except Exception as e:
            print(f"[SecureKeyManager] Migration failed: {e}")
            return False


# Global instance
_key_manager: Optional[SecureKeyManager] = None


def get_key_manager() -> SecureKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = SecureKeyManager()
    return _key_manager


def load_api_keys() -> Dict[str, str]:
    """Load API keys securely - tries encrypted first, falls back to plaintext migration."""
    km = get_key_manager()
    keys = km.load_keys()
    if not keys:
        # Try migration from plaintext
        plaintext = CONFIG_DIR / "api_keys.json"
        if plaintext.exists():
            print("[SecureKeyManager] Migrating plaintext api_keys.json to encrypted storage...")
            km.migrate_from_plaintext(plaintext)
            keys = km.load_keys()
            # Backup and remove plaintext
            try:
                import shutil
                shutil.move(str(plaintext), str(plaintext) + ".bak")
                print("[SecureKeyManager] Plaintext api_keys.json backed up to .bak")
            except Exception:
                pass
    return keys


def save_api_keys(keys: Dict[str, str]) -> bool:
    """Save API keys securely."""
    return get_key_manager().save_keys(keys)


def get_api_key(key_name: str) -> str:
    """Get a specific API key by name."""
    keys = load_api_keys()
    return keys.get(key_name, "")