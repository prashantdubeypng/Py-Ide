"""Secure storage utilities for API keys and secrets."""
import base64
import os
from pathlib import Path
from typing import Optional

from ide.utils.logger import logger

try:
    from cryptography.fernet import Fernet
except ImportError as exc:  # pragma: no cover
    raise ImportError("cryptography package is required for secret encryption. Install with `pip install cryptography`." ) from exc

try:
    import keyring  # Optional but preferred
except ImportError:  # pragma: no cover
    keyring = None


class SecretManager:
    """Encrypts and stores sensitive information using Fernet."""

    SERVICE_NAME = "PyIDE"
    _KEY_ENTRY = "encryption_key"

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._base_dir = Path.home() / ".py_ide" / "keys"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------
    def _get_or_create_key(self) -> bytes:
        """Load an encryption key from keyring or create a new one."""
        key_bytes: Optional[bytes] = None

        if keyring is not None:
            stored = keyring.get_password(self.SERVICE_NAME, self._KEY_ENTRY)
            if stored:
                key_bytes = stored.encode("utf-8")

        if not key_bytes:
            key_bytes = Fernet.generate_key()
            if keyring is not None:
                keyring.set_password(self.SERVICE_NAME, self._KEY_ENTRY, key_bytes.decode("utf-8"))
            else:
                key_file = self._base_dir / "master.key"
                if not key_file.exists():
                    with open(key_file, "wb") as fh:
                        os.chmod(key_file, 0o600)
                        fh.write(key_bytes)
                else:
                    with open(key_file, "rb") as fh:
                        key_bytes = fh.read()

        return key_bytes

    def _get_fernet(self) -> Fernet:
        if self._fernet is None:
            key_bytes = self._get_or_create_key()
            self._fernet = Fernet(key_bytes)
        return self._fernet

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def encrypt(self, value: str) -> str:
        """Encrypt a value using Fernet."""
        if not value:
            return ""
        token = self._get_fernet().encrypt(value.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, value: str) -> str:
        """Decrypt a previously encrypted value."""
        if not value:
            return ""
        try:
            return self._get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except Exception as e:
            # If decryption fails (wrong key, corrupted data), return empty string
            logger.warning(f"Failed to decrypt value: {e}. Returning empty string.")
            return ""

    def set_secret(self, name: str, value: str) -> None:
        """Encrypt and persist a secret for a provider."""
        if not name:
            raise ValueError("Secret name is required")

        encrypted = self.encrypt(value)
        secret_path = self._base_dir / f"{name.lower()}.bin"
        with open(secret_path, "w", encoding="utf-8") as fh:
            fh.write(encrypted)

    def get_secret(self, name: str) -> str:
        """Retrieve and decrypt a stored secret."""
        if not name:
            logger.debug("get_secret called with empty name")
            return ""
        
        secret_path = self._base_dir / f"{name.lower()}.bin"
        logger.debug(f"Looking for secret '{name}' at: {secret_path}")
        
        if not secret_path.exists():
            logger.debug(f"Secret file does not exist: {secret_path}")
            return ""
        
        try:
            with open(secret_path, "r", encoding="utf-8") as fh:
                encrypted = fh.read().strip()
            
            logger.debug(f"Secret file found, encrypted length: {len(encrypted)}")
            decrypted = self.decrypt(encrypted)
            logger.debug(f"Successfully decrypted secret '{name}', length: {len(decrypted)}")
            return decrypted
            
        except Exception as e:
            logger.warning(f"Failed to read secret '{name}': {e}. Returning empty string.")
            return ""

    def delete_secret(self, name: str) -> None:
        secret_path = self._base_dir / f"{name.lower()}.bin"
        if secret_path.exists():
            secret_path.unlink()
