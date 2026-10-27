import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet

from shared_core.config import MASTER_KEY_PATH, SECRETS_STORE_PATH, VAULT_DIR


class ZeroTrustSecurityError(PermissionError):
    """Raised when an unauthorized agent attempts to access the vault."""
    pass


class VaultManager:
    def __init__(self, master_key_path: Path = MASTER_KEY_PATH, store_path: Path = SECRETS_STORE_PATH):
        self.master_key_path = master_key_path
        self.store_path = store_path
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        self.master_key_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.master_key_path.parent, 0o700)
        except OSError:
            pass

        if not self.master_key_path.exists():
            key = Fernet.generate_key()
            self.master_key_path.write_bytes(key)
            try:
                os.chmod(self.master_key_path, 0o600)
            except OSError:
                pass

        if not self.store_path.exists():
            self._save_raw_store({})

    def _get_fernet(self) -> Fernet:
        key = self.master_key_path.read_bytes()
        return Fernet(key)

    def _load_raw_store(self) -> Dict[str, Any]:
        fernet = self._get_fernet()
        encrypted_data = self.store_path.read_bytes()
        if not encrypted_data:
            return {}
        decrypted = fernet.decrypt(encrypted_data)
        return json.loads(decrypted.decode("utf-8"))

    def _save_raw_store(self, data: Dict[str, Any]) -> None:
        fernet = self._get_fernet()
        raw = json.dumps(data).encode("utf-8")
        encrypted = fernet.encrypt(raw)
        
        # Atomic write
        temp_file = self.store_path.with_suffix(".tmp")
        temp_file.write_bytes(encrypted)
        os.replace(temp_file, self.store_path)
        try:
            os.chmod(self.store_path, 0o600)
        except OSError:
            pass

    def _validate_caller(self, caller_path: str) -> None:
        """
        Enforces Zero-Trust isolation.
        Only Root Hermes and devops_ministry (including its specialists) are authorized.
        """
        normalized = caller_path.replace("\\", "/").strip("/")
        allowed_prefixes = (
            "root",
            "root_hermes",
            "shared_core/devops_ministry",
            "devops_ministry",
            "My_credential_devops_hermes",
            "Sub_"
        )
        if not any(prefix in normalized for prefix in allowed_prefixes):
            raise ZeroTrustSecurityError(
                f"Zero-Trust Violation: Agent '{caller_path}' is denied direct access to Vault. "
                "You must file a DEVOPS_TICKET to My_credential_devops_hermes."
            )

    def set_secret(self, caller_path: str, secret_ref: str, secret_value: Any) -> None:
        self._validate_caller(caller_path)
        store = self._load_raw_store()
        store[secret_ref] = secret_value
        self._save_raw_store(store)

    def get_secret(self, caller_path: str, secret_ref: str) -> Optional[Any]:
        self._validate_caller(caller_path)
        store = self._load_raw_store()
        return store.get(secret_ref)

    def delete_secret(self, caller_path: str, secret_ref: str) -> bool:
        self._validate_caller(caller_path)
        store = self._load_raw_store()
        if secret_ref in store:
            del store[secret_ref]
            self._save_raw_store(store)
            return True
        return False


_global_vault: Optional[VaultManager] = None

def get_vault() -> VaultManager:
    global _global_vault
    if _global_vault is None:
        _global_vault = VaultManager()
    return _global_vault
