import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import ENCRYPTION_KEY_BASE64


def _key() -> bytes:
    key = base64.b64decode(ENCRYPTION_KEY_BASE64)

    if len(key) != 32:
        raise RuntimeError("ENCRYPTION_KEY_BASE64 precisa representar exatamente 32 bytes")

    return key


def encrypt_json(data: dict) -> dict:
    key = _key()
    aes = AESGCM(key)

    nonce = os.urandom(12)
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    ciphertext = aes.encrypt(nonce, plaintext, None)

    return {
        "alg": "AES-256-GCM",
        "nonce": base64.b64encode(nonce).decode(),
        "data": base64.b64encode(ciphertext).decode(),
    }


def decrypt_json(payload: dict) -> dict:
    key = _key()
    aes = AESGCM(key)

    nonce = base64.b64decode(payload["nonce"])
    ciphertext = base64.b64decode(payload["data"])

    plaintext = aes.decrypt(nonce, ciphertext, None)

    return json.loads(plaintext.decode("utf-8"))


def sha256_hex(value: str) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()
